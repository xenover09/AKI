"""
AKI Automatic Fact Extraction.

Deterministic, regex-based extraction of high-confidence personal facts
from raw user messages, so AKI can remember important details (name,
preferences, explicit instructions) without any AI round-trip.

Only unambiguous patterns are extracted. Anything uncertain is
intentionally ignored — a missed fact is recoverable, a wrong memory
is not.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

from memory.models import Memory, MemoryMetadata, MemorySource, MemoryType


@dataclass(frozen=True)
class ExtractedFact:
    """
    One fact worth remembering.

    Attributes:
        content: Human-readable memory sentence.
        memory_type: Classification used by the memory subsystem.
        tags: Searchable tags attached to the stored memory.
    """

    content: str
    memory_type: MemoryType
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the fact."""

        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError(
                "content must be a non-empty string."
            )

    def to_memory(self) -> Memory:
        """
        Convert the fact into a persistable Memory.

        The memory id is deterministic, so repeating the same fact
        overwrites the previous entry instead of creating duplicates.
        """

        now = datetime.now(timezone.utc)

        return Memory(
            memory_id=fact_memory_id(self),
            content=self.content,
            metadata=MemoryMetadata(
                memory_type=self.memory_type,
                source=MemorySource.USER,
                tags=self.tags,
                importance=0.9,
                confidence=1.0,
            ),
            created_at=now,
            updated_at=now,
        )


_NAME_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:mera\s+naam|my\s+name(?:'s)?\s+is)\s+"
    r"(?P<value>[A-Za-z][A-Za-z']*(?:\s+[A-Za-z][A-Za-z']*){0,2})",
    re.IGNORECASE,
)

# Words that terminate a candidate name. Anything before them may be
# a real name; the words themselves are grammar, never identity.
_NAME_STOPWORDS: Final[frozenset] = frozenset(
    {
        "hai", "he", "h", "hy", "hos", "hoon", "hun",
        "kya", "what", "kaun", "who",
        "aur", "and", "or", "bhi", "to", "tou",
        "ka", "ki", "ko", "se", "mera", "meri",
        "tumara", "tumhara", "tera", "apna", "naam", "name",
    }
)

_PREFERENCE_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:mujhe|mjhe|humein)\s+(?P<value>[A-Za-z0-9 ]{2,40}?)\s+pasand\s*(?:hai|he|h)?\b"
    r"|\bI\s+(?:like|love)\s+(?P<en_value>[A-Za-z0-9 ']{2,40}[^.,!?\n])",
    re.IGNORECASE,
)

_EXPLICIT_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:yaad\s+rakho|yaad\rakho|remember(?:\s+that)?|note\s+karo?)\s*[:,-]?\s*(?P<value>.{4,200})",
    re.IGNORECASE,
)

_TRAILING_FILLER: Final[re.Pattern] = re.compile(
    r"\s+(?:hai|he|h|hoon|hun|mein|main)\s*[.!]*\s*$",
    re.IGNORECASE,
)


def extract_facts(text: str) -> tuple[ExtractedFact, ...]:
    """
    Extract memorable facts from one user message.

    Args:
        text: Raw user message text.

    Returns:
        Unique extracted facts in discovery order. Empty when nothing
        confident was found.
    """

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string."
        )

    cleaned = text.strip()
    if not cleaned:
        return ()

    facts: list[ExtractedFact] = []
    seen: set[str] = set()

    def add_fact(fact: ExtractedFact) -> None:
        key = fact.content.lower()
        if key not in seen:
            seen.add(key)
            facts.append(fact)

    for match in _NAME_PATTERN.finditer(cleaned):
        name = _clean_name_value(match.group("value"))
        if name:
            add_fact(
                ExtractedFact(
                    content=f"User ka naam {name} hai.",
                    memory_type=MemoryType.FACT,
                    tags=("identity", "name", name.lower().split()[0]),
                )
            )

    for match in _PREFERENCE_PATTERN.finditer(cleaned):
        value = match.group("value") or match.group("en_value")
        preference = _clean_value(value)
        if preference:
            add_fact(
                ExtractedFact(
                    content=f"User ko {preference} pasand hai.",
                    memory_type=MemoryType.PREFERENCE,
                    tags=("preference",),
                )
            )

    for match in _EXPLICIT_PATTERN.finditer(cleaned):
        instruction = _clean_value(match.group("value"), keep_sentence=True)
        if instruction:
            add_fact(
                ExtractedFact(
                    content=f"User ne yaad rakhne ko kaha: {instruction}",
                    memory_type=MemoryType.FACT,
                    tags=("explicit",),
                )
            )

    return tuple(facts)


def fact_memory_id(fact: ExtractedFact) -> str:
    """
    Return a stable memory id for a fact.

    The id is derived from the content hash so repeating the same
    information overwrites the existing memory instead of piling up
    duplicates.
    """

    digest = hashlib.md5(  # noqa: S324 - non-crypto dedupe key only
        fact.content.strip().lower().encode("utf-8"),
    ).hexdigest()[:12]

    return f"auto_{digest}"


def _clean_name_value(value: str) -> str:
    """
    Normalize a candidate name; empty string when it is not a name.

    Grammar words (hai, aur, kya, ...) terminate the candidate so
    sentences like "mera naam aether hai aur tumara name aki hai"
    yield exactly "Aether", and questions like "mera naam kya hai?"
    yield nothing at all.
    """

    if not value:
        return ""

    words: list[str] = []

    for word in value.split():
        if word.lower() in _NAME_STOPWORDS:
            break

        words.append(word)

        if len(words) == 2:
            break

    cleaned = " ".join(words).strip()

    if len(cleaned) < 2:
        return ""

    return cleaned.title()


def _clean_value(value: str, *, keep_sentence: bool = False) -> str:
    """Normalize an extracted value; None when it is not usable."""

    if not value:
        return ""

    cleaned = value.strip().strip("\"'.,!?")

    if not keep_sentence:
        cleaned = _TRAILING_FILLER.sub("", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) < 2:
        return ""

    return cleaned


__all__ = [
    "ExtractedFact",
    "extract_facts",
    "fact_memory_id",
]
