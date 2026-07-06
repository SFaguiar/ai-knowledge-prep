"""Tela de Configurações e Dependências (Seções 12 e 13).

Mostra, por módulo funcional, o estado de cada dependência (Python ou binário),
com versão/caminho quando disponível, e classificação de criticidade. A checagem
roda em background para não travar a UI.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
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

_BADGE = {
    Criticality.REQUIRED: ("#d9534f", "#fff"),
    Criticality.RECOMMENDED: ("#f0ad4e", "#fff"),
    Criticality.OPTIONAL: ("#5bc0de", "#fff"),
    Criticality.EXPERIMENTAL: ("#777", "#fff"),
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
        outer.setContentsMargins(28, 24, 28, 24)

        header = QLabel("Configurações & Dependências")
        header.setStyleSheet("font-size: 22px; font-weight: 700;")
        outer.addWidget(header)

        info = QLabel(
            f"Idioma OCR padrão: {settings.default_ocr_language}  •  "
            f"Idioma transcrição: {settings.default_transcription_language}  •  "
            f"Telemetria: {'desativada' if not settings.telemetry_enabled else 'ATIVA'}"
        )
        info.setStyleSheet("color: #666; font-size: 13px;")
        outer.addWidget(info)

        self.refresh_btn = QPushButton("Verificar dependências")
        self.refresh_btn.clicked.connect(self.refresh)
        outer.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)

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
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 8, 0, 8)

        status_icon = "✅" if report.ok else "⚠️"
        title = QLabel(f"{status_icon}  {report.module_group}")
        title.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 6px;")
        layout.addWidget(title)

        for status in report.statuses:
            layout.addWidget(self._build_row(status))
        return box

    def _build_row(self, status: DependencyStatus) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(14, 2, 4, 2)
        layout.setSpacing(0)

        mark = "OK" if status.available else "Ausente"
        color = "#2e7d32" if status.available else "#b71c1c"
        crit = status.spec.criticality.value

        line = QLabel(
            f"<span style='color:{color}; font-weight:600'>[{mark}]</span> "
            f"{status.spec.display_name} "
            f"<span style='color:#999'>· {crit}</span>"
            + (f"  <span style='color:#888'>({status.version})</span>"
               if status.version else "")
        )
        line.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(line)

        if status.spec.notes and not status.available:
            note = QLabel(status.spec.notes)
            note.setStyleSheet("color:#999; font-size:11px; margin-left:22px;")
            layout.addWidget(note)
        return row
