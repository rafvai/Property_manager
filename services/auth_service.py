"""
services/auth_service.py — lato CLIENT (Property Manager Desktop)

Gestisce:
- Login contro il server remoto delle licenze
- Cache locale cifrata (max 7 giorni offline)
- Verifica stato licenza (grace, warning, scaduta)
"""
import contextlib
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from config import Config

try:
    import requests  # noqa: F401 — verifica disponibilità, i metodi lo importano localmente
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def _utcnow() -> datetime:
    """UTC naive, coerente con le date ISO in cache (datetime.utcnow è deprecato)."""
    return datetime.now(UTC).replace(tzinfo=None)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
LICENSE_SERVER_URL = Config.LICENSE_SERVER_URL
OFFLINE_CACHE_DAYS = 7
CONNECT_TIMEOUT    = 5
READ_TIMEOUT       = 10

_CACHE_DIR = Path(os.getenv("APPDATA")) / "PropertyManager" if os.name == "nt" else Path.home() / ".propertymanager"

_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_FILE    = _CACHE_DIR / ".license_cache"


def _get_hmac_key() -> bytes:
    """
    Chiave HMAC per la firma della cache offline, casuale e per-installazione,
    conservata nel portachiavi di sistema (Windows Credential Manager / macOS
    Keychain). Una chiave hardcoded nel sorgente renderebbe la firma falsificabile
    da chiunque decompili l'eseguibile. Fallback alla chiave legacy se il
    portachiavi non è disponibile.
    """
    try:
        import keyring
        stored = keyring.get_password("PropertyManager", "cache_hmac_key")
        if not stored:
            stored = secrets.token_hex(32)
            keyring.set_password("PropertyManager", "cache_hmac_key", stored)
        return stored.encode()
    except Exception:
        return b"pm-license-cache-v1"


_HMAC_KEY = _get_hmac_key()


# ─────────────────────────────────────────────
#  RISULTATO AUTH
# ─────────────────────────────────────────────
class AuthResult:
    def __init__(self, success: bool, mode: str = "online",
                 token: str = None, email: str = None,
                 expires_at: str = None, days_left: int = 0,
                 is_admin: bool = False,
                 warning: str = None, grace_mode: bool = False,
                 error: str = None):
        self.success    = success
        self.mode       = mode
        self.token      = token
        self.email      = email
        self.expires_at = expires_at
        self.days_left  = days_left
        self.is_admin   = is_admin
        self.warning    = warning
        self.grace_mode = grace_mode
        self.error      = error


# ─────────────────────────────────────────────
#  AUTH SERVICE
# ─────────────────────────────────────────────
class AuthService:

    def __init__(self, logger, server_url: str = None):
        self.logger     = logger
        self.server_url = (server_url or LICENSE_SERVER_URL).rstrip("/")

        if self.server_url.startswith("http://") and \
                not any(h in self.server_url for h in ("localhost", "127.0.0.1")):
            self.logger.warning(
                "AuthService: il server licenze usa HTTP non cifrato — "
                "le credenziali viaggiano in chiaro. Configura HTTPS sul server "
                "e aggiorna LICENSE_SERVER_URL."
            )

    # ── Login principale ────────────────────────────────────────────
    def login(self, email: str, password: str) -> AuthResult:
        email = email.strip().lower()

        if REQUESTS_AVAILABLE:
            result = self._login_online(email, password)
            if result is not None:
                return result

        return self._login_offline(email, password)

    def _login_online(self, email: str, password: str) -> AuthResult | None:
        try:
            import requests as req
            resp = req.post(
                f"{self.server_url}/auth/login",
                json={"email": email, "password": password, "client_info": "desktop-v1"},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )

            if resp.status_code == 200:
                data = resp.json()
                self.logger.info(f"AuthService: Login online OK per {email}")
                self._save_cache(email, password, data)
                return AuthResult(
                    success    = True,
                    mode       = "online",
                    token      = data["token"],
                    email      = data["email"],
                    expires_at = data["expires_at"],
                    days_left  = data["days_left"],
                    is_admin   = data.get("is_admin", False),
                    warning    = data.get("warning"),
                    grace_mode = data.get("grace_mode", False)
                )

            elif resp.status_code in (401, 403):
                detail = resp.json().get("detail", "Accesso negato")
                self.logger.warning(f"AuthService: Login negato ({resp.status_code}): {detail}")
                return AuthResult(success=False, mode="failed", error=detail)

            else:
                self.logger.error(f"AuthService: Risposta server inattesa: {resp.status_code}")
                return None

        except Exception as e:
            self.logger.warning(f"AuthService: Server non raggiungibile: {e}")
            return None

    def _login_offline(self, email: str, password: str) -> AuthResult:
        cache = self._load_cache()

        if not cache:
            return AuthResult(
                success=False, mode="failed",
                error=(
                    "Impossibile connettersi al server delle licenze.\n"
                    "Nessuna sessione precedente trovata.\n"
                    "Verifica la connessione internet e riprova."
                )
            )

        if cache.get("email") != email:
            return AuthResult(
                success=False, mode="failed",
                error="Email non corrisponde alla sessione salvata.\nConnettiti a internet per accedere."
            )

        if not self._verify_pwd_hash(password, cache.get("pwd_hash", "")):
            return AuthResult(success=False, mode="failed", error="Password errata.")

        cached_at = datetime.fromisoformat(cache["cached_at"])
        age_days  = (_utcnow() - cached_at).days

        if age_days > OFFLINE_CACHE_DAYS:
            self._clear_cache()
            return AuthResult(
                success=False, mode="failed",
                error=(
                    f"La sessione offline è scaduta ({age_days} giorni fa).\n"
                    "Connettiti a internet per rinnovare l'accesso."
                )
            )

        expires_at = cache.get("expires_at", "")
        days_left  = self._days_left(expires_at)
        grace_mode = cache.get("grace_mode", False)

        if days_left == 0 and not grace_mode:
            return AuthResult(
                success=False, mode="failed",
                error="La licenza è scaduta. Connettiti a internet per rinnovare."
            )

        remaining_offline = OFFLINE_CACHE_DAYS - age_days
        warning = (
            f"⚠️ Modalità offline – connessione assente da {age_days} giorni.\n"
            f"Connettiti a internet entro {remaining_offline} giorni."
        )

        self.logger.info(f"AuthService: Login offline da cache per {email} (età {age_days}gg)")
        return AuthResult(
            success    = True,
            mode       = "offline_cache",
            token      = cache.get("token"),
            email      = email,
            expires_at = expires_at,
            days_left  = days_left,
            is_admin   = cache.get("is_admin", False),
            warning    = warning,
            grace_mode = grace_mode
        )

    # ── Cache locale firmata con HMAC ───────────────────────────────
    def _save_cache(self, email: str, password: str, server_data: dict):
        cache = {
            "email"      : email,
            "pwd_hash"   : self._hash_pwd(password),
            "token"      : server_data.get("token"),
            "expires_at" : server_data.get("expires_at"),
            "days_left"  : server_data.get("days_left"),
            "is_admin"   : server_data.get("is_admin", False),
            "grace_mode" : server_data.get("grace_mode", False),
            "cached_at"  : _utcnow().isoformat()
        }
        payload   = json.dumps(cache, sort_keys=True).encode()
        signature = hmac.digest(_HMAC_KEY, payload, "sha256").hex()
        _CACHE_FILE.write_text(json.dumps({"payload": cache, "sig": signature}), encoding="utf-8")
        with contextlib.suppress(Exception):
            _CACHE_FILE.chmod(0o600)

    def _load_cache(self) -> dict | None:
        if not _CACHE_FILE.exists():
            return None
        try:
            data      = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            payload   = json.dumps(data["payload"], sort_keys=True).encode()
            expected = hmac.digest(_HMAC_KEY, payload, "sha256").hex()
            if not hmac.compare_digest(data["sig"], expected):
                self.logger.warning("AuthService: Cache locale manomessa, ignorata")
                return None
            return data["payload"]
        except Exception as e:
            self.logger.warning(f"AuthService: Errore lettura cache: {e}")
            return None

    def _clear_cache(self):
        if _CACHE_FILE.exists():
            _CACHE_FILE.unlink()

    def logout(self):
        self._clear_cache()
        self.logger.info("AuthService: Logout, cache rimossa")

    # ── Utilità statiche ────────────────────────────────────────────
    @staticmethod
    def _hash_pwd(password: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), b"pm-local-salt", 100_000).hex()

    @staticmethod
    def _verify_pwd_hash(password: str, stored: str) -> bool:
        # FIX: confronto sicuro contro timing attack
        current = AuthService._hash_pwd(password)
        return hmac.compare_digest(current, stored)

    @staticmethod
    def _days_left(expires_at: str) -> int:
        try:
            return max(0, (datetime.fromisoformat(expires_at) - _utcnow()).days)
        except Exception:
            return 0
