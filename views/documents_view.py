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

    def __init__(self, conn, proprieta, parent=None):
        self.proprieta = proprieta
        self.selected_property = proprieta[0] if proprieta else None

        # Icone
        icon_path = os.path.join(os.path.dirname(__file__), "..", "icons", "folder.png")
        self.folder_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.file_icon = QIcon("icons/file.png")
        self.open_folder_icon = QIcon("icons/open-folder-with-document.png")

        super().__init__(conn, parent)

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

        prop_folder = os.path.join(DOCS_DIR, self.selected_property["name"], sub_directory if sub_directory else "")
        if not os.path.exists(prop_folder):
            os.makedirs(prop_folder)

        files = os.listdir(prop_folder)
        files.sort()

        folders = [f for f in files if os.path.isdir(os.path.join(prop_folder, f))]
        if sub_directory:
            folders.insert(0, "")
        regular_files = [f for f in files if not os.path.isdir(os.path.join(prop_folder, f))]
        ordered_files = folders + regular_files

        for idx_f, f in enumerate(ordered_files):
            file_path = os.path.join(prop_folder, f)
            bg_color = QColor(COLORE_RIGA_2 if idx_f % 2 == 0 else COLORE_RIGA_1)

            row_widget = QWidget()
            layout = QHBoxLayout(row_widget)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(10)

            label = QLabel(f if f != "" else "...")
            label.setStyleSheet("color: white; font-size: 14px;")
            layout.addWidget(label, stretch=1)

            if os.path.isdir(file_path):
                icon_label = QLabel()
                icon_label.setPixmap(self.folder_icon.pixmap(20, 20))
                layout.insertWidget(0, icon_label)

                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")

                if f:
                    new_path = f"{sub_directory}\\{f}" if sub_directory else f
                else:
                    if sub_directory:
                        parts = sub_directory.split("\\")
                        parts.pop()
                        new_path = "\\".join(parts)
                    else:
                        new_path = ""

                open_btn.clicked.connect(lambda _, sub_dir=new_path: self.load_documents(sub_dir))
                layout.addWidget(open_btn)
            else:
                preview_btn = QPushButton()
                preview_btn.setIcon(self.file_icon)
                preview_btn.setIconSize(QSize(18, 18))
                preview_btn.setFixedSize(28, 28)
                preview_btn.setStyleSheet("border: none;")
                preview_btn.clicked.connect(lambda _, path=file_path: self.preview_file(path))
                layout.addWidget(preview_btn)

                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")
                open_btn.clicked.connect(lambda _, path=file_path: self.open_file_location(path))
                layout.addWidget(open_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 35))
            self.docs_list.addItem(item)
            self.docs_list.setItemWidget(item, row_widget)
            row_widget.setStyleSheet(f"background-color: {bg_color.name()};border-radius: 5px;")

    def preview_file(self, path):
        """Preview file (da implementare)"""
        print("Preview:", path)

    def open_file_location(self, path):
        """Apre la cartella contenente il file"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))

    def add_document(self):
        """Aggiunge nuovi documenti"""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec() != QDialog.Accepted:
            return

        selected_files = dialog.selectedFiles()
        prop_folder = os.path.join(DOCS_DIR, self.selected_property["name"])
        os.makedirs(prop_folder, exist_ok=True)

        for path in selected_files:
            filename = os.path.basename(path)
            meta_dialog = DocumentMetadataDialog(filename, self)
            if meta_dialog.exec() != QDialog.Accepted:
                continue

            metadata = meta_dialog.get_data()

            try:
                self.cursor.execute("""
                    INSERT INTO transactions (property_id, date, type, amount, provider, service)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.selected_property["id"],
                    metadata["data_fattura"],
                    metadata["tipo"],
                    float(metadata["importo"]),
                    metadata['provider'],
                    metadata['service']
                ))
                self.conn.commit()
            except Exception as e:
                print("Errore inserendo transazione:", e)

            dest_path = os.path.join(prop_folder, filename)
            try:
                with open(path, "rb") as src_file, open(dest_path, "wb") as dst_file:
                    dst_file.write(src_file.read())
            except Exception as e:
                print(f"Errore copiando {filename}: {e}")

        self.load_documents()