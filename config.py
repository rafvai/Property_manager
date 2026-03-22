"""
config.py
=========
Unica fonte di verità per la configurazione dell'applicazione.
Carica le variabili da .env tramite python-dotenv.

Flusso di caricamento:
    1. Cerca .env nella directory corrente (ignorato da git)
    2. Fallback ai valori di default hardcoded (solo per development)

Per cambiare ambiente basta modificare APP_ENV nel file .env.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import keyring
from dotenv import load_dotenv


# ──────────────────────────────────────────────────────────────────
#  CARICAMENTO .env
#  load_dotenv() non sovrascrive variabili già presenti nell'ambiente
#  di sistema, quindi le variabili CI/CD hanno sempre la precedenza.
# ──────────────────────────────────────────────────────────────────
_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(_ENV_FILE)  # silenzioso se il file non esiste


class Config:
    """
    Gestisce la configurazione in modo sicuro.
    Tutte le variabili vengono lette da os.environ (popolato da .env).
    """

    # ── Identità tenant ─────────────────────────────────────────
    SERVICE_NAME       = "PropertyManager"
    CURRENT_TENANT_ID  = 'local'

    # ── Ambiente ─────────────────────────────────────────────────
    # Valori validi: development | production | saas
    ENV = os.getenv('APP_ENV', 'development')

    # ── Flag specifici development ───────────────────────────────
    # Se True, l'AppController bypassa completamente il login
    DEV_SKIP_LOGIN      = os.getenv('DEV_SKIP_LOGIN', 'false').lower() == 'true'
    # Credenziali pre-compilate nel form (solo dev, mai in production)
    DEV_LOGIN_EMAIL     = os.getenv('DEV_LOGIN_EMAIL', '')
    DEV_LOGIN_PASSWORD  = os.getenv('DEV_LOGIN_PASSWORD', '')

    # ── Directory base ───────────────────────────────────────────
    if ENV == 'saas':
        BASE_DIR   = None
        DOCS_DIR   = None
        EXPORTS_DIR = None
        LOGS_DIR   = Path('/tmp/propertymanager/logs') if os.name != 'nt' else \
            Path(os.getenv('TEMP', '/tmp')) / 'propertymanager' / 'logs'
    else:
        if os.name == 'nt':
            BASE_DIR = Path(os.getenv('APPDATA', '')) / 'PropertyManager'
        else:
            BASE_DIR = Path.home() / '.propertymanager'

        BASE_DIR.mkdir(parents=True, exist_ok=True)

        if ENV == 'production':
            DOCS_DIR    = BASE_DIR / 'docs'
            EXPORTS_DIR = BASE_DIR / 'exports'
            LOGS_DIR    = BASE_DIR / 'logs'
        else:
            # development: directory corrente per facilità di debug
            DOCS_DIR    = Path('docs').absolute()
            EXPORTS_DIR = Path('exports').absolute()
            LOGS_DIR    = Path('logs').absolute()

    # ────────────────────────────────────────────────────────────
    #  METODI STATICI
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def initialize_directories() -> list:
        """
        Crea le directory necessarie all'avvio.
        Va chiamato dopo QApplication, così gli errori
        possono essere mostrati all'utente.
        """
        errors = []
        dirs = [Config.BASE_DIR, Config.DOCS_DIR, Config.EXPORTS_DIR, Config.LOGS_DIR]
        for d in dirs:
            if d is None:
                continue
            try:
                Path(d).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"{d}: {e}")
        return errors

    @staticmethod
    def is_development() -> bool:
        return Config.ENV == 'development'

    @staticmethod
    def is_production() -> bool:
        return Config.ENV == 'production'

    @staticmethod
    def is_saas() -> bool:
        return Config.ENV == 'saas'

    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Ottiene o genera chiave di cifratura locale.
        In production usare un KMS esterno.
        """
        key_file = Config.BASE_DIR / '.encryption_key'

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()

        key = Fernet.generate_key()
        key_file.touch(mode=0o600)
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

    @staticmethod
    def encrypt_password(password: str) -> str:
        key = Config._get_encryption_key()
        return Fernet(key).encrypt(password.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_password(encrypted_password: str) -> str:
        key = Config._get_encryption_key()
        return Fernet(key).decrypt(encrypted_password.encode('utf-8')).decode('utf-8')

    @staticmethod
    def save_db_credentials(username: str, password: str, host: str,
                            port: int, database: str):
        credentials = {'username': username, 'host': host, 'port': port, 'database': database}
        keyring.set_password(Config.SERVICE_NAME, 'db_password', password)
        config_file = Config.BASE_DIR / '.db_config'
        encrypted_data = Config.encrypt_password(json.dumps(credentials))
        config_file.touch(mode=0o600)
        with open(config_file, 'w') as f:
            f.write(encrypted_data)

    @staticmethod
    def load_db_credentials() -> Optional[Dict[str, Any]]:
        config_file = Config.BASE_DIR / '.db_config'
        if not config_file.exists():
            return None
        try:
            with open(config_file, 'r') as f:
                encrypted_data = f.read()
            credentials = json.loads(Config.decrypt_password(encrypted_data))
            password = keyring.get_password(Config.SERVICE_NAME, 'db_password')
            if password:
                credentials['password'] = password
            return credentials
        except Exception as e:
            print(f"Errore caricamento credenziali: {e}")
            return None

    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Configurazione DB basata sull'ambiente."""
        if Config.ENV in ['development', 'production']:
            db_name = 'property_manager.db' if Config.is_development() \
                else 'property_manager_prod.db'
            return {
                'type': 'sqlite',
                'path': str(Config.BASE_DIR / db_name)
            }

        elif Config.ENV == 'saas':
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_pass = os.getenv('DB_PASSWORD')

            if not all([db_host, db_port, db_name, db_user, db_pass]):
                saved = Config.load_db_credentials()
                if saved:
                    db_host = saved.get('host', db_host)
                    db_port = saved.get('port', db_port)
                    db_name = saved.get('database', db_name)
                    db_user = saved.get('username', db_user)
                    db_pass = saved.get('password', db_pass)

            if not all([db_host, db_port, db_name, db_user, db_pass]):
                raise ValueError(
                    "Credenziali database incomplete! "
                    "Imposta le variabili DB_* nel file .env"
                )

            return {
                'type': os.getenv('DB_TYPE', 'postgresql'),
                'host': db_host,
                'port': int(db_port),
                'database': db_name,
                'user': db_user,
                'password': db_pass,
            }

        return {'type': 'sqlite', 'path': 'property_manager_fallback.db'}

    @staticmethod
    def get_allowed_hosts() -> list:
        allowed = os.getenv('ALLOWED_DB_HOSTS', '').split(',')
        default_hosts = ['localhost', '127.0.0.1', '::1']
        all_hosts = list(set(allowed + default_hosts))
        return [h.strip() for h in all_hosts if h.strip()]

    @staticmethod
    def validate_db_host(host: str) -> bool:
        if not host:
            raise ValueError("Host database vuoto")
        allowed_hosts = Config.get_allowed_hosts()
        if not allowed_hosts:
            return True
        if host not in allowed_hosts:
            raise ValueError(
                f"Host '{host}' non permesso. "
                f"Hosts permessi: {', '.join(allowed_hosts)}"
            )
        return True

    @staticmethod
    def get_session_config() -> Dict[str, Any]:
        return {
            'secret_key': os.getenv('SESSION_SECRET_KEY') or
                          Config._get_encryption_key().decode('utf-8'),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '3600')),
            'secure_cookies': Config.is_saas(),
            'httponly_cookies': True,
            'samesite': 'Strict'
        }

    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        return {
            'max_login_attempts'  : int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
            'login_timeout_minutes': int(os.getenv('LOGIN_TIMEOUT', '15')),
            'max_file_size_mb'    : int(os.getenv('MAX_FILE_SIZE_MB', '20')),
            'allowed_extensions'  : {
                'pdf', 'doc', 'docx', 'xls', 'xlsx',
                'txt', 'jpg', 'jpeg', 'png', 'gif'
            },
            'min_password_length' : int(os.getenv('MIN_PASSWORD_LENGTH', '8')),
            'require_special_chars': os.getenv('REQUIRE_SPECIAL_CHARS', 'true').lower() == 'true',
            'password_expiry_days': int(os.getenv('PASSWORD_EXPIRY_DAYS', '90')),
            'log_level'           : os.getenv('LOG_LEVEL', 'INFO'),
            'log_sensitive_data'  : os.getenv('LOG_SENSITIVE_DATA', 'false').lower() == 'true',
            'force_https'         : Config.is_saas(),
            'hsts_max_age'        : int(os.getenv('HSTS_MAX_AGE', '31536000')),
        }

    @staticmethod
    def print_summary(logger=None):
        """Stampa un riepilogo della configurazione attiva (utile all'avvio)."""
        lines = [
            "─" * 45,
            f"  Ambiente   : {Config.ENV}",
            f"  Skip login : {Config.DEV_SKIP_LOGIN}",
            f"  Log level  : {os.getenv('LOG_LEVEL', 'INFO')}",
            f"  Server URL : {os.getenv('LICENSE_SERVER_URL', 'non impostato')}",
            "─" * 45,
        ]
        for line in lines:
            if logger:
                logger.info(line)
            else:
                print(line)