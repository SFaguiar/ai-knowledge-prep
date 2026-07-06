"""Agregação de presets de exportação (Seção 8).

Modelo declarativo e neutro de UI/serviço: cada preset é apenas configuração
(`ExportProfile`, em app.models.export_profile). Cada destino vive em seu
módulo próprio (notebooklm, obsidian, llm_generic, transcription_ai); este
módulo agrega todos e resolve por chave.
"""

from __future__ import annotations

from app.models.export_profile import ExportProfile
from app.presets.llm_generic import LLM_GENERIC
from app.presets.notebooklm import NOTEBOOKLM
from app.presets.obsidian import OBSIDIAN
from app.presets.transcription_ai import TRANSCRIPTION_AI

# Nome histórico (Seção 8); mesmo dataclass.
ExportPreset = ExportProfile

PRESETS: dict[str, ExportProfile] = {
    p.key: p for p in (NOTEBOOKLM, OBSIDIAN, LLM_GENERIC, TRANSCRIPTION_AI)
}


def get_preset(key: str) -> ExportProfile | None:
    return PRESETS.get(key)
