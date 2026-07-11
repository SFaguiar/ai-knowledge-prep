"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Cria um PDF de 5 páginas com texto simples usando PyMuPDF."""
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Pagina {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    """Cria um PDF de 1 página SEM camada de texto (só a imagem rasterizada),
    simulando um escaneado — para testar a detecção/aplicação de OCR de verdade."""
    fitz = pytest.importorskip("fitz")
    text_doc = fitz.open()
    page = text_doc.new_page()
    page.insert_text((72, 100), "TEXTO DE TESTE OCR", fontsize=24)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes("png")
    text_doc.close()

    img_doc = fitz.open("png", img_bytes)
    pdf_bytes = img_doc.convert_to_pdf()
    img_doc.close()

    path = tmp_path / "scanned.pdf"
    path.write_bytes(pdf_bytes)
    return path
