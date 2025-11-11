from PySide6.QtWidgets import QWidget


class BaseView(QWidget):
    """Classe base per tutte le view"""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.cursor = conn.cursor()
        self.cursor_read_only = conn.cursor()
        self.setup_ui()

    def setup_ui(self):
        """Da implementare nelle sottoclassi"""
        raise NotImplementedError("Le sottoclassi devono implementare setup_ui()")

    def refresh(self):
        """Metodo per aggiornare i dati della view (opzionale)"""
        pass