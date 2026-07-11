"""Exportação organizada em pastas com manifest (Módulos 2 e 5).

Escreve o arquivo completo (`fonte_completa.md`/`.txt`) e, conforme o perfil:
um arquivo por capítulo (`capitulos/NN_slug`), divisão por tamanho
(`partes/parte_NNN`), índice Markdown e `manifest.json` (Seções 6 e 9).
"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.logging_config import get_logger
from app.models.conversion_result import ConversionResult
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.models.extraction_result import ExtractionResult, ExtractionSection
from app.services import manifest_service, markdown_service

logger = get_logger(__name__)


def _render_section(section: ExtractionSection, is_markdown: bool,
                    preserve_titles: bool) -> str:
    """Renderiza uma seção no formato de saída, prefixando o título quando útil."""
    body = section.content.strip()
    if is_markdown and preserve_titles and section.title \
            and not body.lstrip().startswith("#"):
        body = f"# {section.title}\n\n{body}"
    return body if is_markdown else markdown_service.markdown_to_plain(body)


def export_extraction_package(
    project_name: str,
    result: ExtractionResult,
    output_dir: str | Path,
    profile: ExportProfile,
    source_entry: manifest_service.SourceFileEntry | None = None,
    extra_outputs: list[tuple[Path, str]] | None = None,
) -> ConversionResult:
    """Exporta um `ExtractionResult` (com seções) como pacote organizado.

    Estratégia de saída, por ordem de prioridade do perfil:
    - `one_file_per_chapter`: um arquivo por seção em `capitulos/`;
    - `split_max_chars > 0`: divisão do texto completo em `partes/`;
    - caso contrário: apenas o arquivo completo.
    Sempre grava `fonte_completa`, e opcionalmente índice e manifest.

    `extra_outputs` registra arquivos já gravados fora desta função (ex.: o
    PDF pesquisável gerado pelo OCR) como pares (caminho, tipo) — entram no
    manifest e no `ConversionResult` junto com os demais, sem serem escritos
    de novo aqui.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    is_markdown = profile.output_format != OutputFormat.TXT
    ext = ".md" if is_markdown else ".txt"
    out_type = "markdown" if is_markdown else "txt"

    sections = result.sections or [
        ExtractionSection(title="", content=result.full_text)
    ]
    sections = [s for s in sections if s.content.strip()]
    if not sections:
        raise ValueError("O documento não produziu conteúdo textual para exportar.")

    rendered = [_render_section(s, is_markdown, profile.preserve_titles) for s in sections]
    full_content = "\n\n".join(rendered)

    outputs: list[Path] = []
    manifest_outputs: list[manifest_service.OutputEntry] = []

    for extra_path, extra_type in extra_outputs or []:
        outputs.append(extra_path)
        try:
            rel = extra_path.relative_to(out_dir)
        except ValueError:
            rel = extra_path.name
        manifest_outputs.append(manifest_service.OutputEntry(file=str(rel), type=extra_type))

    main_file = out_dir / f"fonte_completa{ext}"
    main_file.write_text(full_content, encoding="utf-8")
    outputs.append(main_file)
    manifest_outputs.append(manifest_service.OutputEntry(file=main_file.name, type=out_type))
    index_entries: list[tuple[str, str]] = [("Fonte completa", main_file.name)]

    if profile.one_file_per_chapter and len(sections) > 1:
        chapters_dir = out_dir / "capitulos"
        chapters_dir.mkdir(exist_ok=True)
        for i, (section, content) in enumerate(zip(sections, rendered, strict=True), start=1):
            slug = markdown_service.slugify(section.title or f"capitulo_{i}")
            chapter_file = chapters_dir / f"{i:02d}_{slug}{ext}"
            chapter_file.write_text(content, encoding="utf-8")
            outputs.append(chapter_file)
            rel = f"capitulos/{chapter_file.name}"
            manifest_outputs.append(manifest_service.OutputEntry(
                file=rel, type=out_type, source_ref=section.source_ref or None))
            index_entries.append((section.title or f"Capítulo {i}", rel))
    elif profile.split_max_chars > 0:
        parts = markdown_service.split_by_max_chars(full_content, profile.split_max_chars)
        if len(parts) > 1:
            parts_dir = out_dir / "partes"
            parts_dir.mkdir(exist_ok=True)
            for i, part in enumerate(parts, start=1):
                part_file = parts_dir / f"parte_{i:03d}{ext}"
                part_file.write_text(part, encoding="utf-8")
                outputs.append(part_file)
                rel = f"partes/{part_file.name}"
                manifest_outputs.append(manifest_service.OutputEntry(file=rel, type=out_type))
                index_entries.append((f"Parte {i:03d}", rel))

    if profile.include_index and is_markdown and len(index_entries) > 1:
        index_file = out_dir / "indice.md"
        index_file.write_text(markdown_service.build_index(index_entries), encoding="utf-8")
        outputs.append(index_file)
        manifest_outputs.append(manifest_service.OutputEntry(file="indice.md", type="markdown"))

    manifest_path: Path | None = None
    if profile.write_manifest:
        manifest = manifest_service.build_manifest(
            project_name=project_name,
            source_files=[source_entry] if source_entry else [],
            outputs=manifest_outputs,
        )
        manifest_path = manifest_service.write_manifest(manifest, out_dir)

    logger.info("Pacote '%s' exportado em %s (%d arquivos, backend=%s)",
                project_name, out_dir, len(outputs), result.backend_name)
    return ConversionResult(
        success=True,
        output_files=outputs,
        manifest_path=manifest_path,
        backend_name=result.backend_name,
        message=f"{len(outputs)} arquivo(s) gerado(s).",
        warnings=list(result.warnings),
    )


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
