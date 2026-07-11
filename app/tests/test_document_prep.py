"""Testes de ponta a ponta de "Documento para IA" (Etapas 3 e 4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.backends.documents.base import build_default_registry
from app.backends.documents.pymupdf_backend import PyMuPDFBackend
from app.models.extraction_options import ExtractionOptions, OutputFormat
from app.presets import NOTEBOOKLM
from app.services import document_prep_service


def test_reduce_image_noise_on_by_default() -> None:
    assert ExtractionOptions().reduce_image_noise is True


def test_picture_text_regex_strips_noise_blocks() -> None:
    from app.backends.documents.pymupdf4llm_backend import _PICTURE_TEXT

    md = (
        "Texto real antes.\n\n"
        "<!-- Start of picture text -->\nS fo<br>~ fo<br>\n<!-- End of picture text -->\n\n"
        "Texto real depois."
    )
    cleaned = _PICTURE_TEXT.sub("", md)
    assert "picture text" not in cleaned
    assert "S fo" not in cleaned
    assert "Texto real antes." in cleaned
    assert "Texto real depois." in cleaned


def test_inspect_source_reports_pages_and_no_false_warnings(sample_pdf: Path) -> None:
    inspection = document_prep_service.inspect_source(sample_pdf)
    assert inspection.page_count == 5
    # Arquivo local normal (tmp): sem avisos de nuvem/reparo.
    assert inspection.warnings == []


def test_inspect_source_warns_on_cloud_path(tmp_path: Path, monkeypatch) -> None:
    # Simula caminho em pasta de nuvem sem precisar de arquivo real lá.
    fake = tmp_path / "OneDrive" / "livro.pdf"
    fake.parent.mkdir()
    fake.write_bytes(b"%PDF-1.7\n%%EOF\n")
    inspection = document_prep_service.inspect_source(fake)
    assert any("nuvem" in w.lower() for w in inspection.warnings)


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
