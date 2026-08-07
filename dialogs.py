# dialogs.py
import os
from datetime import date, timedelta

from PySide6.QtCore import QDate, QEvent, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from styles import (
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_ITEM_HOVER,
    COLORE_ITEM_SELEZIONATO,
    COLORE_RIGA_1,
    COLORE_SECONDARIO,
    COLORE_WARNING,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_button_main_header,
    default_dialog_style,
    default_export_button,
    default_selector_date_export,
)
from transaction_types import label_to_canonical
from validation_utils import ValidationError, parse_decimal, validate_date, validate_required_text

DOCS_DIR = "docs"


class DocumentMetadataDialog(QDialog):
    """Dialog per inserire i metadati del documento CON VALIDAZIONE"""

    def __init__(self, filename, tm, parent=None):
        self.tm = tm
        super().__init__(parent)
        self.setWindowTitle(self.tm.get("ETICHETTE","NUOVO_DOCUMENTO"))
        self.setMinimumSize(300, 200)
        self.setStyleSheet(default_dialog_style)

        layout = QFormLayout(self)

        # Spesa/Guadagno
        self.type_box = QComboBox()
        self.type_box.addItems([self.tm.get("ETICHETTE","GUADAGNO"), self.tm.get("ETICHETTE","SPESA")])
        layout.addRow(f"{self.tm.get('ETICHETTE','TIPO')}:", self.type_box)

        # Emittente
        self.emittente_input = QLineEdit()
        self.emittente_input.setPlaceholderText(self.tm.get("PLACEHOLDER","ES_FORNITORE"))
        layout.addRow(f"{self.tm.get('ETICHETTE','FORNITORE')}:", self.emittente_input)

        # servizio
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText(self.tm.get("PLACEHOLDER","NOME_SERVIZIO"))
        layout.addRow(f"{self.tm.get('ETICHETTE','SERVIZIO')}:", self.service_input)

        # Importo
        self.importo_input = QLineEdit()
        self.importo_input.setPlaceholderText(self.tm.get("PLACEHOLDER","ES_IMPORTO"))
        layout.addRow(f"{self.tm.get('ETICHETTE','IMPORTO')}:", self.importo_input)

        # Data Fattura
        self.data_fattura = QDateEdit()
        self.data_fattura.setDisplayFormat("dd/MM/yyyy")
        self.data_fattura.setCalendarPopup(True)
        self.data_fattura.setDate(QDate.currentDate())
        layout.addRow(f"{self.tm.get('ETICHETTE','DATA_FATTURA')}:", self.data_fattura)

        # Pulsanti OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def accept(self):
        """Validazione con gestione errori dettagliata"""
        try:
            # Valida tipo
            tipo = self.type_box.currentText().strip()
            if not tipo:
                raise ValidationError("Seleziona il tipo")

            # Valida emittente (solleva ValidationError se non valido)
            validate_required_text(
                self.emittente_input.text(),
                "Fornitore/Emittente",
                min_length=2,
                max_length=100
            )

            # Valida servizio
            validate_required_text(
                self.service_input.text(),
                "Servizio",
                min_length=2,
                max_length=100
            )

            # Valida importo — gestisce sia virgola che punto
            parse_decimal(
                self.importo_input.text(),
                "Importo"
            )

            # Valida data
            validate_date(self.data_fattura.date(), "Data fattura")

            # Se tutto ok, procedi
            super().accept()

        except ValidationError as e:
            QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))

    def get_data(self):
        """Restituisce i dati validati"""
        return {
            "tipo": label_to_canonical(self.type_box.currentText(), self.tm),
            "provider": self.emittente_input.text().strip(),
            "service": self.service_input.text().strip(),
            "importo": self.importo_input.text().strip(),  # Verrà parsato dal service
            "data_fattura": self.data_fattura.date().toPython(),
        }


class AddDeadlineDialog(QDialog):
    """Dialog per inserire una nuova scadenza CON VALIDAZIONE"""

    def __init__(self, tm, properties=None, parent=None):
        super().__init__(parent)
        self.tm = tm
        self.setWindowTitle(self.tm.get("ETICHETTE", "NUOVA_SCADENZA"))
        self.setMinimumSize(400, 300)
        self.setStyleSheet(default_dialog_style)

        layout = QFormLayout(self)

        # Titolo
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(self.tm.get("ETICHETTE", "NUOVA_SCADENZA"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'TITOLO')}*:", self.title_input)

        # Descrizione
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "DETTAGLI_AGGIUNTIVI"))
        self.description_input.setMaximumHeight(80)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'DESCRIZIONE')}:", self.description_input)

        # Data scadenza
        self.due_date = QDateEdit()
        self.due_date.setDisplayFormat("dd/MM/yyyy")
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())
        layout.addRow(f"{self.tm.get('ETICHETTE', 'DATA_SCADENZA')}*:", self.due_date)

        # Proprietà (opzionale)
        self.property_combo = QComboBox()
        self.property_combo.addItem(self.tm.get('ETICHETTE', 'ALL_PROPERTIES'), None)
        if properties:
            for prop in properties:
                self.property_combo.addItem(prop["name"], prop["id"])
        layout.addRow(f"{self.tm.get('ETICHETTE', 'PROPRIETA')}*:", self.property_combo)

        # Pulsanti
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def accept(self):
        """Validazione"""
        try:
            # Valida titolo
            validate_required_text(
                self.title_input.text(),
                "Titolo",
                min_length=3,
                max_length=200
            )

            # Valida data
            validate_date(self.due_date.date(), self.tm.get("ETICHETTE","DATA_SCADENZA"))

            super().accept()

        except ValidationError as e:
            QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))

    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip() or None,
            "due_date": self.due_date.date().toPython(),
            "property_id": self.property_combo.currentData()
        }

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(50)

        # --- UI ---
        title_container = QWidget()
        title_container.setStyleSheet(f"background-color: {COLORE_SECONDARIO};")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.setSpacing(0)

        title_label = QLabel("🏠 Property Manager")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        title_layout.addWidget(title_label)

        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(40, 30)
        minimize_btn.setStyleSheet(default_button_main_header)
        minimize_btn.clicked.connect(parent.showMinimized)
        title_layout.addWidget(minimize_btn)

        # Salva riferimento al pulsante maximize per aggiornarlo
        self.maximize_btn = QPushButton("☐")
        self.maximize_btn.setFixedSize(40, 30)
        self.maximize_btn.setStyleSheet(default_button_main_header)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.maximize_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 30)
        close_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            border: none;
            color: white;
            font-weight: normal;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #e81123;
        }
        """)
        close_btn.clicked.connect(parent.close)
        title_layout.addWidget(close_btn)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(title_container)

        # --- Drag logic ---
        self._click_pos = None

        # Icona iniziale + sync su OGNI cambio di stato della finestra
        # (doppio click, Win+frecce, snap ai bordi, drag di sistema)
        self.update_maximize_icon()
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent and event.type() == QEvent.Type.WindowStateChange:
            self.update_maximize_icon()
        return super().eventFilter(obj, event)

    def toggle_maximize(self):
        """Toggle massimizza/ripristina (l'icona si aggiorna via eventFilter)"""
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def update_maximize_icon(self):
        """Aggiorna l'icona del pulsante in base allo stato della finestra"""
        if self.parent.isMaximized():
            self.maximize_btn.setText("❐")  # Icona "restore" (due quadrati sovrapposti)
        else:
            self.maximize_btn.setText("☐")  # Icona "maximize" (quadrato vuoto)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._click_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

    def mouseMoveEvent(self, event):
        """
        Delega il trascinamento al sistema operativo (startSystemMove):
        gestisce correttamente monitor multipli con DPI diversi, snap ai
        bordi e animazioni — il move() manuale saltava tra gli schermi.
        """
        if self._click_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        # Soglia per distinguere un click da un drag
        moved = (event.globalPosition().toPoint() - self._click_pos).manhattanLength()
        if moved < QApplication.startDragDistance():
            return

        win = self.parent
        if win.isMaximized():
            # Come le finestre native: il drag ripristina la finestra
            # tenendo il cursore nella stessa posizione relativa della barra
            ratio = event.position().x() / max(1, self.width())
            win.showNormal()
            gp = event.globalPosition().toPoint()
            win.move(int(gp.x() - win.width() * ratio),
                     gp.y() - int(event.position().y()))

        self._click_pos = None
        win.windowHandle().startSystemMove()
        event.accept()


class ClickableDayCell(QFrame):
    """
    Cella giorno del calendario.

    Bordi colorati:
      - Blu (default)     → giorno normale
      - Arancione         → almeno una scadenza cade entro warning_days
      - Hover: sempre blu chiaro
    """

    def __init__(self, day, date_str, deadlines, parent_calendar, tm,
                 is_upcoming: bool = False, is_today: bool = False):
        super().__init__()
        self.day = day
        self.date_str = date_str
        self.deadlines = deadlines
        self.parent_calendar = parent_calendar
        self.tm = tm
        self.is_upcoming = is_upcoming
        self.is_today = is_today

        # Colore bordo basato sullo stato
        if is_today:
            border = f"2px solid {COLORE_ITEM_HOVER}"
        elif is_upcoming and deadlines:
            border = f"2px solid {COLORE_WARNING}"  # arancione = imminente
        elif deadlines:
            border = f"1px solid {COLORE_SECONDARIO}"
        else:
            border = "1px solid transparent"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_RIGA_1};
                border-radius: 6px;
                border: {border};
            }}
            QFrame:hover {{
                background-color: {COLORE_ITEM_HOVER};
                border: 2px solid {COLORE_ITEM_HOVER};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self.tm.get("calendar", "click_add_deadline"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # Numero del giorno
        day_color = COLORE_ITEM_HOVER if is_today else "white"
        label = QLabel(str(day))
        label.setStyleSheet(
            f"font-size: 14px; color: {day_color}; font-weight: bold;"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(label)

        # Scadenze
        for deadline in deadlines:
            # Etichetta colorata in arancione se imminente, altrimenti blu
            bg = COLORE_WARNING if is_upcoming else COLORE_SECONDARIO
            deadline_label = QLabel(f"📌 {deadline['title']}")
            deadline_label.setStyleSheet(f"""
                font-size: 10px;
                color: white;
                background-color: {bg};
                padding: 2px 4px;
                border-radius: 3px;
                margin-top: 2px;
            """)
            deadline_label.setWordWrap(True)
            layout.addWidget(deadline_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_calendar.add_deadline_for_date(self.date_str)
        super().mousePressEvent(event)


class PlannerCalendarWidget(QWidget):
    """
    Calendario scadenze mensile.

    Parametri aggiuntivi rispetto alla versione originale:
        user_prefs_service — opzionale; se fornito, la finestra di preavviso
                             viene letta dal DB invece di usare il default 7.
    """

    def __init__(self, deadline_service, property_service, tm, logger,
                 user_prefs_service=None):
        super().__init__()
        self.deadline_service = deadline_service
        self.property_service = property_service
        self.tm = tm
        self.logger = logger
        self.user_prefs_service = user_prefs_service

        self.setStyleSheet(
            f"background-color: {COLORE_WIDGET_2}; color: {COLORE_BIANCO}"
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setStyleSheet(
            "font-size:16px; font-weight: bold; color:white"
        )
        header.addWidget(self.month_label)
        header.addStretch()

        add_deadline_btn = QPushButton(
            f"+ {self.tm.get('PULSANTI', 'AGGIUNGI')}"
        )
        add_deadline_btn.setStyleSheet(default_aggiungi_button)
        add_deadline_btn.clicked.connect(lambda: self.add_deadline())
        header.addWidget(add_deadline_btn)

        prev_btn = QPushButton()
        prev_btn.setIcon(QIcon("./icons/left-arrow.png"))
        next_btn = QPushButton()
        next_btn.setIcon(QIcon("./icons/right-arrow.png"))
        header.addWidget(prev_btn)
        header.addWidget(next_btn)
        main_layout.addLayout(header)

        # Giorni della settimana
        weekdays_layout = QHBoxLayout()
        weekdays = tm.get("LISTE", "WEEKDAYS_SHORT").split(";")
        for day in weekdays:
            day_label = QLabel(day)
            day_label.setStyleSheet(
                "font-size: 12px; color: white; font-weight: bold;"
            )
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weekdays_layout.addWidget(day_label)
        main_layout.addLayout(weekdays_layout)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        main_layout.addLayout(self.grid)

        self.current_date = QDate.currentDate()
        prev_btn.clicked.connect(self.prev_month)
        next_btn.clicked.connect(self.next_month)

        self.populate_month()

    # ──────────────────────────────────────────────────────────────
    #  Helper preferenze
    # ──────────────────────────────────────────────────────────────

    def _warning_days(self) -> int:
        """Giorni di preavviso letti dal DB tramite user_prefs_service."""
        if self.user_prefs_service:
            return self.user_prefs_service.get_deadline_warning_days()
        return 7

    # ──────────────────────────────────────────────────────────────
    #  Calendario
    # ──────────────────────────────────────────────────────────────

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def populate_month(self):
        self._clear_grid()

        month = self.current_date.month()
        year = self.current_date.year()
        self.month_label.setText(
            self.tm.get("LISTE", "MONTHS_FULL").split(";")[month - 1]
        )

        first_day = QDate(year, month, 1)
        start_col = first_day.dayOfWeek() - 1
        days_in_month = first_day.daysInMonth()

        # Carica scadenze del mese in una query
        all_deadlines = self._load_month_deadlines(year, month)

        # Calcola finestra imminente
        warning_days = self._warning_days()
        today = date.today()
        upcoming_limit = today + timedelta(days=warning_days)

        row, col = 0, start_col
        for day in range(1, days_in_month + 1):
            date_obj = date(year, month, day)
            date_str = date_obj.isoformat()  # "YYYY-MM-DD"
            deadlines = all_deadlines.get(date_str, [])

            # La cella è "imminente" se la data cade entro la finestra
            # e ci sono scadenze quel giorno
            is_upcoming = bool(deadlines) and (today <= date_obj <= upcoming_limit)
            is_today = (date_obj == today)

            cell = ClickableDayCell(
                day, date_str, deadlines, self, self.tm,
                is_upcoming=is_upcoming,
                is_today=is_today,
            )
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def _load_month_deadlines(self, year, month) -> dict:
        try:
            return self.deadline_service.get_by_month(year, month)
        except Exception as e:
            self.logger.error(f"Errore caricamento scadenze mese: {e}")
            return {}

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.populate_month()

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.populate_month()

    # ──────────────────────────────────────────────────────────────
    #  Aggiungi scadenza
    # ──────────────────────────────────────────────────────────────

    def add_deadline(self, preset_date=None):

        properties = self.property_service.get_all()
        dialog = AddDeadlineDialog(self.tm, properties=properties, parent=self)

        if preset_date:
            date_obj = QDate.fromString(preset_date, "yyyy-MM-dd")
            if date_obj.isValid():
                dialog.due_date.setDate(date_obj)

        if dialog.exec():
            data = dialog.get_data()
            deadline_id = self.deadline_service.create(
                title=data["title"],
                description=data["description"],
                due_date=data["due_date"],
                property_id=data["property_id"],
            )
            if deadline_id:
                QMessageBox.information(
                    self,
                    self.tm.get("MESSAGGI", "SUCCESSO"),
                    self.tm.get("MESSAGGI", "SALVATO"),
                )
                self.logger.info(
                    f"{self.tm.get('MESSAGGI', 'SALVATO')} {data['title']}"
                )
                self.populate_month()
            else:
                QMessageBox.warning(
                    self,
                    self.tm.get("MESSAGGI", "ERRORE"),
                    self.tm.get("MESSAGGI", "ERRORE"),
                )
                self.logger.error(
                    f"{self.tm.get('MESSAGGI', 'ERRORE')} {data['title']}"
                )

    def add_deadline_for_date(self, date_str):
        self.add_deadline(preset_date=date_str)


class ExportDialog(QDialog):
    """Dialog per esportare transazioni in PDF/Excel"""

    def __init__(self, transaction_service, property_service, export_service, tm, parent=None):
        super().__init__(parent)
        self.transaction_service = transaction_service
        self.property_service = property_service
        self.export_service = export_service
        self.tm = tm

        self.setWindowTitle(self.tm.get("ETICHETTE", "ESPORTA_DATI"))
        self.setMinimumSize(500, 400)
        self.setStyleSheet("QDialog { background-color: #131b23; }")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Titolo
        title = QLabel(f"📥 {self.tm.get('ETICHETTE', 'ESPORTA_DATI')}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        main_layout.addWidget(title)

        # === SELEZIONE PROPRIETÀ ===
        property_group = QGroupBox(self.tm.get("ETICHETTE", "PROPRIETA"))
        property_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #2c3e50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        property_layout = QVBoxLayout(property_group)

        self.property_combo = QComboBox()
        self.property_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a2530;
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView {
                background-color: #1a2530;
                color: white;
                selection-background-color: #007BFF;
            }
        """)

        self.property_combo.addItem(self.tm.get("ETICHETTE", "ALL_PROPERTIES"), None)
        properties = self.property_service.get_all()
        for prop in properties:
            self.property_combo.addItem(f"{prop['name']}", prop['id'])

        property_layout.addWidget(self.property_combo)
        main_layout.addWidget(property_group)

        # === SELEZIONE PERIODO ===
        period_group = QGroupBox(self.tm.get("ETICHETTE", "PERIODO"))
        period_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #2c3e50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        period_layout = QVBoxLayout(period_group)

        # Date pickers
        dates_layout = QHBoxLayout()

        start_label = QLabel(self.tm.get("ETICHETTE","DAL"))
        start_label.setStyleSheet("color: white;")
        dates_layout.addWidget(start_label)

        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setStyleSheet(default_selector_date_export)
        dates_layout.addWidget(self.start_date)

        end_label = QLabel(self.tm.get("ETICHETTE","AL"))
        end_label.setStyleSheet("color: white;")
        dates_layout.addWidget(end_label)

        self.end_date = QDateEdit()
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setStyleSheet(default_selector_date_export)
        dates_layout.addWidget(self.end_date)

        period_layout.addLayout(dates_layout)

        # Quick selects
        quick_layout = QHBoxLayout()

        btn_month = QPushButton("Ultimo mese")
        btn_month.clicked.connect(lambda: self.set_quick_period(1))

        btn_3months = QPushButton("Ultimi 3 mesi")
        btn_3months.clicked.connect(lambda: self.set_quick_period(3))

        btn_year = QPushButton("Ultimo anno")
        btn_year.clicked.connect(lambda: self.set_quick_period(12))

        for btn in [btn_month, btn_3months, btn_year]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #4a5f7f;
                }
            """)
            quick_layout.addWidget(btn)

        period_layout.addLayout(quick_layout)
        main_layout.addWidget(period_group)

        # === FORMATO EXPORT ===
        format_group = QGroupBox("Formato Export")
        format_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #2c3e50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        format_layout = QHBoxLayout(format_group)

        self.format_group = QButtonGroup()

        self.pdf_radio = QRadioButton("📄 PDF")
        self.pdf_radio.setChecked(True)
        self.pdf_radio.setStyleSheet("QRadioButton { color: white; font-size: 13px; }")

        self.excel_radio = QRadioButton("📊 Excel")
        self.excel_radio.setStyleSheet("QRadioButton { color: white; font-size: 13px; }")

        self.format_group.addButton(self.pdf_radio)
        self.format_group.addButton(self.excel_radio)

        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.excel_radio)
        format_layout.addStretch()

        main_layout.addWidget(format_group)

        # === BOTTONI ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton(f"❌ {self.tm.get('PULSANTI', 'ANNULLA')}")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ERROR};
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        export_btn = QPushButton(f"📥 {self.tm.get('PULSANTI', 'ESPORTA')}")
        export_btn.setStyleSheet(default_export_button)
        export_btn.clicked.connect(self.do_export)
        buttons_layout.addWidget(export_btn)

        main_layout.addLayout(buttons_layout)

    def set_quick_period(self, months):
        """Imposta periodo rapido"""
        end = QDate.currentDate()
        start = end.addMonths(-months)
        self.start_date.setDate(start)
        self.end_date.setDate(end)

    def do_export(self):
        """Esegue l'export"""
        # Valida date
        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(self, self.tm.get("common","error"), "La data di inizio deve essere precedente alla data di fine!")
            return

        # Recupera transazioni
        property_id = self.property_combo.currentData()
        property_name = self.property_combo.currentText().replace("🏠 ", "").replace("🏡 ", "")

        start_str = self.start_date.date().toString("yyyy-MM-dd")
        end_str = self.end_date.date().toString("yyyy-MM-dd")

        transactions = self.transaction_service.get_all(
            property_id=property_id,
            start_date=start_str,
            end_date=end_str
        )

        if not transactions:
            QMessageBox.warning(self, "Nessun dato", "Nessuna transazione trovata per il periodo selezionato!")
            return

        try:
            # Esporta
            if self.pdf_radio.isChecked():
                filepath = self.export_service.export_to_pdf(
                    transactions,
                    property_name=property_name if property_id else None,
                    start_date=self.start_date.date().toString("dd/MM/yyyy"),
                    end_date=self.end_date.date().toString("dd/MM/yyyy")
                )
                format_name = "PDF"
            else:
                filepath = self.export_service.export_to_excel(
                    transactions,
                    property_name=property_name if property_id else None,
                    start_date=self.start_date.date().toString("dd/MM/yyyy"),
                    end_date=self.end_date.date().toString("dd/MM/yyyy")
                )
                format_name = "Excel"

            # Messaggio successo
            reply = QMessageBox.question(
                self,
                "✅ Export Completato",
                f"Report {format_name} generato con successo!\n\n"
                f"📁 {filepath}\n\n"
                f"Vuoi aprire la cartella?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Apri cartella exports
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(filepath)))

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante l'export:\n{str(e)}")


class TransactionDialogWithSuppliers(QDialog):
    """Dialog transazione con suggerimenti fornitori intelligenti"""

    def __init__(self, property_service, supplier_service, tm, parent=None):
        super().__init__(parent)
        self.property_service = property_service
        self.supplier_service = supplier_service
        self.tm = tm
        self.selected_supplier = None

        self.setWindowTitle(self.tm.get("ETICHETTE","NUOVA_TRANSAZIONE"))
        self.setMinimumWidth(600)
        self.setStyleSheet(default_dialog_style)

        self.setup_ui()

    def setup_ui(self):
        """Costruisce l'interfaccia"""
        layout = QFormLayout(self)
        layout.setSpacing(15)

        # Tipo transazione
        self.type_box = QComboBox()
        self.type_box.addItems([
            self.tm.get("ETICHETTE", "SPESA"),
            self.tm.get("ETICHETTE", "GUADAGNO")
        ])
        self.type_box.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }}
        """)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'TIPO')}*:", self.type_box)

        # Proprietà
        self.property_combo = QComboBox()
        properties = self.property_service.get_all()
        for prop in properties:
            self.property_combo.addItem(prop['name'], prop['id'])
        self.property_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }}
        """)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'PROPRIETA')}*:", self.property_combo)

        # Categoria/Servizio
        self.service_combo = QComboBox()
        self.service_combo.setEditable(True)
        self.service_combo.setPlaceholderText(self.tm.get("PLACEHOLDER", "ES_BOLLETTA_LUCE"))
        self.service_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }}
        """)
        categories = self.supplier_service.get_categories()
        for cat in categories:
            self.service_combo.addItem(cat)
        self.service_combo.currentTextChanged.connect(self.show_supplier_suggestions)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'CATEGORIA')}*:", self.service_combo)

        # SUGGERIMENTI FORNITORI
        self.suggestions_group = QGroupBox(f"💡 {self.tm.get('ETICHETTE', 'FORNITORI_SUGGERITI')}")
        self.suggestions_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: {COLORE_WIDGET_2};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        suggestions_layout = QVBoxLayout(self.suggestions_group)
        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(150)
        self.suggestions_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORE_RIGA_1};
                border: none;
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORE_ITEM_SELEZIONATO};
            }}
            QListWidget::item:selected {{
                background-color: {COLORE_ITEM_SELEZIONATO};
            }}
        """)
        self.suggestions_list.itemClicked.connect(self.select_supplier)
        suggestions_layout.addWidget(self.suggestions_list)
        self.suggestions_group.setVisible(False)
        layout.addWidget(self.suggestions_group)

        # Fornitore selezionato (badge)
        self.selected_supplier_label = QLabel()
        self.selected_supplier_label.setStyleSheet(f"""
            background-color: {COLORE_ITEM_SELEZIONATO};
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
        """)
        self.selected_supplier_label.setVisible(False)
        layout.addWidget(self.selected_supplier_label)

        # Fornitore (manuale)
        self.provider_input = QLineEdit()
        self.provider_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "ES_FORNITORE"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'FORNITORE')}*:", self.provider_input)

        # Importo
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText(self.tm.get("PLACEHOLDER", "ES_IMPORTO"))
        layout.addRow(f"{self.tm.get('ETICHETTE', 'IMPORTO')}*:", self.amount_input)

        # Data
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
            }}
        """)
        layout.addRow(f"{self.tm.get('ETICHETTE', 'DATA')}*:", self.date_edit)

        # Bottoni
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def show_supplier_suggestions(self, category):
        """Mostra suggerimenti fornitori per la categoria"""
        if not category or len(category) < 2:
            self.suggestions_group.setVisible(False)
            return

        property_id = self.property_combo.currentData()
        suggestions = self.supplier_service.get_suggestions_for_transaction(
            category,
            property_id
        )

        self.suggestions_list.clear()

        if not suggestions:
            self.suggestions_group.setVisible(False)
            return

        for supplier in suggestions:
            item_widget = self.create_suggestion_item(supplier)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, supplier)  # Salva dati fornitore
            item.setSizeHint(item_widget.sizeHint())
            self.suggestions_list.addItem(item)
            self.suggestions_list.setItemWidget(item, item_widget)

        self.suggestions_group.setVisible(True)

    def create_suggestion_item(self, supplier):
        """Crea widget per suggerimento fornitore"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Nome fornitore
        name = QLabel(f"🏢 {supplier['name']}")
        name.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        layout.addWidget(name)

        # Rating
        if supplier.get('avg_rating', 0) > 0:
            rating = QLabel(f"⭐ {supplier['avg_rating']}/5")
            rating.setStyleSheet("color: #f39c12; font-size: 11px;")
            layout.addWidget(rating)

        # Statistiche
        if supplier.get('service_count', 0) > 0:
            services = QLabel(f"📊 {supplier['service_count']} servizi")
            services.setStyleSheet("color: #95a5a6; font-size: 11px;")
            layout.addWidget(services)

        # Totale speso
        if supplier.get('total_spent', 0) > 0:
            spent = QLabel(f"💰 {supplier['total_spent']:,.0f}€")
            spent.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
            layout.addWidget(spent)

        layout.addStretch()
        return widget

    def select_supplier(self, item):
        """Seleziona un fornitore suggerito"""
        supplier = item.data(Qt.ItemDataRole.UserRole)
        self.selected_supplier = supplier

        # Compila automaticamente i campi
        self.provider_input.setText(supplier['name'])
        if supplier.get('phone'):
            self.provider_input.setToolTip(f"📞 {supplier['phone']}")

        # Mostra badge fornitore selezionato
        self.selected_supplier_label.setText(
            f"✅ Fornitore selezionato: {supplier['name']} "
            f"(⭐ {supplier.get('avg_rating', 0)}/5)"
        )
        self.selected_supplier_label.setVisible(True)

    def get_data(self):
        """Ritorna i dati della transazione"""
        return {
            "tipo": label_to_canonical(self.type_box.currentText(), self.tm),
            "property_id": self.property_combo.currentData(),
            "service": self.service_combo.currentText().strip(),
            "provider": self.provider_input.text().strip(),
            "importo": self.amount_input.text().strip(),
            "data_fattura": self.date_edit.date().toString("dd/MM/yyyy"),
            "supplier_id": self.selected_supplier['id'] if self.selected_supplier else None
        }

    def accept(self):
        """Validazione prima di accettare"""
        try:
            # Valida categoria
            validate_required_text(
                self.service_combo.currentText(),
                "Categoria",
                min_length=2,
                max_length=100
            )

            # Valida fornitore
            validate_required_text(
                self.provider_input.text(),
                "Fornitore",
                min_length=2,
                max_length=100
            )

            # Valida importo
            parse_decimal(self.amount_input.text(), "Importo")

            super().accept()

        except ValidationError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))
