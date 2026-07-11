"""Opções de extração documental compartilhadas entre backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OutputFormat(StrEnum):
    MARKDOWN = "markdown"
    TXT = "txt"
    JSON = "json"


@dataclass
class ExtractionOptions:
    output_format: OutputFormat = OutputFormat.MARKDOWN
    # Divisão por tamanho máximo de caracteres (0 = não dividir).
    max_chars_per_part: int = 0
    # Preservar títulos/listas/tabelas quando o backend suportar.
    preserve_structure: bool = True
    # Extrair imagens embutidas para uma subpasta.
    extract_images: bool = False
    # Remover cabeçalhos/rodapés repetidos quando possível.
    strip_repeated_headers: bool = False
    # Idioma dominante (dica para alguns backends), ISO simples.
    language: str = "pt"
    # Um arquivo por capítulo/seção quando aplicável (EPUB, etc.).
    split_by_chapter: bool = False
    # Suprimir o texto extraído de dentro de imagens/gráficos (ruído comum em
    # PDFs de slides: fragmentos embaralhados, blocos "picture text"). Ligado por
    # padrão porque quase sempre o objetivo é prosa limpa para IA. O conteúdo
    # visual de diagramas/mapas mentais não é recuperado — isso é papel do OCR.
    reduce_image_noise: bool = True
