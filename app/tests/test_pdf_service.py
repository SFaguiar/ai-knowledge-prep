"""Testes do serviço de PDF (Módulo 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import pdf_service


def test_load_model_counts_pages(sample_pdf: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    assert model.original_page_count == 5
    assert len(model.pages) == 5


def test_remove_pages_and_undo(sample_pdf: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    model.remove_pages({0, 1})
    assert len(model.pages) == 3
    assert model.can_undo
    model.undo()
    assert len(model.pages) == 5


def test_keep_only(sample_pdf: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    model.keep_only({2, 4})
    assert [p.source_index for p in model.pages] == [2, 4]


def test_rotate_pages(sample_pdf: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    model.rotate_pages({0}, 90)
    model.rotate_pages({0}, 90)
    assert model.pages[0].rotation == 180


def test_save_pdf_preserves_original(sample_pdf: Path, tmp_path: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    model.remove_pages({0})
    out = tmp_path / "out.pdf"
    saved = pdf_service.save_pdf(model, out)
    assert saved.exists()
    # Original intacto.
    assert pdf_service.load_model(sample_pdf).original_page_count == 5
    # Saída com 4 páginas.
    assert pdf_service.load_model(saved).original_page_count == 4


def test_save_refuses_existing_without_overwrite(sample_pdf: Path, tmp_path: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    out = tmp_path / "out.pdf"
    out.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        pdf_service.save_pdf(model, out, overwrite=False)


def test_save_refuses_overwriting_source(sample_pdf: Path) -> None:
    model = pdf_service.load_model(sample_pdf)
    with pytest.raises(ValueError):
        pdf_service.save_pdf(model, sample_pdf, overwrite=True)


def test_split_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    outputs = pdf_service.split_pdf(sample_pdf, [(1, 2), (3, 5)], tmp_path)
    assert len(outputs) == 2
    assert pdf_service.load_model(outputs[0]).original_page_count == 2
    assert pdf_service.load_model(outputs[1]).original_page_count == 3
