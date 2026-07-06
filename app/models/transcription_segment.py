"""Segmento de transcrição com janela de tempo (Módulo 4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str

    def to_dict(self) -> dict:
        """Formato usado na exportação JSON de segmentos (Seção 9)."""
        return {"start": self.start, "end": self.end, "text": self.text}
