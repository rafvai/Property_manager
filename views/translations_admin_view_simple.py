# ============================================
# ADMIN PANEL TRADUZIONI SEMPLIFICATO
# Tabella con: category, key, it, en, es
# ============================================

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFrame, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QWidget,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from views.base_view import BaseView
from styles import *


class TranslationEditorDialog(QDialog):
    """Dialog per aggiungere/modificare traduzione"""
    
    def __init__(self, translation_db, mode='add', data=None, parent=None):
        super().__init__(parent)
        self.translation_db = translation_db
        self.mode = mode
        self.data = data or {}
        
        self.setWindowTitle("Nuova Traduzione" if mode == 'add' else "Modifica Traduzione")
        self.setMinimumWidth(500)
        self.setStyleSheet(default_dialog_style)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Costruisce interfaccia"""
        layout = QFormLayout(self)
        
        # Categoria
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            'ETICHETTE', 'PULSANTI', 'MESSAGGI', 'PLACEHOLDER', 
            'TOOLTIP', 'MENU', 'VALIDAZIONE', 'ERRORI', 'DIALOGHI', 'TABELLE'
        ])
        if self.mode == 'edit' and self.data.get('category'):
            self.category_combo.setCurrentText(self.data['category'])
        layout.addRow("Categoria*:", self.category_combo)
        
        # Chiave
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Es: FORNITORE, NUOVA_PROPRIETÀ")
        if self.mode == 'edit' and self.data.get('key'):
            self.key_input.setText(self.data['key'])
            self.key_input.setReadOnly(True)  # Non modificabile in edit
        layout.addRow("Chiave*:", self.key_input)
        
        # Italiano
        self.it_input = QLineEdit()
        self.it_input.setPlaceholderText("Es: Fornitore")
        if self.mode == 'edit' and self.data.get('it'):
            self.it_input.setText(self.data['it'])
        layout.addRow("🇮🇹 Italiano:", self.it_input)
        
        # English
        self.en_input = QLineEdit()
        self.en_input.setPlaceholderText("Es: Supplier")
        if self.mode == 'edit' and self.data.get('en'):
            self.en_input.setText(self.data['en'])
        layout.addRow("🇬🇧 English:", self.en_input)
        
        # Español
        self.es_input = QLineEdit()
        self.es_input.setPlaceholderText("Es: Proveedor")
        if self.mode == 'edit' and self.data.get('es'):
            self.es_input.setText(self.data['es'])
        layout.addRow("🇪🇸 Español:", self.es_input)
        
        # Bottoni
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
    
    def get_data(self):
        """Ritorna dati traduzione"""
        return {
            'category': self.category_combo.currentText().strip().upper(),
            'key': self.key_input.text().strip().upper(),
            'it': self.it_input.text().strip() or None,
            'en': self.en_input.text().strip() or None,
            'es': self.es_input.text().strip() or None
        }
    
    def accept(self):
        """Validazione prima di accettare"""
        data = self.get_data()
        
        if not data['category'] or not data['key']:
            QMessageBox.warning(
                self,
                "⚠️ Validazione",
                "Categoria e Chiave sono obbligatori"
            )
            return
        
        if not data['it'] and not data['en'] and not data['es']:
            QMessageBox.warning(
                self,
                "⚠️ Validazione",
                "Inserire almeno una traduzione (IT, EN o ES)"
            )
            return
        
        super().accept()


class TranslationsAdminView(BaseView):
    """View amministrazione traduzioni"""
    
    def __init__(self, translation_manager, logger, parent=None):
        self.tm = translation_manager
        self.translation_db = translation_manager.db
        self.logger = logger
        self.current_category = None
        
        super().__init__(None, None, None, parent)
    
    def setup_ui(self):
        """Costruisce interfaccia"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # HEADER
        header_layout = QHBoxLayout()
        
        title = QLabel("🌐 Gestione Traduzioni")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Bottone aggiungi
        add_btn = QPushButton("➕ Nuova Traduzione")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_translation)
        header_layout.addWidget(add_btn)
        
        main_layout.addLayout(header_layout)
        
        # FILTRI
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(15)
        
        # Categoria
        cat_label = QLabel("Categoria:")
        cat_label.setStyleSheet("color: white; font-size: 14px;")
        filters_layout.addWidget(cat_label)
        
        self.category_selector = QComboBox()
        self.category_selector.setStyleSheet(default_combo_box_style)
        self.populate_categories()
        self.category_selector.currentTextChanged.connect(self.filter_by_category)
        filters_layout.addWidget(self.category_selector)
        
        filters_layout.addStretch()
        
        # Ricerca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cerca...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 300px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
            }}
        """)
        self.search_input.textChanged.connect(self.search_translations)
        filters_layout.addWidget(self.search_input)
        
        main_layout.addLayout(filters_layout)
        
        # STATISTICHE
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_WIDGET_2};
                border-radius: 10px;
                padding: 12px 20px;
            }}
        """)
        stats_layout = QHBoxLayout(stats_frame)
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #bdc3c7; font-size: 13px;")
        stats_layout.addWidget(self.stats_label)
        
        main_layout.addWidget(stats_frame)
        
        # TABELLA TRADUZIONI
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Categoria', 'Chiave', '🇮🇹 Italiano', '🇬🇧 English', '🇪🇸 Español', 'Azioni'
        ])
        
        # Stile tabella
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORE_WIDGET_2};
                border: none;
                border-radius: 8px;
                gridline-color: {COLORE_SECONDARIO};
            }}
            QTableWidget::item {{
                color: white;
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORE_ITEM_SELEZIONATO};
            }}
            QHeaderView::section {{
                background-color: {COLORE_SECONDARIO};
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        # Dimensioni colonne
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 120)
        
        # Selezione
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        main_layout.addWidget(self.table)
        
        self.load_translations()
    
    def populate_categories(self):
        """Popola selettore categorie"""
        self.category_selector.clear()
        self.category_selector.addItem("Tutte le categorie", None)
        
        categories = self.translation_db.get_all_categories()
        for cat in categories:
            self.category_selector.addItem(cat, cat)
    
    def update_stats(self, count):
        """Aggiorna statistiche"""
        stats = self.translation_db.get_statistics()
        
        total = stats['total']
        missing_it = stats['missing']['it']
        missing_en = stats['missing']['en']
        missing_es = stats['missing']['es']
        
        filter_text = f" • Filtrate: {count}" if self.current_category or self.search_input.text() else ""
        
        self.stats_label.setText(
            f"📊 {total} traduzioni totali{filter_text} • "
            f"Mancanti: 🇮🇹 {missing_it} • 🇬🇧 {missing_en} • 🇪🇸 {missing_es}"
        )
    
    def load_translations(self, search_text=""):
        """Carica traduzioni nella tabella"""
        self.table.setRowCount(0)
        
        # Carica traduzioni
        if search_text:
            translations = self.translation_db.search(search_text)
        elif self.current_category:
            translations = self.translation_db.get_by_category(self.current_category)
        else:
            translations = self.translation_db.get_all()
        
        self.update_stats(len(translations))
        
        # Popola tabella
        for row_idx, trans in enumerate(translations):
            self.table.insertRow(row_idx)
            
            # Categoria
            cat_item = QTableWidgetItem(trans['category'])
            cat_item.setForeground(QColor('#3498db'))
            self.table.setItem(row_idx, 0, cat_item)
            
            # Chiave
            key_item = QTableWidgetItem(trans['key'])
            key_item.setForeground(QColor('#f39c12'))
            self.table.setItem(row_idx, 1, key_item)
            
            # Italiano
            it_item = QTableWidgetItem(trans['it'] or "")
            if not trans['it']:
                it_item.setForeground(QColor('#e74c3c'))
            self.table.setItem(row_idx, 2, it_item)
            
            # English
            en_item = QTableWidgetItem(trans['en'] or "")
            if not trans['en']:
                en_item.setForeground(QColor('#e74c3c'))
            self.table.setItem(row_idx, 3, en_item)
            
            # Español
            es_item = QTableWidgetItem(trans['es'] or "")
            if not trans['es']:
                es_item.setForeground(QColor('#e74c3c'))
            self.table.setItem(row_idx, 4, es_item)
            
            # Bottoni azioni
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 5, 0)
            actions_layout.setSpacing(5)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #2980b9; }
            """)
            edit_btn.clicked.connect(
                lambda checked, t=trans: self.edit_translation(t)
            )
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORE_ERROR};
                    color: white;
                    border: none;
                    border-radius: 5px;
                }}
                QPushButton:hover {{ background-color: #c0392b; }}
            """)
            delete_btn.clicked.connect(
                lambda checked, t=trans: self.delete_translation(t)
            )
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row_idx, 5, actions_widget)
    
    def filter_by_category(self, index):
        """Filtra per categoria"""
        self.current_category = self.category_selector.currentData()
        self.search_input.clear()
        self.load_translations()
    
    def search_translations(self, text):
        """Cerca traduzioni"""
        self.load_translations(search_text=text)
    
    def add_translation(self):
        """Dialog nuova traduzione"""
        dialog = TranslationEditorDialog(self.translation_db, mode='add', parent=self)
        
        if dialog.exec():
            data = dialog.get_data()
            
            success = self.translation_db.set_translation(
                data['category'],
                data['key'],
                data['it'],
                data['en'],
                data['es']
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "✅ Successo",
                    f"Traduzione aggiunta: {data['category']}.{data['key']}"
                )
                self.tm.reload()  # Ricarica cache
                self.populate_categories()
                self.load_translations()
            else:
                QMessageBox.warning(
                    self,
                    "❌ Errore",
                    "Impossibile aggiungere la traduzione"
                )
    
    def edit_translation(self, trans):
        """Dialog modifica traduzione"""
        dialog = TranslationEditorDialog(
            self.translation_db, 
            mode='edit', 
            data=trans, 
            parent=self
        )
        
        if dialog.exec():
            new_data = dialog.get_data()
            
            success = self.translation_db.set_translation(
                new_data['category'],
                new_data['key'],
                new_data['it'],
                new_data['en'],
                new_data['es']
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "✅ Successo",
                    "Traduzione aggiornata!"
                )
                self.tm.reload()
                self.load_translations()
            else:
                QMessageBox.warning(
                    self,
                    "❌ Errore",
                    "Impossibile aggiornare"
                )
    
    def delete_translation(self, trans):
        """Elimina traduzione"""
        reply = QMessageBox.question(
            self,
            "Conferma",
            f"Eliminare traduzione '{trans['category']}.{trans['key']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.translation_db.delete_translation(
                trans['category'], 
                trans['key']
            )
            
            if success:
                QMessageBox.information(self, "✅ Successo", "Traduzione eliminata!")
                self.tm.reload()
                self.load_translations()
            else:
                QMessageBox.warning(self, "❌ Errore", "Impossibile eliminare")
