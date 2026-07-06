"""Testes da seleção de backend documental (Seção 5)."""

from __future__ import annotations

from pathlib import Path

from app.backends.documents.base import (
    BackendRegistry,
    DocumentExtractionBackend,
    build_default_registry,
)
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class _FakeBackend(DocumentExtractionBackend):
    name = "fake"
    supported_inputs = [".pdf"]

    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        return ExtractionResult(backend_name=self.name, full_text="ok")


def test_select_auto_skips_unavailable() -> None:
    registry = BackendRegistry()
    registry.register(_FakeBackend(available=False))
    available_backend = _FakeBackend(available=True)
    available_backend.name = "fake2"
    registry.register(available_backend)

    chosen = registry.select_auto(Path("doc.pdf"))
    assert chosen is available_backend


def test_select_auto_returns_none_for_unsupported() -> None:
    registry = BackendRegistry()
    registry.register(_FakeBackend(available=True))
    assert registry.select_auto(Path("audio.mp3")) is None


def test_default_registry_has_pymupdf4llm() -> None:
    registry = build_default_registry()
    assert registry.get("pymupdf4llm") is not None


def test_optional_backend_stubs_probe_availability() -> None:
    """Backends das Etapas 6/8 existem, detectam disponibilidade e declaram entradas."""
    from app.backends.documents.docling_backend import DoclingBackend
    from app.backends.documents.marker_backend import MarkerBackend
    from app.backends.documents.markitdown_backend import MarkItDownBackend
    from app.backends.documents.mineru_backend import MinerUBackend

    for backend_cls in (DoclingBackend, MarkItDownBackend, MarkerBackend, MinerUBackend):
        backend = backend_cls()
        assert isinstance(backend.is_available(), bool)
        assert backend.supported_inputs
        assert backend.can_handle(Path("arquivo.pdf")) in (True, False)
