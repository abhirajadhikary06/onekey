from __future__ import annotations

from typing import Any

from ..category_client import CategoryClient


class DatabaseClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "database")

    def query(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "query"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def insert(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "insert"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def update(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "update"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def delete(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "delete"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_tables(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "list_tables"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_projects(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "list_projects"}
        payload.update(kwargs)
        return self.call(provider, payload)


__all__ = ["DatabaseClient"]
