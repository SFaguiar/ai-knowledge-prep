"""Testes das utilidades de Markdown/texto (Etapas 3–7)."""

from __future__ import annotations

from app.services import markdown_service


def test_markdown_to_plain_strips_syntax() -> None:
    md = ("# Título\n\nTexto **negrito** e *itálico* com `código` "
          "e [link](http://exemplo) e ![alt](img.png).")
    plain = markdown_service.markdown_to_plain(md)
    assert "#" not in plain
    assert "**" not in plain
    assert "`" not in plain
    assert "http://exemplo" not in plain
    for word in ("Título", "negrito", "itálico", "código", "link", "alt"):
        assert word in plain


def test_split_noop_when_small_or_disabled() -> None:
    assert markdown_service.split_by_max_chars("abc", 0) == ["abc"]
    assert markdown_service.split_by_max_chars("abc", 100) == ["abc"]


def test_split_respects_max_and_paragraphs() -> None:
    paragraphs = [f"Parágrafo {i} " + "x" * 50 for i in range(20)]
    text = "\n\n".join(paragraphs)
    parts = markdown_service.split_by_max_chars(text, 200)
    assert len(parts) > 1
    assert all(len(p) <= 200 for p in parts)
    # Nenhum parágrafo foi quebrado no meio: a junção reconstrói o original.
    assert "\n\n".join(parts) == text


def test_split_hard_splits_giant_paragraph() -> None:
    text = "a" * 500
    parts = markdown_service.split_by_max_chars(text, 200)
    assert all(len(p) <= 200 for p in parts)
    assert "".join(parts) == text


def test_build_index() -> None:
    index = markdown_service.build_index(
        [("Parte 001", "partes/parte_001.md"), ("Parte 002", "partes/parte_002.md")]
    )
    assert index.startswith("# Índice")
    assert "- [Parte 001](partes/parte_001.md)" in index


def test_slugify() -> None:
    assert markdown_service.slugify("Introdução à IA!") == "introducao_a_ia"
    assert markdown_service.slugify("  ") == "documento"
