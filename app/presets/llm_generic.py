"""Preset LLM genérico — Markdown/TXT dividido por tamanho (Seção 8)."""

from __future__ import annotations

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat

LLM_GENERIC = ExportProfile(
    key="llm_generic",
    name="LLM genérico",
    description="Markdown/TXT dividido por tamanho, com seções e metadados mínimos.",
    output_format=OutputFormat.MARKDOWN,
    split_max_chars=120_000,
    preserve_titles=True,
    write_manifest=True,
)
