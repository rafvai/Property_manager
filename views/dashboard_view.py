from datetime import datetime, timedelta

import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from styles import (
    COLORE_BIANCO,
    COLORE_GRIGIO,
    COLORE_ITEM_SELEZIONATO,
    COLORE_WIDGET_2,
    default_combo_box_style,
    default_dashboard_widget,
    default_style_text,
    default_title_style,
)
from validation_utils import format_currency
from views.base_view import BaseView


class ClickableFrame(QFrame):
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

    def __init__(self, property_service, transaction_service, deadline_service,
                 preferences_service, main_window, translation_manager, logger,
                 user_prefs_service=None, parent=None):
        self.logger              = logger
        self.deadline_service    = deadline_service
        self.main_window         = main_window
        self.preferences_service = preferences_service
        self.tm                  = translation_manager
        self.user_prefs_service  = user_prefs_service

        self.proprieta         = property_service.get_all()
        self.selected_property = None

        self._saved_property_index = 0
        self._saved_period_index   = 0

        super().__init__(property_service, transaction_service, None, parent)

    # ──────────────────────────────────────────────────────────────
    #  Helpers preferenze
    # ──────────────────────────────────────────────────────────────

    def _currency(self) -> str:
        if self.user_prefs_service:
            return self.user_prefs_service.get_currency()
        return "€"

    def _fmt(self, value: float) -> str:
        return format_currency(value, symbol=self._currency())

    def _warning_days(self) -> int:
        """
        Giorni di preavviso scadenze letti dal DB.
        Default 7 se non impostato o user_prefs_service non disponibile.
        """
        if self.user_prefs_service:
            return self.user_prefs_service.get_deadline_warning_days()
        return 7

    # ──────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────

    def setup_ui(self):
        layout = self.layout()
        if layout is not None:
            self.clear_layout(layout)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(30, 30, 30, 30)
            layout.setSpacing(25)

        # ========== HEADER ========== #
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        prop_widget = QWidget()
        prop_layout = QVBoxLayout(prop_widget)
        prop_layout.setContentsMargins(0, 0, 0, 0)

        label_select = QLabel(self.tm.get("ETICHETTE", "SELEZIONA_PROPRIETA"))
        label_select.setStyleSheet(default_style_text)
        prop_layout.addWidget(label_select)

        self.property_selector = QComboBox()
        self.property_selector.addItem(self.tm.get("ETICHETTE", "ALL_PROPERTIES"), None)
        for p in self.proprieta:
            self.property_selector.addItem(p["name"], p["id"])
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        self.property_selector.setCurrentIndex(self._saved_property_index)
        self.property_selector.currentIndexChanged.connect(self.update_info_box)
        prop_layout.addWidget(self.property_selector)

        top_row.addWidget(prop_widget, stretch=3)
        top_row.addStretch()

        # Cambio lingua
        lang_container = QWidget()
        lang_layout    = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(5)

        self.language_combo = QComboBox()
        self.language_combo.addItem(QIcon("icons/flag-it.png"), "Italiano", "it")
        self.language_combo.addItem(QIcon("icons/flag-uk.png"), "English",  "en")
        self.language_combo.addItem(QIcon("icons/flag-es.png"), "Español",  "es")
        self.language_combo.setIconSize(QSize(20, 20))
        self.language_combo.setFixedWidth(150)

        current_lang = self.preferences_service.get_language()
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.language_combo)
        top_row.addWidget(lang_container)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)

        label_title = QLabel(self.tm.get("ETICHETTE", "PANORAMICA"))
        label_title.setStyleSheet(default_title_style)
        mid_row.addWidget(label_title)
        mid_row.addStretch()

        label_periodo = QLabel(self.tm.get("ETICHETTE", "PERIODO") + ":")
        label_periodo.setStyleSheet("color: white;")
        mid_row.addWidget(label_periodo)

        self.period_selector = QComboBox()
        self.period_selector.setStyleSheet(default_combo_box_style)
        self.period_selector.addItems([
            self.tm.get("ETICHETTE", "1_MONTH"),
            self.tm.get("ETICHETTE", "6_MONTHS"),
            self.tm.get("ETICHETTE", "1_YEAR"),
            self.tm.get("ETICHETTE", "3_YEARS"),
        ])
        self.period_selector.setCurrentIndex(self._saved_period_index)
        self.period_selector.currentIndexChanged.connect(self.update_chart)
        mid_row.addWidget(self.period_selector)

        header_layout.addLayout(top_row)
        header_layout.addLayout(mid_row)
        layout.addLayout(header_layout)

        # ========== SEZIONE CENTRALE ========== #
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(25)

        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # Info proprietà
        info_frame = ClickableFrame(
            on_click=lambda: self.main_window.navigate_to_section("PROPERTIES")
        )
        info_frame.setStyleSheet(default_dashboard_widget)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)

        info_title = QLabel(self.tm.get("ETICHETTE", "INFORMAZIONI_PROPRIETA"))
        info_title.setStyleSheet(default_style_text)
        info_layout.addWidget(info_title)

        self.info_name    = QLabel()
        self.info_address = QLabel()
        self.info_owner   = QLabel()
        for lbl in (self.info_name, self.info_address, self.info_owner):
            lbl.setStyleSheet(default_style_text)
        self.update_info_display()
        info_layout.addWidget(self.info_name)
        info_layout.addWidget(self.info_address)
        info_layout.addWidget(self.info_owner)
        info_layout.addStretch()

        # Prossima scadenza
        deadline_frame = ClickableFrame(
            on_click=lambda: self.main_window.navigate_to_section("CALENDAR")
        )
        deadline_frame.setStyleSheet(default_dashboard_widget)
        deadline_layout = QVBoxLayout(deadline_frame)
        deadline_layout.setSpacing(8)

        deadline_title_label = QLabel(self.tm.get("ETICHETTE", "PROSSIMA_SCADENZA"))
        deadline_title_label.setStyleSheet(default_style_text)
        deadline_layout.addWidget(deadline_title_label)

        self.deadline_title_label = QLabel()
        self.deadline_date_label  = QLabel()
        self.deadline_desc_label  = QLabel()
        self.deadline_title_label.setStyleSheet(default_style_text)
        self.deadline_date_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.deadline_desc_label.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        self.deadline_desc_label.setWordWrap(True)
        deadline_layout.addWidget(self.deadline_title_label)
        deadline_layout.addWidget(self.deadline_date_label)
        deadline_layout.addWidget(self.deadline_desc_label)
        deadline_layout.addStretch()

        left_column.addWidget(info_frame, stretch=1)
        left_column.addWidget(deadline_frame, stretch=1)

        # Grafico donut
        chart_frame = ClickableFrame(
            on_click=lambda: self.main_window.navigate_to_section("FINANZE")
        )
        chart_frame.setStyleSheet(default_dashboard_widget)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setSpacing(10)

        self.fig = Figure(figsize=(4, 4), facecolor=COLORE_WIDGET_2)
        self.chart_canvas = FigureCanvas(self.fig)
        self.chart_canvas.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.ax = self.fig.add_subplot(111, facecolor=COLORE_WIDGET_2)
        chart_layout.addWidget(self.chart_canvas)

        middle_layout.addLayout(left_column, 2)
        middle_layout.addWidget(chart_frame, 3)
        layout.addLayout(middle_layout)

        # Bottom
        bottom_frame = ClickableFrame(
            on_click=lambda: self.main_window.navigate_to_section("DOCUMENTS")
        )
        bottom_frame.setStyleSheet(default_dashboard_widget)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_label  = QLabel(self.tm.get("ETICHETTE", "DOCUMENTS"))
        bottom_label.setStyleSheet("color: white; font-size: 14px;")
        bottom_layout.addWidget(bottom_label)
        layout.addWidget(bottom_frame)

        self.update_chart()
        self.update_next_deadline()

    # ──────────────────────────────────────────────────────────────
    #  Lingua
    # ──────────────────────────────────────────────────────────────

    def on_language_changed(self):
        self.change_language(self.language_combo.currentData())

    def change_language(self, lang_code):
        self._saved_property_index = self.property_selector.currentIndex()
        self._saved_period_index   = self.period_selector.currentIndex()
        self.preferences_service.set_language(lang_code)
        self.tm.set_language(lang_code)

        if hasattr(self.main_window, 'menu'):
            self.main_window.menu.blockSignals(True)
        if hasattr(self.main_window, 'update_menu_items'):
            self.main_window.update_menu_items()
            self.main_window.menu.setCurrentRow(0)
        if hasattr(self.main_window, 'menu'):
            self.main_window.menu.blockSignals(False)

        self.proprieta = self.property_service.get_all()
        self.setup_ui()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item   = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())

    # ──────────────────────────────────────────────────────────────
    #  Info proprietà
    # ──────────────────────────────────────────────────────────────

    def update_info_display(self):
        if not self.proprieta:
            self.info_name.setText(
                self.tm.get("ETICHETTE", "NESSUNA_PROPRIETA_TROVATA")
            )
            self.info_address.setText("")
            self.info_owner.setText("")
        elif self.selected_property is None:
            num_prop = len(self.proprieta)
            self.info_name.setText(
                f"🏡 {num_prop} {self.tm.get('ETICHETTE', 'PROPRIETA_TOTALI')}"
            )
            self.info_address.setText("")
            self.info_owner.setText("")
        else:
            p = self.selected_property
            self.info_name.setText(f"🏡 {p['name']}")
            self.info_address.setText(f"📍 {p['address']}")

            # Riga extra: gestita da / mq / classe energetica
            extras = []
            if p.get('managed_by'):
                extras.append(f"🏢 {p['managed_by']}")
            if p.get('square_meters'):
                sqm = p['square_meters']
                sqm_str = str(int(sqm)) if sqm == int(sqm) else str(sqm)
                extras.append(f"📐 {sqm_str} m²")
            if p.get('energy_class'):
                extras.append(f"⚡ {p['energy_class']}")
            self.info_owner.setText("  ·  ".join(extras) if extras else "")

    # ──────────────────────────────────────────────────────────────
    #  Prossima scadenza — usa warning_days dal DB
    # ──────────────────────────────────────────────────────────────

    def update_next_deadline(self):
        """
        Aggiorna il widget della prossima scadenza.

        Logica colori basata su warning_days letto dal DB:
          - Scaduta (days_left < 0)      → rosso    🔴
          - Oggi (days_left == 0)        → rosso    🔴
          - Entro warning_days giorni    → arancione 🟠  ← preferenza utente dal DB
          - Oltre warning_days giorni    → verde    🟢
        """
        property_id   = self.selected_property["id"] if self.selected_property else None
        next_deadline = self.deadline_service.get_next_deadline(property_id)
        warning_days  = self._warning_days()   # ← letto dal DB

        if not next_deadline:
            self.deadline_title_label.setText(
                self.tm.get("ETICHETTE", "NESSUNA_SCADENZA")
            )
            self.deadline_date_label.setStyleSheet(
                "color: #2ecc71; font-size: 12px;"
            )
            self.deadline_date_label.setText("")
            self.deadline_desc_label.setText("")
            return

        self.deadline_title_label.setText(f"📌 {next_deadline['title']}")

        due_date  = datetime.strptime(next_deadline['due_date'], "%Y-%m-%d")
        days_left = (due_date - datetime.now()).days

        if days_left < 0:
            # Scaduta
            date_text = f"⚠️ Scaduta {abs(days_left)} giorni fa"
            color     = "#e74c3c"   # rosso
            weight    = "bold"
        elif days_left == 0:
            # Oggi
            date_text = self.tm.get("ETICHETTE", "OGGI")
            color     = "#e74c3c"   # rosso
            weight    = "bold"
        elif days_left <= warning_days:
            # Imminente: entro la finestra di preavviso scelta dall'utente
            if days_left == 1:
                date_text = self.tm.get("ETICHETTE", "DOMANI")
            else:
                date_text = (
                    self.tm.get("ETICHETTE", "IN_X_GIORNI")
                    .replace('XXX', str(days_left))
                )
            color  = "#f59e0b"  # arancione COLORE_WARNING
            weight = "bold"
        else:
            # Scadenza lontana, tutto ok
            date_text = (
                self.tm.get("ETICHETTE", "IN_X_GIORNI")
                .replace('XXX', str(days_left))
            )
            color  = "#2ecc71"  # verde
            weight = "normal"

        self.deadline_date_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: {weight};"
        )
        self.deadline_date_label.setText(
            f"{date_text} - {due_date.strftime('%d/%m/%Y')}"
        )
        self.deadline_desc_label.setText(
            next_deadline.get('description')
            or self.tm.get("ETICHETTE", "NESSUNA_DESCRIZIONE")
        )

    # ──────────────────────────────────────────────────────────────
    #  Grafico donut
    # ──────────────────────────────────────────────────────────────

    def update_chart(self):
        self._saved_period_index = self.period_selector.currentIndex()
        text = self.period_selector.currentText()

        period_map = {
            self.tm.get("ETICHETTE", "1_MONTH"):  1,
            self.tm.get("ETICHETTE", "6_MONTHS"): 6,
            self.tm.get("ETICHETTE", "1_YEAR"):   12,
            self.tm.get("ETICHETTE", "3_YEARS"):  36,
        }
        mesi       = period_map.get(text, 1)
        end_date   = datetime.today()
        start_date = end_date - timedelta(days=30 * mesi)

        property_id = self.selected_property["id"] if self.selected_property else None
        rows    = self.transaction_service.get_all(
            property_id=property_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )
        entrate = sum(t["amount"] for t in rows if t["type"] == "Entrata")
        uscite  = sum(t["amount"] for t in rows if t["type"] == "Uscita")

        self.ax.clear()
        sizes  = [entrate, uscite]
        colors = [COLORE_ITEM_SELEZIONATO, COLORE_GRIGIO]

        if sum(sizes) == 0:
            self.ax.pie([1], colors=[COLORE_GRIGIO], startangle=90,
                        wedgeprops=dict(width=0.4))
            self.ax.text(0, 0, self.tm.get("MESSAGGI", "NESSUN_DATO"),
                         ha="center", va="center", fontsize=14, color=COLORE_GRIGIO)
        else:
            self.ax.pie(sizes, colors=colors, startangle=90,
                        wedgeprops=dict(width=0.4))
            self.ax.text(0, 0, self._fmt(entrate - uscite),
                         ha='center', va='center',
                         fontsize=14, fontweight='bold', color=COLORE_BIANCO)

            labels      = [self.tm.get("ETICHETTE", "GUADAGNI"),
                           self.tm.get("ETICHETTE", "SPESE")]
            perc        = [f"{sizes[0] / sum(sizes) * 100:.0f}%",
                           f"{sizes[1] / sum(sizes) * 100:.0f}%"]
            x_positions = [-1.2, 1.1]
            y_text      = -1.5
            dot_offset  = -0.25
            dot_size    = 0.1

            for label, p, x, c in zip(labels, perc, x_positions, colors, strict=False):
                self.ax.add_patch(mpatches.Circle(
                    (x + dot_offset, y_text), dot_size, color=c,
                    transform=self.ax.transData, clip_on=False)
                )
                self.ax.text(x, y_text, f"{label} {p}",
                             ha='left', va='center',
                             color=COLORE_BIANCO, fontsize=10)
            self.ax.set_aspect('equal')

        centre_circle = mpatches.Circle((0, 0), 0.70, fc=COLORE_WIDGET_2)
        self.ax.add_artist(centre_circle)
        self.ax.set_title(self.tm.get("ETICHETTE", "SALDO"), color=COLORE_BIANCO, y=1)
        self.chart_canvas.draw()

    # ──────────────────────────────────────────────────────────────
    #  Selezione proprietà
    # ──────────────────────────────────────────────────────────────

    def update_info_box(self, index):
        self._saved_property_index = index
        if index == 0:
            self.selected_property = None
        elif 0 < index <= len(self.proprieta):
            self.selected_property = self.proprieta[index - 1]

        self.update_info_display()
        self.update_chart()
        self.update_next_deadline()
