"""Backend PyMuPDF4LLM — rápido para PDFs com texto nativo (Seção 4).

Saída Markdown ideal para o "modo rápido". Fica disponível apenas se o pacote
`pymupdf4llm` estiver instalado (grupo opcional `docs`).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions, OutputFormat
from app.models.extraction_result import ExtractionResult, ExtractionSection
from app.services.markdown_service import markdown_to_plain


class PyMuPDF4LLMBackend(DocumentExtractionBackend):
    name = "pymupdf4llm"
    supported_inputs = [".pdf"]

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("pymupdf4llm") is not None
        except (ImportError, ValueError):
            return False

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        import pymupdf4llm  # import tardio — só quando realmente usado

        # to_markdown retorna Markdown; page_chunks permite rastreabilidade por página.
        chunks = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)

        sections: list[ExtractionSection] = []
        parts: list[str] = []
        for chunk in chunks:
            text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            page_no = (
                chunk.get("metadata", {}).get("page")
                if isinstance(chunk, dict)
                else None
            )
            ref = str(page_no) if page_no is not None else ""
            parts.append(text)
            sections.append(
                ExtractionSection(title=f"Página {ref}" if ref else "", content=text,
                                  source_ref=ref)
            )

        full_md = "\n\n".join(p.strip() for p in parts if p.strip())
        full_text = full_md
        if options.output_format == OutputFormat.TXT:
            full_text = markdown_to_plain(full_md)

        return ExtractionResult(
            backend_name=self.name,
            full_text=full_text,
            sections=sections,
            metadata={"pages": len(sections)},
        )
