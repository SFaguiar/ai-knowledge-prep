"""Exportação organizada em pastas com manifest (Módulos 2 e 5).

Versão mínima, usada a partir da Etapa 3: escreve o arquivo completo
(`fonte_completa.md`/`.txt`), divide em `partes/parte_NNN` quando o perfil
pede, gera índice e manifest.json (Seções 6 e 9). Recursos mais ricos dos
presets (imagens, frontmatter, um arquivo por capítulo) entram nas Etapas 4–7.
"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.logging_config import get_logger
from app.models.conversion_result import ConversionResult
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.services import manifest_service, markdown_service

logger = get_logger(__name__)


def export_text_package(
    project_name: str,
    content: str,
    output_dir: str | Path,
    profile: ExportProfile,
    source_entry: manifest_service.SourceFileEntry | None = None,
) -> ConversionResult:
    """Escreve um pacote textual organizado conforme o perfil de exportação."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    is_markdown = profile.output_format != OutputFormat.TXT
    ext = ".md" if is_markdown else ".txt"
    out_type = "markdown" if is_markdown else "txt"
    if not is_markdown:
        content = markdown_service.markdown_to_plain(content)

    outputs: list[Path] = []
    manifest_outputs: list[manifest_service.OutputEntry] = []

    main_file = out_dir / f"fonte_completa{ext}"
    main_file.write_text(content, encoding="utf-8")
    outputs.append(main_file)
    manifest_outputs.append(
        manifest_service.OutputEntry(file=main_file.name, type=out_type)
    )

    index_entries: list[tuple[str, str]] = [("Fonte completa", main_file.name)]

    parts = markdown_service.split_by_max_chars(content, profile.split_max_chars)
    if profile.split_max_chars > 0 and len(parts) > 1:
        parts_dir = out_dir / "partes"
        parts_dir.mkdir(exist_ok=True)
        for i, part in enumerate(parts, start=1):
            part_file = parts_dir / f"parte_{i:03d}{ext}"
            part_file.write_text(part, encoding="utf-8")
            outputs.append(part_file)
            rel = f"partes/{part_file.name}"
            manifest_outputs.append(
                manifest_service.OutputEntry(file=rel, type=out_type)
            )
            index_entries.append((f"Parte {i:03d}", rel))

    if profile.include_index and is_markdown:
        index_file = out_dir / "indice.md"
        index_file.write_text(
            markdown_service.build_index(index_entries), encoding="utf-8"
        )
        outputs.append(index_file)
        manifest_outputs.append(
            manifest_service.OutputEntry(file=index_file.name, type="markdown")
        )

    manifest_path: Path | None = None
    if profile.write_manifest:
        manifest = manifest_service.build_manifest(
            project_name=project_name,
            source_files=[source_entry] if source_entry else [],
            outputs=manifest_outputs,
        )
        manifest_path = manifest_service.write_manifest(manifest, out_dir)

    logger.info("Pacote '%s' exportado em %s (%d arquivos)",
                project_name, out_dir, len(outputs))
    return ConversionResult(
        success=True,
        output_files=outputs,
        manifest_path=manifest_path,
        message=f"{len(outputs)} arquivo(s) gerado(s).",
    )
