import sys
import os

from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QListWidget, QComboBox, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QFileDialog, QListWidgetItem
)
from PySide6.QtCore import Qt, QSize
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from dialogs import *
from datetime import datetime, timedelta

import Functions
from styles import *

DOCS_DIR = "docs"  # cartella dove conservi i documenti
#FOLDER_ICON = QIcon('icons/folder.png')

class DashboardWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.cursor = conn.cursor()
        self.cursor_read_only = conn.cursor()
        # inizializza icona cartella (dopo QApplication)
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "folder.png")
        if os.path.exists(icon_path):
            self.folder_icon = QIcon(icon_path)
        else:
            self.folder_icon = QIcon.fromTheme("folder")
            if self.folder_icon.isNull():
                self.folder_icon = QIcon()  # fallback vuoto

        self.proprieta = Functions.get_dati_proprieta()
        self.selected_property = self.proprieta[0] if self.proprieta else None

        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

        self.setWindowTitle("Property Manager MVP")
        self.setGeometry(200, 200, 1000, 600)

        main_layout = QHBoxLayout()
        menu = QListWidget()
        menu.addItems(["🏠 Dashboard", "Le mie proprietà", "📄 Documenti", "💶 Contabilità", "📊 Report", "⚙️ Impostazioni"])
        menu.setMaximumWidth(150)
        menu.setStyleSheet("""
            QListWidget { color: white; background-color: #222; }
            QListWidget::item { padding: 10px 10px 10px 20px; font-size: 16px; }
            QListWidget::item:selected { background: #444; color: #00BFFF; }
        """)
        main_layout.addWidget(menu)
        menu.currentRowChanged.connect(self.menu_navigation)

        container = QWidget()
        container.setLayout(main_layout)
        container.setStyleSheet(f"background-color: {COLORE_BACKGROUND};")
        self.setCentralWidget(container)

        self.show_dashboard_ui()

    # ===================== DASHBOARD UI =====================
    def show_dashboard_ui(self):
        central_layout = self.centralWidget().layout()
        while central_layout.count() > 1:
            item = central_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        center_layout = QVBoxLayout()
        top_layout = QHBoxLayout()

        # Selettore proprietà
        self.property_selector = QComboBox()
        self.property_selector.addItems([p["name"] for p in self.proprieta])
        self.property_selector.setStyleSheet(default_combo_box_style)

        add_button = QPushButton("+")
        add_button.setFixedSize(30, self.property_selector.sizeHint().height())
        add_button.setStyleSheet("background-color: #007BFF; color: white; font-weight: bold; font-size: 16px; border-radius: 5px;")
        add_button.setToolTip("Aggiungi nuova proprietà")

        # Info box
        self.info_layout = QVBoxLayout()
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 10px; padding: 5px; color:black;")
        if self.proprieta:
            primo = self.proprieta[0]
            self.info_layout.addWidget(QLabel(f"🏡 Proprietà: {primo['name']}"))
            self.info_layout.addWidget(QLabel(f"📍 Indirizzo: {primo['address']}"))
            self.info_layout.addWidget(QLabel(f"👤 Proprietario: {primo['owner']}"))
        else:
            self.info_layout.addWidget(QLabel("🏡 Nessuna proprietà"))
            self.info_layout.addWidget(QLabel(""))
            self.info_layout.addWidget(QLabel(""))
        info_frame.setLayout(self.info_layout)

        wrapper_layout = QVBoxLayout()
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(self.property_selector, stretch=3)
        selector_layout.addWidget(add_button, stretch=1)
        wrapper_layout.addLayout(selector_layout)
        wrapper_layout.addWidget(info_frame, stretch=5)

        info_container = QFrame()
        info_container.setLayout(wrapper_layout)
        top_layout.addWidget(info_container, alignment=Qt.AlignTop)

        # --- Creazione frame grafico ---
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        chart_layout = QVBoxLayout()
        # --- ComboBox per intervallo ---
        self.period_selector = QComboBox()
        self.period_selector.setStyleSheet(default_combo_box_style)
        # todo: si potrebbe pensare di farlo dinamico
        self.period_selector.addItems(["1 mese", "6 mesi", "1 anno", "3 anni"])
        self.period_selector.currentIndexChanged.connect(self.update_chart)  # ridisegna al cambio
        chart_layout.addWidget(self.period_selector)

        # --- Canvas Matplotlib ---
        self.fig = Figure(figsize=(4, 4), facecolor=COLORE_WIDGET_2)
        self.chart_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)
        chart_layout.addWidget(self.chart_canvas)

        chart_frame.setLayout(chart_layout)
        top_layout.addWidget(chart_frame)

        # --- Richiamo iniziale per caricare subito il grafico ---
        self.update_chart()

        center_layout.addLayout(top_layout)

        # Placeholder inferiore
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 10px;")
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(QLabel("📄 Documenti recenti o report trimestrali (placeholder)"))
        bottom_frame.setLayout(bottom_layout)
        bottom_frame.setFixedHeight(150)
        center_layout.addWidget(bottom_frame)

        container = QFrame()
        container.setLayout(center_layout)
        central_layout.addWidget(container)

        # Segnali
        self.property_selector.currentIndexChanged.connect(self.update_info_box)
        add_button.clicked.connect(self.add_property)

    # --- Funzione per aggiornare il grafico ---
    def update_chart(self):
        text = self.period_selector.currentText()
        mesi = {"1 mese": 1, "6 mesi": 6, "1 anno": 12, "3 anni": 36}[text]
        end_date = datetime.today()
        start_date = end_date - timedelta(days=30 * mesi)

        # recupero dati dal DB
        rows = Functions.get_transactions(
            self.cursor_read_only,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            self.selected_property["id"]
        )

        entrate = sum(row[2] for row in rows if row[1] == "Entrata")
        uscite = sum(row[2] for row in rows if row[1] == "Uscita")

        # pulisco e ridisegno grafico
        self.ax.clear()
        sizes, colors = [entrate, uscite], ["green", "red"]
        self.ax.pie(sizes, colors=colors, autopct='%1.1f%%', pctdistance=1.25, startangle=90, wedgeprops=dict(width=0.4))
        centre_circle = Circle((0, 0), 0.70, fc=COLORE_WIDGET_2)
        self.ax.add_artist(centre_circle)
        self.ax.text(0, 0, f"€ {entrate - uscite}", horizontalalignment='center', verticalalignment='center',
                     fontsize=16, fontweight='bold', color='black')
        self.ax.set_title("Entrate vs Uscite", color="black", y=1.1)
        self.chart_canvas.draw()

    def update_info_box(self, index):
        if index < 0 or index >= len(self.proprieta):
            return
        prop = self.proprieta[index]
        self.selected_property = prop
        self.info_layout.itemAt(0).widget().setText(f"🏡 Proprietà: {prop['name']}")
        self.info_layout.itemAt(1).widget().setText(f"📍 Indirizzo: {prop['address']}")
        self.info_layout.itemAt(2).widget().setText(f"👤 Proprietario: {prop['owner']}")
        self.update_chart()

    def add_property(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuova proprietà")
        layout = QFormLayout(dialog)
        name_input, address_input, owner_input = QLineEdit(), QLineEdit(), QLineEdit()
        layout.addRow("Nome:", name_input)
        layout.addRow("Indirizzo:", address_input)
        layout.addRow("Proprietario:", owner_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec():
            nome, indirizzo, proprietario = name_input.text().strip(), address_input.text().strip(), owner_input.text().strip()
            if nome and indirizzo and proprietario:
                try:
                    self.cursor.execute("INSERT INTO properties (name, address, owner) VALUES (?, ?, ?)",
                                        (nome, indirizzo, proprietario))
                    self.conn.commit()
                except Exception as e:
                    print("Errore nell'inserimento:", e)
                    return
                self.proprieta = Functions.get_dati_proprieta()
                self.property_selector.clear()
                self.property_selector.addItems([p["name"] for p in self.proprieta])
                self.property_selector.setCurrentIndex(len(self.proprieta) - 1)
                self.update_chart()

    # ===================== NAVIGATION =====================
    def menu_navigation(self, index):
        voce = self.sender().item(index).text()
        if "Documenti" in voce:
            self.show_documents_ui()
        elif "🏠 Dashboard" in voce:
            self.show_dashboard_ui()

    # ===================== DOCUMENTS UI =====================
    def show_documents_ui(self):
        central_layout = self.centralWidget().layout()
        while central_layout.count() > 1:
            item = central_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        docs_layout = QVBoxLayout()
        docs_layout.addWidget(QLabel("📄 Documenti"))

        # Combo per selezionare la proprietà
        self.docs_property_selector = QComboBox()
        self.docs_property_selector.addItems([p["name"] for p in self.proprieta])
        if self.selected_property:
            self.docs_property_selector.setCurrentText(self.selected_property["name"])
        docs_layout.addWidget(self.docs_property_selector)
        self.docs_property_selector.currentIndexChanged.connect(self.change_property_docs)

        # Lista documenti
        self.docs_list = QListWidget()
        self.docs_list.setStyleSheet("""
             QListWidget::item:hover {
            background: #539fec;   
            border-radius: 8px;
        }
             QListWidget::item:selected {
            background: #007BFF;
            color: white;
            border-radius: 8px;
        }
        """)
        docs_layout.addWidget(self.docs_list)
        self.load_documents()

        # Bottone aggiungi
        add_doc_btn = QPushButton("+")
        add_doc_btn.setFixedSize(40, 40)
        add_doc_btn.setStyleSheet("background-color: #007BFF; color: white; font-size: 18px; font-weight: bold; border-radius: 20px;")
        docs_layout.addWidget(add_doc_btn, alignment=Qt.AlignRight)
        add_doc_btn.clicked.connect(self.add_document)

        container = QFrame()
        container.setLayout(docs_layout)
        central_layout.addWidget(container)

    def change_property_docs(self, index):
        prop = self.proprieta[index]
        self.selected_property = prop
        self.load_documents()

    def load_documents(self):
        self.docs_list.clear()
        if not self.selected_property:
            return
        prop_folder = os.path.join(DOCS_DIR, self.selected_property["name"])
        if not os.path.exists(prop_folder):
            os.makedirs(prop_folder)
        files = os.listdir(prop_folder)
        files.sort()

        # separa cartelle e file
        folders = [f for f in files if os.path.isdir(os.path.join(prop_folder, f))]
        regular_files = [f for f in files if not os.path.isdir(os.path.join(prop_folder, f))]
        ordered_files = folders + regular_files

        for idx_f, f in enumerate(ordered_files):
            file_path = os.path.join(prop_folder, f)
            item = QListWidgetItem(f)
            item.setSizeHint(QSize(100, 35))
            item.setForeground(QColor("black"))
            item.setBackground(QColor(COLORE_RIGA_2 if idx_f % 2 == 0 else COLORE_RIGA_1))

            if os.path.isdir(file_path):
                item.setIcon(self.folder_icon)  # icona cartella

            self.docs_list.addItem(item)

    def add_document(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec() != QDialog.Accepted:
            return

        selected_files = dialog.selectedFiles()
        prop_folder = os.path.join(DOCS_DIR, self.selected_property["name"])
        os.makedirs(prop_folder, exist_ok=True)

        for path in selected_files:
            # apro il dialog dei metadati PASSANDO il nome del file (non self)
            filename = os.path.basename(path)
            meta_dialog = DocumentMetadataDialog(filename, self)
            if meta_dialog.exec() != QDialog.Accepted:
                continue  # se l'utente annulla, salta questo file

            # usa il metodo corretto per leggere i metadati (get_data)
            metadata = meta_dialog.get_data()

            try:
                self.cursor.execute("""
                    INSERT INTO transactions (property_id, date, type, amount, provider)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.selected_property["id"],
                    metadata["data_fattura"],
                    metadata["tipo"],
                    float(metadata["importo"]),
                    metadata['provider']
                ))
                self.conn.commit()
            except Exception as e:
                print("Errore inserendo transazione nel DB:", e)
            else:
                print(f"Dati inseriti correttamnete id={self.selected_property["id"]},data={metadata["data_fattura"]},tipo={metadata["tipo"]},importo={float(metadata["importo"])},fornitore={metadata['provider']}")

            # copia file nella cartella della proprietà solo DOPO aver ottenuto i metadati
            dest_path = os.path.join(prop_folder, filename)
            try:
                with open(path, "rb") as src_file, open(dest_path, "wb") as dst_file:
                    dst_file.write(src_file.read())
            except Exception as e:
                print(f"Errore copiando {filename}: {e}")

            # opzionale: salva i metadati nel DB (se vuoi)
            # self.cursor.execute("INSERT INTO documents (name, tipo, emittente, importo, property_id) VALUES (?, ?, ?, ?, ?)",
            #                     (filename, metadata['tipo'], metadata['emittente'], metadata['importo'], self.selected_property['id']))
            # self.conn.commit()

        self.load_documents()
