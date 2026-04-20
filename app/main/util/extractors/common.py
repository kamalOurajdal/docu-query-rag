from typing import Iterable


def normalize_lines(lines: Iterable[str]) -> str:
    """Strip each line, drop empties, and join with newlines."""
    return "\n".join(line for raw in lines if (line := (raw or "").strip()))

