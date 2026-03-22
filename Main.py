import sys
from PySide6.QtWidgets import QApplication

# ── Config è il primo import: carica .env prima di tutto il resto ──
from config import Config

from log_manager import LogManager
from services.database_service import DatabaseService
from services.preferences_service import PreferencesService
from services.supplier_service import SupplierService
from services.translation_system_simple import TranslationManager
from services.auth_service import AuthService
from ui_login import LoginWindow
from ui_register import RegisterWindow
from ui_main import DashboardWindow


class AppController:
    """
    Gestisce il ciclo di vita delle finestre e i passaggi tra di esse.

    Flusso production/saas:
        Login ──► Dashboard
          │
          └──► Register ──► Dashboard

    Flusso development (DEV_SKIP_LOGIN=true nel .env):
        Direttamente ──► Dashboard (is_admin=True)
    """

    def __init__(self, app, services: dict, logger):
        self.app      = app
        self.services = services
        self.logger   = logger
        self._window  = None

    # ──────────────────────────────────────────────
    #  ENTRY POINT
    # ──────────────────────────────────────────────
    def start(self):
        if Config.is_development() and Config.DEV_SKIP_LOGIN:
            self._skip_login()
        else:
            self._show_login()

    # ──────────────────────────────────────────────
    #  DEVELOPMENT — bypass login
    # ──────────────────────────────────────────────
    def _skip_login(self):
        self.logger.warning("⚠️  DEV MODE: login bypassato (DEV_SKIP_LOGIN=true)")
        win = self._build_dashboard(is_admin=True)
        win.show()
        self._window = win

    # ──────────────────────────────────────────────
    #  LOGIN
    # ──────────────────────────────────────────────
    def _show_login(self):
        win = LoginWindow(self.services['auth'], self.logger)
        win.login_successful.connect(self._on_login_ok)
        win.open_register.connect(self._show_register)

        # In dev, pre-compila le credenziali se impostate nel .env
        if Config.is_development():
            if Config.DEV_LOGIN_EMAIL:
                win.email_input.setText(Config.DEV_LOGIN_EMAIL)
            if Config.DEV_LOGIN_PASSWORD:
                win.password_input.setText(Config.DEV_LOGIN_PASSWORD)

        win.show()
        self._window = win

    def _on_login_ok(self, email: str, token: str, is_admin: bool):
        self.logger.info(f"AppController: accesso confermato per {email}, admin={is_admin}")
        win = self._build_dashboard(is_admin=is_admin)
        win.show()
        self._window = win

    # ──────────────────────────────────────────────
    #  REGISTER
    # ──────────────────────────────────────────────
    def _show_register(self):
        self._window.close()
        win = RegisterWindow(self.services['auth'], self.logger)
        win.register_successful.connect(self._on_register_ok)
        win.show()
        self._window = win

    def _on_register_ok(self):
        self.logger.info("AppController: registrazione completata, ritorno al login")
        self._window.close()
        # I nuovi utenti non sono mai admin
        win = self._build_dashboard(is_admin=False)
        win.show()
        self._window = win

    # ──────────────────────────────────────────────
    #  HELPER
    # ──────────────────────────────────────────────
    def _build_dashboard(self, is_admin: bool) -> DashboardWindow:
        s = self.services
        return DashboardWindow(
            s['db'],
            s['prefs'],
            s['supplier'],
            s['translation'],
            logger=self.logger,
            is_admin=is_admin
        )


# ──────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log_manager = LogManager()
    logger = log_manager.setup_logging()

    # Stampa riepilogo configurazione all'avvio
    Config.print_summary(logger)
    logger.info("🚀 Property Manager avviato")

    app = QApplication(sys.argv)

    # Database
    db_service = DatabaseService(logger=logger)
    db_service.initialize()

    # Traduzioni
    translation_manager = TranslationManager(
        db_path='shared/translations.db',
        default_language='it'
    )
    prefs_service = PreferencesService(logger)
    translation_manager.set_language(prefs_service.get_language())
    logger.info(f"Translation Manager inizializzato (lingua: {translation_manager.get_current_language()})")

    services = {
        'auth'       : AuthService(logger),
        'db'         : db_service,
        'prefs'      : prefs_service,
        'supplier'   : SupplierService(logger),
        'translation': translation_manager,
    }

    controller = AppController(app, services, logger)
    controller.start()

    sys.exit(app.exec())