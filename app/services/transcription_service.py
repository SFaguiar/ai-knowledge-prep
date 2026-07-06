"""Serviço de transcrição (Módulo 4 — Etapa 6).

Orquestra FFmpeg (extração/normalização de áudio) e o backend de transcrição
(faster-whisper por padrão; whisper.cpp como alternativo), exportando
TXT/Markdown/JSON com timestamps. A interface está fixada; a implementação
entra na Etapa 6.
"""

from __future__ import annotations

from pathlib import Path

from app.backends.transcription.base import TranscriptionBackend, TranscriptionResult
from app.backends.transcription.faster_whisper_backend import FasterWhisperBackend
from app.backends.transcription.whisper_cpp_backend import WhisperCppBackend
from app.models.transcription_options import TranscriptionOptions


def available_backends() -> list[TranscriptionBackend]:
    """Backends de transcrição instalados, em ordem de preferência."""
    return [
        backend
        for backend in (FasterWhisperBackend(), WhisperCppBackend())
        if backend.is_available()
    ]


def select_backend() -> TranscriptionBackend | None:
    backends = available_backends()
    return backends[0] if backends else None


def transcribe_file(media_path: str | Path,
                    options: TranscriptionOptions | None = None) -> TranscriptionResult:
    """(Etapa 6) Transcreve um arquivo de áudio ou vídeo."""
    backend = select_backend()
    if backend is None:
        raise RuntimeError(
            "Não foi possível transcrever este arquivo.\n\nPossíveis causas:\n"
            "- faster-whisper não está instalado (grupo opcional `media`).\n"
            "- Nenhum backend de transcrição alternativo foi encontrado."
        )
    return backend.transcribe(Path(media_path), options or TranscriptionOptions())
