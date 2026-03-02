"""
Property Manager - License Server
FastAPI backend per gestione licenze beta/SaaS

Deploy su VPS:
    pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] python-dotenv
    uvicorn license_server:app --host 0.0.0.0 --port 8000

Variabili ambiente richieste (.env):
    SECRET_KEY=<stringa casuale lunga 32+ chars>
    ADMIN_KEY=<chiave segreta per pannello admin>
"""

import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
_KEY_FILE = Path(__file__).parent / ".secret_key"

def _load_or_create_secret_key() -> str:
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip()
    key = secrets.token_hex(32)
    _KEY_FILE.write_text(key)
    _KEY_FILE.chmod(0o600)
    return key

SECRET_KEY = os.getenv("SECRET_KEY") or _load_or_create_secret_key()
ADMIN_KEY  = os.getenv("ADMIN_KEY", "changeme-in-production")
ALGORITHM  = "HS256"
DB_PATH    = Path("licenses.db")

GRACE_PERIOD_DAYS = 7   # giorni di grazia dopo scadenza
WARN_BEFORE_DAYS  = 14  # giorni prima della scadenza per mostrare avviso

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
app = FastAPI(title="Property Manager License Server", version="1.0.0")


# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    plan          TEXT    DEFAULT 'beta',
    status        TEXT    DEFAULT 'active',
    is_admin      INTEGER DEFAULT 0,
    registered_at TEXT    DEFAULT (datetime('now')),
    expires_at    TEXT    NOT NULL,
    grace_until   TEXT,
    notes         TEXT,
    last_login    TEXT,
    last_ip       TEXT,
    login_count   INTEGER DEFAULT 0,
    invite_code   TEXT
);

CREATE TABLE IF NOT EXISTS invite_codes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,
    plan         TEXT    DEFAULT 'beta',
    expires_days INTEGER DEFAULT 90,
    max_uses     INTEGER DEFAULT 1,
    used_count   INTEGER DEFAULT 0,
    is_active    INTEGER DEFAULT 1,
    note         TEXT,
    created_at   TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS login_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    timestamp  TEXT    DEFAULT (datetime('now')),
    ip         TEXT,
    success    INTEGER,
    reason     TEXT
);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

init_db()


# ─────────────────────────────────────────────
#  MODELLI
# ─────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    client_info: Optional[str] = None  # versione app, OS

class LoginResponse(BaseModel):
    token: str
    email: str
    expires_at: str
    days_left: int
    is_admin: bool
    warning: Optional[str] = None
    grace_mode: bool = False

class UserCreate(BaseModel):           # solo admin
    email: str
    password: str
    full_name: Optional[str] = None
    plan: str = "beta"
    expires_days: int = 90             # durata in giorni dalla creazione

class UserInfo(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    plan: str
    status: str
    registered_at: str
    expires_at: str
    days_left: int
    last_login: Optional[str]
    login_count: int

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = None
    invite_code: str

class InviteCreate(BaseModel):
    max_uses: int = 1
    expires_days: int = 90
    plan: str = "beta"
    note: str = None



# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta = timedelta(hours=24)) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def days_left(expires_at_str: str) -> int:
    exp = datetime.fromisoformat(expires_at_str)
    delta = exp - datetime.utcnow()
    return max(0, delta.days)

def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin key non valida")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token mancante")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token non valido")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")

def log_login(conn, user_id: int, ip: str, success: bool, reason: str = None):
    conn.execute(
        "INSERT INTO login_log (user_id, ip, success, reason) VALUES (?,?,?,?)",
        (user_id, ip or "unknown", 1 if success else 0, reason)
    )


# ─────────────────────────────────────────────
#  ENDPOINT PUBBLICI
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, x_forwarded_for: str = Header(None)):
    """Login client: verifica credenziali + stato licenza"""
    conn = get_db()
    ip = x_forwarded_for or "unknown"

    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (req.email.lower().strip(),)
    ).fetchone()

    # Utente non trovato
    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # Password errata
    if not verify_password(req.password, row["password_hash"]):
        log_login(conn, row["id"], ip, False, "wrong_password")
        conn.commit()
        conn.close()
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # Account sospeso
    if row["status"] == "suspended":
        log_login(conn, row["id"], ip, False, "suspended")
        conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail="Account sospeso. Contatta il supporto.")

    # Calcola stato licenza
    remaining = days_left(row["expires_at"])
    warning_msg = None
    grace_mode = False

    if remaining == 0:
        # Verifica grace period
        grace_until = row["grace_until"]
        if grace_until:
            grace_remaining = days_left(grace_until)
            if grace_remaining > 0:
                grace_mode = True
                warning_msg = (
                    f"⚠️ La tua licenza è scaduta. "
                    f"Hai ancora {grace_remaining} giorni di accesso. "
                    f"Rinnova subito per non perdere l'accesso."
                )
            else:
                # Grace period esaurito
                conn.execute("UPDATE users SET status='expired' WHERE id=?", (row["id"],))
                log_login(conn, row["id"], ip, False, "license_expired")
                conn.commit()
                conn.close()
                raise HTTPException(
                    status_code=403,
                    detail="Licenza scaduta. Contatta il supporto per rinnovare."
                )
        else:
            # Imposta grace period al primo accesso dopo scadenza
            grace_date = (datetime.utcnow() + timedelta(days=GRACE_PERIOD_DAYS)).isoformat()
            conn.execute(
                "UPDATE users SET grace_until=? WHERE id=?",
                (grace_date, row["id"])
            )
            grace_mode = True
            warning_msg = (
                f"⚠️ La tua licenza è scaduta. "
                f"Hai {GRACE_PERIOD_DAYS} giorni di grazia per rinnovare."
            )
    elif remaining <= WARN_BEFORE_DAYS:
        warning_msg = f"ℹ️ La tua licenza scade tra {remaining} giorni. Pensa al rinnovo!"

    # Aggiorna statistiche login
    conn.execute(
        """UPDATE users SET 
           last_login=datetime('now'), last_ip=?, login_count=login_count+1
           WHERE id=?""",
        (ip, row["id"])
    )
    log_login(conn, row["id"], ip, True)
    conn.commit()
    conn.close()

    # Genera token JWT (24h di validità, il client ri-verifica al prossimo avvio)
    token = create_token({
        "sub": row["email"],
        "user_id": row["id"],
        "plan": row["plan"],
        "is_admin": bool(row["is_admin"]),
        "expires_at": row["expires_at"],
        "grace": grace_mode
    })

    return LoginResponse(
        token=token,
        email=row["email"],
        expires_at=row["expires_at"],
        days_left=remaining,
        is_admin=bool(row["is_admin"]),
        warning=warning_msg,
        grace_mode=grace_mode
    )


@app.get("/auth/verify")
def verify_token(current_user: str = Depends(get_current_user)):
    """Verifica che il token sia ancora valido (chiamata periodica dell'app)"""
    conn = get_db()
    row = conn.execute(
        "SELECT status, expires_at, grace_until FROM users WHERE email=?",
        (current_user,)
    ).fetchone()
    conn.close()

    if not row or row["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Account non attivo")

    remaining = days_left(row["expires_at"])
    grace_mode = False

    if remaining == 0 and row["grace_until"]:
        grace_remaining = days_left(row["grace_until"])
        if grace_remaining == 0:
            raise HTTPException(status_code=403, detail="Licenza scaduta")
        grace_mode = True

    return {"valid": True, "days_left": remaining, "grace_mode": grace_mode}


@app.post("/auth/change-password")
def change_password(req: PasswordChange, current_user: str = Depends(get_current_user)):
    """Cambio password autenticato"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE email=?", (current_user,)
    ).fetchone()

    if not verify_password(req.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Password attuale errata")

    if len(req.new_password) < 8:
        conn.close()
        raise HTTPException(status_code=400, detail="La nuova password deve essere di almeno 8 caratteri")

    conn.execute(
        "UPDATE users SET password_hash=? WHERE email=?",
        (hash_password(req.new_password), current_user)
    )
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
#  ENDPOINT ADMIN (protetti da ADMIN_KEY nell'header)
# ─────────────────────────────────────────────
@app.post("/admin/users", dependencies=[Depends(require_admin)])
def create_user(user: UserCreate):
    """Crea nuovo utente (solo admin)"""
    expires = (datetime.utcnow() + timedelta(days=user.expires_days)).date().isoformat()
    conn = get_db()

    try:
        conn.execute(
            """INSERT INTO users (email, password_hash, full_name, plan, expires_at)
               VALUES (?,?,?,?,?)""",
            (
                user.email.lower().strip(),
                hash_password(user.password),
                user.full_name,
                user.plan,
                expires
            )
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE email=?", (user.email.lower(),)
        ).fetchone()
        conn.close()
        return {
            "id": row["id"],
            "email": row["email"],
            "expires_at": row["expires_at"],
            "plan": row["plan"]
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Email già registrata")



# ─ REGISTRAZIONE CON CODICE INVITO ────────────────────────────────────────────
@app.post("/auth/register")
def register(req: RegisterRequest, x_forwarded_for: str = Header(None)):
    """Registrazione autonoma con codice invito"""
    conn = get_db()
    ip = x_forwarded_for or "unknown"

    # Verifica codice invito
    invite = conn.execute(
        "SELECT * FROM invite_codes WHERE code=? AND is_active=1",
        (req.invite_code.strip().upper(),)
    ).fetchone()

    if not invite:
        conn.close()
        raise HTTPException(status_code=400, detail="Codice invito non valido o scaduto")

    if invite["used_count"] >= invite["max_uses"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Codice invito già utilizzato")

    # Validazione email e password
    email = req.email.strip().lower()
    if len(req.password) < 8:
        conn.close()
        raise HTTPException(status_code=400, detail="La password deve essere di almeno 8 caratteri")

    # Calcola scadenza
    expires = (datetime.utcnow() + timedelta(days=invite["expires_days"])).date().isoformat()

    try:
        conn.execute(
            """INSERT INTO users (email, password_hash, full_name, plan, expires_at, invite_code)
               VALUES (?,?,?,?,?,?)""",
            (email, hash_password(req.password), req.full_name,
             invite["plan"], expires, req.invite_code.strip().upper())
        )
        # Aggiorna contatore usi
        conn.execute(
            "UPDATE invite_codes SET used_count=used_count+1 WHERE code=?",
            (req.invite_code.strip().upper(),)
        )
        # Disattiva se monouso
        if invite["max_uses"] == 1:
            conn.execute(
                "UPDATE invite_codes SET is_active=0 WHERE code=?",
                (req.invite_code.strip().upper(),)
            )
        conn.commit()

        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return {
            "id": row["id"],
            "email": row["email"],
            "plan": row["plan"],
            "expires_at": row["expires_at"],
            "message": "Registrazione completata! Accedi con le tue credenziali."
        }

    except Exception as e:
        conn.close()
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Email già registrata")
        raise HTTPException(status_code=500, detail="Errore durante la registrazione")

@app.get("/admin/users", dependencies=[Depends(require_admin)])
def list_users():
    """Lista tutti gli utenti con stato licenza"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY registered_at DESC"
    ).fetchall()
    conn.close()

    users = []
    for r in rows:
        remaining = days_left(r["expires_at"])
        users.append({
            "id": r["id"],
            "email": r["email"],
            "full_name": r["full_name"],
            "plan": r["plan"],
            "status": r["status"],
            "registered_at": r["registered_at"],
            "expires_at": r["expires_at"],
            "days_left": remaining,
            "last_login": r["last_login"],
            "login_count": r["login_count"],
            "notes": r["notes"]
        })
    return users


@app.patch("/admin/users/{user_id}/extend", dependencies=[Depends(require_admin)])
def extend_license(user_id: int, days: int):
    """Estende la licenza di N giorni dalla data attuale di scadenza"""
    conn = get_db()
    row = conn.execute("SELECT expires_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato")

    current_exp = datetime.fromisoformat(row["expires_at"])
    # Se già scaduta, parte da oggi
    base = max(current_exp, datetime.utcnow())
    new_exp = (base + timedelta(days=days)).date().isoformat()

    conn.execute(
        "UPDATE users SET expires_at=?, status='active', grace_until=NULL WHERE id=?",
        (new_exp, user_id)
    )
    conn.commit()
    conn.close()
    return {"user_id": user_id, "new_expires_at": new_exp}


@app.patch("/admin/users/{user_id}/suspend", dependencies=[Depends(require_admin)])
def suspend_user(user_id: int):
    """Sospende un utente"""
    conn = get_db()
    conn.execute("UPDATE users SET status='suspended' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "status": "suspended"}


@app.patch("/admin/users/{user_id}/activate", dependencies=[Depends(require_admin)])
def activate_user(user_id: int):
    """Riattiva un utente sospeso"""
    conn = get_db()
    conn.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "status": "active"}


@app.patch("/admin/users/{user_id}/notes", dependencies=[Depends(require_admin)])
def update_notes(user_id: int, notes: str):
    """Aggiorna note admin per un utente"""
    conn = get_db()
    conn.execute("UPDATE users SET notes=? WHERE id=?", (notes, user_id))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "notes": notes}


@app.get("/admin/stats", dependencies=[Depends(require_admin)])
def stats():
    """Statistiche generali"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM users WHERE status='active'").fetchone()[0]
    expiring_soon = conn.execute(
        """SELECT COUNT(*) FROM users WHERE status='active' AND
           julianday(expires_at) - julianday('now') BETWEEN 0 AND ?""",
        (WARN_BEFORE_DAYS,)
    ).fetchone()[0]
    expired = conn.execute(
        "SELECT COUNT(*) FROM users WHERE status='expired' OR expires_at < date('now')"
    ).fetchone()[0]
    logins_today = conn.execute(
        "SELECT COUNT(*) FROM login_log WHERE date(timestamp)=date('now') AND success=1"
    ).fetchone()[0]
    conn.close()

    return {
        "total_users": total,
        "active": active,
        "expiring_soon": expiring_soon,
        "expired": expired,
        "logins_today": logins_today
    }


@app.get("/admin/login-log/{user_id}", dependencies=[Depends(require_admin)])
def login_log(user_id: int, limit: int = 50):
    """Log accessi di un utente"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM login_log WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─ ADMIN: GESTIONE INVITI ─────────────────────────────────────────────────────
@app.post("/admin/invites", dependencies=[Depends(require_admin)])
def create_invite(invite: InviteCreate):
    """Crea un codice invito"""
    import string
    ALPHABET = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(ALPHABET) for _ in range(8))
    conn = get_db()
    conn.execute(
        """INSERT INTO invite_codes (code, plan, expires_days, max_uses, note)
           VALUES (?,?,?,?,?)""",
        (code, invite.plan, invite.expires_days, invite.max_uses, invite.note)
    )
    conn.commit()
    conn.close()
    return {
        "code": code,
        "plan": invite.plan,
        "expires_days": invite.expires_days,
        "max_uses": invite.max_uses,
        "note": invite.note
    }


@app.get("/admin/invites", dependencies=[Depends(require_admin)])
def list_invites():
    """Lista tutti i codici invito"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM invite_codes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/admin/invites/{code}/revoke", dependencies=[Depends(require_admin)])
def revoke_invite(code: str):
    """Revoca un codice invito"""
    conn = get_db()
    conn.execute("UPDATE invite_codes SET is_active=0 WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()
    return {"code": code.upper(), "is_active": False}




@app.patch("/admin/users/{user_id}/promote", dependencies=[Depends(require_admin)])
def promote_to_admin(user_id: int):
    """Promuove un utente ad admin"""
    conn = get_db()
    conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "is_admin": True}


@app.patch("/admin/users/{user_id}/demote", dependencies=[Depends(require_admin)])
def demote_from_admin(user_id: int):
    """Rimuove privilegi admin"""
    conn = get_db()
    conn.execute("UPDATE users SET is_admin=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "is_admin": False}
@app.delete("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: int):
    """Elimina un utente"""
    conn = get_db()
    conn.execute("DELETE FROM login_log WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"deleted": user_id}


# ─────────────────────────────────────────────
#  TRADUZIONI CENTRALIZZATE (PUBBLICO)
# ─────────────────────────────────────────────
TRANSLATIONS_DB = Path("translations.db")

@app.get("/translations/version")
def translations_version():
    """Ritorna hash del file traduzioni per verificare aggiornamenti"""
    if not TRANSLATIONS_DB.exists():
        raise HTTPException(status_code=404, detail="File traduzioni non trovato")
    
    import hashlib
    sha256 = hashlib.sha256()
    with open(TRANSLATIONS_DB, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    return {
        "hash": sha256.hexdigest()[:16],
        "size_bytes": TRANSLATIONS_DB.stat().st_size,
        "updated_at": datetime.fromtimestamp(TRANSLATIONS_DB.stat().st_mtime).isoformat()
    }


@app.get("/translations/download")
def translations_download():
    """Scarica il file translations.db (aperto a tutti)"""
    if not TRANSLATIONS_DB.exists():
        raise HTTPException(status_code=404, detail="File traduzioni non trovato")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=TRANSLATIONS_DB,
        media_type="application/octet-stream",
        filename="translations.db"
    )


@app.post("/admin/translations/upload", dependencies=[Depends(require_admin)])
async def upload_translations(file: UploadFile):
    """Upload nuovo file traduzioni (solo admin)"""
    from fastapi import UploadFile
    
    # Verifica che sia un DB SQLite
    content = await file.read()
    
    temp_path = Path("translations_temp.db")
    temp_path.write_bytes(content)
    
    try:
        conn = sqlite3.connect(temp_path)
        # Verifica struttura base
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
        ).fetchone()
        conn.close()
        
        if not tables:
            temp_path.unlink()
            raise HTTPException(status_code=400, detail="DB non contiene tabella 'translations'")
        
        # Sostituisci il file principale
        if TRANSLATIONS_DB.exists():
            TRANSLATIONS_DB.unlink()
        temp_path.rename(TRANSLATIONS_DB)
        
        return {
            "success": True,
            "size_bytes": TRANSLATIONS_DB.stat().st_size,
            "message": "File traduzioni aggiornato"
        }
    
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=f"Errore: {str(e)}")