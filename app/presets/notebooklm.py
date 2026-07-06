"""Preset NotebookLM — fontes limpas para upload no NotebookLM (Seção 8)."""

from __future__ import annotations

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat

NOTEBOOKLM = ExportProfile(
    key="notebooklm",
    name="NotebookLM",
    description="Fontes limpas para upload no NotebookLM.",
    output_format=OutputFormat.MARKDOWN,
    split_max_chars=180_000,
    preserve_titles=True,
    strip_repeated_headers=True,
    include_index=True,
    write_manifest=True,
)
