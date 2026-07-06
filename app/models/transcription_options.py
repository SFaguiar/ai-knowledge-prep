"""Opções de transcrição de áudio/vídeo (Módulo 4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionOptions:
    #: "pt" por padrão; use "auto" para autodetecção de idioma (Seção 4).
    language: str = "pt"
    include_timestamps: bool = True
    #: Nome/tamanho do modelo (ex.: "small", "medium") — específico do backend.
    model: str = "small"
