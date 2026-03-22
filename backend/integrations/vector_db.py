from fastapi import HTTPException, status

from .common import required


def map_vector_db_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "pinecone":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/vectors/upsert",
                "json": {
                    "vectors": required(body, "vectors", operation),
                    "namespace": body.get("namespace"),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/query",
                "json": {
                    "vector": required(body, "query_vector", operation),
                    "topK": body.get("top_k", 10),
                    "namespace": body.get("namespace"),
                    "filter": body.get("filter"),
                    "includeValues": body.get("include_values", False),
                    "includeMetadata": body.get("include_metadata", True),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": "/vectors/delete",
                "json": {
                    "ids": body.get("ids"),
                    "namespace": body.get("namespace"),
                    "deleteAll": body.get("delete_all", False),
                },
            }
        if operation == "create_index":
            return {
                "method": "POST",
                "endpoint": "/indexes",
                "json": {
                    "name": required(body, "index_name", operation),
                    "dimension": required(body, "dimension", operation),
                    "metric": body.get("metric", "cosine"),
                },
            }
        if operation == "list_indexes":
            return {"method": "GET", "endpoint": "/indexes"}

    if provider == "weaviate":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/v1/objects",
                "json": body.get("object")
                or {
                    "class": required(body, "class_name", operation),
                    "id": body.get("id"),
                    "properties": required(body, "properties", operation),
                    "vector": body.get("vector"),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/v1/graphql",
                "json": {"query": required(body, "query", operation)},
            }
        if operation == "delete":
            class_name = required(body, "class_name", operation)
            object_id = required(body, "id", operation)
            return {
                "method": "DELETE",
                "endpoint": f"/v1/objects/{class_name}/{object_id}",
            }
        if operation == "create_class":
            return {
                "method": "POST",
                "endpoint": "/v1/schema",
                "json": body.get("schema")
                or {
                    "class": required(body, "class_name", operation),
                    "properties": body.get("properties", []),
                },
            }
        if operation == "list_classes":
            return {"method": "GET", "endpoint": "/v1/schema"}

    if provider == "qdrant":
        collection = required(body, "collection", operation)
        if operation == "upsert":
            return {
                "method": "PUT",
                "endpoint": f"/collections/{collection}/points",
                "json": {
                    "points": required(body, "points", operation),
                    "wait": body.get("wait", True),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": f"/collections/{collection}/points/search",
                "json": {
                    "vector": required(body, "query_vector", operation),
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                    "with_payload": body.get("with_payload", True),
                    "with_vector": body.get("with_vector", False),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": f"/collections/{collection}/points/delete",
                "json": {
                    "points": body.get("ids")
                    or {"filter": required(body, "filter", operation)}
                },
            }
        if operation == "create_collection":
            return {
                "method": "PUT",
                "endpoint": f"/collections/{collection}",
                "json": body.get("config")
                or {
                    "vectors": {
                        "size": required(body, "dimension", operation),
                        "distance": body.get("distance", "Cosine"),
                    }
                },
            }
        if operation == "list_collections":
            return {"method": "GET", "endpoint": "/collections"}

    if provider == "milvus":
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/upsert",
                "json": {
                    "collectionName": required(body, "collection", operation),
                    "data": required(body, "rows", operation),
                },
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/search",
                "json": {
                    "collectionName": required(body, "collection", operation),
                    "data": [required(body, "query_vector", operation)],
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/entities/delete",
                "json": {
                    "collectionName": required(body, "collection", operation),
                    "id": body.get("ids") or required(body, "id", operation),
                },
            }
        if operation == "create_collection":
            return {
                "method": "POST",
                "endpoint": "/v2/vectordb/collections/create",
                "json": {
                    "collectionName": required(body, "collection", operation),
                    "dimension": required(body, "dimension", operation),
                    "metricType": body.get("metric", "COSINE"),
                },
            }
        if operation == "list_collections":
            return {"method": "POST", "endpoint": "/v2/vectordb/collections/list", "json": {}}

    if provider == "lancedb":
        table = body.get("table") or body.get("collection")
        if operation == "upsert":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{required({'table': table}, 'table', operation)}/upsert",
                "json": {"data": required(body, "rows", operation)},
            }
        if operation == "query":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{required({'table': table}, 'table', operation)}/query",
                "json": {
                    "vector": required(body, "query_vector", operation),
                    "limit": body.get("top_k", 10),
                    "filter": body.get("filter"),
                },
            }
        if operation == "delete":
            return {
                "method": "POST",
                "endpoint": f"/v1/table/{required({'table': table}, 'table', operation)}/delete",
                "json": {"ids": body.get("ids"), "filter": body.get("filter")},
            }
        if operation == "create_table":
            return {
                "method": "POST",
                "endpoint": "/v1/tables",
                "json": {
                    "name": required(body, "table", operation),
                    "schema": body.get("schema"),
                },
            }
        if operation == "list_tables":
            return {"method": "GET", "endpoint": "/v1/tables"}

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported vector_db operation '{operation}' for provider '{provider}'",
    )
