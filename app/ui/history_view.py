"""Histórico de operações (Etapa 9)."""

from __future__ import annotations

from app.ui.placeholder_view import PlaceholderView


class HistoryView(PlaceholderView):
    def __init__(self) -> None:
        super().__init__(
            "Histórico",
            "Consultar operações anteriores e abrir pastas de saída.",
            roadmap="Etapa 9 — histórico local (SQLite, já provisionado em "
                    "infrastructure/database.py) e repetição de operações.",
        )
