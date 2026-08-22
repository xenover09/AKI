"""Concrete AI backends for AKI's intelligence layer."""

from ai_engine.providers.mock import MockProvider
from ai_engine.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "MockProvider",
    "OpenAICompatibleProvider",
]
