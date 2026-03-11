import sys
import os
from PySide6.QtWidgets import QApplication

os.environ['APP_ENV'] = 'development'  # development | production | saas

from log_manager import LogManager
from services.database_service import DatabaseService
from services.property_service import PropertyService
from services.transaction_service import TransactionService
from services.document_service import DocumentService
from services.deadline_service import DeadlineService
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
    Mantiene i riferimenti vivi per evitare garbage collection.

    Flusso:
        Login ──► Dashboard
          │
          └──► Register ──► Dashboard
    """

    def __init__(self, app, services: dict, logger):
        self.app      = app
        self.services = services
        self.logger   = logger
        self._window  = None   # finestra attiva corrente

    # ──────────────────────────────────────────────
    #  ENTRY POINT
    # ──────────────────────────────────────────────
    def start(self):
        self._show_login()

    # ──────────────────────────────────────────────
    #  LOGIN
    # ──────────────────────────────────────────────
    def _show_login(self):
        win = LoginWindow(self.services['auth'], self.logger)
        win.login_successful.connect(self._on_login_ok)
        win.open_register.connect(self._show_register)
        win.show()
        self._window = win

    def _on_login_ok(self, email: str, token: str, is_admin: bool):
        self.logger.info(f"AppController: accesso confermato per {email}, admin={is_admin}")
        s = self.services
        win = DashboardWindow(
            s['db'],
            s['prefs'],
            s['supplier'],
            s['translation'],
            logger=self.logger
        )
        win.show()
        self._window = win   # login già chiuso dal suo _proceed()

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
        s = self.services
        win = DashboardWindow(
            s['db'],
            s['prefs'],
            s['supplier'],
            s['translation'],
            logger=self.logger
        )
        win.show()
        self._window = win


# ──────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log_manager = LogManager()
    logger = log_manager.setup_logging()
    logger.info("🚀 Property Manager avviato")

    app = QApplication(sys.argv)

    # Database
    db_service = DatabaseService(logger=logger)
    db_service.initialize()

    # Translation
    translation_manager = TranslationManager(
        db_path='shared/translations.db',
        default_language='it'
    )
    prefs_service = PreferencesService(logger)
    translation_manager.set_language(prefs_service.get_language())
    logger.info(f"Translation Manager inizializzato (lingua: {translation_manager.get_current_language()})")

    # Tutti i services raccolti in un dict
    services = {
        'auth'       : AuthService(logger),
        'db'         : db_service,
        'prefs'      : prefs_service,
        'supplier'   : SupplierService(logger),
        'translation': translation_manager,
        'property'   : PropertyService(logger),
        'transaction': TransactionService(logger),
        'deadline'   : DeadlineService(logger),
        'document'   : DocumentService(logger),
    }

    controller = AppController(app, services, logger)
    controller.start()

    sys.exit(app.exec())