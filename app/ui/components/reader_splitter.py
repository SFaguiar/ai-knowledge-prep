"""Divisor arrastável (trilha ↔ preview) com duplo-clique para resetar.

Um `QSplitter` cuja alça, ao receber duplo-clique, emite `reset_requested` —
a view usa isso para voltar à proporção padrão. O arraste normal redimensiona
os painéis livremente (a persistência da posição fica a cargo da view).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSplitter, QSplitterHandle


class _ResetHandle(QSplitterHandle):
    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        splitter = self.splitter()
        if isinstance(splitter, ReaderSplitter):
            splitter.reset_requested.emit()
        super().mouseDoubleClickEvent(event)


class ReaderSplitter(QSplitter):
    reset_requested = Signal()

    def createHandle(self) -> QSplitterHandle:  # noqa: N802 (Qt override)
        return _ResetHandle(self.orientation(), self)
