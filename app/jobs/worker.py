"""Worker que executa um Job em uma thread do QThreadPool.

Usa sinais Qt para comunicar progresso/conclusão de volta à thread da UI de
forma thread-safe. Nunca toca widgets diretamente.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.infrastructure.logging_config import get_logger
from app.jobs.job_model import Job, JobStatus
from app.jobs.progress import CancelledError, Progress

logger = get_logger(__name__)


class WorkerSignals(QObject):
    progress = Signal(str, Progress)          # job_id, progress
    finished = Signal(str, JobStatus)         # job_id, status final
    result = Signal(str, object)              # job_id, result
    error = Signal(str, str)                  # job_id, mensagem amigável


class JobWorker(QRunnable):
    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        job = self.job

        def on_progress(p: Progress) -> None:
            self.signals.progress.emit(job.id, p)

        job.bind_progress(on_progress)
        job.status = JobStatus.RUNNING
        logger.info("Iniciando job %s (%s)", job.id, job.job_type)

        try:
            job.result = job.run()
            job.status = JobStatus.SUCCESS
            self.signals.result.emit(job.id, job.result)
            logger.info("Job %s concluído com sucesso", job.id)
        except CancelledError:
            job.status = JobStatus.CANCELLED
            logger.info("Job %s cancelado", job.id)
        except Exception as exc:  # noqa: BLE001 - fronteira de robustez do worker
            job.status = JobStatus.FAILED
            job.error = str(exc)
            # Log técnico sem conteúdo de documento.
            logger.exception("Job %s falhou: %s", job.id, exc)
            self.signals.error.emit(job.id, str(exc))
        finally:
            self.signals.finished.emit(job.id, job.status)
