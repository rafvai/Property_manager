from PySide6.QtWidgets import QWidget
from translations_manager import get_translation_manager


class BaseView(QWidget):
    """Classe base per tutte le view"""

    def __init__(self, property_service, transaction_service, document_service=None, parent=None):
        super().__init__(parent)

        # Inietta i services
        self.property_service = property_service
        self.transaction_service = transaction_service
        self.document_service = document_service

        # Translation manager (disponibile PRIMA di setup_ui)
        self.tm = get_translation_manager()

        # IMPORTANTE: setup_ui viene chiamato DOPO che self.tm è disponibile
        self.setup_ui()

    def setup_ui(self):
        """Da implementare nelle sottoclassi"""
        raise NotImplementedError("Le sottoclassi devono implementare setup_ui()")

    def refresh(self):
        """Metodo per aggiornare i dati della view (opzionale)"""
        pass