# dialogs.py
import os
import shutil

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFileDialog, QListWidget, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QDateEdit, QWidget, QHBoxLayout, QSizePolicy, QCalendarWidget, QListWidgetItem,
    QInputDialog, QGridLayout, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, QDate, QPoint, QSize
from styles import custom_title_style, COLORE_SECONDARIO, COLORE_WIDGET_2, COLORE_BIANCO, COLORE_RIGA_1

DOCS_DIR = "docs"


class DocumentMetadataDialog(QDialog):
    """Dialog per inserire i metadati del documento"""

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
        layout.addRow("Fornitore/Emittente:", self.emittente_input)

        # servizio
        self.service_input = QLineEdit()
        layout.addRow("Servizio:", self.service_input)

        # Importo
        self.importo_input = QLineEdit()
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
        if not self.type_box.currentText().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Seleziona il tipo.")
            return
        if not self.emittente_input.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci l'emittente.")
            return
        if not self.service_input.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci il servizio.")
            return
        if not self.importo_input.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci l'importo.")
            return
        if not self.data_fattura.date().isValid():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci una data valida.")
            return

        super().accept()

    def get_data(self):
        return {
            "tipo": self.type_box.currentText(),
            "provider": self.emittente_input.text().strip(),
            "service": self.service_input.text().strip(),
            "importo": self.importo_input.text().strip(),
            "data_fattura": self.data_fattura.date().toString("dd/MM/yyyy"),
        }


# 🆕 Dialog per aggiungere scadenze
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

        minimize_btn = QPushButton("-")
        minimize_btn.setFixedSize(25, 25)
        minimize_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            color: white !important;
            font-weight: bold;
            font-size: 20px;
        }
        QPushButton:hover {
            background-color: #e74c3c;
        }
        """)
        minimize_btn.clicked.connect(parent.showMinimized)
        title_layout.addWidget(minimize_btn)

        maximize_btn = QPushButton("□")
        maximize_btn.setFixedSize(25, 25)
        maximize_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            color: white !important;
            font-weight: bold;
            font-size: 26px;
        }
        QPushButton:hover {
            background-color: #e74c3c;
        }
        """)
        maximize_btn.clicked.connect(parent.toggle_max_restore)
        title_layout.addWidget(maximize_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet("""
        QPushButton {
            background-color: red;
            border: none;
            border-radius: 4px;
            color: white !important;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #e74c3c;
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


class PlannerCalendarWidget(QWidget):
    def __init__(self, deadline_service, property_service):
        super().__init__()
        self.deadline_service = deadline_service
        self.property_service = property_service
        self.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; color: white;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # intestazione mese + pulsanti
        header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size:16px;font-weight: bold;color:white")
        header.addWidget(self.month_label)
        header.addStretch()

        # 🆕 Bottone per aggiungere scadenza
        add_deadline_btn = QPushButton("+ Nuova Scadenza")
        add_deadline_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        add_deadline_btn.clicked.connect(self.add_deadline)
        header.addWidget(add_deadline_btn)

        prev_btn = QPushButton()
        prev_btn.setIcon(QIcon("./icons/left-arrow.png"))
        next_btn = QPushButton()
        next_btn.setIcon(QIcon("./icons/right-arrow.png"))
        header.addWidget(prev_btn)
        header.addWidget(next_btn)
        main_layout.addLayout(header)

        # griglia giorni
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        main_layout.addLayout(self.grid)

        self.current_date = QDate.currentDate()

        prev_btn.clicked.connect(self.prev_month)
        next_btn.clicked.connect(self.next_month)

        self.populate_month()

    def add_deadline(self):
        """Apre dialog per aggiungere scadenza"""
        properties = self.property_service.get_all()
        dialog = AddDeadlineDialog(properties, self)

        if dialog.exec():
            data = dialog.get_data()
            deadline_id = self.deadline_service.create(
                title=data["title"],
                description=data["description"],
                due_date=data["due_date"],
                property_id=data["property_id"]
            )

            if deadline_id:
                QMessageBox.information(self, "Successo", "Scadenza aggiunta correttamente!")
                self.populate_month()  # Ricarica il calendario
            else:
                QMessageBox.warning(self, "Errore", "Impossibile salvare la scadenza.")

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
            cell = self.create_day_cell(day, date_str)
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def create_day_cell(self, day, date_str):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {COLORE_RIGA_1}; border-radius: 6px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)

        label = QLabel(str(day))
        label.setStyleSheet("font-size: 14px; color: white; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(label)

        # 🆕 Mostra scadenze per questa data
        deadlines = self.deadline_service.get_by_date(date_str)

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
        else:
            # Spazio vuoto per mantenere dimensioni uniformi
            spacer = QLabel("")
            spacer.setFixedHeight(20)
            layout.addWidget(spacer)

        return frame

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.populate_month()

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.populate_month()