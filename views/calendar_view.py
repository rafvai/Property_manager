from PySide6.QtWidgets import QVBoxLayout, QFrame
from views.base_view import BaseView
from dialogs import PlannerCalendarWidget
from styles import *


class CalendarView(BaseView):
    """View per il calendario/scadenziario"""

    def __init__(self, property_service, transaction_service, deadline_service, parent=None):
        self.deadline_service = deadline_service
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia calendario"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        frame = QFrame()
        frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px;")
        frame_layout = QVBoxLayout(frame)

        # 🆕 Passa i services al calendario
        calendar_widget = PlannerCalendarWidget(self.deadline_service, self.property_service)
        frame_layout.addWidget(calendar_widget)

        main_layout.addWidget(frame)