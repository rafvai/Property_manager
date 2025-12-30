import os
import shutil
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QWidget
)

from views.base_view import BaseView
from styles import *
from translations_manager import get_translation_manager


class SettingsView(BaseView):
    """View per le impostazioni dell'applicazione"""

    def __init__(self, property_service, transaction_service, parent=None):
        self.tm = get_translation_manager()
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia impostazioni"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("settings", "title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # --- LISTA IMPOSTAZIONI ---
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(8)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # Database
        self.add_setting_item(
            settings_layout,
            "💾 Backup Database",
            "Crea una copia di sicurezza dei tuoi dati",
            self.backup_database
        )

        self.add_setting_item(
            settings_layout,
            "📥 Ripristina Database",
            "Ripristina i dati da un backup precedente",
            self.restore_database
        )

        # Documenti
        self.add_setting_item(
            settings_layout,
            "📂 Apri Cartella Documenti",
            "Visualizza tutti i documenti salvati",
            self.open_documents_folder
        )

        # Export
        self.add_setting_item(
            settings_layout,
            "📊 Apri Cartella Export",
            "Visualizza tutti i report esportati",
            self.open_exports_folder
        )

        self.add_setting_item(
            settings_layout,
            "🗑️ Pulisci Export Vecchi",
            "Elimina automaticamente i report più vecchi di 30 giorni",
            self.clean_old_exports
        )

        # Info
        self.add_info_section(settings_layout)

        settings_layout.addStretch()
        main_layout.addWidget(settings_container)

    def add_setting_item(self, parent_layout, title, description, action):
        """Crea una riga di impostazioni cliccabile"""
        # Alterna colori
        index = parent_layout.count()
        bg_color = COLORE_RIGA_1 if index % 2 == 0 else COLORE_RIGA_2

        item = QFrame()
        item.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 15px 20px;
            }}
            QFrame:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        item.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Testo
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 15px; font-weight: 600;")
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Freccia
        arrow_label = QLabel("›")
        arrow_label.setStyleSheet("color: #95a5a6; font-size: 24px; font-weight: bold;")
        layout.addWidget(arrow_label)

        # Click handler
        def mousePressEvent(event):
            if event.button() == Qt.MouseButton.LeftButton:
                action()

        item.mousePressEvent = mousePressEvent

        parent_layout.addWidget(item)

    def add_info_section(self, parent_layout):
        """Aggiunge sezione informazioni app"""
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORE_SECONDARIO}; margin: 20px 0px; max-height: 2px;")
        parent_layout.addWidget(separator)

        # Info compatta
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 8px;
                padding: 20px;
            }}
        """)

        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)

        app_name = QLabel("🏠 Property Manager")
        app_name.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(app_name)

        version = QLabel("Versione 1.0.0")
        version.setStyleSheet("color: #95a5a6; font-size: 12px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(version)

        parent_layout.addWidget(info_frame)

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