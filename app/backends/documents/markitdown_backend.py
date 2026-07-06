"""Backend MarkItDown — conversor leve e genérico para Markdown (Seção 4, Etapa 8).

Útil para DOCX, PPTX, HTML e PDFs simples. Não deve ser o único motor para
PDFs complexos. Classe presente para fixar a interface e detectar
disponibilidade; a extração é ativada na Etapa 8.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class MarkItDownBackend(DocumentExtractionBackend):
    name = "markitdown"
    supported_inputs = [".docx", ".pptx", ".xlsx", ".html", ".htm", ".csv", ".pdf"]

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("markitdown") is not None
        except (ImportError, ValueError):
            return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        raise NotImplementedError(
            "O backend MarkItDown será ativado na Etapa 8."
        )
