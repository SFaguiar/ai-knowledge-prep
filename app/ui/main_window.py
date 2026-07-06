"""Janela principal — navegação orientada por tarefas (Seção 7).

Uma barra lateral leva às tarefas; o conteúdo central troca via QStackedWidget.
A janela cria os serviços compartilhados (JobManager, render service) e os injeta
nas views, mantendo baixo acoplamento.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.settings import load_settings
from app.jobs.job_manager import JobManager
from app.services.pdf_render_service import PdfRenderService
from app.ui.batch_view import BatchView
from app.ui.document_prep_view import DocumentPrepView
from app.ui.history_view import HistoryView
from app.ui.home_view import HomeView
from app.ui.ocr_view import OcrView
from app.ui.pdf_cleaner_view import PdfCleanerView
from app.ui.settings_view import SettingsView
from app.ui.transcription_view import TranscriptionView

# (título da tarefa, subtítulo)
NAV_ITEMS = [
    ("🏠   Início", "home"),
    ("✂️   Limpar PDF", "pdf_cleaner"),
    ("📄   Documento para IA", "document_prep"),
    ("🔎   OCR", "ocr"),
    ("🎙️   Transcrever áudio/vídeo", "transcription"),
    ("📚   Lote", "batch"),
    ("🕘   Histórico", "history"),
    ("⚙️   Configurações", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Knowledge Prep Suite")
        self.resize(1180, 760)

        self.settings = load_settings()
        self.job_manager = JobManager()
        self.render_service = PdfRenderService()

        self._views: dict[str, QWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- barra lateral: marca + navegação ---
        sidebar = QWidget()
        sidebar.setFixedWidth(248)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        brand = QLabel("AI Knowledge\nPrep Suite")
        brand.setProperty("cssClass", "sectionTitle")
        brand.setStyleSheet("padding: 20px 20px 4px 20px;")
        brand_sub = QLabel("Local-first • Offline")
        brand_sub.setProperty("cssClass", "caption")
        brand_sub.setStyleSheet("padding: 0 20px 16px 20px;")

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for label, key in NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(brand_sub)
        sidebar_layout.addWidget(self.nav, 1)

        # --- pilha de conteúdo ---
        self.stack = QStackedWidget()

        self._register_views()

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.addWidget(QLabel("🔒 Local-first  •  Offline  •  Sem telemetria"))
        self.setStatusBar(status)

        self.nav.setCurrentRow(0)

    def _register_views(self) -> None:
        home = HomeView(on_navigate=self.navigate_to)
        pdf_cleaner = PdfCleanerView(
            job_manager=self.job_manager,
            render_service=self.render_service,
            settings=self.settings,
        )
        document_prep = DocumentPrepView(
            job_manager=self.job_manager,
            settings=self.settings,
        )
        ocr = OcrView()
        transcription = TranscriptionView()
        batch = BatchView()
        history = HistoryView()
        settings_view = SettingsView(settings=self.settings)

        self._views = {
            "home": home,
            "pdf_cleaner": pdf_cleaner,
            "document_prep": document_prep,
            "ocr": ocr,
            "transcription": transcription,
            "batch": batch,
            "history": history,
            "settings": settings_view,
        }
        for _, key in NAV_ITEMS:
            self.stack.addWidget(self._views[key])

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < len(NAV_ITEMS):
            key = NAV_ITEMS[row][1]
            self.stack.setCurrentWidget(self._views[key])

    def navigate_to(self, key: str) -> None:
        for row, (_, k) in enumerate(NAV_ITEMS):
            if k == key:
                self.nav.setCurrentRow(row)
                return

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.render_service.close_all()
        self.job_manager.wait_for_done(2000)
        super().closeEvent(event)
