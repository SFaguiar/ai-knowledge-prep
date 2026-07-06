"""Jobs de background do Módulo 1 — PDF Cleaner.

As edições em memória (remover/girar/reordenar) são instantâneas e ficam na UI.
A escrita em disco (salvar, dividir) é feita aqui, fora da thread da interface,
gerando também log e manifest.json para rastreabilidade (Seções 9 e 11).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from app.jobs.job_model import Job
from app.services import manifest_service, pdf_service
from app.services.pdf_service import PdfDocumentModel


class SavePdfJob(Job):
    """Salva o modelo editado como um novo PDF e escreve o manifest."""

    job_type = "SavePdfJob"

    def __init__(self, model: PdfDocumentModel, output_path: str | Path,
                 overwrite: bool = False) -> None:
        super().__init__(title="Salvar PDF")
        # Cópia defensiva: o job roda em outra thread; evita edição concorrente.
        self.model = copy.deepcopy(model)
        self.output_path = Path(output_path)
        self.overwrite = overwrite

    def run(self) -> dict[str, Any]:
        self.report(0.05, "Preparando páginas...")
        self.check_cancelled()

        saved = pdf_service.save_pdf(self.model, self.output_path, overwrite=self.overwrite)
        self.report(0.7, "PDF gravado. Gerando manifesto...")

        # Rastreabilidade: páginas removidas em relação à origem primária.
        primary = self.model.primary_path
        kept_indices = {
            p.source_index for p in self.model.pages
            if p.source_path.resolve() == primary.resolve()
        }
        removed = sorted(set(range(self.model.original_page_count)) - kept_indices)

        source_entry = manifest_service.SourceFileEntry(
            file=primary.name,
            type="pdf",
            pages_total=self.model.original_page_count,
            pages_included=f"{len(self.model.pages)} páginas mantidas",
            pages_removed=[i + 1 for i in removed],  # 1-based para leitura humana
        )
        output_entry = manifest_service.OutputEntry(file=saved.name, type="pdf")
        manifest = manifest_service.build_manifest(
            project_name=saved.stem,
            source_files=[source_entry],
            outputs=[output_entry],
        )
        manifest_path = manifest_service.write_manifest(manifest, saved.parent)

        self.report(1.0, "Concluído.")
        return {"output": saved, "manifest": manifest_path, "pages_removed": removed}


class SplitPdfJob(Job):
    """Divide um PDF em vários arquivos por intervalos (1-based, inclusivos)."""

    job_type = "SplitPdfJob"

    def __init__(self, source_path: str | Path, ranges: list[tuple[int, int]],
                 output_dir: str | Path) -> None:
        super().__init__(title="Dividir PDF")
        self.source_path = Path(source_path)
        self.ranges = ranges
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        self.report(-1, "Dividindo PDF...")
        outputs = pdf_service.split_pdf(self.source_path, self.ranges, self.output_dir)
        self.report(1.0, f"{len(outputs)} arquivos gerados.")
        return {"outputs": outputs}
