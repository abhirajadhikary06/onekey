from __future__ import annotations

from typing import Any

from .client import OnekeyClient


class CategoryClient:
    def __init__(self, client: OnekeyClient, category: str):
        self.client = client
        self.category = category

    def call(self, provider: str, key_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.invoke(self.category, provider, key_slug, payload)
