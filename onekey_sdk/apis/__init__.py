from ..category_client import CategoryClient


class APIsClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "apis")


__all__ = ["APIsClient"]
