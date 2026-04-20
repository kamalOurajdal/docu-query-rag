import base64
import mimetypes
from pathlib import Path

from app.main.components.openai_client import OpenAIClient


ALLOWED_IMAGE_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

_EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _mime_for_image(p: Path) -> str:
    mime, _ = mimetypes.guess_type(str(p))
    if mime in ALLOWED_IMAGE_MIME:
        return mime

    mime = _EXT_TO_MIME.get(p.suffix.lower())
    if mime in ALLOWED_IMAGE_MIME:
        return mime

    raise ValueError(f"Unsupported or unknown image MIME for file: {p.name}")


def extract_text_image_with_openai(path: str) -> str:
    """
    Extract text from an image file using OpenAI Vision.
    Returns a plain-text / Markdown representation of the image content.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    data = p.read_bytes()
    if not data:
        raise ValueError(f"File is empty: {p}")

    mime = _mime_for_image(p)
    b64 = base64.b64encode(data).decode("utf-8")
    image_data_url = f"data:{mime};base64,{b64}"

    prompt_text = (
        "You are an expert document analyst tasked with extracting all relevant "
        "information from the image for subsequent use in a Retrieval-Augmented "
        "Generation (RAG) system. Your goal is to provide a complete, coherent, "
        "and structured text representation of the image's content.\n\n"
        "Follow these steps:\n"
        "1. **Text Extraction:** Extract all visible text exactly as it appears, "
        "preserving its logical flow and hierarchy (e.g., headings, bullet points).\n"
        "2. **Data & Tables:** If a table is present, output it as a Markdown table.\n"
        "3. **Visual Analysis (Graphs/Charts/Diagrams):**\n"
        "   a. Identify and state the main title and all axis labels or legend items.\n"
        "   b. Describe the most important data points, trends, and conclusions.\n"
        "   c. For diagrams (flowcharts, etc.), describe the process step-by-step.\n\n"
        "Combine all extracted and analysed information into a single cohesive text block "
        "ready to be chunked for an embedding model."
    )

    return OpenAIClient.chat_completion(
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }],
        max_tokens=2048,
    ) or ""

def read_image(path: str) -> str:
    return extract_text_image_with_openai(path)