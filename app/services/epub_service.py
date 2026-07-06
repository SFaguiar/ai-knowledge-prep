"""Serviço de EPUB/e-books (Módulo 2 — Etapa 4).

EPUB deve ser extraído como estrutura HTML/texto — nunca convertido para PDF
antes, salvo pedido explícito do usuário (Seção 4). A extração usa ebooklib
para ler o pacote, percorre a espinha (ordem de leitura) e converte o HTML de
cada documento em Markdown com markdownify (com fallback para texto puro via
BeautifulSoup). Os títulos vêm do sumário (TOC) quando disponível.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.infrastructure.logging_config import get_logger
from app.models.extraction_result import ExtractionSection

logger = get_logger(__name__)


def is_available() -> bool:
    """True se as bibliotecas de EPUB (grupo opcional `docs`) estão instaladas."""
    for module in ("ebooklib", "bs4"):
        try:
            if importlib.util.find_spec(module) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def _require() -> None:
    if not is_available():
        raise RuntimeError(
            "Não foi possível ler o EPUB.\n\nPossíveis causas:\n"
            "- A biblioteca ebooklib não está instalada.\n"
            "- A biblioteca BeautifulSoup (bs4) não está instalada.\n\n"
            'Instale o grupo opcional de documentos:  pip install -e ".[docs]"'
        )


def _html_to_markdown(html: str) -> str:
    """Converte HTML de capítulo em Markdown; cai para texto puro se preciso."""
    try:
        from markdownify import markdownify

        return markdownify(html, heading_style="ATX", strip=["script", "style"]).strip()
    except Exception:  # noqa: BLE001 - markdownify ausente ou HTML problemático
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser").get_text("\n").strip()


def _first_heading(md: str) -> str | None:
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _flatten_toc(toc) -> dict[str, str]:
    """Mapeia href (sem fragmento) → título, a partir do sumário do EPUB."""
    titles: dict[str, str] = {}

    def walk(entries) -> None:
        for entry in entries:
            # Cada nó pode ser um Link, um (Section, filhos) ou uma lista.
            if isinstance(entry, (list, tuple)):
                for sub in entry:
                    if isinstance(sub, (list, tuple)):
                        walk(sub)
                    else:
                        _register(sub, titles)
            else:
                _register(entry, titles)

    walk(toc)
    return titles


def _register(node, titles: dict[str, str]) -> None:
    href = getattr(node, "href", None)
    title = getattr(node, "title", None)
    if href and title:
        key = href.split("#", 1)[0]
        titles.setdefault(key, title.strip())


def extract_metadata(epub_path: str | Path) -> dict:
    """Extrai metadados básicos (título, autor, idioma, identificador)."""
    _require()
    from ebooklib import epub

    book = epub.read_epub(str(epub_path))

    def first(field: str) -> str | None:
        data = book.get_metadata("DC", field)
        return data[0][0] if data else None

    return {
        "title": first("title"),
        "author": first("creator"),
        "language": first("language"),
        "identifier": first("identifier"),
        "publisher": first("publisher"),
    }


def extract_chapters(epub_path: str | Path) -> list[ExtractionSection]:
    """Extrai capítulos do EPUB como seções Markdown, em ordem de leitura."""
    _require()
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(str(epub_path))
    toc_titles = _flatten_toc(book.toc)

    # Ordem de leitura pela espinha; fallback para todos os documentos.
    items = []
    for entry in book.spine:
        idref = entry[0] if isinstance(entry, (list, tuple)) else entry
        item = book.get_item_with_id(idref)
        if item is not None:
            items.append(item)
    if not items:
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    sections: list[ExtractionSection] = []
    for index, item in enumerate(items, start=1):
        try:
            html = item.get_content().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        markdown = _html_to_markdown(html)
        if not markdown.strip():
            continue  # ignora páginas vazias (capa, folhas de rosto sem texto)
        name = item.get_name()
        title = toc_titles.get(name) or _first_heading(markdown) or f"Capítulo {index}"
        sections.append(
            ExtractionSection(title=title, content=markdown, source_ref=name)
        )

    logger.info("EPUB '%s': %d capítulo(s) extraído(s)",
                Path(epub_path).name, len(sections))
    return sections
