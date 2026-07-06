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
