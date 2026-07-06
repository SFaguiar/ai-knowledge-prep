"""Testes da exportação organizada com manifest (base dos Módulos 2 e 5)."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.models.extraction_result import ExtractionResult, ExtractionSection
from app.services import export_service


def _profile(**overrides) -> ExportProfile:
    base = {"key": "t", "name": "Teste", "description": ""}
    return ExportProfile(**{**base, **overrides})


def _result(*sections: tuple[str, str], backend: str = "fake") -> ExtractionResult:
    secs = [ExtractionSection(title=t, content=c, source_ref=t) for t, c in sections]
    full = "\n\n".join(f"# {t}\n\n{c}" for t, c in sections)
    return ExtractionResult(backend_name=backend, full_text=full, sections=secs)


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


# --- exportação baseada em seções (Etapa 4) ------------------------------------

def test_export_one_file_per_chapter(tmp_path: Path) -> None:
    result = export_service.export_extraction_package(
        "livro",
        _result(("Introdução", "Texto um."), ("Segundo", "Texto dois.")),
        tmp_path,
        _profile(one_file_per_chapter=True, include_index=True),
    )
    chapters = sorted((tmp_path / "capitulos").glob("*.md"))
    assert len(chapters) == 2
    assert chapters[0].name == "01_introducao.md"
    assert (tmp_path / "fonte_completa.md").exists()
    assert (tmp_path / "indice.md").exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    files = [o["file"] for o in manifest["outputs"]]
    assert "capitulos/01_introducao.md" in files
    # Rastreabilidade da origem por capítulo.
    intro = next(o for o in manifest["outputs"] if o["file"] == "capitulos/01_introducao.md")
    assert intro.get("source_ref") == "Introdução"


def test_export_extraction_splits_when_no_chapters(tmp_path: Path) -> None:
    big = " ".join("palavra" for _ in range(400))
    result = export_service.export_extraction_package(
        "doc",
        ExtractionResult(backend_name="fake", full_text=big),
        tmp_path,
        _profile(split_max_chars=200),
    )
    parts = sorted((tmp_path / "partes").glob("parte_*.md"))
    assert len(parts) >= 2
    assert result.backend_name == "fake"


def test_export_extraction_carries_backend_warnings(tmp_path: Path) -> None:
    res = ExtractionResult(backend_name="pymupdf", full_text="conteúdo",
                           warnings=["aviso de teste"])
    conversion = export_service.export_extraction_package(
        "doc", res, tmp_path, _profile()
    )
    assert "aviso de teste" in conversion.warnings
    assert conversion.backend_name == "pymupdf"
