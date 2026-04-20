import time
import uuid
from typing import Any, Dict, List, Optional

import weaviate
from flask import current_app
from loguru import logger


class WeaviateClient:
    _instance: Optional['WeaviateClient'] = None
    _client: Optional[weaviate.Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeaviateClient, cls).__new__(cls)
        return cls._instance

    @classmethod
    def ping(cls):
        return cls.get_client().schema.get()

    @classmethod
    def get_client(cls) -> weaviate.Client:
        if cls._client is None:
            weaviate_url = current_app.config.get("WEAVIATE_URL")
            logger.info(f"Connecting to Weaviate at {weaviate_url}")

            auth = None
            auth_config = (current_app.config.get("WEAVIATE_AUTH", {}) if current_app else {}) or {}
            if "api_key" in auth_config:
                auth = weaviate.auth.AuthApiKey(api_key=auth_config["api_key"])
            elif "username" in auth_config and "password" in auth_config:
                auth = weaviate.auth.AuthClientPassword(
                    username=auth_config["username"],
                    password=auth_config["password"],
                )

            client = weaviate.Client(
                url=weaviate_url,
                auth_client_secret=auth,
            )

            for _ in range(60):
                try:
                    client.schema.get()
                    break
                except Exception:
                    time.sleep(1)
            else:
                raise RuntimeError("Weaviate did not become ready in time.")

            cls._client = client

        return cls._client

    @classmethod
    def create_schema(cls, schema_name: str, properties: List[Dict[str, Any]]) -> None:
        client = cls.get_client()

        class_obj = {
            "class": schema_name,
            "properties": properties,
            "vectorizer": "none",
        }
        schema = {"classes": [class_obj]}

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                for cls_obj in schema.get("classes", []):
                    try:
                        client.schema.create_class(cls_obj)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            raise

                logger.info(f"Schema '{schema_name}' created or verified.")
                return

            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Schema '{schema_name}' already exists.")
                    return
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to create schema (attempt {attempt + 1}/{max_retries}): "
                        f"{str(e)}. Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to create schema after {max_retries} attempts: {str(e)}")
                    raise

    @classmethod
    def delete_schema(cls, schema_name: str) -> bool:
        try:
            cls.get_client().schema.delete_class(schema_name)
            logger.info(f"Schema '{schema_name}' deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete schema: {str(e)}")
            return False

    @classmethod
    def search_by_vector(
        cls,
        collection_name: str,
        vector: List[float],
        properties: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if options is None:
            options = {}

        limit = options.get("limit", 3)
        distance = options.get("distance", None)
        client = cls.get_client()

        query = (
            client.query
            .get(collection_name, properties)
            .with_near_vector({
                "vector": vector,
                **({"distance": distance} if distance else {}),
            })
            .with_limit(limit)
        )

        if "where" in options:
            query = query.with_where(options["where"])

        result = query.do()

        items = []
        if result and "data" in result and "Get" in result["data"] and collection_name in result["data"]["Get"]:
            items = result["data"]["Get"][collection_name]

        return items

    @classmethod
    def search_relevant_chunks(
        cls,
        collection_name: str,
        vector: List[float],
        properties: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if options is None:
            options = {}

        top_k = options.get("top_k", 6)
        where_filter = options.get("where", {})

        client = cls.get_client()
        query = client.query.get(collection_name, properties)

        if where_filter:
            query = query.with_where(where_filter)

        result = (
            query
            .with_near_vector({"vector": vector})
            .with_limit(top_k)
            .with_additional(["certainty"])
            .do()
        )

        return (result or {}).get("data", {}).get("Get", {}).get(collection_name, []) or []

    @classmethod
    def index_chunks(
        cls,
        collection_name: str,
        objects: List[str],
        vectors: Optional[List[List[float]]] = None,
        props: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not objects:
            return

        if props is None:
            props = {}

        try:
            weaviate_client = cls.get_client()
            weaviate_client.batch.configure(batch_size=len(objects))

            with weaviate_client.batch as batch:
                for idx, (chunk_text, vec) in enumerate(zip(objects, vectors)):
                    item_props = props.copy()
                    item_props["text"] = chunk_text
                    item_props["chunk_index"] = idx

                    batch.add_data_object(
                        data_object=item_props,
                        class_name=collection_name,
                        uuid=str(uuid.uuid4()),
                        vector=vec,
                    )
        except Exception as e:
            logger.error(f"Failed to index chunks into Weaviate: {str(e)}")
            raise Exception("An error occurred while indexing chunks into Weaviate. Please try again.")

    @classmethod
    def weaviate_has_result(cls, collection_name: str, where_filter: Dict[str, Any]) -> bool:
        """Return True if at least one object matches the given filter."""
        try:
            res = (
                cls.get_client().query
                .get(collection_name, ["_additional { id }"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
        except Exception as e:
            logger.error(f"Weaviate query failed: {e}")
            return False

        objects = (res or {}).get("data", {}).get("Get", {}).get(collection_name, []) or []
        return len(objects) > 0

    @classmethod
    def delete_by_filter(cls, collection_name: str, where_filter: Dict[str, Any]) -> None:
        """Delete all objects in a collection matching the given filter."""
        try:
            cls.get_client().batch.delete_objects(
                class_name=collection_name,
                where=where_filter,
            )
        except Exception as e:
            logger.error(f"Weaviate delete failed: {e}")
