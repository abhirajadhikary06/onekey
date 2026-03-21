from ..category_client import CategoryClient


class VectorDBClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "vector_db")


__all__ = ["VectorDBClient"]
