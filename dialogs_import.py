"""
Dialog per importazione transazioni da Excel
"""
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from styles import (
    COLORE_BACKGROUND,
    COLORE_ERROR,
    COLORE_ITEM_HOVER,
    COLORE_SECONDARIO,
    COLORE_SUCCESS,
    COLORE_WIDGET_2,
    default_aggiungi_button,
    default_combo_box_style,
    default_dialog_style,
)


class ImportWorker(QThread):
    """Worker thread per importazione in background"""

    progress = Signal(int, int)  # (current, total)
    finished = Signal(dict)  # result

    def __init__(self, import_service, file_path, property_id):
        super().__init__()
        self.import_service = import_service
        self.file_path = file_path
        self.property_id = property_id

    def run(self):
        """Esegue importazione"""
        result = self.import_service.import_from_excel(
            self.file_path,
            self.property_id
        )
        self.finished.emit(result)


class ImportDialog(QDialog):
    """Dialog per importare transazioni da Excel/CSV"""

    def __init__(self, import_service, property_service, tm, parent=None):
        super().__init__(parent)
        self.import_service = import_service
        self.property_service = property_service
        self.tm = tm

        self.setWindowTitle(self.tm.get("TOOLTIP", "IMPORTA_DA_EXCEL"))
        self.setMinimumSize(700, 500)
        self.setStyleSheet(default_dialog_style)

        self.selected_file = None
        self.import_worker = None

        self.setup_ui()

    def setup_ui(self):
        """Costruisce l'interfaccia"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Titolo
        title = QLabel("📊 Importazione Transazioni")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # === SEZIONE PROPRIETÀ ===
        property_group = QGroupBox("1️⃣ Seleziona Proprietà")
        property_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        property_layout = QVBoxLayout(property_group)

        property_label = QLabel("Le transazioni verranno importate per questa proprietà:")
        property_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        property_layout.addWidget(property_label)

        self.property_selector = QComboBox()
        self.property_selector.setStyleSheet(default_combo_box_style)

        properties = self.property_service.get_all()
        if not properties:
            QMessageBox.warning(
                self,
                "⚠️ Attenzione",
                "Nessuna proprietà trovata!\n\nCrea prima una proprietà nella sezione Proprietà."
            )
            self.reject()
            return

        for prop in properties:
            self.property_selector.addItem(prop['name'], prop['id'])

        property_layout.addWidget(self.property_selector)
        layout.addWidget(property_group)

        # === SEZIONE FILE ===
        file_group = QGroupBox("2️⃣ Seleziona File")
        file_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        file_layout = QVBoxLayout(file_group)

        file_info = QLabel("Formati supportati: Excel (.xlsx, .xls) e CSV (.csv)")
        file_info.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        file_layout.addWidget(file_info)

        file_buttons_layout = QHBoxLayout()

        # Bottone template
        template_btn = QPushButton("📄 Scarica Template")
        template_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_SECONDARIO};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORE_ITEM_HOVER};
            }}
        """)
        template_btn.clicked.connect(self.download_template)
        file_buttons_layout.addWidget(template_btn)

        file_buttons_layout.addStretch()

        # Bottone seleziona file
        select_file_btn = QPushButton("📁 Seleziona File")
        select_file_btn.setStyleSheet(default_aggiungi_button)
        select_file_btn.clicked.connect(self.select_file)
        file_buttons_layout.addWidget(select_file_btn)

        file_layout.addLayout(file_buttons_layout)

        # Label file selezionato
        self.file_label = QLabel("Nessun file selezionato")
        self.file_label.setStyleSheet(f"""
            background-color: {COLORE_WIDGET_2};
            color: #95a5a6;
            padding: 10px;
            border-radius: 6px;
            font-size: 12px;
        """)
        file_layout.addWidget(self.file_label)

        layout.addWidget(file_group)

        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 6px;
                text-align: center;
                color: white;
                background-color: {COLORE_WIDGET_2};
            }}
            QProgressBar::chunk {{
                background-color: {COLORE_SUCCESS};
                border-radius: 4px;
            }}
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # === LOG ===
        log_group = QGroupBox("📋 Log Importazione")
        log_group.setStyleSheet(f"""
            QGroupBox {{
                color: white;
                font-weight: bold;
                border: 2px solid {COLORE_SECONDARIO};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORE_BACKGROUND};
                color: white;
                border: 1px solid {COLORE_SECONDARIO};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # === BOTTONI ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("❌ Chiudi")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_ERROR};
                color: white;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self.import_btn = QPushButton("📥 Importa")
        self.import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORE_SUCCESS};
                color: white;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #27ae60;
            }}
            QPushButton:disabled {{
                background-color: {COLORE_SECONDARIO};
                color: #7f8c8d;
            }}
        """)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)
        buttons_layout.addWidget(self.import_btn)

        layout.addLayout(buttons_layout)

    def download_template(self):
        """Genera e scarica il template Excel"""
        try:
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salva Template",
                "template_importazione.xlsx",
                "Excel Files (*.xlsx)"
            )

            if save_path:
                template_path = self.import_service.generate_template(save_path)

                self.log("✅ Template generato con successo!", "green")
                self.log(f"📁 Salvato in: {template_path}", "white")

                QMessageBox.information(
                    self,
                    "✅ Successo",
                    "Template generato con successo!\n\n"
                    "Apri il file, compila le transazioni seguendo le istruzioni,\n"
                    "e poi importalo usando il pulsante 'Seleziona File'."
                )

        except Exception as e:
            self.log(f"❌ Errore generazione template: {str(e)}", "red")
            QMessageBox.critical(
                self,
                "❌ Errore",
                f"Impossibile generare il template:\n\n{str(e)}"
            )

    def select_file(self):
        """Apre dialog per selezionare file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona File da Importare",
            "",
            "Tutti i File Supportati (*.xlsx *.xls *.csv);;Excel (*.xlsx *.xls);;CSV (*.csv)"
        )

        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"✅ File selezionato: {file_path}")
            self.file_label.setStyleSheet(f"""
                background-color: {COLORE_SUCCESS};
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            """)
            self.import_btn.setEnabled(True)
            self.log(f"📁 File selezionato: {file_path}", "white")

    def start_import(self):
        """Avvia l'importazione"""
        if not self.selected_file:
            QMessageBox.warning(
                self,
                "⚠️ Attenzione",
                "Seleziona prima un file da importare!"
            )
            return

        property_id = self.property_selector.currentData()
        property_name = self.property_selector.currentText()

        # Conferma
        reply = QMessageBox.question(
            self,
            "Conferma Importazione",
            f"Importare transazioni per la proprietà '{property_name}'?\n\n"
            f"File: {self.selected_file}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Disabilita bottoni
        self.import_btn.setEnabled(False)
        self.property_selector.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate

        self.log("🚀 Avvio importazione...", "white")

        # Avvia worker thread
        self.import_worker = ImportWorker(
            self.import_service,
            self.selected_file,
            property_id
        )
        self.import_worker.finished.connect(self.import_finished)
        self.import_worker.start()

    def import_finished(self, result):
        """Callback completamento importazione"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.property_selector.setEnabled(True)

        # Log risultati
        self.log("", "white")
        self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "white")
        self.log("📊 RISULTATO IMPORTAZIONE", "white")
        self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "white")
        self.log(f"✅ Importate con successo: {result['success']}", "green")
        self.log(f"❌ Fallite: {result['failed']}", "red" if result['failed'] > 0 else "white")

        if result['errors']:
            self.log("", "white")
            self.log("📋 Dettaglio Errori:", "yellow")
            for error in result['errors'][:10]:  # Max 10 errori nel log
                self.log(f"  • {error}", "red")

            if len(result['errors']) > 10:
                self.log(f"  ... e altri {len(result['errors']) - 10} errori", "red")

        # Messaggio finale
        if result['success'] > 0:
            QMessageBox.information(
                self,
                "✅ Importazione Completata",
                f"Importate {result['success']} transazioni con successo!\n\n"
                f"Fallite: {result['failed']}\n\n"
                f"Controlla il log per i dettagli."
            )
        else:
            QMessageBox.warning(
                self,
                "⚠️ Importazione Fallita",
                f"Nessuna transazione importata.\n\n"
                f"Errori: {result['failed']}\n\n"
                f"Controlla il log per i dettagli."
            )

    def log(self, message, color="white"):
        """Aggiunge messaggio al log"""
        color_map = {
            "white": "#ffffff",
            "green": "#2ecc71",
            "red": "#e74c3c",
            "yellow": "#f39c12",
            "blue": "#3498db"
        }

        hex_color = color_map.get(color, "#ffffff")
        self.log_text.append(f'<span style="color: {hex_color};">{message}</span>')
