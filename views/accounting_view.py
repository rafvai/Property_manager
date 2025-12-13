from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QWidget, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime

from views.base_view import BaseView
from styles import *


class AccountingView(BaseView):
    """View per la sezione Contabilità"""

    def __init__(self, property_service, transaction_service, parent=None):
        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia contabilità"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel("📊 Contabilità - Andamento annuale")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # 🆕 Selettore proprietà
        property_label = QLabel("Proprietà:")
        property_label.setStyleSheet("color: white;")
        header_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.addItem("Tutte le proprietà", None)  # Opzione "Tutte"

        # Carica proprietà dal service
        properties = self.property_service.get_all()
        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])

        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.currentIndexChanged.connect(self.update_data)
        header_layout.addWidget(self.property_selector)

        # Selettore anno
        year_label = QLabel("Anno:")
        year_label.setStyleSheet("color: white;")
        header_layout.addWidget(year_label)

        self.year_selector = QComboBox()
        current_year = datetime.now().year
        for year in range(current_year - 5, current_year + 1):
            self.year_selector.addItem(str(year))
        self.year_selector.setCurrentText(str(current_year))
        self.year_selector.setStyleSheet(default_combo_box_style)
        self.year_selector.currentIndexChanged.connect(self.update_data)
        header_layout.addWidget(self.year_selector)

        main_layout.addLayout(header_layout)

        # --- GRAFICO CON MATPLOTLIB ---
        self.fig = Figure(figsize=(10, 4), facecolor=COLORE_WIDGET_2)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)

        # Stile grafico
        self.ax.set_xlabel('Mese', color='white', fontsize=12)
        self.ax.set_ylabel('Quantità in €', color='white', fontsize=12)
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.grid(True, alpha=0.3, color='white')

        # Altezza fissa
        self.canvas.setMinimumHeight(300)
        self.canvas.setMaximumHeight(400)

        main_layout.addWidget(self.canvas, stretch=0)

        # --- TABELLA ---
        self.accounting_table = QTableWidget()
        # Tabella orizzontale: 12 colonne (mesi) + 3 righe (Entrate, Uscite, Saldo)
        self.accounting_table.setColumnCount(12)
        self.accounting_table.setRowCount(3)

        month_labels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                        'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        self.accounting_table.setHorizontalHeaderLabels(month_labels)
        self.accounting_table.setVerticalHeaderLabels(["Entrate (€)", "Uscite (€)", "Saldo (€)"])

        # Distribuisci le colonne uniformemente su tutta la larghezza
        self.accounting_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 🆕 Imposta altezza righe fissa più alta
        for i in range(3):
            self.accounting_table.setRowHeight(i, 45)  # 45px per riga

        # Altezza fissa basata sul contenuto (3 righe + header)
        header_height = self.accounting_table.horizontalHeader().height()
        row_height = 45 * 3  # 3 righe da 45px ciascuna
        self.accounting_table.setMaximumHeight(header_height + row_height + 15)

        self.accounting_table.setStyleSheet("""
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 8px; }
            QTableWidget { color: white; background-color: #2c3e50; font-size: 13px; gridline-color: #7f8c8d; }
        """)

        main_layout.addWidget(self.accounting_table, stretch=0)

        # Carica dati iniziali
        self.update_data()

    def update_data(self):
        """Recupera dati dal DB e aggiorna grafico + tabella"""
        year = int(self.year_selector.currentText())

        # 🔧 FIX: Recupera l'ID della proprietà selezionata
        property_id = self.property_selector.currentData()

        # 🔧 FIX: Passa property_id al service
        results = self.transaction_service.get_monthly_summary(year, property_id)

        # Array per 12 mesi
        entrate = np.zeros(12)
        spese = np.zeros(12)

        for row in results:
            month_idx = row[0] - 1
            tipo = row[1]
            importo = row[2]

            if tipo == "Entrata":
                entrate[month_idx] = importo
            elif tipo == "Uscita":
                spese[month_idx] = importo

        saldo = np.cumsum(entrate - spese)

        # Aggiorna grafico e tabella
        self.update_chart(entrate, spese, saldo)
        self.update_table(entrate, spese, saldo)

    def update_chart(self, entrate, spese, saldo):
        """Aggiorna il grafico con matplotlib"""
        mesi = np.arange(1, 13)
        month_labels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                        'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

        # Clear
        self.ax.clear()

        # Verifica dati
        has_data = np.any(entrate > 0) or np.any(spese > 0)

        if not has_data:
            self.ax.text(6.5, 500, 'Nessun dato per l\'anno selezionato',
                         ha='center', va='center', color='white', fontsize=14)
            self.canvas.draw()
            return

        # Plot linee
        self.ax.plot(mesi, entrate,
                     color='#2ecc71',
                     linewidth=3,
                     marker='o',
                     markersize=10,
                     label='Entrate',
                     markerfacecolor='#2ecc71',
                     markeredgecolor='white',
                     markeredgewidth=2)

        self.ax.plot(mesi, spese,
                     color='#e74c3c',
                     linewidth=3,
                     marker='o',
                     markersize=10,
                     label='Uscite',
                     markerfacecolor='#e74c3c',
                     markeredgecolor='white',
                     markeredgewidth=2)

        self.ax.plot(mesi, saldo,
                     color='#bdc3c7',
                     linewidth=3,
                     marker='s',
                     markersize=8,
                     label='Saldo',
                     linestyle='--',
                     markerfacecolor='#bdc3c7',
                     markeredgecolor='white',
                     markeredgewidth=2)

        # Stile
        self.ax.set_xlabel('Mese', color='white', fontsize=12)
        self.ax.set_ylabel('Quantità in €', color='white', fontsize=12)
        self.ax.set_xticks(mesi)
        self.ax.set_xticklabels(month_labels)
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.grid(True, alpha=0.3, color='white')

        # Legenda
        legend = self.ax.legend(loc='upper left', facecolor=COLORE_WIDGET_2,
                                edgecolor='white', fontsize=10)
        for text in legend.get_texts():
            text.set_color('white')

        # Range
        self.ax.set_xlim(0.5, 12.5)

        all_values = np.concatenate([entrate, spese, np.abs(saldo)])
        all_values = all_values[all_values != 0]

        if len(all_values) > 0:
            min_value = min(0, np.min(saldo))
            max_value = np.max(all_values)
            padding_val = max(max_value * 0.15, 100)
            self.ax.set_ylim(min_value - padding_val * 0.1, max_value + padding_val)

        self.fig.tight_layout()
        self.canvas.draw()

    def update_table(self, entrate, spese, saldo):
        """Aggiorna la tabella in formato orizzontale"""
        # Popola le 12 colonne (mesi)
        for i in range(12):
            # Riga 0: Entrate
            entrate_item = QTableWidgetItem(f"{entrate[i]:,.2f}")
            entrate_item.setForeground(QColor("#2ecc71"))
            entrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(0, i, entrate_item)

            # Riga 1: Uscite
            uscite_item = QTableWidgetItem(f"{spese[i]:,.2f}")
            uscite_item.setForeground(QColor("#e74c3c"))
            uscite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(1, i, uscite_item)

            # Riga 2: Saldo
            saldo_item = QTableWidgetItem(f"{saldo[i]:,.2f}")
            if saldo[i] < 0:
                saldo_item.setForeground(QColor("#e74c3c"))
            else:
                saldo_item.setForeground(QColor("#2ecc71"))
            saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(2, i, saldo_item)