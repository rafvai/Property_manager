import sys
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt
from dialogs import CustomTitleBar
import logging
from styles import *

from services.database_service import DatabaseService
from services.property_service import PropertyService
from services.transaction_service import TransactionService
from services.document_service import DocumentService
from services.deadline_service import DeadlineService

from views.dashboard_view import DashboardView
from views.properties_view import PropertiesView
from views.documents_view import DocumentsView
from views.accounting_view import AccountingView
from views.report_view import ReportView
from views.calendar_view import CalendarView
from views.settings_view import SettingsView
from views.suppliers_view import SuppliersView


class DashboardWindow(QMainWindow):
    def __init__(self, db_service, preferences_service, supplier_service, translation_manager, auth_service, user_prefs_service, logger, is_admin=False):
        super().__init__()

        # Logger
        self.logger = logger

        # Ruolo utente
        self.is_admin = is_admin

        # Servizi
        self.db_service = db_service
        self.preferences_service = preferences_service
        self.tm = translation_manager
        self.supplier_service = supplier_service

        # Inizializza i services INTERNAMENTE
        from services.property_service import PropertyService
        from services.transaction_service import TransactionService
        from services.document_service import DocumentService
        from services.deadline_service import DeadlineService

        self.supplier_service = supplier_service
        self.property_service = PropertyService(self.logger)
        self.transaction_service = TransactionService(self.logger,  supplier_service=self.supplier_service)
        self.document_service = DocumentService(self.logger)
        self.deadline_service = DeadlineService(self.logger)
        self.auth_service = auth_service
        self.user_prefs_service = user_prefs_service

        # Finestra principale
        self.setWindowTitle("Property Manager MVP")
        self.setGeometry(200, 200, 1200, 700)
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Container principale
        container = QWidget()
        self.setCentralWidget(container)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)

        # Body: menu + contenuti
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Menu laterale
        self.menu = QListWidget()
        self.update_menu_items()

        self.menu.setFixedWidth(int(self.width() * W_LAT_MENU))
        self.menu.setMinimumWidth(100)
        self.menu.setStyleSheet(default_menu_lat_style)
        self.menu.setFocusPolicy(Qt.NoFocus)
        self.menu.currentRowChanged.connect(self.menu_navigation)
        self.menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Area contenuti
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_area.setLayout(QVBoxLayout())

        # Aggiungi al layout
        body_layout.addWidget(self.menu)
        body_layout.addWidget(self.content_area)
        container_layout.addWidget(body_widget)

        # Stile generale
        container.setStyleSheet(f"background-color: {COLORE_BACKGROUND};")

        # Mostra dashboard di default
        self.show_view(DashboardView(
            property_service=self.property_service,
            transaction_service=self.transaction_service,
            deadline_service=self.deadline_service,
            preferences_service=self.preferences_service,
            main_window=self,
            translation_manager=self.tm,
            logger=self.logger,
            parent=self
        ))

        # SCHERMO INTERO DI DEFAULT
        self.showMaximized()

    def update_menu_items(self):
        """Aggiorna le voci del menu con le traduzioni"""
        self.menu.clear()

        menu_items = [
            ("icons/homepage.png", self.tm.get("ETICHETTE", "DASHBOARD")),
            ("icons/property.png", self.tm.get("ETICHETTE", "PROPERTIES")),
            ("icons/document.png", self.tm.get("ETICHETTE", "DOCUMENTS")),
            ("icons/bar-chart.png", self.tm.get("ETICHETTE", "FINANZE")),
            ("icons/pie-chart.png", self.tm.get("ETICHETTE", "TRANSAZIONI")),
            ("icons/calendar.png", self.tm.get("ETICHETTE", "CALENDAR")),
            ("icons/security.png", self.tm.get("ETICHETTE", "FORNITORI")),
            ("icons/settings.png", self.tm.get("ETICHETTE", "IMPOSTAZIONI"))
        ]
        # La voce Traduzioni è visibile solo agli admin
        if self.is_admin:
            menu_items.append(("icons/settings.png", self.tm.get("MENU", "TRADUZIONI")))

        for icon_path, text in menu_items:
            item = QListWidgetItem(QIcon(icon_path), text)
            self.menu.addItem(item)

    def show_view(self, view):
        """Mostra una view nell'area contenuti"""
        layout = self.content_area.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        layout.addWidget(view)

    def menu_navigation(self, index):
        """Gestisce la navigazione del menu"""
        if index == 0:  # Dashboard
            self.show_view(DashboardView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                deadline_service=self.deadline_service,
                preferences_service=self.preferences_service,
                main_window=self,
                translation_manager=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 1:  # Properties
            self.show_view(PropertiesView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                document_service=self.document_service,
                deadline_service=self.deadline_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 2:  # Documents
            self.show_view(DocumentsView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                document_service=self.document_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 3:  # Accounting
            self.show_view(AccountingView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 4:  # Report
            self.show_view(ReportView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                supplier_service=self.supplier_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 5:  # Calendar
            self.show_view(CalendarView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                deadline_service=self.deadline_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 6:  # Fornitori
            self.show_view(SuppliersView(
                supplier_service=self.supplier_service,
                property_service=self.property_service,
                translation_service=self.tm,
                logger=self.logger,
                parent=self
            ))
        elif index == 7:  # Settings
            self.show_view(SettingsView(
                property_service=self.property_service,
                transaction_service=self.transaction_service,
                translation_service=self.tm,
                auth_service=self.auth_service,
                user_prefs_service=self.user_prefs_service,
                logger=self.logger,
                parent=self
            ))
        elif index == 8 and self.is_admin:  # Traduzioni
            from views.translations_admin_view_simple import TranslationsAdminView
            self.show_view(TranslationsAdminView(
                translation_manager=self.tm,
                logger=self.logger,
                parent=self
            ))

    def navigate_to_section(self, section_key: str):
        """
        Naviga tramite chiave canonica — indipendente da lingua e ordine del menu.
        Usa le stesse chiavi di update_menu_items().
        """
        section_map = {
            "DASHBOARD": 0,
            "PROPERTIES": 1,
            "DOCUMENTS": 2,
            "FINANZE": 3,
            "TRANSAZIONI": 4,
            "CALENDAR": 5,
            "FORNITORI": 6,
            "IMPOSTAZIONI": 7,
        }

        index = section_map.get(section_key)
        if index is None:
            self.logger.warning(f"navigate_to_section: chiave sconosciuta '{section_key}'")
            return

        self.menu.setCurrentRow(index)
        self.menu_navigation(index)

    def resizeEvent(self, event):
        """Ridimensiona il menu laterale"""
        if hasattr(self, 'menu'):
            self.menu.setFixedWidth(int(self.width() * W_LAT_MENU))
        super().resizeEvent(event)

    def toggle_max_restore(self):
        """Massimizza/ripristina finestra"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()