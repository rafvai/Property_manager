import sys
import os
from PySide6.QtWidgets import QApplication

# Imposta environment
os.environ['APP_ENV'] = 'development'  # development | production | saas

from services.database_service import DatabaseService
from services.property_service import PropertyService
from services.transaction_service import TransactionService
from services.document_service import DocumentService
from services.deadline_service import DeadlineService
from services.preferences_service import PreferencesService
from services.supplier_service import SupplierService
from services.translation_system_simple import TranslationManager
from ui_main import DashboardWindow
from log_manager import LogManager
from ui_login import LoginWindow
from ui_register import RegisterWindow

if __name__ == "__main__":
    log_manager = LogManager()
    logger = log_manager.setup_logging()
    logger.info("🚀 Property Manager avviato")

    app = QApplication(sys.argv)

    # Inizializza database
    db_service = DatabaseService(logger=logger)
    db_service.initialize()

    # Inizializza services (ora prendono solo logger)
    property_service = PropertyService(logger)
    transaction_service = TransactionService(logger)
    deadline_service = DeadlineService(logger)
    document_service = DocumentService(logger)
    supplier_service = SupplierService(logger)

    # Crea Translation Manager
    translation_manager = TranslationManager(
        db_path='shared/translations.db',
        default_language='it'
    )
    logger.info(f"Translation Manager inizializzato (lingua: {translation_manager.get_current_language()})")

    prefs_service = PreferencesService(logger)
    # Imposta lingua dal preferences
    translation_manager.set_language(prefs_service.get_language())

    # Avvia interfaccia - PASSAGGIO CORRETTO
    window = DashboardWindow(
        db_service,  # db_service
        prefs_service,  # preferences_service
        supplier_service,
        translation_manager,
        logger=logger  # logger (keyword argument)
    )
    window.show()

    sys.exit(app.exec())