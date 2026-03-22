from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from .llm.client import LLMClient
    from .vector_db import VectorDBClient
    from .devops import DevOpsClient
    from .apis import APIsClient
    from .database import DatabaseClient
    from .data_engineering import DataEngineeringClient


import os

@dataclass
class OnekeyClient:
    base_url: str | None = None
    platform_api_key: str | None = None
    timeout: int = 90

    def __post_init__(self):
        if not self.base_url:
            self.base_url = os.getenv("ONEKEY_BASE_URL") or os.getenv("ONEKEY_URL") or "https://onekey-ciwz.onrender.com"

        if not self.platform_api_key:
            self.platform_api_key = os.getenv("ONEKEY_API_KEY") or os.getenv("ONEKEY_PLATFORM_API_KEY", "")

        if not self.platform_api_key:
            # Try to find it in the local config if not in env
            try:
                from .cli import get_config
                config = get_config()
                self.platform_api_key = config.get("platform_api_key", "")
            except:
                pass
        
        self._llm = None
        self._vector_db = None
        self._devops = None
        self._apis = None
        self._database = None
        self._data_engineering = None

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            from .llm.client import LLMClient
            self._llm = LLMClient(self)
        return self._llm

    @property
    def vector_db(self) -> VectorDBClient:
        if self._vector_db is None:
            from .vector_db import VectorDBClient
            self._vector_db = VectorDBClient(self)
        return self._vector_db

    @property
    def devops(self) -> DevOpsClient:
        if self._devops is None:
            from .devops import DevOpsClient
            self._devops = DevOpsClient(self)
        return self._devops

    @property
    def apis(self) -> APIsClient:
        if self._apis is None:
            from .apis import APIsClient
            self._apis = APIsClient(self)
        return self._apis

    @property
    def database(self) -> DatabaseClient:
        if self._database is None:
            from .database import DatabaseClient
            self._database = DatabaseClient(self)
        return self._database

    @property
    def data_engineering(self) -> DataEngineeringClient:
        if self._data_engineering is None:
            from .data_engineering import DataEngineeringClient
            self._data_engineering = DataEngineeringClient(self)
        return self._data_engineering

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.platform_api_key}",
            "Content-Type": "application/json",
            "X-SDK-Version": "0.1.0",
        }

    def invoke(self, category: str, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Generic invoke method to call any endpoint via the Onekey proxy."""
        url = f"{self.base_url.rstrip('/')}/proxy/sdk/{category}/{provider}"
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            # Re-raise with better context if possible
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = e.response.text or str(e)
            raise Exception(f"Onekey API Error ({e.response.status_code}): {error_detail}") from e
        except Exception as e:
            raise Exception(f"Onekey Connection Error: {str(e)}") from e
