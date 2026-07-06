"""Configurações persistentes do aplicativo (JSON local simples).

Sem telemetria, sem rede. Apenas preferências do usuário salvas localmente.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from app.infrastructure.logging_config import get_logger
from app.infrastructure.paths import default_output_dir, settings_path

logger = get_logger(__name__)


@dataclass
class Settings:
    # Idioma padrão de OCR/transcrição (pt por padrão, conforme spec).
    default_ocr_language: str = "por"
    default_transcription_language: str = "pt"  # "auto" para autodetecção
    default_output_dir: str = ""
    # Preferência de backend de extração: "auto" ou nome específico.
    preferred_document_backend: str = "auto"
    # Nunca alterar sem consentimento explícito do usuário.
    telemetry_enabled: bool = False
    theme: str = "system"
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.default_output_dir:
            self.default_output_dir = str(default_output_dir())


def load_settings() -> Settings:
    path = settings_path()
    if not path.exists():
        s = Settings()
        save_settings(s)
        return s
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        known = {f: data[f] for f in Settings.__dataclass_fields__ if f in data}
        return Settings(**known)
    except (json.JSONDecodeError, OSError, TypeError) as exc:
        logger.warning("Falha ao ler settings (%s). Usando padrões.", exc)
        return Settings()


def save_settings(settings: Settings) -> None:
    path = settings_path()
    try:
        path.write_text(
            json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        logger.error("Não foi possível salvar settings: %s", exc)
