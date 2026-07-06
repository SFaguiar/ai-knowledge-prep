"""Ponto de entrada da aplicação.

Uso:
    python -m app.main
"""

from __future__ import annotations

import signal
import sys

from app.infrastructure.logging_config import configure_logging, get_logger


def main() -> int:
    configure_logging()
    logger = get_logger(__name__)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "PySide6 não está instalado.\n"
            "Instale as dependências com:  uv sync   (ou)   pip install -e .\n"
        )
        return 1

    from app.infrastructure.temp_manager import temp_manager
    from app.ui.main_window import MainWindow

    # Limpa temporários órfãos de sessões anteriores.
    temp_manager.cleanup_all()

    app = QApplication(sys.argv)
    app.setApplicationName("AI Knowledge Prep Suite")
    app.setOrganizationName("AIKnowledgePrep")

    # Permite Ctrl+C encerrar no terminal durante desenvolvimento.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    window = MainWindow()
    window.show()
    logger.info("Aplicação iniciada.")

    exit_code = app.exec()
    temp_manager.cleanup_all()
    logger.info("Aplicação encerrada (código %s).", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
