"""
views/calendar_planner.py
=========================
Calendario mensile delle scadenze.

Componenti:
    PlannerCalendarWidget  griglia del mese, legenda proprietà, navigazione
    DayCell                cella giorno: numero, chip scadenze, "+ altri N"
    DeadlineChip           singola scadenza, colorata per proprietà, cliccabile
    DeadlineDetailDialog   dettaglio modificabile con stato, proprietà, data
    DayDeadlinesDialog     elenco completo delle scadenze di un giorno

Il colore di ogni proprietà è stabile: dipende dall'ordine di creazione
(id crescente), non dal mese visualizzato.
"""
from datetime import date

from PySide6.QtCore import QDate, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dialogs import AddDeadlineDialog
from resources import icon_path
from styles import (
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_RIGA_1,
    COLORE_WARNING,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_dialog_style,
)
from validation_utils import ValidationError, validate_date, validate_required_text

# ──────────────────────────────────────────────────────────────────
#  Palette proprietà: tinte sobrie e ben distinguibili su fondo scuro
# ──────────────────────────────────────────────────────────────────
PALETTE_PROPRIETA = [
    "#6366f1",  # indaco
    "#14b8a6",  # teal
    "#f59e0b",  # ambra
    "#f43f5e",  # rosa
    "#8b5cf6",  # viola
    "#0ea5e9",  # azzurro
    "#84cc16",  # lime
    "#f97316",  # arancio
]
COLORE_GENERALE = "#64748b"   # scadenze senza proprietà

ALTEZZA_CHIP    = 24
SPAZIO_CHIP     = 3
ALTEZZA_MIN_CELLA = 96

STATO_SCADUTA   = "scaduta"
STATO_OGGI      = "oggi"
STATO_IMMINENTE = "imminente"
STATO_OK        = "ok"


def colore_proprieta(property_id, ordine_ids: list) -> str:
    """Colore stabile di una proprietà; grigio per le scadenze generali."""
    if property_id is None or property_id not in ordine_ids:
        return COLORE_GENERALE
    return PALETTE_PROPRIETA[ordine_ids.index(property_id) % len(PALETTE_PROPRIETA)]


def tinta(colore_hex: str, alpha: float) -> str:
    """Versione trasparente di un colore, per gli sfondi dei chip."""
    c = QColor(colore_hex)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha:.2f})"


def stato_scadenza(due: date, oggi: date, warning_days: int) -> tuple[str, int]:
    """Ritorna (stato, giorni_mancanti). Giorni negativi = scaduta."""
    giorni = (due - oggi).days
    if giorni < 0:
        return STATO_SCADUTA, giorni
    if giorni == 0:
        return STATO_OGGI, giorni
    if giorni <= warning_days:
        return STATO_IMMINENTE, giorni
    return STATO_OK, giorni


def icona_pallino(colore_hex: str, diametro: int = 12) -> QIcon:
    """Icona a cerchio pieno, usata nelle combo e nella legenda."""
    pix = QPixmap(diametro, diametro)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colore_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, diametro, diametro)
    painter.end()
    return QIcon(pix)


def _data_da_iso(valore) -> date:
    return valore if isinstance(valore, date) else date.fromisoformat(str(valore)[:10])


# ──────────────────────────────────────────────────────────────────
#  Chip scadenza
# ──────────────────────────────────────────────────────────────────
class DeadlineChip(QFrame):
    """Etichetta di una scadenza dentro la cella. Click → dettaglio."""

    clicked = Signal(dict)

    def __init__(self, deadline: dict, colore: str, stato: str, parent=None):
        super().__init__(parent)
        self.deadline = deadline
        self._testo   = deadline["title"]

        # Stato temporale: barra a sinistra e pallino prima del testo
        if stato == STATO_SCADUTA:
            barra, marcatore = COLORE_ERROR, COLORE_ERROR
        elif stato in (STATO_OGGI, STATO_IMMINENTE):
            barra, marcatore = COLORE_WARNING, COLORE_WARNING
        else:
            barra, marcatore = colore, None

        self.setFixedHeight(ALTEZZA_CHIP)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(deadline["title"])
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {tinta(colore, 0.22)};
                border: none;
                border-left: 3px solid {barra};
                border-radius: 4px;
            }}
            QFrame:hover {{ background-color: {tinta(colore, 0.38)}; }}
            QLabel {{
                color: {COLORE_BIANCO};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(5)
        self._larghezza_marcatore = 0
        if marcatore:
            pallino = QLabel()
            pallino.setFixedSize(8, 8)
            pallino.setPixmap(icona_pallino(marcatore, 8).pixmap(8, 8))
            lay.addWidget(pallino)
            self._larghezza_marcatore = 8 + 5
        self._label = QLabel(self._testo)
        self._label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Larghezza utile dal chip, non dalla label: la label viene
        # dimensionata dal layout solo dopo questo evento
        self._label.ensurePolished()
        metrics   = QFontMetrics(self._label.font())
        larghezza = max(10, self.width() - 12 - 3 - self._larghezza_marcatore)
        self._label.setText(
            metrics.elidedText(self._testo, Qt.TextElideMode.ElideRight, larghezza)
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.deadline)
        event.accept()


# ──────────────────────────────────────────────────────────────────
#  Cella giorno
# ──────────────────────────────────────────────────────────────────
class DayCell(QFrame):
    """
    Cella del calendario. Nessun bordo colorato: il colore lo portano i chip.
    I chip che non entrano nello spazio disponibile vengono riassunti da
    "+ altri N", ricalcolato a ogni ridimensionamento.
    """

    def __init__(self, giorno: int, data: date, deadlines: list, calendario,
                 tm, ordine_ids: list, warning_days: int, oggi: date):
        super().__init__()
        self.data       = data
        self.deadlines  = deadlines
        self.calendario = calendario
        self.tm         = tm
        self._chips: list[DeadlineChip] = []

        e_oggi = (data == oggi)
        self.setMinimumHeight(ALTEZZA_MIN_CELLA)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tm.get("CALENDARIO", "CLICK_NUOVA", fallback="Click per aggiungere una scadenza"))
        self.setStyleSheet(f"""
            QFrame#cella {{
                background-color: {COLORE_RIGA_1};
                border-radius: 8px;
                border: 1px solid transparent;
            }}
            QFrame#cella:hover {{ border: 1px solid {COLORE_ITEM_HOVER}; }}
        """)
        self.setObjectName("cella")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(SPAZIO_CHIP)

        # Numero del giorno: oggi in un cerchietto pieno
        numero = QLabel(str(giorno))
        numero.setFixedSize(26, 26)
        numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if e_oggi:
            numero.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: white; border: none;"
                f"background-color: {COLORE_ITEM_SELEZIONATO}; border-radius: 13px;"
            )
        else:
            numero.setStyleSheet(
                f"font-size: 15px; font-weight: bold; color: {COLORE_BIANCO};"
                f"background: transparent; border: none;"
            )
        riga_numero = QHBoxLayout()
        riga_numero.setContentsMargins(0, 0, 0, 0)
        riga_numero.addWidget(numero)
        riga_numero.addStretch()
        lay.addLayout(riga_numero)
        self._altezza_testata = 26

        for d in deadlines:
            stato, _ = stato_scadenza(_data_da_iso(d["due_date"]), oggi, warning_days)
            chip = DeadlineChip(d, colore_proprieta(d.get("property_id"), ordine_ids), stato)
            chip.clicked.connect(calendario.apri_dettaglio)
            lay.addWidget(chip)
            self._chips.append(chip)

        self._label_altri = QLabel("")
        self._label_altri.setFixedHeight(ALTEZZA_CHIP)
        self._label_altri.setCursor(Qt.CursorShape.PointingHandCursor)
        self._label_altri.setStyleSheet(
            f"color: {COLORE_ITEM_HOVER}; font-size: 12px; font-weight: 600;"
            f"background: transparent; border: none; padding-left: 4px;"
        )
        self._label_altri.hide()
        lay.addWidget(self._label_altri)
        lay.addStretch()

    # ── overflow ──────────────────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ricalcola_visibili()

    def _ricalcola_visibili(self):
        if not self._chips:
            return
        margini    = 12
        disponibile = self.height() - margini - self._altezza_testata - SPAZIO_CHIP
        capienza   = max(0, (disponibile + SPAZIO_CHIP) // (ALTEZZA_CHIP + SPAZIO_CHIP))

        # Se non entrano tutti, una riga resta per "+ altri N"
        visibili = len(self._chips) if len(self._chips) <= capienza else max(0, capienza - 1)

        for i, chip in enumerate(self._chips):
            chip.setVisible(i < visibili)

        nascosti = len(self._chips) - visibili
        if nascosti > 0:
            testo = self.tm.get("CALENDARIO", "ALTRI", fallback="+ altri XXX")
            self._label_altri.setText(testo.replace("XXX", str(nascosti)))
            self._label_altri.show()
        else:
            self._label_altri.hide()

    # ── click ─────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._label_altri.isVisible() and self._label_altri.geometry().contains(event.pos()):
                self.calendario.apri_elenco_giorno(self.data, self.deadlines)
            else:
                self.calendario.add_deadline_for_date(self.data.isoformat())
        event.accept()


# ──────────────────────────────────────────────────────────────────
#  Dettaglio scadenza
# ──────────────────────────────────────────────────────────────────
class DeadlineDetailDialog(QDialog):
    """
    Scheda della scadenza, modificabile. Chiude con:
        self.azione == "salva"   → get_data() contiene i nuovi valori
        self.azione == "elimina" → l'utente ha confermato l'eliminazione
    """

    def __init__(self, tm, deadline: dict, properties: list, ordine_ids: list,
                 warning_days: int, parent=None):
        super().__init__(parent)
        self.tm       = tm
        self.deadline = deadline
        self.azione   = None

        self.setWindowTitle(tm.get("CALENDARIO", "DETTAGLIO", fallback="Dettaglio scadenza"))
        self.setMinimumWidth(560)
        self.setStyleSheet(default_dialog_style + f"""
            QLineEdit#titolo {{
                font-size: 20px; font-weight: bold; color: white;
                background: transparent; border: none; border-bottom: 2px solid #334155;
                border-radius: 0; padding: 6px 2px;
            }}
            QLineEdit#titolo:focus {{ border-bottom: 2px solid {COLORE_ITEM_SELEZIONATO}; }}
            QLabel#campo {{ color: {COLORE_GRIGIO}; font-size: 12px; font-weight: 600; }}
            QPushButton#elimina {{
                background: transparent; color: {COLORE_ERROR};
                border: 1px solid {COLORE_ERROR};
            }}
            QPushButton#elimina:hover {{ background-color: {tinta(COLORE_ERROR, 0.15)}; }}
            QPushButton#annulla {{ background: transparent; border: 1px solid #334155; }}
            QPushButton#annulla:hover {{ background-color: {COLORE_WIDGET_2}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(14)

        # Titolo
        self.titolo = QLineEdit(deadline["title"])
        self.titolo.setObjectName("titolo")
        lay.addWidget(self.titolo)

        # Riga stato temporale
        self.riga_stato = QLabel()
        self.riga_stato.setStyleSheet("font-size: 13px; font-weight: 600;")
        lay.addWidget(self.riga_stato)

        griglia = QGridLayout()
        griglia.setHorizontalSpacing(18)
        griglia.setVerticalSpacing(6)

        # Stato
        griglia.addWidget(self._campo(tm.get("ETICHETTE", "STATO", fallback="Stato")), 0, 0)
        self.stato = QComboBox()
        self.stato.addItem("○  " + tm.get("CALENDARIO", "APERTA", fallback="Aperta"), False)
        self.stato.addItem("✓  " + tm.get("CALENDARIO", "COMPLETATA", fallback="Completata"), True)
        self.stato.setCurrentIndex(1 if deadline.get("completed") else 0)
        griglia.addWidget(self.stato, 1, 0)

        # Proprietà
        griglia.addWidget(self._campo(tm.get("ETICHETTE", "PROPRIETA", fallback="Proprietà")), 0, 1)
        self.proprieta = QComboBox()
        self.proprieta.setIconSize(QSize(12, 12))
        self.proprieta.addItem(icona_pallino(COLORE_GENERALE),
                               tm.get("CALENDARIO", "GENERALE", fallback="Generale"), None)
        for p in properties:
            self.proprieta.addItem(icona_pallino(colore_proprieta(p["id"], ordine_ids)), p["name"], p["id"])
        idx = self.proprieta.findData(deadline.get("property_id"))
        self.proprieta.setCurrentIndex(idx if idx >= 0 else 0)
        griglia.addWidget(self.proprieta, 1, 1)

        # Data
        griglia.addWidget(self._campo(tm.get("ETICHETTE", "DATA_SCADENZA", fallback="Data scadenza")), 2, 0)
        self.data = QDateEdit()
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.data.setCalendarPopup(True)
        due = _data_da_iso(deadline["due_date"])
        self.data.setDate(QDate(due.year, due.month, due.day))
        self.data.dateChanged.connect(lambda _: self._aggiorna_riga_stato(warning_days))
        griglia.addWidget(self.data, 3, 0)

        griglia.setColumnStretch(0, 1)
        griglia.setColumnStretch(1, 1)
        lay.addLayout(griglia)

        # Descrizione
        lay.addWidget(self._campo(tm.get("ETICHETTE", "DESCRIZIONE", fallback="Descrizione")))
        self.descrizione = QTextEdit(deadline.get("description") or "")
        self.descrizione.setPlaceholderText(tm.get("PLACEHOLDER", "DETTAGLI_AGGIUNTIVI", fallback="Dettagli aggiuntivi…"))
        self.descrizione.setMinimumHeight(110)
        lay.addWidget(self.descrizione)

        # Pulsanti
        riga = QHBoxLayout()
        btn_elimina = QPushButton(tm.get("PULSANTI", "ELIMINA", fallback="Elimina"))
        btn_elimina.setObjectName("elimina")
        btn_elimina.clicked.connect(self._elimina)
        riga.addWidget(btn_elimina)
        riga.addStretch()
        btn_annulla = QPushButton(tm.get("PULSANTI", "ANNULLA", fallback="Annulla"))
        btn_annulla.setObjectName("annulla")
        btn_annulla.clicked.connect(self.reject)
        riga.addWidget(btn_annulla)
        btn_salva = QPushButton(tm.get("PULSANTI", "SALVA", fallback="Salva"))
        btn_salva.setDefault(True)
        btn_salva.clicked.connect(self._salva)
        riga.addWidget(btn_salva)
        lay.addLayout(riga)

        self._aggiorna_riga_stato(warning_days)

    def _campo(self, testo: str) -> QLabel:
        lbl = QLabel(testo.upper())
        lbl.setObjectName("campo")
        return lbl

    def _aggiorna_riga_stato(self, warning_days: int):
        due = self.data.date().toPython()
        stato, giorni = stato_scadenza(due, date.today(), warning_days)
        tm = self.tm
        if stato == STATO_SCADUTA:
            testo  = tm.get("CALENDARIO", "SCADUTA_DA", fallback="Scaduta da XXX giorni").replace("XXX", str(-giorni))
            colore = COLORE_ERROR
        elif stato == STATO_OGGI:
            testo  = tm.get("CALENDARIO", "SCADE_OGGI", fallback="Scade oggi")
            colore = COLORE_ERROR
        elif giorni == 1:
            testo  = tm.get("CALENDARIO", "SCADE_DOMANI", fallback="Scade domani")
            colore = COLORE_WARNING
        else:
            testo  = tm.get("CALENDARIO", "SCADE_TRA", fallback="Scade tra XXX giorni").replace("XXX", str(giorni))
            colore = COLORE_WARNING if stato == STATO_IMMINENTE else "#2ecc71"
        self.riga_stato.setText(testo)
        self.riga_stato.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {colore};")

    def _salva(self):
        try:
            validate_required_text(self.titolo.text(), "Titolo", min_length=3, max_length=200)
            validate_date(self.data.date(), self.tm.get("ETICHETTE", "DATA_SCADENZA", fallback="Data scadenza"))
        except ValidationError as e:
            QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))
            return
        self.azione = "salva"
        self.accept()

    def _elimina(self):
        risposta = QMessageBox.question(
            self,
            self.tm.get("PULSANTI", "ELIMINA", fallback="Elimina"),
            self.tm.get("MESSAGGI", "CONFERMA_ELIMINA", fallback="Sei sicuro di voler eliminare?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta == QMessageBox.StandardButton.Yes:
            self.azione = "elimina"
            self.accept()

    def get_data(self) -> dict:
        return {
            "title":       self.titolo.text().strip(),
            "description": self.descrizione.toPlainText().strip() or None,
            "due_date":    self.data.date().toPython(),
            "property_id": self.proprieta.currentData(),
            "completed":   bool(self.stato.currentData()),
        }


# ──────────────────────────────────────────────────────────────────
#  Elenco scadenze di un giorno
# ──────────────────────────────────────────────────────────────────
class DayDeadlinesDialog(QDialog):
    """Tutte le scadenze di un giorno; il click su una apre il dettaglio."""

    def __init__(self, tm, data: date, deadlines: list, ordine_ids: list,
                 warning_days: int, calendario, parent=None):
        super().__init__(parent)
        self.calendario = calendario
        titolo = tm.get("CALENDARIO", "SCADENZE_DEL", fallback="Scadenze del XXX")
        self.setWindowTitle(titolo.replace("XXX", data.strftime("%d/%m/%Y")))
        self.setMinimumWidth(420)
        self.setStyleSheet(default_dialog_style)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(6)
        intestazione = QLabel(self.windowTitle())
        intestazione.setStyleSheet("font-size: 16px; font-weight: bold;")
        lay.addWidget(intestazione)
        lay.addSpacing(6)

        oggi = date.today()
        for d in deadlines:
            stato, _ = stato_scadenza(_data_da_iso(d["due_date"]), oggi, warning_days)
            chip = DeadlineChip(d, colore_proprieta(d.get("property_id"), ordine_ids), stato)
            chip.setFixedHeight(32)
            chip.clicked.connect(self._apri)
            lay.addWidget(chip)

        lay.addSpacing(8)
        btn = QPushButton(tm.get("PULSANTI", "CHIUDI", fallback="Chiudi"))
        btn.clicked.connect(self.reject)
        riga = QHBoxLayout()
        riga.addStretch()
        riga.addWidget(btn)
        lay.addLayout(riga)

    def _apri(self, deadline: dict):
        self.accept()
        self.calendario.apri_dettaglio(deadline)


# ──────────────────────────────────────────────────────────────────
#  Calendario
# ──────────────────────────────────────────────────────────────────
class PlannerCalendarWidget(QWidget):
    """Calendario mensile delle scadenze con legenda per proprietà."""

    def __init__(self, deadline_service, property_service, tm, logger,
                 user_prefs_service=None):
        super().__init__()
        self.deadline_service   = deadline_service
        self.property_service   = property_service
        self.tm                 = tm
        self.logger             = logger
        self.user_prefs_service = user_prefs_service

        self.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; color: {COLORE_BIANCO}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header: mese + azioni
        header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header.addWidget(self.month_label)
        header.addStretch()

        add_btn = QPushButton(f"+ {tm.get('PULSANTI', 'AGGIUNGI', fallback='Aggiungi')}")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.clicked.connect(lambda: self.add_deadline())
        header.addWidget(add_btn)

        stile_nav = f"""
            QPushButton {{ background: transparent; border: 1px solid #334155; border-radius: 6px;
                           padding: 4px 10px; color: {COLORE_BIANCO}; font-size: 14px; }}
            QPushButton:hover {{ border-color: {COLORE_ITEM_HOVER}; }}
        """
        prev_btn = QPushButton()
        prev_btn.setIcon(QIcon(icon_path("left-arrow.png")))
        prev_btn.setStyleSheet(stile_nav)
        next_btn = QPushButton()
        next_btn.setIcon(QIcon(icon_path("right-arrow.png")))
        next_btn.setStyleSheet(stile_nav)
        header.addWidget(prev_btn)
        header.addWidget(next_btn)
        main_layout.addLayout(header)

        # Legenda proprietà (riempita a ogni mese)
        self.legenda = QHBoxLayout()
        self.legenda.setSpacing(14)
        main_layout.addLayout(self.legenda)

        # Giorni della settimana
        weekdays_layout = QHBoxLayout()
        for nome in tm.get("LISTE", "WEEKDAYS_SHORT").split(";"):
            lbl = QLabel(nome)
            lbl.setStyleSheet(f"font-size: 13px; color: {COLORE_GRIGIO}; font-weight: 600;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weekdays_layout.addWidget(lbl)
        main_layout.addLayout(weekdays_layout)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        main_layout.addLayout(self.grid, stretch=1)

        self.current_date = QDate.currentDate()
        prev_btn.clicked.connect(self.prev_month)
        next_btn.clicked.connect(self.next_month)

        self.populate_month()

    # ── helper ────────────────────────────────────────────────────
    def _warning_days(self) -> int:
        if self.user_prefs_service:
            return self.user_prefs_service.get_deadline_warning_days()
        return 7

    def _proprieta(self) -> list:
        try:
            return sorted(self.property_service.get_all(), key=lambda p: p["id"])
        except Exception as e:
            self.logger.error(f"Calendario: errore caricamento proprietà: {e}")
            return []

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    # ── mese ──────────────────────────────────────────────────────
    def populate_month(self):
        self._clear_layout(self.grid)
        self._clear_layout(self.legenda)

        month = self.current_date.month()
        year  = self.current_date.year()
        mesi  = self.tm.get("LISTE", "MONTHS_FULL").split(";")
        self.month_label.setText(f"{mesi[month - 1]} {year}")

        proprieta  = self._proprieta()
        ordine_ids = [p["id"] for p in proprieta]
        nomi       = {p["id"]: p["name"] for p in proprieta}

        scadenze     = self._load_month_deadlines(year, month)
        warning_days = self._warning_days()
        oggi         = date.today()

        # Legenda: solo proprietà con scadenze nel mese, più "Generale" se serve
        presenti = []
        for lista in scadenze.values():
            for d in lista:
                pid = d.get("property_id")
                if pid not in presenti:
                    presenti.append(pid)
        for pid in sorted(presenti, key=lambda p: (p is None, ordine_ids.index(p) if p in ordine_ids else 99)):
            nome = nomi.get(pid, self.tm.get("CALENDARIO", "GENERALE", fallback="Generale"))
            self.legenda.addWidget(self._voce_legenda(colore_proprieta(pid, ordine_ids), nome))
        self.legenda.addStretch()

        first_day     = QDate(year, month, 1)
        col           = first_day.dayOfWeek() - 1
        days_in_month = first_day.daysInMonth()
        row = 0
        for giorno in range(1, days_in_month + 1):
            data = date(year, month, giorno)
            cella = DayCell(giorno, data, scadenze.get(data.isoformat(), []),
                            self, self.tm, ordine_ids, warning_days, oggi)
            self.grid.addWidget(cella, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1
        for r in range(row + 1):
            self.grid.setRowStretch(r, 1)
        for c in range(7):
            self.grid.setColumnStretch(c, 1)

    def _voce_legenda(self, colore: str, nome: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        pallino = QLabel()
        pallino.setPixmap(icona_pallino(colore, 10).pixmap(10, 10))
        lay.addWidget(pallino)
        lbl = QLabel(nome)
        lbl.setStyleSheet(f"font-size: 12px; color: {COLORE_BIANCO};")
        lay.addWidget(lbl)
        return w

    def _load_month_deadlines(self, year, month) -> dict:
        try:
            return self.deadline_service.get_by_month(year, month)
        except Exception as e:
            self.logger.error(f"Errore caricamento scadenze mese: {e}")
            return {}

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.populate_month()

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.populate_month()

    # ── azioni ────────────────────────────────────────────────────
    def add_deadline(self, preset_date=None):
        dialog = AddDeadlineDialog(self.tm, properties=self.property_service.get_all(), parent=self)
        if preset_date:
            qd = QDate.fromString(preset_date, "yyyy-MM-dd")
            if qd.isValid():
                dialog.due_date.setDate(qd)

        if dialog.exec():
            data = dialog.get_data()
            deadline_id = self.deadline_service.create(
                title=data["title"], description=data["description"],
                due_date=data["due_date"], property_id=data["property_id"],
            )
            if deadline_id:
                self.logger.info(f"Calendario: scadenza creata {data['title']}")
                self.populate_month()
            else:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), self.tm.get("MESSAGGI", "ERRORE"))

    def add_deadline_for_date(self, date_str: str):
        self.add_deadline(preset_date=date_str)

    def apri_elenco_giorno(self, data: date, deadlines: list):
        proprieta = self._proprieta()
        DayDeadlinesDialog(self.tm, data, deadlines, [p["id"] for p in proprieta],
                           self._warning_days(), self, parent=self).exec()

    def apri_dettaglio(self, deadline: dict):
        proprieta = self._proprieta()
        dialog = DeadlineDetailDialog(
            self.tm, deadline, proprieta, [p["id"] for p in proprieta],
            self._warning_days(), parent=self,
        )
        if not dialog.exec():
            return

        if dialog.azione == "elimina":
            ok = self.deadline_service.delete(deadline["id"])
        else:
            ok = self.deadline_service.update(deadline["id"], **dialog.get_data())

        if ok:
            self.populate_month()
        else:
            QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), self.tm.get("MESSAGGI", "ERRORE"))
