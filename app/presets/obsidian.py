"""Preset Obsidian — um arquivo por capítulo, imagens em subpasta (Seção 8)."""

from __future__ import annotations

from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat

OBSIDIAN = ExportProfile(
    key="obsidian",
    name="Obsidian",
    description="Um arquivo por capítulo, imagens em subpasta, links relativos.",
    output_format=OutputFormat.MARKDOWN,
    one_file_per_chapter=True,
    preserve_titles=True,
    images_subfolder=True,
    relative_links=True,
    yaml_frontmatter=True,
    write_manifest=True,
)
