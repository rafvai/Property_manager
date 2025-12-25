import os
import shutil
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QScrollArea, QWidget,
    QGroupBox
)

from views.base_view import BaseView
from styles import *


class SettingsView(BaseView):
    """View per le impostazioni dell'applicazione"""

    def __init__(self, property_service, transaction_service, parent=None):
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia impostazioni"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel("⚙️ Impostazioni")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # --- SCROLL AREA ---
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

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # === SEZIONE DATABASE ===
        db_group = self.create_section(
            "💾 Database",
            "Gestisci il database dell'applicazione"
        )
        db_layout = QVBoxLayout()

        # Info database
        db_info = self.create_info_card(
            "📊 Statistiche Database",
            self.get_database_stats()
        )
        db_layout.addWidget(db_info)

        # Pulsanti database
        db_buttons_layout = QHBoxLayout()
        db_buttons_layout.setSpacing(10)

        backup_btn = QPushButton("💾 Backup Database")
        backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        backup_btn.clicked.connect(self.backup_database)
        db_buttons_layout.addWidget(backup_btn)

        restore_btn = QPushButton("📥 Ripristina Database")
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        restore_btn.clicked.connect(self.restore_database)
        db_buttons_layout.addWidget(restore_btn)

        db_buttons_layout.addStretch()
        db_layout.addLayout(db_buttons_layout)

        db_group.layout().addLayout(db_layout)
        scroll_layout.addWidget(db_group)

        # === SEZIONE DOCUMENTI ===
        docs_group = self.create_section(
            "📁 Gestione Documenti",
            "Gestisci i documenti e le cartelle"
        )
        docs_layout = QVBoxLayout()

        # Info documenti
        docs_info = self.create_info_card(
            "📊 Statistiche Documenti",
            self.get_documents_stats()
        )
        docs_layout.addWidget(docs_info)

        # Pulsanti documenti
        docs_buttons_layout = QHBoxLayout()
        docs_buttons_layout.setSpacing(10)

        open_docs_btn = QPushButton("📂 Apri Cartella Documenti")
        open_docs_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        open_docs_btn.clicked.connect(self.open_documents_folder)
        docs_buttons_layout.addWidget(open_docs_btn)

        docs_buttons_layout.addStretch()
        docs_layout.addLayout(docs_buttons_layout)

        docs_group.layout().addLayout(docs_layout)
        scroll_layout.addWidget(docs_group)

        # === SEZIONE EXPORT ===
        export_group = self.create_section(
            "📤 Export",
            "Gestisci i file esportati"
        )
        export_layout = QVBoxLayout()

        # Info export
        export_info = self.create_info_card(
            "📊 Statistiche Export",
            self.get_exports_stats()
        )
        export_layout.addWidget(export_info)

        # Pulsanti export
        export_buttons_layout = QHBoxLayout()
        export_buttons_layout.setSpacing(10)

        open_exports_btn = QPushButton("📂 Apri Cartella Export")
        open_exports_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        open_exports_btn.clicked.connect(self.open_exports_folder)
        export_buttons_layout.addWidget(open_exports_btn)

        clean_exports_btn = QPushButton("🗑️ Pulisci Export Vecchi")
        clean_exports_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        clean_exports_btn.clicked.connect(self.clean_old_exports)
        export_buttons_layout.addWidget(clean_exports_btn)

        export_buttons_layout.addStretch()
        export_layout.addLayout(export_buttons_layout)

        export_group.layout().addLayout(export_layout)
        scroll_layout.addWidget(export_group)

        # === SEZIONE INFO APPLICAZIONE ===
        info_group = self.create_section(
            "ℹ️ Informazioni",
            "Dettagli sull'applicazione"
        )
        info_layout = QVBoxLayout()

        app_info = self.create_info_card(
            "🏠 Property Manager MVP",
            [
                "Versione: 1.0.0",
                "Sviluppato con: Python & PySide6",
                "Database: SQLite",
                "",
                "📧 Supporto: support@propertymanager.com",
                "🌐 Web: www.propertymanager.com"
            ]
        )
        info_layout.addWidget(app_info)

        info_group.layout().addLayout(info_layout)
        scroll_layout.addWidget(info_group)

        # Spacer finale
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def create_section(self, title, description):
        """Crea una sezione con titolo e descrizione"""
        group = QGroupBox()
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 12px;
                padding: 20px;
                margin-top: 10px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(15)

        # Titolo
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        # Descrizione
        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 13px; color: #bdc3c7;")
        layout.addWidget(desc_label)

        # Separatore
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORE_BACKGROUND}; max-height: 2px;")
        layout.addWidget(separator)

        return group

    def create_info_card(self, title, info_list):
        """Crea una card informativa"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Titolo card
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        # Info
        for info in info_list:
            info_label = QLabel(info)
            info_label.setStyleSheet("font-size: 12px; color: #ecf0f1;")
            layout.addWidget(info_label)

        return card

    def get_database_stats(self):
        """Recupera statistiche database"""
        try:
            properties = self.property_service.get_all()
            transactions = self.transaction_service.get_all()

            db_path = "property_manager.db"
            db_size = os.path.getsize(db_path) / 1024  # KB

            return [
                f"🏠 Proprietà: {len(properties)}",
                f"💰 Transazioni: {len(transactions)}",
                f"💾 Dimensione DB: {db_size:.2f} KB",
                f"📍 Percorso: {os.path.abspath(db_path)}"
            ]
        except Exception as e:
            return [f"❌ Errore nel recupero dati: {str(e)}"]

    def get_documents_stats(self):
        """Recupera statistiche documenti"""
        try:
            docs_dir = "docs"
            if not os.path.exists(docs_dir):
                return ["📁 Nessuna cartella documenti trovata"]

            total_files = 0
            total_size = 0

            for root, dirs, files in os.walk(docs_dir):
                total_files += len(files)
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

            total_size_mb = total_size / (1024 * 1024)

            return [
                f"📄 Totale documenti: {total_files}",
                f"💾 Spazio occupato: {total_size_mb:.2f} MB",
                f"📍 Percorso: {os.path.abspath(docs_dir)}"
            ]
        except Exception as e:
            return [f"❌ Errore: {str(e)}"]

    def get_exports_stats(self):
        """Recupera statistiche export"""
        try:
            exports_dir = "exports"
            if not os.path.exists(exports_dir):
                return ["📁 Nessun export presente"]

            files = os.listdir(exports_dir)
            total_size = sum(
                os.path.getsize(os.path.join(exports_dir, f))
                for f in files if os.path.isfile(os.path.join(exports_dir, f))
            )
            total_size_mb = total_size / (1024 * 1024)

            return [
                f"📊 Export totali: {len(files)}",
                f"💾 Spazio occupato: {total_size_mb:.2f} MB",
                f"📍 Percorso: {os.path.abspath(exports_dir)}"
            ]
        except Exception as e:
            return [f"❌ Errore: {str(e)}"]

    def backup_database(self):
        """Crea backup del database"""
        try:
            db_path = "property_manager.db"
            if not os.path.exists(db_path):
                QMessageBox.warning(self, "Errore", "Database non trovato!")
                return

            # Chiedi dove salvare
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"backup_property_manager_{timestamp}.db"

            backup_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salva Backup Database",
                default_name,
                "Database Files (*.db);;All Files (*)"
            )

            if backup_path:
                shutil.copy2(db_path, backup_path)
                QMessageBox.information(
                    self,
                    "✅ Backup Completato",
                    f"Database salvato con successo!\n\n📁 {backup_path}"
                )

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante il backup:\n{str(e)}")

    def restore_database(self):
        """Ripristina database da backup"""
        reply = QMessageBox.question(
            self,
            "⚠️ Conferma Ripristino",
            "Sei sicuro di voler ripristinare il database?\n\n"
            "⚠️ ATTENZIONE: Tutti i dati attuali verranno sovrascritti!\n"
            "Questa operazione è IRREVERSIBILE!\n\n"
            "Assicurati di aver fatto un backup prima di procedere.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                backup_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Seleziona Backup Database",
                    "",
                    "Database Files (*.db);;All Files (*)"
                )

                if backup_path:
                    db_path = "property_manager.db"
                    shutil.copy2(backup_path, db_path)

                    QMessageBox.information(
                        self,
                        "✅ Ripristino Completato",
                        "Database ripristinato con successo!\n\n"
                        "⚠️ Riavvia l'applicazione per applicare le modifiche."
                    )

            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante il ripristino:\n{str(e)}")

    def open_documents_folder(self):
        """Apri cartella documenti"""
        docs_dir = "docs"
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)

        os.startfile(os.path.abspath(docs_dir))

    def open_exports_folder(self):
        """Apri cartella export"""
        exports_dir = "exports"
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        os.startfile(os.path.abspath(exports_dir))

    def clean_old_exports(self):
        """Pulisci export vecchi (>30 giorni)"""
        try:
            exports_dir = "exports"
            if not os.path.exists(exports_dir):
                QMessageBox.information(self, "Info", "Nessun export da pulire.")
                return

            files = os.listdir(exports_dir)
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (30 * 24 * 60 * 60)

            for file in files:
                file_path = os.path.join(exports_dir, file)
                if os.path.isfile(file_path):
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1

            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "✅ Pulizia Completata",
                    f"Eliminati {deleted_count} file più vecchi di 30 giorni."
                )
            else:
                QMessageBox.information(
                    self,
                    "Info",
                    "Nessun file da eliminare (tutti più recenti di 30 giorni)."
                )

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante la pulizia:\n{str(e)}")