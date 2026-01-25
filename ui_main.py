import sys
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt
from dialogs import CustomTitleBar
import Functions
import logging
from styles import *
from translations_manager import get_translation_manager

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


class DashboardWindow(QMainWindow):
    def __init__(self, db_service, preferences_service, logger):
        super().__init__()

        # Logger
        self.logger = logger

        # Servizi
        self.preferences_service = preferences_service
        self.tm = get_translation_manager()

        # Inizializza i services INTERNAMENTE (non li riceve più come parametri)
        from services.property_service import PropertyService
        from services.transaction_service import TransactionService
        from services.document_service import DocumentService
        from services.deadline_service import DeadlineService

        self.property_service = PropertyService(self.logger)
        self.transaction_service = TransactionService(self.logger)
        self.document_service = DocumentService(self.logger)
        self.deadline_service = DeadlineService(self.logger)

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
            self.property_service,
            self.transaction_service,
            self.deadline_service,
            self.preferences_service,
            self
        ))

        # SCHERMO INTERO DI DEFAULT
        self.showMaximized()

    def update_menu_items(self):
        """Aggiorna le voci del menu con le traduzioni"""
        self.menu.clear()

        menu_items = [
            ("icons/homepage.png", self.tm.get("menu", "dashboard")),
            ("icons/property.png", self.tm.get("menu", "properties")),
            ("icons/document.png", self.tm.get("menu", "documents")),
            ("icons/bar-chart.png", self.tm.get("menu", "accounting")),
            ("icons/pie-chart.png", self.tm.get("menu", "report")),
            ("icons/calendar.png", self.tm.get("menu", "calendar")),
            ("icons/settings.png", self.tm.get("menu", "settings")),
        ]

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
                self.property_service,
                self.transaction_service,
                self.deadline_service,
                self.preferences_service,
                self
            ))
        elif index == 1:  # Properties
            self.show_view(PropertiesView(
                self.property_service,
                self.transaction_service,
                self.document_service,
                self.deadline_service,
                self
            ))
        elif index == 2:  # Documents
            self.show_view(DocumentsView(
                self.property_service,
                self.transaction_service,
                self.document_service,
                self
            ))
        elif index == 3:  # Accounting
            self.show_view(AccountingView(
                self.property_service,
                self.transaction_service,
                self
            ))
        elif index == 4:  # Report
            self.show_view(ReportView(
                self.property_service,
                self.transaction_service,
                self
            ))
        elif index == 5:  # Calendar
            self.show_view(CalendarView(
                self.property_service,
                self.transaction_service,
                self.deadline_service,
                self
            ))
        elif index == 6:  # Settings
            self.show_view(SettingsView(
                self.property_service,
                self.transaction_service,
                self
            ))

    def navigate_to_section(self, section_name):
        """Naviga a una sezione specifica tramite nome"""
        # Mappa i nomi tradotti agli indici
        section_indices = {
            self.tm.get("menu", "dashboard"): 0,
            self.tm.get("menu", "properties"): 1,
            self.tm.get("menu", "documents"): 2,
            self.tm.get("menu", "accounting"): 3,
            self.tm.get("menu", "report"): 4,
            self.tm.get("menu", "calendar"): 5,
            self.tm.get("menu", "settings"): 6
        }

        if section_name in section_indices:
            index = section_indices[section_name]
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