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


def get_user_for_platform_key(db: Session, provided_key: str, return_user_on_invalid_key: bool = False) -> models.User | None:
    # Keys are generated as okp-<user_id>-<random>, so we can resolve owner directly.
    parts = provided_key.split("-", 2)
    if len(parts) < 3 or parts[0] != "okp":
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    is_valid = validate_platform_key(user, provided_key)
    if is_valid:
        return user
    
    return user if return_user_on_invalid_key else None
