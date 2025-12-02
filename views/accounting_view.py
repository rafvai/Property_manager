from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QWidget, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import pyqtgraph as pg
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

        # --- GRAFICO ---
        self.accounting_plot = pg.PlotWidget()
        self.accounting_plot.setBackground(COLORE_BACKGROUND)
        self.accounting_plot.showGrid(x=True, y=True, alpha=0.3)

        # 🆕 Etichette invertite
        self.accounting_plot.setLabel("bottom", "Mese", color="white", size="12pt")
        self.accounting_plot.setLabel("left", "Quantità in €", color="white", size="12pt")

        self.accounting_plot.hideButtons()

        # 🆕 Etichette mesi sull'asse X
        month_labels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                        'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        x_axis = self.accounting_plot.getAxis('bottom')
        x_dict = {i + 1: month_labels[i] for i in range(12)}
        x_axis.setTicks([list(x_dict.items())])
        x_axis.setStyle(tickTextOffset=10)

        # Stile assi
        for axis in ['left', 'bottom']:
            self.accounting_plot.getAxis(axis).setTextPen('w')
            self.accounting_plot.getAxis(axis).setPen(pg.mkPen(color='w', width=2))

        main_layout.addWidget(self.accounting_plot, stretch=3)

        # --- TABELLA ---
        self.accounting_table = QTableWidget()
        # 🆕 Tabella orizzontale: 12 colonne (mesi) + 3 righe (Entrate, Uscite, Saldo)
        self.accounting_table.setColumnCount(12)
        self.accounting_table.setRowCount(3)

        month_labels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                        'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        self.accounting_table.setHorizontalHeaderLabels(month_labels)
        self.accounting_table.setVerticalHeaderLabels(["Entrate (€)", "Uscite (€)", "Saldo (€)"])

        # 🆕 Distribuisci le colonne uniformemente su tutta la larghezza
        self.accounting_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 🆕 Ridimensiona righe per contenuto
        self.accounting_table.resizeRowsToContents()

        # 🆕 Altezza fissa basata sul contenuto (3 righe + header)
        header_height = self.accounting_table.horizontalHeader().height()
        row_height = self.accounting_table.rowHeight(0) * 3
        self.accounting_table.setMaximumHeight(header_height + row_height + 10)

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

        # ⭐ USA IL SERVICE
        results = self.transaction_service.get_monthly_summary(year)

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
        """Aggiorna il grafico con mesi sull'asse X"""
        mesi = np.arange(1, 13)

        self.accounting_plot.clear()

        # 🆕 Aggiungi legenda PRIMA di plottare
        legend = self.accounting_plot.addLegend(offset=(10, 10))
        legend.setLabelTextColor('w')

        # 🆕 Linea Entrate (verde)
        self.accounting_plot.plot(
            mesi, entrate,
            pen=pg.mkPen(color="#2ecc71", width=3),
            name="Entrate",
            symbol="o",
            symbolSize=12,
            symbolBrush="#2ecc71",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        # 🆕 Linea Uscite (rosso)
        self.accounting_plot.plot(
            mesi, spese,
            pen=pg.mkPen(color="#e74c3c", width=3),
            name="Uscite",
            symbol="o",
            symbolSize=12,
            symbolBrush="#e74c3c",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        # 🆕 Linea Saldo (grigio tratteggiato)
        self.accounting_plot.plot(
            mesi, saldo,
            pen=pg.mkPen(color="#bdc3c7", width=3, style=Qt.PenStyle.DashLine),
            name="Saldo",
            symbol="s",
            symbolSize=10,
            symbolBrush="#bdc3c7",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        # Blocca movimento
        self.accounting_plot.setMouseEnabled(x=False, y=False)
        self.accounting_plot.setXRange(0.5, 12.5, padding=0)

        # 🆕 Asse Y dinamico - FIX per visualizzare anche valori piccoli
        all_values = np.concatenate([entrate, spese, saldo])
        all_values = all_values[all_values != 0]  # Rimuovi zeri

        if len(all_values) > 0:
            min_value = np.min(all_values)
            max_value = np.max(all_values)
            padding = (max_value - min_value) * 0.1 if max_value > min_value else max_value * 0.1

            if min_value < 0:
                self.accounting_plot.setYRange(min_value - padding, max_value + padding, padding=0)
            else:
                self.accounting_plot.setYRange(0, max_value + padding, padding=0)
        else:
            # Nessun dato - range di default
            self.accounting_plot.setYRange(0, 1000, padding=0)

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