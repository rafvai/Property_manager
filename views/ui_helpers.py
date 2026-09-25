"""
views/ui_helpers.py
===================
Piccole utilità grafiche condivise dalle viste: colori derivati, icone
disegnate in codice (niente emoji, che nel build diventano quadratini)
e foglio di stile per le barre di scorrimento.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QPushButton


def tinta(colore_hex: str, alpha: float) -> str:
    """Colore con trasparenza, per sfondi tenui: rgba(r, g, b, a)."""
    c = QColor(colore_hex)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha:.2f})"


def mescola(colore_hex: str, sfondo_hex: str, quota: float) -> str:
    """
    Mescola un colore con lo sfondo: quota 1.0 = colore pieno, 0.0 = sfondo.
    Sostituisce `opacity`, che i fogli di stile Qt ignorano.
    """
    c, s = QColor(colore_hex), QColor(sfondo_hex)
    canale = lambda a, b: int(round(a * quota + b * (1 - quota)))  # noqa: E731
    return QColor(canale(c.red(), s.red()), canale(c.green(), s.green()), canale(c.blue(), s.blue())).name()


def icona_pallino(colore_hex: str, diametro: int = 12) -> QIcon:
    """Icona a cerchio pieno, per combo, legende e badge."""
    pix = QPixmap(diametro, diametro)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colore_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, diametro, diametro)
    painter.end()
    return QIcon(pix)


def icona_cestino(colore_hex: str, lato: int = 16) -> QIcon:
    """Icona cestino a linee, disegnata in codice."""
    pix = QPixmap(lato, lato)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(colore_hex))
    pen.setWidthF(1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    s = lato / 16
    p.drawLine(QRectF(2 * s, 4 * s, 0, 0).topLeft(), QRectF(14 * s, 4 * s, 0, 0).topLeft())   # coperchio
    p.drawLine(QRectF(6 * s, 2 * s, 0, 0).topLeft(), QRectF(10 * s, 2 * s, 0, 0).topLeft())  # maniglia
    p.drawRoundedRect(QRectF(3.5 * s, 4 * s, 9 * s, 10 * s), 1.5 * s, 1.5 * s)               # corpo
    p.drawLine(QRectF(6.5 * s, 7 * s, 0, 0).topLeft(), QRectF(6.5 * s, 11 * s, 0, 0).topLeft())
    p.drawLine(QRectF(9.5 * s, 7 * s, 0, 0).topLeft(), QRectF(9.5 * s, 11 * s, 0, 0).topLeft())
    p.end()
    return QIcon(pix)


class BottoneIcona(QPushButton):
    """Bottone piatto con icona che cambia colore al passaggio del mouse."""

    def __init__(self, icona_normale: QIcon, icona_hover: QIcon, tooltip: str = "", parent=None):
        super().__init__(parent)
        self._normale = icona_normale
        self._hover   = icona_hover
        self.setIcon(icona_normale)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 2px; }")

    def enterEvent(self, event):
        self.setIcon(self._hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._normale)
        super().leaveEvent(event)


def stile_scrollbar(colore_maniglia: str = "#475569", colore_hover: str = "#64748b") -> str:
    """Barre di scorrimento sottili e scure, coerenti col tema."""
    return f"""
        QScrollBar:vertical {{
            background: transparent; width: 8px; margin: 4px 2px 4px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {colore_maniglia}; border-radius: 4px; min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {colore_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{
            background: transparent; height: 8px; margin: 0 4px 2px 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {colore_maniglia}; border-radius: 4px; min-width: 24px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {colore_hover}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    """
