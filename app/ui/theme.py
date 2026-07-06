"""Tema visual centralizado — paleta, tipografia e QSS globais.

O app define sua própria paleta escura via QPalette + stylesheet Qt (Fusion
style), em vez de herdar cores nativas do Windows. Isso resolve problemas de
contraste (texto ilegível em botões no modo escuro do sistema) e garante uma
aparência consistente em qualquer máquina.

Widgets usam a propriedade dinâmica "cssClass" para pedir variantes (ex.:
botão primário, título grande) sem duplicar cores em cada view:

    label.setProperty("cssClass", "heading")
    button.setProperty("cssClass", "primary")
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# --- Paleta ------------------------------------------------------------------

BG_APP = "#12141a"
BG_SURFACE = "#171a22"
BG_ELEVATED = "#1e222c"
BG_ELEVATED_HOVER = "#262b38"
BG_INPUT = "#0f1116"

BORDER = "#2a3040"
BORDER_STRONG = "#3a4256"

TEXT_PRIMARY = "#eef0f4"
TEXT_SECONDARY = "#9aa3b7"
TEXT_MUTED = "#6b7688"
TEXT_ON_ACCENT = "#ffffff"

ACCENT = "#4c8bf5"
ACCENT_HOVER = "#6ea1ff"
ACCENT_PRESSED = "#3a70d6"
ACCENT_SOFT = "#20304d"

SUCCESS = "#3ecf8e"
WARNING = "#f2b84b"
DANGER = "#f2685c"
DANGER_HOVER = "#ff8478"

FONT_FAMILY = "Segoe UI"


def refresh(widget: QWidget) -> None:
    """Força o widget a reavaliar seletores de QSS após mudar uma propriedade
    dinâmica (ex.: cssClass) em tempo de execução."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, 10))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_APP))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT_ON_ACCENT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    disabled = QPalette.ColorGroup.Disabled
    muted = QColor(TEXT_MUTED)
    palette.setColor(disabled, QPalette.ColorRole.Text, muted)
    palette.setColor(disabled, QPalette.ColorRole.ButtonText, muted)
    palette.setColor(disabled, QPalette.ColorRole.WindowText, muted)
    app.setPalette(palette)

    app.setStyleSheet(STYLESHEET)


STYLESHEET = f"""
/* --- base ---------------------------------------------------------------
   Deliberadamente SEM "background" aqui: QWidget é a classe-base de tudo
   (inclusive QLabel, que no Qt é um QFrame), então pintar um fundo genérico
   faria cada rótulo virar uma "caixa" com cor destacada do cartão ao redor.
   Widgets simples (QWidget/QLabel puros) ficam transparentes e mostram o
   fundo do pai; só quem precisa de "chão" (janela, cartões, botões, inputs)
   declara background explicitamente abaixo. -------------------------------*/
QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "{FONT_FAMILY}";
    font-size: 13px;
}}
QMainWindow {{
    background: {BG_APP};
}}
QStackedWidget {{
    background: {BG_SURFACE};
}}
QToolTip {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 8px;
    border-radius: 6px;
}}

/* --- tipografia (via cssClass) ------------------------------------------ */
QLabel[cssClass="heading"] {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}
QLabel[cssClass="subtitle"] {{
    font-size: 14px;
    color: {TEXT_SECONDARY};
}}
QLabel[cssClass="sectionTitle"] {{
    font-size: 16px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    padding-top: 4px;
}}
QLabel[cssClass="caption"] {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QLabel[cssClass="info"] {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}
QLabel[cssClass="badge-warning"] {{
    background: #4a3a1a;
    color: {WARNING};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}}

/* --- botões --------------------------------------------------------------
   "outline: none" remove o retângulo pontilhado de foco do Qt/SO — sem essa
   regra, o indicador de foco padrão pode herdar a cor de destaque (accent)
   configurada no Windows (ex.: dourado/âmbar) em vez da cor do nosso tema. */
QPushButton {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 18px;
    outline: none;
}}
QPushButton:hover {{
    background: {BG_ELEVATED_HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: {BG_APP};
}}
QPushButton:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton:disabled {{
    background: {BG_SURFACE};
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}
QPushButton[cssClass="primary"] {{
    background: {ACCENT};
    color: {TEXT_ON_ACCENT};
    border: 1px solid {ACCENT};
    font-weight: 600;
}}
QPushButton[cssClass="primary"]:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton[cssClass="primary"]:pressed {{
    background: {ACCENT_PRESSED};
}}
QPushButton[cssClass="primary"]:disabled {{
    background: {BG_ELEVATED};
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}
QPushButton[cssClass="danger"] {{
    color: {DANGER};
    border-color: {DANGER};
}}
QPushButton[cssClass="danger"]:hover {{
    background: {DANGER};
    color: {TEXT_ON_ACCENT};
}}
/* Botões compactos (só ícone/glyph), ex.: zoom +/−, navegação ‹ ›.
   Padding pequeno para o glyph não ser cortado em larguras fixas estreitas. */
QPushButton[cssClass="icon"] {{
    padding: 6px 8px;
    min-width: 18px;
    font-size: 15px;
}}

/* --- navegação lateral --------------------------------------------------- */
QListWidget#nav {{
    background: {BG_APP};
    border: none;
    border-right: 1px solid {BORDER};
    padding: 10px 8px;
    font-size: 14px;
    outline: 0;
}}
QListWidget#nav::item {{
    padding: 12px 14px;
    border: none;
    border-radius: 8px;
    margin: 2px 0;
    color: {TEXT_SECONDARY};
}}
QListWidget#nav::item:selected {{
    background: {ACCENT_SOFT};
    color: {TEXT_PRIMARY};
    font-weight: 600;
}}
QListWidget#nav::item:hover:!selected {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
}}

/* --- entradas de texto / diálogos ---------------------------------------- */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QPlainTextEdit[cssClass="console"] {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    color: {TEXT_SECONDARY};
    background: {BG_INPUT};
}}
QMessageBox {{
    background: {BG_ELEVATED};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* --- combobox ------------------------------------------------------------ */
QComboBox {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 18px;
}}
QComboBox:hover {{
    border-color: {ACCENT};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT_PRIMARY};
    outline: none;
    padding: 4px;
}}

/* --- barra de progresso --------------------------------------------------- */
QProgressBar {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    text-align: center;
    color: {TEXT_SECONDARY};
    height: 16px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}

/* --- barra de status ------------------------------------------------------ */
QStatusBar {{
    background: {BG_APP};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 12px;
}}

/* --- scrollbars modernas --------------------------------------------------- */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* --- cartões (tarefas, dependências, callouts) ---------------------------- */
QFrame[cssClass="card"] {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame[cssClass="card"]:hover {{
    border-color: {BORDER_STRONG};
}}
QFrame[cssClass="callout"] {{
    background: {BG_ELEVATED};
    border: none;
    border-left: 3px solid {ACCENT};
    border-radius: 6px;
}}
"""
