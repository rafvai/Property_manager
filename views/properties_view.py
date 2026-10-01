from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from styles import (
    COLORE_BACKGROUND,
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_SECONDARIO,
    COLORE_SUCCESS,
    COLORE_WARNING,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_dialog_style,
    default_style_search_line,
    default_title_style,
)
from validation_utils import format_currency
from views.base_view import BaseView
from views.calendar_planner import colore_proprieta

COLORE_TESTO_SECONDARIO = "#94a3b8"
COLORI_CLASSE_ENERGETICA = {
    "A+++": "#1a7a1a", "A++": "#1a7a1a", "A+": "#2ecc71", "A": "#2ecc71",
    "B": "#a8d45a", "C": "#f1c40f", "D": "#f39c12",
    "E": "#e67e22", "F": "#e74c3c", "G": "#c0392b",
}
STILE_TITOLO_INDICATORE = (
    f"font-size: 10px; font-weight: 600; color: {COLORE_GRIGIO}; letter-spacing: 0.08em;"
)
STILE_BOTTONE_CARD = f"""
    QPushButton {{
        background: transparent; color: {COLORE_BIANCO}; border: 1px solid #334155;
        border-radius: 6px; padding: 5px 14px; font-size: 12px; min-width: 70px;
    }}
    QPushButton:hover {{ border-color: {COLORE_ITEM_HOVER}; background-color: #263449; }}
"""
STILE_BOTTONE_CARD_ELIMINA = STILE_BOTTONE_CARD.replace(
    f"border-color: {COLORE_ITEM_HOVER}", f"border-color: {COLORE_ERROR}; color: {COLORE_ERROR}"
)


class PropertiesView(BaseView):
    """View per la gestione delle proprietà"""

    def __init__(self, property_service, transaction_service, document_service,
                 deadline_service, translation_service, logger,
                 user_prefs_service=None, parent=None):
        self.deadline_service   = deadline_service
        self.document_service   = document_service
        self.tm                 = translation_service
        self.logger             = logger
        self.user_prefs_service = user_prefs_service
        super().__init__(property_service, transaction_service, document_service, parent)

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
        """Giorni di preavviso scadenze letti dal DB."""
        if self.user_prefs_service:
            return self.user_prefs_service.get_deadline_warning_days()
        return 7

    # ──────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(self.tm.get("ETICHETTE", "LE_MIE_PROPRIETA"))
        title.setStyleSheet(default_title_style)
        header_layout.addWidget(title)
        header_layout.addStretch()

        add_btn = QPushButton(f"+ {self.tm.get('PULSANTI', 'AGGIUNGI')}")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_property)
        header_layout.addWidget(add_btn)
        main_layout.addLayout(header_layout)

        # Barra ricerca
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "CERCA"))
        self.search_input.setStyleSheet(default_style_search_line)
        self.search_input.textChanged.connect(self.filter_properties)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Area scrollabile
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{
                background-color: {COLORE_BACKGROUND}; width: 12px; border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORE_SECONDARIO}; border-radius: 6px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background-color: {COLORE_ITEM_HOVER}; }}
        """)

        self.cards_container = QWidget()
        self.cards_layout    = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(scroll_area)
        self.load_properties()

    def load_properties(self, search_text=""):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        properties = self.property_service.get_all()
        ordine_ids = sorted(p['id'] for p in properties)

        if search_text:
            search_lower = search_text.lower()
            properties = [
                p for p in properties
                if search_lower in p['name'].lower()
                or search_lower in p['address'].lower()
            ]

        if not properties and not search_text:
            self.cards_layout.addWidget(self._card_prima_proprieta())
            self.cards_layout.addStretch()
            return

        if not properties:
            no_data_label = QLabel(
                self.tm.get("ETICHETTE", "NESSUNA_PROPRIETA_TROVATA")
            )
            no_data_label.setStyleSheet(
                "color: #bdc3c7; font-size: 16px; padding: 40px;"
            )
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            self.cards_layout.addStretch()
            return

        # Legge warning_days una sola volta per tutto il loop
        warning_days = self._warning_days()

        for prop in properties:
            card = self.create_property_card(prop, ordine_ids, warning_days)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _card_prima_proprieta(self) -> QFrame:
        """Stato vuoto guidato: invito ad aggiungere la prima proprietà o aprire la guida."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {COLORE_WIDGET_2}; border-radius: 10px; }}
            QLabel {{ background: transparent; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 48, 40, 48)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titolo = QLabel(self.tm.get("GUIDA", "PRIMA_PROPRIETA_TITOLO"))
        titolo.setStyleSheet("color: white; font-size: 20px; font-weight: 700;")
        titolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titolo)

        testo = QLabel(self.tm.get("GUIDA", "PRIMA_PROPRIETA_TESTO"))
        testo.setStyleSheet(f"color: {COLORE_GRIGIO}; font-size: 14px;")
        testo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        testo.setWordWrap(True)
        layout.addWidget(testo)

        bottoni = QHBoxLayout()
        bottoni.setSpacing(12)
        bottoni.addStretch()
        aggiungi = QPushButton(self.tm.get("GUIDA", "PRIMA_PROPRIETA_BOTTONE"))
        aggiungi.setStyleSheet(default_aggiungi_button)
        aggiungi.setFixedHeight(38)
        aggiungi.clicked.connect(self.add_property)
        bottoni.addWidget(aggiungi)
        guida = QPushButton(self.tm.get("GUIDA", "APRI_GUIDA"))
        guida.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: white; border: 1px solid #334155;
                           border-radius: 6px; padding: 0 18px; font-size: 14px; }}
            QPushButton:hover {{ border-color: {COLORE_ITEM_HOVER}; }}
        """)
        guida.setFixedHeight(38)
        guida.clicked.connect(lambda: self.window().open_guide("PROPRIETA"))
        bottoni.addWidget(guida)
        bottoni.addStretch()
        layout.addLayout(bottoni)
        return card

    def get_property_stats(self, property_id):
        transactions = self.transaction_service.get_all(property_id=property_id)

        start_date = None
        if transactions:
            dates = [
                t['date'] if hasattr(t['date'], 'year')
                else datetime.strptime(str(t['date']), '%Y-%m-%d').date()
                for t in transactions
            ]
            start_date = min(dates)

        saldo = self.transaction_service.get_balance(property_id=property_id)

        docs     = self.document_service.list_documents(property_id)
        num_docs = len(docs)

        deadlines_active = self.deadline_service.get_all(
            property_id=property_id, include_completed=False
        )
        deadlines_total = self.deadline_service.get_all(
            property_id=property_id, include_completed=True
        )
        num_deadlines_active    = len(deadlines_active)
        num_deadlines_completed = len(deadlines_total) - num_deadlines_active

        entrate_totali = sum(
            t['amount'] for t in transactions if t['type'] == 'Entrata'
        )
        uscite_totali = sum(
            t['amount'] for t in transactions if t['type'] == 'Uscita'
        )

        mesi_gestione = 0
        if start_date:
            delta         = datetime.now().date() - start_date
            mesi_gestione = max(1, delta.days // 30)

        media_entrate = entrate_totali / mesi_gestione if mesi_gestione > 0 else 0
        media_uscite  = uscite_totali  / mesi_gestione if mesi_gestione > 0 else 0

        return {
            'saldo':                    saldo,
            'start_date':               start_date,
            'num_docs':                 num_docs,
            'num_deadlines_active':     num_deadlines_active,
            'num_deadlines_completed':  num_deadlines_completed,
            'media_entrate':            media_entrate,
            'media_uscite':             media_uscite,
            'mesi_gestione':            mesi_gestione,
        }

    def _count_upcoming_deadlines(self, property_id, warning_days: int) -> int:
        """
        Conta le scadenze imminenti (entro warning_days) per questa proprietà.
        Usa DeadlineService.get_upcoming() se disponibile, altrimenti filtra
        manualmente le scadenze attive.
        """
        try:
            # get_upcoming è il nuovo metodo aggiunto a DeadlineService
            upcoming = self.deadline_service.get_upcoming(
                warning_days=warning_days,
                property_id=property_id,
            )
            return len(upcoming)
        except AttributeError:
            # Fallback compatibile con versioni precedenti del service
            today    = date.today()
            from datetime import timedelta
            deadline_limit = today + timedelta(days=warning_days)
            all_active = self.deadline_service.get_all(
                property_id=property_id, include_completed=False
            )
            return sum(
                1 for d in all_active
                if d.get('due_date') and today <= _parse_date(d['due_date']) <= deadline_limit
            )

    def create_property_card(self, prop, ordine_ids: list, warning_days: int):
        """
        Card proprietà in stile dashboard: barra colore, dati, indicatori, azioni.

        Il colore delle scadenze segue tre stati:
          - Rosso     → ci sono scadenze già scadute
          - Arancione → ci sono scadenze entro warning_days giorni (preferenza DB)
          - Grigio    → nessuna scadenza imminente
        """
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                border: 1px solid transparent;
            }}
            QFrame#card:hover {{ border: 1px solid {COLORE_ITEM_HOVER}; }}
            QLabel {{ background: transparent; border: none; }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 14, 16, 14)
        layout.setSpacing(18)

        barra = QFrame()
        barra.setFixedWidth(4)
        barra.setStyleSheet(
            f"background-color: {colore_proprieta(prop['id'], ordine_ids)}; border-radius: 2px;"
        )
        layout.addWidget(barra)

        stats = self.get_property_stats(prop['id'])

        # Colonna dati: nome, indirizzo, metadati
        dati = QVBoxLayout()
        dati.setSpacing(4)
        nome = QLabel(prop['name'])
        nome.setStyleSheet(f"color: {COLORE_BIANCO}; font-size: 16px; font-weight: 600;")
        dati.addWidget(nome)
        indirizzo = QLabel(prop['address'])
        indirizzo.setStyleSheet(f"color: {COLORE_TESTO_SECONDARIO}; font-size: 12px;")
        dati.addWidget(indirizzo)
        metadati = self._metadati_proprieta(prop, stats)
        if metadati:
            meta_label = QLabel(metadati)
            meta_label.setTextFormat(Qt.TextFormat.RichText)
            meta_label.setStyleSheet(f"color: {COLORE_GRIGIO}; font-size: 11px;")
            dati.addWidget(meta_label)
        dati.addStretch()
        layout.addLayout(dati, stretch=1)

        # Indicatori
        saldo_colore = COLORE_SUCCESS if stats['saldo'] >= 0 else COLORE_ERROR
        layout.addWidget(self._indicatore(
            self.tm.get('ETICHETTE', 'SALDO'), self._fmt(stats['saldo']), saldo_colore, larghezza=150
        ))

        num_active   = stats['num_deadlines_active']
        num_overdue  = len(self.deadline_service.get_overdue(property_id=prop['id']))
        num_upcoming = self._count_upcoming_deadlines(prop['id'], warning_days)
        if num_overdue > 0:
            scadenze_colore = COLORE_ERROR
            scadenze_nota   = self.tm.get("DASHBOARD", "SCADUTE_N").replace("XXX", str(num_overdue))
        elif num_upcoming > 0:
            scadenze_colore = COLORE_WARNING
            scadenze_nota   = self.tm.get("ETICHETTE", "IMMINENTI_N").replace("XXX", str(num_upcoming))
        else:
            scadenze_colore = COLORE_BIANCO if num_active else COLORE_GRIGIO
            scadenze_nota   = self.tm.get("DASHBOARD", "NESSUNA_SCADUTA")
        layout.addWidget(self._indicatore(
            self.tm.get('ETICHETTE', 'SCADENZE'), str(num_active), scadenze_colore, scadenze_nota,
            larghezza=150,
        ))

        if stats['mesi_gestione'] > 0:
            media = f"+{self._fmt(stats['media_entrate'])}  /  -{self._fmt(stats['media_uscite'])}"
        else:
            media = "—"
        layout.addWidget(self._indicatore(
            self.tm.get('ETICHETTE', 'MEDIA_MENSILE'), media,
            COLORE_BIANCO if stats['mesi_gestione'] > 0 else COLORE_GRIGIO, larghezza=230,
        ))

        # Azioni
        azioni = QVBoxLayout()
        azioni.setSpacing(6)
        edit_btn = QPushButton(self.tm.get("PULSANTI", "MODIFICA"))
        edit_btn.setStyleSheet(STILE_BOTTONE_CARD)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_property(prop))
        azioni.addWidget(edit_btn)
        delete_btn = QPushButton(self.tm.get("PULSANTI", "ELIMINA"))
        delete_btn.setStyleSheet(STILE_BOTTONE_CARD_ELIMINA)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_property(prop))
        azioni.addWidget(delete_btn)
        azioni.addStretch()
        layout.addLayout(azioni)

        return card

    def _metadati_proprieta(self, prop, stats) -> str:
        """Riga di metadati separati da punto: gestore, superficie, classe, inizio gestione."""
        voci = []
        if prop.get('managed_by'):
            voci.append(f"{self.tm.get('ETICHETTE', 'GESTITA_DA')} {prop['managed_by']}")
        if prop.get('square_meters'):
            mq = prop['square_meters']
            voci.append(f"{int(mq) if mq == int(mq) else mq} m²")
        if prop.get('energy_class'):
            colore = COLORI_CLASSE_ENERGETICA.get(prop['energy_class'], COLORE_GRIGIO)
            voci.append(
                f"{self.tm.get('ETICHETTE', 'CLASSE_ENERGETICA')} "
                f'<span style="color:{colore}; font-weight:600;">{prop["energy_class"]}</span>'
            )
        if stats['start_date']:
            voci.append(f"{self.tm.get('ETICHETTE', 'DAL')} {stats['start_date'].strftime('%d/%m/%Y')}")
        return "  ·  ".join(voci)

    @staticmethod
    def _indicatore(etichetta: str, valore: str, colore_valore: str, nota: str = "",
                    larghezza: int = 150) -> QWidget:
        """Indicatore in stile dashboard: etichetta in maiuscoletto, valore, nota facoltativa."""
        box = QWidget()
        box.setFixedWidth(larghezza)
        box.setStyleSheet("background: transparent;")
        colonna = QVBoxLayout(box)
        colonna.setContentsMargins(0, 0, 0, 0)
        colonna.setSpacing(2)
        titolo = QLabel(etichetta.upper())
        titolo.setStyleSheet(STILE_TITOLO_INDICATORE)
        colonna.addWidget(titolo)
        testo_valore = QLabel(valore)
        testo_valore.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {colore_valore};")
        colonna.addWidget(testo_valore)
        if nota:
            testo_nota = QLabel(nota)
            testo_nota.setStyleSheet(f"font-size: 11px; color: {COLORE_TESTO_SECONDARIO};")
            colonna.addWidget(testo_nota)
        colonna.addStretch()
        return box

    # ──────────────────────────────────────────────────────────────
    #  CRUD
    # ──────────────────────────────────────────────────────────────

    def add_property(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tm.get("ETICHETTE", "NUOVA_PROPRIETA"))
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "55_BEATIFUL_APARTMENT"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'NOME_PROPRIETA')}*:", name_input)

        address_input = QLineEdit()
        address_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "VIA_APPARTAMENTO"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'INDIRIZZO')}*:", address_input)

        managed_by_input = QLineEdit()
        managed_by_input.setPlaceholderText("es. Agenzia Immobiliare Rossi")
        layout.addRow(f"{self.tm.get('ETICHETTE', 'GESTITA_DA')}:", managed_by_input)

        sqm_input = QLineEdit()
        sqm_input.setPlaceholderText("es. 75")
        layout.addRow(f"{self.tm.get('ETICHETTE', 'METRI_QUADRI')}:", sqm_input)

        energy_combo = QComboBox()
        energy_combo.addItem(self.tm.get('ETICHETTE', "NON_SPECIFICATO"), None)
        for cls in ["A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"]:
            energy_combo.addItem(cls, cls)
        layout.addRow("Classe energetica:", energy_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()

            if not nome or not indirizzo:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                    "Nome e indirizzo sono obbligatori!")
                return

            managed_by = managed_by_input.text().strip() or None
            energy_class = energy_combo.currentData()
            square_meters = None
            raw_sqm = sqm_input.text().strip()
            if raw_sqm:
                try:
                    square_meters = float(raw_sqm.replace(",", "."))
                except ValueError:
                    QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                        "Metri quadri non validi.")
                    return

            property_id = self.property_service.create(
                nome, indirizzo,
                managed_by=managed_by,
                square_meters=square_meters,
                energy_class=energy_class,
            )
            if property_id:
                QMessageBox.information(self, self.tm.get("MESSAGGI", "SUCCESSO"),
                                        f"{nome}: {self.tm.get('MESSAGGI', 'PROPRIETA_AGGIUNTA')}")
                self.load_properties()
            else:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                    self.tm.get("MESSAGGI", "IMPOSSIBILE_AGGIUNGERE_PROPRIETA"))

    def edit_property(self, prop):
        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"{self.tm.get('ETICHETTE', 'MODIFICA_PROPRIETA')}: {prop['name']}"
        )
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit(prop['name'])
        address_input = QLineEdit(prop['address'])
        layout.addRow(f"{self.tm.get('ETICHETTE', 'NOME_PROPRIETA')}*:", name_input)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'INDIRIZZO')}*:", address_input)

        managed_by_input = QLineEdit(prop.get('managed_by') or "")
        managed_by_input.setPlaceholderText("es. Agenzia Immobiliare Rossi")
        layout.addRow(f"{self.tm.get('ETICHETTE', 'GESTITA_DA')}:", managed_by_input)

        sqm_input = QLineEdit(
            str(int(prop['square_meters']))
            if prop.get('square_meters') and prop['square_meters'] == int(prop['square_meters'])
            else str(prop['square_meters']) if prop.get('square_meters') else ""
        )
        sqm_input.setPlaceholderText("es. 75")
        layout.addRow(f"{self.tm.get('ETICHETTE', 'METRI_QUADRI')}:", sqm_input)

        energy_combo = QComboBox()
        energy_combo.addItem(self.tm.get('ETICHETTE', "NON_SPECIFICATO"), None)
        for cls in ["A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"]:
            energy_combo.addItem(cls, cls)
        current_ec = prop.get('energy_class')
        if current_ec:
            idx = energy_combo.findData(current_ec)
            if idx >= 0:
                energy_combo.setCurrentIndex(idx)
        layout.addRow("Classe energetica:", energy_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()

            if not nome or not indirizzo:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                    self.tm.get("ETICHETTE", "TUTTI_CAMPI_OBBLIGATORI"))
                return

            managed_by = managed_by_input.text().strip() or None
            energy_class = energy_combo.currentData()

            square_meters = None
            raw_sqm = sqm_input.text().strip()
            if raw_sqm:
                try:
                    square_meters = float(raw_sqm.replace(",", "."))
                except ValueError:
                    QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                        "Metri quadri non validi.")
                    return

            success = self.property_service.update(
                prop['id'],
                name=nome,
                address=indirizzo,
                managed_by=managed_by,
                square_meters=square_meters,
                energy_class=energy_class,
                _clear_managed_by=(managed_by is None),
                _clear_square_meters=(square_meters is None),
                _clear_energy_class=(energy_class is None),
            )
            if success:
                QMessageBox.information(self, self.tm.get("MESSAGGI", "SUCCESSO"),
                                        self.tm.get("MESSAGGI", "PROPRIETA_AGGIORNATA"))
                self.load_properties()
            else:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), "")

    def delete_property(self, prop):
        transactions = self.transaction_service.get_all(property_id=prop['id'])
        deadlines    = self.deadline_service.get_all(
            property_id=prop['id'], include_completed=True
        )
        folder_size_bytes = self.document_service.get_property_folder_size(prop['id'])
        folder_size_str   = self.document_service.format_size(folder_size_bytes)

        warning_message = (
            self.tm.get("MESSAGGI", "CONFERMA_ELIMINA")
            .replace('?', f"{prop['name']} ?")
        )

        reply = QMessageBox.question(
            self,
            self.tm.get("MESSAGGI", "CONFERMA_ELIMINA"),
            warning_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        error_messages = []
        try:
            deleted_trans = sum(
                1 for t in transactions
                if self.transaction_service.delete(t['id'])
            )
            if deleted_trans < len(transactions):
                error_messages.append(
                    f"⚠️ Solo {deleted_trans}/{len(transactions)} transazioni eliminate"
                )

            deleted_deadlines = sum(
                1 for d in deadlines
                if self.deadline_service.delete(d['id'])
            )
            if deleted_deadlines < len(deadlines):
                error_messages.append(
                    f"⚠️ Solo {deleted_deadlines}/{len(deadlines)} scadenze eliminate"
                )

            folder_result = self.document_service.delete_property_folder(prop['id'])
            success       = self.property_service.delete(prop['id'])

            if success:
                success_message = self.tm.get("MESSAGGI", "PROPRIETA_ELIMINATA")
                if folder_result['success']:
                    success_message += (
                        f"📁 Documenti eliminati: {folder_result['files_deleted']}\n"
                        f"🗑️ Cartelle eliminate: {folder_result['folders_deleted']}\n"
                        f"💾 Spazio liberato: {folder_size_str}\n"
                    )
                elif folder_result['error']:
                    error_messages.append(
                        f"⚠️ Cartella documenti: {folder_result['error']}"
                    )

                success_message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                if error_messages:
                    success_message += "\n\n⚠️ Avvisi:\n" + "\n".join(error_messages)

                QMessageBox.information(
                    self, "✅ Eliminazione Completata", success_message
                )
                self.load_properties()
                self._clean_orphaned_document_folders()
            else:
                QMessageBox.warning(
                    self, self.tm.get("MESSAGGI", "ERRORE"),
                    "Impossibile eliminare la proprietà dal database."
                )

        except Exception as e:
            QMessageBox.critical(
                self, self.tm.get("MESSAGGI", "ERRORE"),
                f"Si è verificato un errore:\n\n{str(e)}"
            )

    def filter_properties(self, text):
        self.load_properties(search_text=text)

    def _clean_orphaned_document_folders(self):
        try:
            from services.document_service import get_docs_dir
            docs_dir  = get_docs_dir()
            if not docs_dir.exists():
                return
            valid_ids = {p['id'] for p in self.property_service.get_all()}
            for tenant_dir in docs_dir.iterdir():
                if not tenant_dir.is_dir():
                    continue
                for folder_path in tenant_dir.iterdir():
                    if not folder_path.is_dir():
                        continue
                    if not folder_path.name.startswith("property_"):
                        continue
                    try:
                        prop_id = int(folder_path.name.split("_")[1])
                        if prop_id not in valid_ids:
                            import shutil
                            shutil.rmtree(folder_path)
                            self.logger.info(
                                f"Cartella orfana rimossa: {folder_path.name}"
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Impossibile rimuovere cartella orfana: {e}"
                        )
        except Exception as e:
            self.logger.warning(f"Pulizia cartelle orfane fallita: {e}")


# ──────────────────────────────────────────────────────────────────
#  Helper locale
# ──────────────────────────────────────────────────────────────────

def _parse_date(due_date_value) -> date:
    """Converte il campo due_date (str o date) in un oggetto date."""
    if isinstance(due_date_value, date):
        return due_date_value
    return datetime.strptime(due_date_value, '%Y-%m-%d').date()
