from typing import List


def chunk_text(text: str, chunk_chars: int = 1500, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping fixed-size chunks.
    Tries to avoid cutting mid-sentence by back-tracking to the last period.
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        end = min(i + chunk_chars, n)
        window = text[i:end]

        if end < n:
            dot = window.rfind(".")
            if dot != -1 and dot > chunk_chars // 3:
                end = i + dot + 1
                window = text[i:end]

        chunks.append(window.strip())
        if end == n:
            break
        i = max(end - overlap, i + 1)

    return [c for c in (s.strip() for s in chunks) if c]
