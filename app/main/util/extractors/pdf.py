import base64
import os
from contextlib import suppress
from pathlib import Path

import fitz
from loguru import logger

from app.main.components.openai_client import OpenAIClient


# Minimum image area (px²) to treat a page as scanned / image-heavy.
_MIN_IMAGE_AREA = 90_000

_OPENAI_EXTRACTION_PROMPT = """
    You are a meticulous document extractor.

    GOAL
    Return **only** the page's content as **RAG-ready Markdown**. No preamble, no notes, no explanations.

    STRICT RULES
    1) Visual reading order: top→bottom, left→right.
    2) Structure: Use Markdown headings (#, ##, ###), paragraphs, and bullet/numbered lists to reflect the page's true hierarchy.
    3) Tables: Convert any table to a valid Markdown table with a header row and aligned columns.
    4) Links: Output ALL hyperlinks inline as [text](url) in the exact order they appear.
    5) Figures (images/graphs/charts/diagrams): For any visual element:
    - Identify the figure type.
    - Extract key labels, axes, legends, and data points.
    - Summarise the core insight or conclusion.
    - Embed the description immediately below the visual, starting with "Figure Description:".
    6) Normalization:
    - Remove page furniture (headers/footers, page numbers, watermarks).
    - Merge hyphenated line-breaks (e.g., "inter-\\nnational" → "international").
    - Preserve original language, accents, punctuation, dates, numbers, and casing.
    7) Fidelity: **Do not hallucinate**. Only include content that actually exists on the page.
    8) Output Format: Return **valid Markdown only** (no code fences). No "Answer:" labels, no metadata.

    EDGE CASES
    - If the page is purely scanned, apply the same rules and describe figures where text is unreadable.
    - If there is truly no extractable content, return an empty string: "".
"""


def read_pdf(path: str) -> str:
    """
    Read text from a PDF page-by-page.
    - Uses native text extraction when available.
    - Falls back to OpenAI for scanned / image-heavy pages.
    """
    try:
        doc = fitz.open(path)
    except Exception as e:
        return f"Error opening PDF with PyMuPDF: {e}"

    texts = []

    for page_num, page in enumerate(doc, start=1):
        temp_pdf_path = f"temp_page_{page_num}.pdf"
        native_text = page.get_text("text") or ""

        contains_large_image = _page_has_large_image(doc, page)

        try:
            if contains_large_image:
                logger.info(f"Page {page_num}: likely scanned or image-heavy, extracting via OpenAI...")
                sub_doc = fitz.open()
                sub_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
                sub_doc.save(temp_pdf_path)
                sub_doc.close()
                extracted_text = _extract_page_with_openai(temp_pdf_path)
            elif native_text.strip():
                logger.debug(f"Page {page_num}: native text found.")
                extracted_text = native_text
            else:
                logger.debug(f"Page {page_num}: no content — skipping.")
                extracted_text = ""
        except Exception as e:
            logger.error(f"Error extracting page {page_num}: {e}")
            extracted_text = native_text or ""
        finally:
            with suppress(OSError):
                os.remove(temp_pdf_path)

        texts.append(extracted_text)

    doc.close()
    return "\n".join(filter(None, texts))


def _page_has_large_image(doc: fitz.Document, page: fitz.Page) -> bool:
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.width * pix.height > _MIN_IMAGE_AREA:
                return True
        except Exception:
            continue
    return False


def _extract_page_with_openai(path: str) -> str:
    """Send a single-page PDF to OpenAI for RAG-ready Markdown extraction."""
    try:
        with open(path, "rb") as f:
            data = f.read()

        base64_string = base64.b64encode(data).decode("utf-8")
        filename = Path(path).name
        logger.debug(f"Extracting page '{filename}' via OpenAI...")

        input_data = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": filename,
                        "file_data": f"data:application/pdf;base64,{base64_string}",
                    },
                    {"type": "input_text", "text": _OPENAI_EXTRACTION_PROMPT},
                ],
            }
        ]

        response = OpenAIClient.create_response(input_data=input_data)
        return (getattr(response, "output_text", None) or "").strip()

    except Exception as e:
        logger.error(f"OpenAI page extraction failed: {e}")
        return ""
