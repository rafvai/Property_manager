from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QMessageBox
)

from styles import *
from views.base_view import BaseView


class PropertiesView(BaseView):
    """View per la gestione delle proprietà"""

    def __init__(self, property_service, transaction_service, document_service, deadline_service, parent=None):
        self.deadline_service = deadline_service
        self.document_service = document_service
        super().__init__(property_service, transaction_service, document_service, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia proprietà"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel("🏠 Le mie proprietà")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Bottone aggiungi
        add_btn = QPushButton("+ Aggiungi proprietà")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_property)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # --- BARRA RICERCA ---
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cerca per nome o indirizzo...")
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
        self.cards_layout.setSpacing(15)
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
            no_data_label = QLabel("📭 Nessuna proprietà trovata")
            no_data_label.setStyleSheet("color: #bdc3c7; font-size: 16px; padding: 40px;")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            self.cards_layout.addStretch()
            return

        # Crea card per ogni proprietà
        for prop in properties:
            card = self.create_property_card(prop)
            self.cards_layout.addWidget(card)

        # Spacer finale
        self.cards_layout.addStretch()

    def create_property_card(self, prop):
        """Crea una card per una proprietà"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 12px;
                padding: 15px;
            }}
            QFrame:hover {{
                background-color: {COLORE_SECONDARIO};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        # --- INFO PRINCIPALI ---
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # Nome
        name_label = QLabel(f"🏡 {prop['name']}")
        name_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        info_layout.addWidget(name_label)

        # Indirizzo
        address_label = QLabel(f"📍 {prop['address']}")
        address_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        info_layout.addWidget(address_label)

        # Proprietario
        owner_label = QLabel(f"👤 {prop['owner']}")
        owner_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        info_layout.addWidget(owner_label)

        layout.addLayout(info_layout)

        # --- SEPARATORE ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORE_BACKGROUND}; max-height: 2px;")
        layout.addWidget(separator)

        # --- STATISTICHE ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        # Calcola statistiche
        saldo = self.transaction_service.get_balance(property_id=prop['id'])

        # Conta documenti
        docs = self.document_service.list_documents(prop['id'])  # 🔧 Usa ID
        num_docs = len(docs)

        # Conta scadenze attive
        deadlines = self.deadline_service.get_all(property_id=prop['id'], include_completed=False)
        num_deadlines = len(deadlines)

        # Saldo
        saldo_color = "#2ecc71" if saldo >= 0 else "#e74c3c"
        saldo_icon = "💰" if saldo >= 0 else "⚠️"
        saldo_label = QLabel(f"{saldo_icon} Saldo: {saldo:,.2f}€")
        saldo_label.setStyleSheet(f"color: {saldo_color}; font-size: 13px; font-weight: bold;")
        stats_layout.addWidget(saldo_label)

        # Documenti
        docs_label = QLabel(f"📄 {num_docs} doc")
        docs_label.setStyleSheet("color: #3498db; font-size: 13px;")
        stats_layout.addWidget(docs_label)

        # Scadenze
        deadline_label = QLabel(f"⏰ {num_deadlines} scadenze")
        deadline_label.setStyleSheet("color: #f39c12; font-size: 13px;")
        stats_layout.addWidget(deadline_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # --- BOTTONI AZIONI ---
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Bottone Modifica
        edit_btn = QPushButton("✏️ Modifica")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_property(prop))
        buttons_layout.addWidget(edit_btn)

        # Bottone Elimina
        delete_btn = QPushButton("🗑️ Elimina")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_property(prop))
        buttons_layout.addWidget(delete_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        return card

    def add_property(self):
        """Dialog per aggiungere una nuova proprietà"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuova proprietà")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Es: Casa Via Roma")
        address_input = QLineEdit()
        address_input.setPlaceholderText("Es: Via Roma 10, Milano")
        owner_input = QLineEdit()
        owner_input.setPlaceholderText("Es: Mario Rossi")

        layout.addRow("Nome*:", name_input)
        layout.addRow("Indirizzo*:", address_input)
        layout.addRow("Proprietario*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, "Campi obbligatori", "Compila tutti i campi!")
                return

            property_id = self.property_service.create(nome, indirizzo, proprietario)

            if property_id:
                QMessageBox.information(self, "Successo", f"Proprietà '{nome}' aggiunta!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile aggiungere la proprietà.")

    def edit_property(self, prop):
        """Dialog per modificare una proprietà esistente"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifica: {prop['name']}")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = QLineEdit(prop['name'])
        address_input = QLineEdit(prop['address'])
        owner_input = QLineEdit(prop['owner'])

        layout.addRow("Nome*:", name_input)
        layout.addRow("Indirizzo*:", address_input)
        layout.addRow("Proprietario*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, "Campi obbligatori", "Compila tutti i campi!")
                return

            success = self.property_service.update(
                prop['id'],
                name=nome,
                address=indirizzo,
                owner=proprietario
            )

            if success:
                QMessageBox.information(self, "Successo", "Proprietà aggiornata!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile aggiornare la proprietà.")

    def delete_property(self, prop):
        """Elimina una proprietà con conferma"""
        reply = QMessageBox.question(
            self,
            "Conferma eliminazione",
            f"Sei sicuro di voler eliminare '{prop['name']}'?\n\n"
            f"⚠️ ATTENZIONE: Verranno eliminate anche:\n"
            f"• Tutte le transazioni associate\n"
            f"• Tutte le scadenze associate\n"
            f"• I documenti NON verranno eliminati\n\n"
            f"Questa operazione è IRREVERSIBILE!",
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
                QMessageBox.information(self, "Successo", f"Proprietà '{prop['name']}' eliminata!")
                self.load_properties()
            else:
                QMessageBox.warning(self, "Errore", "Impossibile eliminare la proprietà.")

    def filter_properties(self, text):
        """Filtra le proprietà in base al testo di ricerca"""
        self.load_properties(search_text=text)
