from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget, QHeaderView, QDialog,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
from collections import defaultdict
from calendar import monthrange

from views.base_view import BaseView
from validation_utils import format_currency
from styles import *


class AccountingView(BaseView):
    """View per la sezione Contabilità"""

    def __init__(self, property_service, transaction_service, translation_service,
                 logger, user_prefs_service=None, parent=None):
        self.tm = translation_service
        self.logger = logger
        self.user_prefs_service = user_prefs_service
        super().__init__(property_service, transaction_service, None, parent)

    # ── helper valuta ──────────────────────────────────────────────
    def _currency(self) -> str:
        if self.user_prefs_service:
            return self.user_prefs_service.get_currency()
        return "€"

    def _fmt(self, value: float) -> str:
        return format_currency(value, symbol=self._currency())

    def setup_ui(self):
        """Costruisce l'interfaccia contabilità"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("ETICHETTE", "ANDAMENTO_ANNUALE"))
        title.setStyleSheet(default_title_style)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Selettore proprietà
        property_label = QLabel(self.tm.get("ETICHETTE", "PROPRIETA") + ":")
        property_label.setStyleSheet(f"color: {COLORE_BIANCO}")
        header_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.addItem(self.tm.get("ETICHETTE", "ALL_PROPERTIES"), None)

        properties = self.property_service.get_all()
        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])

        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.currentIndexChanged.connect(self.update_data)
        header_layout.addWidget(self.property_selector)

        # Selettore anno
        year_label = QLabel(self.tm.get("ETICHETTE", "ANNO") + ":")
        year_label.setStyleSheet(f"color: {COLORE_BIANCO}")
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
        self.fig = Figure(figsize=(10, 3.5), facecolor=COLORE_SECONDARIO)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_SECONDARIO)

        self.ax.set_xlabel(self.tm.get("ETICHETTE", "MESE"), color=COLORE_BIANCO, fontsize=12)
        self.ax.set_ylabel(self.tm.get("ETICHETTE", "QUANTITA"), color=COLORE_BIANCO, fontsize=12)
        self.ax.tick_params(colors=COLORE_BIANCO)
        self.ax.spines['bottom'].set_color(COLORE_BIANCO)
        self.ax.spines['top'].set_color(COLORE_BIANCO)
        self.ax.spines['left'].set_color(COLORE_BIANCO)
        self.ax.spines['right'].set_color(COLORE_BIANCO)
        self.ax.grid(True, alpha=0.3, color=COLORE_BIANCO)

        self.canvas.setMinimumHeight(300)
        self.canvas.setMaximumHeight(600)
        main_layout.addWidget(self.canvas, stretch=0)

        # --- TABELLA ---
        self.accounting_table = QTableWidget()
        self.accounting_table.setColumnCount(12)
        self.accounting_table.setRowCount(3)

        month_labels = self.tm.get("LISTE", "MONTHS_SHORT").split(";")
        self.accounting_table.setHorizontalHeaderLabels(month_labels)
        self.accounting_table.setVerticalHeaderLabels([
            self.tm.get("ETICHETTE", "GUADAGNI"),
            self.tm.get("ETICHETTE", "SPESE"),
            self.tm.get("ETICHETTE", "SALDO")
        ])

        self.accounting_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.accounting_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        row_height = 80
        for i in range(3):
            self.accounting_table.setRowHeight(i, row_height)

        table_height = (self.accounting_table.horizontalHeader().height()
                        + row_height * 3)
        self.accounting_table.setMaximumHeight(table_height + 25)
        self.accounting_table.setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {COLORE_SECONDARIO};
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                border: 1px solid {COLORE_GRIGIO};
            }}
            QTableWidget {{
                color: white;
                background-color: {COLORE_SECONDARIO};
                font-size: 15px;
                gridline-color: {COLORE_GRIGIO};
            }}
        """)

        main_layout.addWidget(self.accounting_table, stretch=0)
        self.update_data()

    def update_data(self):
        """Recupera dati dal DB e aggiorna grafico + tabella"""
        year        = int(self.year_selector.currentText())
        property_id = self.property_selector.currentData()
        results     = self.transaction_service.get_monthly_summary(year, property_id)

        entrate = np.zeros(12)
        spese   = np.zeros(12)

        for row in results:
            month_idx = row[0] - 1
            tipo      = row[1]
            importo   = row[2]
            if tipo == "Entrata":
                entrate[month_idx] = importo
            elif tipo == "Uscita":
                spese[month_idx] = importo

        saldo = np.cumsum(entrate - spese)
        self.update_chart(entrate, spese, saldo)
        self.update_table(entrate, spese, saldo)

    def update_chart(self, entrate, spese, saldo):
        mesi         = np.arange(1, 13)
        month_labels = self.tm.get("LISTE", "MONTHS_SHORT").split(";")

        self.ax.clear()
        has_data = np.any(entrate > 0) or np.any(spese > 0)

        if not has_data:
            self.ax.text(6.5, 500, self.tm.get("MESSAGGI", "NESSUN_DATO"),
                         ha='center', va='center', color=COLORE_BIANCO, fontsize=14)
            self.canvas.draw()
            return

        self.ax.plot(mesi, entrate, color=COLORE_SUCCESS, linewidth=1, marker='o',
                     markersize=10, label=self.tm.get("ETICHETTE", "GUADAGNI"),
                     markerfacecolor=COLORE_SUCCESS, markeredgecolor=COLORE_BIANCO,
                     markeredgewidth=2)
        self.ax.plot(mesi, spese, color=COLORE_ERROR, linewidth=1, marker='o',
                     markersize=10, label=self.tm.get("ETICHETTE", "SPESE"),
                     markerfacecolor=COLORE_ERROR, markeredgecolor=COLORE_BIANCO,
                     markeredgewidth=2)
        self.ax.plot(mesi, saldo, color=COLORE_GRIGIO, linewidth=1, marker='s',
                     markersize=8, label=self.tm.get("ETICHETTE", "SALDO"),
                     linestyle='--', markerfacecolor=COLORE_GRIGIO,
                     markeredgecolor=COLORE_BIANCO, markeredgewidth=2)

        self.ax.set_xlabel(self.tm.get("ETICHETTE", "MESE"), color=COLORE_BIANCO, fontsize=12)
        self.ax.set_ylabel(self.tm.get("ETICHETTE", "QUANTITA"), color=COLORE_BIANCO, fontsize=12)
        self.ax.set_xticks(mesi)
        self.ax.set_xticklabels(month_labels)
        self.ax.tick_params(colors=COLORE_BIANCO)
        for spine in self.ax.spines.values():
            spine.set_color(COLORE_BIANCO)
        self.ax.grid(True, alpha=0.3, color=COLORE_BIANCO)

        legend = self.ax.legend(loc='upper left', facecolor=COLORE_WIDGET_2,
                                edgecolor=COLORE_BIANCO, fontsize=10)
        for text in legend.get_texts():
            text.set_color(COLORE_BIANCO)

        self.ax.set_xlim(0.5, 12.5)
        all_values = np.concatenate([entrate, spese, np.abs(saldo)])
        all_values = all_values[all_values != 0]
        if len(all_values) > 0:
            min_value   = min(0, np.min(saldo))
            max_value   = np.max(all_values * 1.2)
            padding_val = max(max_value * 0.15, 100)
            self.ax.set_ylim(min_value - padding_val * 0.1, max_value + padding_val)

        self.fig.tight_layout()
        self.canvas.draw()

    def update_table(self, entrate, spese, saldo):
        """Aggiorna la tabella con il simbolo valuta dell'utente"""
        for i in range(12):
            entrate_item = QTableWidgetItem(self._fmt(entrate[i]))
            entrate_item.setForeground(QColor(COLORE_SUCCESS))
            entrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(0, i, entrate_item)

            uscite_item = QTableWidgetItem(self._fmt(spese[i]))
            uscite_item.setForeground(QColor(COLORE_ERROR))
            uscite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(1, i, uscite_item)

            saldo_item = QTableWidgetItem(self._fmt(saldo[i]))
            saldo_item.setForeground(
                QColor(COLORE_ERROR) if saldo[i] < 0 else QColor(COLORE_SUCCESS)
            )
            saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.accounting_table.setItem(2, i, saldo_item)