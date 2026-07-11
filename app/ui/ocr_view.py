"""Módulo 3 — OCR (Etapa 5).

Aplica OCR local (OCRmyPDF + Tesseract + Ghostscript) a um PDF escaneado ou a
uma imagem, gerando um PDF pesquisável e exportando o texto reconhecido como
Markdown/TXT com manifest — reaproveitando a mesma infraestrutura de
exportação do Módulo 2. Roda como job em background; o arquivo original é
sempre preservado.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.jobs.job_manager import JobManager
from app.jobs.job_model import JobStatus
from app.jobs.ocr_jobs import DEFAULT_PROFILE, ApplyOcrJob
from app.jobs.progress import Progress
from app.models.export_profile import ExportProfile
from app.models.extraction_options import OutputFormat
from app.presets import LLM_GENERIC, NOTEBOOKLM, OBSIDIAN
from app.services import ocr_service
from app.services.markdown_service import slugify
from app.ui.theme import BORDER_STRONG

logger = get_logger(__name__)

_PRESETS: list[tuple[str, ExportProfile]] = [
    ("Padrão — arquivo único", DEFAULT_PROFILE),
    ("NotebookLM — dividido + índice", NOTEBOOKLM),
    ("Obsidian — um arquivo por página", OBSIDIAN),
    ("LLM genérico — dividido por tamanho", LLM_GENERIC),
]
_FORMATS: list[tuple[str, OutputFormat]] = [
    ("Markdown (.md)", OutputFormat.MARKDOWN),
    ("Texto (.txt)", OutputFormat.TXT),
]
_OPEN_FILTER = (
    "PDF e imagens (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
    ";;PDF (*.pdf)"
    ";;Imagens (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
)


class OcrView(QWidget):
    def __init__(self, job_manager: JobManager, settings: Settings) -> None:
        super().__init__()
        self.job_manager = job_manager
        self.settings = settings
        self.source_path: Path | None = None
        self._active_job_id: str | None = None
        self._last_output_dir: Path | None = None
        self._deps_ok = True

        self.setAcceptDrops(True)
        self._build_ui()
        self._wire_jobs()
        self._populate_languages()
        self._update_actions()

    # --- construção da UI ---
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QLabel("OCR")
        header.setProperty("cssClass", "heading")
        root.addWidget(header)

        subtitle = QLabel(
            "Transforme PDF escaneado ou imagem em PDF pesquisável e em "
            "Markdown/TXT com o texto reconhecido."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("cssClass", "subtitle")
        root.addWidget(subtitle)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_open = QPushButton("📂 Abrir PDF/imagem…")
        self.btn_open.clicked.connect(self.open_document)
        row1.addWidget(self.btn_open)
        row1.addWidget(self._divider())

        row1.addWidget(QLabel("Idioma:"))
        self.combo_language = QComboBox()
        row1.addWidget(self.combo_language)

        row1.addWidget(QLabel("Formato:"))
        self.combo_format = QComboBox()
        for label, _fmt in _FORMATS:
            self.combo_format.addItem(label)
        row1.addWidget(self.combo_format)

        row1.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        for label, _profile in _PRESETS:
            self.combo_preset.addItem(label)
        self.combo_preset.setMinimumWidth(210)
        row1.addWidget(self.combo_preset)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self.check_deskew = QCheckBox("Corrigir inclinação (deskew)")
        self.check_deskew.setChecked(True)
        self.check_rotate = QCheckBox("Corrigir rotação automaticamente")
        self.check_rotate.setChecked(True)
        self.check_force = QCheckBox("Forçar OCR (ignorar texto já existente)")
        self.check_force.setToolTip(
            "Reprocessa todas as páginas via OCR, mesmo as que já têm texto "
            "nativo. Use quando o texto existente estiver corrompido/ilegível."
        )
        row2.addWidget(self.check_deskew)
        row2.addWidget(self.check_rotate)
        row2.addWidget(self.check_force)
        row2.addStretch(1)
        self.btn_apply = QPushButton("🔎 Aplicar OCR e exportar…")
        self.btn_apply.setProperty("cssClass", "primary")
        self.btn_apply.clicked.connect(self.apply_ocr)
        row2.addWidget(self.btn_apply)
        root.addLayout(row2)

        self.info = QLabel(
            "Abra um PDF escaneado ou uma imagem, ou arraste o arquivo para esta janela."
        )
        self.info.setProperty("cssClass", "info")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        self.log = QPlainTextEdit()
        self.log.setProperty("cssClass", "console")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Registro do OCR…")
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
        line.setStyleSheet(f"color: {BORDER_STRONG};")
        return line

    def _wire_jobs(self) -> None:
        self.job_manager.job_progress.connect(self._on_progress)
        self.job_manager.job_error.connect(self._on_job_error)
        self.job_manager.job_finished.connect(self._on_job_finished)
        self.job_manager.job_result.connect(self._on_job_result)

    def _populate_languages(self) -> None:
        langs = ocr_service.available_languages() or [ocr_service.DEFAULT_LANGUAGE]
        preferred = self.settings.default_ocr_language
        for code in langs:
            self.combo_language.addItem(f"{ocr_service.language_label(code)} ({code})", code)
        idx = self.combo_language.findData(preferred)
        self.combo_language.setCurrentIndex(idx if idx >= 0 else 0)

    # --- carregamento ---
    def open_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir PDF ou imagem", self.settings.default_output_dir, _OPEN_FILTER
        )
        if path:
            self._load(Path(path))

    def _load(self, path: Path) -> None:
        suffix = path.suffix.lower()
        is_pdf = suffix == ".pdf"
        is_image = suffix in ocr_service.IMAGE_SUFFIXES
        if not (is_pdf or is_image):
            self._error("Formato não suportado.",
                        "Aceitos: PDF e imagens (PNG, JPG, TIFF, BMP).")
            return

        self.source_path = path
        self._deps_ok, missing = ocr_service.ocr_available()
        if not self._deps_ok:
            self.info.setText(f"⚠️  Dependências de OCR ausentes: {', '.join(missing)}")
            self._log("Não é possível aplicar OCR: " + ", ".join(missing) + " não instalado(s). "
                      "Veja Configurações > Verificar dependências.")
            self._update_actions()
            return

        if is_pdf:
            try:
                import fitz

                with fitz.open(str(path)) as doc:
                    pages = doc.page_count
                scanned = ocr_service.is_probably_scanned(path)
            except Exception as exc:  # noqa: BLE001
                self._error("Não foi possível abrir o PDF.", str(exc))
                self.source_path = None
                self._update_actions()
                return
            hint = ("parece escaneado — bom candidato a OCR" if scanned
                   else "já parece ter texto nativo — OCR vai preservar essas páginas, "
                        "a menos que 'Forçar OCR' esteja marcado")
            self.info.setText(f"{path.name}  ·  {pages} páginas  ·  {hint}")
            self._log(f"Aberto: {path.name} ({pages} páginas, {hint})")
        else:
            self.info.setText(f"{path.name}  ·  imagem — será convertida em PDF de 1 página")
            self._log(f"Aberto: {path.name} (imagem)")
        self._update_actions()

    # --- OCR (job) ---
    def _current_profile(self) -> ExportProfile:
        from dataclasses import replace

        _, profile = _PRESETS[self.combo_preset.currentIndex()]
        _, fmt = _FORMATS[self.combo_format.currentIndex()]
        return replace(profile, output_format=fmt)

    def apply_ocr(self) -> None:
        if self.source_path is None:
            self._log("Abra um PDF ou imagem primeiro.")
            return
        if not self._deps_ok:
            self._error("Não é possível aplicar OCR.",
                        "Dependências ausentes. Veja Configurações > Verificar dependências.")
            return

        base_dir = QFileDialog.getExistingDirectory(
            self, "Escolher pasta de saída", self.settings.default_output_dir
        )
        if not base_dir:
            return

        package_dir = Path(base_dir) / f"{slugify(self.source_path.stem)}_ocr"
        if package_dir.exists() and any(package_dir.iterdir()):
            reply = QMessageBox.question(
                self, "Pasta já existe",
                f"A pasta de saída já existe e não está vazia:\n{package_dir}\n\n"
                "Os arquivos podem ser sobrescritos. Deseja continuar?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        language = self.combo_language.currentData() or ocr_service.DEFAULT_LANGUAGE
        job = ApplyOcrJob(
            source_path=self.source_path,
            output_dir=package_dir,
            language=language,
            deskew=self.check_deskew.isChecked(),
            rotate_pages=self.check_rotate.isChecked(),
            force_ocr=self.check_force.isChecked(),
            profile=self._current_profile(),
        )
        self._last_output_dir = package_dir
        self._start_job(job)

    def _start_job(self, job) -> None:
        self._active_job_id = job.id
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # OCR é indeterminado (sem progresso por página)
        self.btn_open_folder.setVisible(False)
        self._set_busy(True)
        self._log(f"Aplicando OCR em {self.source_path.name}…")
        self.job_manager.submit(job)

    def _on_progress(self, job_id: str, progress: Progress) -> None:
        if job_id != self._active_job_id:
            return
        if progress.percent < 0:
            self.progress.setRange(0, 0)
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
        self._log(f"✔ {conversion.message}")
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
        self._error("O OCR falhou.", message)

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
        for w in (self.btn_open, self.btn_apply, self.combo_format,
                  self.combo_preset, self.combo_language, self.check_deskew,
                  self.check_rotate, self.check_force):
            w.setEnabled(not busy)

    def _update_actions(self) -> None:
        self.btn_apply.setEnabled(
            self.source_path is not None and self._deps_ok and self._active_job_id is None
        )

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)
        logger.info("[OCR] %s", message)

    def _error(self, title: str, detail: str) -> None:
        QMessageBox.warning(self, title, f"{title}\n\n{detail}")
        self._log(f"ERRO: {title}")

    # --- drag & drop ---
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                suffix = Path(url.toLocalFile()).suffix.lower()
                if suffix == ".pdf" or suffix in ocr_service.IMAGE_SUFFIXES:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() == ".pdf" or p.suffix.lower() in ocr_service.IMAGE_SUFFIXES:
                self._load(p)
                return
