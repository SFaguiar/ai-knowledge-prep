"""Backend PyMuPDF4LLM — rápido para PDFs com texto nativo (Seção 4).

Saída Markdown ideal para o "modo rápido". Fica disponível apenas se o pacote
`pymupdf4llm` estiver instalado (grupo opcional `docs`).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions, OutputFormat
from app.models.extraction_result import ExtractionResult, ExtractionSection
from app.services.markdown_service import markdown_to_plain

# Blocos que o pymupdf4llm emite com o texto extraído de dentro de imagens.
# Em PDFs de slides isso vira ruído (fragmentos embaralhados de decoração).
_PICTURE_TEXT = re.compile(
    r"(<!--|-{2,}) Start of picture text.*?End of picture text (-->|-{2,})\s*",
    re.DOTALL,
)


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

        # page_chunks permite rastreabilidade por página. Quando o usuário quer
        # reduzir ruído (padrão), desligamos o OCR automático de imagens
        # (use_ocr=False) — no pymupdf4llm 1.28 ele vem LIGADO e OCRiza gráficos
        # decorativos de slides, gerando fragmentos embaralhados. O texto nativo
        # do PDF é preservado; os blocos "picture text" residuais são removidos
        # em seguida por _strip_picture_text.
        kwargs: dict = {"page_chunks": True}
        if options.reduce_image_noise:
            kwargs["use_ocr"] = False
        try:
            chunks = pymupdf4llm.to_markdown(str(file_path), **kwargs)
        except TypeError:
            # Versão antiga do pymupdf4llm sem esses parâmetros: degrada para o básico.
            chunks = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)

        sections: list[ExtractionSection] = []
        parts: list[str] = []
        for chunk in chunks:
            text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            if options.reduce_image_noise:
                text = _PICTURE_TEXT.sub("", text)
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
