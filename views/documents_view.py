import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QWidget,
    QFileDialog, QDialog, QFrame
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QColor
from PySide6.QtGui import QDesktopServices

from views.base_view import BaseView
from dialogs import DocumentMetadataDialog
from styles import *

DOCS_DIR = "docs"


class DocumentsView(BaseView):
    """View per la gestione documenti"""

    def __init__(self, property_service, transaction_service, document_service, parent=None):
        self.proprieta = property_service.get_all()
        self.selected_property = self.proprieta[0] if self.proprieta else None

        # Icone
        icon_path = os.path.join(os.path.dirname(__file__), "..", "icons", "folder.png")
        self.folder_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.file_icon = QIcon("icons/file.png")
        self.open_folder_icon = QIcon("icons/folder.png")

        super().__init__(property_service, transaction_service, document_service, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia documenti"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        main_layout.addWidget(QLabel("📄 Documenti"))

        # Combo proprietà
        self.property_selector = QComboBox()
        self.property_selector.addItems([p["name"] for p in self.proprieta])
        self.property_selector.setStyleSheet(default_combo_box_style)
        if self.selected_property:
            self.property_selector.setCurrentText(self.selected_property["name"])
        self.property_selector.currentIndexChanged.connect(self.change_property)
        main_layout.addWidget(self.property_selector)

        # Lista documenti
        self.docs_list = QListWidget()
        self.docs_list.setStyleSheet(f"""
            QListWidget::item:hover {{
                background: {COLORE_ITEM_HOVER};   
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                background: #007BFF;
                color: white;
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(self.docs_list)
        self.load_documents()

        # Bottone aggiungi
        add_doc_btn = QPushButton("+")
        add_doc_btn.setFixedSize(40, 40)
        add_doc_btn.setStyleSheet(
            "background-color: #007BFF; color: white; font-size: 18px; font-weight: bold; border-radius: 20px;"
        )
        add_doc_btn.clicked.connect(self.add_document)
        main_layout.addWidget(add_doc_btn, alignment=Qt.AlignRight)

    def change_property(self, index):
        """Cambia proprietà selezionata"""
        if index >= 0 and index < len(self.proprieta):
            self.selected_property = self.proprieta[index]
            self.load_documents()

    def load_documents(self, sub_directory=None):
        """Carica i documenti della proprietà"""
        self.docs_list.clear()
        if not self.selected_property:
            return

        # ⭐ USA IL SERVICE
        documents = self.document_service.list_documents(
            self.selected_property["name"],
            sub_directory
        )

        # Aggiungi navigazione indietro se in sottocartella
        if sub_directory:
            documents.insert(0, {"name": "...", "path": "", "is_folder": True})

        for idx, doc in enumerate(documents):
            bg_color = QColor(COLORE_RIGA_2 if idx % 2 == 0 else COLORE_RIGA_1)

            row_widget = QWidget()
            layout = QHBoxLayout(row_widget)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(10)

            label = QLabel(doc["name"])
            label.setStyleSheet("color: white; font-size: 14px;")
            layout.addWidget(label, stretch=1)

            if doc["is_folder"]:
                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")

                if doc["name"] == "...":
                    # Torna indietro
                    if sub_directory:
                        parts = sub_directory.split("\\")
                        parts.pop()
                        new_path = "\\".join(parts) if parts else None
                    else:
                        new_path = None
                else:
                    # Vai avanti
                    new_path = f"{sub_directory}\\{doc['name']}" if sub_directory else doc["name"]

                open_btn.clicked.connect(lambda _, sub_dir=new_path: self.load_documents(sub_dir))
                layout.addWidget(open_btn)
            else:
                # File buttons (preview e open location)
                preview_btn = QPushButton()
                preview_btn.setIcon(self.file_icon)
                preview_btn.setIconSize(QSize(18, 18))
                preview_btn.setFixedSize(28, 28)
                preview_btn.setStyleSheet("border: none;")
                preview_btn.clicked.connect(lambda _, path=doc["path"]: self.preview_file(path))
                layout.addWidget(preview_btn)

                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")
                open_btn.clicked.connect(lambda _, path=doc["path"]: self.open_file_location(path))
                layout.addWidget(open_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 35))
            self.docs_list.addItem(item)
            self.docs_list.setItemWidget(item, row_widget)
            row_widget.setStyleSheet(f"background-color: {bg_color.name()};border-radius: 5px;")

    def add_document(self):
        """Aggiunge nuovi documenti"""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec() != QDialog.Accepted:
            return

        selected_files = dialog.selectedFiles()

        for path in selected_files:
            filename = os.path.basename(path)
            meta_dialog = DocumentMetadataDialog(filename, self)
            if meta_dialog.exec() != QDialog.Accepted:
                continue

            metadata = meta_dialog.get_data()

            # ⭐ USA IL SERVICE per salvare transazione
            trans_id = self.transaction_service.create(
                property_id=self.selected_property["id"],
                date=metadata["data_fattura"],
                trans_type=metadata["tipo"],
                amount=float(metadata["importo"]),
                provider=metadata['provider'],
                service=metadata['service']
            )

            if trans_id:
                # USA IL SERVICE per salvare documento
                dest_path = self.document_service.save_document(
                    path,
                    self.selected_property["name"],
                    metadata=metadata
                )

                if dest_path:
                    print(f"✅ Documento salvato: {dest_path}")

        self.load_documents()


    def preview_file(self, path):
        """Preview file (da implementare)"""
        print("Preview:", path)

    def open_file_location(self, path):
        """Apre la cartella contenente il file"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))