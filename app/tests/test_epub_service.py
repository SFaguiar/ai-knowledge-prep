"""Testes do serviço de EPUB (interface fixada; implementação na Etapa 4)."""

from __future__ import annotations

import pytest

from app.services import epub_service


def test_is_available_returns_bool() -> None:
    assert isinstance(epub_service.is_available(), bool)


def test_extract_chapters_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="Etapa 4"):
        epub_service.extract_chapters("livro.epub")


def test_extract_metadata_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="Etapa 4"):
        epub_service.extract_metadata("livro.epub")
