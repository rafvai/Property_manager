"""
test_auth_service.py
====================
Test unitari per services/auth_service.py

Copertura:
- login: delega a _login_online / _login_offline
- _login_online: risposta 200, 401/403, errore server, eccezione rete
- _login_offline: cache valida, email errata, password errata, cache scaduta,
                  licenza scaduta, modalità grace
- _save_cache / _load_cache: firma HMAC, manomissione rilevata
- _clear_cache / logout: rimozione file cache
- _hash_pwd / _verify_pwd_hash: determinismo, timing-safe compare
- _days_left: parsing ISO, data scaduta, formato non valido

Esecuzione:
    pytest tests/test_auth_service.py -v
"""

import hmac
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import _HMAC_KEY, AuthResult, AuthService

# ══════════════════════════════════════════════════════════
#  Fixture condivise
# ══════════════════════════════════════════════════════════

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    return logger


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Directory temporanea isolata per ogni test"""
    return tmp_path


@pytest.fixture
def auth_service(mock_logger, tmp_path):
    """AuthService con cache in directory temporanea"""
    svc = AuthService(logger=mock_logger, server_url="http://test-server")
    # Redirige la cache alla directory temporanea
    svc._cache_file = tmp_path / ".license_cache"
    return svc


def _make_cache_payload(email="test@email.com", password="password123",
                        days_offset=-2, days_left=30,
                        grace_mode=False, is_admin=False):
    """Helper: costruisce payload cache firmato con HMAC valido"""
    expires_at = (datetime.utcnow() + timedelta(days=days_left)).isoformat()
    cached_at = (datetime.utcnow() + timedelta(days=days_offset)).isoformat()

    cache = {
        "email": email,
        "pwd_hash": AuthService._hash_pwd(password),
        "token": "tok_abc123",
        "expires_at": expires_at,
        "days_left": days_left,
        "is_admin": is_admin,
        "grace_mode": grace_mode,
        "cached_at": cached_at,
    }

    payload = json.dumps(cache, sort_keys=True).encode()
    signature = hmac.digest(_HMAC_KEY, payload, "sha256").hex()
    return json.dumps({"payload": cache, "sig": signature})


# ══════════════════════════════════════════════════════════
#  _hash_pwd / _verify_pwd_hash
# ══════════════════════════════════════════════════════════

class TestPasswordUtils:
    """Test per le utility statiche di hashing password"""

    def test_hash_pwd_restituisce_stringa(self):
        result = AuthService._hash_pwd("password123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_pwd_deterministico(self):
        """Stessa password → stesso hash (salt fisso interno)"""
        h1 = AuthService._hash_pwd("stessa_password")
        h2 = AuthService._hash_pwd("stessa_password")
        assert h1 == h2

    def test_hash_pwd_password_diverse_hash_diversi(self):
        h1 = AuthService._hash_pwd("password_A")
        h2 = AuthService._hash_pwd("password_B")
        assert h1 != h2

    def test_verify_pwd_hash_corretta(self):
        stored = AuthService._hash_pwd("mypassword")
        assert AuthService._verify_pwd_hash("mypassword", stored) is True

    def test_verify_pwd_hash_errata(self):
        stored = AuthService._hash_pwd("password_corretta")
        assert AuthService._verify_pwd_hash("password_sbagliata", stored) is False

    def test_verify_pwd_hash_vuota(self):
        stored = AuthService._hash_pwd("qualcosa")
        assert AuthService._verify_pwd_hash("", stored) is False

    def test_verify_pwd_hash_timing_safe(self):
        """_verify_pwd_hash usa compare_digest — non deve sollevare eccezioni"""
        stored = AuthService._hash_pwd("test")
        # Non deve crashare nemmeno con hash di lunghezza diversa
        result = AuthService._verify_pwd_hash("x", stored)
        assert isinstance(result, bool)


# ══════════════════════════════════════════════════════════
#  _days_left
# ══════════════════════════════════════════════════════════

class TestDaysLeft:
    """Test per il calcolo dei giorni residui alla scadenza"""

    def test_scadenza_futura(self):
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()
        result = AuthService._days_left(future)
        assert result >= 29  # Margine di 1 giorno per esecuzione

    def test_scadenza_oggi(self):
        today = datetime.utcnow().isoformat()
        result = AuthService._days_left(today)
        assert result == 0

    def test_scadenza_passata(self):
        past = (datetime.utcnow() - timedelta(days=5)).isoformat()
        result = AuthService._days_left(past)
        assert result == 0  # Non può essere negativo

    def test_formato_non_valido_ritorna_zero(self):
        result = AuthService._days_left("data-non-valida")
        assert result == 0

    def test_stringa_vuota_ritorna_zero(self):
        result = AuthService._days_left("")
        assert result == 0


# ══════════════════════════════════════════════════════════
#  _save_cache / _load_cache
# ══════════════════════════════════════════════════════════

class TestCacheOperations:
    """Test per la gestione della cache locale firmata con HMAC"""

    def test_save_e_load_cache_round_trip(self, auth_service, tmp_path):
        """Salva e ricarica: i dati devono essere identici"""
        auth_service._cache_file = tmp_path / ".license_cache"

        server_data = {
            "token": "tok_xyz",
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "days_left": 30,
            "is_admin": False,
            "grace_mode": False,
        }

        with patch("services.auth_service._CACHE_FILE", auth_service._cache_file):
            auth_service._save_cache("user@test.com", "pass123", server_data)
            loaded = auth_service._load_cache()

        assert loaded is not None
        assert loaded["email"] == "user@test.com"
        assert loaded["token"] == "tok_xyz"

    def test_load_cache_file_assente_ritorna_none(self, auth_service, tmp_path):
        """Nessun file cache → None"""
        auth_service._cache_file = tmp_path / ".non_esistente"
        with patch("services.auth_service._CACHE_FILE", auth_service._cache_file):
            result = auth_service._load_cache()
        assert result is None

    def test_load_cache_firma_manomessa_ritorna_none(self, auth_service, tmp_path):
        """Cache con firma HMAC alterata deve essere scartata"""
        cache_file = tmp_path / ".license_cache"

        # Scrivi cache con firma errata
        tampered = json.dumps({
            "payload": {"email": "hacker@evil.com"},
            "sig": "firma_falsa_0000000000000000"
        })
        cache_file.write_text(tampered, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._load_cache()

        assert result is None
        auth_service.logger.warning.assert_called()

    def test_load_cache_json_corrotto_ritorna_none(self, auth_service, tmp_path):
        """JSON malformato non deve far crashare l'app"""
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text("{ questo non e' json valido }", encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._load_cache()

        assert result is None

    def test_clear_cache_rimuove_file(self, auth_service, tmp_path):
        """_clear_cache deve eliminare il file"""
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text("dati", encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            auth_service._clear_cache()

        assert not cache_file.exists()

    def test_clear_cache_senza_file_non_crasha(self, auth_service, tmp_path):
        """_clear_cache senza file preesistente non deve sollevare eccezioni"""
        with patch("services.auth_service._CACHE_FILE", tmp_path / ".inesistente"):
            auth_service._clear_cache()  # Non deve sollevare eccezioni


# ══════════════════════════════════════════════════════════
#  _login_online
# ══════════════════════════════════════════════════════════

class TestLoginOnline:
    """Test per il flusso di autenticazione online"""

    def _make_ok_response(self, email="user@test.com", days_left=30):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "token": "tok_online_123",
            "email": email,
            "expires_at": (datetime.utcnow() + timedelta(days=days_left)).isoformat(),
            "days_left": days_left,
            "is_admin": False,
            "warning": None,
            "grace_mode": False,
        }
        return resp

    def test_login_online_successo(self, auth_service, tmp_path):
        resp = self._make_ok_response()

        with patch("services.auth_service._CACHE_FILE", tmp_path / ".lc"), \
             patch("requests.post", return_value=resp):
            result = auth_service._login_online("user@test.com", "password")

        assert result is not None
        assert result.success is True
        assert result.mode == "online"
        assert result.token == "tok_online_123"

    def test_login_online_401_ritorna_fallimento(self, auth_service):
        resp = MagicMock()
        resp.status_code = 401
        resp.json.return_value = {"detail": "Credenziali errate"}

        with patch("requests.post", return_value=resp):
            result = auth_service._login_online("user@test.com", "wrong")

        assert result is not None
        assert result.success is False
        assert result.mode == "failed"
        assert "Credenziali errate" in (result.error or "")

    def test_login_online_403_ritorna_fallimento(self, auth_service):
        resp = MagicMock()
        resp.status_code = 403
        resp.json.return_value = {"detail": "Accesso negato"}

        with patch("requests.post", return_value=resp):
            result = auth_service._login_online("user@test.com", "pass")

        assert result is not None
        assert result.success is False

    def test_login_online_500_ritorna_none(self, auth_service):
        """Errore server inatteso → None (si passa all'offline)"""
        resp = MagicMock()
        resp.status_code = 500

        with patch("requests.post", return_value=resp):
            result = auth_service._login_online("user@test.com", "pass")

        assert result is None

    def test_login_online_eccezione_rete_ritorna_none(self, auth_service):
        """Timeout/connection error → None (si passa all'offline)"""
        with patch("requests.post", side_effect=Exception("Connection refused")):
            result = auth_service._login_online("user@test.com", "pass")

        assert result is None

    def test_login_online_salva_cache_dopo_successo(self, auth_service, tmp_path):
        """Dopo un login riuscito la cache deve essere aggiornata"""
        resp = self._make_ok_response()
        cache_file = tmp_path / ".license_cache"

        with patch("services.auth_service._CACHE_FILE", cache_file), \
             patch("requests.post", return_value=resp):
            auth_service._login_online("user@test.com", "password")

        assert cache_file.exists()

    def test_login_online_imposta_is_admin(self, auth_service, tmp_path):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "token": "tok", "email": "admin@test.com",
            "expires_at": (datetime.utcnow() + timedelta(days=10)).isoformat(),
            "days_left": 10, "is_admin": True,
            "warning": None, "grace_mode": False,
        }

        with patch("services.auth_service._CACHE_FILE", tmp_path / ".lc"), \
             patch("requests.post", return_value=resp):
            result = auth_service._login_online("admin@test.com", "pass")

        assert result.is_admin is True


# ══════════════════════════════════════════════════════════
#  _login_offline
# ══════════════════════════════════════════════════════════

class TestLoginOffline:
    """Test per il flusso di autenticazione offline da cache"""

    def test_offline_cache_valida_successo(self, auth_service, tmp_path):
        """Cache recente e password corretta → login OK"""
        cache_content = _make_cache_payload(
            email="user@test.com", password="pass123",
            days_offset=-1, days_left=25
        )
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "pass123")

        assert result.success is True
        assert result.mode == "offline_cache"
        assert result.warning is not None  # Deve avvertire modalità offline

    def test_offline_nessuna_cache_fallisce(self, auth_service, tmp_path):
        """Nessuna cache → errore con messaggio chiaro"""
        with patch("services.auth_service._CACHE_FILE", tmp_path / ".assente"):
            result = auth_service._login_offline("user@test.com", "pass")

        assert result.success is False
        assert "internet" in result.error.lower() or "server" in result.error.lower()

    def test_offline_email_diversa_fallisce(self, auth_service, tmp_path):
        """Email diversa da quella in cache → accesso negato"""
        cache_content = _make_cache_payload(email="cached@test.com", password="pass")
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("altro@test.com", "pass")

        assert result.success is False
        assert "email" in result.error.lower() or "corrisponde" in result.error.lower()

    def test_offline_password_errata_fallisce(self, auth_service, tmp_path):
        """Password sbagliata → accesso negato"""
        cache_content = _make_cache_payload(email="user@test.com", password="corretta")
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "sbagliata")

        assert result.success is False
        assert "password" in result.error.lower()

    def test_offline_cache_scaduta_fallisce(self, auth_service, tmp_path):
        """Cache più vecchia di 7 giorni → accesso negato e cache rimossa"""
        cache_content = _make_cache_payload(
            email="user@test.com", password="pass",
            days_offset=-8  # 8 giorni fa — oltre il limite di 7
        )
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "pass")

        assert result.success is False
        assert "scaduta" in result.error.lower() or "internet" in result.error.lower()

    def test_offline_licenza_scaduta_senza_grace_fallisce(self, auth_service, tmp_path):
        """Licenza scaduta e grace_mode=False → accesso negato"""
        cache_content = _make_cache_payload(
            email="user@test.com", password="pass",
            days_offset=-1, days_left=0, grace_mode=False
        )
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "pass")

        assert result.success is False
        assert "scaduta" in result.error.lower() or "licenza" in result.error.lower()

    def test_offline_licenza_scaduta_con_grace_successo(self, auth_service, tmp_path):
        """Licenza scaduta ma grace_mode=True → accesso consentito"""
        cache_content = _make_cache_payload(
            email="user@test.com", password="pass",
            days_offset=-1, days_left=0, grace_mode=True
        )
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "pass")

        assert result.success is True
        assert result.grace_mode is True

    def test_offline_warning_contiene_giorni_rimanenti(self, auth_service, tmp_path):
        """Il warning offline deve indicare quanti giorni rimangono"""
        cache_content = _make_cache_payload(
            email="user@test.com", password="pass",
            days_offset=-3, days_left=30
        )
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text(cache_content, encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            result = auth_service._login_offline("user@test.com", "pass")

        assert result.success is True
        assert result.warning is not None
        # Deve indicare i giorni trascorsi offline
        assert "3" in result.warning or "offline" in result.warning.lower()


# ══════════════════════════════════════════════════════════
#  login (entry point principale)
# ══════════════════════════════════════════════════════════

class TestLogin:
    """Test per il metodo login() che coordina online e offline"""

    def test_login_preferisce_online_se_disponibile(self, auth_service):
        """Se online funziona, non deve tentare offline"""
        online_result = AuthResult(success=True, mode="online", token="tok")
        auth_service._login_online = MagicMock(return_value=online_result)
        auth_service._login_offline = MagicMock()

        result = auth_service.login("user@test.com", "pass")

        auth_service._login_online.assert_called_once()
        auth_service._login_offline.assert_not_called()
        assert result.mode == "online"

    def test_login_fallback_offline_se_online_ritorna_none(self, auth_service):
        """Se _login_online ritorna None (server irraggiungibile) → usa offline"""
        auth_service._login_online = MagicMock(return_value=None)
        offline_result = AuthResult(success=True, mode="offline_cache")
        auth_service._login_offline = MagicMock(return_value=offline_result)

        result = auth_service.login("user@test.com", "pass")

        auth_service._login_offline.assert_called_once()
        assert result.mode == "offline_cache"

    def test_login_normalizza_email(self, auth_service):
        """L'email deve essere lowercase e senza spazi"""
        auth_service._login_online = MagicMock(return_value=None)
        auth_service._login_offline = MagicMock(
            return_value=AuthResult(success=False, error="test")
        )

        auth_service.login("  USER@TEST.COM  ", "pass")

        call_args = auth_service._login_offline.call_args
        assert call_args[0][0] == "user@test.com"

    def test_login_senza_requests_usa_solo_offline(self, auth_service):
        """Se requests non è disponibile, deve usare direttamente offline"""
        auth_service._login_offline = MagicMock(
            return_value=AuthResult(success=False, error="no cache")
        )

        with patch("services.auth_service.REQUESTS_AVAILABLE", False):
            auth_service.login("user@test.com", "pass")

        auth_service._login_offline.assert_called_once()


# ══════════════════════════════════════════════════════════
#  logout
# ══════════════════════════════════════════════════════════

class TestLogout:
    """Test per il logout"""

    def test_logout_rimuove_cache(self, auth_service, tmp_path):
        cache_file = tmp_path / ".license_cache"
        cache_file.write_text("dati", encoding="utf-8")

        with patch("services.auth_service._CACHE_FILE", cache_file):
            auth_service.logout()

        assert not cache_file.exists()

    def test_logout_logga_operazione(self, auth_service, tmp_path):
        with patch("services.auth_service._CACHE_FILE", tmp_path / ".lc"):
            auth_service.logout()

        auth_service.logger.info.assert_called()
        log_msg = str(auth_service.logger.info.call_args)
        assert "logout" in log_msg.lower() or "Logout" in log_msg
