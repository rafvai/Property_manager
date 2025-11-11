from PySide6.QtWidgets import QVBoxLayout, QFrame
from views.base_view import BaseView
from dialogs import PlannerCalendarWidget
from styles import *


class CalendarView(BaseView):
    """View per il calendario/scadenziario"""

    def setup_ui(self):
        """Costruisce l'interfaccia calendario"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        frame = QFrame()
        frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px;")
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(PlannerCalendarWidget())

        main_layout.addWidget(frame)