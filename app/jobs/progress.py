"""Modelo de progresso emitido por jobs em background."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Progress:
    # 0.0 a 1.0; use -1 para indeterminado.
    fraction: float = 0.0
    message: str = ""

    @property
    def percent(self) -> int:
        if self.fraction < 0:
            return -1
        return int(round(max(0.0, min(1.0, self.fraction)) * 100))


class CancelledError(Exception):
    """Levantada internamente quando um job é cancelado cooperativamente."""
