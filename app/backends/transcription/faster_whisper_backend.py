"""Backend faster-whisper — principal para transcrição local (Seção 4, Etapa 6).

A detecção de disponibilidade já funciona (tela de Configurações). A
transcrição de fato é ligada na Etapa 6; a interface está fixada desde já.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.backends.transcription.base import (
    TranscriptionBackend,
    TranscriptionOptions,
    TranscriptionResult,
)


class FasterWhisperBackend(TranscriptionBackend):
    name = "faster-whisper"

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("faster_whisper") is not None
        except (ImportError, ValueError):
            return False

    def transcribe(self, audio_path: Path,
                   options: TranscriptionOptions) -> TranscriptionResult:
        raise NotImplementedError(
            "A transcrição com faster-whisper será ativada na Etapa 6."
        )
