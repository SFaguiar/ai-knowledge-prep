"""Operações em lote (Etapa 9)."""

from __future__ import annotations

from app.ui.placeholder_view import PlaceholderView


class BatchView(PlaceholderView):
    def __init__(self) -> None:
        super().__init__(
            "Lote",
            "Aplicar operações a vários arquivos.",
            roadmap="Etapa 9 — fila de jobs, histórico e relatório final.",
        )
