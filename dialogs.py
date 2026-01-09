# dialogs.py
import os
import shutil

from PySide6.QtCore import Qt, QDate, QPoint, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFileDialog, QListWidget, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QDateEdit, QWidget, QHBoxLayout, QSizePolicy, QGridLayout, QFrame, QTextEdit, QRadioButton, QButtonGroup, QGroupBox
)

from styles import COLORE_SECONDARIO, COLORE_WIDGET_2, COLORE_RIGA_1, COLORE_ITEM_HOVER, default_button_main_header, \
    default_aggiungi_button, default_selector_date_export, default_export_button, COLORE_ERROR
from validation_utils import parse_decimal, validate_required_text, validate_date, ValidationError


DOCS_DIR = "docs"


class DocumentMetadataDialog(QDialog):
    """Dialog per inserire i metadati del documento CON VALIDAZIONE"""

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Metadati per {filename}")
        self.setMinimumSize(300, 200)

        layout = QFormLayout(self)

        # Spesa/Guadagno
        self.type_box = QComboBox()
        self.type_box.addItems(["Entrata", "Uscita"])
        layout.addRow("Tipo:", self.type_box)

        # Emittente
        self.emittente_input = QLineEdit()
        self.emittente_input.setPlaceholderText("Es: ENEL Energia")
        layout.addRow("Fornitore/Emittente:", self.emittente_input)

        # servizio
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("Es: Bolletta Luce")
        layout.addRow("Servizio:", self.service_input)

        # Importo
        self.importo_input = QLineEdit()
        self.importo_input.setPlaceholderText("Es: 123,45 oppure 123.45")
        self.importo_input.setToolTip("Puoi usare sia la virgola (123,45) che il punto (123.45)")
        layout.addRow("Importo totale (€):", self.importo_input)

        # Data Fattura
        self.data_fattura = QDateEdit()
        self.data_fattura.setDisplayFormat("dd/MM/yyyy")
        self.data_fattura.setCalendarPopup(True)
        self.data_fattura.setDate(QDate.currentDate())
        layout.addRow("Data fattura:", self.data_fattura)

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

            # Valida emittente
            emittente = validate_required_text(
                self.emittente_input.text(),
                "Fornitore/Emittente",
                min_length=2,
                max_length=100
            )

            # Valida servizio
            servizio = validate_required_text(
                self.service_input.text(),
                "Servizio",
                min_length=2,
                max_length=100
            )

            # Valida importo - 🔥 GESTISCE SIA VIRGOLA CHE PUNTO
            importo = parse_decimal(
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
            "tipo": self.type_box.currentText(),
            "provider": self.emittente_input.text().strip(),
            "service": self.service_input.text().strip(),
            "importo": self.importo_input.text().strip(),  # Verrà parsato dal service
            "data_fattura": self.data_fattura.date().toString("dd/MM/yyyy"),
        }


class AddDeadlineDialog(QDialog):
    """Dialog per inserire una nuova scadenza CON VALIDAZIONE"""

    def __init__(self, tm, properties=None, parent=None):
        super().__init__(parent)
        self.tm = tm
        self.setWindowTitle(self.tm.get("calendar", "new_deadline"))
        self.setMinimumSize(400, 300)

        layout = QFormLayout(self)

        # Titolo
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Es: Pagamento IMU")
        layout.addRow("Titolo*:", self.title_input)

        # Descrizione
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Dettagli aggiuntivi (opzionale)")
        self.description_input.setMaximumHeight(80)
        layout.addRow("Descrizione:", self.description_input)

        # Data scadenza
        self.due_date = QDateEdit()
        self.due_date.setDisplayFormat("dd/MM/yyyy")
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())
        layout.addRow("Data scadenza*:", self.due_date)

        # Proprietà (opzionale)
        self.property_combo = QComboBox()
        self.property_combo.addItem("Nessuna proprietà", None)
        if properties:
            for prop in properties:
                self.property_combo.addItem(prop["name"], prop["id"])
        layout.addRow("Proprietà:", self.property_combo)

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
            validate_date(self.due_date.date(), "Data scadenza")

            super().accept()

        except ValidationError as e:
            QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))

    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip() or None,
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "property_id": self.property_combo.currentData()
        }


# Dialog per aggiungere scadenze
class AddDeadlineDialog(QDialog):
    """Dialog per inserire una nuova scadenza"""

    def __init__(self, properties=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuova Scadenza")
        self.setMinimumSize(400, 300)

        layout = QFormLayout(self)

        # Titolo
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Es: Pagamento IMU")
        layout.addRow("Titolo*:", self.title_input)

        # Descrizione
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Dettagli aggiuntivi (opzionale)")
        self.description_input.setMaximumHeight(80)
        layout.addRow("Descrizione:", self.description_input)

        # Data scadenza
        self.due_date = QDateEdit()
        self.due_date.setDisplayFormat("dd/MM/yyyy")
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())
        layout.addRow("Data scadenza*:", self.due_date)

        # Proprietà (opzionale)
        self.property_combo = QComboBox()
        self.property_combo.addItem("Nessuna proprietà", None)
        if properties:
            for prop in properties:
                self.property_combo.addItem(prop["name"], prop["id"])
        layout.addRow("Proprietà:", self.property_combo)

        # Pulsanti
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def accept(self):
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il titolo della scadenza.")
            return
        if not self.due_date.date().isValid():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci una data valida.")
            return
        super().accept()

    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip() or None,
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "property_id": self.property_combo.currentData()
        }


class AddDocumentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aggiungi documento")
        self.setMinimumSize(400, 300)
        self.setAcceptDrops(True)

        self.selected_files = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Trascina qui i documenti oppure premi il pulsante:"))

        self.docs_list = QListWidget()
        layout.addWidget(self.docs_list)

        self.browse_btn = QPushButton("Sfoglia...")
        layout.addWidget(self.browse_btn, alignment=Qt.AlignRight)
        self.browse_btn.clicked.connect(self.browse_files)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            self.add_file(file_path)

    def browse_files(self):
        """Apre dialog per selezionare file"""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona documenti")
        for path in file_paths:
            self.add_file(path)

    def add_file(self, file_path):
        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

        filename = os.path.basename(file_path)
        dest_path = os.path.join(DOCS_DIR, filename)

        try:
            shutil.copy(file_path, dest_path)
            self.docs_list.addItem(filename)
            self.selected_files.append(dest_path)

            self.docs_list.hide()
            self.browse_btn.hide()

            meta_dialog = DocumentMetadataDialog(filename, self)
            if meta_dialog.exec():
                data = meta_dialog.get_data()
                print("Metadati salvati:", data)

            self.accept()

        except Exception as e:
            print(f"Errore copiando {filename}: {e}")


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
        self._is_dragging = False
        self._drag_pos = QPoint()

        # Aggiorna icona iniziale
        self.update_maximize_icon()

    def toggle_maximize(self):
        """Gestisce il toggle e aggiorna l'icona"""
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
        self.update_maximize_icon()

    def update_maximize_icon(self):
        """Aggiorna l'icona del pulsante in base allo stato della finestra"""
        if self.parent.isMaximized():
            self.maximize_btn.setText("❐")  # Icona "restore" (due quadrati sovrapposti)
        else:
            self.maximize_btn.setText("☐")  # Icona "maximize" (quadrato vuoto)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class ClickableDayCell(QFrame):
    """Cella giorno cliccabile per aggiungere scadenze"""

    def __init__(self, day, date_str, deadlines, parent_calendar, tm):
        super().__init__()
        self.day = day
        self.date_str = date_str
        self.deadlines = deadlines
        self.parent_calendar = parent_calendar
        self.tm = tm

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_RIGA_1}; 
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {COLORE_ITEM_HOVER};
                border: 2px solid #007BFF;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setToolTip(self.tm.get("calendar", "click_add_deadline"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # Numero del giorno
        label = QLabel(str(day))
        label.setStyleSheet("font-size: 14px; color: white; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(label)

        # Mostra scadenze
        if deadlines:
            for deadline in deadlines:
                deadline_label = QLabel(f"📌 {deadline['title']}")
                deadline_label.setStyleSheet("""
                    font-size: 10px; 
                    color: white; 
                    background-color: rgba(231, 76, 60, 0.8); 
                    padding: 2px 4px; 
                    border-radius: 3px;
                    margin-top: 2px;
                """)
                deadline_label.setWordWrap(True)
                layout.addWidget(deadline_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        """Click sulla cella = apri dialog nuova scadenza"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_calendar.add_deadline_for_date(self.date_str)
        super().mousePressEvent(event)


class PlannerCalendarWidget(QWidget):
    def __init__(self, deadline_service, property_service, tm):
        super().__init__()
        self.deadline_service = deadline_service
        self.property_service = property_service
        self.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; color: white;")
        self.tm = tm

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # intestazione mese + pulsanti
        header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size:16px;font-weight: bold;color:white")
        header.addWidget(self.month_label)
        header.addStretch()

        # Bottone per aggiungere scadenza generica
        add_deadline_btn = QPushButton(f"+ {self.tm.get("calendar", "new_deadline")}")
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
        weekdays = tm.get("weekdays", "short")
        for day in weekdays:
            day_label = QLabel(day)
            day_label.setStyleSheet("font-size: 12px; color: white; font-weight: bold;")
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weekdays_layout.addWidget(day_label)
        main_layout.addLayout(weekdays_layout)

        # griglia giorni
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        main_layout.addLayout(self.grid)

        self.current_date = QDate.currentDate()

        prev_btn.clicked.connect(self.prev_month)
        next_btn.clicked.connect(self.next_month)

        self.populate_month()

    def add_deadline(self, preset_date=None):
        """Apre dialog per aggiungere scadenza (con data opzionale preimpostata)"""
        properties = self.property_service.get_all()
        dialog = AddDeadlineDialog(self.tm, properties, self)

        # Se viene passata una data, preimpostala nel dialog
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
                property_id=data["property_id"]
            )

            if deadline_id:
                QMessageBox.information(self, self.tm.get("common", "success"), "Scadenza aggiunta correttamente!")
                self.populate_month()  # Ricarica il calendario
            else:
                QMessageBox.warning(self, self.tm.get("common", "error"), "Impossibile salvare la scadenza.")

    def add_deadline_for_date(self, date_str):
        """ Aggiunge scadenza per una data specifica (chiamato dal click sulla cella)"""
        self.add_deadline(preset_date=date_str)

    def populate_month(self):
        # pulisci celle precedenti
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        month = self.current_date.month()
        year = self.current_date.year()
        self.month_label.setText(f"{self.current_date.toString('MMMM yyyy')}")
        first_day = QDate(year, month, 1)
        start_col = first_day.dayOfWeek() - 1
        days_in_month = first_day.daysInMonth()

        row, col = 0, start_col
        for day in range(1, days_in_month + 1):
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            deadlines = self.deadline_service.get_by_date(date_str)

            # Usa la nuova cella cliccabile
            cell = ClickableDayCell(day, date_str, deadlines, self, self.tm)

            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.populate_month()

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.populate_month()


class ExportDialog(QDialog):
    """Dialog per esportare transazioni in PDF/Excel"""

    def __init__(self, transaction_service, property_service, export_service, tm, parent=None):
        super().__init__(parent)
        self.transaction_service = transaction_service
        self.property_service = property_service
        self.export_service = export_service
        self.tm = tm

        self.setWindowTitle(self.tm.get("report", "export"))
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"QDialog {{ background-color: #131b23; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Titolo
        title = QLabel(f"📥 {self.tm.get("report", "export_transactions")}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        main_layout.addWidget(title)

        # === SELEZIONE PROPRIETÀ ===
        property_group = QGroupBox(self.tm.get("common", "property"))
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

        self.property_combo.addItem(self.tm.get("common", "all_properties"), None)
        properties = self.property_service.get_all()
        for prop in properties:
            self.property_combo.addItem(f"{prop['name']}", prop['id'])

        property_layout.addWidget(self.property_combo)
        main_layout.addWidget(property_group)

        # === SELEZIONE PERIODO ===
        period_group = QGroupBox(self.tm.get("common", "period"))
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

        start_label = QLabel("Da:")
        start_label.setStyleSheet("color: white;")
        dates_layout.addWidget(start_label)

        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setStyleSheet(default_selector_date_export)
        dates_layout.addWidget(self.start_date)

        end_label = QLabel("A:")
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

        cancel_btn = QPushButton(f"❌ {self.tm.get("common", "cancel")}")
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

        export_btn = QPushButton(f"📥 {self.tm.get("report", "export")}")
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
