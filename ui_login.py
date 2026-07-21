"""
ui_login.py — Login window con autenticazione remota
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve

from styles import (
    COLORE_SECONDARIO, COLORE_WIDGET_2, COLORE_ITEM_SELEZIONATO,
    COLORE_ITEM_HOVER, COLORE_BIANCO, COLORE_ERROR, COLORE_SUCCESS, COLORE_GRIGIO
)

_CARD = f"QFrame#loginCard {{ background-color: {COLORE_WIDGET_2}; border-radius: 16px; }}"

_INPUT = f"""
    QLineEdit {{
        background-color: {COLORE_SECONDARIO}; color: {COLORE_BIANCO};
        border: 2px solid #334155; border-radius: 8px;
        padding: 12px 16px; font-size: 15px;
    }}
    QLineEdit:focus {{ border: 2px solid {COLORE_ITEM_SELEZIONATO}; }}
    QLineEdit:disabled {{ color: {COLORE_GRIGIO}; }}
"""

_BTN = f"""
    QPushButton {{
        background-color: {COLORE_ITEM_SELEZIONATO}; color: white;
        border: none; border-radius: 8px;
        padding: 13px; font-size: 15px; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {COLORE_ITEM_HOVER}; }}
    QPushButton:pressed {{ background-color: #1d4ed8; }}
    QPushButton:disabled {{ background-color: #334155; color: {COLORE_GRIGIO}; }}
"""


class LoginWindow(QWidget):
    """
    Finestra di login (email + password) contro il server licenze remoto.
    Emette login_successful(email, token, is_admin) dopo autenticazione avvenuta.
    """

    login_successful = Signal(str, str, bool)  # email, token, is_admin
    open_register    = Signal()                 # apre la finestra di registrazione

    def __init__(self, auth_service, logger):
        super().__init__()
        self.auth_service  = auth_service
        self.logger        = logger
        self._drag_pos     = None
        self._attempts     = 0
        self._max_attempts = 5

        self.setWindowTitle("Property Manager")
        self.setMinimumSize(460, 560)          # ← altezza aumentata da 480 a 560
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        geo = QApplication.primaryScreen().geometry()
        self.setGeometry((geo.width() - 460) // 2, (geo.height() - 560) // 2, 460, 560)

        self._build_ui()

    # ──────────────────────────────────────────────
    #  BUILD UI
    # ──────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setStyleSheet(_CARD)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(10)                     # ← spacing ridotto da 16 a 10

        # drag / close bar
        drag_row = QHBoxLayout()
        drag_row.addWidget(self._lbl("🏠 Property Manager", f"color:{COLORE_GRIGIO};font-size:12px;"))
        drag_row.addStretch()
        close = QPushButton("✕")
        close.setFixedSize(28, 28)
        close.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{COLORE_GRIGIO};font-size:16px;}}"
                            f"QPushButton:hover{{color:{COLORE_ERROR};}}")
        close.clicked.connect(QApplication.quit)
        drag_row.addWidget(close)
        lay.addLayout(drag_row)

        # icona + titoli
        icon = self._lbl("🔐", "font-size:44px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        t = self._lbl("Accedi a Property Manager", f"color:{COLORE_BIANCO};font-size:22px;font-weight:bold;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        sub = self._lbl("Usa le credenziali fornite per la beta", f"color:{COLORE_GRIGIO};font-size:12px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(8)

        # email
        lay.addWidget(self._lbl("Email", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tua@email.com")
        self.email_input.setStyleSheet(_INPUT)
        self.email_input.setMinimumHeight(48)
        self.email_input.returnPressed.connect(lambda: self.password_input.setFocus())
        lay.addWidget(self.email_input)

        lay.addSpacing(4)                      # ← spazio esplicito tra i due campi

        # password
        lay.addWidget(self._lbl("Password", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Inserisci la password…")
        self.password_input.setStyleSheet(_INPUT)
        self.password_input.setMinimumHeight(48)
        self.password_input.returnPressed.connect(self._on_submit)
        lay.addWidget(self.password_input)

        # messaggio errore/avviso — occupa spazio fisso per evitare salti di layout
        self.msg_label = QLabel("")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_label.setWordWrap(True)
        self.msg_label.setFixedHeight(36)      # ← altezza fissa: non sposta gli altri widget
        self.msg_label.setStyleSheet(f"color:{COLORE_ERROR};font-size:12px;padding:4px 0;")
        self.msg_label.hide()
        lay.addWidget(self.msg_label)

        # bottone
        self.submit_btn = QPushButton("Accedi")
        self.submit_btn.setStyleSheet(_BTN)
        self.submit_btn.setMinimumHeight(50)
        self.submit_btn.clicked.connect(self._on_submit)
        lay.addWidget(self.submit_btn)

        footer = self._lbl("Problemi? Contatta il supporto", f"color:{COLORE_GRIGIO};font-size:11px;padding-top:4px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(footer)

        # link registrazione
        register_row = QHBoxLayout()
        register_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_row.addWidget(self._lbl("Non hai un account?", f"color:{COLORE_GRIGIO};font-size:12px;"))
        register_link = QPushButton("Registrati")
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {COLORE_ITEM_SELEZIONATO}; font-size: 12px;
                font-weight: 600; padding: 0 2px;
            }}
            QPushButton:hover {{ color: {COLORE_ITEM_HOVER}; text-decoration: underline; }}
        """)
        register_link.clicked.connect(self.open_register.emit)
        register_row.addWidget(register_link)
        lay.addLayout(register_row)

        self.email_input.setFocus()

    @staticmethod
    def _lbl(text, style=""):
        l = QLabel(text)
        if style:
            l.setStyleSheet(style)
        return l

    # ──────────────────────────────────────────────
    #  LOGICA
    # ──────────────────────────────────────────────
    def _on_submit(self):
        email    = self.email_input.text().strip()
        password = self.password_input.text()

        if not email:
            self._show_msg("Inserisci la tua email", "error")
            self._shake(self.email_input)
            return
        if not password:
            self._show_msg("Inserisci la password", "error")
            self._shake(self.password_input)
            return

        self._set_loading(True)
        self._show_msg("Connessione al server…", "info")
        QTimer.singleShot(50, lambda: self._do_login(email, password))

    def _do_login(self, email: str, password: str):
        result = self.auth_service.login(email, password)
        self._set_loading(False)

        if result.success:
            if result.warning:
                self._show_msg(result.warning, "warning")
                QTimer.singleShot(2500, lambda: self._proceed(result))
            else:
                self._proceed(result)
        else:
            self._attempts += 1
            remaining = self._max_attempts - self._attempts

            if remaining <= 0:
                self._show_msg("Troppi tentativi falliti. Chiusura…", "error")
                self.submit_btn.setEnabled(False)
                QTimer.singleShot(2000, QApplication.quit)
                return

            msg = result.error or "Credenziali non valide"
            if self._attempts > 1:
                msg += f"\n(Tentativi rimanenti: {remaining})"
            self._show_msg(msg, "error")
            self._shake(self.password_input)
            self.password_input.clear()
            self.password_input.setFocus()

    def _proceed(self, result):
        self.logger.info(
            f"LoginWindow: Accesso OK per {result.email} "
            f"(mode={result.mode}, days_left={result.days_left}, admin={result.is_admin})"
        )
        self.login_successful.emit(result.email, result.token or "", result.is_admin)
        self.close()

    # ──────────────────────────────────────────────
    #  UI helpers
    # ──────────────────────────────────────────────
    def _set_loading(self, on: bool):
        self.submit_btn.setEnabled(not on)
        self.email_input.setEnabled(not on)
        self.password_input.setEnabled(not on)
        self.submit_btn.setText("Verifica in corso…" if on else "Accedi")

    def _show_msg(self, text: str, kind: str = "error"):
        colors = {"error": COLORE_ERROR, "warning": "#f59e0b",
                  "info": COLORE_GRIGIO, "success": COLORE_SUCCESS}
        self.msg_label.setStyleSheet(
            f"color:{colors.get(kind, COLORE_ERROR)};font-size:12px;padding:4px 0;"
        )
        self.msg_label.setText(text)
        self.msg_label.show()

    def _shake(self, widget):
        pos  = widget.pos()
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(280)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        d = 8
        anim.setKeyValueAt(0.0, pos)
        anim.setKeyValueAt(0.2, pos + type(pos)(d, 0))
        anim.setKeyValueAt(0.4, pos + type(pos)(-d, 0))
        anim.setKeyValueAt(0.6, pos + type(pos)(d // 2, 0))
        anim.setKeyValueAt(0.8, pos + type(pos)(-d // 2, 0))
        anim.setKeyValueAt(1.0, pos)
        anim.start()
        self._shake_anim = anim

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        # startSystemMove: drag nativo dell'OS, fluido anche tra monitor con DPI diversi
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if (e.globalPosition().toPoint() - self._drag_pos).manhattanLength() \
                    >= QApplication.startDragDistance():
                self._drag_pos = None
                self.windowHandle().startSystemMove()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None