"""Preset Transcrição para IA — Markdown com timestamps e JSON (Seção 8)."""

from __future__ import annotations

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat

TRANSCRIPTION_AI = ExportProfile(
    key="transcription_ai",
    name="Transcrição para IA",
    description="Markdown com timestamps opcionais, segmentação e JSON de segmentos.",
    output_format=OutputFormat.MARKDOWN,
    include_timestamps=True,
    segments_json=True,
    write_manifest=True,
)
