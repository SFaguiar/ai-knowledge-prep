"""Jobs de background do Módulo 2 — Documento para IA (Etapas 3 e 4).

Cobre os papéis de PdfToMarkdownJob e EpubToMarkdownJob (Seção 11): a extração
e a exportação rodam fora da thread da UI, reportando progresso e devolvendo o
`ConversionResult`. O backend é escolhido automaticamente pelo tipo de arquivo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.jobs.job_model import Job
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.services import document_prep_service


class ExtractDocumentJob(Job):
    """Extrai um PDF/EPUB para Markdown/TXT e exporta um pacote organizado."""

    job_type = "ExtractDocumentJob"

    def __init__(self, source_path: str | Path, output_dir: str | Path,
                 profile: ExportProfile | None = None,
                 output_format: OutputFormat | None = None) -> None:
        super().__init__(title="Preparar documento para IA")
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.profile = profile
        self.output_format = output_format

    def run(self) -> dict[str, Any]:
        def on_progress(fraction: float, message: str) -> None:
            self.check_cancelled()
            self.report(fraction, message)

        conversion = document_prep_service.convert_document(
            source_path=self.source_path,
            output_dir=self.output_dir,
            profile=self.profile,
            output_format=self.output_format,
            progress=on_progress,
        )
        return {"conversion": conversion}
