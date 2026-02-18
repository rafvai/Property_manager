"""
ui_register.py — Registrazione con codice invito (prima volta)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve

from styles import (
    COLORE_SECONDARIO, COLORE_WIDGET_2, COLORE_ITEM_SELEZIONATO,
    COLORE_ITEM_HOVER, COLORE_BIANCO, COLORE_ERROR, COLORE_SUCCESS, COLORE_GRIGIO
)

_CARD = f"QFrame#regCard {{ background-color: {COLORE_WIDGET_2}; border-radius: 16px; }}"
_INPUT = f"""
    QLineEdit {{
        background-color: {COLORE_SECONDARIO}; color: {COLORE_BIANCO};
        border: 2px solid #334155; border-radius: 8px;
        padding: 12px 16px; font-size: 14px;
    }}
    QLineEdit:focus {{ border: 2px solid {COLORE_ITEM_SELEZIONATO}; }}
    QLineEdit:disabled {{ color: {COLORE_GRIGIO}; }}
"""
_BTN_PRIMARY = f"""
    QPushButton {{
        background-color: {COLORE_ITEM_SELEZIONATO}; color: white;
        border: none; border-radius: 8px;
        padding: 13px; font-size: 15px; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {COLORE_ITEM_HOVER}; }}
    QPushButton:disabled {{ background-color: #334155; color: {COLORE_GRIGIO}; }}
"""
_BTN_GHOST = f"""
    QPushButton {{
        background: transparent; color: {COLORE_GRIGIO};
        border: none; font-size: 13px; padding: 6px;
    }}
    QPushButton:hover {{ color: {COLORE_BIANCO}; }}
"""


class RegisterWindow(QWidget):
    """
    Schermata di registrazione con codice invito.
    Emette:
      - register_successful()  → apre il login
      - back_to_login()        → torna al login (ha già un account)
    """

    register_successful = Signal()
    back_to_login       = Signal()

    def __init__(self, auth_service, logger):
        super().__init__()
        self.auth_service = auth_service
        self.logger       = logger
        self._drag_pos    = None

        self.setWindowTitle("Property Manager — Registrazione")
        self.setMinimumSize(480, 580)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        geo = QApplication.primaryScreen().geometry()
        self.setGeometry((geo.width() - 480) // 2, (geo.height() - 580) // 2, 480, 580)

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("regCard")
        card.setStyleSheet(_CARD)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(14)

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

        # header
        icon = self._lbl("🎟️", "font-size:40px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        t = self._lbl("Crea il tuo account", f"color:{COLORE_BIANCO};font-size:21px;font-weight:bold;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        sub = self._lbl("Inserisci il codice invito ricevuto", f"color:{COLORE_GRIGIO};font-size:12px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(4)

        # Codice invito
        lay.addWidget(self._lbl("Codice invito *", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.invite_input = QLineEdit()
        self.invite_input.setPlaceholderText("es. AB3X7K9M")
        self.invite_input.setStyleSheet(_INPUT)
        self.invite_input.setMinimumHeight(46)
        self.invite_input.textChanged.connect(
            lambda t: self.invite_input.setText(t.upper())
        )
        lay.addWidget(self.invite_input)

        # Nome (opzionale)
        lay.addWidget(self._lbl("Nome completo (opzionale)", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Mario Rossi")
        self.name_input.setStyleSheet(_INPUT)
        self.name_input.setMinimumHeight(46)
        lay.addWidget(self.name_input)

        # Email
        lay.addWidget(self._lbl("Email *", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tua@email.com")
        self.email_input.setStyleSheet(_INPUT)
        self.email_input.setMinimumHeight(46)
        lay.addWidget(self.email_input)

        # Password
        lay.addWidget(self._lbl("Password * (min. 8 caratteri)", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("Scegli una password sicura…")
        self.pwd_input.setStyleSheet(_INPUT)
        self.pwd_input.setMinimumHeight(46)
        lay.addWidget(self.pwd_input)

        # Conferma password
        lay.addWidget(self._lbl("Conferma password *", f"color:{COLORE_BIANCO};font-size:13px;font-weight:600;"))
        self.pwd_confirm = QLineEdit()
        self.pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_confirm.setPlaceholderText("Ripeti la password…")
        self.pwd_confirm.setStyleSheet(_INPUT)
        self.pwd_confirm.setMinimumHeight(46)
        self.pwd_confirm.returnPressed.connect(self._on_submit)
        lay.addWidget(self.pwd_confirm)

        # Messaggio
        self.msg_label = QLabel("")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_label.setWordWrap(True)
        self.msg_label.setStyleSheet(f"color:{COLORE_ERROR};font-size:12px;")
        self.msg_label.hide()
        lay.addWidget(self.msg_label)

        # Bottone registra
        self.submit_btn = QPushButton("Crea account")
        self.submit_btn.setStyleSheet(_BTN_PRIMARY)
        self.submit_btn.setMinimumHeight(50)
        self.submit_btn.clicked.connect(self._on_submit)
        lay.addWidget(self.submit_btn)

        # Link login
        back_btn = QPushButton("Ho già un account → Accedi")
        back_btn.setStyleSheet(_BTN_GHOST)
        back_btn.clicked.connect(self.back_to_login.emit)
        lay.addWidget(back_btn)

        self.invite_input.setFocus()

    # ──────────────────────────────────────────────
    #  LOGICA
    # ──────────────────────────────────────────────
    def _on_submit(self):
        invite = self.invite_input.text().strip().upper()
        email  = self.email_input.text().strip().lower()
        name   = self.name_input.text().strip() or None
        pwd    = self.pwd_input.text()
        pwd2   = self.pwd_confirm.text()

        if not invite:
            self._show_msg("Inserisci il codice invito", "error")
            self._shake(self.invite_input)
            return
        if not email or "@" not in email:
            self._show_msg("Inserisci un'email valida", "error")
            self._shake(self.email_input)
            return
        if len(pwd) < 8:
            self._show_msg("La password deve essere di almeno 8 caratteri", "error")
            self._shake(self.pwd_input)
            return
        if pwd != pwd2:
            self._show_msg("Le password non coincidono", "error")
            self._shake(self.pwd_confirm)
            return

        self._set_loading(True)
        self._show_msg("Registrazione in corso…", "info")
        QTimer.singleShot(50, lambda: self._do_register(invite, email, name, pwd))

    def _do_register(self, invite: str, email: str, name, pwd: str):
        try:
            import requests as req
            resp = req.post(
                f"{self.auth_service.server_url}/auth/register",
                json={
                    "email": email,
                    "password": pwd,
                    "full_name": name,
                    "invite_code": invite
                },
                timeout=10
            )
            self._set_loading(False)

            if resp.status_code == 200:
                self._show_msg("✅ Account creato! Ora accedi con le tue credenziali.", "success")
                QTimer.singleShot(1800, self.register_successful.emit)
            else:
                detail = resp.json().get("detail", "Errore durante la registrazione")
                self._show_msg(detail, "error")

        except Exception as e:
            self._set_loading(False)
            self._show_msg("Impossibile connettersi al server.\nVerifica la connessione internet.", "error")
            self.logger.error(f"RegisterWindow: errore connessione: {e}")

    # ──────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────
    def _set_loading(self, on: bool):
        self.submit_btn.setEnabled(not on)
        for w in [self.invite_input, self.email_input, self.name_input,
                  self.pwd_input, self.pwd_confirm]:
            w.setEnabled(not on)
        self.submit_btn.setText("Registrazione…" if on else "Crea account")

    def _show_msg(self, text, kind="error"):
        colors = {"error": COLORE_ERROR, "success": COLORE_SUCCESS,
                  "info": COLORE_GRIGIO, "warning": "#f59e0b"}
        self.msg_label.setStyleSheet(f"color:{colors.get(kind, COLORE_ERROR)};font-size:12px;")
        self.msg_label.setText(text)
        self.msg_label.show()

    def _shake(self, widget):
        pos  = widget.pos()
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        d = 7
        anim.setKeyValueAt(0.0, pos)
        anim.setKeyValueAt(0.2, pos + type(pos)(d, 0))
        anim.setKeyValueAt(0.4, pos + type(pos)(-d, 0))
        anim.setKeyValueAt(0.6, pos + type(pos)(d // 2, 0))
        anim.setKeyValueAt(0.8, pos + type(pos)(-d // 2, 0))
        anim.setKeyValueAt(1.0, pos)
        anim.start()
        self._shake_anim = anim

    @staticmethod
    def _lbl(text, style=""):
        l = QLabel(text)
        if style:
            l.setStyleSheet(style)
        return l

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
