"""Trilha de miniaturas do PDF Cleaner (layout de leitor).

Coluna vertical de cartões: cada página é uma miniatura com um checkbox de
seleção e uma legenda com as primeiras linhas do texto (quando o PDF tem camada
textual). A interação separa dois conceitos:

- **Foco** (clicar no corpo do cartão): abre a página no painel de leitura.
  Não altera a seleção. Emite `focus_changed`.
- **Seleção** (checkbox, ou tecla Espaço na página em foco): marca a página
  para as operações (remover, extrair, girar…). Emite `selection_changed`.

Miniaturas e trechos de texto são renderizados/extraídos em background para não
travar a UI.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.pdf_render_service import PdfRenderService
from app.services.pdf_service import PageRef
from app.ui.theme import (
    ACCENT,
    ACCENT_SOFT,
    BG_ELEVATED,
    BG_ELEVATED_HOVER,
    BORDER,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WARNING,
)

_THUMB_DIM = 150


class _RailSignals(QObject):
    thumb_ready = Signal(int, bytes)   # position, png
    snippet_ready = Signal(int, str)   # position, texto (vazio = sem texto)
    thumb_failed = Signal(int)


class _RailWorker(QRunnable):
    """Renderiza miniatura e extrai o trecho de texto de cada página."""

    def __init__(self, render_service: PdfRenderService,
                 pages: list[tuple[int, PageRef]]) -> None:
        super().__init__()
        self.render_service = render_service
        self.pages = pages
        self.signals = _RailSignals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        for position, pref in self.pages:
            if self._cancelled:
                return
            try:
                png = self.render_service.render_thumbnail(
                    pref.source_path, pref.source_index,
                    max_dim=_THUMB_DIM, rotation=pref.rotation,
                )
                self.signals.thumb_ready.emit(position, png)
            except Exception:  # noqa: BLE001
                self.signals.thumb_failed.emit(position)
            if self._cancelled:
                return
            try:
                snippet = self.render_service.page_snippet(
                    pref.source_path, pref.source_index
                )
                self.signals.snippet_ready.emit(position, snippet)
            except Exception:  # noqa: BLE001
                pass


class PageCard(QFrame):
    def __init__(self, position: int, pref: PageRef,
                 on_focus: Callable[[int], None],
                 on_toggle: Callable[[int, bool], None]) -> None:
        super().__init__()
        self.position = position
        self._focused = False
        self._match = False
        self._on_focus = on_focus

        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.toggled.connect(lambda checked: on_toggle(self.position, checked))
        check_col = QVBoxLayout()
        check_col.setContentsMargins(0, 0, 0, 0)
        check_col.addWidget(self.checkbox)
        check_col.addStretch(1)
        layout.addLayout(check_col)

        self.image = QLabel("…")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedSize(_THUMB_DIM, _THUMB_DIM)
        self.image.setStyleSheet(f"color:{TEXT_MUTED}; border:none;")
        layout.addWidget(self.image)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 2, 0, 2)
        text_col.setSpacing(4)
        self.caption = QLabel(f"#{position + 1}  ·  orig. p.{pref.source_index + 1}")
        self.caption.setStyleSheet(
            f"font-size:12px; font-weight:600; color:{TEXT_SECONDARY}; border:none;")
        self.snippet = QLabel("")
        self.snippet.setWordWrap(True)
        self.snippet.setStyleSheet(f"font-size:11px; color:{TEXT_MUTED}; border:none;")
        text_col.addWidget(self.caption)
        text_col.addWidget(self.snippet)
        text_col.addStretch(1)
        layout.addLayout(text_col, 1)

        self._apply_style()

    # --- estado visual ---
    def set_pixmap(self, png: bytes) -> None:
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.image.setText("")
        self.image.setPixmap(pix)

    def set_failed(self) -> None:
        self.image.setText("⚠")

    def set_snippet(self, text: str) -> None:
        if text:
            self.snippet.setText(text)
            self.snippet.setStyleSheet(f"font-size:11px; color:{TEXT_MUTED}; border:none;")
        else:
            self.snippet.setText("sem texto (imagem) — considere OCR")
            self.snippet.setStyleSheet(
                f"font-size:11px; color:{TEXT_MUTED}; font-style:italic; border:none;")

    @property
    def selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_selected(self, value: bool) -> None:
        # Bloqueia o sinal para não disparar callback ao ajustar programaticamente.
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(value)
        self.checkbox.blockSignals(False)

    def set_focused(self, value: bool) -> None:
        self._focused = value
        self._apply_style()

    def set_match(self, value: bool) -> None:
        self._match = value
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._on_focus(self.position)
        super().mousePressEvent(event)

    def _apply_style(self) -> None:
        if self._focused:
            border = f"2px solid {ACCENT}"
            bg = ACCENT_SOFT
        elif self._match:
            border = f"2px solid {WARNING}"
            bg = BG_ELEVATED
        else:
            border = f"1px solid {BORDER}"
            bg = BG_ELEVATED
        self.setStyleSheet(
            f"#card {{ background:{bg}; border:{border}; border-radius:10px; }}"
            f"#card:hover {{ background:{BG_ELEVATED_HOVER}; }}"
        )


class ThumbnailRail(QScrollArea):
    """Coluna rolável de páginas com foco (leitura) e seleção (checkbox)."""

    focus_changed = Signal(int)       # posição focada
    selection_changed = Signal(int)   # nº de páginas selecionadas

    def __init__(self, render_service: PdfRenderService) -> None:
        super().__init__()
        self.render_service = render_service
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._col = QVBoxLayout(self._container)
        self._col.setContentsMargins(8, 8, 8, 8)
        self._col.setSpacing(10)
        self._col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._container)

        self._cards: list[PageCard] = []
        self._selected: set[int] = set()
        self._focused: int | None = None
        self._worker: _RailWorker | None = None
        self._generation = 0

    # --- construção ---
    def set_pages(self, pages: list[PageRef]) -> None:
        self._generation += 1
        if self._worker is not None:
            self._worker.cancel()
        self._clear()
        self._selected.clear()
        self._focused = None

        for position, pref in enumerate(pages):
            card = PageCard(position, pref, self._on_focus, self._on_toggle)
            self._cards.append(card)
            self._col.addWidget(card)

        self.selection_changed.emit(0)
        if not pages:
            return

        worker = _RailWorker(self.render_service, list(enumerate(pages)))
        gen = self._generation
        worker.signals.thumb_ready.connect(
            lambda pos, png, g=gen: self._on_thumb_ready(pos, png, g))
        worker.signals.thumb_failed.connect(
            lambda pos, g=gen: self._on_thumb_failed(pos, g))
        worker.signals.snippet_ready.connect(
            lambda pos, text, g=gen: self._on_snippet_ready(pos, text, g))
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

        # Foca a primeira página automaticamente (abre o preview).
        self.set_focus(0)

    # --- seleção ---
    def selected_positions(self) -> set[int]:
        return set(self._selected)

    def select_positions(self, positions: set[int]) -> None:
        valid = {p for p in positions if 0 <= p < len(self._cards)}
        for card in self._cards:
            card.set_selected(card.position in valid)
        self._selected = valid
        self.selection_changed.emit(len(self._selected))

    def set_selected(self, position: int, value: bool) -> None:
        if 0 <= position < len(self._cards):
            self._cards[position].set_selected(value)
            if value:
                self._selected.add(position)
            else:
                self._selected.discard(position)
            self.selection_changed.emit(len(self._selected))

    def _on_toggle(self, position: int, checked: bool) -> None:
        if checked:
            self._selected.add(position)
        else:
            self._selected.discard(position)
        self.selection_changed.emit(len(self._selected))

    # --- foco ---
    def focused_position(self) -> int | None:
        return self._focused

    def set_focus(self, position: int) -> None:
        if not (0 <= position < len(self._cards)):
            return
        if self._focused is not None and self._focused < len(self._cards):
            self._cards[self._focused].set_focused(False)
        self._focused = position
        card = self._cards[position]
        card.set_focused(True)
        self.ensureWidgetVisible(card)
        self.focus_changed.emit(position)

    def _on_focus(self, position: int) -> None:
        self.setFocus()
        self.set_focus(position)

    # --- busca ---
    def set_matches(self, positions: set[int]) -> None:
        valid = {p for p in positions if 0 <= p < len(self._cards)}
        for card in self._cards:
            card.set_match(card.position in valid)

    # --- teclado ---
    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._cards or self._focused is None:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Right):
            self.set_focus(min(self._focused + 1, len(self._cards) - 1))
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Left):
            self.set_focus(max(self._focused - 1, 0))
        elif key == Qt.Key.Key_Space:
            card = self._cards[self._focused]
            self.set_selected(self._focused, not card.selected)
        else:
            super().keyPressEvent(event)

    # --- callbacks de background ---
    def _on_thumb_ready(self, position: int, png: bytes, generation: int) -> None:
        if generation == self._generation and 0 <= position < len(self._cards):
            self._cards[position].set_pixmap(png)

    def _on_thumb_failed(self, position: int, generation: int) -> None:
        if generation == self._generation and 0 <= position < len(self._cards):
            self._cards[position].set_failed()

    def _on_snippet_ready(self, position: int, text: str, generation: int) -> None:
        if generation == self._generation and 0 <= position < len(self._cards):
            self._cards[position].set_snippet(text)

    def _clear(self) -> None:
        while self._col.count():
            item = self._col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cards.clear()
