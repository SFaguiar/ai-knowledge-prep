"""Backend Docling — parsing documental estruturado (Seção 4, Etapa 8).

Backend principal planejado para o "modo equilibrado": PDF, DOCX, PPTX, HTML e
imagens com foco em documentos para IA. Neste MVP a classe existe para fixar a
interface e permitir detecção de disponibilidade; a extração é ativada na
Etapa 8, quando o backend passa a ser registrado em `build_default_registry`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult


class DoclingBackend(DocumentExtractionBackend):
    name = "docling"
    supported_inputs = [".pdf", ".docx", ".pptx", ".html", ".htm",
                        ".png", ".jpg", ".jpeg", ".tiff"]

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("docling") is not None
        except (ImportError, ValueError):
            return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        raise NotImplementedError(
            "O backend Docling será ativado na Etapa 8. "
            "Para PDFs com texto nativo, use o backend PyMuPDF4LLM."
        )
