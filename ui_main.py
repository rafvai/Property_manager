import sys
import os

from PySide6.QtGui import QColor, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QListWidget, QComboBox, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QFileDialog, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QUrl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
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

        # icona cartella
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "folder.png")
        if os.path.exists(icon_path):
            self.folder_icon = QIcon(icon_path)
        else:
            self.folder_icon = QIcon.fromTheme("folder") or QIcon()
        # icona file
        self.file_icon = QIcon("icons/file.png")
        # icona open folder
        self.open_folder_icon = QIcon("icons/open-folder-with-document.png")

        self.proprieta = Functions.get_dati_proprieta()
        self.selected_property = self.proprieta[0] if self.proprieta else None

        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

        # finestra principale
        self.setWindowTitle("Property Manager MVP")
        self.setGeometry(200, 200, 1000, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # --- WIDGET CONTAINER PRINCIPALE ---
        container = QWidget()
        self.setCentralWidget(container)

        # layout verticale principale
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # --- CUSTOM TITLE BAR ---
        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)

        # --- BODY: menu + contenuti ---
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Menu laterale
        self.menu = QListWidget()
        menu_items = [
            ("icons/homepage.png", "Dashboard"),
            ("icons/property.png", "Le mie proprietà"),
            ("icons/document.png", "Documenti"),
            ("icons/bar-chart.png", "Contabilità"),
            ("icons/pie-chart.png", "Report"),
            ("icons/settings.png", "Impostazioni"),
        ]
        for icon_path, text in menu_items:
            item = QListWidgetItem(QIcon(icon_path), text)
            self.menu.addItem(item)

        self.menu.setFixedWidth(int(self.width() * W_LAT_MENU))
        self.menu.setMinimumWidth(100)
        self.menu.setStyleSheet(default_menu_lat_style)
        self.menu.setFocusPolicy(Qt.NoFocus)
        self.menu.currentRowChanged.connect(self.menu_navigation)
        self.menu.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Area contenuti
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_area.setLayout(QVBoxLayout())  # layout iniziale

        # aggiungi al layout orizzontale
        body_layout.addWidget(self.menu)
        body_layout.addWidget(self.content_area)

        # aggiungi body sotto la title bar
        container_layout.addWidget(body_widget)

        # stile generale
        container.setStyleSheet(f"background-color: {COLORE_BACKGROUND};")

        # mostra la dashboard di default
        self.show_dashboard_ui()
    # ===================== DASHBOARD UI =====================
    def show_dashboard_ui(self):
        # pulisci solo l'area contenuti
        layout = self.content_area.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # --- Layout principale del contenuto (verticale) ---
        main_content = QVBoxLayout()
        main_content.setContentsMargins(30, 30, 30, 30)
        main_content.setSpacing(25)

        # ========== HEADER ========== #
        header_main_layout = QVBoxLayout()
        header_main_layout.setContentsMargins(0, 0, 0, 0)
        header_main_layout.setSpacing(6)

        # --- Riga 1: Selezione proprietà + bottone aggiungi ---
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        top_widget_seleziona_proprietà = QWidget()
        layout_prop = QVBoxLayout()
        layout_prop.setContentsMargins(0, 0, 0, 0)
        layout_prop.addWidget(QLabel("Seleziona proprietà:"))

        self.property_selector = QComboBox()
        self.property_selector.addItems([p["name"] for p in self.proprieta])
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        if self.selected_property:
            self.property_selector.setCurrentText(self.selected_property["name"])
        layout_prop.addWidget(self.property_selector)
        top_widget_seleziona_proprietà.setLayout(layout_prop)

        top_row.addWidget(top_widget_seleziona_proprietà, stretch=3)
        top_row.addSpacing(200)

        add_button = QPushButton("+ Aggiungi")
        add_button.setFixedHeight(36)
        add_button.setStyleSheet(default_aggiungi_button)

        top_row.addStretch()
        top_row.addWidget(add_button, stretch=0)

        # --- Riga 2: "Proprietà" e "Periodo" ---
        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)

        label_proprieta = QLabel("Proprietà")
        label_proprieta.setStyleSheet("font-weight: 650; font-size: 20px; color: white;")
        mid_row.addWidget(label_proprieta)
        mid_row.addStretch()

        label_periodo = QLabel("Periodo:")
        label_periodo.setStyleSheet("color: white;")
        mid_row.addWidget(label_periodo)

        self.period_selector = QComboBox()
        self.period_selector.setStyleSheet(default_combo_box_style)
        self.period_selector.addItems(["1 mese", "6 mesi", "1 anno", "3 anni"])
        self.period_selector.currentIndexChanged.connect(self.update_chart)
        mid_row.addWidget(self.period_selector)

        header_main_layout.addLayout(top_row)
        header_main_layout.addLayout(mid_row)

        main_content.addLayout(header_main_layout)

        # ========== SEZIONE CENTRALE ========== #
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(25)

        # --- Info proprietà ---
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 12px; padding: 20px;")
        self.info_layout = QVBoxLayout(info_frame)
        self.info_layout.setSpacing(5)
        self.info_name = QLabel()
        self.info_address = QLabel()
        self.info_owner = QLabel()

        if self.proprieta:
            p = self.proprieta[0]
            self.info_name.setText(f"🏡 {p['name']}")
            self.info_address.setText(f"📍 {p['address']}")
            self.info_owner.setText(f"👤 {p['owner']}")
        else:
            self.info_name.setText("Nessuna proprietà registrata.")
            self.info_address.setText("")
            self.info_owner.setText("")

        self.info_layout.addWidget(self.info_name)
        self.info_layout.addWidget(self.info_address)
        self.info_layout.addWidget(self.info_owner)

        # --- Grafico Donut ---
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 12px; padding: 20px;")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setSpacing(10)

        self.fig = Figure(figsize=(4, 4), facecolor=COLORE_WIDGET_2)
        self.chart_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)
        chart_layout.addWidget(self.chart_canvas)
        self.update_chart()

        middle_layout.addWidget(info_frame, 2)
        middle_layout.addWidget(chart_frame, 3)

        main_content.addLayout(middle_layout)

        # ========== SEZIONE INFERIORE ========== #
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("📄 Documenti recenti o report trimestrali"))
        main_content.addWidget(bottom_frame)

        # aggiungi al layout della content_area
        for i in reversed(range(layout.count())):
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.addLayout(main_content)

        # segnali
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
        sizes, colors = [entrate, uscite], ["#1e7be7", "gray"]
        if sum(sizes) == 0:
            # Mostra un donut grigio neutro con testo centrale
            self.ax.pie([1], colors=["#d3d3d3"], startangle=90, wedgeprops=dict(width=0.4))
            self.ax.text(
                0, 0, "Nessun dato",
                ha="center", va="center",
                fontsize=14, color="gray"
            )
        else:
            self.ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.4))
            self.ax.text(
                0, 0,
                f"€ {entrate - uscite}",
                ha='center', va='center',
                fontsize=16, fontweight='bold', color='white'
            )

            labels = ['Entrate', 'Uscite']
            perc = [f"{sizes[0] / sum(sizes) * 100:.0f}%", f"{sizes[1] / sum(sizes) * 100:.0f}%"]
            x_positions = [-1.8, 1.1]  # centrati rispetto al grafico
            y_text = -1.5
            dot_offset = -0.25  # distanza orizzontale del pallino rispetto al testo
            dot_size = 0.1  # raggio pallino

            for label, p, x, c in zip(labels, perc, x_positions, colors):
                # Pallino colorato
                self.ax.add_patch(mpatches.Circle(
                    (x + dot_offset, y_text), dot_size, color=c, transform=self.ax.transData, clip_on=False)
                )
                # Testo accanto
                self.ax.text(x, y_text,f"{label} {p}", ha='left', va='center', color='white', fontsize=10)

            self.ax.set_aspect('equal')
        centre_circle = mpatches.Circle((0, 0), 0.70, fc=COLORE_WIDGET_2)
        self.ax.add_artist(centre_circle)
        self.ax.set_title("Movimenti", color="white", y=1)
        self.chart_canvas.draw()

    def update_info_box(self, index):
        if index < 0 or index >= len(self.proprieta):
            return
        prop = self.proprieta[index]
        self.selected_property = prop
        self.info_name.setText(f"🏡 Proprietà: {prop['name']}")
        self.info_address.setText(f"📍 Indirizzo: {prop['address']}")
        self.info_owner.setText(f"👤 Proprietario: {prop['owner']}")
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
        elif "Dashboard" in voce:
            self.show_dashboard_ui()
        elif "Contabilità" in voce:
            pass

    # ===================== DOCUMENTS UI =====================
    def show_documents_ui(self):
        # Pulisci solo l'area contenuti
        layout = self.content_area.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Crea il layout dei documenti
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
        docs_layout.addWidget(self.docs_list)
        self.load_documents()

        # Bottone aggiungi
        add_doc_btn = QPushButton("+")
        add_doc_btn.setFixedSize(40, 40)
        add_doc_btn.setStyleSheet(
            "background-color: #007BFF; color: white; font-size: 18px; font-weight: bold; border-radius: 20px;"
        )
        docs_layout.addWidget(add_doc_btn, alignment=Qt.AlignRight)
        add_doc_btn.clicked.connect(self.add_document)

        # Aggiungi tutto al layout di self.content_area
        content_widget = QFrame()
        content_widget.setLayout(docs_layout)
        layout.addWidget(content_widget)

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

        folders = [f for f in files if os.path.isdir(os.path.join(prop_folder, f))]
        regular_files = [f for f in files if not os.path.isdir(os.path.join(prop_folder, f))]
        ordered_files = folders + regular_files

        for idx_f, f in enumerate(ordered_files):
            file_path = os.path.join(prop_folder, f)
            bg_color = QColor(COLORE_RIGA_2 if idx_f % 2 == 0 else COLORE_RIGA_1)

            # crea widget personalizzato per la riga
            row_widget = QWidget()
            layout = QHBoxLayout(row_widget)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(10)

            label = QLabel(f)
            label.setStyleSheet("color: white; font-size: 14px;")
            layout.addWidget(label, stretch=1)

            if os.path.isdir(file_path):
                icon_label = QLabel()
                icon_label.setPixmap(self.folder_icon.pixmap(20, 20))
                layout.insertWidget(0, icon_label)
                # pulsante entra nella cartella
                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)  # stessa icona di prima o una diversa
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")
                open_btn.clicked.connect(lambda _, path=file_path: self.enter_folder(path))
                layout.addWidget(open_btn)
            else:
                # pulsante preview
                preview_btn = QPushButton()
                preview_btn.setIcon(self.file_icon)  # definisci self.preview_icon altrove
                preview_btn.setIconSize(QSize(18, 18))
                preview_btn.setFixedSize(28, 28)
                preview_btn.setStyleSheet("border: none;")
                preview_btn.clicked.connect(lambda _, path=file_path: self.preview_file(path))
                layout.addWidget(preview_btn)

                # pulsante apri cartella
                open_btn = QPushButton()
                open_btn.setIcon(self.open_folder_icon)  # definisci self.open_folder_icon altrove
                open_btn.setIconSize(QSize(18, 18))
                open_btn.setFixedSize(28, 28)
                open_btn.setStyleSheet("border: none;")
                open_btn.clicked.connect(lambda _, path=file_path: self.open_file_location(path))
                layout.addWidget(open_btn)

            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 35))
            self.docs_list.addItem(item)
            self.docs_list.setItemWidget(item, row_widget)

            # colore di sfondo
            row_widget.setStyleSheet(f"background-color: {bg_color.name()};")

    def enter_folder(self, folder_path):
        # aggiorna selected_property per navigare dentro
        self.selected_property = {"name": os.path.relpath(folder_path, DOCS_DIR)}
        self.load_documents()

    def preview_file(self, path):
        print("Preview:", path)

    def open_file_location(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))

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

    def resizeEvent(self, event):
        self.menu.setFixedWidth(int(self.width() * W_LAT_MENU))
        super().resizeEvent(event)

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


