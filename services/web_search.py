"""
AKI Web Search Service.

Fetches live web results through DuckDuckGo's HTML endpoint — no API
key, no extra dependencies. Results are parsed with a tolerant regex
extractor and returned as compact context blocks for the AI layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from logs.logger import get_logger

logger = get_logger("services.web_search")

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_DEFAULT_TIMEOUT = 8.0
_MAX_RESULTS = 5
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_RESULT_LINK = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

_SNIPPET = re.compile(
    r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

_TAG_STRIP = re.compile(r"<[^>]+>")
_URL_DECODE = re.compile(r"&(?:amp|quot|#x27|lt|gt);")


@dataclass(frozen=True)
class SearchResult:
    """One organic web result."""

    title: str
    url: str
    snippet: str


class WebSearchService:
    """
    Live web lookups for AKI's intelligence layer.

    Responsibilities:
        - Query DuckDuckGo's HTML endpoint with a browser-like UA.
        - Parse titles, URLs, and snippets defensively.
        - Render results as a compact context block for prompts.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout_seconds = float(timeout_seconds)
        self._client = client
        self._owns_client = client is None

    def search(self, query: str, *, limit: int = _MAX_RESULTS) -> tuple[SearchResult, ...]:
        """
        Search the web for one query.

        Returns:
            Up to `limit` results; empty tuple on any failure so
            callers can degrade gracefully.
        """

        cleaned = (query or "").strip()

        if not cleaned:
            return ()

        try:
            response = self._http_client().post(
                _SEARCH_URL,
                data={"q": cleaned},
                headers={"User-Agent": _USER_AGENT},
            )
        except httpx.HTTPError as error:
            logger.warning("Web search transport failed: %s", error)
            return ()

        if response.status_code >= 400:
            logger.warning(
                "Web search returned %d for query %r.",
                response.status_code,
                cleaned[:60],
            )
            return ()

        return self._parse(response.text, limit=limit)

    def render_context(self, results: tuple[SearchResult, ...]) -> str:
        """Format results as a prompt context block."""

        if not results:
            return "WEB RESULTS: none found."

        lines = ["WEB RESULTS (live):"]

        for index, result in enumerate(results, start=1):
            snippet = result.snippet[:220]
            lines.append(f"{index}. {result.title} — {snippet} ({result.url})")

        return "\n".join(lines)

    # ============================================================
    # Internals
    # ============================================================

    def _parse(self, html: str, *, limit: int) -> tuple[SearchResult, ...]:
        """Extract organic results from the HTML endpoint's markup."""

        titles = _RESULT_LINK.finditer(html)
        snippets = [m.group("snippet") for m in _SNIPPET.finditer(html)]

        results: list[SearchResult] = []

        for index, match in enumerate(titles):
            if len(results) >= limit:
                break

            title = _clean(match.group("title"))
            url = _clean(match.group("url"))

            # DuckDuckGo wraps URLs in a redirect; unwrap the real one.
            if "uddg=" in url:
                from urllib.parse import parse_qs, urlparse

                try:
                    query = parse_qs(urlparse(url).query)
                    url = query.get("uddg", [url])[0]
                except Exception:
                    pass

            if not title or not url.startswith("http"):
                continue

            snippet = _clean(snippets[index]) if index < len(snippets) else ""

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                )
            )

        return tuple(results)

    def _http_client(self) -> httpx.Client:
        """Return the injected test client, creating one on first use."""

        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout_seconds)

        return self._client

    def close(self) -> None:
        """Close the HTTP client when this service created it."""

        if self._owns_client and self._client is not None:
            self._client.close()

        self._client = None
        self._owns_client = True


def _clean(fragment: str) -> str:
    """Strip tags and decode entities from an HTML fragment."""

    text = _TAG_STRIP.sub("", fragment)
    text = _URL_DECODE.sub(
        lambda m: {
            "&amp;": "&",
            "&quot;": '"',
            "&#x27;": "'",
            "&lt;": "<",
            "&gt;": ">",
        }.get(m.group(0), m.group(0)),
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "SearchResult",
    "WebSearchService",
]
