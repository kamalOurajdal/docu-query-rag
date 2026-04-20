from loguru import logger

from app.main.components.weaviate_client import WeaviateClient
from app.main.util.enums.weaviate_enums import WeaviateClassEnum


def is_file_indexed(document_id: str) -> bool:
    """Return True if the document already has at least one chunk in Weaviate."""
    try:
        where_filter = {
            "operator": "And",
            "operands": [
                {"path": ["document_id"], "operator": "Equal", "valueString": document_id},
            ],
        }
        return WeaviateClient.weaviate_has_result(
            collection_name=WeaviateClassEnum.APP_DOCUMENTS.value,
            where_filter=where_filter,
        )
    except Exception as e:
        logger.error(f"Error checking if document is indexed: {str(e)}")
        return False
