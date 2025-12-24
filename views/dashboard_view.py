from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import numpy as np

from views.base_view import BaseView
import Functions
from styles import *


class ClickableFrame(QFrame):
    """Frame cliccabile per navigazione"""

    def __init__(self, parent=None, on_click=None):
        super().__init__(parent)
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(event)


class DashboardView(BaseView):
    """View per la Dashboard principale"""

    def __init__(self, property_service, transaction_service, deadline_service, main_window, parent=None):
        self.deadline_service = deadline_service
        self.main_window = main_window  # 🔧 Riferimento alla finestra principale
        self.proprieta = property_service.get_all()
        self.selected_property = None  # 🔧 Inizia con None (tutte le proprietà)
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia della dashboard"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # ========== HEADER ========== #
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        # --- Riga 1: Selezione proprietà + bottone aggiungi ---
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        prop_widget = QWidget()
        prop_layout = QVBoxLayout(prop_widget)
        prop_layout.setContentsMargins(0, 0, 0, 0)
        prop_layout.addWidget(QLabel("Seleziona proprietà:"))

        # 🔧 3. AGGIUNTA "TUTTE LE PROPRIETÀ"
        self.property_selector = QComboBox()
        self.property_selector.addItem("Tutte le proprietà", None)  # 🔧 Opzione default
        for p in self.proprieta:
            self.property_selector.addItem(p["name"], p["id"])

        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        self.property_selector.setCurrentIndex(0)  # 🔧 Seleziona "Tutte" di default
        prop_layout.addWidget(self.property_selector)

        top_row.addWidget(prop_widget, stretch=3)
        top_row.addSpacing(200)
        top_row.addStretch()

        # --- Riga 2: "Proprietà" e "Periodo" ---
        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)

        label_proprieta = QLabel("Dashboard")
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

        header_layout.addLayout(top_row)
        header_layout.addLayout(mid_row)

        main_layout.addLayout(header_layout)

        # ========== SEZIONE CENTRALE ========== #
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(25)

        # --- Colonna sinistra: Info proprietà + Prossima scadenza ---
        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # 🔧 Info proprietà - CLICCABILE
        info_frame = ClickableFrame(on_click=lambda: self.main_window.navigate_to_section("Le mie proprietà"))
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORE_WIDGET_2}; 
                border-radius: 12px; 
                padding: 15px;
            }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)

        info_title = QLabel("📋 Informazioni Proprietà")
        info_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        info_layout.addWidget(info_title)

        self.info_name = QLabel()
        self.info_address = QLabel()
        self.info_owner = QLabel()

        self.info_name.setStyleSheet("color: white; font-size: 13px;")
        self.info_address.setStyleSheet("color: white; font-size: 13px;")
        self.info_owner.setStyleSheet("color: white; font-size: 13px;")

        self.update_info_display()

        info_layout.addWidget(self.info_name)
        info_layout.addWidget(self.info_address)
        info_layout.addWidget(self.info_owner)
        info_layout.addStretch()

        # 🔧 Widget Prossima Scadenza - CLICCABILE
        deadline_frame = ClickableFrame(on_click=lambda: self.main_window.navigate_to_section("Calendario"))
        deadline_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORE_WIDGET_2}; 
                border-radius: 12px; 
                padding: 15px;
            }}
        """)
        deadline_layout = QVBoxLayout(deadline_frame)
        deadline_layout.setSpacing(8)

        deadline_title = QLabel("⏰ Prossima Scadenza")
        deadline_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        deadline_layout.addWidget(deadline_title)

        self.deadline_title_label = QLabel()
        self.deadline_date_label = QLabel()
        self.deadline_desc_label = QLabel()

        self.deadline_title_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        self.deadline_date_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.deadline_desc_label.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        self.deadline_desc_label.setWordWrap(True)

        deadline_layout.addWidget(self.deadline_title_label)
        deadline_layout.addWidget(self.deadline_date_label)
        deadline_layout.addWidget(self.deadline_desc_label)
        deadline_layout.addStretch()

        # Aggiungi i frame alla colonna sinistra
        left_column.addWidget(info_frame, stretch=1)
        left_column.addWidget(deadline_frame, stretch=1)

        # --- Grafico Donut - CLICCABILE ---
        chart_frame = ClickableFrame(on_click=lambda: self.main_window.navigate_to_section("Contabilità"))
        chart_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORE_WIDGET_2}; 
                border-radius: 12px; 
                padding: 20px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setSpacing(10)

        self.fig = Figure(figsize=(4, 4), facecolor=COLORE_WIDGET_2)
        self.chart_canvas = FigureCanvas(self.fig)
        self.chart_canvas.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)
        chart_layout.addWidget(self.chart_canvas)

        middle_layout.addLayout(left_column, 2)
        middle_layout.addWidget(chart_frame, 3)

        main_layout.addLayout(middle_layout)

        # ========== SEZIONE INFERIORE - CLICCABILE ========== #
        bottom_frame = ClickableFrame(on_click=lambda: self.main_window.navigate_to_section("Documenti"))
        bottom_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORE_WIDGET_2}; 
                border-radius: 12px; 
                padding: 15px;
            }}
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("📄 Documenti - Clicca per gestire"))
        main_layout.addWidget(bottom_frame)

        # Connetti segnali
        self.property_selector.currentIndexChanged.connect(self.update_info_box)

        # Carica dati iniziali
        self.update_chart()
        self.update_next_deadline()

    def update_info_display(self):
        """Aggiorna la visualizzazione delle informazioni"""
        if not self.proprieta:
            self.info_name.setText("Nessuna proprietà registrata.")
            self.info_address.setText("")
            self.info_owner.setText("")
        elif self.selected_property is None:
            # Mostra info aggregate
            num_prop = len(self.proprieta)
            self.info_name.setText(f"🏡 {num_prop} proprietà totali")
            self.info_address.setText(f"📊 Vista aggregata di tutte le proprietà")
            self.info_owner.setText(f"👥 Clicca per gestire le proprietà")
        else:
            # Mostra singola proprietà
            p = self.selected_property
            self.info_name.setText(f"🏡 {p['name']}")
            self.info_address.setText(f"📍 {p['address']}")
            self.info_owner.setText(f"👤 {p['owner']}")

    def update_next_deadline(self):
        """Aggiorna il widget della prossima scadenza"""
        property_id = self.selected_property["id"] if self.selected_property else None
        next_deadline = self.deadline_service.get_next_deadline(property_id)

        if next_deadline:
            self.deadline_title_label.setText(f"📌 {next_deadline['title']}")

            # Formatta la data
            due_date = datetime.strptime(next_deadline['due_date'], "%Y-%m-%d")
            days_left = (due_date - datetime.now()).days

            if days_left < 0:
                date_text = f"⚠️ Scaduta {abs(days_left)} giorni fa"
                self.deadline_date_label.setStyleSheet("color: #e74c3c; font-size: 12px; font-weight: bold;")
            elif days_left == 0:
                date_text = "🔴 OGGI"
                self.deadline_date_label.setStyleSheet("color: #e74c3c; font-size: 12px; font-weight: bold;")
            elif days_left == 1:
                date_text = "🟡 Domani"
                self.deadline_date_label.setStyleSheet("color: #f39c12; font-size: 12px; font-weight: bold;")
            elif days_left <= 7:
                date_text = f"🟡 Tra {days_left} giorni"
                self.deadline_date_label.setStyleSheet("color: #f39c12; font-size: 12px; font-weight: bold;")
            else:
                date_text = f"🟢 Tra {days_left} giorni"
                self.deadline_date_label.setStyleSheet("color: #2ecc71; font-size: 12px;")

            self.deadline_date_label.setText(f"{date_text} - {due_date.strftime('%d/%m/%Y')}")

            # Descrizione
            if next_deadline.get('description'):
                self.deadline_desc_label.setText(next_deadline['description'])
            else:
                self.deadline_desc_label.setText("Nessuna descrizione")
        else:
            self.deadline_title_label.setText("Nessuna scadenza imminente")
            self.deadline_date_label.setText("✅ Tutto in regola!")
            self.deadline_date_label.setStyleSheet("color: #2ecc71; font-size: 12px;")
            self.deadline_desc_label.setText("")

    def update_chart(self):
        """Aggiorna il grafico donut"""
        text = self.period_selector.currentText()
        mesi = {"1 mese": 1, "6 mesi": 6, "1 anno": 12, "3 anni": 36}[text]
        end_date = datetime.today()
        start_date = end_date - timedelta(days=30 * mesi)

        property_id = self.selected_property["id"] if self.selected_property else None

        rows = self.transaction_service.get_all(
            property_id=property_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )

        entrate = sum(t["amount"] for t in rows if t["type"] == "Entrata")
        uscite = sum(t["amount"] for t in rows if t["type"] == "Uscita")

        self.ax.clear()
        sizes, colors = [entrate, uscite], ["#1e7be7", "gray"]

        if sum(sizes) == 0:
            self.ax.pie([1], colors=["#d3d3d3"], startangle=90, wedgeprops=dict(width=0.4))
            self.ax.text(0, 0, "Nessun dato", ha="center", va="center", fontsize=14, color="gray")
        else:
            self.ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.4))
            self.ax.text(0, 0, f"€ {entrate - uscite:.0f}", ha='center', va='center',
                         fontsize=16, fontweight='bold', color='white')

            labels = ['Entrate', 'Uscite']
            perc = [f"{sizes[0] / sum(sizes) * 100:.0f}%", f"{sizes[1] / sum(sizes) * 100:.0f}%"]
            x_positions = [-1.2, 1.1]
            y_text = -1.5
            dot_offset = -0.25
            dot_size = 0.1

            for label, p, x, c in zip(labels, perc, x_positions, colors):
                self.ax.add_patch(mpatches.Circle(
                    (x + dot_offset, y_text), dot_size, color=c, transform=self.ax.transData, clip_on=False)
                )
                self.ax.text(x, y_text, f"{label} {p}", ha='left', va='center', color='white', fontsize=10)

            self.ax.set_aspect('equal')

        centre_circle = mpatches.Circle((0, 0), 0.70, fc=COLORE_WIDGET_2)
        self.ax.add_artist(centre_circle)
        self.ax.set_title("Movimenti", color="white", y=1)
        self.chart_canvas.draw()

    def update_info_box(self, index):
        """Aggiorna le info della proprietà selezionata"""
        if index == 0:
            # "Tutte le proprietà" selezionato
            self.selected_property = None
        elif index > 0 and index <= len(self.proprieta):
            # Proprietà specifica selezionata
            self.selected_property = self.proprieta[index - 1]

        self.update_info_display()
        self.update_chart()
        self.update_next_deadline()