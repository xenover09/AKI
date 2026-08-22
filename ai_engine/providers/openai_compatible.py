"""
AKI OpenAI-Compatible AI Provider.

Talks to any endpoint that implements the OpenAI chat-completions
API shape, which covers OpenAI, Groq, OpenRouter, LM Studio, and
Ollama's compatibility layer. The provider is configured entirely
through its constructor so the boot layer stays in charge of
configuration and tests can inject fake transports.
"""

from __future__ import annotations

import httpx

from ai_engine.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
)
from ai_engine.provider import (
    AIConfigurationError,
    AIProvider,
    AIProviderError,
)

_DEFAULT_TIMEOUT_SECONDS = 60.0


class OpenAICompatibleProvider(AIProvider):
    """
    AI backend for any OpenAI-compatible chat-completions endpoint.

    Responsibilities:
        - Translate AKI's normalized request payload into the
          endpoint's JSON schema.
        - Perform the HTTP call with a bounded timeout.
        - Normalize successful replies into `CompletionResponse`.
        - Convert transport and API failures into the AKI error
          hierarchy.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        """
        Create a provider bound to one endpoint.

        Args:
            base_url: Root URL of the compatible API, for example
                ``https://api.groq.com/openai/v1`` or Ollama's
                ``http://localhost:11434/v1``.
            api_key: Bearer token; local endpoints may accept any
                non-empty placeholder.
            model: Default model identifier used when a request does
                not override it.
            timeout_seconds: Per-request timeout in seconds.
            client: Optional pre-built HTTP client, used by tests to
                inject deterministic transports.

        Raises:
            AIConfigurationError: If required settings are missing.
        """

        if not isinstance(base_url, str) or not base_url.strip():
            raise AIConfigurationError(
                "base_url must be a non-empty string."
            )

        if not isinstance(api_key, str) or not api_key.strip():
            raise AIConfigurationError(
                "api_key must be a non-empty string."
            )

        if not isinstance(model, str) or not model.strip():
            raise AIConfigurationError(
                "model must be a non-empty string."
            )

        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout_seconds = float(timeout_seconds)
        self._client = client
        self._owns_client = client is None

    @property
    def name(self) -> str:
        """Return the provider identifier used in responses."""

        return "openai_compatible"

    @property
    def default_model(self) -> str:
        """Return the configured fallback model identifier."""

        return self._model

    def complete(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """
        Produce one completion through the configured endpoint.

        Raises:
            AIProviderError: On transport failure or non-2xx reply.
        """

        model = request.model or self._model
        payload = {
            "model": model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        payload.update(request.extra)

        try:
            response = self._http_client().post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
        except httpx.HTTPError as error:
            raise AIProviderError(
                f"Could not reach AI endpoint: {error}"
            ) from error

        if response.status_code >= 400:
            raise AIProviderError(
                f"AI endpoint returned {response.status_code}: "
                f"{self._error_detail(response)}",
                status_code=response.status_code,
            )

        body = response.json()

        return self._parse_response(body, model=model)

    # ============================================================
    # Internals
    # ============================================================

    def _http_client(self) -> httpx.Client:
        """Return the injected test client, creating one on first use."""

        if self._client is None:
            self._client = httpx.Client(
                timeout=self._timeout_seconds,
            )

        return self._client

    def close(self) -> None:
        """Close the HTTP client when this provider created it."""

        if self._owns_client and self._client is not None:
            self._client.close()

        self._client = None
        self._owns_client = True

    def _parse_response(
        self,
        body: dict,
        *,
        model: str,
    ) -> CompletionResponse:
        """
        Convert a success envelope into a `CompletionResponse`.

        Raises:
            AIProviderError: If the envelope has no usable content.
        """

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AIProviderError(
                "AI endpoint returned an unexpected response shape."
            ) from error

        usage = body.get("usage") or {}

        return CompletionResponse(
            content=content,
            model=str(body.get("model", model)),
            provider=self.name,
            finish_reason=choice.get("finish_reason"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """Extract a short error message from a failed reply."""

        try:
            detail = response.json()["error"]["message"]
        except Exception:
            detail = response.text[:200]

        return detail


__all__ = [
    "OpenAICompatibleProvider",
]
