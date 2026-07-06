"""Resolução de caminhos locais do aplicativo.

Centraliza onde ficam configurações, logs, banco de histórico e temporários.
Local-first: tudo dentro da pasta de dados do usuário, nada em nuvem.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "AIKnowledgePrep"


def _base_data_dir() -> Path:
    """Diretório base de dados do app, dependente do SO.

    Windows: %LOCALAPPDATA%\\AIKnowledgePrep
    Linux:   ~/.local/share/AIKnowledgePrep (ou $XDG_DATA_HOME)
    """
    if sys.platform.startswith("win"):
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(root) / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / APP_DIR_NAME


def data_dir() -> Path:
    p = _base_data_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_dir() -> Path:
    p = data_dir() / "config"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def temp_dir() -> Path:
    p = data_dir() / "temp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def database_path() -> Path:
    return data_dir() / "history.sqlite3"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def default_output_dir() -> Path:
    """Pasta de saída padrão sugerida (dentro de Documentos quando possível)."""
    docs = Path.home() / "Documents"
    base = docs if docs.exists() else Path.home()
    p = base / "AIKnowledgePrep"
    return p
