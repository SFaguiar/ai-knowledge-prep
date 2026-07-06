"""Gerenciador de temporários controlado (Seção 14).

Cria diretórios temporários dentro da área de dados do app e garante limpeza.
Evita usar %TEMP% do sistema diretamente para manter previsibilidade e
facilitar a limpeza de resíduos de conversões/OCR/transcrições.
"""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.infrastructure.logging_config import get_logger
from app.infrastructure.paths import temp_dir

logger = get_logger(__name__)


class TempManager:
    def __init__(self) -> None:
        self._root = temp_dir()

    def new_workspace(self, prefix: str = "job") -> Path:
        ws = self._root / f"{prefix}_{uuid.uuid4().hex[:12]}"
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def cleanup(self, workspace: Path) -> None:
        try:
            if workspace.exists() and self._root in workspace.parents:
                shutil.rmtree(workspace, ignore_errors=True)
        except OSError as exc:
            logger.warning("Falha ao limpar temporário %s: %s", workspace, exc)

    def cleanup_all(self) -> None:
        """Remove todos os workspaces temporários órfãos (ex.: no shutdown)."""
        for child in self._root.glob("*"):
            if child.is_dir():
                self.cleanup(child)

    @contextmanager
    def workspace(self, prefix: str = "job") -> Iterator[Path]:
        ws = self.new_workspace(prefix)
        try:
            yield ws
        finally:
            self.cleanup(ws)


# Instância compartilhada.
temp_manager = TempManager()
