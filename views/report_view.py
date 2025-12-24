from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget, QFrame, QDialog,
    QFormLayout, QLineEdit, QDateEdit, QDialogButtonBox, QMessageBox,
    QHeaderView, QTextEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
from collections import defaultdict
from calendar import monthrange

from views.base_view import BaseView
from dialogs import ExportDialog
from services.export_service import ExportService
from styles import *


class TransactionsDialog(QDialog):
    """Dialog per visualizzare tutte le transazioni"""

    def __init__(self, transactions, transaction_service, parent=None):
        super().__init__(parent)
        self.transactions = transactions
        self.transaction_service = transaction_service
        self.all_transactions = transactions.copy()

        self.setWindowTitle("📋 Transacciones detalladas")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header con filtro categoria
        header_layout = QHBoxLayout()

        title = QLabel("📋 Lista completa de transacciones")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        filter_label = QLabel("Filtrar:")
        filter_label.setStyleSheet("color: white;")
        header_layout.addWidget(filter_label)

        self.category_filter = QComboBox()
        self.category_filter.setStyleSheet(default_combo_box_style)
        self.category_filter.currentIndexChanged.connect(self.filter_transactions)
        header_layout.addWidget(self.category_filter)

        layout.addLayout(header_layout)

        # Tabella transazioni
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels([
            "Fecha", "Importe", "Descripción", "Categoría", "Tipo", ""
        ])
        self.transactions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.setStyleSheet("""
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 8px; }
            QTableWidget { color: white; background-color: #2c3e50; font-size: 13px; gridline-color: #7f8c8d; }
        """)
        layout.addWidget(self.transactions_table)

        # Popola filtro e tabella
        self.populate_category_filter()
        self.filter_transactions()

        # Stile dialog
        self.setStyleSheet(f"QDialog {{ background-color: {COLORE_BACKGROUND}; }}")

    def populate_category_filter(self):
        """Popola il filtro categorie"""
        self.category_filter.addItem("Todas las categorías", None)

        categories = set()
        for trans in self.all_transactions:
            cat = trans.get('service') or 'Otros'
            categories.add(cat)

        for cat in sorted(categories):
            self.category_filter.addItem(cat, cat)

    def filter_transactions(self):
        """Filtra transazioni per categoria"""
        selected_category = self.category_filter.currentData()

        filtered = self.all_transactions.copy()
        if selected_category:
            filtered = [t for t in filtered if t.get('service') == selected_category]

        filtered.sort(key=lambda x: x['date'], reverse=True)

        # 🔧 FIX: Pulisce completamente la tabella
        self.transactions_table.clearContents()
        self.transactions_table.setRowCount(len(filtered))

        for i, trans in enumerate(filtered):
            date_item = QTableWidgetItem(trans['date'])
            date_item.setForeground(QColor("white"))
            self.transactions_table.setItem(i, 0, date_item)

            amount_color = "#e74c3c" if trans['type'] == 'Uscita' else "#2ecc71"
            amount_item = QTableWidgetItem(f"{trans['amount']:,.2f} €")
            amount_item.setForeground(QColor(amount_color))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.transactions_table.setItem(i, 1, amount_item)

            desc = trans.get('provider') or trans['service']
            desc_item = QTableWidgetItem(desc)
            desc_item.setForeground(QColor("white"))
            self.transactions_table.setItem(i, 2, desc_item)

            category = trans.get('service') or 'Otros'
            cat_item = QTableWidgetItem(category)
            cat_item.setForeground(QColor("#bdc3c7"))
            self.transactions_table.setItem(i, 3, cat_item)

            tipo_item = QTableWidgetItem(trans['type'])
            tipo_item.setForeground(QColor(amount_color))
            self.transactions_table.setItem(i, 4, tipo_item)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            # 🔧 FIX: Lambda corretta con checked=False
            delete_btn.clicked.connect(lambda checked=False, t=trans: self.delete_transaction(t))
            self.transactions_table.setCellWidget(i, 5, delete_btn)

    def delete_transaction(self, trans):
        """Elimina transazione"""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar transacción de {trans['amount']}€?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.transaction_service.delete(trans['id'])
            if success:
                QMessageBox.information(self, "Éxito", "Transacción eliminada!")
                # Rimuovi dalla lista locale
                self.all_transactions = [t for t in self.all_transactions if t['id'] != trans['id']]
                self.filter_transactions()


class ReportView(BaseView):
    """View per la sezione Report con categorie"""

    def __init__(self, property_service, transaction_service, parent=None):
        # Cache per le categorie dinamiche
        self.categories_gastos = set()
        self.categories_ganancias = set()

        # 🆕 Export service
        self.export_service = ExportService()

        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia report"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        header_layout = QHBoxLayout()

        title = QLabel("📊 Tracking mensile")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Selettore proprietà
        property_label = QLabel("Proprietà:")
        property_label.setStyleSheet("color: white;")
        header_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.addItem("Tutte le proprietà", None)

        properties = self.property_service.get_all()
        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])

        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.currentIndexChanged.connect(self.update_report)
        header_layout.addWidget(self.property_selector)

        # Selettore mese/anno
        month_label = QLabel("Periodo:")
        month_label.setStyleSheet("color: white;")
        header_layout.addWidget(month_label)

        self.month_selector = QComboBox()
        self.populate_month_selector()
        self.month_selector.setStyleSheet(default_combo_box_style)
        self.month_selector.currentIndexChanged.connect(self.update_report)
        header_layout.addWidget(self.month_selector)

        # Bottone aggiungi transazione
        add_btn = QPushButton("+ Nueva transacción")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.clicked.connect(self.add_transaction)
        header_layout.addWidget(add_btn)

        # Bottone visualizza transazioni
        view_trans_btn = QPushButton("📋 Ver transacciones")
        view_trans_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        view_trans_btn.clicked.connect(self.show_transactions_dialog)
        header_layout.addWidget(view_trans_btn)

        # 🆕 Bottone Export
        export_btn = QPushButton("📥 Esporta")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        export_btn.clicked.connect(self.open_export_dialog)
        header_layout.addWidget(export_btn)

        main_layout.addLayout(header_layout)

        # --- GRAFICI RIEPILOGO ---
        charts_layout = QHBoxLayout()

        # Grafico Gastos
        self.fig_gastos = Figure(figsize=(6, 3), facecolor=COLORE_WIDGET_2)
        self.canvas_gastos = FigureCanvas(self.fig_gastos)
        self.ax_gastos = self.fig_gastos.add_subplot(111, facecolor=COLORE_WIDGET_2)
        charts_layout.addWidget(self.canvas_gastos)

        # Grafico Ganancias
        self.fig_ganancias = Figure(figsize=(6, 3), facecolor=COLORE_WIDGET_2)
        self.canvas_ganancias = FigureCanvas(self.fig_ganancias)
        self.ax_ganancias = self.fig_ganancias.add_subplot(111, facecolor=COLORE_WIDGET_2)
        charts_layout.addWidget(self.canvas_ganancias)

        main_layout.addLayout(charts_layout)

        # --- TABELLE CATEGORIE ---
        tables_layout = QHBoxLayout()

        # Tabella Gastos
        gastos_frame = QFrame()
        gastos_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        gastos_layout = QVBoxLayout(gastos_frame)

        gastos_title = QLabel("🔴 Gastos")
        gastos_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
        gastos_layout.addWidget(gastos_title)

        self.gastos_table = QTableWidget()
        self.gastos_table.setColumnCount(3)
        self.gastos_table.setHorizontalHeaderLabels(["Categoría", "Real €", "% Total"])
        self.gastos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.gastos_table.verticalHeader().setVisible(False)
        self.gastos_table.setStyleSheet("""
            QHeaderView::section { background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; }
            QTableWidget { color: white; background-color: #2c3e50; font-size: 13px; gridline-color: #7f8c8d; }
        """)
        gastos_layout.addWidget(self.gastos_table)
        tables_layout.addWidget(gastos_frame)

        # Tabella Ganancias
        ganancias_frame = QFrame()
        ganancias_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        ganancias_layout = QVBoxLayout(ganancias_frame)

        ganancias_title = QLabel("🟢 Ganancias")
        ganancias_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;")
        ganancias_layout.addWidget(ganancias_title)

        self.ganancias_table = QTableWidget()
        self.ganancias_table.setColumnCount(3)
        self.ganancias_table.setHorizontalHeaderLabels(["Categoría", "Real €", "% Total"])
        self.ganancias_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ganancias_table.verticalHeader().setVisible(False)
        self.ganancias_table.setStyleSheet("""
            QHeaderView::section { background-color: #2ecc71; color: white; font-weight: bold; padding: 8px; }
            QTableWidget { color: white; background-color: #2c3e50; font-size: 13px; gridline-color: #7f8c8d; }
        """)
        ganancias_layout.addWidget(self.ganancias_table)
        tables_layout.addWidget(ganancias_frame)

        main_layout.addLayout(tables_layout)

        # Carica dati
        self.update_report()

    def populate_month_selector(self):
        """Popola il selettore con gli ultimi 24 mesi"""
        current_date = datetime.now()
        months_it = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                     "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

        for i in range(24):
            date = datetime(current_date.year, current_date.month, 1)
            month = date.month - i
            year = date.year

            while month <= 0:
                month += 12
                year -= 1

            label = f"{months_it[month - 1]} {year}"
            value = f"{year}-{month:02d}"

            self.month_selector.addItem(label, value)

        self.month_selector.setCurrentIndex(0)

    def update_report(self):
        """Aggiorna tutto il report"""
        selected_month = self.month_selector.currentData()
        if not selected_month:
            return

        year, month = selected_month.split('-')

        last_day = monthrange(int(year), int(month))[1]
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-{last_day}"

        property_id = self.property_selector.currentData()

        transactions = self.transaction_service.get_all(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date
        )

        # Salva le transazioni per il dialog
        self.current_transactions = transactions

        self.categories_gastos.clear()
        self.categories_ganancias.clear()

        gastos = defaultdict(float)
        ganancias = defaultdict(float)

        for trans in transactions:
            category = trans.get('service') or 'Otros'
            amount = trans['amount']

            if trans['type'] == 'Uscita':
                gastos[category] += amount
                self.categories_gastos.add(category)
            else:
                ganancias[category] += amount
                self.categories_ganancias.add(category)

        self.update_chart(self.ax_gastos, self.canvas_gastos, gastos, "Gastos", "#e74c3c")
        self.update_chart(self.ax_ganancias, self.canvas_ganancias, ganancias, "Ganancias", "#2ecc71")

        self.update_category_table(self.gastos_table, gastos, "#e74c3c")
        self.update_category_table(self.ganancias_table, ganancias, "#2ecc71")

    def show_transactions_dialog(self):
        """Mostra dialog con tutte le transazioni"""
        if not hasattr(self, 'current_transactions'):
            QMessageBox.warning(self, "Avviso", "Nessuna transazione da visualizzare!")
            return

        dialog = TransactionsDialog(self.current_transactions, self.transaction_service, self)
        dialog.exec()

        # Ricarica il report dopo la chiusura del dialog
        self.update_report()

    def open_export_dialog(self):
        """🆕 Apre il dialog per esportare transazioni"""
        dialog = ExportDialog(
            self.transaction_service,
            self.property_service,
            self.export_service,
            self
        )
        dialog.exec()

    def update_chart(self, ax, canvas, data, title, color):
        """Aggiorna grafico a barre"""
        ax.clear()

        if not data:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                    color='white', fontsize=14, transform=ax.transAxes)
            canvas.draw()
            return

        categories = list(data.keys())
        values = list(data.values())

        bars = ax.barh(categories, values, color=color, alpha=0.8)

        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2,
                    f'{width:.0f}€', ha='left', va='center',
                    color='white', fontsize=10, fontweight='bold')

        ax.set_xlabel('Importe €', color='white', fontsize=11)
        ax.set_title(title, color=color, fontsize=14, fontweight='bold')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_visible(False)
        ax.set_facecolor(COLORE_WIDGET_2)

        canvas.figure.tight_layout()
        canvas.draw()

    def update_category_table(self, table, data, color):
        """Aggiorna tabella categorie"""
        table.setRowCount(0)

        if not data:
            return

        total = sum(data.values())
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

        table.setRowCount(len(sorted_data) + 1)

        for i, (category, amount) in enumerate(sorted_data):
            percentage = (amount / total * 100) if total > 0 else 0

            cat_item = QTableWidgetItem(category)
            cat_item.setForeground(QColor("white"))
            table.setItem(i, 0, cat_item)

            amount_item = QTableWidgetItem(f"{amount:,.2f} €")
            amount_item.setForeground(QColor(color))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 1, amount_item)

            perc_item = QTableWidgetItem(f"{percentage:.1f}%")
            perc_item.setForeground(QColor("#bdc3c7"))
            perc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 2, perc_item)

        total_cat = QTableWidgetItem("TOTAL")
        total_cat.setForeground(QColor("white"))
        total_cat.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        table.setItem(len(sorted_data), 0, total_cat)

        total_amount = QTableWidgetItem(f"{total:,.2f} €")
        total_amount.setForeground(QColor(color))
        total_amount.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        total_amount.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        table.setItem(len(sorted_data), 1, total_amount)

        total_perc = QTableWidgetItem("100%")
        total_perc.setForeground(QColor("#bdc3c7"))
        total_perc.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        total_perc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(len(sorted_data), 2, total_perc)

    def add_transaction(self):
        """Dialog per aggiungere transazione manuale"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nueva transacción")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        type_combo = QComboBox()
        type_combo.addItems(["Uscita", "Entrata"])
        layout.addRow("Tipo*:", type_combo)

        category_combo = QComboBox()
        category_combo.setEditable(True)
        category_combo.setPlaceholderText("Scrivi o seleziona...")

        def update_categories():
            category_combo.clear()
            if type_combo.currentText() == "Uscita":
                for cat in sorted(self.categories_gastos):
                    category_combo.addItem(cat)
            else:
                for cat in sorted(self.categories_ganancias):
                    category_combo.addItem(cat)

        type_combo.currentTextChanged.connect(update_categories)
        update_categories()
        layout.addRow("Categoría*:", category_combo)

        amount_input = QLineEdit()
        amount_input.setPlaceholderText("100.50")
        layout.addRow("Importe €*:", amount_input)

        provider_input = QLineEdit()
        provider_input.setPlaceholderText("Nombre proveedor")
        layout.addRow("Proveedor:", provider_input)

        date_input = QDateEdit()
        date_input.setDisplayFormat("dd/MM/yyyy")
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.currentDate())
        layout.addRow("Fecha*:", date_input)

        property_combo = QComboBox()
        properties = self.property_service.get_all()
        for prop in properties:
            property_combo.addItem(prop['name'], prop['id'])
        if properties:
            layout.addRow("Propiedad:", property_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            try:
                amount = float(amount_input.text().strip().replace(',', '.'))
                category = category_combo.currentText().strip()
                trans_type = type_combo.currentText()
                provider = provider_input.text().strip() or "Manual"
                date_str = date_input.date().toString("dd/MM/yyyy")
                property_id = property_combo.currentData() if properties else None

                if not category:
                    QMessageBox.warning(self, "Error", "Inserta una categoría!")
                    return

                trans_id = self.transaction_service.create(
                    property_id=property_id,
                    date=date_str,
                    trans_type=trans_type,
                    amount=amount,
                    provider=provider,
                    service=category
                )

                if trans_id:
                    QMessageBox.information(self, "Éxito", f"Transacción añadida!\n\nCategoría: {category}")
                    self.update_report()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo guardar la transacción.")

            except ValueError:
                QMessageBox.warning(self, "Error", "Importe inválido!")