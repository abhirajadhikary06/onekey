from fastapi import HTTPException, status


def required(body: dict, key: str, operation: str):
    value = body.get(key)
    if value in (None, ""):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Missing required field '{key}' for operation '{operation}'",
        )
    return value
