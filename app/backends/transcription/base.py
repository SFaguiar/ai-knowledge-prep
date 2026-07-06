"""Interface comum para backends de transcrição (Seção 5).

Prepara a Etapa 6 (FasterWhisperBackend) e a extensão futura (WhisperCppBackend),
mantendo a mesma filosofia intercambiável dos backends documentais.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.models.transcription_options import TranscriptionOptions
from app.models.transcription_segment import TranscriptionSegment

__all__ = [
    "TranscriptionBackend",
    "TranscriptionOptions",
    "TranscriptionResult",
    "TranscriptionSegment",
]


@dataclass
class TranscriptionResult:
    backend_name: str
    language: str
    full_text: str
    segments: list[TranscriptionSegment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class TranscriptionBackend(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def transcribe(self, audio_path: Path,
                   options: TranscriptionOptions) -> TranscriptionResult:
        raise NotImplementedError
