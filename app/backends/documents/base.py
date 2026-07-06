"""Interface comum para backends de extração documental (Seção 5).

Motores de conversão são intercambiáveis. Cada backend declara os tipos de
entrada suportados, se está disponível no ambiente e se consegue lidar com um
arquivo específico, além de implementar a extração de fato.

O `registry` permite seleção automática (MVP) e prepara a seleção manual futura.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class DocumentExtractionBackend(ABC):
    #: Nome estável do backend, ex.: "pymupdf4llm".
    name: str = "base"
    #: Extensões suportadas (minúsculas, com ponto), ex.: [".pdf"].
    supported_inputs: list[str] = []

    @abstractmethod
    def is_available(self) -> bool:
        """True se as dependências necessárias estão instaladas."""
        raise NotImplementedError

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_inputs

    @abstractmethod
    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        raise NotImplementedError


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: list[DocumentExtractionBackend] = []

    def register(self, backend: DocumentExtractionBackend) -> None:
        self._backends.append(backend)

    def all(self) -> list[DocumentExtractionBackend]:
        return list(self._backends)

    def available(self) -> list[DocumentExtractionBackend]:
        return [b for b in self._backends if b.is_available()]

    def get(self, name: str) -> DocumentExtractionBackend | None:
        return next((b for b in self._backends if b.name == name), None)

    def select_auto(self, file_path: Path) -> DocumentExtractionBackend | None:
        """Seleção automática simples (MVP): primeiro backend disponível que
        consegue lidar com o arquivo, respeitando a ordem de registro
        (ordenada por preferência para cada tipo)."""
        for backend in self._backends:
            if backend.is_available() and backend.can_handle(file_path):
                return backend
        return None


def build_default_registry() -> BackendRegistry:
    """Monta o registro na ordem de preferência do MVP.

    Ordem de preferência para PDF: PyMuPDF4LLM (rápido) → outros quando
    implementados. Backends ausentes simplesmente reportam is_available()=False.
    """
    from app.backends.documents.pymupdf4llm_backend import PyMuPDF4LLMBackend

    registry = BackendRegistry()
    registry.register(PyMuPDF4LLMBackend())
    # Etapa 8: registrar aqui, na ordem de preferência, os backends já
    # esboçados neste pacote (DoclingBackend, MarkItDownBackend,
    # MarkerBackend, MinerUBackend) quando a extração deles for ativada.
    return registry
