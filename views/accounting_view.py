from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QWidget
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
        self.accounting_plot.setLabel("left", "Quantità in €", color="white")
        self.accounting_plot.setLabel("bottom", "Mese", color="white")
        self.accounting_plot.hideButtons()

        main_layout.addWidget(self.accounting_plot, stretch=2)

        # --- TABELLA ---
        self.accounting_table = QTableWidget()
        self.accounting_table.setColumnCount(4)
        self.accounting_table.setHorizontalHeaderLabels(["Mese", "Entrate (€)", "Spese (€)", "Saldo finale (€)"])
        self.accounting_table.verticalHeader().setVisible(False)
        self.accounting_table.setStyleSheet("""
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; }
            QTableWidget { color: white; background-color: #2c3e50; font-size: 13px; gridline-color: #7f8c8d; }
        """)

        main_layout.addWidget(self.accounting_table, stretch=1)

        # Carica dati iniziali
        self.update_data()

    def update_data(self):
        """Recupera dati dal DB e aggiorna grafico + tabella"""
        year = int(self.year_selector.currentText())
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        # Query
        query = """
            SELECT 
                CAST(substr(date, 4, 2) AS INTEGER) as month,
                type,
                SUM(amount) as total
            FROM transactions
            WHERE 
                date(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2))
                BETWEEN date(?) AND date(?)
            GROUP BY month, type
            ORDER BY month ASC
        """

        self.cursor_read_only.execute(query, [start_date, end_date])
        results = self.cursor_read_only.fetchall()

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

        # Aggiorna grafico
        self.update_chart(entrate, spese, saldo)

        # Aggiorna tabella
        self.update_table(entrate, spese, saldo)

    def update_chart(self, entrate, spese, saldo):
        """Aggiorna il grafico"""
        mesi = np.arange(1, 13)

        self.accounting_plot.clear()

        self.accounting_plot.plot(
            mesi, entrate,
            pen=pg.mkPen(color="#2ecc71", width=3),
            name="Entrate",
            symbol="o",
            symbolSize=15,
            symbolBrush="#2ecc71",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        self.accounting_plot.plot(
            mesi, spese,
            pen=pg.mkPen(color="#e74c3c", width=3),
            name="Uscita",
            symbol="o",
            symbolSize=15,
            symbolBrush="#e74c3c",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        self.accounting_plot.plot(
            mesi, saldo,
            pen=pg.mkPen(color="#bdc3c7", width=3, style=Qt.PenStyle.DashLine),
            name="Saldo finale",
            symbol="s",
            symbolSize=12,
            symbolBrush="#bdc3c7",
            symbolPen=pg.mkPen(color="w", width=2)
        )

        # Blocca movimento
        self.accounting_plot.setMouseEnabled(x=False, y=False)
        self.accounting_plot.setXRange(0.5, 12.5, padding=0)

        # Asse Y dinamico
        max_value = max(np.max(entrate), np.max(spese), np.max(np.abs(saldo)))
        if max_value > 0:
            self.accounting_plot.setYRange(-max_value * 0.1, max_value * 1.2, padding=0)
        else:
            self.accounting_plot.setYRange(0, 100, padding=0)

    def update_table(self, entrate, spese, saldo):
        """Aggiorna la tabella"""
        mesi_nomi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

        self.accounting_table.setRowCount(12)

        for i in range(12):
            self.accounting_table.setItem(i, 0, QTableWidgetItem(mesi_nomi[i]))
            self.accounting_table.setItem(i, 1, QTableWidgetItem(f"{entrate[i]:,.2f} €"))
            self.accounting_table.setItem(i, 2, QTableWidgetItem(f"{spese[i]:,.2f} €"))
            self.accounting_table.setItem(i, 3, QTableWidgetItem(f"{saldo[i]:,.2f} €"))

            # Colora saldo
            saldo_item = self.accounting_table.item(i, 3)
            if saldo[i] < 0:
                saldo_item.setForeground(QColor("#e74c3c"))
            else:
                saldo_item.setForeground(QColor("#2ecc71"))