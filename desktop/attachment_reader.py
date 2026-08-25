"""
AKI Attachment Reader.

Turns a selected file into a text block the AI can reason about.
Text-like files are read verbatim (size-capped); binary formats are
summarized by their metadata instead of failing.
"""

from __future__ import annotations

from pathlib import Path

_MAX_ATTACHMENT_CHARS = 12_000

_TEXT_EXTENSIONS = frozenset(
    {
        ".txt", ".md", ".py", ".js", ".ts", ".json", ".html", ".css",
        ".csv", ".xml", ".yml", ".yaml", ".ini", ".cfg", ".log",
        ".sh", ".bat", ".ps1", ".sql", ".java", ".c", ".cpp", ".h",
        ".rs", ".go", ".rb", ".php", ".toml", ".env",
    }
)


def read_attachment(
    file_path: str,
    *,
    max_chars: int = _MAX_ATTACHMENT_CHARS,
) -> tuple[str, bool]:
    """
    Read one attachment for AI context.

    Args:
        file_path: Absolute path selected by the user.
        max_chars: Upper bound on returned content length.

    Returns:
        Tuple of (content_block, truncated). The block is ready to
        append to a prompt; unreadable/binary files return a short
        metadata note instead of raising.
    """

    path = Path(file_path)

    if not path.exists():
        return "[ATTACHED FILE: file no longer exists]", False

    suffix = path.suffix.lower()
    size_bytes = path.stat().st_size

    header = f"[ATTACHED FILE: {path.name} | {size_bytes} bytes]"

    if suffix not in _TEXT_EXTENSIONS:
        return f"{header}\n(Binary file — content cannot be shown as text.)", False

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as error:
        return f"{header}\n(File could not be read: {error})", False

    if len(raw) <= max_chars:
        return f"{header}\n{raw}", False

    truncated = raw[:max_chars]
    return (
        f"{header}\n{truncated}\n[...file truncated at {max_chars} characters...]",
        True,
    )


__all__ = [
    "read_attachment",
]
