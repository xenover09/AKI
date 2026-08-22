"""Unit tests for AKI's automatic fact extraction."""

from __future__ import annotations

import pytest

from memory.extraction import (
    ExtractedFact,
    extract_facts,
    fact_memory_id,
)
from memory.models import MemoryType


class TestNameExtraction:
    """Identity facts from Roman Urdu and English."""

    def test_roman_urdu_name(self) -> None:
        facts = extract_facts("hello aki mera naam Aether hai")

        assert len(facts) == 1
        assert facts[0].content == "User ka naam Aether hai."
        assert facts[0].memory_type is MemoryType.FACT
        assert "aether" in facts[0].tags

    def test_name_with_alternate_spelling(self) -> None:
        facts = extract_facts("mera naam aether hy")

        assert facts[0].content == "User ka naam Aether hai."

    def test_compound_sentence_yields_only_the_name(self) -> None:
        # Exactly the shape users type in chat: clauses joined by 'aur'.
        facts = extract_facts(
            "hello aki mera naam aether hai aur tumara name aki hai"
        )

        assert len(facts) == 1
        assert facts[0].content == "User ka naam Aether hai."

    def test_two_word_english_name(self) -> None:
        facts = extract_facts("my name is John Doe")

        assert facts[0].content == "User ka naam John Doe hai."

    def test_question_is_not_memorized(self) -> None:
        assert extract_facts("mera naam kya hai?") == ()

    def test_missing_name_yields_nothing(self) -> None:
        assert extract_facts("mera naam") == ()


class TestPreferenceExtraction:
    """Likes and dislikes."""

    def test_urdu_preference(self) -> None:
        facts = extract_facts("mujhe programming pasand hai")

        assert len(facts) == 1
        assert facts[0].content == "User ko programming pasand hai."
        assert facts[0].memory_type is MemoryType.PREFERENCE

    def test_urdu_preference_without_hai(self) -> None:
        facts = extract_facts("mjhe chai pasand")

        assert facts[0].content == "User ko chai pasand hai."

    def test_english_preference(self) -> None:
        facts = extract_facts("I like dark mode themes")

        assert facts[0].content == "User ko dark mode themes pasand hai."


class TestExplicitMemory:
    """Deliberate remember-me commands."""

    def test_yaad_rakho(self) -> None:
        facts = extract_facts("yaad rakho: kal 9 baje meeting hai")

        assert len(facts) == 1
        assert "kal 9 baje meeting hai" in facts[0].content
        assert "explicit" in facts[0].tags

    def test_remember_that(self) -> None:
        facts = extract_facts("remember that I have an exam on Friday")

        assert len(facts) == 1


class TestExtractionSafety:
    """Uncertain input must produce no memories."""

    def test_empty_and_whitespace(self) -> None:
        assert extract_facts("") == ()
        assert extract_facts("   ") == ()

    def test_plain_chat_produces_nothing(self) -> None:
        assert extract_facts("aaj mausam kaisa hai?") == ()
        assert extract_facts("tell me a joke") == ()

    def test_non_string_rejected(self) -> None:
        with pytest.raises(TypeError):
            extract_facts(123)  # type: ignore[arg-type]

    def test_duplicate_content_deduped(self) -> None:
        facts = extract_facts("mera naam Aether hai. mera naam Aether hai")

        names = [f for f in facts if f.content.startswith("User ka naam")]

        assert len(names) == 1


class TestDeterministicIds:
    """Same fact must always map to the same memory id."""

    def test_id_stable_across_instances(self) -> None:
        fact_a = ExtractedFact(
            content="User ka naam Aether hai.",
            memory_type=MemoryType.FACT,
            tags=("identity",),
        )
        fact_b = ExtractedFact(
            content="user ka naam aether hai.",  # case-insensitive match
            memory_type=MemoryType.FACT,
            tags=("identity",),
        )

        assert fact_memory_id(fact_a) == fact_memory_id(fact_b)
        assert fact_memory_id(fact_a).startswith("auto_")
