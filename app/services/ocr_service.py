"""Serviço de OCR (Módulo 3 — Etapa 5).

A detecção de PDF escaneado (pouca camada textual) já funciona. A aplicação de
OCR de fato — OCRmyPDF + Tesseract + Ghostscript, idioma padrão português,
com deskew e correção de rotação — entra na Etapa 5.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

DEFAULT_LANGUAGE = "por"

# Nomes do executável do Ghostscript variam por plataforma.
_GHOSTSCRIPT_NAMES = ("gswin64c", "gswin32c", "gs")


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


def apply_ocr(pdf_path: str | Path, output_path: str | Path,
              language: str = DEFAULT_LANGUAGE, deskew: bool = True,
              rotate_pages: bool = True) -> Path:
    """(Etapa 5) Gera um PDF pesquisável via OCRmyPDF."""
    ok, missing = ocr_available()
    if not ok:
        raise RuntimeError(
            "Não foi possível aplicar OCR neste PDF.\n\nPossíveis causas:\n"
            + "\n".join(f"- {item} não está instalado." for item in missing)
        )
    raise NotImplementedError(
        "A aplicação de OCR será implementada na Etapa 5 (OCRmyPDF)."
    )
