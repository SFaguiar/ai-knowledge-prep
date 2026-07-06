"""Módulo 4 — Transcrição de áudio/vídeo (Etapa 6)."""

from __future__ import annotations

from app.ui.placeholder_view import PlaceholderView


class TranscriptionView(PlaceholderView):
    def __init__(self) -> None:
        super().__init__(
            "Transcrever áudio/vídeo",
            "Gerar texto limpo a partir de áudio ou vídeo, com timestamps.",
            roadmap="Etapa 6 — FFmpeg + faster-whisper, exportação TXT/Markdown/JSON.",
        )
