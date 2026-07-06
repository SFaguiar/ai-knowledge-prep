"""Backend MinerU — experimental para PDFs científicos/complexos (Seção 4, Etapa 8).

Não é obrigatório no MVP. Classe presente para fixar a interface e detectar
disponibilidade; a extração é ativada na Etapa 8.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class MinerUBackend(DocumentExtractionBackend):
    name = "mineru"
    supported_inputs = [".pdf"]

    def is_available(self) -> bool:
        # Versões novas expõem "mineru"; antigas, "magic_pdf".
        for module in ("mineru", "magic_pdf"):
            try:
                if importlib.util.find_spec(module) is not None:
                    return True
            except (ImportError, ValueError):
                continue
        return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        raise NotImplementedError(
            "O backend MinerU (experimental) será ativado na Etapa 8."
        )
