import sys
from PySide6.QtWidgets import QApplication

from services.database_service import DatabaseService
from services.preferences_service import PreferencesService
from translations_manager import get_translation_manager
from ui_main import DashboardWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Inizializza preferenze e traduzioni
    prefs_service = PreferencesService()
    tm = get_translation_manager()
    tm.set_language(prefs_service.get_language())

    # Inizializza database
    db_service = DatabaseService()
    conn = db_service.initialize()

    # Avvia interfaccia
    window = DashboardWindow(db_service, prefs_service)
    window.show()

    sys.exit(app.exec())