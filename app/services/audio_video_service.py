"""Serviço de áudio/vídeo via FFmpeg (Módulo 4 — Etapa 6).

Responsável por extrair a trilha de áudio de vídeos e aplicar normalização
básica antes da transcrição. A interface está fixada; a implementação entra
na Etapa 6.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def is_available() -> bool:
    return ffmpeg_path() is not None


def extract_audio(video_path: str | Path, output_wav: str | Path,
                  sample_rate: int = 16_000) -> Path:
    """(Etapa 6) Extrai o áudio de um vídeo como WAV mono (padrão 16 kHz)."""
    if not is_available():
        raise RuntimeError(
            "FFmpeg não foi encontrado no PATH.\n"
            "Instale com:  winget install Gyan.FFmpeg"
        )
    raise NotImplementedError(
        "A extração de áudio será implementada na Etapa 6 (FFmpeg)."
    )
