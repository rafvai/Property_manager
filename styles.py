
########### COLORS ####################
COLORE_BACKGROUND = "#06101c"
COLORE_ITEM_SELEZIONATO = "#1e7be7"
COLORE_ITEM_HOVER = "#539fec"
COLORE_WIDGET_1 = "#FFFDF8"
COLORE_WIDGET_2 = "#7BAE7F"
COLORE_RIGA_1 = "#D0D0D0"
COLORE_RIGA_2 = "#F0F0F0"

########### DIMENSIONS ##################
W_LAT_MENU = 0.25


######## STYLES #######################
default_combo_box_style = """
    QComboBox {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        color: black;
        font-size: 14px;
    }
    QComboBox::drop-down {
        border: 0px;
    }
    QComboBox QAbstractItemView {
        background-color: black;
        color: white;
        selection-background-color: #007BFF;
        selection-color: white;
    }
"""
default_menu_lat_style = f"""
    QListWidget {{ color: white; background-color: {COLORE_BACKGROUND}; padding: 10px; border-radius: 5px;}}
    QListWidget::item {{ padding: 10px 10px 10px 20px; font-size: 20px; }}
    QListWidget::item:selected {{ background:{COLORE_ITEM_SELEZIONATO}; border-radius: 8px;}}
    QListWidget::item:hover {{background: {COLORE_ITEM_HOVER}; border-radius: 8px;}}
    """
