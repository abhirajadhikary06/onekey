import time
import base64
from datetime import datetime, timezone
import requests
from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from requests.adapters import HTTPAdapter
from sqlalchemy.orm import Session
from urllib3.util.retry import Retry

from . import database, dependencies, models, security
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


CATEGORY_PROVIDER_CONFIG = {
    "vector_db": {
        "pinecone": {"base_url": "https://api.pinecone.io", "auth_header": "Api-Key"},
        "weaviate": {"base_url": None, "auth_header": "Authorization", "bearer": True},
        "qdrant": {"base_url": "https://api.cloud.qdrant.io", "auth_header": "api-key"},
        "milvus": {"base_url": None, "auth_header": "Authorization", "bearer": True},
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


def _map_vector_db_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "pinecone":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/vectors/upsert",
                "json": {
                    "vectors": _required(body, "vectors", operation),
                    "namespace": body.get("namespace"),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/query",
                "json": {
                    "vector": _required(body, "query_vector", operation),
                    "topK": body.get("top_k", 10),
                    "namespace": body.get("namespace"),
                    "filter": body.get("filter"),
                    "includeValues": body.get("include_values", False),
                    "includeMetadata": body.get("include_metadata", True),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": "/vectors/delete",
                "json": {
                    "ids": body.get("ids"),
                    "namespace": body.get("namespace"),
                    "deleteAll": body.get("delete_all", False),
                },
            }
        if operation == "create_index":
            return {
                "method": "POST",
                "endpoint": "/indexes",
                "json": {
                    "name": _required(body, "index_name", operation),
                    "dimension": _required(body, "dimension", operation),
                    "metric": body.get("metric", "cosine"),
                },
            }
        if operation == "list_indexes":
            return {"method": "GET", "endpoint": "/indexes"}

    if provider == "weaviate":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/v1/objects",
                "json": body.get("object")
                or {
                    "class": _required(body, "class_name", operation),
                    "id": body.get("id"),
                    "properties": _required(body, "properties", operation),
                    "vector": body.get("vector"),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/v1/graphql",
                "json": {"query": _required(body, "query", operation)},
            }
        if operation == "delete":
            class_name = _required(body, "class_name", operation)
            object_id = _required(body, "id", operation)
            return {
                "method": "DELETE",
                "endpoint": f"/v1/objects/{class_name}/{object_id}",
            }
        if operation == "create_class":
            return {
                "method": "POST",
                "endpoint": "/v1/schema",
                "json": body.get("schema")
                or {
                    "class": _required(body, "class_name", operation),
                    "properties": body.get("properties", []),
                },
            }
        if operation == "list_classes":
            return {"method": "GET", "endpoint": "/v1/schema"}

    if provider == "qdrant":
        collection = _required(body, "collection", operation)
        if operation == "upsert":
            return {
                "method": "PUT",
                "endpoint": f"/collections/{collection}/points",
                "json": {
                    "points": _required(body, "points", operation),
                    "wait": body.get("wait", True),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": f"/collections/{collection}/points/search",
                "json": {
                    "vector": _required(body, "query_vector", operation),
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                    "with_payload": body.get("with_payload", True),
                    "with_vector": body.get("with_vector", False),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": f"/collections/{collection}/points/delete",
                "json": {
                    "points": body.get("ids")
                    or {"filter": _required(body, "filter", operation)}
                },
            }
        if operation == "create_collection":
            return {
                "method": "PUT",
                "endpoint": f"/collections/{collection}",
                "json": body.get("config")
                or {
                    "vectors": {
                        "size": _required(body, "dimension", operation),
                        "distance": body.get("distance", "Cosine"),
                    }
                },
            }
        if operation == "list_collections":
            return {"method": "GET", "endpoint": "/collections"}

    if provider == "milvus":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/upsert",
                "json": {
                    "collectionName": _required(body, "collection", operation),
                    "data": _required(body, "rows", operation),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/search",
                "json": {
                    "collectionName": _required(body, "collection", operation),
                    "data": [_required(body, "query_vector", operation)],
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/delete",
                "json": {
                    "collectionName": _required(body, "collection", operation),
                    "id": body.get("ids") or _required(body, "id", operation),
                },
            }
        if operation == "create_collection":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/collections/create",
                "json": {
                    "collectionName": _required(body, "collection", operation),
                    "dimension": _required(body, "dimension", operation),
                    "metricType": body.get("metric", "COSINE"),
                },
            }
        if operation == "list_collections":
            return {"method": "POST", "endpoint": "/v2/vectordb/collections/list", "json": {}}

    if provider == "lancedb":
        table = body.get("table") or body.get("collection")
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{_required({'table': table}, 'table', operation)}/upsert",
                "json": {"data": _required(body, "rows", operation)},
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{_required({'table': table}, 'table', operation)}/query",
                "json": {
                    "vector": _required(body, "query_vector", operation),
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{_required({'table': table}, 'table', operation)}/delete",
                "json": {"ids": body.get("ids"), "filter": body.get("filter")},
            }
        if operation == "create_table":
            return {
                "method": "POST",
                "endpoint": "/v1/tables",
                "json": {
                    "name": _required(body, "table", operation),
                    "schema": body.get("schema"),
                },
            }
        if operation == "list_tables":
            return {"method": "GET", "endpoint": "/v1/tables"}

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported vector_db operation '{operation}' for provider '{provider}'",
    )


def _map_devops_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "github":
        if operation == "list_repos":
            return {"method": "GET", "endpoint": "/user/repos", "params": body.get("params")}
        if operation == "get_repo":
            return {
                "method": "GET",
                "endpoint": f"/repos/{_required(body, 'owner', operation)}/{_required(body, 'repo', operation)}",
            }
        if operation == "list_issues":
            return {
                "method": "GET",
                "endpoint": f"/repos/{_required(body, 'owner', operation)}/{_required(body, 'repo', operation)}/issues",
            }
        if operation == "create_issue":
            return {
                "method": "POST",
                "endpoint": f"/repos/{_required(body, 'owner', operation)}/{_required(body, 'repo', operation)}/issues",
                "json": {
                    "title": _required(body, "title", operation),
                    "body": body.get("body", ""),
                    "assignees": body.get("assignees", []),
                    "labels": body.get("labels", []),
                },
            }

    if provider == "gitlab":
        project_id = body.get("project_id")
        if operation == "list_projects":
            return {"method": "GET", "endpoint": "/projects", "params": body.get("params")}
        if operation == "get_project":
            return {"method": "GET", "endpoint": f"/projects/{_required(body, 'project_id', operation)}"}
        if operation == "list_merge_requests":
            return {"method": "GET", "endpoint": f"/projects/{_required({'project_id': project_id}, 'project_id', operation)}/merge_requests"}
        if operation == "create_merge_request":
            return {
                "method": "POST",
                "endpoint": f"/projects/{_required({'project_id': project_id}, 'project_id', operation)}/merge_requests",
                "json": {
                    "source_branch": _required(body, "source_branch", operation),
                    "target_branch": _required(body, "target_branch", operation),
                    "title": _required(body, "title", operation),
                    "description": body.get("description", ""),
                },
            }

    if provider == "bitbucket":
        workspace = _required(body, "workspace", operation)
        if operation == "list_repos":
            return {"method": "GET", "endpoint": f"/repositories/{workspace}"}
        if operation == "get_repo":
            return {
                "method": "GET",
                "endpoint": f"/repositories/{workspace}/{_required(body, 'repo_slug', operation)}",
            }
        if operation == "list_pull_requests":
            return {
                "method": "GET",
                "endpoint": f"/repositories/{workspace}/{_required(body, 'repo_slug', operation)}/pullrequests",
            }
        if operation == "create_pull_request":
            return {
                "method": "POST",
                "endpoint": f"/repositories/{workspace}/{_required(body, 'repo_slug', operation)}/pullrequests",
                "json": _required(body, "payload", operation),
            }

    if provider == "vercel":
        if operation == "list_projects":
            return {"method": "GET", "endpoint": "/v9/projects"}
        if operation == "get_project":
            return {"method": "GET", "endpoint": f"/v9/projects/{_required(body, 'project_id', operation)}"}
        if operation == "list_deployments":
            return {"method": "GET", "endpoint": "/v6/deployments", "params": body.get("params")}
        if operation == "create_deployment":
            return {"method": "POST", "endpoint": "/v13/deployments", "json": _required(body, "payload", operation)}

    if provider == "render":
        if operation == "list_services":
            return {"method": "GET", "endpoint": "/services"}
        if operation == "get_service":
            return {"method": "GET", "endpoint": f"/services/{_required(body, 'service_id', operation)}"}
        if operation == "list_deploys":
            return {"method": "GET", "endpoint": f"/services/{_required(body, 'service_id', operation)}/deploys"}
        if operation == "trigger_deploy":
            return {"method": "POST", "endpoint": f"/services/{_required(body, 'service_id', operation)}/deploys"}

    if provider == "cloudflare":
        if operation == "list_zones":
            return {"method": "GET", "endpoint": "/zones"}
        if operation == "get_zone":
            return {"method": "GET", "endpoint": f"/zones/{_required(body, 'zone_id', operation)}"}
        if operation == "list_dns_records":
            return {"method": "GET", "endpoint": f"/zones/{_required(body, 'zone_id', operation)}/dns_records"}
        if operation == "create_dns_record":
            return {
                "method": "POST",
                "endpoint": f"/zones/{_required(body, 'zone_id', operation)}/dns_records",
                "json": _required(body, "record", operation),
            }

    if provider == "railway":
        if operation == "list_projects":
            return {
                "method": "POST",
                "endpoint": "/",
                "json": {"query": "query { projects { edges { node { id name } } } }"},
            }
        if operation == "project_details":
            return {
                "method": "POST",
                "endpoint": "/",
                "json": {
                    "query": "query($projectId: String!) { project(id: $projectId) { id name services { edges { node { id name } } } } }",
                    "variables": {"projectId": _required(body, "project_id", operation)},
                },
            }

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported devops operation '{operation}' for provider '{provider}'",
    )


def _map_api_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "stripe":
        if operation == "create_payment_intent":
            return {"method": "POST", "endpoint": "/payment_intents", "data": _required(body, "payload", operation)}
        if operation == "retrieve_payment_intent":
            return {"method": "GET", "endpoint": f"/payment_intents/{_required(body, 'payment_intent_id', operation)}"}
        if operation == "list_customers":
            return {"method": "GET", "endpoint": "/customers"}
        if operation == "create_customer":
            return {"method": "POST", "endpoint": "/customers", "data": _required(body, "payload", operation)}

    if provider == "twilio":
        account_sid = _required(body, "account_sid", operation)
        if operation == "send_sms":
            return {
                "method": "POST",
                "endpoint": f"/Accounts/{account_sid}/Messages.json",
                "basic_username": account_sid,
                "data": {
                    "To": _required(body, "to", operation),
                    "From": _required(body, "from", operation),
                    "Body": _required(body, "body", operation),
                },
            }
        if operation == "list_messages":
            return {
                "method": "GET",
                "endpoint": f"/Accounts/{account_sid}/Messages.json",
                "basic_username": account_sid,
            }

    if provider == "sendgrid":
        if operation == "send_email":
            return {"method": "POST", "endpoint": "/mail/send", "json": _required(body, "payload", operation)}
        if operation == "list_templates":
            return {"method": "GET", "endpoint": "/templates"}

    if provider == "slack":
        if operation == "post_message":
            return {
                "method": "POST",
                "endpoint": "/chat.postMessage",
                "json": {
                    "channel": _required(body, "channel", operation),
                    "text": _required(body, "text", operation),
                },
            }
        if operation == "list_channels":
            return {"method": "GET", "endpoint": "/conversations.list"}

    if provider == "notion":
        if operation == "query_database":
            return {
                "method": "POST",
                "endpoint": f"/databases/{_required(body, 'database_id', operation)}/query",
                "json": body.get("payload", {}),
            }
        if operation == "create_page":
            return {"method": "POST", "endpoint": "/pages", "json": _required(body, "payload", operation)}

    if provider == "shopify":
        if operation == "list_products":
            return {"method": "GET", "endpoint": "/admin/api/2024-10/products.json"}
        if operation == "create_product":
            return {
                "method": "POST",
                "endpoint": "/admin/api/2024-10/products.json",
                "json": _required(body, "payload", operation),
            }
        if operation == "list_orders":
            return {"method": "GET", "endpoint": "/admin/api/2024-10/orders.json"}

    if provider == "discord":
        if operation == "create_message":
            return {
                "method": "POST",
                "endpoint": f"/channels/{_required(body, 'channel_id', operation)}/messages",
                "json": {"content": _required(body, "content", operation)},
            }
        if operation == "get_channel":
            return {"method": "GET", "endpoint": f"/channels/{_required(body, 'channel_id', operation)}"}

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported apis operation '{operation}' for provider '{provider}'",
    )


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