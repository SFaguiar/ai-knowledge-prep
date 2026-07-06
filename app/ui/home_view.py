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
    QVBoxLayout,
    QWidget,
)

# (título, descrição, chave de navegação, ativo?)
TASKS = [
    ("Limpar PDF", "Remover páginas, dividir, juntar, extrair e girar.",
     "pdf_cleaner", True),
    ("Preparar documento para IA",
     "Converter PDF/EPUB/documentos para Markdown, TXT e pacotes para LLMs.",
     "document_prep", False),
    ("OCR", "Transformar PDF escaneado ou imagem em texto e PDF pesquisável.",
     "ocr", False),
    ("Transcrever áudio/vídeo", "Gerar texto limpo a partir de áudio ou vídeo.",
     "transcription", False),
    ("Lote", "Aplicar operações a vários arquivos.", "batch", False),
    ("Histórico", "Consultar operações anteriores e abrir pastas de saída.",
     "history", False),
    ("Configurações", "Verificar dependências, idiomas, modelos e backends.",
     "settings", True),
]


class TaskCard(QFrame):
    def __init__(self, title: str, desc: str, on_click: Callable[[], None],
                 enabled: bool) -> None:
        super().__init__()
        self.setObjectName("taskCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled
                       else Qt.CursorShape.ArrowCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 600;")
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #555; font-size: 13px;")

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch(1)

        btn = QPushButton("Abrir" if enabled else "Em breve")
        btn.setEnabled(enabled)
        btn.clicked.connect(lambda: on_click())
        layout.addWidget(btn)

        self.setStyleSheet(
            "#taskCard { background: #ffffff; border: 1px solid #e2e2e2;"
            " border-radius: 10px; }"
        )


class HomeView(QWidget):
    def __init__(self, on_navigate: Callable[[str], None]) -> None:
        super().__init__()
        self._on_navigate = on_navigate

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)

        heading = QLabel("O que você quer preparar para IA?")
        heading.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitle = QLabel(
            "Transforme material bruto em fontes limpas para NotebookLM, ChatGPT, "
            "Claude, Gemini e ferramentas similares. Tudo local e offline."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #666; font-size: 14px; margin-bottom: 8px;")

        outer.addWidget(heading)
        outer.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)
        for idx, (title, desc, key, enabled) in enumerate(TASKS):
            card = TaskCard(title, desc, lambda k=key: self._on_navigate(k), enabled)
            grid.addWidget(card, idx // 3, idx % 3)
        outer.addLayout(grid)
        outer.addStretch(1)
