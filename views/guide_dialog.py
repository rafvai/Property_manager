"""
views/guide_dialog.py
=====================
Guida all'uso: indice degli argomenti a sinistra, passi a destra e pulsante
per saltare alla sezione descritta. Testi dal DB traduzioni (categoria GUIDA).
"""
import re
from html import escape

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from resources import icon_path
from styles import (
    COLORE_BIANCO,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_WIDGET_2,
    default_dialog_style,
)

# (chiave testi GUIDA, icona, sezione del menu principale)
ARGOMENTI = [
    ("PROPRIETA",    "property.png",  "PROPERTIES"),
    ("TRANSAZIONI",  "pie-chart.png", "TRANSAZIONI"),
    ("FORNITORI",    "security.png",  "FORNITORI"),
    ("SCADENZE",     "calendar.png",  "CALENDAR"),
    ("DOCUMENTI",    "document.png",  "DOCUMENTS"),
    ("FINANZE",      "bar-chart.png", "FINANZE"),
    ("IMPOSTAZIONI", "settings.png",  "IMPOSTAZIONI"),
]

RIGA_NUMERATA = re.compile(r"^\d+\.\s+")

STILE_INDICE = f"""
    QListWidget {{
        background-color: {COLORE_WIDGET_2}; border: none; border-radius: 8px;
        color: {COLORE_BIANCO}; font-size: 13px; outline: none; padding: 6px;
    }}
    QListWidget::item {{ padding: 10px 8px; border-radius: 6px; }}
    QListWidget::item:hover {{ background-color: #1e293b; }}
    QListWidget::item:selected {{ background-color: {COLORE_ITEM_SELEZIONATO}; }}
"""
STILE_TESTO = f"""
    QTextBrowser {{
        background-color: {COLORE_WIDGET_2}; border: none; border-radius: 8px;
        color: {COLORE_BIANCO}; padding: 14px;
    }}
"""
STILE_BOTTONE_SECONDARIO = f"""
    QPushButton {{
        background-color: transparent; color: {COLORE_BIANCO};
        border: 1px solid #334155; border-radius: 6px;
        padding: 10px 20px; font-size: 14px; min-width: 80px;
    }}
    QPushButton:hover {{ background-color: {COLORE_WIDGET_2}; border-color: {COLORE_ITEM_SELEZIONATO}; }}
"""
FOGLIO_STILE_HTML = f"""
    p  {{ font-size: 13px; color: {COLORE_BIANCO}; margin: 0 0 10px 0; line-height: 140%; }}
    ol {{ font-size: 13px; color: {COLORE_BIANCO}; margin: 4px 0 12px 18px; }}
    li {{ margin-bottom: 6px; line-height: 140%; }}
    .nota {{ color: {COLORE_GRIGIO}; }}
"""


class GuideDialog(QDialog):
    """Al termine `sezione_scelta` contiene la sezione da aprire, se richiesta."""

    def __init__(self, tm, argomento_iniziale: str | None = None, parent=None):
        super().__init__(parent)
        self.tm = tm
        self.sezione_scelta = None

        self.setWindowTitle(self.tm.get("GUIDA", "TITOLO"))
        self.setMinimumSize(820, 560)
        self.setStyleSheet(default_dialog_style)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        titolo = QLabel(self.tm.get("GUIDA", "TITOLO"))
        titolo.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORE_BIANCO};")
        layout.addWidget(titolo)

        corpo = QHBoxLayout()
        corpo.setSpacing(14)

        self.indice = QListWidget()
        self.indice.setStyleSheet(STILE_INDICE)
        self.indice.setFixedWidth(240)
        self.indice.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.indice.setIconSize(QSize(18, 18))
        self.indice.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for chiave, icona, sezione in ARGOMENTI:
            voce = QListWidgetItem(QIcon(icon_path(icona)), self.tm.get("GUIDA", f"{chiave}_TITOLO"))
            voce.setData(Qt.ItemDataRole.UserRole, (chiave, sezione))
            self.indice.addItem(voce)
        self.indice.currentRowChanged.connect(self._mostra_argomento)
        corpo.addWidget(self.indice)

        colonna = QVBoxLayout()
        colonna.setSpacing(10)
        self.titolo_argomento = QLabel()
        self.titolo_argomento.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORE_ITEM_HOVER};")
        colonna.addWidget(self.titolo_argomento)
        self.testo = QTextBrowser()
        self.testo.setStyleSheet(STILE_TESTO)
        self.testo.setOpenExternalLinks(False)
        self.testo.document().setDefaultStyleSheet(FOGLIO_STILE_HTML)
        colonna.addWidget(self.testo, stretch=1)
        corpo.addLayout(colonna, stretch=1)
        layout.addLayout(corpo, stretch=1)

        barra = QHBoxLayout()
        barra.addStretch()
        bottone_chiudi = QPushButton(self.tm.get("PULSANTI", "CHIUDI"))
        bottone_chiudi.setStyleSheet(STILE_BOTTONE_SECONDARIO)
        bottone_chiudi.clicked.connect(self.reject)
        barra.addWidget(bottone_chiudi)
        self.bottone_vai = QPushButton(self.tm.get("GUIDA", "VAI_SEZIONE"))
        self.bottone_vai.clicked.connect(self._vai_alla_sezione)
        barra.addWidget(self.bottone_vai)
        layout.addLayout(barra)

        chiavi = [chiave for chiave, _, _ in ARGOMENTI]
        self.indice.setCurrentRow(chiavi.index(argomento_iniziale) if argomento_iniziale in chiavi else 0)

    # ──────────────────────────────────────────────────────────────

    def _mostra_argomento(self, riga: int):
        voce = self.indice.item(riga)
        if voce is None:
            return
        chiave, _ = voce.data(Qt.ItemDataRole.UserRole)
        self.titolo_argomento.setText(self.tm.get("GUIDA", f"{chiave}_TITOLO"))
        self.testo.setHtml(self._testo_in_html(self.tm.get("GUIDA", f"{chiave}_TESTO")))

    @staticmethod
    def _testo_in_html(testo: str) -> str:
        """Le righe '1. ...' diventano un elenco numerato, le altre paragrafi."""
        blocchi, passi = [], []

        def chiudi_elenco():
            if passi:
                blocchi.append("<ol>" + "".join(f"<li>{p}</li>" for p in passi) + "</ol>")
                passi.clear()

        for riga in testo.splitlines():
            riga = riga.strip()
            if not riga:
                continue
            if RIGA_NUMERATA.match(riga):
                passi.append(escape(RIGA_NUMERATA.sub("", riga)))
            else:
                chiudi_elenco()
                blocchi.append(f"<p>{escape(riga)}</p>")
        chiudi_elenco()
        return "".join(blocchi)

    def _vai_alla_sezione(self):
        voce = self.indice.currentItem()
        if voce is not None:
            _, self.sezione_scelta = voce.data(Qt.ItemDataRole.UserRole)
        self.accept()
