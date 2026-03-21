from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class OnekeyClient:
    base_url: str
    platform_api_key: str
    timeout: int = 90

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.platform_api_key}",
            "Content-Type": "application/json",
        }

    def invoke(self, category: str, provider: str, key_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/proxy/sdk/{category}/{provider}/{key_slug}"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def invoke_legacy(self, provider: str, key_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Backward-compatible endpoint for existing deployments.
        url = f"{self.base_url.rstrip('/')}/proxy/u/{provider}/{key_slug}"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
