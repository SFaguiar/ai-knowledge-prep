"""Orquestração de "Documento para IA" (Módulo 2 — Etapas 3 e 4).

Fluxo: seleciona o backend adequado ao arquivo (registro intercambiável),
extrai o conteúdo e exporta um pacote organizado com manifest. Centraliza a
lógica consumida pela UI e pelos jobs, com mensagens de erro claras quando o
backend necessário não está disponível.
"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
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

# Pastas de sincronização em nuvem: converter direto delas pode ler um arquivo
# ainda não baixado por completo (foi o que corrompeu uma conversão real).
_CLOUD_MARKERS = (
    "proton drive", "onedrive", "google drive", "googledrive", "dropbox",
    "icloud", "nextcloud", "mega", "pcloud",
)


@dataclass
class SourceInspection:
    """Resultado da inspeção prévia de um arquivo de origem."""
    page_count: int | None = None
    warnings: list[str] = field(default_factory=list)


def _is_cloud_placeholder(path: Path) -> bool:
    """True se o arquivo é um placeholder de nuvem ainda não materializado (Windows)."""
    if not sys.platform.startswith("win"):
        return False
    offline = 0x1000
    recall_data = 0x400000
    recall_open = 0x40000
    invalid = 0xFFFFFFFF
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    except Exception:  # noqa: BLE001 - API indisponível: sem alerta
        return False
    if attrs == invalid:
        return False
    return bool(attrs & (offline | recall_data | recall_open))


def _looks_cloud_synced(path: Path) -> bool:
    lowered = str(path).lower()
    return any(marker in lowered for marker in _CLOUD_MARKERS)


def inspect_source(path: str | Path) -> SourceInspection:
    """Inspeciona a origem antes de converter: contagem de páginas e avisos de
    risco (placeholder de nuvem, PDF reparado/incompleto). Não bloqueia nada —
    apenas dá visibilidade para o usuário notar problemas como um arquivo parcial.
    """
    p = Path(path)
    warnings: list[str] = []

    if _is_cloud_placeholder(p):
        warnings.append(
            "Este arquivo parece ser um placeholder de nuvem ainda NÃO baixado "
            "por completo. Converter agora pode ler um arquivo parcial. Garanta "
            "que ele esteja 100% baixado ('sempre manter neste dispositivo') ou "
            "copie-o para uma pasta local antes."
        )
    elif _looks_cloud_synced(p):
        warnings.append(
            "Este arquivo está numa pasta de sincronização em nuvem. Confirme "
            "que ele está totalmente baixado; se a saída vier incompleta, "
            "converta a partir de uma cópia local."
        )

    page_count: int | None = None
    if SourceDocument.from_path(p).source_type == SourceType.PDF:
        try:
            import fitz

            with fitz.open(str(p)) as pdf:
                page_count = pdf.page_count
                if getattr(pdf, "is_repaired", False):
                    warnings.append(
                        "O PDF precisou ser reparado ao abrir — pode estar "
                        "corrompido ou incompleto. Confira a contagem de páginas."
                    )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Não foi possível inspecionar o PDF: {exc}")

    return SourceInspection(page_count=page_count, warnings=warnings)

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
    # Avisos da inspeção (placeholder de nuvem, PDF reparado) vão junto do
    # resultado para o usuário ver no log da conversão.
    inspection = inspect_source(path)
    if inspection.warnings:
        conversion.warnings = [*inspection.warnings, *conversion.warnings]
    report(1.0, "Concluído.")
    return conversion
