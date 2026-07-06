"""Presets de exportação (Seção 8).

Um preset descreve como preparar a saída para um destino específico
(NotebookLM, Obsidian, LLM genérico, Transcrição para IA). São dados puros,
consumidos pelos módulos de exportação nas etapas futuras.
"""

from __future__ import annotations

from app.presets.base import PRESETS, ExportPreset, get_preset
from app.presets.llm_generic import LLM_GENERIC
from app.presets.notebooklm import NOTEBOOKLM
from app.presets.obsidian import OBSIDIAN
from app.presets.transcription_ai import TRANSCRIPTION_AI

__all__ = [
    "ExportPreset",
    "PRESETS",
    "get_preset",
    "NOTEBOOKLM",
    "OBSIDIAN",
    "LLM_GENERIC",
    "TRANSCRIPTION_AI",
]
