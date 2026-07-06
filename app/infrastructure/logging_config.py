"""Configuração de logging.

Regra de privacidade (Seção 14/15): logs contêm detalhes técnicos suficientes
para depuração, mas NUNCA o conteúdo textual dos documentos do usuário.
Registre caminhos, contagem de páginas, nomes de backend e erros — não trechos
extraídos, transcrições ou texto OCR.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.infrastructure.paths import logs_dir

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_file = logs_dir() / "app.log"
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging inicializado. Arquivo: %s", log_file)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
