"""Tela de Configurações e Dependências (Seções 12 e 13).

Mostra, por módulo funcional, o estado de cada dependência (Python ou binário),
com versão/caminho quando disponível, e classificação de criticidade. A checagem
roda em background para não travar a UI.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.dependency_checker import (
    Criticality,
    DependencyStatus,
    ModuleReport,
    check_all,
)
from app.infrastructure.settings import Settings
from app.ui.theme import DANGER, SUCCESS, TEXT_MUTED, WARNING

_CRIT_COLOR = {
    Criticality.REQUIRED: DANGER,
    Criticality.RECOMMENDED: WARNING,
    Criticality.OPTIONAL: "#5bc0de",
    Criticality.EXPERIMENTAL: TEXT_MUTED,
}


class _CheckSignals(QObject):
    done = Signal(object)  # list[ModuleReport]


class _CheckWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = _CheckSignals()

    def run(self) -> None:
        reports = check_all()
        self.signals.done.emit(reports)


class SettingsView(QWidget):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(8)

        header = QLabel("Configurações & Dependências")
        header.setProperty("cssClass", "heading")
        outer.addWidget(header)

        info = QLabel(
            f"Idioma OCR padrão: {settings.default_ocr_language}  •  "
            f"Idioma transcrição: {settings.default_transcription_language}  •  "
            f"Telemetria: {'desativada' if not settings.telemetry_enabled else 'ATIVA'}"
        )
        info.setProperty("cssClass", "subtitle")
        outer.addWidget(info)

        self.refresh_btn = QPushButton("🔄  Verificar dependências")
        self.refresh_btn.setProperty("cssClass", "primary")
        self.refresh_btn.clicked.connect(self.refresh)
        outer.addSpacing(4)
        outer.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        outer.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

        # Mantém referência ao worker ativo para evitar coleta prematura pelo GC
        # (o QThreadPool detém o QRunnable em C++, mas o objeto de sinais é Python).
        self._worker: _CheckWorker | None = None
        self.refresh()

    def refresh(self) -> None:
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Verificando...")
        self._clear()
        self._content_layout.addWidget(QLabel("Analisando ambiente..."))

        worker = _CheckWorker()
        worker.signals.done.connect(self._on_done)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_done(self, reports: list[ModuleReport]) -> None:
        self._clear()
        for report in reports:
            self._content_layout.addWidget(self._build_group(report))
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Verificar dependências")

    def _clear(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _build_group(self, report: ModuleReport) -> QWidget:
        card = QFrame()
        card.setProperty("cssClass", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        status_icon = "✅" if report.ok else "⚠️"
        title = QLabel(f"{status_icon}  {report.module_group}")
        title.setProperty("cssClass", "sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)

        for status in report.statuses:
            layout.addWidget(self._build_row(status))

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 14)
        wrapper_layout.addWidget(card)
        return wrapper

    def _build_row(self, status: DependencyStatus) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(6, 6, 4, 6)
        layout.setSpacing(0)

        dot_color = SUCCESS if status.available else _CRIT_COLOR[status.spec.criticality]
        mark = "OK" if status.available else "Ausente"
        crit = status.spec.criticality.value

        line = QLabel(
            f"<span style='color:{dot_color}; font-weight:700'>●</span>  "
            f"<b>{status.spec.display_name}</b> "
            f"<span style='color:{dot_color}'>{mark}</span> "
            f"<span style='color:{TEXT_MUTED}'>· {crit}</span>"
            + (f"  <span style='color:{TEXT_MUTED}'>({status.version})</span>"
               if status.version else "")
        )
        line.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(line)

        if status.spec.notes and not status.available:
            note = QLabel(status.spec.notes)
            note.setProperty("cssClass", "caption")
            note.setStyleSheet("margin-left: 20px;")
            layout.addWidget(note)
        return row
