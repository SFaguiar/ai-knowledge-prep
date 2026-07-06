"""Geração de manifest.json (Seção 9).

Cada exportação relevante gera um manifesto com rastreabilidade da origem e das
saídas. Marca sempre local_only=true e telemetry=false (Seção 14).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app import __version__


@dataclass
class SourceFileEntry:
    file: str
    type: str
    pages_total: int | None = None
    pages_included: str | None = None
    pages_removed: list[int] = field(default_factory=list)
    ocr_applied: bool | None = None
    extraction_backend: str | None = None

    def to_dict(self) -> dict:
        d = {"file": self.file, "type": self.type}
        if self.pages_total is not None:
            d["pages_total"] = self.pages_total
        if self.pages_included is not None:
            d["pages_included"] = self.pages_included
        if self.pages_removed:
            d["pages_removed"] = self.pages_removed
        if self.ocr_applied is not None:
            d["ocr_applied"] = self.ocr_applied
        if self.extraction_backend is not None:
            d["extraction_backend"] = self.extraction_backend
        return d


@dataclass
class OutputEntry:
    file: str
    type: str
    source_pages: str | None = None
    source_ref: str | None = None

    def to_dict(self) -> dict:
        d = {"file": self.file, "type": self.type}
        if self.source_pages is not None:
            d["source_pages"] = self.source_pages
        if self.source_ref is not None:
            d["source_ref"] = self.source_ref
        return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_manifest(
    project_name: str,
    source_files: list[SourceFileEntry],
    outputs: list[OutputEntry],
    extra_notes: dict | None = None,
) -> dict:
    notes = {"local_only": True, "telemetry": False}
    if extra_notes:
        notes.update(extra_notes)
    return {
        "project_name": project_name,
        "created_at": _now_iso(),
        "tool_version": __version__,
        "source_files": [s.to_dict() for s in source_files],
        "outputs": [o.to_dict() for o in outputs],
        "notes": notes,
    }


def build_transcription_manifest(
    source_file: str,
    source_type: str,
    audio_extracted: bool,
    backend: str,
    language: str,
    outputs: list[OutputEntry],
) -> dict:
    return {
        "source_file": source_file,
        "type": source_type,
        "audio_extracted": audio_extracted,
        "transcription_backend": backend,
        "language": language,
        "created_at": _now_iso(),
        "tool_version": __version__,
        "outputs": [o.to_dict() for o in outputs],
        "notes": {"local_only": True, "telemetry": False},
    }


def write_manifest(manifest: dict, output_dir: str | Path, filename: str = "manifest.json") -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / filename
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
