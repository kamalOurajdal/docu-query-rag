from pathlib import Path

from .image import read_image
from .office import read_csv, read_docx, read_excel, read_pptx
from .pdf import read_pdf
from .text import read_txt


IMAGE_EXTS = {"png", "jpg", "jpeg", "webp"}

_DISPATCHER = {
    "pdf": read_pdf,
    "docx": read_docx,
    "txt": read_txt,
    "csv": read_csv,
    "xlsx": read_excel,
    "pptx": read_pptx,
    "png": read_image,
    "jpg": read_image,
    "jpeg": read_image,
    "webp": read_image,
}


def extract_text(path: str, ext: str) -> str:
    """Dispatch to the appropriate extractor based on file extension."""
    handler = _DISPATCHER.get(ext)
    if handler is None:
        raise ValueError(f"Unsupported extension: {ext} (file: {Path(path).name})")
    return handler(path)


__all__ = [
    "extract_text",
    "read_pdf",
    "read_docx",
    "read_txt",
    "read_csv",
    "read_excel",
    "read_pptx",
    "extract_text_image_with_openai",
    "IMAGE_EXTS",
]
