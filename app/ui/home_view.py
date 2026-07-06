"""Tela inicial orientada por tarefas (Seção 7).

Cartões grandes representam tarefas, não formatos. O usuário escolhe primeiro
"o que quer fazer".
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import ACCENT_SOFT, TEXT_MUTED

# (ícone, título, descrição, chave de navegação, ativo?)
TASKS = [
    ("✂️", "Limpar PDF", "Remover páginas, dividir, juntar, extrair e girar.",
     "pdf_cleaner", True),
    ("📄", "Preparar documento para IA",
     "Converter PDF/EPUB/documentos para Markdown, TXT e pacotes para LLMs.",
     "document_prep", False),
    ("🔎", "OCR", "Transformar PDF escaneado ou imagem em texto e PDF pesquisável.",
     "ocr", False),
    ("🎙️", "Transcrever áudio/vídeo", "Gerar texto limpo a partir de áudio ou vídeo.",
     "transcription", False),
    ("📚", "Lote", "Aplicar operações a vários arquivos.", "batch", False),
    ("⚙️", "Configurações", "Verificar dependências, idiomas, modelos e backends.",
     "settings", True),
]


class TaskCard(QFrame):
    def __init__(self, icon: str, title: str, desc: str,
                 on_click: Callable[[], None], enabled: bool) -> None:
        super().__init__()
        self.setProperty("cssClass", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled
                       else Qt.CursorShape.ArrowCursor)
        self.setMinimumHeight(178)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        icon_badge = QLabel(icon)
        icon_badge.setFixedSize(44, 44)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            f"background: {ACCENT_SOFT}; border-radius: 12px; font-size: 20px;"
        )

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 8px;")
        title_lbl.setWordWrap(True)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setProperty("cssClass", "subtitle")

        layout.addWidget(icon_badge)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch(1)

        btn = QPushButton("Abrir" if enabled else "Em breve")
        btn.setEnabled(enabled)
        if enabled:
            btn.setProperty("cssClass", "primary")
        btn.clicked.connect(lambda: on_click())
        layout.addWidget(btn)

        if not enabled:
            self.setStyleSheet(f"QFrame {{ border-style: dashed; }}"
                               f"QLabel {{ color: {TEXT_MUTED}; }}")


class HomeView(QScrollArea):
    def __init__(self, on_navigate: Callable[[str], None]) -> None:
        super().__init__()
        self._on_navigate = on_navigate
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(36, 32, 36, 32)
        outer.setSpacing(4)

        heading = QLabel("O que você quer preparar para IA?")
        heading.setProperty("cssClass", "heading")
        subtitle = QLabel(
            "Transforme material bruto em fontes limpas para NotebookLM, ChatGPT, "
            "Claude, Gemini e ferramentas similares. Tudo local e offline."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setStyleSheet("margin-bottom: 12px;")

        outer.addWidget(heading)
        outer.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)
        for idx, (icon, title, desc, key, enabled) in enumerate(TASKS):
            card = TaskCard(icon, title, desc, lambda k=key: self._on_navigate(k), enabled)
            grid.addWidget(card, idx // 3, idx % 3)
        outer.addLayout(grid)
        outer.addStretch(1)

        self.setWidget(content)
