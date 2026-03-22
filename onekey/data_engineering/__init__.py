from __future__ import annotations

from typing import Any

from ..category_client import CategoryClient


class DataEngineeringClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "data_engineering")

    def list_jobs(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "list_jobs"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def trigger_sync(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "trigger_sync"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def get_job_status(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "get_job_status"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_connections(self, provider: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"operation": "list_connections"}
        payload.update(kwargs)
        return self.call(provider, payload)


__all__ = ["DataEngineeringClient"]
