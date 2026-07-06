"""Backend PyMuPDF (fitz) — extração básica de texto de PDF (Seção 4).

Fallback SEMPRE disponível: PyMuPDF é dependência obrigatória do app, então
este backend garante que "PDF → Markdown/TXT" funcione com a instalação mínima,
sem exigir o pacote opcional `pymupdf4llm`. A saída é texto puro por página
(sem detecção rica de estrutura); quando `pymupdf4llm` está instalado, o
registro o prefere para um Markdown mais estruturado.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult, ExtractionSection


class PyMuPDFBackend(DocumentExtractionBackend):
    name = "pymupdf"
    supported_inputs = [".pdf"]

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("fitz") is not None
        except (ImportError, ValueError):
            return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        import fitz  # PyMuPDF — import tardio

        sections: list[ExtractionSection] = []
        parts: list[str] = []
        with fitz.open(str(file_path)) as doc:
            for i, page in enumerate(doc, start=1):
                text = (page.get_text("text") or "").strip()
                parts.append(text)
                sections.append(
                    ExtractionSection(title=f"Página {i}", content=text, source_ref=str(i))
                )

        full_text = "\n\n".join(p for p in parts if p)
        return ExtractionResult(
            backend_name=self.name,
            full_text=full_text,
            sections=sections,
            metadata={"pages": len(sections)},
            warnings=[
                "Extração básica de texto (sem estrutura rica). Instale "
                "'pymupdf4llm' para Markdown mais estruturado."
            ],
        )
