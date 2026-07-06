"""Grade de miniaturas de páginas com seleção (Módulo 1).

Renderiza cada página do `PdfDocumentModel` como um cartão selecionável. A
renderização das imagens ocorre em background (QRunnable) para não travar a UI;
cada miniatura é atualizada assim que fica pronta.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.pdf_render_service import PdfRenderService
from app.services.pdf_service import PageRef
from app.ui.theme import ACCENT, ACCENT_SOFT, BG_ELEVATED, BG_ELEVATED_HOVER, BORDER, TEXT_MUTED, TEXT_SECONDARY

_COLUMNS = 4
_THUMB_DIM = 200


class _ThumbSignals(QObject):
    ready = Signal(int, bytes)  # position, png bytes
    failed = Signal(int, str)


class _ThumbWorker(QRunnable):
    """Renderiza uma lista de páginas e emite cada miniatura ao ficar pronta."""

    def __init__(self, render_service: PdfRenderService,
                 pages: list[tuple[int, PageRef]], generation: int) -> None:
        super().__init__()
        self.render_service = render_service
        self.pages = pages
        self.generation = generation
        self.signals = _ThumbSignals()
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
                self.signals.ready.emit(position, png)
            except Exception as exc:  # noqa: BLE001
                self.signals.failed.emit(position, str(exc))


class PageThumbnail(QFrame):
    def __init__(self, position: int, pref: PageRef,
                 on_toggle) -> None:
        super().__init__()
        self.position = position
        self._selected = False
        self._on_toggle = on_toggle

        self.setObjectName("thumb")
        self.setFixedSize(_THUMB_DIM + 24, _THUMB_DIM + 60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image = QLabel("carregando…")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedHeight(_THUMB_DIM)
        self.image.setStyleSheet(f"color:{TEXT_MUTED}; border: none;")

        # Rótulo: posição atual (1-based) e página original.
        self.caption = QLabel(f"#{position + 1}  ·  orig. p.{pref.source_index + 1}")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setStyleSheet(f"font-size: 11px; color:{TEXT_SECONDARY}; border: none;")

        layout.addWidget(self.image)
        layout.addWidget(self.caption)
        self._apply_style()

    def set_pixmap(self, png: bytes) -> None:
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.image.setText("")
        self.image.setPixmap(pix)

    def set_failed(self) -> None:
        self.image.setText("⚠ erro")

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._selected = not self._selected
        self._apply_style()
        self._on_toggle(self.position, self._selected)
        super().mousePressEvent(event)

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"#thumb {{ background:{ACCENT_SOFT}; border:2px solid {ACCENT};"
                f" border-radius:10px; }}"
            )
        else:
            self.setStyleSheet(
                f"#thumb {{ background:{BG_ELEVATED}; border:1px solid {BORDER};"
                f" border-radius:10px; }}"
                f"#thumb:hover {{ background:{BG_ELEVATED_HOVER}; }}"
            )


class ThumbnailGrid(QScrollArea):
    """Área rolável com a grade de miniaturas."""

    selection_changed = Signal(int)  # nº de páginas selecionadas

    def __init__(self, render_service: PdfRenderService) -> None:
        super().__init__()
        self.render_service = render_service
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self._container)

        self._thumbs: list[PageThumbnail] = []
        self._selected: set[int] = set()
        self._generation = 0
        self._worker: _ThumbWorker | None = None

    def set_pages(self, pages: list[PageRef]) -> None:
        # Cancela renderização anterior.
        self._generation += 1
        if self._worker is not None:
            self._worker.cancel()
        self._clear()
        self._selected.clear()

        for position, pref in enumerate(pages):
            thumb = PageThumbnail(position, pref, self._on_toggle)
            self._thumbs.append(thumb)
            self._grid.addWidget(thumb, position // _COLUMNS, position % _COLUMNS)

        self.selection_changed.emit(0)

        if not pages:
            return

        worker = _ThumbWorker(
            self.render_service, list(enumerate(pages)), self._generation
        )
        gen = self._generation
        worker.signals.ready.connect(
            lambda pos, png, g=gen: self._on_thumb_ready(pos, png, g)
        )
        worker.signals.failed.connect(
            lambda pos, _err, g=gen: self._on_thumb_failed(pos, g)
        )
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    def selected_positions(self) -> set[int]:
        return set(self._selected)

    def select_positions(self, positions: set[int]) -> None:
        for thumb in self._thumbs:
            sel = thumb.position in positions
            thumb.set_selected(sel)
        self._selected = {p for p in positions if 0 <= p < len(self._thumbs)}
        self.selection_changed.emit(len(self._selected))

    def clear_selection(self) -> None:
        self.select_positions(set())

    def _on_toggle(self, position: int, selected: bool) -> None:
        if selected:
            self._selected.add(position)
        else:
            self._selected.discard(position)
        self.selection_changed.emit(len(self._selected))

    def _on_thumb_ready(self, position: int, png: bytes, generation: int) -> None:
        if generation != self._generation:
            return
        if 0 <= position < len(self._thumbs):
            self._thumbs[position].set_pixmap(png)

    def _on_thumb_failed(self, position: int, generation: int) -> None:
        if generation != self._generation:
            return
        if 0 <= position < len(self._thumbs):
            self._thumbs[position].set_failed()

    def _clear(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._thumbs.clear()
