"""
AKI AI Provider Abstraction.

Defines the contract every AI backend must satisfy and the error
hierarchy the rest of AKI relies on.

Concrete providers (OpenAI-compatible endpoints, local models, test
fakes) live in `ai_engine.providers` and are selected at boot time.
No other AKI subsystem may depend on a concrete provider class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_engine.models import CompletionRequest, CompletionResponse


class AIError(Exception):
    """Base class for every intelligence-layer failure."""


class AIConfigurationError(AIError):
    """Raised when provider configuration is missing or invalid."""


class AIProviderError(AIError):
    """
    Raised when a configured provider fails at request time.

    Attributes:
        message: Human-readable failure description.
        status_code: HTTP status code when the failure came from a
            remote endpoint, otherwise ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class AIProvider(ABC):
    """
    Abstract backend that turns a completion request into a response.

    Implementations must be safe to call repeatedly and must raise
    ``AIProviderError`` for transport failures and
    ``AIConfigurationError`` for unusable configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the short provider identifier used in responses."""

    @abstractmethod
    def complete(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """
        Produce one completion.

        Args:
            request: Fully validated request payload.

        Returns:
            A normalized completion response.

        Raises:
            AIConfigurationError: If the provider is not usable.
            AIProviderError: If the request fails at the backend.
        """

    def close(self) -> None:
        """
        Release any resources held by the provider.

        The default implementation does nothing; backends that own
        connections override it.
        """


__all__ = [
    "AIConfigurationError",
    "AIError",
    "AIProvider",
    "AIProviderError",
]
