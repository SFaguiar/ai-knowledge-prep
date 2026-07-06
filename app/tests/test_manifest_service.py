"""Testes do serviço de manifest.json (Seção 9)."""

from __future__ import annotations

import json
from pathlib import Path

from app.services import manifest_service


def test_build_manifest_has_local_only_and_no_telemetry() -> None:
    manifest = manifest_service.build_manifest(
        project_name="pacote",
        source_files=[manifest_service.SourceFileEntry(
            file="livro.pdf", type="pdf", pages_total=300,
            pages_included="15-120", pages_removed=[1, 2, 3])],
        outputs=[manifest_service.OutputEntry(
            file="partes/parte_001.md", type="markdown", source_pages="15-35")],
    )
    assert manifest["notes"]["local_only"] is True
    assert manifest["notes"]["telemetry"] is False
    assert manifest["project_name"] == "pacote"
    assert manifest["source_files"][0]["pages_removed"] == [1, 2, 3]
    assert manifest["outputs"][0]["source_pages"] == "15-35"


def test_write_manifest_roundtrip(tmp_path: Path) -> None:
    manifest = manifest_service.build_transcription_manifest(
        source_file="aula.mp4", source_type="video", audio_extracted=True,
        backend="faster-whisper", language="pt",
        outputs=[manifest_service.OutputEntry(file="aula.md", type="markdown")],
    )
    path = manifest_service.write_manifest(manifest, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["transcription_backend"] == "faster-whisper"
    assert data["language"] == "pt"
