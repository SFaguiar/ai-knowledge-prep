"""View de espaço reservado para módulos ainda não implementados.

Comunica claramente o que a tarefa fará e em que etapa do roadmap ela entra,
mantendo a aplicação utilizável e honesta a cada etapa (Diretriz final).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderView(QWidget):
    def __init__(self, title: str, description: str, roadmap: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setProperty("cssClass", "heading")

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setProperty("cssClass", "subtitle")
        desc_lbl.setStyleSheet("margin-top: 2px;")

        badge = QLabel("🚧  Em desenvolvimento")
        badge.setProperty("cssClass", "badge-warning")
        badge.setMaximumWidth(220)

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addSpacing(10)
        layout.addWidget(badge)

        if roadmap:
            callout = QFrame()
            callout.setProperty("cssClass", "callout")
            callout_layout = QVBoxLayout(callout)
            callout_layout.setContentsMargins(16, 12, 16, 12)
            roadmap_lbl = QLabel(roadmap)
            roadmap_lbl.setWordWrap(True)
            roadmap_lbl.setProperty("cssClass", "info")
            callout_layout.addWidget(roadmap_lbl)

            layout.addSpacing(20)
            layout.addWidget(callout)
