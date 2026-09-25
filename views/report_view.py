from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dialogs import ExportDialog, TransactionDialogWithSuppliers
from dialogs_import import ImportDialog
from resources import icon_path
from services.export_service import ExportService
from services.import_service import ImportService
from styles import (
    COLORE_BIANCO,
    COLORE_ERROR,
    COLORE_ITEM_HOVER,
    COLORE_SUCCESS,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_combo_box_style,
    default_title_style,
)
from validation_utils import ValidationError, format_currency, parse_decimal
from views.base_view import BaseView
from views.ui_helpers import (
    BottoneIcona,
    icona_cestino,
    icona_pallino,
    mescola,
    stile_scrollbar,
    tinta,
)

COLORE_TESTO_SECONDARIO = "#94a3b8"
COLORE_DIVISORE         = "#2b3a4f"

STILE_BOTTONE_ICONA = f"""
    QPushButton {{
        background: transparent; border: 1px solid #334155; border-radius: 6px;
        padding: 6px 12px; min-width: 20px;
    }}
    QPushButton:hover {{ border-color: {COLORE_ITEM_HOVER}; background-color: {COLORE_WIDGET_2}; }}
"""


class ReportView(BaseView):
    """View per la sezione Report con categorie"""

    def __init__(self, property_service, transaction_service, supplier_service,
                 translation_service, logger, user_prefs_service=None, parent=None):
        self.categories_gastos    = set()
        self.categories_ganancias = set()
        self.tm                   = translation_service
        self.logger               = logger
        self.supplier_service     = supplier_service
        self.user_prefs_service   = user_prefs_service
        self.current_transactions = []

        super().__init__(property_service, transaction_service, None, parent)

        self.export_service = ExportService()
        self.import_service = ImportService(
            self.transaction_service,
            self.property_service,
            self.supplier_service,
            self.logger
        )

    # ── helper valuta ──────────────────────────────────────────────
    def _currency(self) -> str:
        if self.user_prefs_service:
            return self.user_prefs_service.get_currency()
        return "€"

    def _fmt(self, value: float) -> str:
        """Formatta un importo con la valuta dell'utente."""
        return format_currency(value, symbol=self._currency())

    # ──────────────────────────────────────────────────────────────
    #  SETUP UI
    # ──────────────────────────────────────────────────────────────

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ── Header riga 1: titolo + selettori ─────────────────────
        header_layout = QHBoxLayout()

        title = QLabel(self.tm.get("ETICHETTE", "LE_MIE_TRANSAZIONI"))
        title.setStyleSheet(default_title_style)
        header_layout.addWidget(title)
        header_layout.addStretch()

        property_label = QLabel(f"{self.tm.get('ETICHETTE', 'PROPRIETA')}:")
        property_label.setStyleSheet("color: white;")
        header_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.addItem(self.tm.get("ETICHETTE", "ALL_PROPERTIES"), None)
        for prop in self.property_service.get_all():
            self.property_selector.addItem(prop['name'], prop['id'])
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.currentIndexChanged.connect(self.update_report)
        header_layout.addWidget(self.property_selector)

        month_label = QLabel(f"{self.tm.get('ETICHETTE', 'PERIODO')}:")
        month_label.setStyleSheet("color: white;")
        header_layout.addWidget(month_label)

        self.month_selector = QComboBox()
        self.populate_month_selector()
        self.month_selector.setStyleSheet(default_combo_box_style)
        self.month_selector.currentIndexChanged.connect(self.update_report)
        header_layout.addWidget(self.month_selector)

        header_layout.addSpacing(12)

        add_btn = QPushButton(f"+ {self.tm.get('PULSANTI', 'AGGIUNGI')}")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.clicked.connect(self.add_transaction)
        header_layout.addWidget(add_btn)

        import_btn = QPushButton()
        import_btn.setIcon(QIcon(icon_path("import.png")))
        import_btn.setToolTip(self.tm.get("TOOLTIP", "IMPORTA_DA_EXCEL"))
        import_btn.setStyleSheet(STILE_BOTTONE_ICONA)
        import_btn.clicked.connect(self.import_from_excel)
        header_layout.addWidget(import_btn)

        export_btn = QPushButton()
        export_btn.setIcon(QIcon(icon_path("export.png")))
        export_btn.setToolTip(self.tm.get("TOOLTIP", "ESPORTA"))
        export_btn.setStyleSheet(STILE_BOTTONE_ICONA)
        export_btn.clicked.connect(self.open_export_dialog)
        header_layout.addWidget(export_btn)

        main_layout.addLayout(header_layout)

        # ── Tabelle categorie Spese / Guadagni ─────────────────────
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)

        self.gastos_frame,    self.gastos_table,    self.gastos_total_label    = \
            self._build_category_panel(COLORE_ERROR,   self.tm.get("ETICHETTE", "SPESE"))
        self.ganancias_frame, self.ganancias_table, self.ganancias_total_label = \
            self._build_category_panel(COLORE_SUCCESS, self.tm.get("ETICHETTE", "GUADAGNI"))

        tables_layout.addWidget(self.gastos_frame)
        tables_layout.addWidget(self.ganancias_frame)
        main_layout.addLayout(tables_layout)

        # ── Tabella storico transazioni ────────────────────────────
        transactions_frame = QFrame()
        transactions_frame.setStyleSheet(
            f"background-color: {COLORE_WIDGET_2}; border-radius: 10px;"
        )
        transactions_layout = QVBoxLayout(transactions_frame)
        transactions_layout.setContentsMargins(0, 0, 0, 0)
        transactions_layout.setSpacing(0)

        # Header storico
        # Stesso fondo della scheda, separato dal contenuto da un filo
        trans_header_widget = QFrame()
        trans_header_widget.setObjectName("intestazione")
        trans_header_widget.setStyleSheet(
            f"QFrame#intestazione {{ background: transparent; border: none;"
            f" border-bottom: 1px solid {COLORE_DIVISORE}; }}"
        )
        trans_header_layout = QHBoxLayout(trans_header_widget)
        trans_header_layout.setContentsMargins(20, 10, 20, 10)

        trans_title = QLabel(self.tm.get("ETICHETTE", "STORICO_TRANSAZIONI").upper())
        trans_title.setStyleSheet(
            "font-size: 11px; font-weight: 500; color: #7f8c8d; letter-spacing: 0.06em;"
        )
        trans_header_layout.addWidget(trans_title)
        trans_header_layout.addStretch()

        filter_label = QLabel(self.tm.get("ETICHETTE", "CATEGORIA") + ":")
        filter_label.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        trans_header_layout.addWidget(filter_label)

        self.category_filter = QComboBox()
        self.category_filter.setStyleSheet(default_combo_box_style)
        self.category_filter.currentIndexChanged.connect(self.filter_transactions)
        trans_header_layout.addWidget(self.category_filter)

        transactions_layout.addWidget(trans_header_widget)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.horizontalHeader().setVisible(False)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.setShowGrid(False)
        self.transactions_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.transactions_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORE_WIDGET_2};
                color: {COLORE_BIANCO};
                font-size: 13px;
                border: none;
                border-radius: 0 0 10px 10px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {COLORE_DIVISORE};
            }}
            QTableWidget::item:hover {{ background-color: {tinta(COLORE_ITEM_HOVER, 0.10)}; }}
            QTableWidget::item:selected {{
                background-color: {tinta(COLORE_ITEM_HOVER, 0.18)};
                color: white;
            }}
        """ + stile_scrollbar())
        self.transactions_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        transactions_layout.addWidget(self.transactions_table)

        main_layout.addWidget(transactions_frame, stretch=1)

        self.update_report()

    def _build_category_panel(self, accent_color: str, label: str):
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLORE_WIDGET_2}; border-radius: 10px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header_widget = QFrame()
        header_widget.setObjectName("intestazione")
        header_widget.setStyleSheet(
            f"QFrame#intestazione {{ background: transparent; border: none;"
            f" border-bottom: 1px solid {COLORE_DIVISORE}; }}"
            f"QLabel {{ background: transparent; border: none; }}"
        )
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 14, 20, 14)
        header_layout.setSpacing(12)

        accent_bar = QFrame()
        accent_bar.setFixedSize(4, 36)
        accent_bar.setStyleSheet(
            f"background-color: {accent_color}; border-radius: 2px;"
        )
        header_layout.addWidget(accent_bar)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        lbl_small = QLabel(label.upper())
        lbl_small.setStyleSheet(
            "font-size: 11px; font-weight: 500; color: #7f8c8d; letter-spacing: 0.08em;"
        )
        text_col.addWidget(lbl_small)

        # Il colore lo porta la barra: il totale resta bianco e leggibile
        total_label = QLabel(f"0,00 {self._currency()}")
        total_label.setStyleSheet(
            f"font-size: 22px; font-weight: 600; color: {COLORE_BIANCO};"
        )
        text_col.addWidget(total_label)

        header_layout.addLayout(text_col)
        header_layout.addStretch()
        layout.addWidget(header_widget)

        table = QTableWidget()
        table.setColumnCount(3)
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORE_WIDGET_2};
                color: {COLORE_BIANCO};
                font-size: 13px;
                border: none;
                border-radius: 0 0 10px 10px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 10px 0px;
                border-bottom: 1px solid {COLORE_DIVISORE};
            }}
            QTableWidget::item:selected {{
                background-color: transparent;
                color: white;
            }}
        """ + stile_scrollbar())
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 120)

        layout.addWidget(table)
        return frame, table, total_label

    # ──────────────────────────────────────────────────────────────
    #  AGGIORNAMENTO DATI
    # ──────────────────────────────────────────────────────────────

    def update_report(self):
        selected_month = self.month_selector.currentData()
        if not selected_month:
            return

        year, month = selected_month.split('-')
        last_day   = monthrange(int(year), int(month))[1]
        start_date = f"{year}-{month}-01"
        end_date   = f"{year}-{month}-{last_day}"

        transactions = self.transaction_service.get_all(
            property_id=self.property_selector.currentData(),
            start_date=start_date,
            end_date=end_date
        )
        self.current_transactions = transactions

        self.categories_gastos.clear()
        self.categories_ganancias.clear()
        gastos    = defaultdict(float)
        ganancias = defaultdict(float)

        for trans in transactions:
            category = trans.get('service') or 'Altro'
            amount   = trans['amount']
            if trans['type'] == 'Uscita':
                gastos[category]    += amount
                self.categories_gastos.add(category)
            else:
                ganancias[category] += amount
                self.categories_ganancias.add(category)

        total_gastos    = sum(gastos.values())
        total_ganancias = sum(ganancias.values())

        # Aggiorna totali con simbolo valuta corrente
        self.gastos_total_label.setText(self._fmt(total_gastos))
        self.ganancias_total_label.setText(self._fmt(total_ganancias))

        self.update_category_table(self.gastos_table,    gastos,    COLORE_ERROR,   total_gastos)
        self.update_category_table(self.ganancias_table, ganancias, COLORE_SUCCESS, total_ganancias)

        self.populate_category_filter()
        self.filter_transactions()

    def update_category_table(self, table: QTableWidget, data: dict,
                               accent_color: str, grand_total: float):
        table.clearContents()
        table.setRowCount(0)

        if not data:
            table.setRowCount(1)
            empty = QTableWidgetItem(self.tm.get("MESSAGGI", "NESSUN_DATO"))
            empty.setForeground(QColor("#7f8c8d"))
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(0, 0, empty)
            table.setSpan(0, 0, 1, 3)
            table.setRowHeight(0, 48)
            return

        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        table.setRowCount(len(sorted_data) + 1)

        ROW_H = 42

        for i, (category, amount) in enumerate(sorted_data):
            percentage = (amount / grand_total * 100) if grand_total > 0 else 0

            cat_widget = QWidget()
            cat_layout = QHBoxLayout(cat_widget)
            cat_layout.setContentsMargins(20, 0, 8, 0)
            cat_layout.setSpacing(10)

            # Pallino sempre più tenue scendendo in classifica: colore
            # mescolato con lo sfondo, perché opacity nei QSS non esiste
            dot = QFrame()
            dot.setFixedSize(8, 8)
            quota = max(0.35, 1.0 - i * 0.15)
            dot.setStyleSheet(
                f"background-color: {mescola(accent_color, COLORE_WIDGET_2, quota)}; border-radius: 4px;"
            )
            cat_layout.addWidget(dot)

            cat_lbl = QLabel(category)
            cat_lbl.setStyleSheet(f"color: {COLORE_BIANCO}; font-size: 13px;")
            cat_layout.addWidget(cat_lbl)
            cat_layout.addStretch()

            table.setCellWidget(i, 0, cat_widget)

            # Importo con simbolo valuta corretto
            amount_item = QTableWidgetItem(self._fmt(amount))
            amount_item.setForeground(QColor(COLORE_BIANCO))
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            amount_item.setFont(self._font(table, QFont.Weight.Medium))
            table.setItem(i, 1, amount_item)

            bar_widget = QWidget()
            bar_layout = QHBoxLayout(bar_widget)
            bar_layout.setContentsMargins(8, 0, 16, 0)
            bar_layout.setSpacing(8)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(percentage))
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #334155;
                    border-radius: 2px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background-color: {mescola(accent_color, COLORE_WIDGET_2, 0.85)};
                    border-radius: 2px;
                }}
            """)
            bar_layout.addWidget(bar, stretch=1)

            perc_lbl = QLabel(f"{percentage:.0f}%")
            perc_lbl.setStyleSheet(f"color: {COLORE_TESTO_SECONDARIO}; font-size: 12px;")
            perc_lbl.setFixedWidth(32)
            perc_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bar_layout.addWidget(perc_lbl)

            table.setCellWidget(i, 2, bar_widget)
            table.setRowHeight(i, ROW_H)

        # Riga totale
        tot_row = len(sorted_data)

        tot_widget = QWidget()
        tot_layout = QHBoxLayout(tot_widget)
        tot_layout.setContentsMargins(20, 0, 0, 0)
        tot_lbl = QLabel(self.tm.get("ETICHETTE", "TOTALE") if
                         self.tm.get("ETICHETTE", "TOTALE") != "[ETICHETTE.TOTALE]"
                         else "Totale")
        tot_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        tot_layout.addWidget(tot_lbl)
        table.setCellWidget(tot_row, 0, tot_widget)

        total_item = QTableWidgetItem(self._fmt(grand_total))
        total_item.setForeground(QColor(COLORE_BIANCO))
        total_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        total_item.setFont(self._font(table, QFont.Weight.Bold))
        table.setItem(tot_row, 1, total_item)
        table.setItem(tot_row, 2, QTableWidgetItem(""))
        table.setRowHeight(tot_row, 36)

    # ──────────────────────────────────────────────────────────────
    #  STORICO TRANSAZIONI
    # ──────────────────────────────────────────────────────────────

    def populate_month_selector(self):
        current_date = datetime.now()
        months_list  = self.tm.get("LISTE", "MONTHS_FULL").split(";")

        for i in range(24):
            month = current_date.month - i
            year  = current_date.year
            while month <= 0:
                month += 12
                year  -= 1
            self.month_selector.addItem(
                f"{months_list[month - 1]} {year}",
                f"{year}-{month:02d}"
            )
        self.month_selector.setCurrentIndex(0)

    def populate_category_filter(self):
        self.category_filter.clear()
        self.category_filter.addItem(self.tm.get("ETICHETTE", "TUTTE_LE_CATEGORIE"), None)
        categories = sorted({
            trans.get('service') or 'Altro'
            for trans in self.current_transactions
        })
        for cat in categories:
            self.category_filter.addItem(cat, cat)

    def filter_transactions(self):
        selected_category = self.category_filter.currentData()
        filtered = [
            t for t in self.current_transactions
            if not selected_category or t.get('service') == selected_category
        ]
        filtered.sort(key=lambda x: x['date'], reverse=True)

        self.transactions_table.setRowCount(len(filtered) + 1)

        # Header finto
        headers = [
            self.tm.get("ETICHETTE", "DATA"),
            self.tm.get("ETICHETTE", "IMPORTO"),
            self.tm.get("ETICHETTE", "DESCRIZIONE"),
            self.tm.get("ETICHETTE", "CATEGORIA"),
            self.tm.get("ETICHETTE", "TIPO"),
            ""
        ]
        font_intestazione = self._font(self.transactions_table, QFont.Weight.DemiBold)
        font_intestazione.setPointSizeF(max(7.5, font_intestazione.pointSizeF() - 1))
        for col, text in enumerate(headers):
            item = QTableWidgetItem(text.upper())
            item.setForeground(QColor(COLORE_TESTO_SECONDARIO))
            item.setFont(font_intestazione)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                if col == 2 else Qt.AlignmentFlag.AlignCenter
            )
            self.transactions_table.setItem(0, col, item)
        self.transactions_table.setRowHeight(0, 32)
        self.transactions_table.setColumnWidth(5, 48)

        font_importo = self._font(self.transactions_table, QFont.Weight.Medium)

        for i, trans in enumerate(filtered, start=1):
            is_uscita   = trans['type'] == 'Uscita'
            colore_tipo = COLORE_ERROR if is_uscita else COLORE_SUCCESS

            def _cell(text, align=Qt.AlignmentFlag.AlignCenter, color=COLORE_BIANCO):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(color))
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                return item

            self.transactions_table.setItem(i, 0, _cell(self._data_breve(trans['date'])))

            # Importo neutro con segno: il colore lo porta il badge del tipo
            segno   = "\u2212" if is_uscita else "+"
            importo = _cell(f"{segno} {self._fmt(trans['amount'])}", Qt.AlignmentFlag.AlignRight)
            importo.setFont(font_importo)
            self.transactions_table.setItem(i, 1, importo)

            self.transactions_table.setItem(
                i, 2,
                _cell(trans.get('provider') or trans.get('service', ''),
                      Qt.AlignmentFlag.AlignLeft)
            )
            self.transactions_table.setItem(
                i, 3,
                _cell(trans.get('service') or 'Altro',
                      Qt.AlignmentFlag.AlignLeft, COLORE_TESTO_SECONDARIO)
            )
            self.transactions_table.setCellWidget(i, 4, self._badge_tipo(trans['type'], colore_tipo))

            del_btn = BottoneIcona(
                icona_cestino(COLORE_TESTO_SECONDARIO), icona_cestino(COLORE_ERROR),
                tooltip=self.tm.get("PULSANTI", "ELIMINA"),
            )
            del_btn.setFixedSize(26, 26)
            del_btn.clicked.connect(
                lambda checked=False, t=trans: self.delete_transaction(t)
            )
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            cl = QHBoxLayout(container)
            cl.setContentsMargins(0, 0, 8, 0)
            cl.addStretch()
            cl.addWidget(del_btn)
            self.transactions_table.setCellWidget(i, 5, container)
            self.transactions_table.setRowHeight(i, 40)

    # ── helper di presentazione ────────────────────────────────────
    @staticmethod
    def _font(widget, peso) -> QFont:
        """Font del widget con un peso diverso: QFont("") userebbe una famiglia vuota."""
        f = QFont(widget.font())
        f.setWeight(peso)
        return f

    @staticmethod
    def _data_breve(valore) -> str:
        """dd/MM/yyyy da date o da stringa ISO."""
        if isinstance(valore, date):
            return valore.strftime("%d/%m/%Y")
        try:
            return date.fromisoformat(str(valore)[:10]).strftime("%d/%m/%Y")
        except ValueError:
            return str(valore)

    def _badge_tipo(self, testo: str, colore: str) -> QWidget:
        """Badge discreto: pallino colorato e testo su sfondo tinto."""
        contenitore = QWidget()
        contenitore.setStyleSheet("background: transparent;")
        esterno = QHBoxLayout(contenitore)
        esterno.setContentsMargins(0, 0, 0, 0)
        esterno.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QFrame()
        badge.setStyleSheet(
            f"QFrame {{ background-color: {tinta(colore, 0.14)}; border-radius: 11px; }}"
            f"QLabel {{ background: transparent; color: {COLORE_BIANCO}; font-size: 12px; }}"
        )
        badge.setFixedHeight(22)
        lay = QHBoxLayout(badge)
        lay.setContentsMargins(9, 0, 10, 0)
        lay.setSpacing(6)
        pallino = QLabel()
        pallino.setPixmap(icona_pallino(colore, 7).pixmap(7, 7))
        lay.addWidget(pallino)
        lay.addWidget(QLabel(testo))
        esterno.addWidget(badge)
        return contenitore

    def delete_transaction(self, trans):
        reply = QMessageBox.question(
            self,
            self.tm.get("PULSANTI", "CONFERMA"),
            self.tm.get("MESSAGGI", "ELIMINARE_TRANSAZIONE"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes and self.transaction_service.delete(trans['id']):
            QMessageBox.information(
                self,
                self.tm.get("MESSAGGI", "SUCCESSO"),
                self.tm.get("MESSAGGI", "TRANSAZIONE_ELIMINATA")
            )
            self.update_report()

    # ──────────────────────────────────────────────────────────────
    #  AZIONI
    # ──────────────────────────────────────────────────────────────

    def open_export_dialog(self):
        ExportDialog(
            self.transaction_service,
            self.property_service,
            self.export_service,
            self.tm,
            self
        ).exec()

    def add_transaction(self):
        dialog = TransactionDialogWithSuppliers(
            self.property_service, self.supplier_service, self.tm, self
        )
        if dialog.exec():
            try:
                data     = dialog.get_data()
                amount   = parse_decimal(data["importo"], self.tm.get("ETICHETTE", "IMPORTO"))
                date_obj = datetime.strptime(data["data_fattura"], "%d/%m/%Y").date()

                trans_id = self.transaction_service.create_with_supplier(
                    property_id=data["property_id"],
                    date=date_obj,
                    trans_type=data["tipo"],
                    amount=amount,
                    provider=data["provider"],
                    service=data["service"],
                    supplier_id=data.get("supplier_id")
                )

                if trans_id:
                    QMessageBox.information(
                        self,
                        self.tm.get("MESSAGGI", "TRANSAZIONE_AGGIUNTA"),
                        f"{self.tm.get('ETICHETTE', 'CATEGORIA')}: {data['service']}\n"
                        f"{self.tm.get('ETICHETTE', 'IMPORTO')}: {self._fmt(amount)}"
                    )
                    self.update_report()
                else:
                    QMessageBox.warning(
                        self,
                        self.tm.get("MESSAGGI", "IMPOSSIBILE_SALVARE_TRANSAZIONE"),
                        ""
                    )
            except ValidationError as e:
                QMessageBox.warning(
                    self,
                    self.tm.get("MESSAGGI", "IMPOSSIBILE_SALVARE_TRANSAZIONE"),
                    str(e)
                )

    def import_from_excel(self):
        dialog = ImportDialog(
            self.import_service, self.property_service, self.tm, self
        )
        if dialog.exec():
            self.update_report()
            self.logger.info("Import completato, dati ricaricati")
