"""Unit tests for AKI's attachment reading and web search services."""

from __future__ import annotations

import httpx
import pytest

from desktop.attachment_reader import read_attachment
from services.web_search import WebSearchService


class TestAttachmentReader:
    """File-to-context conversion."""

    def test_text_file_read_verbatim(self, tmp_path) -> None:
        file = tmp_path / "script.py"
        file.write_text("print('hello')", encoding="utf-8")

        content, truncated = read_attachment(str(file))

        assert "print('hello')" in content
        assert "script.py" in content
        assert truncated is False

    def test_large_file_truncated(self, tmp_path) -> None:
        file = tmp_path / "big.txt"
        file.write_text("x" * 5000, encoding="utf-8")

        content, truncated = read_attachment(str(file), max_chars=1000)

        assert truncated is True
        assert "truncated" in content

    def test_binary_file_gets_metadata_note(self, tmp_path) -> None:
        file = tmp_path / "photo.png"
        file.write_bytes(b"\x89PNG...")

        content, truncated = read_attachment(str(file))

        assert "Binary file" in content
        assert truncated is False

    def test_missing_file_handled(self, tmp_path) -> None:
        content, _ = read_attachment(str(tmp_path / "ghost.py"))

        assert "no longer exists" in content


_SAMPLE_HTML = """
<div class="result">
  <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Farticle&amp;rut=x">
    <b>Qatar</b> visa latest updates
  </a>
  <a class="result__snippet" href="#">New rules for <b>work visas</b> announced...</a>
</div>
<div class="result">
  <a class="result__a" href="https://example2.com">Second result</a>
  <a class="result__snippet" href="#">Second snippet text</a>
</div>
"""


class TestWebSearchParsing:
    """HTML parsing against a canned DuckDuckGo response."""

    def make_service(self, html: str, status: int = 200) -> WebSearchService:
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, text=html)
            )
        )
        return WebSearchService(client=client)

    def test_parses_results_and_unwraps_redirect(self) -> None:
        results = self.make_service(_SAMPLE_HTML).search("qatar visa")

        assert len(results) == 2
        assert results[0].url == "https://example.com/article"
        assert "visa" in results[0].title.lower()
        assert "work visas" in results[0].snippet

    def test_rejects_empty_query(self) -> None:
        assert self.make_service("").search("   ") == ()

    def test_http_error_returns_empty(self) -> None:
        assert self.make_service("", status=403).search("anything") == ()

    def test_context_block_rendering(self) -> None:
        results = self.make_service(_SAMPLE_HTML).search("qatar visa")
        context = self.make_service("").render_context(results)

        assert context.startswith("WEB RESULTS")
        assert "1." in context
        assert "example.com/article" in context
