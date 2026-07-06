"""Testes do serviço de EPUB (Etapa 4).

Constroem um EPUB mínimo com ebooklib e verificam extração de capítulos e
metadados. Os testes são pulados quando as bibliotecas do grupo `docs` não
estão instaladas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import epub_service


@pytest.fixture
def sample_epub(tmp_path: Path) -> Path:
    pytest.importorskip("ebooklib")
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("id-123")
    book.set_title("Livro de Teste")
    book.set_language("pt")
    book.add_author("Autora Exemplo")

    c1 = epub.EpubHtml(title="Introdução", file_name="c1.xhtml", lang="pt")
    c1.content = "<h1>Introdução</h1><p>Primeiro capítulo do livro.</p>"
    c2 = epub.EpubHtml(title="Capítulo Dois", file_name="c2.xhtml", lang="pt")
    c2.content = "<h1>Capítulo Dois</h1><p>Segundo capítulo, com <b>negrito</b>.</p>"

    book.add_item(c1)
    book.add_item(c2)
    book.toc = (c1, c2)
    book.spine = [c1, c2]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    out = tmp_path / "livro.epub"
    epub.write_epub(str(out), book)
    return out


def test_is_available_returns_bool() -> None:
    assert isinstance(epub_service.is_available(), bool)


def test_extract_metadata(sample_epub: Path) -> None:
    meta = epub_service.extract_metadata(sample_epub)
    assert meta["title"] == "Livro de Teste"
    assert meta["author"] == "Autora Exemplo"
    assert meta["language"] == "pt"


def test_extract_chapters_in_order(sample_epub: Path) -> None:
    chapters = epub_service.extract_chapters(sample_epub)
    # Pode incluir nav; garantimos que os dois capítulos de conteúdo estão lá,
    # em ordem de leitura, com títulos do TOC.
    titles = [c.title for c in chapters]
    assert "Introdução" in titles
    assert "Capítulo Dois" in titles
    assert titles.index("Introdução") < titles.index("Capítulo Dois")
    intro = next(c for c in chapters if c.title == "Introdução")
    assert "Primeiro capítulo" in intro.content
    assert intro.source_ref  # rastreabilidade (nome do item no EPUB)
