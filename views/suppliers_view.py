from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFrame, QScrollArea, QWidget, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QMessageBox, QTextEdit,
    QListWidget, QListWidgetItem, QFileDialog, QSpinBox, QTabWidget
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QColor, QDesktopServices, QIcon

from views.base_view import BaseView
from styles import *
from translations_manager import get_translation_manager
from validation_utils import validate_required_text, ValidationError
import os
from datetime import datetime


class StarRatingWidget(QWidget):
    """Widget per visualizzare/selezionare rating con stelle"""
    
    def __init__(self, rating=0, editable=False, parent=None):
        super().__init__(parent)
        self.rating = rating
        self.editable = editable
        self.hovered_star = -1
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.star_labels = []
        for i in range(5):
            label = QLabel()
            label.setFixedSize(20, 20)
            if editable:
                label.setCursor(Qt.CursorShape.PointingHandCursor)
                label.mousePressEvent = lambda e, star=i: self.set_rating(star + 1)
                label.enterEvent = lambda e, star=i: self.hover_star(star)
                label.leaveEvent = lambda e: self.hover_star(-1)
            
            self.star_labels.append(label)
            layout.addWidget(label)
        
        self.update_stars()
    
    def set_rating(self, rating):
        """Imposta il rating"""
        self.rating = rating
        self.update_stars()
    
    def hover_star(self, star):
        """Gestisce hover sulle stelle"""
        if self.editable:
            self.hovered_star = star
            self.update_stars()
    
    def update_stars(self):
        """Aggiorna visualizzazione stelle"""
        display_rating = self.hovered_star + 1 if self.hovered_star >= 0 else self.rating
        
        for i, label in enumerate(self.star_labels):
            if i < display_rating:
                label.setText("⭐")
            else:
                label.setText("☆")
            label.setStyleSheet("font-size: 18px; background: transparent;")
    
    def get_rating(self):
        """Ritorna il rating corrente"""
        return self.rating


class SupplierCard(QFrame):
    """Card fornitore con statistiche avanzate"""

    def __init__(self, supplier, on_edit, on_delete, on_view_details, index, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_view_details = on_view_details

        bg_color = COLORE_RIGA_1 if index % 2 == 0 else COLORE_RIGA_2

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 15px 20px;
            }}
            QFrame:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def mousePressEvent(self, event):
        """Click sulla card apre i dettagli"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_view_details(self.supplier)
        super().mousePressEvent(event)

    def setup_ui(self):
        """Costruisce l'interfaccia della card"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # RIGA 1: Nome, Rating e Azioni
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        name_label = QLabel(f"🏢 {self.supplier['name']}")
        name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        top_row.addWidget(name_label)

        # Rating stelle
        if self.supplier.get('avg_rating', 0) > 0:
            stars = StarRatingWidget(int(self.supplier['avg_rating']))
            top_row.addWidget(stars)
            
            rating_text = QLabel(f"({self.supplier['avg_rating']}/5)")
            rating_text.setStyleSheet("color: #f39c12; font-size: 11px; font-weight: bold;")
            top_row.addWidget(rating_text)
            
            if self.supplier.get('review_count', 0) > 0:
                review_count = QLabel(f"{self.supplier['review_count']} recensioni")
                review_count.setStyleSheet("color: #95a5a6; font-size: 10px;")
                top_row.addWidget(review_count)

        # Badge proprietà
        if self.supplier.get('property_name'):
            property_badge = QLabel(f"🏠 {self.supplier['property_name']}")
            property_badge.setStyleSheet(f"""
                background-color: {COLORE_ITEM_SELEZIONATO};
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            """)
            top_row.addWidget(property_badge)

        top_row.addStretch()

        # Bottoni
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        edit_btn.clicked.connect(lambda: self.on_edit(self.supplier))
        edit_btn.mousePressEvent = lambda e: (e.accept(), edit_btn.clicked.emit())
        top_row.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ERROR};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        delete_btn.clicked.connect(lambda: self.on_delete(self.supplier))
        delete_btn.mousePressEvent = lambda e: (e.accept(), delete_btn.clicked.emit())
        top_row.addWidget(delete_btn)

        layout.addLayout(top_row)

        # RIGA 2: Categoria e Statistiche
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        category_label = QLabel(f"📂 {self.supplier['category']}")
        category_label.setStyleSheet("color: #95a5a6; font-size: 12px; font-weight: 600;")
        stats_row.addWidget(category_label)

        # Ultimo servizio
        if self.supplier.get('last_service_date'):
            try:
                date_obj = datetime.strptime(self.supplier['last_service_date'], '%Y-%m-%d')
                date_str = date_obj.strftime('%d/%m/%Y')
                last_service = QLabel(f"🔧 Ultimo: {date_str}")
                last_service.setStyleSheet("color: #3498db; font-size: 11px;")
                stats_row.addWidget(last_service)
            except:
                pass

        # Totale speso
        if self.supplier.get('total_spent', 0) > 0:
            total = QLabel(f"💰 {self.supplier['total_spent']:,.0f}€")
            total.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
            stats_row.addWidget(total)

        # Numero servizi
        if self.supplier.get('service_count', 0) > 0:
            services = QLabel(f"📊 {self.supplier['service_count']} servizi")
            services.setStyleSheet("color: #95a5a6; font-size: 11px;")
            stats_row.addWidget(services)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # RIGA 3: Contatti
        if self.supplier.get('phone') or self.supplier.get('email'):
            contacts_row = QHBoxLayout()
            contacts_row.setSpacing(20)

            if self.supplier.get('phone'):
                phone = QLabel(f"📞 {self.supplier['phone']}")
                phone.setStyleSheet("color: #bdc3c7; font-size: 11px;")
                contacts_row.addWidget(phone)

            if self.supplier.get('email'):
                email = QLabel(f"✉️ {self.supplier['email']}")
                email.setStyleSheet("color: #bdc3c7; font-size: 11px;")
                contacts_row.addWidget(email)

            contacts_row.addStretch()
            layout.addLayout(contacts_row)


class SupplierDetailsDialog(QDialog):
    """Dialog dettagliato per visualizzare tutte le info del fornitore"""
    
    def __init__(self, supplier, supplier_service, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.supplier_service = supplier_service
        self.tm = get_translation_manager()
        
        self.setWindowTitle(f"Dettagli: {supplier['name']}")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(default_dialog_style)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Costruisce l'interfaccia del dialog"""
        layout = QVBoxLayout(self)
        
        # Header con nome e rating
        header = QHBoxLayout()
        
        name_label = QLabel(f"🏢 {self.supplier['name']}")
        name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header.addWidget(name_label)
        
        if self.supplier.get('avg_rating', 0) > 0:
            stars = StarRatingWidget(int(self.supplier['avg_rating']))
            header.addWidget(stars)
            
            rating_label = QLabel(f"{self.supplier['avg_rating']}/5")
            rating_label.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
            header.addWidget(rating_label)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Tabs per le diverse sezioni
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORE_SECONDARIO};
                border-radius: 6px;
                background-color: {COLORE_WIDGET_2};
            }}
            QTabBar::tab {{
                background-color: {COLORE_SECONDARIO};
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORE_ITEM_SELEZIONATO};
            }}
            QTabBar::tab:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        
        # Tab 1: Info Generali
        info_tab = self.create_info_tab()
        tabs.addTab(info_tab, "📋 Info")
        
        # Tab 2: Recensioni
        reviews_tab = self.create_reviews_tab()
        tabs.addTab(reviews_tab, f"⭐ Recensioni ({self.supplier.get('review_count', 0)})")
        
        # Tab 3: Documenti
        documents_tab = self.create_documents_tab()
        tabs.addTab(documents_tab, "📄 Documenti")
        
        layout.addWidget(tabs)
        
        # Bottone chiudi
        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(default_aggiungi_button)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def create_info_tab(self):
        """Crea tab con info generali"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Categoria
        cat_label = QLabel(f"📂 Categoria: {self.supplier['category']}")
        cat_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(cat_label)
        
        # Proprietà
        if self.supplier.get('property_name'):
            prop_label = QLabel(f"🏠 Proprietà: {self.supplier['property_name']}")
            prop_label.setStyleSheet("color: #3498db; font-size: 13px;")
            layout.addWidget(prop_label)
        
        # Contatti
        if self.supplier.get('phone') or self.supplier.get('email') or self.supplier.get('address'):
            contacts_frame = QFrame()
            contacts_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORE_SECONDARIO};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)
            contacts_layout = QVBoxLayout(contacts_frame)
            
            contacts_title = QLabel("📞 Contatti")
            contacts_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            contacts_layout.addWidget(contacts_title)
            
            if self.supplier.get('phone'):
                phone = QLabel(f"Telefono: {self.supplier['phone']}")
                phone.setStyleSheet("color: #bdc3c7; font-size: 12px;")
                contacts_layout.addWidget(phone)
            
            if self.supplier.get('email'):
                email = QLabel(f"Email: {self.supplier['email']}")
                email.setStyleSheet("color: #bdc3c7; font-size: 12px;")
                contacts_layout.addWidget(email)
            
            if self.supplier.get('address'):
                address = QLabel(f"Indirizzo: {self.supplier['address']}")
                address.setStyleSheet("color: #bdc3c7; font-size: 12px;")
                address.setWordWrap(True)
                contacts_layout.addWidget(address)
            
            layout.addWidget(contacts_frame)
        
        # Statistiche
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        stats_layout = QVBoxLayout(stats_frame)
        
        stats_title = QLabel("📊 Statistiche")
        stats_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        stats_layout.addWidget(stats_title)
        
        stats_grid = QHBoxLayout()
        
        if self.supplier.get('service_count', 0) > 0:
            services = QLabel(f"{self.supplier['service_count']}\nServizi")
            services.setStyleSheet("color: #3498db; font-size: 12px; text-align: center;")
            services.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_grid.addWidget(services)
        
        if self.supplier.get('total_spent', 0) > 0:
            spent = QLabel(f"€ {self.supplier['total_spent']:,.0f}\nSpesi")
            spent.setStyleSheet("color: #2ecc71; font-size: 12px; text-align: center;")
            spent.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_grid.addWidget(spent)
        
        if self.supplier.get('last_service_date'):
            try:
                date_obj = datetime.strptime(self.supplier['last_service_date'], '%Y-%m-%d')
                date_str = date_obj.strftime('%d/%m/%Y')
                last = QLabel(f"{date_str}\nUltimo Servizio")
                last.setStyleSheet("color: #f39c12; font-size: 12px; text-align: center;")
                last.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stats_grid.addWidget(last)
            except:
                pass
        
        stats_layout.addLayout(stats_grid)
        layout.addWidget(stats_frame)
        
        # Note
        if self.supplier.get('notes'):
            notes_frame = QFrame()
            notes_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORE_SECONDARIO};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)
            notes_layout = QVBoxLayout(notes_frame)
            
            notes_title = QLabel("📝 Note")
            notes_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            notes_layout.addWidget(notes_title)
            
            notes_text = QLabel(self.supplier['notes'])
            notes_text.setStyleSheet("color: #bdc3c7; font-size: 12px;")
            notes_text.setWordWrap(True)
            notes_layout.addWidget(notes_text)
            
            layout.addWidget(notes_frame)
        
        layout.addStretch()
        return widget
    
    def create_reviews_tab(self):
        """Crea tab recensioni"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Bottone aggiungi recensione
        add_review_btn = QPushButton("➕ Aggiungi Recensione")
        add_review_btn.setStyleSheet(default_aggiungi_button)
        add_review_btn.clicked.connect(self.add_review)
        layout.addWidget(add_review_btn)
        
        # Lista recensioni
        reviews = self.supplier_service.get_reviews(self.supplier['id'])
        
        if not reviews:
            no_reviews = QLabel("📭 Nessuna recensione ancora")
            no_reviews.setStyleSheet("color: #95a5a6; font-size: 14px; padding: 20px;")
            no_reviews.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_reviews)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("border: none; background-color: transparent;")
            
            reviews_container = QWidget()
            reviews_layout = QVBoxLayout(reviews_container)
            
            for review in reviews:
                review_card = self.create_review_card(review)
                reviews_layout.addWidget(review_card)
            
            reviews_layout.addStretch()
            scroll.setWidget(reviews_container)
            layout.addWidget(scroll)
        
        return widget
    
    def create_review_card(self, review):
        """Crea una card per una recensione"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # Header: stelle e data
        header = QHBoxLayout()
        
        stars = StarRatingWidget(review['rating'])
        header.addWidget(stars)
        
        if review.get('created_at'):
            try:
                date_obj = datetime.fromisoformat(review['created_at'])
                date_str = date_obj.strftime('%d/%m/%Y')
                date_label = QLabel(date_str)
                date_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
                header.addWidget(date_label)
            except:
                pass
        
        header.addStretch()
        
        # Bottone elimina
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ERROR};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        delete_btn.clicked.connect(lambda: self.delete_review(review['id']))
        header.addWidget(delete_btn)
        
        layout.addLayout(header)
        
        # Titolo recensione
        if review.get('title'):
            title = QLabel(review['title'])
            title.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            layout.addWidget(title)
        
        # Commento
        if review.get('comment'):
            comment = QLabel(review['comment'])
            comment.setStyleSheet("color: #bdc3c7; font-size: 12px;")
            comment.setWordWrap(True)
            layout.addWidget(comment)
        
        return card
    
    def add_review(self):
        """Dialog per aggiungere recensione"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuova Recensione")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(default_dialog_style)
        
        layout = QFormLayout(dialog)
        
        # Rating
        rating_widget = StarRatingWidget(0, editable=True)
        layout.addRow("Valutazione*:", rating_widget)
        
        # Titolo
        title_input = QLineEdit()
        title_input.setPlaceholderText("Es: Ottimo servizio")
        layout.addRow("Titolo:", title_input)
        
        # Commento
        comment_input = QTextEdit()
        comment_input.setPlaceholderText("Descrivi la tua esperienza...")
        comment_input.setMaximumHeight(100)
        layout.addRow("Commento:", comment_input)
        
        # Bottoni
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        if dialog.exec():
            rating = rating_widget.get_rating()
            if rating == 0:
                QMessageBox.warning(self, "⚠️ Attenzione", "Seleziona una valutazione!")
                return
            
            title = title_input.text().strip() or None
            comment = comment_input.toPlainText().strip() or None
            
            review_id = self.supplier_service.add_review(
                self.supplier['id'],
                rating,
                title,
                comment
            )
            
            if review_id:
                QMessageBox.information(self, "✅ Successo", "Recensione aggiunta!")
                # Ricarica tab
                self.setup_ui()
            else:
                QMessageBox.warning(self, "❌ Errore", "Impossibile aggiungere la recensione")
    
    def delete_review(self, review_id):
        """Elimina una recensione"""
        reply = QMessageBox.question(
            self,
            "Conferma",
            "Eliminare questa recensione?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.supplier_service.delete_review(review_id):
                QMessageBox.information(self, "✅ Successo", "Recensione eliminata!")
                self.setup_ui()
            else:
                QMessageBox.warning(self, "❌ Errore", "Impossibile eliminare")
    
    def create_documents_tab(self):
        """Crea tab documenti"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Bottone aggiungi documento
        add_doc_btn = QPushButton("➕ Aggiungi Documento")
        add_doc_btn.setStyleSheet(default_aggiungi_button)
        add_doc_btn.clicked.connect(self.add_document)
        layout.addWidget(add_doc_btn)
        
        # Lista documenti
        documents = self.supplier_service.get_documents(self.supplier['id'])
        
        if not documents:
            no_docs = QLabel("📭 Nessun documento caricato")
            no_docs.setStyleSheet("color: #95a5a6; font-size: 14px; padding: 20px;")
            no_docs.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_docs)
        else:
            docs_list = QListWidget()
            docs_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: transparent;
                    border: none;
                }}
                QListWidget::item {{
                    background-color: {COLORE_SECONDARIO};
                    border-radius: 6px;
                    padding: 10px;
                    margin-bottom: 5px;
                }}
                QListWidget::item:hover {{
                    background-color: {COLORE_ITEM_HOVER};
                }}
            """)
            
            for doc in documents:
                item_widget = self.create_document_item(doc)
                item = QListWidgetItem()
                item.setSizeHint(item_widget.sizeHint())
                docs_list.addItem(item)
                docs_list.setItemWidget(item, item_widget)
            
            layout.addWidget(docs_list)
        
        return widget
    
    def create_document_item(self, doc):
        """Crea widget per un documento"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Icona tipo documento
        icon_map = {
            'contratto': '📝',
            'preventivo': '💰',
            'fattura': '🧾',
            'altro': '📄'
        }
        icon = icon_map.get(doc['document_type'], '📄')
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)
        
        # Info documento
        info_layout = QVBoxLayout()
        
        title = QLabel(doc['title'])
        title.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        info_layout.addWidget(title)
        
        type_label = QLabel(doc['document_type'].capitalize())
        type_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        info_layout.addWidget(type_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Bottone apri
        open_btn = QPushButton("📂 Apri")
        open_btn.setFixedHeight(28)
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(doc['file_path'])))
        layout.addWidget(open_btn)
        
        # Bottone elimina
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ERROR};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        delete_btn.clicked.connect(lambda: self.delete_document(doc['id']))
        layout.addWidget(delete_btn)
        
        return widget
    
    def add_document(self):
        """Dialog per aggiungere documento"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuovo Documento")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(default_dialog_style)
        
        layout = QFormLayout(dialog)
        
        # Tipo documento
        type_combo = QComboBox()
        type_combo.addItems(['Contratto', 'Preventivo', 'Fattura', 'Altro'])
        layout.addRow("Tipo*:", type_combo)
        
        # Titolo
        title_input = QLineEdit()
        title_input.setPlaceholderText("Es: Contratto annuale 2024")
        layout.addRow("Titolo*:", title_input)
        
        # Selezione file
        file_path_input = QLineEdit()
        file_path_input.setReadOnly(True)
        
        browse_btn = QPushButton("📁 Sfoglia...")
        browse_btn.clicked.connect(lambda: self.browse_file(file_path_input))
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(file_path_input)
        file_layout.addWidget(browse_btn)
        layout.addRow("File*:", file_layout)
        
        # Note
        notes_input = QTextEdit()
        notes_input.setMaximumHeight(80)
        notes_input.setPlaceholderText("Note opzionali...")
        layout.addRow("Note:", notes_input)
        
        # Bottoni
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        if dialog.exec():
            title = title_input.text().strip()
            file_path = file_path_input.text().strip()
            
            if not title or not file_path:
                QMessageBox.warning(self, "⚠️ Attenzione", "Compilare tutti i campi obbligatori!")
                return
            
            doc_type = type_combo.currentText().lower()
            notes = notes_input.toPlainText().strip() or None
            
            doc_id = self.supplier_service.add_document(
                self.supplier['id'],
                doc_type,
                title,
                file_path,
                notes
            )
            
            if doc_id:
                QMessageBox.information(self, "✅ Successo", "Documento aggiunto!")
                self.setup_ui()
            else:
                QMessageBox.warning(self, "❌ Errore", "Impossibile aggiungere il documento")
    
    def browse_file(self, line_edit):
        """Apre dialog per selezionare file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona Documento",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            line_edit.setText(file_path)
    
    def delete_document(self, doc_id):
        """Elimina un documento"""
        reply = QMessageBox.question(
            self,
            "Conferma",
            "Eliminare questo documento?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.supplier_service.delete_document(doc_id):
                QMessageBox.information(self, "✅ Successo", "Documento eliminato!")
                self.setup_ui()
            else:
                QMessageBox.warning(self, "❌ Errore", "Impossibile eliminare")


class SuppliersView(BaseView):
    """View completa per gestione fornitori"""

    def __init__(self, supplier_service, property_service, logger, parent=None):
        self.supplier_service = supplier_service
        self.property_service = property_service
        self.logger = logger
        self.tm = get_translation_manager()
        self.current_category = None
        self.current_property_id = None
        self.current_min_rating = None
        
        super().__init__(property_service, None, None, parent)

    def setup_ui(self):
        """Costruisce l'interfaccia"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # HEADER
        header_layout = QHBoxLayout()

        title = QLabel("🏢 Gestione Fornitori")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        add_btn = QPushButton("+ Aggiungi Fornitore")
        add_btn.setStyleSheet(default_aggiungi_button)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_supplier)
        header_layout.addWidget(add_btn)

        main_layout.addLayout(header_layout)

        # FILTRI
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(15)

        # Proprietà
        property_label = QLabel("Proprietà:")
        property_label.setStyleSheet("color: white; font-size: 14px;")
        filters_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.setStyleSheet(default_combo_box_style)
        self.property_selector.setMinimumWidth(200)
        self.property_selector.addItem("Tutte le proprietà", None)
        
        properties = self.property_service.get_all()
        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])
        
        self.property_selector.currentIndexChanged.connect(self.filter_by_property)
        filters_layout.addWidget(self.property_selector)

        # Categoria
        category_label = QLabel("Categoria:")
        category_label.setStyleSheet("color: white; font-size: 14px;")
        filters_layout.addWidget(category_label)

        self.category_selector = QComboBox()
        self.category_selector.setStyleSheet(default_combo_box_style)
        self.category_selector.setMinimumWidth(200)
        self.populate_categories()
        self.category_selector.currentIndexChanged.connect(self.filter_by_category)
        filters_layout.addWidget(self.category_selector)

        # Rating minimo
        rating_label = QLabel("Rating Min:")
        rating_label.setStyleSheet("color: white; font-size: 14px;")
        filters_layout.addWidget(rating_label)

        self.rating_selector = QComboBox()
        self.rating_selector.setStyleSheet(default_combo_box_style)
        self.rating_selector.addItem("Tutti", None)
        for i in range(1, 6):
            self.rating_selector.addItem(f"⭐ {i}+", i)
        self.rating_selector.currentIndexChanged.connect(self.filter_by_rating)
        filters_layout.addWidget(self.rating_selector)

        filters_layout.addStretch()

        # Barra ricerca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cerca fornitore...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORE_WIDGET_2};
                color: white;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 250px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORE_ITEM_SELEZIONATO};
            }}
        """)
        self.search_input.textChanged.connect(self.search_suppliers)
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

        # AREA SCROLLABILE
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORE_BACKGROUND};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORE_SECONDARIO};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(scroll_area)

        self.load_suppliers()

    def populate_categories(self):
        """Popola selettore categorie"""
        self.category_selector.clear()
        self.category_selector.addItem("Tutte le categorie", None)

        categories = self.supplier_service.get_categories(self.current_property_id)
        for category in categories:
            self.category_selector.addItem(category, category)

    def update_stats(self, suppliers_count):
        """Aggiorna statistiche"""
        filter_text = []
        
        if self.current_property_id:
            property_name = self.property_selector.currentText()
            filter_text.append(f"proprietà '{property_name}'")
        
        if self.current_category:
            filter_text.append(f"categoria '{self.current_category}'")
        
        if self.current_min_rating:
            filter_text.append(f"rating ≥ {self.current_min_rating}⭐")
        
        if filter_text:
            self.stats_label.setText(
                f"📊 {suppliers_count} fornitori • Filtri: {' + '.join(filter_text)}"
            )
        else:
            stats = self.supplier_service.get_stats()
            total = stats['total']
            categories_count = len(stats['by_category'])
            self.stats_label.setText(
                f"📊 {total} fornitori totali • {categories_count} categorie"
            )

    def load_suppliers(self, search_text=""):
        """Carica fornitori"""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if search_text:
            suppliers = self.supplier_service.search(
                search_text, 
                self.current_category, 
                self.current_property_id
            )
        else:
            suppliers = self.supplier_service.get_all(
                self.current_category, 
                self.current_property_id,
                self.current_min_rating
            )

        self.update_stats(len(suppliers))

        if not suppliers:
            no_data_label = QLabel("📭 Nessun fornitore trovato")
            no_data_label.setStyleSheet("color: #bdc3c7; font-size: 16px; padding: 40px;")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            self.cards_layout.addStretch()
            return

        for index, supplier in enumerate(suppliers):
            card = SupplierCard(
                supplier,
                self.edit_supplier,
                self.delete_supplier,
                self.view_supplier_details,
                index
            )
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def view_supplier_details(self, supplier):
        """Apre dialog dettagli fornitore"""
        dialog = SupplierDetailsDialog(supplier, self.supplier_service, self)
        dialog.exec()
        # Ricarica per aggiornare eventuali modifiche
        self.load_suppliers()

    def filter_by_property(self, index):
        """Filtra per proprietà"""
        self.current_property_id = self.property_selector.currentData()
        self.current_category = None
        self.category_selector.setCurrentIndex(0)
        self.search_input.clear()
        self.populate_categories()
        self.load_suppliers()

    def filter_by_category(self, index):
        """Filtra per categoria"""
        self.current_category = self.category_selector.currentData()
        self.search_input.clear()
        self.load_suppliers()

    def filter_by_rating(self, index):
        """Filtra per rating"""
        self.current_min_rating = self.rating_selector.currentData()
        self.load_suppliers()

    def search_suppliers(self, text):
        """Cerca fornitori"""
        self.load_suppliers(search_text=text)

    def add_supplier(self):
        """Dialog aggiungi fornitore"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nuovo Fornitore")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Es: ENEL Energia")
        layout.addRow("Nome*:", name_input)

        category_combo = QComboBox()
        category_combo.setEditable(True)
        category_combo.setPlaceholderText("Es: Bolletta Luce")
        
        categories = self.supplier_service.get_categories()
        for cat in categories:
            category_combo.addItem(cat)
        
        layout.addRow("Categoria*:", category_combo)

        property_combo = QComboBox()
        property_combo.addItem("Nessuna proprietà", None)
        
        properties = self.property_service.get_all()
        for prop in properties:
            property_combo.addItem(prop['name'], prop['id'])
        
        if self.current_property_id:
            index = property_combo.findData(self.current_property_id)
            if index >= 0:
                property_combo.setCurrentIndex(index)
        
        layout.addRow("Proprietà:", property_combo)

        phone_input = QLineEdit()
        phone_input.setPlaceholderText("Es: +39 123 456 7890")
        layout.addRow("Telefono:", phone_input)

        email_input = QLineEdit()
        email_input.setPlaceholderText("Es: info@fornitore.it")
        layout.addRow("Email:", email_input)

        address_input = QLineEdit()
        address_input.setPlaceholderText("Es: Via Roma 123, Milano")
        layout.addRow("Indirizzo:", address_input)

        notes_input = QTextEdit()
        notes_input.setPlaceholderText("Note aggiuntive...")
        notes_input.setMaximumHeight(80)
        layout.addRow("Note:", notes_input)

        # Rating iniziale
        rating_spin = QSpinBox()
        rating_spin.setRange(0, 5)
        rating_spin.setValue(0)
        rating_spin.setSuffix(" ⭐")
        layout.addRow("Valutazione:", rating_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            try:
                name = validate_required_text(
                    name_input.text(),
                    "Nome",
                    min_length=2,
                    max_length=200
                )

                category = validate_required_text(
                    category_combo.currentText(),
                    "Categoria",
                    min_length=2,
                    max_length=200
                )

                property_id = property_combo.currentData()
                phone = phone_input.text().strip() or None
                email = email_input.text().strip() or None
                address = address_input.text().strip() or None
                notes = notes_input.toPlainText().strip() or None
                rating = rating_spin.value() if rating_spin.value() > 0 else None

                supplier_id = self.supplier_service.create(
                    name=name,
                    category=category,
                    property_id=property_id,
                    phone=phone,
                    email=email,
                    address=address,
                    notes=notes,
                    rating=rating
                )

                if supplier_id:
                    QMessageBox.information(
                        self,
                        "✅ Successo",
                        f"Fornitore '{name}' aggiunto con successo!"
                    )
                    self.populate_categories()
                    self.load_suppliers()
                else:
                    QMessageBox.warning(
                        self,
                        "❌ Errore",
                        "Impossibile aggiungere il fornitore."
                    )

            except ValidationError as e:
                QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))

    def edit_supplier(self, supplier):
        """Dialog modifica fornitore"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifica Fornitore: {supplier['name']}")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(default_dialog_style)

        layout = QFormLayout(dialog)

        name_input = QLineEdit(supplier['name'])
        layout.addRow("Nome*:", name_input)

        category_combo = QComboBox()
        category_combo.setEditable(True)
        categories = self.supplier_service.get_categories()
        for cat in categories:
            category_combo.addItem(cat)
        category_combo.setCurrentText(supplier['category'])
        layout.addRow("Categoria*:", category_combo)

        property_combo = QComboBox()
        property_combo.addItem("Nessuna proprietà", None)
        
        properties = self.property_service.get_all()
        for prop in properties:
            property_combo.addItem(prop['name'], prop['id'])
        
        if supplier.get('property_id'):
            index = property_combo.findData(supplier['property_id'])
            if index >= 0:
                property_combo.setCurrentIndex(index)
        
        layout.addRow("Proprietà:", property_combo)

        phone_input = QLineEdit(supplier.get('phone') or "")
        layout.addRow("Telefono:", phone_input)

        email_input = QLineEdit(supplier.get('email') or "")
        layout.addRow("Email:", email_input)

        address_input = QLineEdit(supplier.get('address') or "")
        layout.addRow("Indirizzo:", address_input)

        notes_input = QTextEdit()
        notes_input.setPlainText(supplier.get('notes') or "")
        notes_input.setMaximumHeight(80)
        layout.addRow("Note:", notes_input)

        rating_spin = QSpinBox()
        rating_spin.setRange(0, 5)
        rating_spin.setValue(supplier.get('rating') or 0)
        rating_spin.setSuffix(" ⭐")
        layout.addRow("Valutazione:", rating_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            try:
                name = validate_required_text(
                    name_input.text(),
                    "Nome",
                    min_length=2,
                    max_length=200
                )

                category = validate_required_text(
                    category_combo.currentText(),
                    "Categoria",
                    min_length=2,
                    max_length=200
                )

                property_id = property_combo.currentData()
                phone = phone_input.text().strip() or None
                email = email_input.text().strip() or None
                address = address_input.text().strip() or None
                notes = notes_input.toPlainText().strip() or None
                rating = rating_spin.value() if rating_spin.value() > 0 else None

                success = self.supplier_service.update(
                    supplier['id'],
                    name=name,
                    category=category,
                    property_id=property_id,
                    phone=phone,
                    email=email,
                    address=address,
                    notes=notes,
                    rating=rating
                )

                if success:
                    QMessageBox.information(
                        self,
                        "✅ Successo",
                        "Fornitore aggiornato con successo!"
                    )
                    self.populate_categories()
                    self.load_suppliers()
                else:
                    QMessageBox.warning(
                        self,
                        "❌ Errore",
                        "Impossibile aggiornare il fornitore."
                    )

            except ValidationError as e:
                QMessageBox.warning(self, "⚠️ Validazione fallita", str(e))

    def delete_supplier(self, supplier):
        """Elimina fornitore"""
        property_info = f"\n🏠 Proprietà: {supplier['property_name']}" if supplier.get('property_name') else ""
        stats_info = ""
        if supplier.get('service_count', 0) > 0:
            stats_info = f"\n📊 {supplier['service_count']} servizi utilizzati"
        if supplier.get('total_spent', 0) > 0:
            stats_info += f"\n💰 {supplier['total_spent']:,.0f}€ spesi"
        
        reply = QMessageBox.question(
            self,
            "🗑️ Conferma Eliminazione",
            f"Sei sicuro di voler eliminare il fornitore '{supplier['name']}'?{property_info}{stats_info}\n\n"
            f"⚠️ Verranno eliminati anche tutti i documenti e le recensioni associati!\n"
            f"Questa operazione è IRREVERSIBILE!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.supplier_service.delete(supplier['id'])

            if success:
                QMessageBox.information(
                    self,
                    "✅ Successo",
                    f"Fornitore '{supplier['name']}' eliminato con successo!"
                )
                self.populate_categories()
                self.load_suppliers()
            else:
                QMessageBox.warning(
                    self,
                    "❌ Errore",
                    "Impossibile eliminare il fornitore."
                )
