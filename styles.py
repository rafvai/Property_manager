########### COLORS ####################
# Schema colori professionale: Dark Blue Corporate
COLORE_BACKGROUND = "#0f1419"           # Nero-blu molto scuro
COLORE_SECONDARIO = "#1a2332"           # Blu scuro
COLORE_TERZIARIO = "#2c3e50"
COLORE_ITEM_SELEZIONATO = "#2563eb"     # Blu corporate
COLORE_ITEM_HOVER = "#3b82f6"           # Blu più chiaro per hover
COLORE_WIDGET_1 = "#ffffff"             # Bianco
COLORE_WIDGET_2 = "#1e293b"             # Slate scuro
COLORE_RIGA_1 = "#334155"               # Slate
COLORE_RIGA_2 = "#475569"               # Slate chiaro
COLORE_BIANCO = "#f8fafc"               # Off-white

# Colori semantici
COLORE_SUCCESS = "#10b981"              # Verde
COLORE_ERROR = "#ef4444"                # Rosso
COLORE_WARNING = "#f59e0b"              # Arancione
COLORE_INFO = "#3b82f6"

########### DIMENSIONS ##################
W_LAT_MENU = 0.20

######## STYLES #######################
default_combo_box_style = f"""
    QComboBox {{
        background-color: {COLORE_SECONDARIO}; 
        padding: 8px 12px; 
        min-height: 20px; 
        border-radius: 6px; 
        color: {COLORE_BIANCO}; 
        font-size: 14px;
        border: 1px solid #334155;
    }}
    QComboBox:hover {{
        border: 1px solid {COLORE_ITEM_HOVER};
    }}
    QComboBox::drop-down {{ 
        border: 0px;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        image: url(icons/down-arrow.png);
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{ 
        background-color: {COLORE_SECONDARIO}; 
        color: {COLORE_BIANCO}; 
        selection-background-color: {COLORE_ITEM_SELEZIONATO}; 
        selection-color: white;
        border: 1px solid #334155;
    }}
"""

default_menu_lat_style = f"""
    QListWidget {{ 
        color: {COLORE_BIANCO}; 
        background-color: {COLORE_BACKGROUND}; 
        padding: 10px; 
        border-radius: 0px;
        border-right: 1px solid #334155;
    }}
    QListWidget::item {{ 
        padding: 12px 10px 12px 20px; 
        font-size: 15px;
        font-weight: 500;
        margin: 2px 0px;
    }}
    QListWidget::item:selected {{ 
        background: {COLORE_ITEM_SELEZIONATO}; 
        border-radius: 6px;
        color: white;
    }}
    QListWidget::item:hover {{
        background: {COLORE_ITEM_HOVER}; 
        border-radius: 6px;
    }}
"""

default_aggiungi_button = f"""
    QPushButton {{
        background-color: {COLORE_ITEM_SELEZIONATO};
        color: white;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {COLORE_ITEM_HOVER};
    }}
    QPushButton:pressed {{
        background-color: #1d4ed8;
    }}
"""

custom_title_style = f"""
    background-color: {COLORE_SECONDARIO}; 
    color: white;
    padding: 10px 15px;
    border-bottom: 1px solid #334155;
"""

default_report_table = f"""
    QTableWidget {{
        color: {COLORE_BIANCO}; 
        background-color: {COLORE_TERZIARIO}; 
        font-size: 13px; 
        gridline-color: #7f8c8d; 
    }}
"""

default_button_main_header = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {COLORE_BIANCO};
            font-weight: normal;
            font-size: 16px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
"""

default_selector_date_export = f"""
        QDateEdit {{
        background-color: #1a2530;
        color: {COLORE_BIANCO};
        padding: 8px;
        border-radius: 6px;
    }}
"""

default_export_button = f"""
        QPushButton {{
        background-color: #28a745;
        color: {COLORE_BIANCO};
        font-weight: bold;
        font-size 14px;
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
    }}
    QPushButton:hover {{
        background-color: #218838;
    }}
"""

default_dialog_style = f"""
            QDialog {{
                background-color: {COLORE_BACKGROUND};
            }}
            QLabel {{
                color: white;
                font-size: 13px;
                background-color: transparent;
            }}
            QLineEdit, QTextEdit {{
                background-color: {COLORE_WIDGET_2};
                color: #94a3b8;
                border: 2px solid #334155;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                selection-background-color: {COLORE_ITEM_SELEZIONATO};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
                color: white;
            }}
            QDateEdit, QComboBox {{
                background-color: {COLORE_WIDGET_2};
                color: #94a3b8;
                border: 2px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QDateEdit:focus, QComboBox:focus {{
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
                color: white;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: url(icons/down-arrow.png);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                selection-background-color: {COLORE_ITEM_SELEZIONATO};
                border: 1px solid #334155;
            }}
            QPushButton {{
                background-color: {COLORE_ITEM_SELEZIONATO};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #1d4ed8;
            }}
            QPushButton[text="Cancel"], QPushButton[text="Annulla"], QPushButton[text="Cancelar"] {{
                background-color: transparent;
                border: 1px solid #334155;
            }}
            QPushButton[text="Cancel"]:hover, QPushButton[text="Annulla"]:hover, QPushButton[text="Cancelar"]:hover {{
                background-color: {COLORE_WIDGET_2};
                border: 1px solid {COLORE_ITEM_SELEZIONATO};
            }}
        """

