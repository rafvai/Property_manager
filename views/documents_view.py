import os

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QWidget,
    QFileDialog, QDialog, QMessageBox
)

from dialogs import DocumentMetadataDialog
from styles import *
from views.base_view import BaseView
from translations_manager import get_translation_manager

DOCS_DIR = "docs"


class DocumentsView(BaseView):
    """View per la gestione documenti"""

    def __init__(self, property_service, transaction_service, document_service, logger, parent=None):
        self.proprieta = property_service.get_all()
        self.selected_property = self.proprieta[0] if self.proprieta else None
        self.tm = get_translation_manager()
        self.logger = logger
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

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("documents", "title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Bottone aggiungi spostato qui
        add_doc_btn = QPushButton(f"+ {self.tm.get("documents", "add_document")}")
        add_doc_btn.setStyleSheet(default_aggiungi_button)
        add_doc_btn.setFixedHeight(36)
        add_doc_btn.clicked.connect(self.add_document)
        header_layout.addWidget(add_doc_btn)

        main_layout.addLayout(header_layout)

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

    def change_property(self, index):
        """Cambia proprietà selezionata"""
        if index >= 0 and index < len(self.proprieta):
            self.selected_property = self.proprieta[index]
            self.load_documents()

    def load_documents(self, sub_directory=None):
        """Carica i documenti della proprietà usando l'ID"""
        self.docs_list.clear()
        if not self.selected_property:
            return

        documents = self.document_service.list_documents(
            self.selected_property["id"],
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
                # Bottone per aprire la cartella
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
                # Bottone per APRIRE il file
                open_file_btn = QPushButton()
                open_file_btn.setIcon(self.file_icon)
                open_file_btn.setIconSize(QSize(18, 18))
                open_file_btn.setFixedSize(28, 28)
                open_file_btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #3498db;
                        border-radius: 4px;
                    }
                """)
                open_file_btn.setToolTip("Apri documento")
                open_file_btn.clicked.connect(lambda _, path=doc["path"]: self.open_file(path))
                layout.addWidget(open_file_btn)

                # Bottone per aprire la CARTELLA contenente il file
                open_folder_btn = QPushButton()
                open_folder_btn.setIcon(self.open_folder_icon)
                open_folder_btn.setIconSize(QSize(18, 18))
                open_folder_btn.setFixedSize(28, 28)
                open_folder_btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #f39c12;
                        border-radius: 4px;
                    }
                """)
                open_folder_btn.setToolTip("Apri cartella")
                open_folder_btn.clicked.connect(lambda _, path=doc["path"]: self.open_file_location(path))
                layout.addWidget(open_folder_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 35))
            self.docs_list.addItem(item)
            self.docs_list.setItemWidget(item, row_widget)
            row_widget.setStyleSheet(f"background-color: {bg_color.name()};border-radius: 5px;")

    def add_document(self):
        """Aggiunge nuovi documenti CON VALIDAZIONE"""
        from validation_utils import parse_decimal, ValidationError

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

            try:
                # converti importo
                importo_float = parse_decimal(metadata["importo"], "Importo")

                # Salva transazione
                trans_id = self.transaction_service.create(
                    property_id=self.selected_property["id"],
                    date=metadata["data_fattura"],
                    trans_type=metadata["tipo"],
                    amount=importo_float,
                    provider=metadata['provider'],
                    service=metadata['service']
                )

                if trans_id:
                    dest_path = self.document_service.save_document(
                        path,
                        self.selected_property["id"],
                        metadata=metadata
                    )

                    if dest_path:
                        self.logger.info(f"Documento salvato: {dest_path}")
                        QMessageBox.information(
                            self,
                            "✅ Successo",
                            f"Documento salvato correttamente!\n\n"
                            f"📄 {os.path.basename(dest_path)}\n"
                            f"💰 {importo_float:,.2f}€"
                        )
                else:
                    self.logger.error(f"Impossibile salvare la transazione nel database")
                    QMessageBox.warning(
                        self,
                        f"⚠️ {self.tm.get("common", "error")}",
                        "Impossibile salvare la transazione nel database"
                    )

            except ValidationError as e:
                self.logger.exception(f"Errore nell'importo del documento '{filename} {str(e)}")
                QMessageBox.warning(
                    self,
                    "⚠️ Validazione fallita",
                    f"Errore nell'importo del documento '{filename}':\n\n{str(e)}"
                )
                continue
            except Exception as e:
                self.logger.exception(f"Errore durante il salvataggio {str(e)}")
                QMessageBox.critical(
                    self,
                    f"❌ {self.tm.get("common", "error")}",
                    f"Errore durante il salvataggio:\n\n{str(e)}"
                )
                continue

        self.load_documents()

    def open_file(self, path):
        """ Apre il file con l'applicazione predefinita del sistema"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            self.logger.info(f"Apertura file: {path}")
        except Exception as e:
            self.logger.exception(f"Errore apertura file: {str(e)}")

    def open_file_location(self, path):
        """Apre la cartella contenente il file"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            self.logger.info(f"Apertura cartella: {os.path.dirname(path)}")
        except Exception as e:
            self.logger.exception(f"Errore apertura cartella: {str(e)}")