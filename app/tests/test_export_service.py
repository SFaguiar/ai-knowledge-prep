"""Testes da exportação organizada com manifest (base dos Módulos 2 e 5)."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.services import export_service


def _profile(**overrides) -> ExportProfile:
    base = {"key": "t", "name": "Teste", "description": ""}
    return ExportProfile(**{**base, **overrides})


def test_export_single_markdown_with_manifest(tmp_path: Path) -> None:
    result = export_service.export_text_package(
        "Meu Livro", "# Título\n\nCorpo.", tmp_path, _profile()
    )
    assert result.success
    assert (tmp_path / "fonte_completa.md").exists()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_name"] == "Meu Livro"
    assert manifest["notes"]["local_only"] is True
    assert manifest["notes"]["telemetry"] is False


def test_export_splits_parts_and_builds_index(tmp_path: Path) -> None:
    content = "\n\n".join(f"Parágrafo {i} " + "x" * 40 for i in range(10))
    result = export_service.export_text_package(
        "pacote", content, tmp_path,
        _profile(split_max_chars=100, include_index=True),
    )
    parts = sorted((tmp_path / "partes").glob("parte_*.md"))
    assert len(parts) >= 2
    assert (tmp_path / "indice.md").exists()
    assert result.manifest_path is not None
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    files = [o["file"] for o in manifest["outputs"]]
    assert "partes/parte_001.md" in files


def test_export_txt_converts_markdown(tmp_path: Path) -> None:
    export_service.export_text_package(
        "t", "# Título\n\n**Negrito**", tmp_path,
        _profile(output_format=OutputFormat.TXT),
    )
    text = (tmp_path / "fonte_completa.txt").read_text(encoding="utf-8")
    assert "#" not in text
    assert "**" not in text
    assert "Título" in text
