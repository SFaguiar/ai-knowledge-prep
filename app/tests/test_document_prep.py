"""Testes de ponta a ponta de "Documento para IA" (Etapas 3 e 4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.backends.documents.base import build_default_registry
from app.backends.documents.pymupdf_backend import PyMuPDFBackend
from app.models.extraction_options import OutputFormat
from app.presets import NOTEBOOKLM
from app.services import document_prep_service


def test_registry_registers_pdf_and_epub_backends() -> None:
    registry = build_default_registry()
    assert registry.get("pymupdf4llm") is not None
    assert registry.get("pymupdf") is not None      # fallback sempre presente
    assert registry.get("epub") is not None


def test_pymupdf_fallback_always_available() -> None:
    assert PyMuPDFBackend().is_available() is True


def test_select_backend_for_pdf_and_epub() -> None:
    assert document_prep_service.select_backend(Path("a.pdf")) is not None
    # EPUB depende do grupo opcional; select pode ser None se ebooklib ausente.
    from app.services import epub_service
    expected = epub_service.is_available()
    assert (document_prep_service.select_backend(Path("a.epub")) is not None) == expected


def test_convert_pdf_to_markdown_package(sample_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "saida"
    result = document_prep_service.convert_document(
        sample_pdf, out, profile=NOTEBOOKLM, output_format=OutputFormat.MARKDOWN
    )
    assert result.success
    assert (out / "fonte_completa.md").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_files"][0]["type"] == "pdf"
    assert manifest["source_files"][0]["pages_total"] == 5
    assert manifest["source_files"][0]["extraction_backend"] in ("pymupdf4llm", "pymupdf")
    # Original preservado.
    assert sample_pdf.exists()


def test_convert_pdf_to_txt(sample_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "saida_txt"
    document_prep_service.convert_document(
        sample_pdf, out, output_format=OutputFormat.TXT
    )
    assert (out / "fonte_completa.txt").exists()
    assert not (out / "fonte_completa.md").exists()


def test_convert_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        document_prep_service.convert_document(tmp_path / "nao_existe.pdf", tmp_path)


def test_convert_epub_package(tmp_path: Path) -> None:
    pytest.importorskip("ebooklib")
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_title("E2E")
    book.set_language("pt")
    c1 = epub.EpubHtml(title="Um", file_name="c1.xhtml")
    c1.content = "<h1>Um</h1><p>Alfa.</p>"
    c2 = epub.EpubHtml(title="Dois", file_name="c2.xhtml")
    c2.content = "<h1>Dois</h1><p>Beta.</p>"
    book.add_item(c1)
    book.add_item(c2)
    book.toc = (c1, c2)
    book.spine = [c1, c2]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub_path = tmp_path / "e2e.epub"
    epub.write_epub(str(epub_path), book)

    out = tmp_path / "saida_epub"
    result = document_prep_service.convert_document(
        epub_path, out, profile=NOTEBOOKLM, output_format=OutputFormat.MARKDOWN
    )
    assert result.success
    full = (out / "fonte_completa.md").read_text(encoding="utf-8")
    assert "Alfa." in full
    assert "Beta." in full
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_files"][0]["type"] == "epub"
    assert manifest["source_files"][0]["extraction_backend"] == "epub"
