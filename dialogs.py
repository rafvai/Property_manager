# dialogs.py
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFileDialog, QListWidget, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate

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

        # Importo
        self.importo_input = QLineEdit()
        layout.addRow("Importo totale (€):", self.importo_input)

        # Data Fattura
        self.data_fattura = QDateEdit()
        self.data_fattura.setDisplayFormat("dd/MM/yyyy")  # formato visivo
        self.data_fattura.setCalendarPopup(True)  # apre calendario
        self.data_fattura.setDate(QDate.currentDate())  # default oggi
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
        if not self.importo_input.text().strip():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci l'importo.")
            return
        if not self.data_fattura.date().isValid():
            QMessageBox.warning(self, "Campo obbligatorio", "Inserisci una data valida.")
            return

        super().accept()

        super().accept()
    def get_data(self):
        return {
            "tipo": self.type_box.currentText(),
            "provider": self.emittente_input.text().strip(),
            "importo": self.importo_input.text().strip(),
            "data_fattura": self.data_fattura.date().toString("dd/MM/yyyy"),
        }


class AddDocumentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aggiungi documento")
        self.setMinimumSize(400, 300)
        self.setAcceptDrops(True)

        self.selected_files = []  # memorizza i file aggiunti

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Trascina qui i documenti oppure premi il pulsante:"))

        self.docs_list = QListWidget()
        layout.addWidget(self.docs_list)

        self.browse_btn = QPushButton("Sfoglia...")
        layout.addWidget(self.browse_btn, alignment=Qt.AlignRight)
        self.browse_btn.clicked.connect(self.browse_files)  # <--- errore veniva da qui

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

            # nascondo i widget drag/browse
            self.docs_list.hide()
            self.browse_btn.hide()

            # apro dialog metadati
            meta_dialog = DocumentMetadataDialog(filename, self)
            if meta_dialog.exec():
                data = meta_dialog.get_data()
                print("Metadati salvati:", data)

            self.accept()  # chiudo il dialog principale

        except Exception as e:
            print(f"Errore copiando {filename}: {e}")
