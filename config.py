import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import keyring


class Config:
    """
    Gestisce la configurazione in modo sicuro
    - NO password hardcoded
    - Usa variabili ambiente
    - Cripta credenziali sensibili
    """

    # Service name per keyring
    SERVICE_NAME = "PropertyManager"

    # Determina ambiente
    ENV = os.getenv('APP_ENV', 'development')

    # Directory base
    if ENV == 'saas':
        BASE_DIR = None
        DOCS_DIR = None
        EXPORTS_DIR = None
        LOGS_DIR = Path('/tmp/propertymanager/logs') if os.name != 'nt' else \
            Path(os.getenv('TEMP')) / 'propertymanager' / 'logs'
    else:
        # Desktop: usa AppData (Windows) o equivalente
        if os.name == 'nt':
            BASE_DIR = Path(os.getenv('APPDATA')) / 'PropertyManager'
        else:
            BASE_DIR = Path.home() / '.propertymanager'

        BASE_DIR.mkdir(parents=True, exist_ok=True)

        # PRODUZIONE: usa directory system
        if ENV == 'production':
            DOCS_DIR = BASE_DIR / 'docs'
            EXPORTS_DIR = BASE_DIR / 'exports'
            LOGS_DIR = BASE_DIR / 'logs'
        else:
            # Development: directory corrente
            DOCS_DIR = Path('docs').absolute()
            EXPORTS_DIR = Path('exports').absolute()
            LOGS_DIR = Path('logs').absolute()

        # Crea directories
        for dir_path in [DOCS_DIR, EXPORTS_DIR, LOGS_DIR]:
            if dir_path:
                dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Ottiene o genera chiave di cifratura
        ATTENZIONE: In produzione, usa un Key Management System (KMS)
        """
        key_file = Config.BASE_DIR / '.encryption_key'

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Genera nuova chiave
            key = Fernet.generate_key()

            # Salva con permessi restrittivi
            key_file.touch(mode=0o600)
            with open(key_file, 'wb') as f:
                f.write(key)

            return key

    @staticmethod
    def encrypt_password(password: str) -> str:
        """
        Cripta una password

        Args:
            password: Password in chiaro

        Returns:
            Password criptata (base64)
        """
        key = Config._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(password.encode('utf-8'))
        return encrypted.decode('utf-8')

    @staticmethod
    def decrypt_password(encrypted_password: str) -> str:
        """
        Decripta una password

        Args:
            encrypted_password: Password criptata

        Returns:
            Password in chiaro
        """
        key = Config._get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_password.encode('utf-8'))
        return decrypted.decode('utf-8')

    @staticmethod
    def save_db_credentials(username: str, password: str, host: str,
                            port: int, database: str):
        """
        Salva credenziali database in modo sicuro usando keyring

        Args:
            username: Username database
            password: Password database
            host: Host database
            port: Porta
            database: Nome database
        """
        credentials = {
            'username': username,
            'host': host,
            'port': port,
            'database': database
        }

        # Salva password in keyring (encrypted by OS)
        keyring.set_password(Config.SERVICE_NAME, 'db_password', password)

        # Salva altri dati in file criptato
        config_file = Config.BASE_DIR / '.db_config'
        encrypted_data = Config.encrypt_password(json.dumps(credentials))

        config_file.touch(mode=0o600)
        with open(config_file, 'w') as f:
            f.write(encrypted_data)

    @staticmethod
    def load_db_credentials() -> Optional[Dict[str, Any]]:
        """
        Carica credenziali database salvate

        Returns:
            Dict con credenziali o None
        """
        config_file = Config.BASE_DIR / '.db_config'

        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r') as f:
                encrypted_data = f.read()

            decrypted = Config.decrypt_password(encrypted_data)
            credentials = json.loads(decrypted)

            # Recupera password da keyring
            password = keyring.get_password(
                Config.SERVICE_NAME,
                'db_password'
            )

            if password:
                credentials['password'] = password

            return credentials

        except Exception as e:
            print(f"Errore caricamento credenziali: {e}")
            return None

    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """
        Ritorna configurazione DB basata su ambiente
        CON GESTIONE SICURA CREDENZIALI
        """

        if Config.ENV in ['development', 'production']:
            # Desktop: SQLite (no credenziali necessarie)
            db_name = 'property_manager.db' if Config.ENV == 'development' \
                else 'property_manager_prod.db'

            return {
                'type': 'sqlite',
                'path': str(Config.BASE_DIR / db_name)
            }

        elif Config.ENV == 'saas':
            # SaaS: Database cloud

            # PRIORITÀ 1: Variabili ambiente (production)
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_pass = os.getenv('DB_PASSWORD')

            # PRIORITÀ 2: Credenziali salvate
            if not all([db_host, db_port, db_name, db_user, db_pass]):
                saved_creds = Config.load_db_credentials()

                if saved_creds:
                    db_host = saved_creds.get('host', db_host)
                    db_port = saved_creds.get('port', db_port)
                    db_name = saved_creds.get('database', db_name)
                    db_user = saved_creds.get('username', db_user)
                    db_pass = saved_creds.get('password', db_pass)

            # Verifica che tutte le credenziali siano presenti
            if not all([db_host, db_port, db_name, db_user, db_pass]):
                raise ValueError(
                    "Credenziali database incomplete! "
                    "Imposta variabili ambiente o salva credenziali."
                )

            db_type = os.getenv('DB_TYPE', 'postgresql')

            return {
                'type': db_type,
                'host': db_host,
                'port': int(db_port),
                'database': db_name,
                'user': db_user,
                'password': db_pass,
            }

        # Fallback
        return {
            'type': 'sqlite',
            'path': 'property_manager_fallback.db'
        }

    @staticmethod
    def get_allowed_hosts() -> list:
        """
        Ritorna lista host permessi per connessioni database
        Previene connection string injection
        """
        allowed = os.getenv('ALLOWED_DB_HOSTS', '').split(',')

        # Default hosts fidati
        default_hosts = [
            'localhost',
            '127.0.0.1',
            '::1'
        ]

        # Merge e rimuovi duplicati
        all_hosts = list(set(allowed + default_hosts))

        return [h.strip() for h in all_hosts if h.strip()]

    @staticmethod
    def validate_db_host(host: str) -> bool:
        """
        Valida che un host sia nella whitelist

        Args:
            host: Host da validare

        Returns:
            True se permesso

        Raises:
            ValueError: Se host non permesso
        """
        if not host:
            raise ValueError("Host database vuoto")

        allowed_hosts = Config.get_allowed_hosts()

        # Se lista vuota, permetti tutto (dev mode)
        if not allowed_hosts:
            return True

        # Verifica whitelist
        if host not in allowed_hosts:
            raise ValueError(
                f"Host '{host}' non permesso. "
                f"Hosts permessi: {', '.join(allowed_hosts)}"
            )

        return True

    @staticmethod
    def get_session_config() -> Dict[str, Any]:
        """
        Configurazione sessioni sicure
        """
        return {
            'secret_key': os.getenv('SESSION_SECRET_KEY') or \
                          Config._get_encryption_key().decode('utf-8'),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '3600')),  # 1 ora
            'secure_cookies': Config.ENV == 'saas',
            'httponly_cookies': True,
            'samesite': 'Strict'
        }

    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        """
        Configurazione sicurezza generale
        """
        return {
            # Rate limiting
            'max_login_attempts': int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
            'login_timeout_minutes': int(os.getenv('LOGIN_TIMEOUT', '15')),

            # File upload
            'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '20')),
            'allowed_extensions': {
                'pdf', 'doc', 'docx', 'xls', 'xlsx',
                'txt', 'jpg', 'jpeg', 'png', 'gif'
            },

            # Password policy
            'min_password_length': int(os.getenv('MIN_PASSWORD_LENGTH', '8')),
            'require_special_chars': os.getenv('REQUIRE_SPECIAL_CHARS', 'true').lower() == 'true',
            'password_expiry_days': int(os.getenv('PASSWORD_EXPIRY_DAYS', '90')),

            # Logging
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_sensitive_data': os.getenv('LOG_SENSITIVE_DATA', 'false').lower() == 'true',

            # HTTPS
            'force_https': Config.ENV == 'saas',
            'hsts_max_age': int(os.getenv('HSTS_MAX_AGE', '31536000')),  # 1 anno
        }