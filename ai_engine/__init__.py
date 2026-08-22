"""
AKI Intelligence Layer.

Exposes AKI's AI engine: normalized request/response models, the
provider abstraction, concrete providers, prompt assembly, and the
application-facing AIService facade.

Public surface:

    AIService                  High-level entry point.
    PromptManager              Message-sequence assembly.
    AIProvider                 Provider contract (abstract).
    OpenAICompatibleProvider   Groq / OpenAI / Ollama / etc.
    MockProvider               Deterministic offline backend.
    CompletionRequest          Validated request payload.
    CompletionResponse         Normalized provider reply.
    ChatMessage                Single provider message.
    AIError / AIConfigurationError / AIProviderError
"""

from ai_engine.ai_service import AIService
from ai_engine.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
)
from ai_engine.prompt_manager import PromptManager
from ai_engine.provider import (
    AIConfigurationError,
    AIError,
    AIProvider,
    AIProviderError,
)
from ai_engine.providers.mock import MockProvider
from ai_engine.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "AIConfigurationError",
    "AIError",
    "AIProvider",
    "AIProviderError",
    "AIService",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "MockProvider",
    "OpenAICompatibleProvider",
    "PromptManager",
]
