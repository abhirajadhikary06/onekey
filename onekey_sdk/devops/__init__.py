from ..category_client import CategoryClient


class DevOpsClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "devops")


__all__ = ["DevOpsClient"]
