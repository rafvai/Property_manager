from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QMessageBox
)
from datetime import datetime

from styles import *
from views.base_view import BaseView
from translations_manager import get_translation_manager


class PropertiesView(BaseView):
    """View per la gestione delle proprietà"""

    def __init__(self, property_service, transaction_service, document_service, deadline_service, parent=None):
        self.deadline_service = deadline_service
        self.document_service = document_service
        self.tm = get_translation_manager()
        super().__init__(property_service, transaction_service, document_service, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia proprietà"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("properties", "title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Bottone aggiungi
        add_btn = QPushButton(self.tm.get("properties", "add_property"))
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_property)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # --- BARRA RICERCA ---
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tm.get("properties", "search_placeholder"))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid #007BFF;
            }}
        """)
        self.search_input.textChanged.connect(self.filter_properties)
        search_layout.addWidget(self.search_input)

        main_layout.addLayout(search_layout)

        # --- AREA SCROLLABILE PER LE CARD ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORE_BACKGROUND};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)

        # Container per le card
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(scroll_area)

        # Carica le proprietà
        self.load_properties()

    def load_properties(self, search_text=""):
        """Carica e visualizza tutte le proprietà"""
        # Pulisci layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Recupera proprietà
        properties = self.property_service.get_all()

        # Filtra per ricerca
        if search_text:
            search_lower = search_text.lower()
            properties = [
                p for p in properties
                if search_lower in p['name'].lower() or search_lower in p['address'].lower()
            ]

        # Se non ci sono proprietà
        if not properties:
            no_data_label = QLabel(self.tm.get("properties", "no_properties"))
            no_data_label.setStyleSheet("color: #bdc3c7; font-size: 16px; padding: 40px;")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            self.cards_layout.addStretch()
            return

        # Crea card per ogni proprietà
        for index, prop in enumerate(properties):
            card = self.create_property_card(prop, index)
            self.cards_layout.addWidget(card)

        # Spacer finale
        self.cards_layout.addStretch()

    def get_property_stats(self, property_id):
        """Calcola statistiche avanzate per una proprietà"""
        # Recupera tutte le transazioni
        transactions = self.transaction_service.get_all(property_id=property_id)

        # Data prima transazione (data di inizio gestione)
        start_date = None
        if transactions:
            dates = [datetime.strptime(t['date'], '%d/%m/%Y') for t in transactions]
            start_date = min(dates)

        # Calcola saldo
        saldo = self.transaction_service.get_balance(property_id=property_id)

        # Conta transazioni per tipo
        num_entrate = len([t for t in transactions if t['type'] == 'Entrata'])
        num_uscite = len([t for t in transactions if t['type'] == 'Uscita'])

        # Conta documenti
        docs = self.document_service.list_documents(property_id)
        num_docs = len(docs)

        # Conta scadenze attive e totali
        deadlines_active = self.deadline_service.get_all(property_id=property_id, include_completed=False)
        deadlines_total = self.deadline_service.get_all(property_id=property_id, include_completed=True)
        num_deadlines_active = len(deadlines_active)
        num_deadlines_completed = len(deadlines_total) - num_deadlines_active

        # Calcola media mensile entrate/uscite
        entrate_totali = sum(t['amount'] for t in transactions if t['type'] == 'Entrata')
        uscite_totali = sum(t['amount'] for t in transactions if t['type'] == 'Uscita')

        # Calcola mesi di gestione
        mesi_gestione = 0
        if start_date:
            delta = datetime.now() - start_date
            mesi_gestione = max(1, delta.days // 30)

        media_entrate = entrate_totali / mesi_gestione if mesi_gestione > 0 else 0
        media_uscite = uscite_totali / mesi_gestione if mesi_gestione > 0 else 0

        return {
            'saldo': saldo,
            'start_date': start_date,
            'num_entrate': num_entrate,
            'num_uscite': num_uscite,
            'num_docs': num_docs,
            'num_deadlines_active': num_deadlines_active,
            'num_deadlines_completed': num_deadlines_completed,
            'media_entrate': media_entrate,
            'media_uscite': media_uscite,
            'mesi_gestione': mesi_gestione
        }

    def create_property_card(self, prop, index):
        """Crea una card compatta e professionale per una proprietà"""
        # Alternanza colori
        bg_color = COLORE_RIGA_1 if index % 2 == 0 else COLORE_RIGA_2

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 15px 20px;
            }}
        """)

        # Layout principale
        main_layout = QVBoxLayout(card)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- RIGA 1: NOME E AZIONI ---
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        # Nome proprietà
        name_label = QLabel(f"{prop['name']}")
        name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        top_row.addWidget(name_label)

        top_row.addStretch()

        # Bottoni azioni
        edit_btn = QPushButton(self.tm.get("common", "edit"))
        edit_btn.setFixedHeight(28)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_property(prop))
        top_row.addWidget(edit_btn)

        delete_btn = QPushButton(self.tm.get("common", "delete"))
        delete_btn.setFixedHeight(28)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_property(prop))
        top_row.addWidget(delete_btn)

        main_layout.addLayout(top_row)

        # --- RIGA 2: INFO BASE ---
        info_row = QHBoxLayout()
        info_row.setSpacing(20)

        # Indirizzo
        address_label = QLabel(f"{self.tm.get("common", "address")}: {prop['address']}")
        address_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_row.addWidget(address_label, stretch=2)

        # Proprietario
        owner_label = QLabel(f"{self.tm.get("common", "owner")}: {prop['owner']}")
        owner_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_row.addWidget(owner_label, stretch=1)

        main_layout.addLayout(info_row)

        # --- RIGA 3: STATISTICHE ---
        stats = self.get_property_stats(prop['id'])

        stats_row = QHBoxLayout()
        stats_row.setSpacing(25)

        # Gestita dal
        if stats['start_date']:
            start_str = stats['start_date'].strftime('%d/%m/%Y')
            managed_label = QLabel(f"Gestita dal: {start_str}")
            managed_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
            stats_row.addWidget(managed_label)

        # Saldo
        saldo_color = "#2ecc71" if stats['saldo'] >= 0 else "#e74c3c"
        saldo_label = QLabel(f"Saldo: {stats['saldo']:,.2f}€")
        saldo_label.setStyleSheet(f"color: {saldo_color}; font-size: 12px; font-weight: bold;")
        stats_row.addWidget(saldo_label)

        # Transazioni
        trans_label = QLabel(f"{self.tm.get("report", "transactions")}: {stats['num_entrate']} entrate, {stats['num_uscite']} uscite")
        trans_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        stats_row.addWidget(trans_label)

        # Documenti
        docs_label = QLabel(f"{self.tm.get("documents", "title")}: {stats['num_docs']}")
        docs_label.setStyleSheet("color: #3498db; font-size: 11px;")
        stats_row.addWidget(docs_label)

        # Scadenze
        deadline_color = "#e74c3c" if stats['num_deadlines_active'] > 0 else "#95a5a6"
        deadline_label = QLabel(f"{self.tm.get("properties", "deadlines")}: {stats['num_deadlines_active']} attive")
        deadline_label.setStyleSheet(f"color: {deadline_color}; font-size: 11px;")
        stats_row.addWidget(deadline_label)

        # Media mensile
        if stats['mesi_gestione'] > 0:
            avg_label = QLabel(f"Media mensile: +{stats['media_entrate']:,.0f}€ / -{stats['media_uscite']:,.0f}€")
            avg_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
            stats_row.addWidget(avg_label)

        stats_row.addStretch()
        main_layout.addLayout(stats_row)

        return card

    def add_property(self):
        """Dialog per aggiungere una nuova proprietà"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuova Proprietà")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Es: Casa Via Roma")
        address_input = QLineEdit()
        address_input.setPlaceholderText("Es: Via Roma 10, Milano")
        owner_input = QLineEdit()
        owner_input.setPlaceholderText("Es: Mario Rossi")

        layout.addRow("Nome*:", name_input)
        layout.addRow(f"{self.tm.get("common", "address")}*:", address_input)
        layout.addRow(f"{self.tm.get("common", "owner")}*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, "Errore", "Tutti i campi sono obbligatori!")
                return

            property_id = self.property_service.create(nome, indirizzo, proprietario)

            if property_id:
                QMessageBox.information(self, "Successo", f"Proprietà '{nome}' aggiunta con successo!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile aggiungere la proprietà.")

    def edit_property(self, prop):
        """Dialog per modificare una proprietà esistente"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifica Proprietà: {prop['name']}")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = QLineEdit(prop['name'])
        address_input = QLineEdit(prop['address'])
        owner_input = QLineEdit(prop['owner'])

        layout.addRow("Nome*:", name_input)
        layout.addRow(f"{self.tm.get("common", "address")}*:", address_input)
        layout.addRow(f"{self.tm.get("common", "owner")}*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, "Errore", "Tutti i campi sono obbligatori!")
                return

            success = self.property_service.update(
                prop['id'],
                name=nome,
                address=indirizzo,
                owner=proprietario
            )

            if success:
                QMessageBox.information(self, "Successo", "Proprietà aggiornata con successo!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile aggiornare la proprietà.")

    def delete_property(self, prop):
        """Elimina una proprietà con conferma"""
        reply = QMessageBox.question(
            self,
            "Conferma Eliminazione",
            f"Sei sicuro di voler eliminare '{prop['name']}'?\n\n"
            "ATTENZIONE: Verranno eliminate anche tutte le transazioni, documenti e scadenze associate!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Elimina transazioni associate
            transactions = self.transaction_service.get_all(property_id=prop['id'])
            for trans in transactions:
                self.transaction_service.delete(trans['id'])

            # Elimina scadenze associate
            deadlines = self.deadline_service.get_all(property_id=prop['id'], include_completed=True)
            for deadline in deadlines:
                self.deadline_service.delete(deadline['id'])

            # Elimina proprietà
            success = self.property_service.delete(prop['id'])

            if success:
                QMessageBox.information(self, "Successo", f"Proprietà '{prop['name']}' eliminata con successo!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile eliminare la proprietà.")

    def filter_properties(self, text):
        """Filtra le proprietà in base al testo di ricerca"""
        self.load_properties(search_text=text)