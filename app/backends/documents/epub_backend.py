"""Backend EPUB — adapta o epub_service à interface de backends (Etapa 4).

Faz o EPUB seguir o mesmo fluxo intercambiável dos backends de PDF: seleção
automática pelo registro, extração por capítulos (seções) e exportação
organizada. A disponibilidade depende do grupo opcional `docs` (ebooklib + bs4).
"""

from __future__ import annotations

from pathlib import Path

from app.backends.documents.base import DocumentExtractionBackend
from app.models.extraction_options import ExtractionOptions
from app.models.extraction_result import ExtractionResult
from app.services import epub_service


class EpubBackend(DocumentExtractionBackend):
    name = "epub"
    supported_inputs = [".epub"]

    def is_available(self) -> bool:
        return epub_service.is_available()

    def extract(self, file_path: Path, options: ExtractionOptions) -> ExtractionResult:
        sections = epub_service.extract_chapters(file_path)
        metadata = epub_service.extract_metadata(file_path)

        # O texto completo (em Markdown) concatena os capítulos com seus títulos;
        # a camada de exportação decide formato final e divisão por capítulo.
        blocks: list[str] = []
        for section in sections:
            body = section.content.strip()
            if section.title and not body.lstrip().startswith("#"):
                body = f"# {section.title}\n\n{body}"
            blocks.append(body)

        return ExtractionResult(
            backend_name=self.name,
            full_text="\n\n".join(blocks),
            sections=sections,
            metadata={
                "chapters": len(sections),
                **{k: v for k, v in metadata.items() if v},
            },
        )
