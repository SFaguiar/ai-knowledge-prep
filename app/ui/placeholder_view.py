"""View de espaço reservado para módulos ainda não implementados.

Comunica claramente o que a tarefa fará e em que etapa do roadmap ela entra,
mantendo a aplicação utilizável e honesta a cada etapa (Diretriz final).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderView(QWidget):
    def __init__(self, title: str, description: str, roadmap: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 700;")

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #555; font-size: 14px; margin-top: 6px;")

        badge = QLabel("Em desenvolvimento")
        badge.setStyleSheet(
            "background: #fff3cd; color: #856404; padding: 4px 10px;"
            " border-radius: 6px; font-size: 12px; margin-top: 14px;"
        )
        badge.setMaximumWidth(180)

        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addWidget(badge)

        if roadmap:
            roadmap_lbl = QLabel(roadmap)
            roadmap_lbl.setWordWrap(True)
            roadmap_lbl.setStyleSheet("color: #777; font-size: 13px; margin-top: 18px;")
            layout.addWidget(roadmap_lbl)
