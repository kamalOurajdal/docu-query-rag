import os
from datetime import datetime

from flask import current_app
from loguru import logger
from werkzeug.utils import secure_filename

from app.db.models.app_document import AppDocument
from app.main.components.weaviate_client import WeaviateClient
from app.main.util.enums.embedding_status import EmbeddingStatusEnum
from app.main.util.enums.weaviate_enums import WeaviateClassEnum
from app.main.util.indexing import ALLOWED_EXTS, process_single_file
from app.main.util.utils import generate_id


def upload_and_embed_document(file, name=None) -> tuple:
    """Save an uploaded file, create an AppDocument record, and kick off background embedding."""
    try:
        filename = secure_filename(file.filename or "")
        if not filename:
            return {"status": "error", "message": "Invalid or missing filename"}, 400

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTS:
            return {"status": "error", "message": f"File type .{ext} is not allowed"}, 400

        upload_folder = current_app.config.get("UPLOAD_FOLDER", "./uploads")
        os.makedirs(upload_folder, exist_ok=True)

        unique_filename = f"{generate_id()}_{filename}"
        full_path = os.path.abspath(os.path.join(upload_folder, unique_filename))
        file.save(full_path)

        document = AppDocument(
            name=name or filename,
            path=full_path,
            size=os.path.getsize(full_path),
            embedding={"status": EmbeddingStatusEnum.NOT_STARTED.value},
            created_on=datetime.utcnow().isoformat(),
        )
        document.save()

        result, status_code = process_single_file(app_document=document)
        result["document_id"] = document._id
        return result, status_code

    except Exception as e:
        logger.exception(f"Error uploading and embedding document: {e}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}, 500


def reindex_document(document_id: str) -> tuple:
    """Re-attempt indexing for a document that previously failed or was never indexed."""
    if not document_id:
        return {"status": "error", "message": "document_id is required"}, 400

    app_document = AppDocument().load({"_id": document_id})

    if not app_document or not app_document._id:
        return {"status": "error", "message": "File not found"}, 404

    file_path = app_document.path
    embedding_status = app_document.embedding.get("status")

    if not file_path or not os.path.exists(file_path):
        return {
            "status": "error",
            "message": "File path is invalid or file does not exist. Please re-upload the file.",
        }, 400

    if embedding_status == EmbeddingStatusEnum.DONE.value:
        return {"status": "error", "message": "File is already indexed"}, 400

    if embedding_status == EmbeddingStatusEnum.RUNNING.value:
        return {"status": "error", "message": "File is already being processed"}, 400

    try:
        result = process_single_file(app_document, retry=True)
        return {"status": "success", "data": result}, 202
    except Exception as e:
        logger.exception(f"Error retrying indexing for document_id {document_id}: {e}")
        return {
            "status": "error",
            "message": f"An error occurred while retrying indexing: {str(e)}",
        }, 500


def unindex_document(document_id: str) -> tuple:
    """Remove all Weaviate chunks for a document."""
    try:
        app_document = AppDocument().load({"_id": document_id})
        if not app_document:
            logger.error(f"Document not found: {document_id}")
            return {"status": "error", "message": "Document not found."}, 404

        where_filter = {
            "path": ["document_id"],
            "operator": "Equal",
            "valueString": document_id,
        }
        WeaviateClient.delete_by_filter(WeaviateClassEnum.APP_DOCUMENTS.value, where_filter)

        return {"status": "success", "message": "Document unindexed successfully."}, 200

    except Exception as e:
        logger.error(f"Error unindexing document {document_id}: {e}")
        return {"status": "error", "message": "An error occurred while unindexing the document."}, 500


def reset_processing_files() -> None:
    """On server restart, reset documents stuck in RUNNING state to ERROR."""
    AppDocument().db().update_many(
        {"embedding.status": EmbeddingStatusEnum.RUNNING.value},
        {
            "$set": {
                "embedding.status": EmbeddingStatusEnum.ERROR.value,
                "embedding.message": "Server restarted while processing. Please retry indexing.",
            }
        },
    )
