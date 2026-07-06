"""Backend Marker — alta qualidade para PDF → Markdown/JSON (Seção 4, Etapa 8).

Opcional: bom para tabelas, fórmulas e layouts complexos. Classe presente para
fixar a interface e detectar disponibilidade; a extração é ativada na Etapa 8.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class MarkerBackend(DocumentExtractionBackend):
    name = "marker"
    supported_inputs = [".pdf"]

    def is_available(self) -> bool:
        # O pacote PyPI chama-se marker-pdf; o módulo importável é "marker".
        try:
            return importlib.util.find_spec("marker") is not None
        except (ImportError, ValueError):
            return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        raise NotImplementedError(
            "O backend Marker (opcional) será ativado na Etapa 8."
        )
