"""Módulo 2 — Documento para IA (Etapas 3 e 4).

Converte PDF (texto nativo) e EPUB em Markdown/TXT, exportando um pacote
organizado (fonte completa, capítulos/partes, índice e manifest.json). A
extração roda como job em background; o backend é escolhido automaticamente
pelo tipo de arquivo. O arquivo original é sempre preservado.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.logging_config import get_logger
from app.infrastructure.settings import Settings
from app.jobs.document_jobs import ExtractDocumentJob
from app.jobs.job_manager import JobManager
from app.jobs.job_model import JobStatus
from app.jobs.progress import Progress
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.presets import LLM_GENERIC, NOTEBOOKLM, OBSIDIAN
from app.services import document_prep_service
from app.services.document_prep_service import DEFAULT_PROFILE
from app.services.markdown_service import slugify

logger = get_logger(__name__)

# (rótulo, perfil de exportação)
_PRESETS: list[tuple[str, ExportProfile]] = [
    ("Padrão — arquivo único", DEFAULT_PROFILE),
    ("NotebookLM — dividido + índice", NOTEBOOKLM),
    ("Obsidian — um arquivo por capítulo", OBSIDIAN),
    ("LLM genérico — dividido por tamanho", LLM_GENERIC),
]
_FORMATS: list[tuple[str, OutputFormat]] = [
    ("Markdown (.md)", OutputFormat.MARKDOWN),
    ("Texto (.txt)", OutputFormat.TXT),
]


class DocumentPrepView(QWidget):
    def __init__(self, job_manager: JobManager, settings: Settings) -> None:
        super().__init__()
        self.job_manager = job_manager
        self.settings = settings
        self.source_path: Path | None = None
        self._active_job_id: str | None = None
        self._last_output_dir: Path | None = None

        self.setAcceptDrops(True)
        self._build_ui()
        self._wire_jobs()
        self._update_actions()

    # --- construção da UI ---
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QLabel("Documento para IA")
        header.setProperty("cssClass", "heading")
        root.addWidget(header)

        subtitle = QLabel(
            "Converta PDF ou EPUB em Markdown/TXT e gere um pacote organizado "
            "(fonte completa, capítulos/partes, índice e manifest.json)."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("cssClass", "subtitle")
        root.addWidget(subtitle)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_open = QPushButton("📂 Abrir documento…")
        self.btn_open.clicked.connect(self.open_document)
        bar.addWidget(self.btn_open)
        bar.addWidget(self._divider())

        bar.addWidget(QLabel("Formato:"))
        self.combo_format = QComboBox()
        for label, _fmt in _FORMATS:
            self.combo_format.addItem(label)
        bar.addWidget(self.combo_format)

        bar.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        for label, _profile in _PRESETS:
            self.combo_preset.addItem(label)
        self.combo_preset.setMinimumWidth(230)
        bar.addWidget(self.combo_preset)

        bar.addStretch(1)
        self.btn_convert = QPushButton("✨ Converter e exportar…")
        self.btn_convert.setProperty("cssClass", "primary")
        self.btn_convert.clicked.connect(self.convert)
        bar.addWidget(self.btn_convert)
        root.addLayout(bar)

        self.info = QLabel("Abra um PDF ou EPUB, ou arraste o arquivo para esta janela.")
        self.info.setProperty("cssClass", "info")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        self.log = QPlainTextEdit()
        self.log.setProperty("cssClass", "console")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Registro da conversão…")
        root.addWidget(self.log, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        foot = QHBoxLayout()
        foot.addStretch(1)
        self.btn_open_folder = QPushButton("📁 Abrir pasta de saída")
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        self.btn_open_folder.setVisible(False)
        foot.addWidget(self.btn_open_folder)
        root.addLayout(foot)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedHeight(24)
        line.setStyleSheet("color: #3a4256;")
        return line

    def _wire_jobs(self) -> None:
        self.job_manager.job_progress.connect(self._on_progress)
        self.job_manager.job_error.connect(self._on_job_error)
        self.job_manager.job_finished.connect(self._on_job_finished)
        self.job_manager.job_result.connect(self._on_job_result)

    # --- carregamento ---
    def open_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir documento", self.settings.default_output_dir,
            "Documentos (*.pdf *.epub);;PDF (*.pdf);;EPUB (*.epub)"
        )
        if path:
            self._load(Path(path))

    def _load(self, path: Path) -> None:
        suffix = path.suffix.lower()
        if suffix not in document_prep_service.SUPPORTED_SUFFIXES:
            self._error("Formato não suportado nesta etapa.",
                        "Aceitos: PDF e EPUB. Outros formatos chegam nas próximas etapas.")
            return
        self.source_path = path
        backend = document_prep_service.select_backend(path)
        if backend is None:
            self.info.setText(f"⚠️  {path.name} — nenhum backend disponível para este arquivo.")
            if suffix == ".epub":
                self._log("EPUB requer o grupo opcional 'docs' (ebooklib + bs4). "
                          'Instale com:  pip install -e ".[docs]"')
        else:
            note = ""
            if backend.name == "pymupdf":
                note = "  (extração básica — instale 'pymupdf4llm' para Markdown estruturado)"
            self.info.setText(f"{path.name}  ·  backend: {backend.name}{note}")
            self._log(f"Aberto: {path.name} (backend selecionado: {backend.name})")
        self._update_actions()

    # --- conversão (job) ---
    def _current_profile(self) -> ExportProfile:
        _, profile = _PRESETS[self.combo_preset.currentIndex()]
        _, fmt = _FORMATS[self.combo_format.currentIndex()]
        return replace(profile, output_format=fmt)

    def convert(self) -> None:
        if self.source_path is None:
            self._log("Abra um documento primeiro.")
            return
        if document_prep_service.select_backend(self.source_path) is None:
            self._error(
                "Não é possível converter este arquivo.",
                "O backend necessário não está instalado. Para EPUB, instale o "
                'grupo opcional de documentos:  pip install -e ".[docs]"'
            )
            return

        base_dir = QFileDialog.getExistingDirectory(
            self, "Escolher pasta de saída", self.settings.default_output_dir
        )
        if not base_dir:
            return

        profile = self._current_profile()
        fmt_tag = "md" if profile.output_format == OutputFormat.MARKDOWN else "txt"
        package_dir = Path(base_dir) / f"{slugify(self.source_path.stem)}_{fmt_tag}"
        if package_dir.exists() and any(package_dir.iterdir()):
            reply = QMessageBox.question(
                self, "Pasta já existe",
                f"A pasta de saída já existe e não está vazia:\n{package_dir}\n\n"
                "Os arquivos podem ser sobrescritos. Deseja continuar?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        job = ExtractDocumentJob(
            source_path=self.source_path,
            output_dir=package_dir,
            profile=profile,
            output_format=profile.output_format,
        )
        self._last_output_dir = package_dir
        self._start_job(job)

    def _start_job(self, job) -> None:
        self._active_job_id = job.id
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_open_folder.setVisible(False)
        self._set_busy(True)
        self._log(f"Convertendo {self.source_path.name}…")
        self.job_manager.submit(job)

    def _on_progress(self, job_id: str, progress: Progress) -> None:
        if job_id != self._active_job_id:
            return
        if progress.percent < 0:
            self.progress.setRange(0, 0)  # indeterminado
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(progress.percent)
        if progress.message:
            self.info.setText(progress.message)

    def _on_job_result(self, job_id: str, result) -> None:
        if job_id != self._active_job_id or not isinstance(result, dict):
            return
        conversion = result.get("conversion")
        if conversion is None:
            return
        self._log(f"✔ {conversion.message}  (backend: {conversion.backend_name})")
        for out in conversion.output_files:
            try:
                rel = out.relative_to(self._last_output_dir)
            except (ValueError, TypeError):
                rel = out.name
            self._log(f"   • {rel}")
        if conversion.manifest_path:
            self._log(f"   • {conversion.manifest_path.name}")
        for warning in conversion.warnings:
            self._log(f"⚠ {warning}")
        self.btn_open_folder.setVisible(True)

    def _on_job_error(self, job_id: str, message: str) -> None:
        if job_id != self._active_job_id:
            return
        self._error("A conversão falhou.", message)

    def _on_job_finished(self, job_id: str, status: JobStatus) -> None:
        if job_id != self._active_job_id:
            return
        self.progress.setVisible(False)
        self._set_busy(False)
        self._active_job_id = None
        self.info.setText(f"Operação {status.value}.")
        self._update_actions()

    # --- helpers ---
    def _open_output_folder(self) -> None:
        if self._last_output_dir and self._last_output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output_dir)))

    def _set_busy(self, busy: bool) -> None:
        for w in (self.btn_open, self.btn_convert, self.combo_format, self.combo_preset):
            w.setEnabled(not busy)

    def _update_actions(self) -> None:
        has_source = self.source_path is not None
        self.btn_convert.setEnabled(has_source and self._active_job_id is None)

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)
        logger.info("[Documento para IA] %s", message)

    def _error(self, title: str, detail: str) -> None:
        QMessageBox.warning(self, title, f"{title}\n\n{detail}")
        self._log(f"ERRO: {title}")

    # --- drag & drop ---
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".pdf", ".epub")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith((".pdf", ".epub")):
                self._load(Path(p))
                return
