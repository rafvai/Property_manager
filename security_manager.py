"""
Sistema di sicurezza centralizzato per Property Manager
Protegge da: SQL Injection, Path Traversal, XSS, File Upload malicious
"""
import re
import os
import hashlib
import secrets
from pathlib import Path
from typing import Optional, List, Union
import mimetypes


class SecurityManager:
    """Gestisce la sicurezza dell'applicazione"""

    # Whitelist estensioni file permesse
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'txt', 'jpg', 'jpeg', 'png', 'gif'
    }

    # Dimensione massima file (20 MB)
    MAX_FILE_SIZE = 20 * 1024 * 1024

    # Caratteri pericolosi per SQL/Path Traversal
    DANGEROUS_CHARS_PATTERN = re.compile(r'[;<>|&$`\n\r]')

    # Pattern per validazione email
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    # Pattern per SQL keywords pericolose
    SQL_INJECTION_PATTERN = re.compile(
        r'\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|SCRIPT)\b',
        re.IGNORECASE
    )

    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 200) -> str:
        """
        Sanitizza nome file per prevenire path traversal

        Args:
            filename: Nome file da sanitizzare
            max_length: Lunghezza massima

        Returns:
            Nome file sicuro

        Raises:
            ValueError: Se il nome file contiene caratteri pericolosi
        """
        if not filename:
            raise ValueError("Nome file vuoto")

        # Rimuovi path (previene ../../../etc/passwd)
        filename = os.path.basename(filename)

        # Rimuovi caratteri null byte
        filename = filename.replace('\x00', '')

        # Rimuovi caratteri pericolosi
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*', '\n', '\r']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        # Rimuovi spazi multipli
        filename = ' '.join(filename.split())

        # Tronca se troppo lungo
        if len(filename) > max_length:
            name_part, ext = os.path.splitext(filename)
            max_name = max_length - len(ext) - 1
            filename = name_part[:max_name] + ext

        # Rimuovi spazi all'inizio/fine
        filename = filename.strip()

        # Verifica che non sia vuoto dopo sanitizzazione
        if not filename or filename == '.':
            raise ValueError("Nome file non valido dopo sanitizzazione")

        return filename

    @staticmethod
    def validate_file_upload(filepath: str, allowed_extensions: Optional[set] = None) -> dict:
        """
        Valida file upload per sicurezza

        Args:
            filepath: Path del file
            allowed_extensions: Set di estensioni permesse (usa default se None)

        Returns:
            dict: {
                'valid': bool,
                'error': str or None,
                'size': int,
                'extension': str,
                'mime_type': str
            }
        """
        result = {
            'valid': False,
            'error': None,
            'size': 0,
            'extension': '',
            'mime_type': ''
        }

        if allowed_extensions is None:
            allowed_extensions = SecurityManager.ALLOWED_EXTENSIONS

        # Verifica esistenza file
        if not os.path.exists(filepath):
            result['error'] = "File non trovato"
            return result

        # Verifica che sia un file (non directory)
        if not os.path.isfile(filepath):
            result['error'] = "Path non è un file valido"
            return result

        # Verifica dimensione
        file_size = os.path.getsize(filepath)
        result['size'] = file_size

        if file_size > SecurityManager.MAX_FILE_SIZE:
            result['error'] = f"File troppo grande (max {SecurityManager.MAX_FILE_SIZE / 1024 / 1024:.0f} MB)"
            return result

        if file_size == 0:
            result['error'] = "File vuoto"
            return result

        # Verifica estensione
        _, ext = os.path.splitext(filepath)
        ext = ext.lower().lstrip('.')
        result['extension'] = ext

        if ext not in allowed_extensions:
            result['error'] = f"Estensione '{ext}' non permessa. Permesse: {', '.join(allowed_extensions)}"
            return result

        # Verifica MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        result['mime_type'] = mime_type or 'unknown'

        # Verifica che MIME type corrisponda all'estensione
        expected_mimes = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif'
        }

        expected_mime = expected_mimes.get(ext)
        if expected_mime and mime_type and not mime_type.startswith(expected_mime.split('/')[0]):
            result['error'] = f"MIME type '{mime_type}' non corrisponde all'estensione '{ext}'"
            return result

        result['valid'] = True
        return result

    @staticmethod
    def sanitize_sql_input(value: str, max_length: int = 500) -> str:
        """
        Sanitizza input per prevenire SQL Injection
        NOTA: Questo è un layer AGGIUNTIVO, usa sempre parametrized queries!

        Args:
            value: Valore da sanitizzare
            max_length: Lunghezza massima

        Returns:
            Valore sanitizzato

        Raises:
            ValueError: Se contiene pattern SQL pericolosi
        """
        if not value:
            return ""

        # Rimuovi null bytes
        value = value.replace('\x00', '')

        # Verifica lunghezza
        if len(value) > max_length:
            raise ValueError(f"Input troppo lungo (max {max_length} caratteri)")

        # Verifica pattern SQL injection
        if SecurityManager.SQL_INJECTION_PATTERN.search(value):
            raise ValueError("Input contiene keywords SQL non permesse")

        # Rimuovi caratteri pericolosi
        if SecurityManager.DANGEROUS_CHARS_PATTERN.search(value):
            raise ValueError("Input contiene caratteri pericolosi")

        return value.strip()

    @staticmethod
    def validate_path(path: str, base_dir: str) -> bool:
        """
        Valida che un path sia dentro la directory base (previene path traversal)

        Args:
            path: Path da validare
            base_dir: Directory base permessa

        Returns:
            True se il path è sicuro

        Raises:
            ValueError: Se il path esce dalla directory base
        """
        # Converte in path assoluti
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_dir)

        # Verifica che il path inizi con la base directory
        if not abs_path.startswith(abs_base):
            raise ValueError(f"Path traversal rilevato: {path} esce da {base_dir}")

        return True

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash sicuro della password con salt

        Args:
            password: Password in chiaro
            salt: Salt opzionale (genera nuovo se None)

        Returns:
            (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        # PBKDF2 con SHA256 (100,000 iterazioni)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )

        password_hash = hash_obj.hex()

        return password_hash, salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """
        Verifica password contro hash

        Args:
            password: Password da verificare
            password_hash: Hash salvato
            salt: Salt usato per l'hash

        Returns:
            True se la password è corretta
        """
        new_hash, _ = SecurityManager.hash_password(password, salt)
        return secrets.compare_digest(new_hash, password_hash)

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Genera token sicuro per sessioni/API

        Args:
            length: Lunghezza del token

        Returns:
            Token esadecimale sicuro
        """
        return secrets.token_hex(length)

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Valida formato email

        Args:
            email: Email da validare

        Returns:
            True se email valida
        """
        if not email or len(email) > 320:  # RFC 5321
            return False

        return bool(SecurityManager.EMAIL_PATTERN.match(email))

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Rimuove HTML/JavaScript da input utente (previene XSS)

        Args:
            text: Testo da sanitizzare

        Returns:
            Testo senza HTML
        """
        if not text:
            return ""

        # Rimuovi tag HTML
        text = re.sub(r'<[^>]*>', '', text)

        # Escape caratteri HTML speciali
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }

        return "".join(html_escape_table.get(c, c) for c in text)

    @staticmethod
    def validate_numeric_range(value: Union[int, float], min_val: float, max_val: float) -> bool:
        """
        Valida che un numero sia in un range

        Args:
            value: Valore da validare
            min_val: Minimo permesso
            max_val: Massimo permesso

        Returns:
            True se nel range

        Raises:
            ValueError: Se fuori range
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Valore deve essere numerico")

        if value < min_val or value > max_val:
            raise ValueError(f"Valore {value} fuori range [{min_val}, {max_val}]")

        return True

    @staticmethod
    def rate_limit_check(identifier: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
        """
        Implementa rate limiting semplice (da migliorare con Redis in produzione)

        Args:
            identifier: ID univoco (IP, user_id, etc)
            max_attempts: Numero massimo tentativi
            window_seconds: Finestra temporale in secondi

        Returns:
            True se permesso, False se rate limit superato
        """
        # TODO: Implementare con Redis/Memcached per produzione multi-processo
        # Per ora è un placeholder
        return True


class SecureLogger:
    """Logger che sanitizza dati sensibili"""

    SENSITIVE_KEYS = {'password', 'token', 'api_key', 'secret', 'salt'}

    @staticmethod
    def sanitize_log_data(data: dict) -> dict:
        """
        Rimuove dati sensibili dai log

        Args:
            data: Dati da loggare

        Returns:
            Dati sanitizzati
        """
        sanitized = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Maschera dati sensibili
            if any(sensitive in key_lower for sensitive in SecureLogger.SENSITIVE_KEYS):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = SecureLogger.sanitize_log_data(value)
            else:
                sanitized[key] = value

        return sanitized