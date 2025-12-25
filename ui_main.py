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


class DashboardWindow(QMainWindow):
    def __init__(self, db_service):
        super().__init__()

        # Inizializza i services
        conn = db_service.conn
        self.property_service = PropertyService(conn)
        self.transaction_service = TransactionService(conn)
        self.document_service = DocumentService(conn)
        self.deadline_service = DeadlineService(conn)

        # Finestra principale
        self.setWindowTitle("Property Manager MVP")
        self.setGeometry(200, 200, 1000, 600)
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
        menu_items = [
            ("icons/homepage.png", "Dashboard"),
            ("icons/property.png", "Le mie proprietà"),
            ("icons/document.png", "Documenti"),
            ("icons/bar-chart.png", "Contabilità"),
            ("icons/pie-chart.png", "Report"),
            ("icons/calendar.png", "Calendario"),
            ("icons/settings.png", "Impostazioni"),
        ]
        for icon_path, text in menu_items:
            item = QListWidgetItem(QIcon(icon_path), text)
            self.menu.addItem(item)

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
            self  # Passa riferimento alla finestra principale
        ))

        # SCHERMO INTERO DI DEFAULT
        self.showMaximized()

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
        voce = self.sender().item(index).text()

        if "Dashboard" in voce:
            self.show_view(DashboardView(
                self.property_service,
                self.transaction_service,
                self.deadline_service,
                self
            ))
        elif "proprietà" in voce:
            self.show_view(PropertiesView(
                self.property_service,
                self.transaction_service,
                self.document_service,
                self.deadline_service,
                self
            ))
        elif "Documenti" in voce:
            self.show_view(DocumentsView(
                self.property_service,
                self.transaction_service,
                self.document_service,
                self
            ))
        elif "Contabilità" in voce:
            self.show_view(AccountingView(
                self.property_service,
                self.transaction_service,
                self
            ))
        elif "Report" in voce:
            self.show_view(ReportView(
                self.property_service,
                self.transaction_service,
                self
            ))
        elif "Calendario" in voce:
            self.show_view(CalendarView(
                self.property_service,
                self.transaction_service,
                self.deadline_service,
                self
            ))
        elif "Impostazioni" in voce:
            self.show_view(SettingsView(
                self.property_service,
                self.transaction_service,
                self
            ))

    # NAVIGA ALLE SEZIONI
    def navigate_to_section(self, section_name):
        """Naviga a una sezione specifica tramite nome"""
        section_map = {
            "Dashboard": 0,
            "Le mie proprietà": 1,
            "Documenti": 2,
            "Contabilità": 3,
            "Report": 4,
            "Calendario": 5,
            "Impostazioni": 6
        }

        if section_name in section_map:
            index = section_map[section_name]
            self.menu.setCurrentRow(index)
            self.menu_navigation(index)

    def resizeEvent(self, event):
        """Ridimensiona il menu laterale"""
        if hasattr(self, 'menu'):  # 🔧 Verifica che il menu esista
            self.menu.setFixedWidth(int(self.width() * W_LAT_MENU))
        super().resizeEvent(event)

    def toggle_max_restore(self):
        """Massimizza/ripristina finestra"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
