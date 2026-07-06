"""Backend whisper.cpp — alternativo/opcional para transcrição (Seção 4).

Depende do binário externo `whisper-cli`. Classe presente para fixar a
interface e detectar disponibilidade; implementação futura (pós-Etapa 6).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.backends.transcription.base import (
    TranscriptionBackend,
    TranscriptionOptions,
    TranscriptionResult,
)


class WhisperCppBackend(TranscriptionBackend):
    name = "whisper.cpp"

    def is_available(self) -> bool:
        return shutil.which("whisper-cli") is not None

    def transcribe(self, audio_path: Path,
                   options: TranscriptionOptions) -> TranscriptionResult:
        raise NotImplementedError(
            "O backend whisper.cpp (opcional) será implementado após a Etapa 6."
        )
