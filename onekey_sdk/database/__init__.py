from ..category_client import CategoryClient


class DatabaseClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "database")


__all__ = ["DatabaseClient"]
