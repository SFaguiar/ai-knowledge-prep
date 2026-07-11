"""Testes de ponta a ponta do job de OCR (Etapa 5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.jobs.ocr_jobs import ApplyOcrJob
from app.models.extraction_options import OutputFormat
from app.presets import NOTEBOOKLM
from app.services import ocr_service

_DEPS_OK, _DEPS_MISSING = ocr_service.ocr_available()
requires_ocr = pytest.mark.skipif(
    not _DEPS_OK, reason=f"dependências de OCR ausentes: {_DEPS_MISSING}"
)


@requires_ocr
def test_apply_ocr_job_generates_searchable_pdf_and_markdown(
    scanned_pdf: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "saida"
    job = ApplyOcrJob(scanned_pdf, out_dir, language="por")
    result = job.run()

    conversion = result["conversion"]
    assert conversion.success
    assert result["searchable_pdf"].exists()
    assert (out_dir / "fonte_completa.md").exists()

    full = (out_dir / "fonte_completa.md").read_text(encoding="utf-8")
    assert "TEXTO DE TESTE OCR" in full.upper()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_files"][0]["ocr_applied"] is True
    assert manifest["source_files"][0]["extraction_backend"] == "ocrmypdf"
    files = [o["file"] for o in manifest["outputs"]]
    assert any(f.endswith("_pesquisavel.pdf") for f in files)

    # Original preservado.
    assert scanned_pdf.exists()


@requires_ocr
def test_apply_ocr_job_with_notebooklm_preset_and_txt(
    scanned_pdf: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "saida_txt"
    job = ApplyOcrJob(
        scanned_pdf, out_dir, language="por",
        profile=NOTEBOOKLM, output_format=OutputFormat.TXT,
    )
    result = job.run()
    assert result["conversion"].success
    assert (out_dir / "fonte_completa.txt").exists()
    assert not (out_dir / "fonte_completa.md").exists()
