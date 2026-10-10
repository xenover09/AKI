"""Unit tests for AKI's knowledge (book intelligence) subsystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.database_service import DatabaseService
from knowledge.extractor import (
    KnowledgeExtractionError,
    extract_pages,
    is_supported,
)
from knowledge.store import KnowledgeLibrary


@pytest.fixture()
def library(tmp_path) -> KnowledgeLibrary:
    service = DatabaseService(tmp_path / "knowledge.db")
    service.initialize()
    return KnowledgeLibrary(service)


def _build_pdf(path: Path, page_texts: list[str]) -> Path:
    """Construct a valid multi-page PDF with real text and a correct xref."""

    n = len(page_texts)
    page_ids = [4 + 2 * index for index in range(n)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)

    bodies: dict[int, bytes] = {}
    bodies[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    bodies[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()
    bodies[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for index, text in enumerate(page_texts):
        page_id = page_ids[index]
        content_id = page_id + 1
        bodies[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode()

        stream = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
        bodies[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    total_objects = 3 + 2 * n

    for object_id in range(1, total_objects + 1):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n".encode()
        out += bodies[object_id]
        out += b"\nendobj\n"

    xref_position = len(out)
    out += f"xref\n0 {total_objects + 1}\n".encode()
    out += b"0000000000 65535 f \n"

    for object_id in range(1, total_objects + 1):
        out += f"{offsets[object_id]:010d} 00000 n \n".encode()

    out += (
        f"trailer\n<< /Size {total_objects + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF"
    ).encode()

    path.write_bytes(bytes(out))
    return path


class TestExtraction:
    """Page-anchored text extraction."""

    def test_unsupported_extension_rejected(self, tmp_path: Path) -> None:
        file = tmp_path / "photo.png"
        file.write_bytes(b"x")

        assert is_supported(file) is False

        with pytest.raises(KnowledgeExtractionError):
            extract_pages(file)

    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(KnowledgeExtractionError):
            extract_pages(tmp_path / "ghost.pdf")

    def test_text_file_single_page(self, tmp_path: Path) -> None:
        file = tmp_path / "notes.md"
        file.write_text("# Firewall Rules\nDeny all by default.", encoding="utf-8")

        book, pages = extract_pages(file)

        assert book.page_count == 1
        assert pages[0][0] == 1
        assert "Firewall" in pages[0][1]

    def test_pdf_pages_numbered(self, tmp_path: Path) -> None:
        file = _build_pdf(
            tmp_path / "cyber_notes.pdf",
            ["Port scanning with nmap", "Firewalls filter traffic", "Phishing steals credentials"],
        )

        book, pages = extract_pages(file)

        assert book.page_count == 3
        assert [page for page, _ in pages] == [1, 2, 3]
        assert "nmap" in pages[0][1]


class TestLibrary:
    """Ingest, search, and exact page lookup."""

    def test_ingest_and_list(self, library: KnowledgeLibrary, tmp_path: Path) -> None:
        file = tmp_path / "security.md"
        file.write_text(
            "Port scanning basics.\n\nNmap is the standard tool.",
            encoding="utf-8",
        )

        book = library.ingest(str(file))

        assert book.title == "security"
        assert len(library.list_books()) == 1

    def test_reingest_replaces_chunks(
        self, library: KnowledgeLibrary, tmp_path: Path
    ) -> None:
        file = tmp_path / "book.txt"
        file.write_text("version one content", encoding="utf-8")
        library.ingest(str(file))

        file.write_text("version two content " * 50, encoding="utf-8")
        library.ingest(str(file))

        assert len(library.list_books()) == 1

    def test_search_ranks_relevant_chunk(
        self, library: KnowledgeLibrary, tmp_path: Path
    ) -> None:
        file = tmp_path / "cyber.md"
        file.write_text(
            "SQL injection attacks target databases.\n\n"
            "Firewalls filter network traffic.\n\n"
            "Phishing emails steal credentials.\n",
            encoding="utf-8",
        )
        library.ingest(str(file))

        matches = library.search("sql injection database")

        assert matches
        assert "SQL injection" in matches[0].chunk.text

    def test_search_empty_query(self, library: KnowledgeLibrary) -> None:
        assert library.search("   ") == ()

    def test_page_lookup_exact(
        self, library: KnowledgeLibrary, tmp_path: Path
    ) -> None:
        file = tmp_path / "manual.txt"
        file.write_text("Page one content. " * 200, encoding="utf-8")
        book = library.ingest(str(file))

        # Text files are single-page: page 1 must exist, page 9 must not.
        assert library.lookup_page("manual", 1)
        assert library.lookup_page("manual", 9) == ()

    def test_page_lookup_partial_title(
        self, library: KnowledgeLibrary, tmp_path: Path
    ) -> None:
        file = tmp_path / "hacking_handbook.txt"
        file.write_text("Recon techniques.", encoding="utf-8")
        library.ingest(str(file))

        assert library.lookup_page("handbook", 1)
