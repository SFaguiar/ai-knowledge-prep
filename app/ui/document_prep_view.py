"""Módulo 2 — Documento para IA (Etapas 3, 4 e 8)."""

from __future__ import annotations

from app.ui.placeholder_view import PlaceholderView


class DocumentPrepView(PlaceholderView):
    def __init__(self) -> None:
        super().__init__(
            "Documento para IA",
            "Converter PDF/EPUB/documentos para Markdown, TXT e pacotes para LLMs.",
            roadmap="Etapas 3, 4 e 8 — backends de extração (PyMuPDF4LLM, Docling, "
                    "MarkItDown, Marker) e exportação por capítulos com manifest.json.",
        )
