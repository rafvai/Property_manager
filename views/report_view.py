from calendar import monthrange
from collections import defaultdict
from datetime import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QDialog,
    QFormLayout, QLineEdit, QDateEdit, QDialogButtonBox, QMessageBox,
    QHeaderView
)

from dialogs import ExportDialog
from services.export_service import ExportService
from styles import *
from views.base_view import BaseView


class ReportView(BaseView):
    """View per la sezione Report con categorie"""

    def __init__(self, property_service, transaction_service, parent=None):
        # Cache per le categorie dinamiche
        self.categories_gastos = set()
        self.categories_ganancias = set()

        # Export service
        self.export_service = ExportService()

        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia report"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER RIGA 1 ---
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

        main_layout.addLayout(header_layout)

        # --- HEADER RIGA 2 - PULSANTI AZIONI ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        actions_layout.addStretch()  # Spinge i bottoni a destra

        # Bottone aggiungi transazione
        add_btn = QPushButton("+ Nueva transacción")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.clicked.connect(self.add_transaction)
        actions_layout.addWidget(add_btn)

        # Bottone Export
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
        actions_layout.addWidget(export_btn)

        main_layout.addLayout(actions_layout)

        # --- TABELLE CATEGORIE IN ALTO ---
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(15)

        # Tabella Gastos
        gastos_frame = QFrame()
        gastos_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        gastos_layout = QVBoxLayout(gastos_frame)

        gastos_title = QLabel("● Gastos")
        gastos_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
        gastos_layout.addWidget(gastos_title)

        self.gastos_table = QTableWidget()
        self.gastos_table.setColumnCount(3)
        self.gastos_table.horizontalHeader().setVisible(False)
        self.gastos_table.verticalHeader().setVisible(False)
        self.gastos_table.setStyleSheet("""
            QTableWidget { 
                color: white; 
                background-color: #2c3e50; 
                font-size: 13px; 
                gridline-color: #7f8c8d; 
            }
        """)
        gastos_layout.addWidget(self.gastos_table)
        tables_layout.addWidget(gastos_frame)

        # Tabella Ganancias
        ganancias_frame = QFrame()
        ganancias_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        ganancias_layout = QVBoxLayout(ganancias_frame)

        ganancias_title = QLabel("● Ganancias")
        ganancias_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;")
        ganancias_layout.addWidget(ganancias_title)

        self.ganancias_table = QTableWidget()
        self.ganancias_table.setColumnCount(3)
        self.ganancias_table.horizontalHeader().setVisible(False)
        self.ganancias_table.verticalHeader().setVisible(False)
        self.ganancias_table.setStyleSheet("""
            QTableWidget { 
                color: white; 
                background-color: #2c3e50; 
                font-size: 13px; 
                gridline-color: #7f8c8d; 
            }
        """)
        ganancias_layout.addWidget(self.ganancias_table)
        tables_layout.addWidget(ganancias_frame)

        main_layout.addLayout(tables_layout)

        # --- TABELLA TRANSAZIONI IN BASSO ---
        transactions_frame = QFrame()
        transactions_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        transactions_layout = QVBoxLayout(transactions_frame)

        # Header con filtro
        trans_header = QHBoxLayout()

        trans_title = QLabel("📋 Lista Transacciones")
        trans_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        trans_header.addWidget(trans_title)
        trans_header.addStretch()

        filter_label = QLabel("Filtrar:")
        filter_label.setStyleSheet("color: white;")
        trans_header.addWidget(filter_label)

        self.category_filter = QComboBox()
        self.category_filter.setStyleSheet(default_combo_box_style)
        self.category_filter.currentIndexChanged.connect(self.filter_transactions)
        trans_header.addWidget(self.category_filter)

        transactions_layout.addLayout(trans_header)

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
        transactions_layout.addWidget(self.transactions_table)

        main_layout.addWidget(transactions_frame)

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

    def populate_category_filter(self):
        """Popola il filtro categorie"""
        self.category_filter.clear()
        self.category_filter.addItem("Todas las categorías", None)

        categories = set()
        for trans in self.current_transactions:
            cat = trans.get('service') or 'Otros'
            categories.add(cat)

        for cat in sorted(categories):
            self.category_filter.addItem(cat, cat)

    def filter_transactions(self):
        """Filtra transazioni per categoria"""
        selected_category = self.category_filter.currentData()

        filtered = self.current_transactions.copy()
        if selected_category:
            filtered = [t for t in filtered if t.get('service') == selected_category]

        filtered.sort(key=lambda x: x['date'], reverse=True)

        # Pulisce completamente la tabella
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
                self.update_report()

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

        # Salva le transazioni
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

        self.update_category_table(self.gastos_table, gastos, "#e74c3c")
        self.update_category_table(self.ganancias_table, ganancias, "#2ecc71")

        # Aggiorna filtro e tabella transazioni
        self.populate_category_filter()
        self.filter_transactions()

    def open_export_dialog(self):
        """Apre il dialog per esportare transazioni"""
        dialog = ExportDialog(
            self.transaction_service,
            self.property_service,
            self.export_service,
            self
        )
        dialog.exec()

    def update_category_table(self, table, data, color):
        """Aggiorna tabella categorie"""
        table.setRowCount(0)

        if not data:
            # Se non ci sono dati, mostra solo l'header
            table.setRowCount(1)

            # Header personalizzato
            for col, text in enumerate(["Categoría", "Real €", "% Total"]):
                header_item = QTableWidgetItem(text)
                header_item.setForeground(QColor("white"))
                header_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                header_item.setBackground(QColor("#34495e"))
                header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(0, col, header_item)

            # Imposta larghezze colonne
            table.setColumnWidth(0, 200)
            table.setColumnWidth(1, 120)
            table.setColumnWidth(2, 100)
            return

        total = sum(data.values())
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

        # +2 righe: 1 per header, 1 per totale
        table.setRowCount(len(sorted_data) + 2)

        # RIGA 0: Header personalizzato
        for col, text in enumerate(["Categoría", "Real €", "% Total"]):
            header_item = QTableWidgetItem(text)
            header_item.setForeground(QColor("white"))
            header_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            header_item.setBackground(QColor("#34495e"))
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(0, col, header_item)

        # RIGHE DATI (a partire dalla riga 1)
        for i, (category, amount) in enumerate(sorted_data, start=1):
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

        # RIGA TOTALE (ultima riga)
        total_row = len(sorted_data) + 1

        total_cat = QTableWidgetItem("TOTAL")
        total_cat.setForeground(QColor("white"))
        total_cat.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        total_cat.setBackground(QColor("#1a2530"))
        table.setItem(total_row, 0, total_cat)

        total_amount = QTableWidgetItem(f"{total:,.2f} €")
        total_amount.setForeground(QColor(color))
        total_amount.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        total_amount.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_amount.setBackground(QColor("#1a2530"))
        table.setItem(total_row, 1, total_amount)

        total_perc = QTableWidgetItem("100%")
        total_perc.setForeground(QColor("#bdc3c7"))
        total_perc.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        total_perc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_perc.setBackground(QColor("#1a2530"))
        table.setItem(total_row, 2, total_perc)

        # Imposta larghezze colonne
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 100)

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
                QMessageBox.warning(self, "Error", "Importe inválido!") #errore