"""Serviço de EPUB/e-books (Módulo 2 — Etapa 4).

EPUB deve ser extraído como estrutura HTML/texto — nunca convertido para PDF
antes, salvo pedido explícito do usuário (Seção 4). Implementação na Etapa 4
com ebooklib + BeautifulSoup + markdownify, e Calibre CLI como fallback para
formatos de e-book mais amplos. A interface está fixada desde já.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models.extraction_result import ExtractionSection


def is_available() -> bool:
    """True se as bibliotecas de EPUB (grupo opcional `docs`) estão instaladas."""
    for module in ("ebooklib", "bs4"):
        try:
            if importlib.util.find_spec(module) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def extract_chapters(epub_path: str | Path) -> list[ExtractionSection]:
    """(Etapa 4) Extrai capítulos do EPUB como seções Markdown/texto."""
    raise NotImplementedError(
        "A extração de EPUB será implementada na Etapa 4 "
        "(ebooklib + BeautifulSoup + markdownify)."
    )


def extract_metadata(epub_path: str | Path) -> dict:
    """(Etapa 4) Extrai metadados (título, autor, idioma, sumário) do EPUB."""
    raise NotImplementedError(
        "A extração de metadados de EPUB será implementada na Etapa 4."
    )
