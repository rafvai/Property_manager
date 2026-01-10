import os
import shutil
from datetime import datetime

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QWidget, QGraphicsDropShadowEffect, QDialog
)

from views.base_view import BaseView
from styles import *
from translations_manager import get_translation_manager


class SettingItem(QFrame):
    """Widget personalizzato per ogni elemento delle impostazioni con animazioni"""

    def __init__(self, icon, title, description, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.is_hovered = False

        # Stile base
        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                border: 2px solid transparent;
            }}
        """)

        # Ombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout principale
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(15)

        # Icona container
        icon_container = QFrame()
        icon_container.setFixedSize(50, 50)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_ITEM_SELEZIONATO};
                border-radius: 25px;
            }}
        """)
        icon_container_layout = QVBoxLayout(icon_container)
        icon_container_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_container_layout.addWidget(icon_label)

        layout.addWidget(icon_container)

        # Testo container
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        # Titolo
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: white; 
            font-size: 15px; 
            font-weight: 600;
            background: transparent;
        """)
        text_layout.addWidget(self.title_label)

        # Descrizione
        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet("""
            color: #95a5a6; 
            font-size: 12px;
            background: transparent;
        """)
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.desc_label)

        layout.addWidget(text_container, stretch=1)

        # Freccia
        self.arrow_label = QLabel("›")
        self.arrow_label.setStyleSheet("""
            color: #95a5a6; 
            font-size: 28px; 
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self.arrow_label)

        # Animazione per la freccia
        self.arrow_animation = QPropertyAnimation(self.arrow_label, b"pos")
        self.arrow_animation.setDuration(200)
        self.arrow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        """Hover in"""
        self.is_hovered = True
        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_ITEM_HOVER};
                border-radius: 10px;
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
            }}
        """)

        # Anima freccia verso destra
        current_pos = self.arrow_label.pos()
        self.arrow_animation.setStartValue(current_pos)
        self.arrow_animation.setEndValue(current_pos + Qt.QPoint(5, 0))
        self.arrow_animation.start()

        # Cambia colore freccia
        self.arrow_label.setStyleSheet(f"""
            color: {COLORE_ITEM_SELEZIONATO}; 
            font-size: 28px; 
            font-weight: bold;
            background: transparent;
        """)

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hover out"""
        self.is_hovered = False
        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                border: 2px solid transparent;
            }}
        """)

        # Riporta freccia alla posizione originale
        current_pos = self.arrow_label.pos()
        self.arrow_animation.setStartValue(current_pos)
        self.arrow_animation.setEndValue(current_pos - Qt.QPoint(5, 0))
        self.arrow_animation.start()

        # Ripristina colore freccia
        self.arrow_label.setStyleSheet("""
            color: #95a5a6; 
            font-size: 28px; 
            font-weight: bold;
            background: transparent;
        """)

        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Click handler"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Effetto click
            self.setStyleSheet(f"""
                SettingItem {{
                    background-color: {COLORE_ITEM_SELEZIONATO};
                    border-radius: 10px;
                    border: 2px solid {COLORE_ITEM_SELEZIONATO};
                }}
            """)

            # Esegui azione dopo breve delay (per mostrare l'effetto)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self.action)

        super().mousePressEvent(event)


class SettingsSection(QWidget):
    """Sezione raggruppata di impostazioni"""

    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        # Titolo sezione
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {COLORE_BIANCO};
            font-size: 16px;
            font-weight: bold;
            padding: 10px 5px;
            background: transparent;
        """)
        self.layout.addWidget(title_label)

    def add_item(self, item):
        """Aggiungi elemento alla sezione"""
        self.layout.addWidget(item)


class SettingsView(BaseView):
    """View per le impostazioni dell'applicazione - Versione migliorata"""

    def __init__(self, property_service, transaction_service, parent=None):
        self.tm = get_translation_manager()
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia impostazioni"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER SEMPLICE ---
        title = QLabel(self.tm.get('settings', 'title'))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        main_layout.addWidget(title)

        # --- SCROLL AREA ---
        from PySide6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORE_BACKGROUND};
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(25)
        scroll_layout.setContentsMargins(0, 0, 10, 0)

        # === SEZIONE LINGUA ===
        lang_section = SettingsSection(self.tm.get("settings", "language_section"))

        lang_section.add_item(SettingItem(
            "🌐",
            self.tm.get("settings", "change_language"),
            self.tm.get("settings", "change_language_desc"),
            self.change_language
        ))

        scroll_layout.addWidget(lang_section)

        # === SEZIONE DATABASE ===
        db_section = SettingsSection(self.tm.get("settings", "database_section"))

        db_section.add_item(SettingItem(
            "💾",
            self.tm.get("settings", "backup_db"),
            self.tm.get("settings", "backup_db_desc"),
            self.backup_database
        ))

        db_section.add_item(SettingItem(
            "📥",
            self.tm.get("settings", "restore_db"),
            self.tm.get("settings", "restore_db_desc"),
            self.restore_database
        ))

        scroll_layout.addWidget(db_section)

        # === SEZIONE GESTIONE FILE ===
        files_section = SettingsSection(self.tm.get("settings", "files_section"))

        files_section.add_item(SettingItem(
            "📊",
            self.tm.get("settings", "open_exports"),
            self.tm.get("settings", "open_exports_desc"),
            self.open_exports_folder
        ))

        files_section.add_item(SettingItem(
            "🗑️",
            self.tm.get("settings", "clean_exports"),
            self.tm.get("settings", "clean_exports_desc"),
            self.clean_old_exports
        ))

        files_section.add_item(SettingItem(
            "🗂️",
            self.tm.get("settings", "clean_orphaned"),
            self.tm.get("settings", "clean_orphaned_desc"),
            self.clean_orphaned_folders
        ))

        scroll_layout.addWidget(files_section)

        # === SEZIONE INFO ===
        scroll_layout.addStretch()

        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                padding: 15px;
                border: 1px solid {COLORE_SECONDARIO};
            }}
        """)

        info_layout = QHBoxLayout(info_frame)
        info_layout.setSpacing(15)

        app_icon = QLabel("🏠")
        app_icon.setStyleSheet("font-size: 32px; background: transparent;")
        info_layout.addWidget(app_icon)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        app_name = QLabel("Property Manager")
        app_name.setStyleSheet("""
            color: white; 
            font-size: 14px; 
            font-weight: bold;
            background: transparent;
        """)
        text_layout.addWidget(app_name)

        version = QLabel(self.tm.get("settings", "version"))
        version.setStyleSheet("""
            color: #95a5a6; 
            font-size: 11px;
            background: transparent;
        """)
        text_layout.addWidget(version)

        info_layout.addWidget(text_container)
        info_layout.addStretch()

        scroll_layout.addWidget(info_frame)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def change_language(self):
        """Dialog per cambiare lingua"""
        from PySide6.QtWidgets import QButtonGroup, QRadioButton

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tm.get("settings", "change_language"))
        dialog.setMinimumWidth(350)
        dialog.setStyleSheet(f"QDialog {{ background-color: {COLORE_BACKGROUND}; }}")

        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)

        # Titolo
        title = QLabel(self.tm.get("settings", "select_language"))
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Radio buttons per lingue
        lang_group = QButtonGroup(dialog)

        languages = [
            ("it", "🇮🇹 Italiano"),
            ("es", "🇪🇸 Español"),
            ("en", "🇬🇧 English")
        ]

        current_lang = self.tm.current_language

        for lang_code, lang_name in languages:
            radio = QRadioButton(lang_name)
            radio.setStyleSheet("""
                QRadioButton {
                    color: white;
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            radio.setProperty("lang_code", lang_code)

            if lang_code == current_lang:
                radio.setChecked(True)

            lang_group.addButton(radio)
            layout.addWidget(radio)

        # Bottoni
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton(self.tm.get("common", "cancel"))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_SECONDARIO};
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tm.get("common", "save"))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ITEM_SELEZIONATO};
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        save_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        if dialog.exec():
            # Trova il radio button selezionato
            selected_lang = None
            for button in lang_group.buttons():
                if button.isChecked():
                    selected_lang = button.property("lang_code")
                    break

            if selected_lang and selected_lang != current_lang:
                # Salva la preferenza
                from services.preferences_service import PreferencesService
                prefs = PreferencesService()
                prefs.set_language(selected_lang)

                # Mostra messaggio
                QMessageBox.information(
                    self,
                    self.tm.get("common", "success"),
                    self.tm.get("settings", "language_changed")
                )

                # Ricarica l'app (necessario per applicare le traduzioni)
                QMessageBox.information(
                    self,
                    self.tm.get("settings", "restart_required"),
                    self.tm.get("settings", "restart_required_desc")
                )

    def backup_database(self):
        """Crea backup del database"""
        try:
            db_path = "property_manager.db"
            if not os.path.exists(db_path):
                QMessageBox.warning(self, self.tm.get("common", "error"), "Database non trovato!")
                return

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
            QMessageBox.critical(self, self.tm.get("common", "error"), f"Errore durante il backup:\n{str(e)}")

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
                QMessageBox.critical(self, self.tm.get("common", "error"), f"Errore durante il ripristino:\n{str(e)}")

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
            QMessageBox.critical(self, self.tm.get("common", "error"), f"Errore durante la pulizia:\n{str(e)}")

    def clean_orphaned_folders(self):
        """Pulisce cartelle documenti senza proprietà associate"""
        try:
            docs_dir = "docs"
            if not os.path.exists(docs_dir):
                QMessageBox.information(self, "Info", "Nessuna cartella documenti trovata.")
                return

            properties = self.property_service.get_all()
            valid_property_ids = {prop['id'] for prop in properties}

            orphaned_folders = []
            total_size = 0

            for folder_name in os.listdir(docs_dir):
                folder_path = os.path.join(docs_dir, folder_name)

                if not os.path.isdir(folder_path):
                    continue

                if folder_name.startswith("property_"):
                    try:
                        property_id = int(folder_name.split("_")[1])

                        if property_id not in valid_property_ids:
                            folder_size = 0
                            for root, dirs, files in os.walk(folder_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    if os.path.exists(file_path):
                                        folder_size += os.path.getsize(file_path)

                            orphaned_folders.append({
                                'name': folder_name,
                                'path': folder_path,
                                'size': folder_size,
                                'property_id': property_id
                            })
                            total_size += folder_size

                    except (ValueError, IndexError):
                        continue

            if not orphaned_folders:
                QMessageBox.information(
                    self,
                    f"✅ {self.tm.get("common", "success")}",
                    "Non sono state trovate cartelle documenti orfane.\n\n"
                    "Tutte le cartelle corrispondono a proprietà esistenti."
                )
                return

            def format_size(size_bytes):
                if size_bytes == 0:
                    return "0 B"
                units = ['B', 'KB', 'MB', 'GB']
                unit_index = 0
                size = float(size_bytes)
                while size >= 1024 and unit_index < len(units) - 1:
                    size /= 1024
                    unit_index += 1
                return f"{size:.2f} {units[unit_index]}"

            total_size_str = format_size(total_size)

            orphaned_list = "\n".join([
                f"  • {f['name']} ({format_size(f['size'])})"
                for f in orphaned_folders
            ])

            reply = QMessageBox.question(
                self,
                "🗑️ Cartelle Orfane Trovate",
                f"Trovate {len(orphaned_folders)} cartelle senza proprietà associate:\n\n"
                f"{orphaned_list}\n\n"
                f"Spazio totale occupato: {total_size_str}\n\n"
                f"⚠️ Vuoi eliminarle definitivamente?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                deleted_count = 0
                deleted_size = 0
                errors = []

                for folder_info in orphaned_folders:
                    try:
                        shutil.rmtree(folder_info['path'])
                        deleted_count += 1
                        deleted_size += folder_info['size']
                    except Exception as e:
                        errors.append(f"{folder_info['name']}: {str(e)}")

                result_message = (
                    f"✅ Pulizia completata!\n\n"
                    f"Cartelle eliminate: {deleted_count}/{len(orphaned_folders)}\n"
                    f"Spazio liberato: {format_size(deleted_size)}"
                )

                if errors:
                    result_message += f"\n\n⚠️ Errori:\n" + "\n".join(errors)

                QMessageBox.information(self, "Pulizia Completata", result_message)

        except Exception as e:
            QMessageBox.critical(
                self,
                f"❌ {self.tm.get("common", "error")}",
                f"Errore durante la pulizia:\n\n{str(e)}"
            )