"""JobManager — agenda e acompanha jobs em background.

A UI interage apenas com este objeto para rodar operações longas, conectando-se
aos sinais para receber progresso, resultado e erros sem travar a interface.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.infrastructure.logging_config import get_logger
from app.jobs.job_model import Job, JobStatus
from app.jobs.progress import Progress
from app.jobs.worker import JobWorker

logger = get_logger(__name__)


class JobManager(QObject):
    # Reemitidos para a UI (job_id nos permite rotear para o widget correto).
    job_started = Signal(str)                 # job_id
    job_progress = Signal(str, Progress)      # job_id, progress
    job_result = Signal(str, object)          # job_id, result
    job_error = Signal(str, str)              # job_id, mensagem
    job_finished = Signal(str, JobStatus)     # job_id, status final

    def __init__(self, max_threads: int | None = None) -> None:
        super().__init__()
        self._pool = QThreadPool.globalInstance()
        if max_threads is not None:
            self._pool.setMaxThreadCount(max_threads)
        self._jobs: dict[str, Job] = {}

    def submit(self, job: Job) -> str:
        self._jobs[job.id] = job
        worker = JobWorker(job)
        worker.signals.progress.connect(self.job_progress)
        worker.signals.result.connect(self.job_result)
        worker.signals.error.connect(self.job_error)
        worker.signals.finished.connect(self._on_finished)
        self.job_started.emit(job.id)
        self._pool.start(worker)
        logger.info("Job %s agendado (%s)", job.id, job.job_type)
        return job.id

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job.request_cancel()
            logger.info("Cancelamento solicitado para job %s", job_id)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _on_finished(self, job_id: str, status: JobStatus) -> None:
        self.job_finished.emit(job_id, status)

    def wait_for_done(self, msecs: int = -1) -> bool:
        """Aguarda todos os jobs (usado no shutdown)."""
        return self._pool.waitForDone(msecs)
