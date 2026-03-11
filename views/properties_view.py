import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QMessageBox
)
from datetime import datetime

from styles import *
from views.base_view import BaseView

class PropertiesView(BaseView):
    """View per la gestione delle proprietà"""

    def __init__(self, property_service, transaction_service, document_service, deadline_service, translation_service, logger, parent=None):
        self.deadline_service = deadline_service
        self.document_service = document_service
        self.tm = translation_service
        self.logger = logger
        super().__init__(property_service, transaction_service, document_service, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia proprietà"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("ETICHETTE", "LE_MIE_PROPRIETA"))
        title.setStyleSheet(default_title_style)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Bottone aggiungi
        add_btn = QPushButton(f"+ {self.tm.get("PULSANTI", "AGGIUNGI")}")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_property)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # --- BARRA RICERCA ---
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "CERCA"))
        self.search_input.setStyleSheet(default_style_search_line)
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
            no_data_label = QLabel(self.tm.get("ETICHETTE", "NESSUNA_PROPRIETA_TROVATA"))
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
        edit_btn = QPushButton(self.tm.get("PULSANTI", "MODIFICA"))
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

        delete_btn = QPushButton(self.tm.get("PULSANTI", "ELIMINA"))
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
        address_label = QLabel(f"{self.tm.get("ETICHETTE", "INDIRIZZO")}: {prop['address']}")
        address_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_row.addWidget(address_label)

        # Proprietario
        owner_label = QLabel(f"{self.tm.get("ETICHETTE", "PROPRIETARIO")}: {prop['owner']}")
        owner_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_row.addWidget(owner_label)

        info_row.addStretch()
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

        # Scadenze
        deadline_color = "#e74c3c" if stats['num_deadlines_active'] > 0 else "#95a5a6"
        deadline_label = QLabel(f"{self.tm.get("ETICHETTE", "SCADENZE")}: {stats['num_deadlines_active']}")
        deadline_label.setStyleSheet(f"color: {deadline_color}; font-size: 11px;")
        stats_row.addWidget(deadline_label)

        # Media mensile
        if stats['mesi_gestione'] > 0:
            avg_label = QLabel(f"{self.tm.get("ETICHETTE", "MEDIA_MENSILE")}: +{stats['media_entrate']:,.0f}€ / -{stats['media_uscite']:,.0f}€")
            avg_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
            stats_row.addWidget(avg_label)

        # Saldo
        saldo_color = COLORE_SUCCESS if stats['saldo'] >= 0 else "#e74c3c"
        saldo_label = QLabel(f"{self.tm.get("ETICHETTE", "SALDO")}: {stats['saldo']:,.2f}€")
        saldo_label.setStyleSheet(f"color: {saldo_color}; font-size: 12px; font-weight: bold;")
        stats_row.addWidget(saldo_label)

        stats_row.addStretch()
        main_layout.addLayout(stats_row)

        return card

    def add_property(self):
        """Dialog per aggiungere una nuova proprietà"""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tm.get("ETICHETTE", "NUOVA_PROPRIETA"))
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "55_BEATIFUL_APARTMENT"))
        address_input = QLineEdit()
        address_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "VIA_APPARTAMENTO"))
        owner_input = QLineEdit()
        owner_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "PROPRIETARIO_NOME"))

        layout.addRow(f"{self.tm.get("ETICHETTE", "NOME_PROPRIETA")}*:", name_input)
        layout.addRow(f"{self.tm.get("ETICHETTE", "INDIRIZZO")}*:", address_input)
        layout.addRow(f"{self.tm.get("ETICHETTE", "PROPRIETARIO")}*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), "Tutti i campi sono obbligatori!")
                return

            property_id = self.property_service.create(nome, indirizzo, proprietario)

            if property_id:
                QMessageBox.information(self, self.tm.get("MESSAGGI", "SUCCESSO"), f"{nome}: {self.tm.get("MESSAGGI", "PROPRIETA_AGGIUNTA")}")
                self.load_properties()
            else:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), self.tm.get("MESSAGGI","IMPOSSIBILE_AGGIUNGERE_PROPRIETA"))

    def edit_property(self, prop):
        """Dialog per modificare una proprietà esistente"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.tm.get("ETICHETTE", "MODIFICA_PROPRIETA")}: {prop['name']}")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit(prop['name'])
        address_input = QLineEdit(prop['address'])
        owner_input = QLineEdit(prop['owner'])

        layout.addRow(f"{self.tm.get("ETICHETTE", "NOME_PROPRIETA")}*:", name_input)
        layout.addRow(f"{self.tm.get("ETICHETTE", "INDIRIZZO")}*:", address_input)
        layout.addRow(f"{self.tm.get("ETICHETTE", "PROPRIETARIO")}*:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if not nome or not indirizzo or not proprietario:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), self.tm.get("ETICHETTE","TUTTI_CAMPI_OBBLIGATORI"))
                return

            success = self.property_service.update(
                prop['id'],
                name=nome,
                address=indirizzo,
                owner=proprietario
            )

            if success:
                QMessageBox.information(self, self.tm.get("MESSAGGI", "SUCCESSO"), self.tm.get("MESSAGGI","PROPRIETA_AGGIORNATA"))
                self.load_properties()
            else:
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"), "")

    def delete_property(self, prop):
        """Elimina una proprietà con conferma e pulizia completa"""

        # Conta quanti dati verranno eliminati
        transactions = self.transaction_service.get_all(property_id=prop['id'])
        deadlines = self.deadline_service.get_all(property_id=prop['id'], include_completed=True)

        # Verifica cartella documenti e calcola dimensione
        folder_size_bytes = self.document_service.get_property_folder_size(prop['id'])
        folder_size_str = self.document_service.format_size(folder_size_bytes)
        property_folder = self.document_service.get_property_folder(prop['id'])
        has_documents = os.path.exists(property_folder)

        # Costruisci messaggio di conferma dettagliato
        warning_message = f"{self.tm.get("MESSAGGI","CONFERMA_ELIMINA").replace('?',f"{prop['name']} ?")}"

        reply = QMessageBox.question(
            self,
            self.tm.get("MESSAGGI","CONFERMA_ELIMINA"),
            warning_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            error_messages = []

            try:
                # 1. Elimina transazioni associate
                deleted_trans = 0
                for trans in transactions:
                    if self.transaction_service.delete(trans['id']):
                        deleted_trans += 1

                if deleted_trans < len(transactions):
                    error_messages.append(
                        f"⚠️ Solo {deleted_trans}/{len(transactions)} transazioni eliminate"
                    )

                # 2. Elimina scadenze associate
                deleted_deadlines = 0
                for deadline in deadlines:
                    if self.deadline_service.delete(deadline['id']):
                        deleted_deadlines += 1

                if deleted_deadlines < len(deadlines):
                    error_messages.append(
                        f"⚠️ Solo {deleted_deadlines}/{len(deadlines)} scadenze eliminate"
                    )

                # Elimina cartella documenti usando il service
                folder_result = self.document_service.delete_property_folder(prop['id'])

                # Elimina proprietà dal database
                success = self.property_service.delete(prop['id'])

                if success:
                    # Messaggio di successo dettagliato
                    success_message = self.tm.get("MESSAGGI","PROPRIETA_ELIMINATA")

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

                    success_message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

                    # Aggiungi eventuali warning
                    if error_messages:
                        success_message += f"\n\n⚠️ Avvisi:\n" + "\n".join(error_messages)

                    QMessageBox.information(
                        self,
                        "✅ Eliminazione Completata",
                        success_message
                    )
                    self.load_properties()
                else:
                    QMessageBox.warning(
                        self,
                        self.tm.get("MESSAGGI", "ERRORE"),
                        "Impossibile eliminare la proprietà dal database."
                    )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tm.get("MESSAGGI", "ERRORE"),
                    f"Si è verificato un errore durante l'eliminazione:\n\n{str(e)}\n\n"
                    f"La proprietà potrebbe essere stata eliminata solo parzialmente.\n"
                    f"Controlla manualmente i dati."
                )

    def filter_properties(self, text):
        """Filtra le proprietà in base al testo di ricerca"""
        self.load_properties(search_text=text)