from __future__ import annotations

from typing import Any

from ..category_client import CategoryClient


class VectorDBClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "vector_db")

    def upsert(self, provider: str, **kwargs: Any):
        payload = {"operation": "upsert"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def query(self, provider: str, **kwargs: Any):
        payload = {"operation": "query"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def delete(self, provider: str, **kwargs: Any):
        payload = {"operation": "delete"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_collection(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_collection"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_collections(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_collections"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_index(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_index"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_indexes(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_indexes"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_class(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_class"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_classes(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_classes"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_table(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_table"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_tables(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_tables"}
        payload.update(kwargs)
        return self.call(provider, payload)


__all__ = ["VectorDBClient"]
