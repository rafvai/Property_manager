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


class DashboardView(BaseView):
    """View per la Dashboard principale"""

    def __init__(self, property_service, transaction_service, parent=None):
        # Carica proprietà dal service
        self.proprieta = property_service.get_all()
        self.selected_property = self.proprieta[0] if self.proprieta else None
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

        self.property_selector = QComboBox()
        self.property_selector.addItems([p["name"] for p in self.proprieta])
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        if self.selected_property:
            self.property_selector.setCurrentText(self.selected_property["name"])
        prop_layout.addWidget(self.property_selector)

        top_row.addWidget(prop_widget, stretch=3)
        top_row.addSpacing(200)

        add_button = QPushButton("+ Aggiungi")
        add_button.setFixedHeight(36)
        add_button.setStyleSheet(default_aggiungi_button)
        add_button.clicked.connect(self.add_property)

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

        header_layout.addLayout(top_row)
        header_layout.addLayout(mid_row)

        main_layout.addLayout(header_layout)

        # ========== SEZIONE CENTRALE ========== #
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(25)

        # --- Info proprietà ---
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 12px; padding: 5px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(0)

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

        info_layout.addWidget(self.info_name)
        info_layout.addWidget(self.info_address)
        info_layout.addWidget(self.info_owner)

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

        middle_layout.addWidget(info_frame, 2, alignment=Qt.AlignTop)
        middle_layout.addWidget(chart_frame, 3)

        main_layout.addLayout(middle_layout)

        # ========== SEZIONE INFERIORE ========== #
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"background: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.addWidget(QLabel("📄 Documenti recenti o report trimestrali"))
        main_layout.addWidget(bottom_frame)

        # Connetti segnali
        self.property_selector.currentIndexChanged.connect(self.update_info_box)

    def update_chart(self):
        """Aggiorna il grafico donut"""
        text = self.period_selector.currentText()
        mesi = {"1 mese": 1, "6 mesi": 6, "1 anno": 12, "3 anni": 36}[text]
        end_date = datetime.today()
        start_date = end_date - timedelta(days=30 * mesi)

        property_id = self.selected_property["id"] if self.selected_property else None

        # USA IL SERVICE invece di query diretta
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
            self.ax.text(0, 0, f"€ {entrate - uscite}", ha='center', va='center',
                         fontsize=16, fontweight='bold', color='white')

            labels = ['Entrate', 'Uscite']
            perc = [f"{sizes[0] / sum(sizes) * 100:.0f}%", f"{sizes[1] / sum(sizes) * 100:.0f}%"]
            x_positions = [-1.8, 1.1]
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
        if index < 0 or index >= len(self.proprieta):
            return
        prop = self.proprieta[index]
        self.selected_property = prop
        self.info_name.setText(f"🏡 Proprietà: {prop['name']}")
        self.info_address.setText(f"📍 Indirizzo: {prop['address']}")
        self.info_owner.setText(f"👤 Proprietario: {prop['owner']}")
        self.update_chart()

    def add_property(self):
        """Dialog per aggiungere una nuova proprietà"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuova proprietà")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        address_input = QLineEdit()
        owner_input = QLineEdit()

        layout.addRow("Nome:", name_input)
        layout.addRow("Indirizzo:", address_input)
        layout.addRow("Proprietario:", owner_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            nome = name_input.text().strip()
            indirizzo = address_input.text().strip()
            proprietario = owner_input.text().strip()

            if nome and indirizzo and proprietario:
                # ⭐ USA IL SERVICE
                property_id = self.property_service.create(nome, indirizzo, proprietario)

                if property_id:
                    self.proprieta = self.property_service.get_all()
                    self.property_selector.clear()
                    self.property_selector.addItems([p["name"] for p in self.proprieta])
                    self.property_selector.setCurrentIndex(len(self.proprieta) - 1)
                    self.update_chart()