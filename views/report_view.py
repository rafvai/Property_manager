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

from dialogs import ExportDialog, TransactionDialogWithSuppliers
from services import supplier_service
from services.export_service import ExportService
from styles import *
from validation_utils import parse_decimal, ValidationError
from views.base_view import BaseView
from translations_manager import get_translation_manager


class ReportView(BaseView):
    """View per la sezione Report con categorie"""

    def __init__(self, property_service, transaction_service, supplier_service, logger, parent=None):
        # Cache per le categorie dinamiche
        self.categories_gastos = set()
        self.categories_ganancias = set()
        self.tm = get_translation_manager()
        self.logger = logger

        # Export service
        self.export_service = ExportService()
        self.supplier_service = supplier_service

        super().__init__(property_service, transaction_service, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia report"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER RIGA 1 ---
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("report", "title"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Selettore proprietà
        property_label = QLabel(f"{self.tm.get("common", "property")}:")
        property_label.setStyleSheet("color: white;")
        header_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.addItem(self.tm.get("common", "all_properties"), None)

        properties = self.property_service.get_all()
        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])

        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.currentIndexChanged.connect(self.update_report)
        header_layout.addWidget(self.property_selector)

        # Selettore mese/anno
        month_label = QLabel(f"{self.tm.get("common", "period")}:")
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
        add_btn = QPushButton(f"+ {self.tm.get('report', 'new_transaction')}")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.clicked.connect(self.add_transaction)
        actions_layout.addWidget(add_btn)

        # Bottone Export
        export_btn = QPushButton(f"📥 {self.tm.get("report", "export")}")
        export_btn.setStyleSheet(default_export_button)
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

        # Header con totale e linea verticale rossa
        gastos_header = QHBoxLayout()
        self.gastos_total_label = QLabel(f"{self.tm.get('report', 'expenses').upper()} € 0.00")
        self.gastos_total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORE_BIANCO};border-left: 6px solid {COLORE_ERROR};padding-left: 20px;margin-left: 20px;border-radius: 0px;")
        gastos_header.addWidget(self.gastos_total_label)
        gastos_header.addStretch()

        gastos_layout.addLayout(gastos_header)

        self.gastos_table = QTableWidget()
        self.gastos_table.setColumnCount(3)
        self.gastos_table.horizontalHeader().setVisible(False)
        self.gastos_table.verticalHeader().setVisible(False)
        self.gastos_table.setStyleSheet(default_report_table)
        gastos_layout.addWidget(self.gastos_table)
        tables_layout.addWidget(gastos_frame)

        # Tabella Ganancias
        ganancias_frame = QFrame()
        ganancias_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        ganancias_layout = QVBoxLayout(ganancias_frame)

        # Header con totale
        ganancias_header = QHBoxLayout()
        self.ganancias_total_label = QLabel(f"{self.tm.get('report', 'income').upper()} € 0.00")
        self.ganancias_total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORE_BIANCO};border-left: 6px solid {COLORE_SUCCESS};padding-left: 20px;margin-left: 20px;border-radius: 0px;")
        ganancias_header.addWidget(self.ganancias_total_label)
        ganancias_header.addStretch()

        ganancias_layout.addLayout(ganancias_header)

        self.ganancias_table = QTableWidget()
        self.ganancias_table.setColumnCount(3)
        self.ganancias_table.horizontalHeader().setVisible(False)
        self.ganancias_table.verticalHeader().setVisible(False)
        self.ganancias_table.setStyleSheet(default_report_table)
        ganancias_layout.addWidget(self.ganancias_table)
        tables_layout.addWidget(ganancias_frame)

        main_layout.addLayout(tables_layout)

        # --- TABELLA TRANSAZIONI IN BASSO ---
        transactions_frame = QFrame()
        transactions_frame.setStyleSheet(f"background-color: {COLORE_WIDGET_2}; border-radius: 12px; padding: 15px;")
        transactions_layout = QVBoxLayout(transactions_frame)

        # Header con filtro
        trans_header = QHBoxLayout()

        trans_title = QLabel(self.tm.get("report", "view_transactions"))
        trans_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        trans_header.addWidget(trans_title)
        trans_header.addStretch()

        filter_label = QLabel(self.tm.get("report", "filter"))
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
        self.transactions_table.horizontalHeader().setVisible(False)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.setStyleSheet(default_report_table)

        # Imposta resize mode per colonna descrizione (indice 2)
        self.transactions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        transactions_layout.addWidget(self.transactions_table)

        main_layout.addWidget(transactions_frame)

        # Carica dati
        self.update_report()

    def populate_month_selector(self):
        """Popola il selettore con gli ultimi 24 mesi"""
        current_date = datetime.now()
        months_it = self.tm.get("months", "full")

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

        # +1 riga per l'header personalizzato
        self.transactions_table.setRowCount(len(filtered) + 1)

        # RIGA 0: Header personalizzato
        headers = [
            self.tm.get("common", "date"),
            self.tm.get("report", "amount"),
            self.tm.get("common", "description"),
            self.tm.get("common", "category"),
            self.tm.get("common", "type"),
            ""
        ]

        for col, header_text in enumerate(headers):
            header_item = QTableWidgetItem(header_text)
            header_item.setForeground(QColor("white"))
            header_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            header_item.setBackground(QColor(COLORE_WIDGET_2))
            header_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter if col != 2 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.transactions_table.setItem(0, col, header_item)

        # Imposta larghezza colonne DOPO aver creato l'header
        self.transactions_table.setColumnWidth(5, 50)  # Colonna delete button più stretta

        # RIGHE DATI (a partire dalla riga 1)
        for i, trans in enumerate(filtered, start=1):
            date_item = QTableWidgetItem(trans['date'])
            date_item.setForeground(QColor("white"))
            self.transactions_table.setItem(i, 0, date_item)

            amount_color = COLORE_ERROR if trans['type'] == 'Uscita' else COLORE_SUCCESS
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
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORE_ERROR};
                    color: white;
                    border: none;
                    border-radius: 0px;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    background-color: #c0392b;
                }}
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
                QMessageBox.information(self, self.tm.get("common", "success"), "Transacción eliminada!")
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

        # Calcola totali
        total_gastos = sum(gastos.values())
        total_ganancias = sum(ganancias.values())

        # Aggiorna label totali
        self.gastos_total_label.setText(f"{self.tm.get('report', 'expenses').upper()} € {total_gastos:,.2f}")
        self.ganancias_total_label.setText(f"{self.tm.get('report', 'income').upper()} € {total_ganancias:,.2f}")

        self.update_category_table(self.gastos_table, gastos, COLORE_ERROR)
        self.update_category_table(self.ganancias_table, ganancias, COLORE_SUCCESS)

        # Aggiorna filtro e tabella transazioni
        self.populate_category_filter()
        self.filter_transactions()

    def open_export_dialog(self):
        """Apre il dialog per esportare transazioni"""
        dialog = ExportDialog(
            self.transaction_service,
            self.property_service,
            self.export_service,
            self.tm,
            self
        )
        dialog.exec()

    def update_category_table(self, table, data, color):
        """Aggiorna tabella categorie SENZA riga totale"""
        table.setRowCount(0)

        if not data:
            # Se non ci sono dati, mostra solo l'header
            table.setRowCount(1)

            # Header personalizzato
            for col, text in enumerate(
                    [self.tm.get("common", "category"), f"{self.tm.get("report", "amount")} €",
                     f"% {self.tm.get('common', 'total')}"]):
                header_item = QTableWidgetItem(text)
                header_item.setForeground(QColor("white"))
                header_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                header_item.setBackground(QColor(COLORE_WIDGET_2))
                header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(0, col, header_item)

            # Imposta larghezze colonne
            table.setColumnWidth(0, 200)
            table.setColumnWidth(1, 120)
            table.setColumnWidth(2, 100)
            return

        total = sum(data.values())
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

        # +1 riga solo per header (rimossa riga totale)
        table.setRowCount(len(sorted_data) + 1)

        # RIGA 0: Header personalizzato
        for col, text in enumerate(
                [self.tm.get("common", "category"), f"{self.tm.get("report", "amount")} €",
                 f"% {self.tm.get('common', 'total')}"]):
            header_item = QTableWidgetItem(text)
            header_item.setForeground(QColor("white"))
            header_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            header_item.setBackground(QColor(COLORE_WIDGET_2))
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

        # Imposta showGrid e gridline color
        table.setShowGrid(True)
        table.setStyleSheet(f"""
            QTableWidget {{ 
                color: white; 
                background-color: {COLORE_WIDGET_2}; 
                font-size: 14px; 
                gridline-color: {COLORE_GRIGIO};
            }}
            QTableWidget::item {{
                border: 1px solid {COLORE_GRIGIO};
                padding: 8px;
            }}
        """)

        # Imposta resize mode per adattare le colonne al widget
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def add_transaction(self):
        """Dialog per aggiungere transazione manuale CON VALIDAZIONE"""

        # crea dialog con suggerimenti fornitori
        dialog = TransactionDialogWithSuppliers(
            self.property_service,
            self.supplier_service,
            self
        )

        # SOSTITUISCI tutto il codice di creazione dialog con:
        if dialog.exec():
            try:
                data = dialog.get_data()

                # Valida importo
                amount = parse_decimal(data["importo"], "Importo")

                trans_id = self.transaction_service.create_with_supplier(  # <- USA create_with_supplier
                    property_id=data["property_id"],
                    date=data["data_fattura"],
                    trans_type=data["tipo"],
                    amount=amount,
                    provider=data["provider"],
                    service=data["service"],
                    supplier_id=data.get("supplier_id")  # <- NUOVO: passa supplier_id
                )

                if trans_id:
                    QMessageBox.information(
                        self,
                        self.tm.get("common", "success"),
                        f"✅ Transazione aggiunta!\n\n"
                        f"Categoria: {data['service']}\n"
                        f"Importo: {amount:,.2f}€"
                    )
                    self.update_report()
                else:
                    QMessageBox.warning(
                        self,
                        self.tm.get("common", "error"),
                        "❌ Impossibile salvare la transazione."
                    )

            except ValidationError as e:
                QMessageBox.warning(
                    self,
                    "⚠️ Validazione fallita",
                    str(e)
                )