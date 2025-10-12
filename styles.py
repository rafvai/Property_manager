
########### COLORS ####################
COLORE_BACKGROUND = "#131b23"
COLORE_SECONDARIO = "#1a2530"
COLORE_ITEM_SELEZIONATO = "#1e7be7"
COLORE_ITEM_HOVER = "#539fec"
COLORE_WIDGET_1 = "#FFFDF8"
COLORE_WIDGET_2 = "#1a2530"
COLORE_RIGA_1 = "#D0D0D0"
COLORE_RIGA_2 = "#F0F0F0"

########### DIMENSIONS ##################
W_LAT_MENU = 0.25

######## STYLES #######################
default_combo_box_style = f"""
    QComboBox {{background-color: {COLORE_SECONDARIO}; padding: 4px 8px; min-height: 24px; border-radius: 5px; color: white; font-size: 14px;}}
    QComboBox::drop-down {{ border: 0px;}}
    QComboBox QAbstractItemView {{ background-color: {COLORE_SECONDARIO}; color: white; selection-background-color: #007BFF; selection-color: white;}}
    """

default_menu_lat_style = f"""
    QListWidget {{ color: white; background-color: {COLORE_BACKGROUND}; padding: 10px; border-radius: 5px;}}
    QListWidget::item {{ padding: 10px 10px 10px 20px; font-size: 20px; }}
    QListWidget::item:selected {{ background:{COLORE_ITEM_SELEZIONATO}; border-radius: 8px;}}
    QListWidget::item:hover {{background: {COLORE_ITEM_HOVER}; border-radius: 8px;}}
    """

default_aggiungi_button = """
            QPushButton {
                background-color: #007BFF;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """
