from typing import List

from loguru import logger

from app.main.components.openai_client import OpenAIClient
from app.main.components.weaviate_client import WeaviateClient
from app.main.util.constants import RAG_SYSTEM_PROMPT_TEMPLATE, TOP_K
from app.main.util.enums.weaviate_enums import WeaviateClassEnum


def build_context_block(objects: list) -> str:
    """
    Concatenate non-empty text chunks from Weaviate results into a single context block.
    Returns "(no context)" when nothing is found.
    """
    chunks = [
        txt
        for obj in objects
        if (txt := (obj.get("text") or "").strip())
    ]
    return "\n\n".join(chunks) if chunks else "(no context)"


def perform_rag_generation(
    document_ids: List[str],
    query: str,
    refusal_rule: str,
) -> str:
    """
    Retrieve relevant chunks from Weaviate for the given document IDs and query,
    then call the LLM to generate a structured report section.
    """
    vector = OpenAIClient.embed_texts([query])[0]
    properties = ["document_id", "chunk_index", "text", "filename"]

    where_filter = {
        "operator": "Or",
        "operands": [
            {"path": ["document_id"], "operator": "Equal", "valueText": doc_id}
            for doc_id in document_ids
        ],
    }

    objects = WeaviateClient.search_relevant_chunks(
        WeaviateClassEnum.APP_DOCUMENTS.value,
        vector,
        properties,
        {"top_k": TOP_K, "where": where_filter},
    ) or []

    logger.info(f"RAG retrieved {len(objects)} chunk(s)")
    context_block = build_context_block(objects)

    system_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(refusal_rule=refusal_rule)

    user_prompt = (
        "<SECTION_TITLE>\n"
        f"{query}\n"
        "</SECTION_TITLE>\n\n"
        "<CONTEXT_BLOCK>\n"
        f"{context_block}\n"
        "</CONTEXT_BLOCK>\n\n"
        "Generate the section content now, following the rules."
    )

    return OpenAIClient.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
