"""Orquestração de "Documento para IA" (Módulo 2 — Etapas 3 e 4).

Fluxo: seleciona o backend adequado ao arquivo (registro intercambiável),
extrai o conteúdo e exporta um pacote organizado com manifest. Centraliza a
lógica consumida pela UI e pelos jobs, com mensagens de erro claras quando o
backend necessário não está disponível.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from app.backends.documents.base import (
    BackendRegistry,
    DocumentExtractionBackend,
    build_default_registry,
)
from app.infrastructure.logging_config import get_logger
from app.models.conversion_result import ConversionResult
from app.models.export_profile import ExportProfile
from app.models.extraction_options import ExtractionOptions, OutputFormat
from app.models.source_document import SourceDocument, SourceType
from app.presets.base import ExportPreset
from app.services import export_service, manifest_service

logger = get_logger(__name__)

# Perfil padrão quando o usuário não escolhe um preset: arquivo único + manifest.
DEFAULT_PROFILE = ExportPreset(
    key="default",
    name="Padrão (arquivo único)",
    description="Um único arquivo Markdown/TXT, com manifest.",
    output_format=OutputFormat.MARKDOWN,
    write_manifest=True,
)

SUPPORTED_SUFFIXES = (".pdf", ".epub")


def select_backend(
    file_path: str | Path, registry: BackendRegistry | None = None
) -> DocumentExtractionBackend | None:
    registry = registry or build_default_registry()
    return registry.select_auto(Path(file_path))


def _missing_backend_error(path: Path) -> RuntimeError:
    suffix = path.suffix.lower()
    if suffix == ".epub":
        return RuntimeError(
            "Não foi possível preparar este EPUB.\n\nPossíveis causas:\n"
            "- A biblioteca ebooklib não está instalada.\n"
            "- A biblioteca BeautifulSoup (bs4) não está instalada.\n\n"
            'Instale o grupo opcional de documentos:  pip install -e ".[docs]"'
        )
    if suffix == ".pdf":
        return RuntimeError(
            "Não foi possível preparar este PDF: nenhum backend de extração "
            "disponível (PyMuPDF é obrigatório)."
        )
    return RuntimeError(
        f"Formato não suportado nesta etapa: {suffix or 'desconhecido'}.\n"
        "Formatos aceitos: PDF e EPUB."
    )


def _source_entry(path: Path, doc: SourceDocument,
                  backend: DocumentExtractionBackend) -> manifest_service.SourceFileEntry:
    entry = manifest_service.SourceFileEntry(
        file=path.name,
        type=doc.source_type.value,
        extraction_backend=backend.name,
    )
    if doc.source_type == SourceType.PDF:
        try:
            import fitz

            with fitz.open(str(path)) as pdf:
                entry.pages_total = pdf.page_count
        except Exception:  # noqa: BLE001 - contagem é só rastreabilidade
            pass
    return entry


def convert_document(
    source_path: str | Path,
    output_dir: str | Path,
    profile: ExportProfile | None = None,
    output_format: OutputFormat | None = None,
    registry: BackendRegistry | None = None,
    progress: Callable[[float, str], None] | None = None,
) -> ConversionResult:
    """Extrai um PDF/EPUB e exporta um pacote organizado no `output_dir`.

    `profile` define a organização da saída (divisão, capítulos, índice);
    `output_format` sobrepõe o formato do perfil quando informado.
    """
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    doc = SourceDocument.from_path(path)
    profile = profile or DEFAULT_PROFILE
    if output_format is not None:
        profile = replace(profile, output_format=output_format)

    def report(fraction: float, message: str) -> None:
        if progress is not None:
            progress(fraction, message)

    report(0.05, "Selecionando backend...")
    backend = select_backend(path, registry)
    if backend is None:
        raise _missing_backend_error(path)

    report(-1, f"Extraindo conteúdo ({backend.name})...")
    options = ExtractionOptions(
        output_format=profile.output_format,
        max_chars_per_part=profile.split_max_chars,
        split_by_chapter=profile.one_file_per_chapter,
        strip_repeated_headers=profile.strip_repeated_headers,
    )
    result = backend.extract(path, options)

    report(0.8, "Gravando pacote...")
    conversion = export_service.export_extraction_package(
        project_name=path.stem,
        result=result,
        output_dir=output_dir,
        profile=profile,
        source_entry=_source_entry(path, doc, backend),
    )
    report(1.0, "Concluído.")
    return conversion
