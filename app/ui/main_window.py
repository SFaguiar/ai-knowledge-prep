"""Janela principal — navegação orientada por tarefas (Seção 7).

Uma barra lateral leva às tarefas; o conteúdo central troca via QStackedWidget.
A barra é **colapsável** (modo só-ícones) para dar mais espaço aos módulos; o
estado é persistido. A janela cria os serviços compartilhados (JobManager,
render service) e os injeta nas views, mantendo baixo acoplamento.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.settings import load_settings, save_settings
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

# (emoji, rótulo, chave de navegação)
NAV_ITEMS = [
    ("🏠", "Início", "home"),
    ("✂️", "Limpar PDF", "pdf_cleaner"),
    ("📄", "Documento para IA", "document_prep"),
    ("🔎", "OCR", "ocr"),
    ("🎙️", "Transcrever áudio/vídeo", "transcription"),
    ("📚", "Lote", "batch"),
    ("🕘", "Histórico", "history"),
    ("⚙️", "Configurações", "settings"),
]

_SIDEBAR_EXPANDED = 248
_SIDEBAR_COLLAPSED = 60


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Knowledge Prep Suite")
        self.resize(1180, 760)

        self.settings = load_settings()
        self.job_manager = JobManager()
        self.render_service = PdfRenderService()

        self._views: dict[str, QWidget] = {}
        self._collapsed = bool(self.settings.sidebar_collapsed)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- barra lateral: alternador + marca + navegação ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(10, 12, 10, 4)
        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("sidebarToggle")
        self.btn_toggle.setFixedSize(38, 32)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        toggle_row.addWidget(self.btn_toggle)
        toggle_row.addStretch(1)
        sidebar_layout.addLayout(toggle_row)

        self.brand = QLabel("AI Knowledge\nPrep Suite")
        self.brand.setProperty("cssClass", "sectionTitle")
        self.brand.setStyleSheet("padding: 6px 20px 4px 20px;")
        self.brand_sub = QLabel("Local-first • Offline")
        self.brand_sub.setProperty("cssClass", "caption")
        self.brand_sub.setStyleSheet("padding: 0 20px 16px 20px;")

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for _emoji, label, key in NAV_ITEMS:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(label)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        sidebar_layout.addWidget(self.brand)
        sidebar_layout.addWidget(self.brand_sub)
        sidebar_layout.addWidget(self.nav, 1)

        # Animação suave de largura (recolher/expandir).
        self._sidebar_anim = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            anim = QPropertyAnimation(self.sidebar, prop, self)
            anim.setDuration(160)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim.addAnimation(anim)
        self._sidebar_anim.finished.connect(self._on_anim_finished)

        # --- pilha de conteúdo ---
        self.stack = QStackedWidget()
        self._register_views()

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.addWidget(QLabel("🔒 Local-first  •  Offline  •  Sem telemetria"))
        self.setStatusBar(status)

        # Aplica o estado inicial (sem animar) e seleciona o Início.
        self._apply_sidebar_state(self._collapsed, animate=False)
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
        for _, _, key in NAV_ITEMS:
            self.stack.addWidget(self._views[key])

    # --- barra lateral colapsável ---
    def toggle_sidebar(self) -> None:
        self._apply_sidebar_state(not self._collapsed, animate=True)
        self.settings.sidebar_collapsed = self._collapsed
        save_settings(self.settings)

    def _apply_sidebar_state(self, collapsed: bool, animate: bool) -> None:
        self._collapsed = collapsed
        target = _SIDEBAR_COLLAPSED if collapsed else _SIDEBAR_EXPANDED

        # Conteúdo: marca oculta e itens só-ícone quando recolhido.
        self.brand.setVisible(not collapsed)
        self.brand_sub.setVisible(not collapsed)
        self.btn_toggle.setText("»" if collapsed else "«")
        self.btn_toggle.setToolTip("Expandir menu" if collapsed else "Recolher menu")
        for row, (emoji, label, _key) in enumerate(NAV_ITEMS):
            item = self.nav.item(row)
            item.setText(emoji if collapsed else f"{emoji}   {label}")
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter if collapsed
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        if animate:
            self._sidebar_anim.stop()
            start = self.sidebar.width()
            for anim in self._child_anims():
                anim.setStartValue(start)
                anim.setEndValue(target)
            self._sidebar_anim.start()
        else:
            self.sidebar.setFixedWidth(target)

    def _child_anims(self):
        return (
            self._sidebar_anim.animationAt(i)
            for i in range(self._sidebar_anim.animationCount())
        )

    def _on_anim_finished(self) -> None:
        # Fixa a largura final para estabilidade do layout.
        self.sidebar.setFixedWidth(_SIDEBAR_COLLAPSED if self._collapsed
                                   else _SIDEBAR_EXPANDED)

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < len(NAV_ITEMS):
            key = NAV_ITEMS[row][2]
            self.stack.setCurrentWidget(self._views[key])

    def navigate_to(self, key: str) -> None:
        for row, (_, _, k) in enumerate(NAV_ITEMS):
            if k == key:
                self.nav.setCurrentRow(row)
                return

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.render_service.close_all()
        self.job_manager.wait_for_done(2000)
        super().closeEvent(event)
