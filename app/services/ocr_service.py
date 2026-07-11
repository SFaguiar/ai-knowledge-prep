"""Serviço de OCR (Módulo 3 — Etapa 5).

Aplica OCR local com OCRmyPDF (que orquestra Tesseract + Ghostscript),
gerando um PDF pesquisável a partir de um PDF escaneado ou de uma imagem, e
extrai o texto reconhecido por página. Também detecta PDFs provavelmente
escaneados e os idiomas de OCR instalados no Tesseract.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

from app.infrastructure.logging_config import get_logger
from app.infrastructure.temp_manager import temp_manager
from app.models.extraction_result import ExtractionResult, ExtractionSection

logger = get_logger(__name__)

DEFAULT_LANGUAGE = "por"

# Nomes do executável do Ghostscript variam por plataforma.
_GHOSTSCRIPT_NAMES = ("gswin64c", "gswin32c", "gs")

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")

# Rótulos amigáveis para códigos de idioma comuns do Tesseract.
LANGUAGE_LABELS: dict[str, str] = {
    "por": "Português",
    "eng": "English",
    "spa": "Español",
    "fra": "Français",
    "deu": "Deutsch",
    "ita": "Italiano",
}


def language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def is_probably_scanned(pdf_path: str | Path, sample_pages: int = 5,
                        min_chars_per_page: int = 40) -> bool:
    """Heurística: True se o PDF tem pouca (ou nenhuma) camada textual."""
    import fitz  # PyMuPDF

    with fitz.open(str(pdf_path)) as doc:
        checked = min(sample_pages, doc.page_count)
        if checked == 0:
            return False
        chars = sum(
            len((doc.load_page(i).get_text("text") or "").strip())
            for i in range(checked)
        )
        return (chars / checked) <= min_chars_per_page


def ocr_available() -> tuple[bool, list[str]]:
    """Verifica a cadeia de OCR. Retorna (ok, lista de itens ausentes)."""
    missing: list[str] = []
    try:
        if importlib.util.find_spec("ocrmypdf") is None:
            missing.append("OCRmyPDF")
    except (ImportError, ValueError):
        missing.append("OCRmyPDF")
    if shutil.which("tesseract") is None:
        missing.append("Tesseract")
    if not any(shutil.which(name) for name in _GHOSTSCRIPT_NAMES):
        missing.append("Ghostscript")
    return (not missing, missing)


def available_languages() -> list[str]:
    """Idiomas de OCR instalados no Tesseract (sem 'osd', que não é idioma).

    Retorna lista vazia se o Tesseract não estiver disponível ou a sondagem
    falhar — a UI deve então cair para `[DEFAULT_LANGUAGE]`.
    """
    tess = shutil.which("tesseract")
    if not tess:
        return []
    try:
        out = subprocess.run(
            [tess, "--list-langs"], capture_output=True, text=True, timeout=10
        )
        lines = (out.stdout or out.stderr or "").splitlines()
        # A 1a linha é um cabeçalho ("List of available languages...").
        langs = {ln.strip() for ln in lines[1:] if ln.strip()}
        langs.discard("osd")
        return sorted(langs)
    except (OSError, subprocess.SubprocessError):
        return []


def _missing_deps_error(missing: list[str]) -> RuntimeError:
    return RuntimeError(
        "Não foi possível aplicar OCR neste arquivo.\n\nPossíveis causas:\n"
        + "\n".join(f"- {item} não está instalado." for item in missing)
    )


def _ensure_pdf(source_path: Path) -> tuple[Path, Path | None]:
    """Garante um PDF de entrada para o OCRmyPDF, convertendo imagem se preciso.

    Retorna (caminho_do_pdf, workspace_temporario_ou_none) — quando não-None,
    o workspace deve ser limpo pelo chamador após o uso.
    """
    if source_path.suffix.lower() not in IMAGE_SUFFIXES:
        return source_path, None

    import fitz  # PyMuPDF

    workspace = temp_manager.new_workspace("ocr_img")
    temp_pdf = workspace / "origem.pdf"
    img_doc = fitz.open(str(source_path))
    pdf_bytes = img_doc.convert_to_pdf()
    img_doc.close()
    temp_pdf.write_bytes(pdf_bytes)
    return temp_pdf, workspace


def apply_ocr(
    source_path: str | Path,
    output_path: str | Path,
    *,
    language: str = DEFAULT_LANGUAGE,
    deskew: bool = True,
    rotate_pages: bool = True,
    force_ocr: bool = False,
) -> Path:
    """Gera um PDF pesquisável via OCRmyPDF. Aceita PDF ou imagem como origem.

    Por padrão (`force_ocr=False`) páginas que já têm texto são preservadas
    como estão (`skip_text`); ligue `force_ocr` para reprocessar tudo via OCR
    — útil quando o texto nativo existente está corrompido ou ilegível.
    """
    ok, missing = ocr_available()
    if not ok:
        raise _missing_deps_error(missing)

    import ocrmypdf
    from ocrmypdf.exceptions import ExitCodeException

    src = Path(source_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf_input, workspace = _ensure_pdf(src)
    try:
        kwargs: dict = dict(
            language=language,
            deskew=deskew,
            rotate_pages=rotate_pages,
            progress_bar=False,
        )
        if force_ocr:
            kwargs["force_ocr"] = True
        else:
            kwargs["skip_text"] = True
        ocrmypdf.ocr(str(pdf_input), str(out), **kwargs)
    except ExitCodeException as exc:
        raise RuntimeError(f"OCRmyPDF não conseguiu processar o arquivo: {exc}") from exc
    finally:
        if workspace is not None:
            temp_manager.cleanup(workspace)

    logger.info("OCR aplicado: %s -> %s (idioma=%s)", src.name, out.name, language)
    return out


def extract_text(searchable_pdf: str | Path) -> ExtractionResult:
    """Extrai o texto (já com a camada de OCR) de um PDF pesquisável, por página."""
    import fitz  # PyMuPDF

    sections: list[ExtractionSection] = []
    parts: list[str] = []
    with fitz.open(str(searchable_pdf)) as doc:
        for i, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            parts.append(text)
            sections.append(
                ExtractionSection(title=f"Página {i}", content=text, source_ref=str(i))
            )

    return ExtractionResult(
        backend_name="ocrmypdf",
        full_text="\n\n".join(p for p in parts if p),
        sections=sections,
        metadata={"pages": len(sections)},
    )
