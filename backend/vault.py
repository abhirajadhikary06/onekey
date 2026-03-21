import re
import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import database, dependencies, models, schemas, security, provider_detection
from .platform_key import get_or_create_platform_key
from .proxy import PROVIDER_CATEGORY_MAP

router = APIRouter(prefix="/keys", tags=["vault"])

# Constants for API key limits
MAX_FREE_API_KEYS = 3
MAX_SUBSCRIBED_API_KEYS = float('inf')  # Unlimited


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return clean.strip("-") or "key"


def _mask_api_key(key: str) -> str:
    """Mask API key showing only first 4 and last 4 characters."""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


class ApiKeyCreate(BaseModel):
    name: str
    key: str
    provider: Optional[str] = None
    expires_at: Optional[datetime] = None


class RequestlyConfigRequest(BaseModel):
    provider: str
    operation: Optional[str] = None


REQUESTLY_PROVIDER_TEMPLATES = {
    "github": {
        "category": "devops",
        "default_operation": "list_repos",
        "operations": {
            "list_repos": {"operation": "list_repos", "per_page": 5, "sort": "updated", "direction": "desc"},
            "get_repo": {"operation": "get_repo", "owner": "torvalds", "repo": "linux"},
            "list_issues": {"operation": "list_issues", "state": "open", "per_page": 3},
        },
    },
    "gitlab": {
        "category": "devops",
        "default_operation": "list_projects",
        "operations": {
            "list_projects": {"operation": "list_projects"},
        },
    },
    "bitbucket": {
        "category": "devops",
        "default_operation": "list_repos",
        "operations": {
            "list_repos": {"operation": "list_repos", "workspace": "your-workspace"},
        },
    },
    "openai": {
        "category": "llm",
        "default_operation": "chat",
        "operations": {
            "chat": {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say hello from Onekey."}],
            }
        },
    },
    "groq": {
        "category": "llm",
        "default_operation": "chat",
        "operations": {
            "chat": {
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": "user", "content": "Say hello from Onekey."}],
            }
        },
    },
    "stripe": {
        "category": "apis",
        "default_operation": "list_customers",
        "operations": {
            "list_customers": {"operation": "list_customers"},
        },
    },
    "slack": {
        "category": "apis",
        "default_operation": "list_channels",
        "operations": {
            "list_channels": {"operation": "list_channels"},
        },
    },
    "pinecone": {
        "category": "vector_db",
        "default_operation": "list_indexes",
        "operations": {
            "list_indexes": {"operation": "list_indexes"},
        },
    },
}


def _default_payload_for_category(category: str) -> dict:
    if category == "llm":
        return {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Say hello from Onekey."}],
        }
    if category == "vector_db":
        return {"operation": "list_indexes"}
    if category == "devops":
        return {"operation": "list_repos"}
    if category == "apis":
        return {"operation": "list_channels"}
    if category == "database":
        return {"operation": "list_tables"}
    if category == "data_engineering":
        return {"operation": "list_projects"}
    return {"operation": "health_check"}


def _build_requestly_payload(provider: str, requested_operation: Optional[str]) -> tuple[str, str, dict, List[str]]:
    provider_slug = provider.strip().lower()
    template = REQUESTLY_PROVIDER_TEMPLATES.get(provider_slug)

    if template:
        category = template["category"]
        operation = requested_operation or template["default_operation"]
        payload = template["operations"].get(operation)
        if not payload:
            operation = template["default_operation"]
            payload = template["operations"][operation]
        available = list(template["operations"].keys())
        return category, operation, payload, available

    category = PROVIDER_CATEGORY_MAP.get(provider_slug)
    if not category:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider_slug}'")

    payload = _default_payload_for_category(category)
    operation = requested_operation or str(payload.get("operation", "chat"))
    if requested_operation:
        payload = {**payload, "operation": requested_operation}
    return category, operation, payload, [operation]


def _build_python_sdk_snippet(category: str, provider: str, payload: dict) -> str:
    payload_json = json.dumps(payload, indent=2)
    return (
        "from onekey_sdk import OnekeyClient\n"
        "import os\n\n"
        "client = OnekeyClient(\n"
        "    base_url=os.getenv(\"ONEKEY_API_URL\", \"https://onekey-ciwz.onrender.com\"),\n"
        "    platform_api_key=os.getenv(\"ONEKEY_PLATFORM_API_KEY\"),\n"
        "    timeout=30,\n"
        ")\n\n"
        f"payload = {payload_json}\n\n"
        f"response = client.invoke(\"{category}\", \"{provider}\", payload)\n"
        "print(response)\n"
    )


def _build_curl_snippet(category: str, provider: str, payload: dict) -> str:
    payload_json = json.dumps(payload)
    return (
        f"curl -X POST https://onekey-ciwz.onrender.com/proxy/sdk/{category}/{provider} "
        "-H \"Authorization: Bearer <ONEKEY_PLATFORM_API_KEY>\" "
        "-H \"Content-Type: application/json\" "
        f"-d '{payload_json}'"
    )


@router.post("/", response_model=schemas.ApiKeyOut, status_code=status.HTTP_201_CREATED)
def add_key(
    key_in: ApiKeyCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    platform_api_key = get_or_create_platform_key(current_user, db)

    # Check rate limit for non-subscribed users
    if not current_user.is_subscribed:
        key_count = (
            db.query(models.ApiKey)
            .filter(models.ApiKey.user_id == current_user.id)
            .count()
        )
        if key_count >= MAX_FREE_API_KEYS:
            raise HTTPException(
                status_code=400,
                detail=f"Free users can only have {MAX_FREE_API_KEYS} API keys. Please delete existing keys or upgrade to premium.",
            )
    
    if key_in.provider:
        provider = key_in.provider.strip().lower()
    else:
        # Auto-detect provider from API key
        try:
            provider = provider_detection.detect_provider(key_in.key)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"{str(e)}. You can also pass provider explicitly in request payload.",
            )
    
    provider_slug = _slugify(provider)
    name_slug = _slugify(key_in.name)

    existing = (
        db.query(models.ApiKey)
        .filter(
            models.ApiKey.user_id == current_user.id,
            models.ApiKey.api_provider == provider_slug,
            models.ApiKey.name_slug == name_slug,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Key name already exists for this provider")

    legacy_unified_api_key_plain = f"apikey-{provider_slug}-{name_slug}"
    expires_at = key_in.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    db_key = models.ApiKey(
        user_id=current_user.id,
        api_provider=provider_slug,
        name=key_in.name.strip(),
        name_slug=name_slug,
        encrypted_key=security.encrypt_api_key(key_in.key),
        unified_key_encrypted=security.encrypt_api_key(legacy_unified_api_key_plain),
        unified_endpoint=f"/proxy/u/{provider_slug}/{name_slug}",
        expires_at=expires_at,
    )

    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    decrypted_key = security.decrypt_api_key(db_key.encrypted_key)

    return schemas.ApiKeyOut(
        id=db_key.id,
        provider=db_key.api_provider,
        name=db_key.name,
        created_at=db_key.created_at,
        expires_at=db_key.expires_at,
        api_key=_mask_api_key(decrypted_key),
        unified_api_key=platform_api_key,
        platform_api_key=platform_api_key,
        unified_endpoint=db_key.unified_endpoint,
    )


@router.get("/", response_model=List[schemas.ApiKeyOut])
def list_keys(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    platform_api_key = get_or_create_platform_key(current_user, db)

    keys = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.user_id == current_user.id)
        .order_by(models.ApiKey.created_at.desc())
        .all()
    )

    return [
        schemas.ApiKeyOut(
            id=k.id,
            provider=k.api_provider,
            name=k.name,
            created_at=k.created_at,
            expires_at=k.expires_at,
            api_key=_mask_api_key(security.decrypt_api_key(k.encrypted_key)),
            unified_api_key=platform_api_key,
            platform_api_key=platform_api_key,
            unified_endpoint=k.unified_endpoint,
        )
        for k in keys
    ]


@router.get("/status", response_model=dict)
def get_key_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Get user's subscription status and API key count."""
    key_count = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.user_id == current_user.id)
        .count()
    )
    max_keys = MAX_SUBSCRIBED_API_KEYS if current_user.is_subscribed else MAX_FREE_API_KEYS
    
    return {
        "is_subscribed": current_user.is_subscribed,
        "key_count": key_count,
        "max_keys": max_keys if max_keys != float('inf') else None,
        "can_add_more": key_count < max_keys,
    }


@router.get("/platform-key", response_model=dict)
def get_platform_key(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    return {
        "platform_api_key": get_or_create_platform_key(current_user, db),
        "usage_note": "Use this same key across all category SDK calls.",
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(
    key_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.id == key_id, models.ApiKey.user_id == current_user.id)
        .first()
    )

    if not key:
        raise HTTPException(status_code=404, detail="Key not found or not owned by you")

    # Optionally cascade delete usage entries for this key
    db.query(models.UsageLog).filter(models.UsageLog.api_key_id == key_id).delete()

    db.delete(key)
    db.commit()
    return None


@router.post("/upgrade", status_code=status.HTTP_200_OK)
def upgrade_to_premium(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Upgrade user to premium subscription (unlimited API keys)."""
    current_user.is_subscribed = True
    db.commit()
    return {
        "message": "Successfully upgraded to premium!",
        "is_subscribed": True,
    }


@router.post("/requestly-config", response_model=dict)
def requestly_config(
    req: RequestlyConfigRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    platform_api_key = get_or_create_platform_key(current_user, db)
    provider = req.provider.strip().lower()
    category, operation, payload, available_ops = _build_requestly_payload(provider, req.operation)

    return {
        "provider": provider,
        "category": category,
        "operation": operation,
        "available_operations": available_ops,
        "endpoint": f"/proxy/sdk/{category}/{provider}",
        "method": "POST",
        "payload": payload,
        "platform_api_key": platform_api_key,
        "python_sdk": _build_python_sdk_snippet(category, provider, payload),
        "curl": _build_curl_snippet(category, provider, payload),
        "requestly_url": "https://requestly.com/",
        "notes": [
            "Clicking Requestly opens the Requestly app.",
            "Onekey also runs the same request immediately and shows output in a modal.",
            "Copy the SDK or curl snippet to reproduce outside the UI.",
        ],
    }
