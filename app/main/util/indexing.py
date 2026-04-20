import math
import threading
from typing import Any, Dict

from flask import copy_current_request_context
from loguru import logger

from app.db.models.app_document import AppDocument
from app.main.components.openai_client import OpenAIClient
from app.main.components.weaviate_client import WeaviateClient
from app.main.util.chunking import chunk_text
from app.main.util.document_utils import is_file_indexed
from app.main.util.enums.embedding_status import EmbeddingStatusEnum
from app.main.util.enums.weaviate_enums import WeaviateClassEnum
from app.main.util.extractors import extract_text


ALLOWED_EXTS = {"pdf", "docx", "txt", "doc", "xlsx", "ppt", "pptx", "png", "jpg", "jpeg", "webp"}
BATCH_SIZE = 20


def process_single_file(app_document: AppDocument, retry: bool = False) -> Dict[str, Any]:
    """
    Kick off background indexing for a document.
    If `retry=True`, first checks whether the document is already indexed in Weaviate.
    """
    original_name = app_document.file_metadata.get("filename")
    try:
        if retry:
            logger.info(f"Retrying indexing for file {app_document.id}...")
            if is_file_indexed(app_document._id):
                app_document.embedding["status"] = EmbeddingStatusEnum.DONE.value
                app_document.embedding["message"] = None
                app_document.save()
                return {"status": "success", "message": "File already indexed"}, 200

        app_document.embedding["status"] = EmbeddingStatusEnum.RUNNING.value
        app_document.save()

        _index_in_background(app_document)

        return {
            "status": EmbeddingStatusEnum.RUNNING.value,
            "message": "Embedding process started successfully.",
        }, 202

    except Exception as e:
        logger.error(f"Error processing file {original_name}: {e}")
        app_document.embedding["status"] = EmbeddingStatusEnum.ERROR.value
        app_document.embedding["message"] = "Error during processing. Please retry again."
        app_document.save()
        return {"status": "error", "message": str(e)}, 500


def _index_in_background(document: AppDocument) -> None:
    """Spawn a daemon thread that extracts, chunks, embeds, and indexes the document."""

    @copy_current_request_context
    def bg_task():
        try:
            ext = document.file_metadata.get("file_type", "").lower()
            text = extract_text(str(document.file_metadata["full_path"]), ext)
            chunks = chunk_text(text)

            if not chunks:
                document.embedding["status"] = EmbeddingStatusEnum.ERROR.value
                document.embedding["message"] = "No extractable text found in document."
                document.save()
                return

            total_batches = math.ceil(len(chunks) / BATCH_SIZE)
            logger.info(
                f"File {document.id}: processing {len(chunks)} chunks "
                f"in {total_batches} batch(es)."
            )

            properties = {
                "filename": document.file_metadata["filename"],
                "document_id": document.id,
            }

            for i in range(0, len(chunks), BATCH_SIZE):
                batch_chunks = chunks[i: i + BATCH_SIZE]
                batch_vectors = OpenAIClient.embed_texts(batch_chunks)
                WeaviateClient.index_chunks(
                    collection_name=WeaviateClassEnum.APP_DOCUMENTS.value,
                    objects=batch_chunks,
                    vectors=batch_vectors,
                    props=properties,
                )

            document.embedding["status"] = EmbeddingStatusEnum.DONE.value
            document.embedding["message"] = None
            document.save()
            logger.info(f"Document '{document.id}' indexed successfully.")

        except Exception as e:
            logger.error(f"Indexing failed for document {document.id}: {str(e)}")
            document.embedding["status"] = EmbeddingStatusEnum.ERROR.value
            document.embedding["message"] = f"Indexing failed: {str(e)}"
            document.save()

    threading.Thread(target=bg_task, daemon=True).start()
