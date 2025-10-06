import sys
import sqlite3

from PySide6.QtWidgets import QApplication

from Functions import init_db
from ui_main import DashboardWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # inizializza DB (crea tabelle se non ci sono)
    conn = init_db()

    # avvia interfaccia
    window = DashboardWindow(conn)
    window.show()

    sys.exit(app.exec())
