from PySide6.QtWidgets import QFrame, QVBoxLayout

from styles import (
    COLORE_WIDGET_2,
)
from views.base_view import BaseView


class CalendarView(BaseView):
    """View per il calendario/scadenziario"""

    def __init__(self, property_service, transaction_service, deadline_service,
                 translation_service, logger, user_prefs_service=None, parent=None):
        self.tm                 = translation_service
        self.logger             = logger
        self.deadline_service   = deadline_service
        self.user_prefs_service = user_prefs_service
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLORE_WIDGET_2}; border-radius: 12px;"
        )
        frame_layout = QVBoxLayout(frame)

        # Importa qui per non creare circolarità; usa la versione patchata
        # che accetta user_prefs_service
        try:
            from dialogs_calendar_patch import PlannerCalendarWidget
        except ImportError:
            # Fallback alla versione originale se il patch non è ancora applicato
            from dialogs import PlannerCalendarWidget

        calendar_widget = PlannerCalendarWidget(
            self.deadline_service,
            self.property_service,
            self.tm,
            self.logger,
            user_prefs_service=self.user_prefs_service,
        )
        frame_layout.addWidget(calendar_widget)

        main_layout.addWidget(frame)
