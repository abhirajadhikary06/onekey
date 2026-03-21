import time
import base64
from datetime import datetime, timezone
import requests
from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from requests.adapters import HTTPAdapter
from sqlalchemy.orm import Session
from urllib3.util.retry import Retry

from . import database, dependencies, models, security
from .integrations import (
    CATEGORY_PROVIDER_CONFIG,
    PROVIDER_CATEGORY_MAP,
    map_api_operation,
    map_devops_operation,
    map_vector_db_operation,
)
from .platform_key import get_user_for_platform_key, validate_platform_key

router = APIRouter(prefix="/proxy", tags=["proxy"])

# Reuse outbound connections to reduce DNS/TCP/TLS handshake overhead.
_HTTP = requests.Session()
_ADAPTER = HTTPAdapter(
    pool_connections=128,
    pool_maxsize=128,
    max_retries=Retry(total=0, connect=0, read=0, redirect=0),
)
_HTTP.mount("https://", _ADAPTER)
_HTTP.mount("http://", _ADAPTER)


def _http_post(url: str, *, headers: dict | None = None, json: dict | None = None, timeout: int = 60):
    return _HTTP.post(url, headers=headers, json=json, timeout=timeout)


def _http_get(url: str, *, headers: dict | None = None, timeout: int = 60):
    return _HTTP.get(url, headers=headers, timeout=timeout)


PROVIDER_ALIASES = {}


def _canonical_provider(provider: str) -> str:
    provider = provider.lower().strip()
    return PROVIDER_ALIASES.get(provider, provider)


def _normalize_category(category: str) -> str:
    return category.strip().lower().replace(" ", "").replace("-", "")


def _provider_in_category(provider: str, category: str) -> bool:
    normalized = _normalize_category(category)
    expected = PROVIDER_CATEGORY_MAP.get(provider, "")
    return normalized in {expected, expected.replace("_", "")}


def _ensure_not_expired(key: models.ApiKey) -> None:
    if key.expires_at:
        # Handle both naive and aware datetimes
        expires_at = key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "API key has expired")


def _find_key_by_name(db: Session, provider: str, name_slug: str, user_id: int | None = None):
    q = db.query(models.ApiKey).filter(
        models.ApiKey.api_provider == provider,
        models.ApiKey.name_slug == name_slug,
    )
    if user_id:
        q = q.filter(models.ApiKey.user_id == user_id)
    return q.first()


def _find_latest_key_for_user_provider(db: Session, user_id: int, provider: str):
    return (
        db.query(models.ApiKey)
        .filter(models.ApiKey.user_id == user_id, models.ApiKey.api_provider == provider)
        .order_by(models.ApiKey.created_at.desc())
        .first()
    )


def _extract_provided_key(x_api_key: str | None, authorization: str | None) -> str | None:
    provided_key = x_api_key
    if not provided_key and authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization.split(" ", 1)[1]
    return provided_key


def _required(body: dict, key: str, operation: str):
    value = body.get(key)
    if value in (None, ""):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Missing required field '{key}' for operation '{operation}'",
        )
    return value


def _map_vector_db_operation(provider: str, operation: str, body: dict) -> dict:
    return map_vector_db_operation(provider, operation, body)


def _map_devops_operation(provider: str, operation: str, body: dict) -> dict:
    return map_devops_operation(provider, operation, body)


def _map_api_operation(provider: str, operation: str, body: dict) -> dict:
    return map_api_operation(provider, operation, body)


def _apply_operation_mapping(category: str, provider: str, body: dict) -> dict:
    # If caller already provided explicit endpoint/path, preserve passthrough behavior.
    if body.get("endpoint") or body.get("path"):
        return body

    operation = str(body.get("operation", "")).strip().lower()
    if not operation:
        return body

    if category == "vector_db":
        mapped = _map_vector_db_operation(provider, operation, body)
    elif category == "devops":
        mapped = _map_devops_operation(provider, operation, body)
    elif category == "apis":
        mapped = _map_api_operation(provider, operation, body)
    else:
        return body

    # Preserve caller-provided tuning knobs and headers.
    if body.get("headers") and not mapped.get("headers"):
        mapped["headers"] = body["headers"]
    if body.get("timeout") and not mapped.get("timeout"):
        mapped["timeout"] = body["timeout"]
    if body.get("base_url") and not mapped.get("base_url"):
        mapped["base_url"] = body["base_url"]
    if body.get("basic_username") and not mapped.get("basic_username"):
        mapped["basic_username"] = body["basic_username"]

    return mapped


def _safe_target_url(base_url: str | None, endpoint: str | None) -> str:
    if endpoint and endpoint.startswith("https://"):
        return endpoint
    if not base_url or not endpoint:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "For this provider, supply full HTTPS endpoint in 'endpoint' field",
        )
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _run_category_passthrough(category: str, provider: str, api_key: str, body: dict):
    cfg = CATEGORY_PROVIDER_CONFIG.get(category, {}).get(provider)
    if not cfg:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Proxy not configured for {category}/{provider}")

    body = _apply_operation_mapping(category, provider, body)

    method = str(body.get("method", "POST")).upper()
    endpoint = body.get("endpoint") or body.get("path")
    url = _safe_target_url(body.get("base_url") or cfg.get("base_url"), endpoint)

    headers = dict(body.get("headers", {}))
    auth_mode = cfg.get("auth_mode", "header")
    auth_header = cfg.get("auth_header", "Authorization")
    if auth_mode == "basic":
        basic_username = body.get("basic_username")
        basic_secret = f"{basic_username}:{api_key}" if basic_username else api_key
        token = base64.b64encode(basic_secret.encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    elif cfg.get("bearer", False):
        headers[auth_header] = f"Bearer {api_key}"
    else:
        headers[auth_header] = api_key

    params = body.get("params")
    json_payload = body.get("json")
    data_payload = body.get("data")
    timeout = int(body.get("timeout", 60))

    if json_payload is None and data_payload is None:
        json_payload = {
            k: v for k, v in body.items()
            if k not in {
                "method",
                "endpoint",
                "path",
                "headers",
                "params",
                "timeout",
                "operation",
                "base_url",
                "basic_username",
            }
        }

    return _HTTP.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_payload,
        data=data_payload,
        timeout=timeout,
    )


def _run_openai(api_key: str, body: dict):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_groq(api_key: str, body: dict):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_anthropic(api_key: str, body: dict):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_gemini(api_key: str, body: dict):
    # Gemini uses a different format - model in URL
    model = body.get("model", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    return _http_post(url, json=body)


def _run_openrouter(api_key: str, body: dict):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_mistral(api_key: str, body: dict):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_together(api_key: str, body: dict):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_fireworks(api_key: str, body: dict):
    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_anyscale(api_key: str, body: dict):
    url = "https://api.endpoints.anyscale.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_deepinfra(api_key: str, body: dict):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_nebius(api_key: str, body: dict):
    url = "https://api.ai.nebius.cloud/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_cohere(api_key: str, body: dict):
    url = "https://api.cohere.com/v1/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_ai21(api_key: str, body: dict):
    url = "https://api.ai21.com/studio/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_perplexity(api_key: str, body: dict):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_deepseek(api_key: str, body: dict):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_qwen(api_key: str, body: dict):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_grok(api_key: str, body: dict):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_replicate(api_key: str, body: dict):
    create_url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    create_resp = _http_post(create_url, headers=headers, json=body)
    if create_resp.status_code >= 400:
        return create_resp
    prediction = create_resp.json()
    prediction_id = prediction.get("id")
    if not prediction_id:
        raise HTTPException(500, "Failed to create prediction")
    
    while True:
        get_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        get_resp = _http_get(get_url, headers=headers)
        if get_resp.status_code >= 400:
            return get_resp
        data = get_resp.json()
        status = data.get("status")
        if status in ["succeeded", "failed", "canceled"]:
            # Return the get_resp as the final response
            return get_resp
        time.sleep(1)


def _run_baseten(api_key: str, body: dict):
    url = "https://inference.baseten.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)


def _run_huggingface(api_key: str, body: dict):
    url = "https://api.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return _http_post(url, headers=headers, json=body)

# Note: For "modal", no fixed API endpoint as it's a deployment platform. 
# Users deploy custom endpoints, so proxy not implemented here.
# If you have a specific base URL, you can add it similarly.


def _proxy_request(provider: str, key_record: models.ApiKey, body: dict, db: Session, category: str = "llm"):
    _ensure_not_expired(key_record)

    api_key = security.decrypt_api_key(key_record.encrypted_key)

    start_time = time.time()
    if category == "llm":
        if provider == "openai":
            resp = _run_openai(api_key, body)
        elif provider == "groq":
            resp = _run_groq(api_key, body)
        elif provider == "anthropic":
            resp = _run_anthropic(api_key, body)
        elif provider == "gemini":
            resp = _run_gemini(api_key, body)
        elif provider == "openrouter":
            resp = _run_openrouter(api_key, body)
        elif provider == "mistral":
            resp = _run_mistral(api_key, body)
        elif provider == "together":
            resp = _run_together(api_key, body)
        elif provider == "fireworks":
            resp = _run_fireworks(api_key, body)
        elif provider == "anyscale":
            resp = _run_anyscale(api_key, body)
        elif provider == "deepinfra":
            resp = _run_deepinfra(api_key, body)
        elif provider == "nebius":
            resp = _run_nebius(api_key, body)
        elif provider == "cohere":
            resp = _run_cohere(api_key, body)
        elif provider == "ai21":
            resp = _run_ai21(api_key, body)
        elif provider == "perplexity":
            resp = _run_perplexity(api_key, body)
        elif provider == "deepseek":
            resp = _run_deepseek(api_key, body)
        elif provider == "qwen":
            resp = _run_qwen(api_key, body)
        elif provider == "grok":
            resp = _run_grok(api_key, body)
        elif provider == "replicate":
            resp = _run_replicate(api_key, body)
        elif provider == "baseten":
            resp = _run_baseten(api_key, body)
        elif provider == "huggingface":
            resp = _run_huggingface(api_key, body)
        else:
            raise HTTPException(400, f"Proxy not implemented for {provider}")
    else:
        resp = _run_category_passthrough(category, provider, api_key, body)

    latency = int((time.time() - start_time) * 1000)

    usage_log = models.UsageLog(
        user_id=key_record.user_id,
        api_key_id=key_record.id,
        api_provider=provider,
        endpoint_or_model=body.get("model") or body.get("endpoint") or body.get("path") or "unknown",
        status_code=resp.status_code,
        latency_ms=latency,
        total_tokens=resp.json().get("usage", {}).get("total_tokens", 0) if resp.ok else 0,
    )
    db.add(usage_log)
    db.commit()

    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)

    return resp.json()

@router.post("/{provider}/{name_slug}")
def proxy_request_named(
    provider: str,
    name_slug: str,
    body: dict = Body(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    provider = _canonical_provider(provider)
    key_record = _find_key_by_name(db, provider, name_slug, current_user.id)
    if not key_record:
        raise HTTPException(404, f"No {provider} key named {name_slug} found for user")

    return _proxy_request(provider, key_record, body, db, category="llm")


@router.post("/{provider}")
def proxy_request_default(
    provider: str,
    body: dict = Body(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    provider = _canonical_provider(provider)
    key_record = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.user_id == current_user.id, models.ApiKey.api_provider == provider)
        .order_by(models.ApiKey.created_at.desc())
        .first()
    )
    if not key_record:
        raise HTTPException(404, f"No {provider} key found for user")

    return _proxy_request(provider, key_record, body, db, category="llm")


@router.post("/u/{provider}/{name_slug}")
def proxy_unified(
    provider: str,
    name_slug: str,
    body: dict = Body(...),
    db: Session = Depends(database.get_db),
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    provider = _canonical_provider(provider)
    key_record = _find_key_by_name(db, provider, name_slug, user_id=None)
    if not key_record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unified key not found")

    provided_key = _extract_provided_key(x_api_key, authorization)

    if not provided_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")

    owner = db.query(models.User).filter(models.User.id == key_record.user_id).first()
    if not owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User for API key not found")

    if not validate_platform_key(owner, provided_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    return _proxy_request(provider, key_record, body, db, category="llm")


@router.post("/sdk/{category}/{provider}/{name_slug}")
def proxy_unified_category(
    category: str,
    provider: str,
    name_slug: str,
    body: dict = Body(...),
    db: Session = Depends(database.get_db),
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    provider = _canonical_provider(provider)
    key_record = _find_key_by_name(db, provider, name_slug, user_id=None)
    if not key_record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unified key not found")

    if not _provider_in_category(provider, category):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Provider '{provider}' does not belong to category '{category}'",
        )

    provided_key = _extract_provided_key(x_api_key, authorization)

    if not provided_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")

    owner = db.query(models.User).filter(models.User.id == key_record.user_id).first()
    if not owner or not validate_platform_key(owner, provided_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid platform API key")

    return _proxy_request(provider, key_record, body, db, category=category)


@router.post("/sdk/{category}/{provider}")
def proxy_unified_category_default(
    category: str,
    provider: str,
    body: dict = Body(...),
    db: Session = Depends(database.get_db),
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    authorization: str | None = Header(default=None),
):
    provider = _canonical_provider(provider)

    if not _provider_in_category(provider, category):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Provider '{provider}' does not belong to category '{category}'",
        )

    provided_key = _extract_provided_key(x_api_key, authorization)
    if not provided_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")

    owner = get_user_for_platform_key(db, provided_key)
    if not owner:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid platform API key")

    key_record = _find_latest_key_for_user_provider(db, owner.id, provider)
    if not key_record:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No API key configured for provider '{provider}'",
        )

    return _proxy_request(provider, key_record, body, db, category=category)