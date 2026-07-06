"""Módulo 1 — PDF Cleaner (Seção 6) — layout de leitor.

Abrir PDF, ver a trilha de páginas (miniatura + legenda de texto), ler a página
em foco num painel grande, buscar por texto, selecionar (checkbox/Espaço),
remover, extrair, girar, juntar, dividir e salvar um novo PDF — preservando
sempre o original. Operações de disco rodam como jobs em background; o manifesto
e o log registram o que foi mantido/removido/extraído.

Interação: clicar numa página a **foca** (abre no preview) sem marcá-la; a
seleção para operações é feita pelo **checkbox** do cartão ou pela tecla Espaço.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.logging_config import get_logger
from app.infrastructure.settings import Settings, save_settings
from app.jobs.job_manager import JobManager
from app.jobs.job_model import JobStatus
from app.jobs.pdf_jobs import SavePdfJob, SplitPdfJob
from app.jobs.progress import Progress
from app.services import pdf_service
from app.services.pdf_render_service import PdfRenderService, normalize_text
from app.services.pdf_service import PdfDocumentModel
from app.ui.components.page_preview import PagePreview
from app.ui.components.reader_splitter import ReaderSplitter
from app.ui.components.thumbnail_rail import ThumbnailRail
from app.ui.theme import BORDER_STRONG

logger = get_logger(__name__)

_DEFAULT_SPLIT = [360, 620]


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


class _SearchSignals(QObject):
    done = Signal(int, object)  # generation, list[int] posições


class _SearchWorker(QRunnable):
    """Busca (em background) as posições cujo texto contém o termo normalizado."""

    def __init__(self, render_service: PdfRenderService,
                 entries: list[tuple[int, Path, int]], norm_query: str,
                 generation: int) -> None:
        super().__init__()
        self.render_service = render_service
        self.entries = entries
        self.norm_query = norm_query
        self.generation = generation
        self.signals = _SearchSignals()

    def run(self) -> None:
        matches = [
            pos for (pos, source_path, source_index) in self.entries
            if self.render_service.page_contains(source_path, source_index, self.norm_query)
        ]
        self.signals.done.emit(self.generation, matches)


class PdfCleanerView(QWidget):
    def __init__(self, job_manager: JobManager, render_service: PdfRenderService,
                 settings: Settings) -> None:
        super().__init__()
        self.job_manager = job_manager
        self.render_service = render_service
        self.settings = settings
        self.model: PdfDocumentModel | None = None
        self._active_job_id: str | None = None

        self._matches: list[int] = []
        self._match_idx: int = -1
        self._search_gen: int = 0

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

        self._build_toolbar(root)
        self._build_search_bar(root)

        self.info = QLabel("Abra um PDF ou arraste um arquivo para esta janela.")
        self.info.setProperty("cssClass", "info")
        root.addWidget(self.info)

        # Trilha (esquerda) + painel de leitura (direita), separados por um
        # divisor arrastável e redimensionável (proporção persistida em settings).
        self.rail = ThumbnailRail(self.render_service)
        self.rail.focus_changed.connect(self._on_focus_changed)
        self.rail.selection_changed.connect(self._on_selection_changed)

        self.preview = PagePreview(self.render_service)
        self.preview.selection_toggled.connect(self._on_preview_toggled)

        self.splitter = ReaderSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.rail)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.rail.setMinimumWidth(300)
        self.preview.setMinimumWidth(320)
        self._restore_split()
        self.splitter.splitterMoved.connect(lambda *_: self._save_split_timer.start())
        self.splitter.reset_requested.connect(self._reset_split)
        root.addWidget(self.splitter, 1)

        self._save_split_timer = QTimer(self)
        self._save_split_timer.setSingleShot(True)
        self._save_split_timer.setInterval(400)
        self._save_split_timer.timeout.connect(self._save_split)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setProperty("cssClass", "console")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(80)
        self.log.setPlaceholderText("Registro de operações…")
        root.addWidget(self.log)

        # Debounce da busca por texto.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._run_search)

    def _build_toolbar(self, root: QVBoxLayout) -> None:
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
        for b in (self.btn_rot_l, self.btn_rot_r, self.btn_remove,
                  self.btn_extract, self.btn_split):
            row2.addWidget(b)
        row2.addWidget(self._divider())
        self.btn_undo = self._btn("↶ Desfazer", self.undo)
        self.btn_redo = self._btn("↷ Refazer", self.redo)
        row2.addWidget(self.btn_undo)
        row2.addWidget(self.btn_redo)
        row2.addStretch(1)
        root.addLayout(row2)

    def _build_search_bar(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎 Buscar nas páginas…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda _: self._search_timer.start())
        self.search_input.returnPressed.connect(self._next_match)
        row.addWidget(self.search_input, 1)

        self.search_count = QLabel("")
        self.search_count.setProperty("cssClass", "caption")
        self.search_count.setMinimumWidth(120)
        row.addWidget(self.search_count)

        self.btn_prev_match = self._btn("‹", self._prev_match, "icon")
        self.btn_next_match = self._btn("›", self._next_match, "icon")
        self.btn_prev_match.setToolTip("Resultado anterior")
        self.btn_next_match.setToolTip("Próximo resultado")
        self.btn_prev_match.setFixedWidth(38)
        self.btn_next_match.setFixedWidth(38)
        self.btn_select_matches = self._btn("Selecionar achadas", self._select_matches)
        row.addWidget(self.btn_prev_match)
        row.addWidget(self.btn_next_match)
        row.addWidget(self.btn_select_matches)
        root.addLayout(row)

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

    # --- divisor (persistência) ---
    def _restore_split(self) -> None:
        sizes = self.settings.pdf_cleaner_split_sizes
        self.splitter.setSizes(list(sizes) if len(sizes) == 2 else _DEFAULT_SPLIT)

    def _save_split(self) -> None:
        sizes = self.splitter.sizes()
        if len(sizes) == 2 and all(s > 0 for s in sizes):
            self.settings.pdf_cleaner_split_sizes = sizes
            save_settings(self.settings)

    def _reset_split(self) -> None:
        self.splitter.setSizes(_DEFAULT_SPLIT)
        self._save_split()

    # --- carregamento ---
    def open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir PDF", "", "PDF (*.pdf)")
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
        self.search_input.clear()
        self.rail.set_pages(self.model.pages)  # foca a 1ª página → abre no preview
        self._update_actions()

    def merge_pdf(self) -> None:
        if not self._require_model():
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
        self._refresh()

    # --- edição ---
    def _require_model(self) -> bool:
        if self.model is None:
            self._load_prompt()
            return False
        return True

    def _require_selection(self) -> set[int] | None:
        if not self._require_model():
            return None
        sel = self.rail.selected_positions()
        if not sel:
            self._log("Nenhuma página selecionada (marque o checkbox das páginas).")
            return None
        return sel

    def remove_selected(self) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.remove_pages(sel)
        self._log(f"Removidas {len(sel)} página(s).")
        self._refresh()

    def extract_selected(self) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.keep_only(sel)
        self._log(f"Mantidas apenas {len(sel)} página(s) selecionada(s).")
        self._refresh()

    def rotate(self, delta: int) -> None:
        sel = self._require_selection()
        if sel is None:
            return
        self.model.rotate_pages(sel, delta)
        self._log(f"Giradas {len(sel)} página(s) em {delta}°.")
        self._refresh(keep_selection=sel)

    def select_range(self) -> None:
        if not self._require_model():
            return
        text, ok = QInputDialog.getText(
            self, "Selecionar intervalo", "Páginas (ex.: 1-5, 8, 10-12):"
        )
        if not ok or not text.strip():
            return
        n = len(self.model.pages)
        positions: set[int] = set()
        for start, end in parse_ranges(text, n):
            positions.update(range(start - 1, end))  # 1-based → posição 0-based
        self.rail.select_positions(positions)
        self._log(f"Selecionadas {len(positions)} página(s) por intervalo.")

    def detect_blanks(self) -> None:
        if not self._require_model():
            return
        try:
            blanks = pdf_service.detect_blank_pages(self.model.primary_path)
        except Exception as exc:  # noqa: BLE001
            self._error("Falha ao detectar páginas em branco.", str(exc))
            return
        blank_set = set(blanks)
        positions = {
            pos for pos, p in enumerate(self.model.pages)
            if p.source_path == self.model.primary_path and p.source_index in blank_set
        }
        if not positions:
            self._log("Nenhuma página em branco detectada.")
            return
        self.rail.select_positions(positions)
        self._log(f"{len(positions)} possível(is) página(s) em branco selecionada(s). "
                  "Revise antes de remover.")

    def undo(self) -> None:
        if self.model and self.model.can_undo:
            self.model.undo()
            self._log("Desfazer.")
            self._refresh()

    def redo(self) -> None:
        if self.model and self.model.can_redo:
            self.model.redo()
            self._log("Refazer.")
            self._refresh()

    # --- busca por texto ---
    def _run_search(self) -> None:
        if self.model is None:
            return
        query = self.search_input.text().strip()
        self._search_gen += 1
        if not query:
            self._matches = []
            self._match_idx = -1
            self.rail.set_matches(set())
            self.search_count.setText("")
            self._update_search_nav()
            return
        entries = [
            (pos, p.source_path, p.source_index)
            for pos, p in enumerate(self.model.pages)
        ]
        worker = _SearchWorker(self.render_service, entries, normalize_text(query),
                               self._search_gen)
        worker.signals.done.connect(self._on_search_done)
        self.search_count.setText("buscando…")
        QThreadPool.globalInstance().start(worker)

    def _on_search_done(self, generation: int, matches: list[int]) -> None:
        if generation != self._search_gen:
            return
        self._matches = matches
        self.rail.set_matches(set(matches))
        self.search_count.setText(
            f"{len(matches)} encontrada(s)" if matches else "nenhuma encontrada")
        self._match_idx = -1
        if matches:
            self._go_to_match(0)
        self._update_search_nav()

    def _go_to_match(self, idx: int) -> None:
        if not self._matches:
            return
        self._match_idx = idx % len(self._matches)
        self.rail.set_focus(self._matches[self._match_idx])
        self.search_count.setText(
            f"{self._match_idx + 1} de {len(self._matches)}")

    def _next_match(self) -> None:
        if self._matches:
            self._go_to_match(self._match_idx + 1)

    def _prev_match(self) -> None:
        if self._matches:
            self._go_to_match(self._match_idx - 1)

    def _select_matches(self) -> None:
        if not self._matches:
            return
        self.rail.select_positions(self.rail.selected_positions() | set(self._matches))
        self._log(f"{len(self._matches)} página(s) da busca adicionadas à seleção.")

    def _update_search_nav(self) -> None:
        has = bool(self._matches)
        for b in (self.btn_prev_match, self.btn_next_match, self.btn_select_matches):
            b.setEnabled(has)

    # --- preview / seleção ---
    def _on_focus_changed(self, position: int) -> None:
        if self.model is None or not (0 <= position < len(self.model.pages)):
            return
        pref = self.model.pages[position]
        self.preview.set_page(pref, position, position in self.rail.selected_positions())

    def _on_preview_toggled(self, position: int, checked: bool) -> None:
        self.rail.set_selected(position, checked)

    def _on_selection_changed(self, count: int) -> None:
        focused = self.rail.focused_position()
        if focused is not None:
            self.preview.set_selected(focused in self.rail.selected_positions())
        self._update_actions()

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
        self._start_job(SavePdfJob(self.model, out, overwrite=overwrite))

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
        self._start_job(SplitPdfJob(self.model.primary_path, ranges, out_dir))

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
            self.progress.setRange(0, 0)
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
    def _refresh(self, keep_selection: set[int] | None = None) -> None:
        if self.model is None:
            return
        prev_focus = self.rail.focused_position()
        self.rail.set_pages(self.model.pages)
        if keep_selection:
            self.rail.select_positions(
                {p for p in keep_selection if p < len(self.model.pages)})
        if self.model.pages:
            restore = prev_focus if (prev_focus is not None
                                     and prev_focus < len(self.model.pages)) else 0
            self.rail.set_focus(restore)
        else:
            self.preview.clear()
        self.info.setText(f"{self.model.primary_path.name} — "
                          f"{len(self.model.pages)} páginas")
        if self.search_input.text().strip():
            self._run_search()
        self._update_actions()

    def _set_busy(self, busy: bool) -> None:
        for b in (self.btn_open, self.btn_add, self.btn_remove, self.btn_extract,
                  self.btn_rot_l, self.btn_rot_r, self.btn_split, self.btn_save):
            b.setEnabled(not busy)

    def _update_actions(self) -> None:
        has_model = self.model is not None
        has_pages = has_model and bool(self.model.pages)
        has_sel = has_model and bool(self.rail.selected_positions())
        for b in (self.btn_add, self.btn_range, self.btn_blank, self.btn_split):
            b.setEnabled(has_model)
        for b in (self.btn_remove, self.btn_extract, self.btn_rot_l, self.btn_rot_r):
            b.setEnabled(has_sel)
        self.search_input.setEnabled(has_model)
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
