import sys
from PySide6.QtWidgets import QApplication

from services.database_service import DatabaseService
from ui_main import DashboardWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Inizializza database tramite service
    db_service = DatabaseService()
    conn = db_service.initialize()

    # Avvia interfaccia
    window = DashboardWindow(db_service)
    window.show()

    sys.exit(app.exec())
