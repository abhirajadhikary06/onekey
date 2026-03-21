from __future__ import annotations

from typing import Any

from ..category_client import CategoryClient


class DevOpsClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "devops")

    def list_repos(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_repos"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def get_repo(self, provider: str, **kwargs: Any):
        payload = {"operation": "get_repo"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_issues(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_issues"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_issue(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_issue"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_projects(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_projects"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def get_project(self, provider: str, **kwargs: Any):
        payload = {"operation": "get_project"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_pull_requests(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_pull_requests"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_pull_request(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_pull_request"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_deployments(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_deployments"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_deployment(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_deployment"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_services(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_services"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def get_service(self, provider: str, **kwargs: Any):
        payload = {"operation": "get_service"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def list_zones(self, provider: str, **kwargs: Any):
        payload = {"operation": "list_zones"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def create_dns_record(self, provider: str, **kwargs: Any):
        payload = {"operation": "create_dns_record"}
        payload.update(kwargs)
        return self.call(provider, payload)

    def project_details(self, provider: str, **kwargs: Any):
        payload = {"operation": "project_details"}
        payload.update(kwargs)
        return self.call(provider, payload)


__all__ = ["DevOpsClient"]
