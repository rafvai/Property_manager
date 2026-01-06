import sys
from PySide6.QtWidgets import QApplication

from services.database_service import DatabaseService
from services.preferences_service import PreferencesService
from translations_manager import get_translation_manager
from ui_main import DashboardWindow
from log_manager import LogManager

if __name__ == "__main__":
    # Setup log manager
    log_manager = LogManager()
    logger = log_manager.setup_logging()

    logger.info("🚀 Property Manager avviato")

    # Esegui manutenzione all'avvio (opzionale)
    log_manager.maintenance()

    app = QApplication(sys.argv)

    # Inizializza preferenze e traduzioni
    prefs_service = PreferencesService()
    tm = get_translation_manager()
    tm.set_language(prefs_service.get_language())

    # Inizializza database
    db_service = DatabaseService(logger=logger)
    conn = db_service.initialize()

    # Avvia interfaccia
    window = DashboardWindow(db_service, prefs_service)
    window.show()

    sys.exit(app.exec())