from PySide6.QtWidgets import QWidget


class BaseView(QWidget):
    """Classe base per tutte le view"""

    def __init__(self, property_service, transaction_service, document_service=None, parent=None):
        super().__init__(parent)

        # Inietta i services
        self.property_service = property_service
        self.transaction_service = transaction_service
        self.document_service = document_service

        self.setup_ui()

    def setup_ui(self):
        """Da implementare nelle sottoclassi"""
        raise NotImplementedError("Le sottoclassi devono implementare setup_ui()")

    def refresh(self):
        """Metodo per aggiornare i dati della view (opzionale)"""
        pass