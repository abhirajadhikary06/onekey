from ..category_client import CategoryClient


class DataEngineeringClient(CategoryClient):
    def __init__(self, client):
        super().__init__(client, "data_engineering")


__all__ = ["DataEngineeringClient"]
