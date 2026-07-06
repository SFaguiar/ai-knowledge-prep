"""Definição base de um Job.

Um Job encapsula uma operação longa (remover páginas, converter, OCR,
transcrever...). A regra é: a UI nunca chama a lógica pesada diretamente —
ela agenda um Job no JobManager, que o executa fora da thread da interface.

Subclasses implementam apenas `run()`, usando `self.report()` para progresso
e `self.check_cancelled()` para permitir cancelamento cooperativo.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable

from app.jobs.progress import CancelledError, Progress


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(ABC):
    """Unidade de trabalho executável em background."""

    #: Nome legível curto (usado em logs/histórico), ex.: "RemovePdfPagesJob".
    job_type: str = "Job"

    def __init__(self, title: str = "") -> None:
        self.id: str = uuid.uuid4().hex[:12]
        self.title: str = title or self.job_type
        self.status: JobStatus = JobStatus.PENDING
        self.result: Any = None
        self.error: str | None = None
        self._cancel_requested: bool = False
        # Preenchido pelo worker para emitir progresso à UI.
        self._progress_cb: Callable[[Progress], None] | None = None

    # --- API para o JobManager/worker ---
    def bind_progress(self, cb: Callable[[Progress], None]) -> None:
        self._progress_cb = cb

    def request_cancel(self) -> None:
        self._cancel_requested = True

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    # --- API para subclasses ---
    def report(self, fraction: float, message: str = "") -> None:
        if self._progress_cb is not None:
            self._progress_cb(Progress(fraction=fraction, message=message))

    def check_cancelled(self) -> None:
        if self._cancel_requested:
            raise CancelledError()

    @abstractmethod
    def run(self) -> Any:
        """Executa o trabalho. Deve levantar exceção em caso de falha."""
        raise NotImplementedError
