"""Testes do serviço de OCR (Etapa 5).

Os testes que invocam o OCR de verdade (`apply_ocr`) são pulados quando o
ambiente não tem a cadeia completa (OCRmyPDF + Tesseract + Ghostscript).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import ocr_service

_DEPS_OK, _DEPS_MISSING = ocr_service.ocr_available()
requires_ocr = pytest.mark.skipif(
    not _DEPS_OK, reason=f"dependências de OCR ausentes: {_DEPS_MISSING}"
)


def test_ocr_available_returns_bool_and_list() -> None:
    ok, missing = ocr_service.ocr_available()
    assert isinstance(ok, bool)
    assert isinstance(missing, list)
    assert ok == (not missing)


def test_available_languages_is_list_of_str() -> None:
    langs = ocr_service.available_languages()
    assert isinstance(langs, list)
    assert all(isinstance(code, str) for code in langs)
    assert "osd" not in langs  # não é um idioma de verdade


def test_language_label_known_and_unknown() -> None:
    assert ocr_service.language_label("por") == "Português"
    assert ocr_service.language_label("xyz") == "xyz"  # fallback: o próprio código


def test_is_probably_scanned_false_for_dense_native_text(tmp_path: Path) -> None:
    # sample_pdf tem só "Pagina N" (8 chars) — abaixo do limiar; aqui usamos
    # texto denso o bastante para não ser confundido com pouca camada textual.
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "denso.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Este é um parágrafo com texto nativo suficiente "
                               "para não ser considerado uma página escaneada.")
    doc.save(str(path))
    doc.close()
    assert ocr_service.is_probably_scanned(path) is False


def test_is_probably_scanned_true_for_sparse_native_text(sample_pdf: Path) -> None:
    # "Pagina 1" (8 chars) fica abaixo do limiar de densidade — tratado como
    # candidato a OCR mesmo tendo (pouquíssimo) texto nativo.
    assert ocr_service.is_probably_scanned(sample_pdf) is True


def test_is_probably_scanned_true_for_image_only(scanned_pdf: Path) -> None:
    assert ocr_service.is_probably_scanned(scanned_pdf) is True


def test_apply_ocr_raises_clear_error_when_deps_missing(
    scanned_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr_service, "ocr_available", lambda: (False, ["Tesseract"]))
    with pytest.raises(RuntimeError, match="Tesseract"):
        ocr_service.apply_ocr(scanned_pdf, tmp_path / "out.pdf")


def test_extract_text_returns_one_section_per_page(sample_pdf: Path) -> None:
    result = ocr_service.extract_text(sample_pdf)
    assert result.backend_name == "ocrmypdf"
    assert len(result.sections) == 5
    assert result.sections[0].content == "Pagina 1"
    assert result.sections[0].source_ref == "1"


@requires_ocr
def test_apply_ocr_recognizes_text_on_scanned_pdf(scanned_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "pesquisavel.pdf"
    result_path = ocr_service.apply_ocr(scanned_pdf, out, language="por")
    assert result_path == out
    assert out.exists()

    extracted = ocr_service.extract_text(out)
    assert "TEXTO DE TESTE OCR" in extracted.full_text.upper()


@requires_ocr
def test_apply_ocr_accepts_image_input(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "IMAGEM COM TEXTO", fontsize=24)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_path = tmp_path / "foto.png"
    pix.save(str(img_path))
    doc.close()

    out = tmp_path / "pesquisavel.pdf"
    ocr_service.apply_ocr(img_path, out, language="por")
    assert out.exists()
    extracted = ocr_service.extract_text(out)
    assert "IMAGEM COM TEXTO" in extracted.full_text.upper()


@requires_ocr
def test_apply_ocr_skip_text_preserves_native_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    # PDF já com texto nativo + skip_text (padrão): não deveria falhar, e o
    # texto original permanece recuperável.
    out = tmp_path / "pesquisavel.pdf"
    ocr_service.apply_ocr(sample_pdf, out, force_ocr=False)
    extracted = ocr_service.extract_text(out)
    assert "Pagina 1" in extracted.full_text
