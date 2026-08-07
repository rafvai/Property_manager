import shutil
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import Config
from styles import (
    COLORE_BACKGROUND,
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_GRIGIO,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_SECONDARIO,
    COLORE_SUCCESS,
    COLORE_WARNING,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_combo_box_style,
    default_dialog_style,
    default_style_secondary_buttons,
    default_style_text,
    default_style_text_small,
    default_title_style,
)
from views.base_view import BaseView


class SettingItem(QFrame):
    """Widget personalizzato per ogni elemento delle impostazioni con animazioni"""

    def __init__(self, icon, title, description, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.is_hovered = False

        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                border: 2px solid transparent;
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(15)

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

        text_container = QWidget()
        # Senza questo il container eredita lo sfondo scuro dallo stylesheet
        # globale e disegna un riquadro più scuro dietro a titolo e descrizione
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: white;
            font-size: 15px;
            font-weight: 600;
            background: transparent;
        """)
        text_layout.addWidget(self.title_label)

        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet("""
            color: #95a5a6;
            font-size: 12px;
            background: transparent;
        """)
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.desc_label)

        layout.addWidget(text_container, stretch=1)

        self.arrow_label = QLabel("›")
        self.arrow_label.setStyleSheet("""
            color: #95a5a6;
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self.arrow_label)

        self.arrow_animation = QPropertyAnimation(self.arrow_label, b"pos")
        self.arrow_animation.setDuration(200)
        self.arrow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self.is_hovered = True
        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_ITEM_HOVER};
                border-radius: 10px;
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
            }}
        """)
        current_pos = self.arrow_label.pos()
        self.arrow_animation.setStartValue(current_pos)
        self.arrow_animation.setEndValue(current_pos + QPoint(5, 0))
        self.arrow_animation.start()
        self.arrow_label.setStyleSheet(f"""
            color: {COLORE_ITEM_SELEZIONATO};
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.setStyleSheet(f"""
            SettingItem {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                border: 2px solid transparent;
            }}
        """)
        current_pos = self.arrow_label.pos()
        self.arrow_animation.setStartValue(current_pos)
        self.arrow_animation.setEndValue(current_pos - QPoint(5, 0))
        self.arrow_animation.start()
        self.arrow_label.setStyleSheet("""
            color: #95a5a6;
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet(f"""
                SettingItem {{
                    background-color: {COLORE_ITEM_SELEZIONATO};
                    border-radius: 10px;
                    border: 2px solid {COLORE_ITEM_SELEZIONATO};
                }}
            """)
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
        self.layout.addWidget(item)


class SettingsView(BaseView):
    """View per le impostazioni dell'applicazione"""

    def __init__(self, property_service, transaction_service, translation_service,auth_service, user_prefs_service, logger, parent=None):
        self.tm = translation_service
        self.auth_service = auth_service
        self.user_prefs_service  = user_prefs_service
        self.logger = logger
        super().__init__(property_service, transaction_service, None, parent)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _db_path() -> Path:
        """
        Ritorna il path corretto del DB in base all'ambiente.
        ora usa Config.get_database_config() come il resto dell'app.
        """
        db_config = Config.get_database_config()
        return Path(db_config['path'])

    @staticmethod
    def _exports_dir() -> Path:
        """
        Ritorna la directory exports corretta in base all'ambiente.
        """
        exports = Config.EXPORTS_DIR or Path('exports').absolute()
        Path(exports).mkdir(parents=True, exist_ok=True)
        return Path(exports)

    # ── setup UI ──────────────────────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        title = QLabel(self.tm.get('ETICHETTE', 'IMPOSTAZIONI'))
        title.setStyleSheet(default_title_style)
        main_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORE_GRIGIO};
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORE_GRIGIO};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(25)
        scroll_layout.setContentsMargins(0, 0, 10, 0)

        # === SEZIONE DATABASE ===
        db_section = SettingsSection(self.tm.get("ETICHETTE", "BACKUP_DB"))
        db_section.add_item(SettingItem(
            "💾",
            self.tm.get("ETICHETTE", "BACKUP_DB"),
            self.tm.get("ETICHETTE", "CREA_UN_BACKUP_DEL_DB"),
            self.backup_database
        ))
        db_section.add_item(SettingItem(
            "📥",
            self.tm.get("ETICHETTE", "RIPRISTINA_DB"),
            self.tm.get("ETICHETTE", "RIPRISTINA_DB_DESCR"),
            self.restore_database
        ))
        scroll_layout.addWidget(db_section)

        # === SEZIONE GESTIONE FILE ===
        files_section = SettingsSection(self.tm.get("ETICHETTE", "SEZIONE_FILES"))
        files_section.add_item(SettingItem(
            "📊",
            self.tm.get("ETICHETTE", "open_exports"),
            self.tm.get("ETICHETTE", "open_exports_desc"),
            self.open_exports_folder
        ))
        files_section.add_item(SettingItem(
            "🗑️",
            self.tm.get("ETICHETTE", "clean_exports"),
            self.tm.get("ETICHETTE", "clean_exports_desc"),
            self.clean_old_exports
        ))

        scroll_layout.addWidget(files_section)
        # === SEZIONE PREFERENZE ===
        prefs_section = SettingsSection(self.tm.get("ETICHETTE", "PREFERENZE"))
        prefs_section.add_item(SettingItem(
            "🔔",
            self.tm.get("ETICHETTE", "TEMPO_PREAVVISO"),
            self.tm.get("ETICHETTE", "TEMPO_PREAVVISO_NOTIFICHE_DESCR"),
            self.open_deadline_warning_dialog
        ))
        prefs_section.add_item(SettingItem(
            "💱",
            self.tm.get("ETICHETTE", "VALUTA"),
            self.tm.get("ETICHETTE", "MODIFICA_VALUTA"),
            self.open_currency_dialog
        ))
        scroll_layout.addWidget(prefs_section)

        # === SEZIONE ACCOUNT & LICENZA ===
        account_section = SettingsSection(self.tm.get("ETICHETTE", "account_section"))
        account_section.add_item(SettingItem(
            "🔑",
            self.tm.get("ETICHETTE", "CAMBIA_PASSWORD"),
            self.tm.get("ETICHETTE", "change_password_desc"),
            self.open_change_password_dialog
        ))
        account_section.add_item(SettingItem(
            "📋",
            self.tm.get("ETICHETTE", "license_info"),
            self.tm.get("ETICHETTE", "license_info_desc"),
            self.open_license_info_dialog
        ))
        scroll_layout.addWidget(account_section)

        # === SEZIONE LOG & DIAGNOSTICA ===
        log_section = SettingsSection(self.tm.get("ETICHETTE", "log_section"))
        log_section.add_item(SettingItem(
            "📄",
            self.tm.get("ETICHETTE", "LOGS"),
            self.tm.get("ETICHETTE", "view_logs_desc"),
            self.open_log_viewer_dialog
        ))
        log_section.add_item(SettingItem(
            "🔄",
            self.tm.get("ETICHETTE", "rotate_logs"),
            self.tm.get("ETICHETTE", "rotate_logs_desc"),
            self.rotate_logs
        ))
        log_section.add_item(SettingItem(
            "🗜️",
            self.tm.get("ETICHETTE", "archive_logs"),
            self.tm.get("ETICHETTE", "archive_logs_desc"),
            self.archive_logs
        ))
        scroll_layout.addWidget(log_section)

        scroll_layout.addStretch()

        # === INFO ===
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_BACKGROUND};
                border-radius: 10px;
                padding: 15px;
                border: 1px solid {COLORE_SECONDARIO};
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setSpacing(15)

        app_icon = QLabel("🏠 Property Manager")
        app_icon.setStyleSheet(default_style_text)
        info_layout.addWidget(app_icon)

        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        version = QLabel(self.tm.get("ETICHETTE", "VERSIONE"))
        version.setStyleSheet(default_style_text_small)
        text_layout.addWidget(version)

        info_layout.addWidget(text_container)
        info_layout.addStretch()
        scroll_layout.addWidget(info_frame)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    # ── azioni ────────────────────────────────────────────────────────────────
    def backup_database(self):
        """Crea backup del database — usa il path corretto da Config."""
        try:
            db_path = self._db_path()
            if not db_path.exists():
                QMessageBox.warning(self, self.tm.get("MESSAGGI", "ERRORE"),
                                    f"{self.tm.get('MESSAGGI','DATABASE_NON_TROVATO')}:\n{db_path}")
                return

            timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"backup_property_manager_{timestamp}.db"

            backup_path, _ = QFileDialog.getSaveFileName(
                self, "Salva Backup Database", default_name,
                "Database Files (*.db);;All Files (*)"
            )

            if backup_path:
                shutil.copy2(str(db_path), backup_path)
                QMessageBox.information(
                    self, f"✅ {self.tm.get('MESSAGGI', 'BACKUP_COMPLETATO')}",
                    f"Database salvato con successo!\n\n📁 {backup_path}"
                )

        except Exception as e:
            QMessageBox.critical(self, self.tm.get("MESSAGGI", "ERRORE"),
                                 f"Errore durante il backup:\n{str(e)}")

    def restore_database(self):
        """Ripristina database da backup — usa il path corretto da Config."""
        reply = QMessageBox.question(
            self, "⚠️ Conferma Ripristino",
            "Sei sicuro di voler ripristinare il database?\n\n"
            "⚠️ ATTENZIONE: Tutti i dati attuali verranno sovrascritti!\n"
            "Questa operazione è IRREVERSIBILE!\n\n"
            "Assicurati di aver fatto un backup prima di procedere.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                backup_path, _ = QFileDialog.getOpenFileName(
                    self, "Seleziona Backup Database", "",
                    "Database Files (*.db);;All Files (*)"
                )

                if backup_path:
                    db_path = self._db_path()
                    shutil.copy2(backup_path, str(db_path))
                    QMessageBox.information(
                        self, "✅ Ripristino Completato",
                        "Database ripristinato con successo!\n\n"
                        "⚠️ Riavvia l'applicazione per applicare le modifiche."
                    )

            except Exception as e:
                QMessageBox.critical(self, self.tm.get("common", "error"),
                                     f"Errore durante il ripristino:\n{str(e)}")

    def open_exports_folder(self):
        """Apri cartella export — usa il path corretto da Config."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        exports_dir = self._exports_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(exports_dir)))

    def clean_old_exports(self):
        """Pulisci export vecchi (>30 giorni) — usa il path corretto da Config."""
        try:
            exports_dir = self._exports_dir()
            files = list(exports_dir.iterdir())
            deleted_count = 0
            cutoff_time   = datetime.now().timestamp() - (30 * 24 * 60 * 60)

            for file_path in files:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                QMessageBox.information(
                    self, "✅ Pulizia Completata",
                    f"Eliminati {deleted_count} file più vecchi di 30 giorni."
                )
            else:
                QMessageBox.information(
                    self, "Info",
                    "Nessun file da eliminare (tutti più recenti di 30 giorni)."
                )

        except Exception as e:
            QMessageBox.critical(self, self.tm.get("common", "error"),
                                 f"Errore durante la pulizia:\n{str(e)}")



    # ── PREFERENZE ────────────────────────────────────────────────

    def open_deadline_warning_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Preavviso Scadenze")
        dialog.setMinimumWidth(360)
        dialog.setStyleSheet(default_dialog_style)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel(self.tm.get("ETICHETTE", "GIORNI_PREAVVISO_MESSAGGIO"))
        lbl.setStyleSheet(default_style_text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        combo = QComboBox()
        combo.setStyleSheet(default_combo_box_style)
        options = [1, 3, 7, 14, 30]
        for d in options:
            combo.addItem(f"{d} giorn{'o' if d == 1 else 'i'}", d)

        current = self.user_prefs_service.get_deadline_warning_days()
        idx = options.index(current) if current in options else 2
        combo.setCurrentIndex(idx)
        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("color: white;")
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            self.user_prefs_service.set_deadline_warning_days(combo.currentData())
            QMessageBox.information(self, self.tm.get("MESSAGGI", "SALVATO"),
                                    f"Preavviso impostato a {combo.currentData()} "
                                    f"giorn{'o' if combo.currentData() == 1 else 'i'}.")

    def open_currency_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tm.get("ETICHETTE","VALUTA"))
        dialog.setMinimumWidth(320)
        dialog.setStyleSheet(default_dialog_style)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel(self.tm.get("MESSAGGI", "SELEZIONA_VALUTA"))
        lbl.setStyleSheet(default_style_text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        combo = QComboBox()
        combo.setStyleSheet(default_combo_box_style)
        currencies = [("€  Euro", "€"), ("$  Dollaro", "$"), ("£  Sterlina", "£")]
        for label, symbol in currencies:
            combo.addItem(label, symbol)

        current = self.user_prefs_service.get_currency()
        for i, (_, s) in enumerate(currencies):
            if s == current:
                combo.setCurrentIndex(i)
                break
        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            self.user_prefs_service.set_currency(combo.currentData())
            QMessageBox.information(self, self.tm.get("MESSAGGI", "SALVATO"),
                                    f"{self.tm.get('MESSAGGI', 'VALUTA_IMPOSTATA_A')} {combo.currentData()}.")

    # ── ACCOUNT & LICENZA ─────────────────────────────────────────

    def open_change_password_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tm.get("ETICHETTE","CAMBIA_PASSWORD"))
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        current_pwd = QLineEdit()
        current_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        current_pwd.setPlaceholderText(self.tm.get("ETICHETTE", "PASSWORD_ATTUALE"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'PASSWORD_ATTUALE')}*:", current_pwd)

        new_pwd = QLineEdit()
        new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        new_pwd.setPlaceholderText("Minimo 8 caratteri")
        layout.addRow(f"{self.tm.get('ETICHETTE', 'NUOVA_PASSWORD')}*:", new_pwd)

        confirm_pwd = QLineEdit()
        confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_pwd.setPlaceholderText("Ripeti la nuova password")
        layout.addRow("Conferma password*:", confirm_pwd)

        msg_lbl = QLabel("")
        msg_lbl.setStyleSheet(f"color: {COLORE_ERROR}; font-size: 12px;")
        msg_lbl.setWordWrap(True)
        layout.addRow(msg_lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        buttons.rejected.connect(dialog.reject)

        def on_accept():
            if not current_pwd.text():
                msg_lbl.setText("Inserisci la password attuale.")
                return
            if len(new_pwd.text()) < 8:
                msg_lbl.setText("La nuova password deve essere di almeno 8 caratteri.")
                return
            if new_pwd.text() != confirm_pwd.text():
                msg_lbl.setText("Le password non coincidono.")
                return
            dialog.accept()

        buttons.accepted.connect(on_accept)

        if dialog.exec():
            try:
                import hmac
                import json

                import requests

                from services.auth_service import _CACHE_FILE, _HMAC_KEY

                cache_file = _CACHE_FILE
                if not cache_file.exists():
                    QMessageBox.warning(self, "⚠️ Errore",
                                        "Nessuna sessione attiva. Effettua il login e riprova.")
                    return

                raw = json.loads(cache_file.read_text(encoding="utf-8"))
                payload = json.dumps(raw["payload"], sort_keys=True).encode()
                expected = hmac.digest(_HMAC_KEY, payload, "sha256").hex()
                if not hmac.compare_digest(raw["sig"], expected):
                    QMessageBox.warning(self, "⚠️ Errore", "Cache non valida.")
                    return

                token = raw["payload"].get("token")
                if not token:
                    QMessageBox.warning(self, "⚠️ Errore", "Token non trovato.")
                    return

                resp = requests.post(
                    f"{self.auth_service.server_url}/auth/change-password",
                    json={
                        "current_password": current_pwd.text(),
                        "new_password": new_pwd.text()
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )

                if resp.status_code == 200:
                    QMessageBox.information(self, "✅ Password Aggiornata",
                                            "Password cambiata con successo!")
                else:
                    detail = resp.json().get("detail", "Errore sconosciuto")
                    QMessageBox.warning(self, "❌ Errore", detail)

            except requests.exceptions.ConnectionError:
                QMessageBox.critical(self, "❌ Errore di connessione",
                                     "Server non raggiungibile. Verifica la connessione.")
            except Exception as e:
                self.logger.error(f"SettingsView: cambio password: {e}")
                QMessageBox.critical(self, "❌ Errore", str(e))

    def open_license_info_dialog(self):
        """Mostra info licenza leggendo dalla cache locale."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Informazioni Licenza")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(default_dialog_style)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        try:
            import hmac
            import json

            from services.auth_service import _CACHE_FILE, _HMAC_KEY

            if not _CACHE_FILE.exists():
                raise FileNotFoundError

            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            payload_bytes = json.dumps(raw["payload"], sort_keys=True).encode()
            expected_sig = hmac.digest(_HMAC_KEY, payload_bytes, "sha256").hex()
            if not hmac.compare_digest(raw["sig"], expected_sig):
                raise ValueError("Cache manomessa")

            cache = raw["payload"]
            email = cache.get("email", "—")
            expires_at = cache.get("expires_at", "")
            days_left = cache.get("days_left", 0)
            is_admin = cache.get("is_admin", False)
            grace_mode = cache.get("grace_mode", False)
            cached_at = cache.get("cached_at", "")

            # Calcola giorni rimasti in tempo reale
            try:
                from datetime import datetime as dt
                exp_dt = dt.fromisoformat(expires_at)
                now_utc = dt.now(UTC).replace(tzinfo=None)
                days_left = max(0, (exp_dt - now_utc).days)
                expires_str = exp_dt.strftime("%d/%m/%Y")
            except Exception:
                expires_str = expires_at[:10] if expires_at else "—"

            try:
                cached_str = dt.fromisoformat(cached_at).strftime("%d/%m/%Y %H:%M")
            except Exception:
                cached_str = "—"

            rows = [
                ("👤 Account", email),
                ("📋 Piano", "Admin" if is_admin else "Beta"),
                ("📅 Scadenza", expires_str),
                ("⏳ Giorni rimasti",
                 f"{days_left} gg {'(periodo di grazia)' if grace_mode else ''}".strip()),
                ("🔄 Ultimo sync", cached_str),
            ]

        except FileNotFoundError:
            rows = [("⚠️ Stato", "Nessuna sessione trovata. Effettua il login.")]
        except Exception as e:
            rows = [("❌ Errore", str(e))]

        # Rendering righe
        for label, value in rows:
            row_frame = QFrame()
            row_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORE_SECONDARIO};
                    border-radius: 8px;
                }}
            """)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(16, 10, 16, 10)

            lbl_w = QLabel(label)
            lbl_w.setStyleSheet("color: #95a5a6; font-size: 13px; background: transparent;")
            lbl_w.setFixedWidth(140)
            row_layout.addWidget(lbl_w)

            val_w = QLabel(value)
            val_w.setStyleSheet("color: white; font-size: 13px; font-weight: 600; background: transparent;")
            val_w.setWordWrap(True)
            row_layout.addWidget(val_w, stretch=1)

            layout.addWidget(row_frame)

        # Giorni rimasti: barra colorata
        if rows and rows[0][0] != "⚠️ Stato" and rows[0][0] != "❌ Errore":
            try:
                bar_color = COLORE_SUCCESS if days_left > 14 else (COLORE_WARNING if days_left > 7 else COLORE_ERROR)
                bar_frame = QFrame()
                bar_frame.setStyleSheet(f"""
                    QFrame {{
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 {bar_color},
                            stop:{min(days_left / 90, 1.0):.2f} {bar_color},
                            stop:{min(days_left / 90 + 0.001, 1.0):.3f} {COLORE_SECONDARIO},
                            stop:1 {COLORE_SECONDARIO}
                        );
                        border-radius: 4px;
                        min-height: 6px;
                        max-height: 6px;
                    }}
                """)
                layout.addWidget(bar_frame)
            except Exception:
                pass

        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(default_aggiungi_button)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    # ── LOG & DIAGNOSTICA ─────────────────────────────────────────

    def open_log_viewer_dialog(self):
        """Mostra le ultime 100 righe di app.log."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Log Applicazione")
        dialog.setMinimumSize(700, 500)
        dialog.setStyleSheet(default_dialog_style)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header con stats
        from log_manager import LogManager
        lm = LogManager()
        stats = lm.get_log_stats()

        stats_lbl = QLabel(
            f"📄 {stats['log_files']} file log  •  "
            f"💾 {stats['total_log_size_mb']} MB  •  "
            f"🗜️ {stats['archives']} archivi ({stats['total_archive_size_mb']} MB)"
        )
        stats_lbl.setStyleSheet(f"color: {COLORE_GRIGIO}; font-size: 12px;")
        layout.addWidget(stats_lbl)

        # Area testo log
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORE_BACKGROUND};
                color: #a8c7a8;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid {COLORE_SECONDARIO};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

        log_path = Path("logs") / "app.log"
        if log_path.exists():
            try:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                last_lines = lines[-100:] if len(lines) > 100 else lines
                log_text.setPlainText("".join(last_lines))
                # Scroll in fondo
                cursor = log_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                log_text.setTextCursor(cursor)
            except Exception as e:
                log_text.setPlainText(f"Errore lettura log: {e}")
        else:
            log_text.setPlainText("Nessun file log trovato.")

        layout.addWidget(log_text)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Aggiorna")
        refresh_btn.setStyleSheet(default_style_secondary_buttons)
        refresh_btn.clicked.connect(lambda: self._refresh_log_text(log_text, log_path))
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()

        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(default_aggiungi_button)
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
        dialog.exec()

    def _refresh_log_text(self, text_edit: QTextEdit, log_path: Path):
        if log_path.exists():
            try:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                last_lines = lines[-100:] if len(lines) > 100 else lines
                text_edit.setPlainText("".join(last_lines))
                cursor = text_edit.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                text_edit.setTextCursor(cursor)
            except Exception as e:
                text_edit.setPlainText(f"Errore lettura log: {e}")

    def rotate_logs(self):
        try:
            from log_manager import LogManager
            lm = LogManager()
            rotated = lm.rotate_logs()
            if rotated:
                QMessageBox.information(self, "✅ Log Ruotati",
                                        f"Ruotati {len(rotated)} file:\n" +
                                        "\n".join(r.name for r in rotated))
            else:
                QMessageBox.information(self, "ℹ️ Nessuna Rotazione",
                                        "Nessun log supera la dimensione massima configurata.")
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", str(e))

    def archive_logs(self):
        try:
            from log_manager import LogManager
            lm = LogManager()
            count = lm.archive_old_logs()
            if count:
                QMessageBox.information(self, "✅ Log Archiviati",
                                        f"Archiviati {count} file log.")
            else:
                QMessageBox.information(self, "ℹ️ Nessun Archivio",
                                        "Nessun log abbastanza vecchio da archiviare (< 30 giorni).")
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", str(e))
