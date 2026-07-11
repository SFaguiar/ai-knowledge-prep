"""Job de background do Módulo 3 — OCR (Etapa 5).

Gera um PDF pesquisável a partir de um PDF escaneado (ou imagem) e exporta o
texto reconhecido como pacote organizado (Markdown/TXT + manifest),
reaproveitando a infraestrutura de exportação do Módulo 2 (Seção 11).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from app.jobs.job_model import Job
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.models.source_document import SourceDocument
from app.services import export_service, manifest_service, ocr_service

# Perfil padrão quando o usuário não escolhe um preset: arquivo único + manifest.
DEFAULT_PROFILE = ExportProfile(
    key="ocr_default",
    name="Padrão (arquivo único)",
    description="PDF pesquisável + um único arquivo Markdown/TXT, com manifest.",
    output_format=OutputFormat.MARKDOWN,
    write_manifest=True,
)


class ApplyOcrJob(Job):
    """Aplica OCR a um PDF/imagem e exporta o texto reconhecido."""

    job_type = "ApplyOcrJob"

    def __init__(self, source_path: str | Path, output_dir: str | Path,
                 language: str = ocr_service.DEFAULT_LANGUAGE,
                 deskew: bool = True, rotate_pages: bool = True,
                 force_ocr: bool = False,
                 profile: ExportProfile | None = None,
                 output_format: OutputFormat | None = None) -> None:
        super().__init__(title="Aplicar OCR")
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.language = language
        self.deskew = deskew
        self.rotate_pages = rotate_pages
        self.force_ocr = force_ocr
        self.profile = profile or DEFAULT_PROFILE
        if output_format is not None:
            self.profile = replace(self.profile, output_format=output_format)

    def run(self) -> dict[str, Any]:
        self.report(-1, f"Aplicando OCR ({self.language})...")
        self.check_cancelled()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        searchable_pdf = self.output_dir / f"{self.source_path.stem}_pesquisavel.pdf"
        ocr_service.apply_ocr(
            self.source_path, searchable_pdf,
            language=self.language, deskew=self.deskew,
            rotate_pages=self.rotate_pages, force_ocr=self.force_ocr,
        )
        self.check_cancelled()

        self.report(0.7, "Extraindo texto reconhecido...")
        result = ocr_service.extract_text(searchable_pdf)

        self.report(0.85, "Gravando pacote...")
        doc = SourceDocument.from_path(self.source_path)
        source_entry = manifest_service.SourceFileEntry(
            file=self.source_path.name,
            type=doc.source_type.value,
            ocr_applied=True,
            extraction_backend="ocrmypdf",
        )
        conversion = export_service.export_extraction_package(
            project_name=self.source_path.stem,
            result=result,
            output_dir=self.output_dir,
            profile=self.profile,
            source_entry=source_entry,
            extra_outputs=[(searchable_pdf, "pdf")],
        )
        self.report(1.0, "Concluído.")
        return {"conversion": conversion, "searchable_pdf": searchable_pdf}
