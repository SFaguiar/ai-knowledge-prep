"""Painel de leitura do PDF Cleaner (layout de leitor).

Mostra a página em foco em tamanho grande e legível, ajustada à largura do
painel (com zoom manual e rolagem). Um checkbox no cabeçalho reflete e alterna
a seleção da página em foco, para marcar sem sair da leitura. O render ocorre em
background, com um contador de geração que descarta renders obsoletos quando o
foco muda rápido (ex.: navegação por teclado).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.pdf_render_service import PdfRenderService
from app.services.pdf_service import PageRef
from app.ui.theme import BG_INPUT, TEXT_MUTED, TEXT_SECONDARY

_ZOOM_MIN = 0.5
_ZOOM_MAX = 3.0
_ZOOM_STEP = 0.25


class _PreviewSignals(QObject):
    ready = Signal(int, bytes)   # generation, png
    failed = Signal(int, str)    # generation, mensagem


class _PreviewWorker(QRunnable):
    def __init__(self, render_service: PdfRenderService, pref: PageRef,
                 target_width: int, generation: int) -> None:
        super().__init__()
        self.render_service = render_service
        self.pref = pref
        self.target_width = target_width
        self.generation = generation
        self.signals = _PreviewSignals()

    def run(self) -> None:
        try:
            png = self.render_service.render_page(
                self.pref.source_path, self.pref.source_index,
                target_width=self.target_width, rotation=self.pref.rotation,
            )
            self.signals.ready.emit(self.generation, png)
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(self.generation, str(exc))


class PagePreview(QWidget):
    """Preview grande da página em foco, com zoom e seleção da página."""

    selection_toggled = Signal(int, bool)  # posição, selecionada?

    def __init__(self, render_service: PdfRenderService) -> None:
        super().__init__()
        self.render_service = render_service
        self._pref: PageRef | None = None
        self._position: int | None = None
        self._zoom = 1.0
        self._generation = 0

        self._build_ui()

        # Debounce para re-renderizar ao redimensionar o painel (ajuste à largura).
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._render)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.label = QLabel("Nenhuma página em foco")
        self.label.setStyleSheet(f"font-weight:600; color:{TEXT_SECONDARY};")
        header.addWidget(self.label)
        header.addStretch(1)

        self.check_select = QCheckBox("Selecionar")
        self.check_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_select.toggled.connect(self._on_check_toggled)
        self.check_select.setEnabled(False)
        header.addWidget(self.check_select)

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setProperty("cssClass", "icon")
        self.btn_zoom_out.setToolTip("Diminuir zoom")
        self.btn_zoom_out.clicked.connect(lambda: self._change_zoom(-_ZOOM_STEP))
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setProperty("cssClass", "icon")
        self.btn_zoom_in.setToolTip("Aumentar zoom")
        self.btn_zoom_in.clicked.connect(lambda: self._change_zoom(+_ZOOM_STEP))
        self.btn_fit = QPushButton("Ajustar")
        self.btn_fit.clicked.connect(self._reset_zoom)
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_fit):
            b.setEnabled(False)
            header.addWidget(b)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background:{BG_INPUT}; border-radius:10px; }}")
        self.image = QLabel("Clique numa página na trilha para lê-la aqui.")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet(f"color:{TEXT_MUTED}; background:{BG_INPUT};")
        self.scroll.setWidget(self.image)
        root.addWidget(self.scroll, 1)

    # --- API pública ---
    def set_page(self, pref: PageRef, position: int, selected: bool) -> None:
        self._pref = pref
        self._position = position
        self.label.setText(f"Página #{position + 1}  ·  original p.{pref.source_index + 1}")
        self.check_select.setEnabled(True)
        self.check_select.blockSignals(True)
        self.check_select.setChecked(selected)
        self.check_select.blockSignals(False)
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_fit):
            b.setEnabled(True)
        self._render()

    def clear(self) -> None:
        self._pref = None
        self._position = None
        self._generation += 1
        self.label.setText("Nenhuma página em foco")
        self.image.setPixmap(QPixmap())
        self.image.setText("Clique numa página na trilha para lê-la aqui.")
        self.image.adjustSize()
        self.check_select.setEnabled(False)
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_fit):
            b.setEnabled(False)

    def set_selected(self, selected: bool) -> None:
        """Reflete a seleção da página em foco sem reemitir o sinal."""
        self.check_select.blockSignals(True)
        self.check_select.setChecked(selected)
        self.check_select.blockSignals(False)

    # --- zoom ---
    def _change_zoom(self, delta: float) -> None:
        self._zoom = max(_ZOOM_MIN, min(_ZOOM_MAX, self._zoom + delta))
        self._render()

    def _reset_zoom(self) -> None:
        self._zoom = 1.0
        self._render()

    def _on_check_toggled(self, checked: bool) -> None:
        if self._position is not None:
            self.selection_toggled.emit(self._position, checked)

    # --- render ---
    def _target_width(self) -> int:
        avail = max(300, self.scroll.viewport().width() - 24)
        return int(avail * self._zoom)

    def _render(self) -> None:
        if self._pref is None:
            return
        self._generation += 1
        worker = _PreviewWorker(
            self.render_service, self._pref, self._target_width(), self._generation
        )
        worker.signals.ready.connect(self._on_ready)
        worker.signals.failed.connect(self._on_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_ready(self, generation: int, png: bytes) -> None:
        if generation != self._generation:
            return
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.image.setPixmap(pix)
        self.image.setText("")
        self.image.resize(pix.size())

    def _on_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        self.image.setText("Não foi possível renderizar esta página.")

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self._pref is not None:
            self._resize_timer.start()
