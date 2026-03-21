import secrets

from sqlalchemy.orm import Session

from . import models, security


def _build_platform_key(user_id: int) -> str:
    # One platform-wide key for all category/provider SDK calls of a user.
    return f"okp-{user_id}-{secrets.token_urlsafe(24)}"


def get_or_create_platform_key(user: models.User, db: Session) -> str:
    if user.platform_unified_key_encrypted:
        return security.decrypt_api_key(user.platform_unified_key_encrypted)

    key = _build_platform_key(user.id)
    user.platform_unified_key_encrypted = security.encrypt_api_key(key)
    db.add(user)
    db.commit()
    db.refresh(user)
    return key


def validate_platform_key(user: models.User, provided_key: str) -> bool:
    if not user.platform_unified_key_encrypted:
        return False
    return security.decrypt_api_key(user.platform_unified_key_encrypted) == provided_key
