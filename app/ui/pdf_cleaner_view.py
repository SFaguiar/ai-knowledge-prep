"""Módulo 1 — PDF Cleaner (Seção 6).

Abrir PDF, ver miniaturas, selecionar páginas (visual ou por intervalo), remover,
extrair, girar, juntar, dividir e salvar um novo PDF — preservando sempre o
original. Operações de disco rodam como jobs em background; o manifesto e o log
registram o que foi mantido/removido/extraído.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
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
from app.jobs.pdf_jobs import SavePdfJob, SplitPdfJob
from app.jobs.progress import Progress
from app.services import pdf_service
from app.services.pdf_render_service import PdfRenderService
from app.services.pdf_service import PdfDocumentModel
from app.ui.components.thumbnail_grid import ThumbnailGrid
from app.ui.theme import BORDER_STRONG

logger = get_logger(__name__)


def parse_ranges(text: str, max_page: int) -> list[tuple[int, int]]:
    """Interpreta '1-5, 8, 10-12' em intervalos 1-based inclusivos e válidos."""
    ranges: list[tuple[int, int]] = []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, _, b = token.partition("-")
            start, end = int(a), int(b)
        else:
            start = end = int(token)
        start = max(1, min(start, max_page))
        end = max(1, min(end, max_page))
        if start > end:
            start, end = end, start
        ranges.append((start, end))
    return ranges


class PdfCleanerView(QWidget):
    def __init__(self, job_manager: JobManager, render_service: PdfRenderService,
                 settings: Settings) -> None:
        super().__init__()
        self.job_manager = job_manager
        self.render_service = render_service
        self.settings = settings
        self.model: PdfDocumentModel | None = None
        self._active_job_id: str | None = None

        self.setAcceptDrops(True)
        self._build_ui()
        self._wire_jobs()
        self._update_actions()

    # --- construção da UI ---
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QLabel("Limpar PDF")
        header.setProperty("cssClass", "heading")
        root.addWidget(header)

        # Barra de ações em duas linhas, agrupadas por tipo de operação — evita
        # que muitos botões espremidos numa única linha cortem o texto quando
        # a janela não é muito larga.
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_open = self._btn("📂 Abrir PDF", self.open_pdf)
        self.btn_add = self._btn("➕ Juntar PDF…", self.merge_pdf)
        row1.addWidget(self.btn_open)
        row1.addWidget(self.btn_add)
        row1.addWidget(self._divider())

        self.btn_range = self._btn("▤ Intervalo…", self.select_range)
        self.btn_blank = self._btn("👁 Detectar brancas", self.detect_blanks)
        row1.addWidget(self.btn_range)
        row1.addWidget(self.btn_blank)

        row1.addStretch(1)
        self.btn_save = self._btn("💾 Salvar como…", self.save_as, "primary")
        row1.addWidget(self.btn_save)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.btn_rot_l = self._btn("⟲ Girar", lambda: self.rotate(-90))
        self.btn_rot_r = self._btn("⟳ Girar", lambda: self.rotate(90))
        self.btn_remove = self._btn("🗑 Remover sel.", self.remove_selected, "danger")
        self.btn_extract = self._btn("✂ Extrair sel.", self.extract_selected)
        self.btn_split = self._btn("◫ Dividir…", self.split_pdf)
        row2.addWidget(self.btn_rot_l)
        row2.addWidget(self.btn_rot_r)
        row2.addWidget(self.btn_remove)
        row2.addWidget(self.btn_extract)
        row2.addWidget(self.btn_split)
        row2.addWidget(self._divider())

        self.btn_undo = self._btn("↶ Desfazer", self.undo)
        self.btn_redo = self._btn("↷ Refazer", self.redo)
        row2.addWidget(self.btn_undo)
        row2.addWidget(self.btn_redo)
        row2.addStretch(1)
        root.addLayout(row2)

        self.info = QLabel("Abra um PDF ou arraste um arquivo para esta janela.")
        self.info.setProperty("cssClass", "info")
        root.addWidget(self.info)

        self.grid = ThumbnailGrid(self.render_service)
        self.grid.selection_changed.connect(self._on_selection_changed)
        root.addWidget(self.grid, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setProperty("cssClass", "console")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(90)
        self.log.setPlaceholderText("Registro de operações…")
        root.addWidget(self.log)

    def _btn(self, text: str, slot, css_class: str = "") -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(slot)
        if css_class:
            b.setProperty("cssClass", css_class)
        return b

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

    # --- carregamento ---
    def open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir PDF", "", "PDF (*.pdf)"
        )
        if path:
            self._load(Path(path))

    def _load(self, path: Path) -> None:
        try:
            self.model = pdf_service.load_model(path)
        except Exception as exc:  # noqa: BLE001
            self._error("Não foi possível abrir o PDF.",
                        "Verifique se o arquivo é um PDF válido e não está corrompido.\n"
                        f"Detalhe técnico: {exc}")
            return
        self._log(f"Aberto: {path.name} ({self.model.original_page_count} páginas)")
        self.info.setText(f"{path.name} — {len(self.model.pages)} páginas")
        self.grid.set_pages(self.model.pages)
        self._update_actions()

    def merge_pdf(self) -> None:
        if self.model is None:
            self._load_prompt()
            return
        path, _ = QFileDialog.getOpenFileName(self, "Juntar PDF", "", "PDF (*.pdf)")
        if not path:
            return
        try:
            extra = pdf_service.pages_from_pdf(path)
        except Exception as exc:  # noqa: BLE001
            self._error("Não foi possível ler o PDF a juntar.", str(exc))
            return
        self.model.append_pages(extra)
        self._log(f"Juntado: {Path(path).name} (+{len(extra)} páginas)")
        self._refresh_grid()

    # --- edição ---
    def _require_model(self) -> bool:
        if self.model is None:
            self._load_prompt()
            return False
        return True

    def _require_selection(self) -> set[int] | None:
        if not self._require_model():
            return None
        sel = self.grid.selected_positions()
        if not sel:
            self._log("Nenhuma página selecionada.")
            return None
        return sel

    def remove_selected(self) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.remove_pages(sel)
        self._log(f"Removidas {len(sel)} página(s).")
        self._refresh_grid()

    def extract_selected(self) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.keep_only(sel)
        self._log(f"Mantidas apenas {len(sel)} página(s) selecionada(s).")
        self._refresh_grid()

    def rotate(self, delta: int) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.rotate_pages(sel, delta)
        self._log(f"Giradas {len(sel)} página(s) em {delta}°.")
        self._refresh_grid(keep_selection=sel)

    def select_range(self) -> None:
        if not self._require_model():
            return
        text, ok = QInputDialog.getText(
            self, "Selecionar intervalo",
            "Páginas (ex.: 1-5, 8, 10-12):"
        )
        if not ok or not text.strip():
            return
        n = len(self.model.pages)
        positions: set[int] = set()
        for start, end in parse_ranges(text, n):
            positions.update(range(start - 1, end))  # 1-based → posição 0-based
        self.grid.select_positions(positions)
        self._log(f"Selecionadas {len(positions)} página(s) por intervalo.")

    def detect_blanks(self) -> None:
        if not self._require_model():
            return
        try:
            blanks = pdf_service.detect_blank_pages(self.model.primary_path)
        except Exception as exc:  # noqa: BLE001
            self._error("Falha ao detectar páginas em branco.", str(exc))
            return
        # Mapeia índices da origem primária para posições atuais.
        positions = {
            pos for pos, p in enumerate(self.model.pages)
            if p.source_path == self.model.primary_path and p.source_index in set(blanks)
        }
        if not positions:
            self._log("Nenhuma página em branco detectada.")
            return
        self.grid.select_positions(positions)
        self._log(f"{len(positions)} possível(is) página(s) em branco selecionada(s). "
                  "Revise antes de remover.")

    def undo(self) -> None:
        if self.model and self.model.can_undo:
            self.model.undo()
            self._log("Desfazer.")
            self._refresh_grid()

    def redo(self) -> None:
        if self.model and self.model.can_redo:
            self.model.redo()
            self._log("Refazer.")
            self._refresh_grid()

    # --- disco (jobs) ---
    def save_as(self) -> None:
        if not self._require_model():
            return
        if not self.model.pages:
            self._error("Nada para salvar.", "O documento não tem páginas.")
            return
        suggested = str(self.model.primary_path.with_name(
            self.model.primary_path.stem + "_limpo.pdf"))
        path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", suggested, "PDF (*.pdf)")
        if not path:
            return
        out = Path(path)
        overwrite = out.exists()
        if overwrite:
            reply = QMessageBox.question(
                self, "Sobrescrever?",
                f"O arquivo já existe:\n{out}\n\nDeseja sobrescrever?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        job = SavePdfJob(self.model, out, overwrite=overwrite)
        self._start_job(job)

    def split_pdf(self) -> None:
        if not self._require_model():
            return
        n = self.model.original_page_count
        text, ok = QInputDialog.getText(
            self, "Dividir PDF",
            f"Intervalos para dividir o original ({n} páginas), ex.: 1-50, 51-100:"
        )
        if not ok or not text.strip():
            return
        ranges = parse_ranges(text, n)
        if not ranges:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Pasta de saída")
        if not out_dir:
            return
        job = SplitPdfJob(self.model.primary_path, ranges, out_dir)
        self._start_job(job)

    # --- infraestrutura de jobs ---
    def _start_job(self, job) -> None:
        self._active_job_id = job.id
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_busy(True)
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
        if "output" in result:
            self._log(f"Salvo: {Path(result['output']).name}")
            self._log(f"Manifesto: {Path(result['manifest']).name}")
        if "outputs" in result:
            self._log(f"{len(result['outputs'])} arquivo(s) gerado(s) na divisão.")

    def _on_job_error(self, job_id: str, message: str) -> None:
        if job_id != self._active_job_id:
            return
        self._error("A operação falhou.", message)

    def _on_job_finished(self, job_id: str, status: JobStatus) -> None:
        if job_id != self._active_job_id:
            return
        self.progress.setVisible(False)
        self._set_busy(False)
        self._active_job_id = None
        self.info.setText(f"Operação {status.value}.")
        self._update_actions()

    # --- helpers de UI ---
    def _refresh_grid(self, keep_selection: set[int] | None = None) -> None:
        if self.model is None:
            return
        self.grid.set_pages(self.model.pages)
        if keep_selection:
            valid = {p for p in keep_selection if p < len(self.model.pages)}
            self.grid.select_positions(valid)
        self.info.setText(f"{self.model.primary_path.name} — "
                          f"{len(self.model.pages)} páginas")
        self._update_actions()

    def _on_selection_changed(self, count: int) -> None:
        self._update_actions()

    def _set_busy(self, busy: bool) -> None:
        for b in (self.btn_open, self.btn_add, self.btn_remove, self.btn_extract,
                  self.btn_rot_l, self.btn_rot_r, self.btn_split, self.btn_save):
            b.setEnabled(not busy)

    def _update_actions(self) -> None:
        has_model = self.model is not None
        has_pages = has_model and bool(self.model.pages)
        has_sel = has_model and bool(self.grid.selected_positions())
        for b in (self.btn_add, self.btn_range, self.btn_blank, self.btn_split):
            b.setEnabled(has_model)
        for b in (self.btn_remove, self.btn_extract, self.btn_rot_l, self.btn_rot_r):
            b.setEnabled(has_sel)
        self.btn_save.setEnabled(has_pages)
        self.btn_undo.setEnabled(has_model and self.model.can_undo)
        self.btn_redo.setEnabled(has_model and self.model.can_redo)

    def _load_prompt(self) -> None:
        self._log("Abra um PDF primeiro.")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)
        logger.info("[PDF Cleaner] %s", message)

    def _error(self, title: str, detail: str) -> None:
        QMessageBox.warning(self, title, f"{title}\n\n{detail}")
        self._log(f"ERRO: {title}")

    # --- drag & drop ---
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(".pdf"):
                self._load(Path(p))
                return
