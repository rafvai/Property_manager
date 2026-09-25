"""
views/dashboard_view.py
=======================
Panoramica: indicatori del periodo, saldo a ciambella, prossime scadenze
e ultime transazioni. Ogni card è cliccabile e porta alla sezione relativa.
"""
from datetime import date, datetime, timedelta

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from resources import icon_path
from styles import (
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_SUCCESS,
    COLORE_WARNING,
    COLORE_WIDGET_2,
    default_combo_box_style,
    default_title_style,
)
from validation_utils import format_currency
from views.base_view import BaseView
from views.calendar_planner import (
    STATO_IMMINENTE,
    STATO_OGGI,
    STATO_SCADUTA,
    colore_proprieta,
    stato_scadenza,
)
from views.ui_helpers import icona_pallino, mescola, tinta

COLORE_TESTO_SECONDARIO = "#94a3b8"
COLORE_DIVISORE         = "#2b3a4f"
COLORE_VERDE_OK         = "#2ecc71"

STILE_CARD = f"""
    QFrame#card {{
        background-color: {COLORE_WIDGET_2};
        border-radius: 10px;
        border: 1px solid transparent;
    }}
    QFrame#card:hover {{ border: 1px solid {COLORE_ITEM_HOVER}; }}
    QLabel {{ background: transparent; border: none; }}
"""
STILE_TITOLO_CARD = (
    f"font-size: 11px; font-weight: 600; color: {COLORE_GRIGIO}; letter-spacing: 0.08em;"
)
STILE_VUOTO = f"color: {COLORE_GRIGIO}; font-size: 13px; padding: 8px 0;"


class ClickableFrame(QFrame):
    def __init__(self, parent=None, on_click=None):
        super().__init__(parent)
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(event)


class DashboardView(BaseView):
    """View per la Dashboard principale"""

    def __init__(self, property_service, transaction_service, deadline_service,
                 preferences_service, main_window, translation_manager, logger,
                 user_prefs_service=None, parent=None):
        self.logger              = logger
        self.deadline_service    = deadline_service
        self.main_window         = main_window
        self.preferences_service = preferences_service
        self.tm                  = translation_manager
        self.user_prefs_service  = user_prefs_service

        self.proprieta         = sorted(property_service.get_all(), key=lambda p: p["id"])
        self.selected_property = None

        self._saved_property_index = 0
        self._saved_period_index   = 0

        super().__init__(property_service, transaction_service, None, parent)

    # ──────────────────────────────────────────────────────────────
    #  Helpers preferenze
    # ──────────────────────────────────────────────────────────────

    def _currency(self) -> str:
        if self.user_prefs_service:
            return self.user_prefs_service.get_currency()
        return "€"

    def _fmt(self, value: float) -> str:
        return format_currency(value, symbol=self._currency())

    def _warning_days(self) -> int:
        """Giorni di preavviso scadenze letti dal DB, 7 se non impostati."""
        if self.user_prefs_service:
            return self.user_prefs_service.get_deadline_warning_days()
        return 7

    def _t(self, categoria: str, chiave: str, fallback: str) -> str:
        return self.tm.get(categoria, chiave, fallback=fallback)

    # ──────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────

    def setup_ui(self):
        layout = self.layout()
        if layout is not None:
            self.clear_layout(layout)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(14)

        layout.addLayout(self._costruisci_header())
        layout.addLayout(self._costruisci_indicatori())

        centro = QHBoxLayout()
        centro.setSpacing(14)
        centro.addWidget(self._costruisci_card_saldo(), stretch=2)
        centro.addWidget(self._costruisci_card_scadenze(), stretch=3)
        layout.addLayout(centro, stretch=1)

        layout.addWidget(self._costruisci_card_transazioni(), stretch=0)

        self._righe_mostrate = self._righe_visibili()
        self.aggiorna_dati()

    def _righe_visibili(self) -> int:
        """Righe nelle liste: 5 su schermi bassi, fino a 8 su finestre alte."""
        return 8 if self.height() >= 900 else 5

    def resizeEvent(self, event):
        super().resizeEvent(event)
        righe = self._righe_visibili()
        if getattr(self, "_righe_mostrate", None) not in (None, righe):
            self._righe_mostrate = righe
            self.aggiorna_dati()

    # ── header ────────────────────────────────────────────────────
    def _costruisci_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)

        titolo = QLabel(self.tm.get("ETICHETTE", "PANORAMICA"))
        titolo.setStyleSheet(default_title_style)
        header.addWidget(titolo)
        header.addStretch()

        header.addWidget(self._etichetta_selettore(self.tm.get("ETICHETTE", "PROPRIETA")))
        self.property_selector = QComboBox()
        self.property_selector.addItem(self.tm.get("ETICHETTE", "ALL_PROPERTIES"), None)
        for p in self.proprieta:
            self.property_selector.addItem(p["name"], p["id"])
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        self.property_selector.setCurrentIndex(self._saved_property_index)
        self.property_selector.currentIndexChanged.connect(self.update_info_box)
        header.addWidget(self.property_selector)

        header.addWidget(self._etichetta_selettore(self.tm.get("ETICHETTE", "PERIODO")))
        self.period_selector = QComboBox()
        self.period_selector.setStyleSheet(default_combo_box_style)
        self.period_selector.addItems([
            self.tm.get("ETICHETTE", "1_MONTH"),
            self.tm.get("ETICHETTE", "6_MONTHS"),
            self.tm.get("ETICHETTE", "1_YEAR"),
            self.tm.get("ETICHETTE", "3_YEARS"),
        ])
        self.period_selector.setCurrentIndex(self._saved_period_index)
        self.period_selector.currentIndexChanged.connect(self.aggiorna_dati)
        header.addWidget(self.period_selector)

        header.addSpacing(8)
        self.language_combo = QComboBox()
        self.language_combo.addItem(QIcon(icon_path("flag-it.png")), "Italiano", "it")
        self.language_combo.addItem(QIcon(icon_path("flag-uk.png")), "English",  "en")
        self.language_combo.addItem(QIcon(icon_path("flag-es.png")), "Español",  "es")
        self.language_combo.setIconSize(QSize(18, 18))
        self.language_combo.setStyleSheet(default_combo_box_style)
        self.language_combo.setFixedWidth(140)
        current_lang = self.preferences_service.get_language()
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        header.addWidget(self.language_combo)
        return header

    @staticmethod
    def _etichetta_selettore(testo: str) -> QLabel:
        lbl = QLabel(f"{testo}:")
        lbl.setStyleSheet(f"color: {COLORE_TESTO_SECONDARIO}; font-size: 12px;")
        return lbl

    # ── indicatori ────────────────────────────────────────────────
    def _costruisci_indicatori(self) -> QHBoxLayout:
        riga = QHBoxLayout()
        riga.setSpacing(14)
        self.kpi_saldo    = self._tile(COLORE_ITEM_SELEZIONATO, self.tm.get("ETICHETTE", "SALDO"), "FINANZE")
        self.kpi_entrate  = self._tile(COLORE_SUCCESS, self._t("DASHBOARD", "ENTRATE", "Entrate"), "TRANSAZIONI")
        self.kpi_uscite   = self._tile(COLORE_ERROR, self._t("DASHBOARD", "USCITE", "Uscite"), "TRANSAZIONI")
        self.kpi_scadenze = self._tile(COLORE_WARNING, self._t("DASHBOARD", "SCADENZE_APERTE", "Scadenze aperte"), "CALENDAR")
        for tile in (self.kpi_saldo, self.kpi_entrate, self.kpi_uscite, self.kpi_scadenze):
            riga.addWidget(tile["frame"], stretch=1)
        return riga

    def _tile(self, colore: str, etichetta: str, sezione: str) -> dict:
        """Riquadro indicatore: barra colorata, etichetta, valore grande, nota."""
        frame = self._card(sezione)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 12, 16, 12)
        lay.setSpacing(12)

        barra = QFrame()
        barra.setFixedSize(4, 40)
        barra.setStyleSheet(f"background-color: {colore}; border-radius: 2px;")
        lay.addWidget(barra)

        colonna = QVBoxLayout()
        colonna.setSpacing(2)
        lbl = QLabel(etichetta.upper())
        lbl.setStyleSheet(STILE_TITOLO_CARD)
        valore = QLabel("—")
        valore.setStyleSheet(f"font-size: 22px; font-weight: 600; color: {COLORE_BIANCO};")
        nota = QLabel("")
        nota.setStyleSheet(f"font-size: 11px; color: {COLORE_TESTO_SECONDARIO};")
        colonna.addWidget(lbl)
        colonna.addWidget(valore)
        colonna.addWidget(nota)
        lay.addLayout(colonna)
        lay.addStretch()
        return {"frame": frame, "valore": valore, "nota": nota}

    # ── card ──────────────────────────────────────────────────────
    def _card(self, sezione: str) -> ClickableFrame:
        frame = ClickableFrame(on_click=lambda: self.main_window.navigate_to_section(sezione))
        frame.setObjectName("card")
        frame.setStyleSheet(STILE_CARD)
        return frame

    def _card_con_titolo(self, sezione: str, titolo: str):
        """Card con intestazione; ritorna (frame, layout del contenuto)."""
        frame = self._card(sezione)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)
        lbl = QLabel(titolo.upper())
        lbl.setStyleSheet(STILE_TITOLO_CARD)
        lay.addWidget(lbl)
        return frame, lay

    def _costruisci_card_saldo(self) -> QFrame:
        frame, lay = self._card_con_titolo("FINANZE", self._t("DASHBOARD", "SALDO_PERIODO", "Saldo del periodo"))
        self.fig = Figure(figsize=(3.2, 3.2), facecolor=COLORE_WIDGET_2)
        self.fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
        self.chart_canvas = FigureCanvas(self.fig)
        self.chart_canvas.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.chart_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)
        lay.addWidget(self.chart_canvas, stretch=1)

        legenda = QHBoxLayout()
        legenda.setSpacing(18)
        legenda.addStretch()
        self.legenda_entrate = self._voce_legenda(COLORE_ITEM_SELEZIONATO)
        self.legenda_uscite  = self._voce_legenda(COLORE_GRIGIO)
        legenda.addWidget(self.legenda_entrate["widget"])
        legenda.addWidget(self.legenda_uscite["widget"])
        legenda.addStretch()
        lay.addLayout(legenda)
        return frame

    @staticmethod
    def _voce_legenda(colore: str) -> dict:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        pallino = QLabel()
        pallino.setPixmap(icona_pallino(colore, 9).pixmap(9, 9))
        testo = QLabel("")
        testo.setStyleSheet(f"font-size: 12px; color: {COLORE_BIANCO};")
        lay.addWidget(pallino)
        lay.addWidget(testo)
        return {"widget": w, "testo": testo}

    def _costruisci_card_scadenze(self) -> QFrame:
        frame, lay = self._card_con_titolo("CALENDAR", self._t("DASHBOARD", "PROSSIME_SCADENZE", "Prossime scadenze"))
        self.lista_scadenze = QVBoxLayout()
        self.lista_scadenze.setSpacing(0)
        lay.addLayout(self.lista_scadenze)
        lay.addStretch()
        return frame

    def _costruisci_card_transazioni(self) -> QFrame:
        frame, lay = self._card_con_titolo("TRANSAZIONI", self._t("DASHBOARD", "ULTIME_TRANSAZIONI", "Ultime transazioni"))
        self.lista_transazioni = QGridLayout()
        self.lista_transazioni.setHorizontalSpacing(14)
        self.lista_transazioni.setVerticalSpacing(0)
        lay.addLayout(self.lista_transazioni)
        lay.addStretch()
        return frame

    # ──────────────────────────────────────────────────────────────
    #  Dati
    # ──────────────────────────────────────────────────────────────

    def _periodo(self) -> tuple[datetime, datetime]:
        self._saved_period_index = self.period_selector.currentIndex()
        mesi = {0: 1, 1: 6, 2: 12, 3: 36}.get(self._saved_period_index, 1)
        fine = datetime.today()
        return fine - timedelta(days=30 * mesi), fine

    def aggiorna_dati(self):
        property_id = self.selected_property["id"] if self.selected_property else None
        inizio, fine = self._periodo()
        righe = self.transaction_service.get_all(
            property_id=property_id,
            start_date=inizio.strftime("%Y-%m-%d"),
            end_date=fine.strftime("%Y-%m-%d"),
        )
        entrate = sum(t["amount"] for t in righe if t["type"] == "Entrata")
        uscite  = sum(t["amount"] for t in righe if t["type"] == "Uscita")

        scadenze = sorted(
            self.deadline_service.get_all(property_id=property_id, include_completed=False),
            key=lambda d: d["due_date"],
        )
        oggi    = date.today()
        scadute = [d for d in scadenze if date.fromisoformat(d["due_date"][:10]) < oggi]

        self._aggiorna_indicatori(entrate, uscite, scadenze, scadute)
        self._aggiorna_ciambella(entrate, uscite)
        righe = self._righe_visibili()
        self._righe_mostrate = righe
        self._aggiorna_scadenze(scadenze[:righe], oggi)
        self._aggiorna_transazioni(self.transaction_service.get_all(property_id=property_id)[:righe])

    def _aggiorna_indicatori(self, entrate, uscite, scadenze, scadute):
        nel_periodo = self._t("DASHBOARD", "NEL_PERIODO", "nel periodo selezionato")
        saldo = entrate - uscite
        self.kpi_saldo["valore"].setText(self._fmt(saldo))
        self.kpi_saldo["valore"].setStyleSheet(
            f"font-size: 22px; font-weight: 600; color: {COLORE_BIANCO if saldo >= 0 else COLORE_ERROR};"
        )
        self.kpi_saldo["nota"].setText(nel_periodo)
        self.kpi_entrate["valore"].setText(self._fmt(entrate))
        self.kpi_entrate["nota"].setText(nel_periodo)
        self.kpi_uscite["valore"].setText(self._fmt(uscite))
        self.kpi_uscite["nota"].setText(nel_periodo)
        self.kpi_scadenze["valore"].setText(str(len(scadenze)))
        if scadute:
            testo = self._t("DASHBOARD", "SCADUTE_N", "XXX già scadute").replace("XXX", str(len(scadute)))
            self.kpi_scadenze["nota"].setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORE_ERROR};")
        else:
            testo = self._t("DASHBOARD", "NESSUNA_SCADUTA", "nessuna scaduta")
            self.kpi_scadenze["nota"].setStyleSheet(f"font-size: 11px; color: {COLORE_TESTO_SECONDARIO};")
        self.kpi_scadenze["nota"].setText(testo)

    def _aggiorna_ciambella(self, entrate: float, uscite: float):
        self.ax.clear()
        self.ax.set_aspect("equal")
        totale = entrate + uscite
        if totale == 0:
            self.ax.pie([1], colors=[mescola(COLORE_GRIGIO, COLORE_WIDGET_2, 0.5)], startangle=90,
                        wedgeprops=dict(width=0.32))
            self.ax.text(0, 0, self.tm.get("MESSAGGI", "NESSUN_DATO"),
                         ha="center", va="center", fontsize=10, color=COLORE_GRIGIO)
            self.legenda_entrate["testo"].setText(self.tm.get("ETICHETTE", "GUADAGNI"))
            self.legenda_uscite["testo"].setText(self.tm.get("ETICHETTE", "SPESE"))
        else:
            self.ax.pie([entrate, uscite], colors=[COLORE_ITEM_SELEZIONATO, COLORE_GRIGIO],
                        startangle=90, counterclock=False, wedgeprops=dict(width=0.32))
            self.ax.text(0, 0.08, self._fmt(entrate - uscite), ha="center", va="center",
                         fontsize=13, fontweight="bold", color=COLORE_BIANCO)
            self.ax.text(0, -0.16, self.tm.get("ETICHETTE", "SALDO"), ha="center", va="center",
                         fontsize=8, color=COLORE_GRIGIO)
            self.legenda_entrate["testo"].setText(
                f"{self.tm.get('ETICHETTE', 'GUADAGNI')}  {entrate / totale * 100:.0f}%")
            self.legenda_uscite["testo"].setText(
                f"{self.tm.get('ETICHETTE', 'SPESE')}  {uscite / totale * 100:.0f}%")
        self.chart_canvas.draw()

    def _aggiorna_scadenze(self, scadenze: list, oggi: date):
        self.clear_layout(self.lista_scadenze)
        if not scadenze:
            vuoto = QLabel(self.tm.get("ETICHETTE", "NESSUNA_SCADENZA"))
            vuoto.setStyleSheet(STILE_VUOTO)
            self.lista_scadenze.addWidget(vuoto)
            return

        ordine_ids   = [p["id"] for p in self.proprieta]
        nomi         = {p["id"]: p["name"] for p in self.proprieta}
        warning_days = self._warning_days()
        for indice, d in enumerate(scadenze):
            due = date.fromisoformat(d["due_date"][:10])
            stato, giorni = stato_scadenza(due, oggi, warning_days)
            self.lista_scadenze.addWidget(self._riga_scadenza(
                d, colore_proprieta(d.get("property_id"), ordine_ids),
                nomi.get(d.get("property_id"), self._t("CALENDARIO", "GENERALE", "Generale")),
                stato, giorni, due, ultima=(indice == len(scadenze) - 1),
            ))

    def _riga_scadenza(self, d: dict, colore: str, nome_proprieta: str,
                       stato: str, giorni: int, due: date, ultima: bool) -> QWidget:
        riga = QFrame()
        riga.setObjectName("riga")
        bordo = "none" if ultima else f"1px solid {COLORE_DIVISORE}"
        riga.setStyleSheet(f"QFrame#riga {{ border: none; border-bottom: {bordo}; }}")
        lay = QHBoxLayout(riga)
        lay.setContentsMargins(0, 7, 6, 7)
        lay.setSpacing(10)

        barra = QFrame()
        barra.setFixedSize(3, 30)
        barra.setStyleSheet(f"background-color: {colore}; border-radius: 1px;")
        lay.addWidget(barra)

        testi = QVBoxLayout()
        testi.setSpacing(1)
        titolo = QLabel(d["title"])
        titolo.setStyleSheet(f"font-size: 13px; color: {COLORE_BIANCO};")
        sotto = QLabel(f"{nome_proprieta}  ·  {due.strftime('%d/%m/%Y')}")
        sotto.setStyleSheet(f"font-size: 11px; color: {COLORE_TESTO_SECONDARIO};")
        testi.addWidget(titolo)
        testi.addWidget(sotto)
        lay.addLayout(testi, stretch=1)

        if stato == STATO_SCADUTA:
            testo = self._t("CALENDARIO", "SCADUTA_DA", "Scaduta da XXX giorni").replace("XXX", str(-giorni))
            col   = COLORE_ERROR
        elif stato == STATO_OGGI:
            testo, col = self.tm.get("ETICHETTE", "OGGI"), COLORE_ERROR
        elif giorni == 1:
            testo, col = self.tm.get("ETICHETTE", "DOMANI"), COLORE_WARNING
        else:
            testo = self.tm.get("ETICHETTE", "IN_X_GIORNI").replace("XXX", str(giorni))
            col   = COLORE_WARNING if stato == STATO_IMMINENTE else COLORE_VERDE_OK
        quando = QLabel(testo)
        quando.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {col};")
        lay.addWidget(quando)
        return riga

    def _aggiorna_transazioni(self, transazioni: list):
        self.clear_layout(self.lista_transazioni)
        if not transazioni:
            vuoto = QLabel(self.tm.get("MESSAGGI", "NESSUN_DATO"))
            vuoto.setStyleSheet(STILE_VUOTO)
            self.lista_transazioni.addWidget(vuoto, 0, 0, 1, 5)
            return

        for r, t in enumerate(transazioni):
            uscita = t["type"] == "Uscita"
            colore = COLORE_ERROR if uscita else COLORE_SUCCESS
            data_txt = date.fromisoformat(str(t["date"])[:10]).strftime("%d/%m/%Y")

            self.lista_transazioni.addWidget(self._cella(data_txt, COLORE_TESTO_SECONDARIO, 12), r, 0)
            self.lista_transazioni.addWidget(self._cella(t.get("provider") or "", COLORE_BIANCO, 13), r, 1)
            self.lista_transazioni.addWidget(self._cella(t.get("service") or "", COLORE_TESTO_SECONDARIO, 12), r, 2)
            importo = self._cella(f"{'−' if uscita else '+'} {self._fmt(t['amount'])}", COLORE_BIANCO, 13, peso=600)
            importo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.lista_transazioni.addWidget(importo, r, 3)
            self.lista_transazioni.addWidget(self._badge(t["type"], colore), r, 4)
        self.lista_transazioni.setColumnStretch(1, 3)
        self.lista_transazioni.setColumnStretch(2, 2)
        self.lista_transazioni.setColumnMinimumWidth(3, 110)

    @staticmethod
    def _cella(testo: str, colore: str, dimensione: int, peso: int = 400) -> QLabel:
        lbl = QLabel(testo)
        lbl.setStyleSheet(
            f"font-size: {dimensione}px; color: {colore}; font-weight: {peso}; padding: 6px 0;"
        )
        return lbl

    @staticmethod
    def _badge(testo: str, colore: str) -> QWidget:
        contenitore = QWidget()
        contenitore.setStyleSheet("background: transparent;")
        esterno = QHBoxLayout(contenitore)
        esterno.setContentsMargins(0, 0, 0, 0)
        esterno.setAlignment(Qt.AlignmentFlag.AlignRight)
        badge = QFrame()
        badge.setFixedHeight(22)
        badge.setStyleSheet(
            f"QFrame {{ background-color: {tinta(colore, 0.14)}; border-radius: 11px; }}"
            f"QLabel {{ background: transparent; color: {COLORE_BIANCO}; font-size: 12px; }}"
        )
        lay = QHBoxLayout(badge)
        lay.setContentsMargins(9, 0, 10, 0)
        lay.setSpacing(6)
        pallino = QLabel()
        pallino.setPixmap(icona_pallino(colore, 7).pixmap(7, 7))
        lay.addWidget(pallino)
        lay.addWidget(QLabel(testo))
        esterno.addWidget(badge)
        return contenitore

    # ──────────────────────────────────────────────────────────────
    #  Lingua
    # ──────────────────────────────────────────────────────────────

    def on_language_changed(self):
        self.change_language(self.language_combo.currentData())

    def change_language(self, lang_code):
        self._saved_property_index = self.property_selector.currentIndex()
        self._saved_period_index   = self.period_selector.currentIndex()
        self.preferences_service.set_language(lang_code)
        self.tm.set_language(lang_code)

        if hasattr(self.main_window, 'menu'):
            self.main_window.menu.blockSignals(True)
        if hasattr(self.main_window, 'update_menu_items'):
            self.main_window.update_menu_items()
            self.main_window.menu.setCurrentRow(0)
        if hasattr(self.main_window, 'menu'):
            self.main_window.menu.blockSignals(False)

        self.proprieta = sorted(self.property_service.get_all(), key=lambda p: p["id"])
        self.setup_ui()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item   = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())

    # ──────────────────────────────────────────────────────────────
    #  Selezione proprietà
    # ──────────────────────────────────────────────────────────────

    def update_info_box(self, index):
        self._saved_property_index = index
        if index == 0:
            self.selected_property = None
        elif 0 < index <= len(self.proprieta):
            self.selected_property = self.proprieta[index - 1]
        self.aggiorna_dati()
