from typing import Any, Dict

from loguru import logger

from app.main.util.constants import REPORT_REFUSAL_RULE
from app.main.util.rag_utils import perform_rag_generation


def generate_section(data: Dict[str, Any]) -> tuple:
    """
    Generate content for a given query title based on the provided documents.
    Returns formatted paragraphs, or NOT_FOUND when context is insufficient.
    """
    document_ids = data.get("document_ids")
    title = (data.get("title") or "").strip()

    if not document_ids:
        return {"status": "error", "message": "document_ids is required"}, 400
    if not title:
        return {"status": "error", "message": "title is required"}, 400

    try:
        answer_text = perform_rag_generation(
            document_ids=document_ids,
            query=title,
            refusal_rule=REPORT_REFUSAL_RULE,
        )

        if answer_text.strip() == "NOT_FOUND":
            return {"status": "not_found", "content": None}, 404

        return {"content": answer_text}, 200

    except Exception as e:
        logger.error(f"Error generating section: {e}")
        return {"status": "error", "message": "Internal error generating section"}, 500
