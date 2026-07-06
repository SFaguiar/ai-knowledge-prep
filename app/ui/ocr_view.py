"""Módulo 3 — OCR (Etapa 5)."""

from __future__ import annotations

from app.ui.placeholder_view import PlaceholderView


class OcrView(PlaceholderView):
    def __init__(self) -> None:
        super().__init__(
            "OCR",
            "Transformar PDF escaneado ou imagem em texto e PDF pesquisável.",
            roadmap="Etapa 5 — OCRmyPDF + Tesseract (idioma padrão: português), "
                    "geração de PDF pesquisável e exportação Markdown/TXT.",
        )
