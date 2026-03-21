import time
import base64
from datetime import datetime, timezone
import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import database, dependencies, models, security
from .platform_key import get_user_for_platform_key, validate_platform_key

router = APIRouter(prefix="/proxy", tags=["proxy"])


PROVIDER_CATEGORY_MAP = {
    "openai": "llm",
    "groq": "llm",
    "anthropic": "llm",
    "gemini": "llm",
    "openrouter": "llm",
    "mistral": "llm",
    "together": "llm",
    "fireworks": "llm",
    "anyscale": "llm",
    "deepinfra": "llm",
    "nebius": "llm",
    "cohere": "llm",
    "ai21": "llm",
    "perplexity": "llm",
    "deepseek": "llm",
    "qwen": "llm",
    "grok": "llm",
    "replicate": "llm",
    "baseten": "llm",
    "huggingface": "llm",
    "pinecone": "vector_db",
    "weaviate": "vector_db",
    "qdrant": "vector_db",
    "milvus": "vector_db",
    "neondb": "database",
    "xata": "database",
    "airbyte": "data_engineering",
    "dbt": "data_engineering",
    "fivetran": "data_engineering",
    "github": "devops",
    "gitlab": "devops",
    "bitbucket": "devops",
    "supabase": "database",
    "mongodb": "database",
    "planetscale": "database",
    "chroma": "vector_db",
    "dagster": "data_engineering",
    "prefect": "data_engineering",
    "astronomer": "data_engineering",
    "vercel": "devops",
    "render": "devops",
    "cloudflare": "devops",
    "stripe": "apis",
    "twilio": "apis",
    "sendgrid": "apis",
    "slack": "apis",
    "notion": "apis",
    "shopify": "apis",
    "cockroachdb": "database",
    "lancedb": "vector_db",
    "meltano": "data_engineering",
    "railway": "devops",
    "discord": "apis",
}

PROVIDER_ALIASES = {
    "claude": "anthropic",
}


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


CATEGORY_PROVIDER_CONFIG = {
    "vector_db": {
        "pinecone": {"base_url": "https://api.pinecone.io", "auth_header": "Api-Key"},
        "weaviate": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "qdrant": {"base_url": "https://api.cloud.qdrant.io", "auth_header": "api-key"},
        "milvus": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "chroma": {"base_url": "https://api.trychroma.com", "auth_header": "Authorization", "bearer": True},
        "lancedb": {"base_url": None, "auth_header": "Authorization", "bearer": True},
    },
    "database": {
        "neondb": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "xata": {"base_url": "https://api.xata.io", "auth_header": "Authorization", "bearer": True},
        "supabase": {"base_url": "https://api.supabase.com/v1", "auth_header": "apikey"},
        "mongodb": {"base_url": None, "auth_header": "api-key"},
        "planetscale": {"base_url": "https://api.planetscale.com/v1", "auth_header": "Authorization", "bearer": True},
        "cockroachdb": {"base_url": "https://cockroachlabs.cloud/api/v1", "auth_header": "Authorization", "bearer": True},
    },
    "data_engineering": {
        "airbyte": {"base_url": "https://api.airbyte.com/v1", "auth_header": "Authorization", "bearer": True},
        "dbt": {"base_url": "https://cloud.getdbt.com/api/v2", "auth_header": "Authorization", "bearer": True},
        "fivetran": {"base_url": "https://api.fivetran.com/v1", "auth_header": "Authorization", "bearer": True},
        "dagster": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "prefect": {"base_url": "https://api.prefect.cloud/api", "auth_header": "Authorization", "bearer": True},
        "astronomer": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "meltano": {"base_url": None, "auth_header": "Authorization", "bearer": True},
    },
    "devops": {
        "github": {"base_url": "https://api.github.com", "auth_header": "Authorization", "bearer": True},
        "gitlab": {"base_url": "https://gitlab.com/api/v4", "auth_header": "Authorization", "bearer": True},
        "bitbucket": {"base_url": "https://api.bitbucket.org/2.0", "auth_header": "Authorization", "bearer": True},
        "vercel": {"base_url": "https://api.vercel.com", "auth_header": "Authorization", "bearer": True},
        "render": {"base_url": "https://api.render.com/v1", "auth_header": "Authorization", "bearer": True},
        "cloudflare": {"base_url": "https://api.cloudflare.com/client/v4", "auth_header": "Authorization", "bearer": True},
        "railway": {"base_url": "https://backboard.railway.app/graphql/v2", "auth_header": "Authorization", "bearer": True},
    },
    "apis": {
        "stripe": {"base_url": "https://api.stripe.com/v1", "auth_header": "Authorization", "bearer": True},
        "twilio": {"base_url": "https://api.twilio.com/2010-04-01", "auth_mode": "basic"},
        "sendgrid": {"base_url": "https://api.sendgrid.com/v3", "auth_header": "Authorization", "bearer": True},
        "slack": {"base_url": "https://slack.com/api", "auth_header": "Authorization", "bearer": True},
        "notion": {"base_url": "https://api.notion.com/v1", "auth_header": "Authorization", "bearer": True},
        "shopify": {"base_url": None, "auth_header": "X-Shopify-Access-Token"},
        "discord": {"base_url": "https://discord.com/api/v10", "auth_header": "Authorization", "bearer": True},
    },
}


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

    method = str(body.get("method", "POST")).upper()
    endpoint = body.get("endpoint") or body.get("path")
    url = _safe_target_url(cfg.get("base_url"), endpoint)

    headers = dict(body.get("headers", {}))
    auth_mode = cfg.get("auth_mode", "header")
    auth_header = cfg.get("auth_header", "Authorization")
    if auth_mode == "basic":
        token = base64.b64encode(api_key.encode()).decode()
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
            if k not in {"method", "endpoint", "path", "headers", "params", "timeout"}
        }

    return requests.request(
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
    return requests.post(url, headers=headers, json=body)


def _run_groq(api_key: str, body: dict):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_anthropic(api_key: str, body: dict):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_gemini(api_key: str, body: dict):
    # Gemini uses a different format - model in URL
    model = body.get("model", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    return requests.post(url, json=body)


def _run_openrouter(api_key: str, body: dict):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_mistral(api_key: str, body: dict):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_together(api_key: str, body: dict):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_fireworks(api_key: str, body: dict):
    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_anyscale(api_key: str, body: dict):
    url = "https://api.endpoints.anyscale.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_deepinfra(api_key: str, body: dict):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_nebius(api_key: str, body: dict):
    url = "https://api.ai.nebius.cloud/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_cohere(api_key: str, body: dict):
    url = "https://api.cohere.com/v1/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_ai21(api_key: str, body: dict):
    url = "https://api.ai21.com/studio/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_perplexity(api_key: str, body: dict):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_deepseek(api_key: str, body: dict):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_qwen(api_key: str, body: dict):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_grok(api_key: str, body: dict):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)


def _run_replicate(api_key: str, body: dict):
    create_url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    create_resp = requests.post(create_url, headers=headers, json=body)
    if create_resp.status_code >= 400:
        return create_resp
    prediction = create_resp.json()
    prediction_id = prediction.get("id")
    if not prediction_id:
        raise HTTPException(500, "Failed to create prediction")
    
    while True:
        get_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        get_resp = requests.get(get_url, headers=headers)
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
    return requests.post(url, headers=headers, json=body)


def _run_huggingface(api_key: str, body: dict):
    url = "https://api.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=body)

# Note: For "modal", no fixed API endpoint as it's a deployment platform. 
# Users deploy custom endpoints, so proxy not implemented here.
# If you have a specific base URL, you can add it similarly.


async def _proxy_request(provider: str, key_record: models.ApiKey, request: Request, db: Session, category: str = "llm"):
    _ensure_not_expired(key_record)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

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
async def proxy_request_named(
    provider: str,
    name_slug: str,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    provider = _canonical_provider(provider)
    key_record = _find_key_by_name(db, provider, name_slug, current_user.id)
    if not key_record:
        raise HTTPException(404, f"No {provider} key named {name_slug} found for user")

    return await _proxy_request(provider, key_record, request, db, category="llm")


@router.post("/{provider}")
async def proxy_request_default(
    provider: str,
    request: Request,
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

    return await _proxy_request(provider, key_record, request, db, category="llm")


@router.post("/u/{provider}/{name_slug}")
async def proxy_unified(
    provider: str,
    name_slug: str,
    request: Request,
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

    return await _proxy_request(provider, key_record, request, db, category="llm")


@router.post("/sdk/{category}/{provider}/{name_slug}")
async def proxy_unified_category(
    category: str,
    provider: str,
    name_slug: str,
    request: Request,
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

    return await _proxy_request(provider, key_record, request, db, category=category)


@router.post("/sdk/{category}/{provider}")
async def proxy_unified_category_default(
    category: str,
    provider: str,
    request: Request,
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

    return await _proxy_request(provider, key_record, request, db, category=category)