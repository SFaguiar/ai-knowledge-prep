"""Perfil de exportação — como preparar a saída para um destino específico.

Dados puros, sem dependência de UI ou serviços. Consumido pelos presets
(Seção 8) e pelos módulos de exportação (Etapas 3–7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.extraction_options import OutputFormat


@dataclass(frozen=True)
class ExportProfile:
    key: str
    name: str
    description: str
    output_format: OutputFormat = OutputFormat.MARKDOWN
    # 0 = não dividir por tamanho.
    split_max_chars: int = 0
    one_file_per_chapter: bool = False
    preserve_titles: bool = True
    strip_repeated_headers: bool = False
    include_index: bool = False
    images_subfolder: bool = False
    relative_links: bool = False
    yaml_frontmatter: bool = False
    write_manifest: bool = True
    # Específico de transcrição.
    include_timestamps: bool = False
    segments_json: bool = False
    extra: dict = field(default_factory=dict)
