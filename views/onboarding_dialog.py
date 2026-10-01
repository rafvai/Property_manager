"""
views/onboarding_dialog.py
==========================
Wizard di benvenuto al primo avvio: presentazione delle sezioni, preferenze
di base, prima proprietà e prossimi passi. Tutti i testi vengono dal DB
traduzioni (categoria ONBOARDING).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from resources import icon_path
from styles import (
    COLORE_BIANCO,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_WIDGET_2,
    default_combo_box_style,
    default_dialog_style,
)

NUMERO_PASSI = 4
LINGUE = [("it", "Italiano"), ("en", "English"), ("es", "Español")]
VALUTE = ["€", "$", "£"]
GIORNI_PREAVVISO = [1, 3, 7, 14, 30]

SEZIONI_PRESENTATE = [
    ("property.png",  "SEZIONE_PROPRIETA"),
    ("pie-chart.png", "SEZIONE_TRANSAZIONI"),
    ("security.png",  "SEZIONE_FORNITORI"),
    ("calendar.png",  "SEZIONE_CALENDAR"),
    ("document.png",  "SEZIONE_DOCUMENTS"),
    ("bar-chart.png", "SEZIONE_FINANZE"),
]

AZIONI_FINALI = [
    ("pie-chart.png", "AZIONE_TRANSAZIONE", "TRANSAZIONI"),
    ("security.png",  "AZIONE_FORNITORE",   "FORNITORI"),
    ("calendar.png",  "AZIONE_SCADENZA",    "CALENDAR"),
]

STILE_TITOLO_PAGINA = f"font-size: 20px; font-weight: 700; color: {COLORE_BIANCO};"
STILE_TESTO_PAGINA  = f"font-size: 13px; color: {COLORE_GRIGIO};"
STILE_PASSO         = f"font-size: 12px; color: {COLORE_GRIGIO};"
STILE_BOTTONE_SECONDARIO = f"""
    QPushButton {{
        background-color: transparent; color: {COLORE_BIANCO};
        border: 1px solid #334155; border-radius: 6px;
        padding: 10px 20px; font-size: 14px; min-width: 80px;
    }}
    QPushButton:hover {{ background-color: {COLORE_WIDGET_2}; border-color: {COLORE_ITEM_SELEZIONATO}; }}
    QPushButton:disabled {{ color: #475569; border-color: #1e293b; }}
"""
STILE_AZIONE = f"""
    QPushButton {{
        background-color: {COLORE_WIDGET_2}; color: {COLORE_BIANCO}; text-align: left;
        border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; font-size: 14px;
    }}
    QPushButton:hover {{ border-color: {COLORE_ITEM_HOVER}; background-color: #1e293b; }}
"""


class OnboardingDialog(QDialog):
    """Dialog a passi; al termine espone la sezione scelta e la proprietà creata."""

    def __init__(self, tm, user_prefs_service, preferences_service,
                 property_service, main_window, logger, parent=None):
        super().__init__(parent)
        self.tm                  = tm
        self.user_prefs_service  = user_prefs_service
        self.preferences_service = preferences_service
        self.property_service    = property_service
        self.main_window         = main_window
        self.logger              = logger

        self.sezione_scelta   = None
        self.proprieta_creata = None

        self.setWindowTitle(self._t("TITOLO"))
        self.setMinimumSize(680, 540)
        self.setStyleSheet(default_dialog_style)

        self._layout_principale = QVBoxLayout(self)
        self._layout_principale.setContentsMargins(32, 28, 32, 24)
        self._layout_principale.setSpacing(18)
        self._costruisci()

    # ──────────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────────

    def _t(self, chiave: str) -> str:
        return self.tm.get("ONBOARDING", chiave)

    @staticmethod
    def _svuota(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                OnboardingDialog._svuota(item.layout())

    def _etichetta(self, testo: str, stile: str) -> QLabel:
        label = QLabel(testo)
        label.setStyleSheet(stile)
        label.setWordWrap(True)
        return label

    def _riga_con_icona(self, icona: str, testo: str) -> QWidget:
        riga = QWidget()
        riga.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(riga)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        immagine = QLabel()
        immagine.setPixmap(QPixmap(icon_path(icona)).scaled(
            22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        immagine.setFixedWidth(26)
        layout.addWidget(immagine)
        layout.addWidget(self._etichetta(testo, f"font-size: 13px; color: {COLORE_BIANCO};"), stretch=1)
        return riga

    # ──────────────────────────────────────────────────────────────
    #  Costruzione (richiamata anche dopo un cambio lingua)
    # ──────────────────────────────────────────────────────────────

    def _costruisci(self, pagina_iniziale: int = 0):
        self._svuota(self._layout_principale)
        self.setWindowTitle(self._t("TITOLO"))

        self.etichetta_passo = QLabel()
        self.etichetta_passo.setStyleSheet(STILE_PASSO)
        self._layout_principale.addWidget(self.etichetta_passo)

        self.pagine = QStackedWidget()
        self.pagine.addWidget(self._pagina_benvenuto())
        self.pagine.addWidget(self._pagina_preferenze())
        self.pagine.addWidget(self._pagina_proprieta())
        self.pagine.addWidget(self._pagina_fine())
        self._layout_principale.addWidget(self.pagine, stretch=1)

        barra = QHBoxLayout()
        self.bottone_salta = QPushButton(self._t("SALTA"))
        self.bottone_salta.setStyleSheet(STILE_BOTTONE_SECONDARIO)
        self.bottone_salta.clicked.connect(self.reject)
        barra.addWidget(self.bottone_salta)
        barra.addStretch()

        self.bottone_indietro = QPushButton(self._t("INDIETRO"))
        self.bottone_indietro.setStyleSheet(STILE_BOTTONE_SECONDARIO)
        self.bottone_indietro.clicked.connect(self._indietro)
        barra.addWidget(self.bottone_indietro)

        self.bottone_avanti = QPushButton()
        self.bottone_avanti.clicked.connect(self._avanti)
        barra.addWidget(self.bottone_avanti)
        self._layout_principale.addLayout(barra)

        self.pagine.setCurrentIndex(pagina_iniziale)
        self._aggiorna_navigazione()

    def _pagina_benvenuto(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self._etichetta(self._t("BENVENUTO_TITOLO"), STILE_TITOLO_PAGINA))
        layout.addWidget(self._etichetta(self._t("BENVENUTO_TESTO"), STILE_TESTO_PAGINA))
        layout.addSpacing(6)
        for icona, chiave in SEZIONI_PRESENTATE:
            layout.addWidget(self._riga_con_icona(icona, self._t(chiave)))
        layout.addStretch()
        return pagina

    def _pagina_preferenze(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self._etichetta(self._t("PREFERENZE_TITOLO"), STILE_TITOLO_PAGINA))
        layout.addWidget(self._etichetta(self._t("PREFERENZE_TESTO"), STILE_TESTO_PAGINA))

        form = QFormLayout()
        form.setSpacing(14)
        form.setContentsMargins(0, 10, 0, 0)

        self.combo_lingua = QComboBox()
        self.combo_lingua.setStyleSheet(default_combo_box_style)
        for codice, nome in LINGUE:
            self.combo_lingua.addItem(nome, codice)
        self.combo_lingua.setCurrentIndex(
            max(0, [c for c, _ in LINGUE].index(self.tm.get_current_language())))
        form.addRow(f"{self._t('LINGUA')}:", self.combo_lingua)

        self.combo_valuta = QComboBox()
        self.combo_valuta.setStyleSheet(default_combo_box_style)
        self.combo_valuta.addItems(VALUTE)
        valuta_attuale = self.user_prefs_service.get_currency()
        if valuta_attuale in VALUTE:
            self.combo_valuta.setCurrentIndex(VALUTE.index(valuta_attuale))
        form.addRow(f"{self.tm.get('ETICHETTE', 'VALUTA')}:", self.combo_valuta)

        self.combo_preavviso = QComboBox()
        self.combo_preavviso.setStyleSheet(default_combo_box_style)
        for giorni in GIORNI_PREAVVISO:
            testo = self._t("GIORNO_1") if giorni == 1 else self._t("GIORNI_N").replace("XXX", str(giorni))
            self.combo_preavviso.addItem(testo, giorni)
        preavviso_attuale = self.user_prefs_service.get_deadline_warning_days()
        if preavviso_attuale in GIORNI_PREAVVISO:
            self.combo_preavviso.setCurrentIndex(GIORNI_PREAVVISO.index(preavviso_attuale))
        form.addRow(f"{self._t('GIORNI_PREAVVISO')}:", self.combo_preavviso)

        layout.addLayout(form)
        layout.addStretch()
        return pagina

    def _pagina_proprieta(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self._etichetta(self._t("PROPRIETA_TITOLO"), STILE_TITOLO_PAGINA))
        layout.addWidget(self._etichetta(self._t("PROPRIETA_TESTO"), STILE_TESTO_PAGINA))

        form = QFormLayout()
        form.setSpacing(14)
        form.setContentsMargins(0, 10, 0, 0)
        self.campo_nome = QLineEdit()
        self.campo_nome.setPlaceholderText(self.tm.get("PLACEHOLDER", "55_BEATIFUL_APARTMENT"))
        form.addRow(f"{self.tm.get('ETICHETTE', 'NOME_PROPRIETA')}*:", self.campo_nome)
        self.campo_indirizzo = QLineEdit()
        self.campo_indirizzo.setPlaceholderText(self.tm.get("PLACEHOLDER", "VIA_APPARTAMENTO"))
        form.addRow(f"{self.tm.get('ETICHETTE', 'INDIRIZZO')}*:", self.campo_indirizzo)
        layout.addLayout(form)

        self.etichetta_esito_proprieta = self._etichetta("", f"font-size: 13px; color: {COLORE_ITEM_HOVER};")
        layout.addWidget(self.etichetta_esito_proprieta)
        if self.proprieta_creata:
            self._mostra_proprieta_creata()
        layout.addStretch()
        return pagina

    def _pagina_fine(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self._etichetta(self._t("FINE_TITOLO"), STILE_TITOLO_PAGINA))
        layout.addWidget(self._etichetta(self._t("FINE_TESTO"), STILE_TESTO_PAGINA))
        layout.addSpacing(6)
        for icona, chiave, sezione in AZIONI_FINALI:
            bottone = QPushButton(f"   {self._t(chiave)}")
            bottone.setStyleSheet(STILE_AZIONE)
            bottone.setIcon(QPixmap(icon_path(icona)))
            bottone.clicked.connect(lambda _=False, s=sezione: self._vai_a(s))
            layout.addWidget(bottone)
        layout.addStretch()
        return pagina

    # ──────────────────────────────────────────────────────────────
    #  Navigazione
    # ──────────────────────────────────────────────────────────────

    def _aggiorna_navigazione(self):
        indice = self.pagine.currentIndex()
        self.etichetta_passo.setText(
            self._t("PASSO_DI").replace("XXX", str(indice + 1)).replace("YYY", str(NUMERO_PASSI)))
        self.bottone_indietro.setEnabled(indice > 0)
        ultima = indice == NUMERO_PASSI - 1
        self.bottone_avanti.setText(self._t("FINE") if ultima else self._t("AVANTI"))
        self.bottone_salta.setVisible(not ultima)

    def _indietro(self):
        self.pagine.setCurrentIndex(max(0, self.pagine.currentIndex() - 1))
        self._aggiorna_navigazione()

    def _avanti(self):
        indice = self.pagine.currentIndex()
        if indice == 1 and not self._applica_preferenze():
            return
        if indice == 2 and not self._salva_proprieta():
            return
        if indice == NUMERO_PASSI - 1:
            self._completa()
            self.accept()
            return
        self.pagine.setCurrentIndex(indice + 1)
        self._aggiorna_navigazione()

    def _vai_a(self, sezione: str):
        self.sezione_scelta = sezione
        self._completa()
        self.accept()

    def _completa(self):
        self.user_prefs_service.set_onboarding_completed()

    def reject(self):
        # Saltare o chiudere il tour conta come completato: non ricompare al prossimo avvio
        self._completa()
        super().reject()

    # ──────────────────────────────────────────────────────────────
    #  Azioni dei passi
    # ──────────────────────────────────────────────────────────────

    def _applica_preferenze(self) -> bool:
        self.user_prefs_service.set_currency(self.combo_valuta.currentText())
        self.user_prefs_service.set_deadline_warning_days(self.combo_preavviso.currentData())
        nuova_lingua = self.combo_lingua.currentData()
        if nuova_lingua != self.tm.get_current_language():
            self.main_window.apply_language(nuova_lingua)
            self._costruisci(pagina_iniziale=2)
            return False
        return True

    def _salva_proprieta(self) -> bool:
        nome      = self.campo_nome.text().strip()
        indirizzo = self.campo_indirizzo.text().strip()
        if not nome and not indirizzo:
            return True
        if not nome or not indirizzo:
            QMessageBox.warning(self, self._t("PROPRIETA_TITOLO"), self._t("PROPRIETA_INCOMPLETA"))
            return False
        if self.proprieta_creata == nome:
            return True
        nuovo_id = self.property_service.create(nome, indirizzo)
        if not nuovo_id:
            QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                self.tm.get("MESSAGGI", "IMPOSSIBILE_AGGIUNGERE_PROPRIETA"))
            return False
        self.proprieta_creata = nome
        self._mostra_proprieta_creata()
        return True

    def _mostra_proprieta_creata(self):
        self.etichetta_esito_proprieta.setText(
            self._t("PROPRIETA_CREATA").replace("XXX", self.proprieta_creata))
        self.campo_nome.setText(self.proprieta_creata)
        self.campo_nome.setEnabled(False)
        self.campo_indirizzo.setEnabled(False)
