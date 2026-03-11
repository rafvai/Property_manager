"""
test_security_manager.py
========================
Test unitari per security_manager.py

Copertura:
- sanitize_filename: path traversal, caratteri pericolosi, lunghezza
- validate_file_upload: estensioni, dimensione, MIME type
- sanitize_sql_input: SQL keywords, caratteri pericolosi, lunghezza
- validate_path: path traversal prevention
- hash_password / verify_password: PBKDF2, salt, timing-safe compare
- generate_secure_token: lunghezza, unicità
- validate_email: formato RFC
- sanitize_html: rimozione tag, escape caratteri
- validate_numeric_range: min/max check

Esecuzione:
    pytest tests/test_security_manager.py -v
"""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_manager import SecurityManager


# ══════════════════════════════════════════════════════════
#  sanitize_filename
# ══════════════════════════════════════════════════════════

class TestSanitizeFilename:
    """Test per sanitize_filename — prevenzione path traversal"""

    def test_nome_normale(self):
        result = SecurityManager.sanitize_filename("fattura_gennaio.pdf")
        assert result == "fattura_gennaio.pdf"

    def test_path_traversal_slash(self):
        """../../../etc/passwd deve diventare un nome sicuro"""
        result = SecurityManager.sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_path_traversal_backslash(self):
        result = SecurityManager.sanitize_filename("..\\..\\windows\\system32")
        assert ".." not in result
        assert "\\" not in result

    def test_null_byte_rimosso(self):
        result = SecurityManager.sanitize_filename("file\x00.pdf")
        assert "\x00" not in result

    def test_solo_basename(self):
        """Deve restituire solo il nome file, senza path"""
        result = SecurityManager.sanitize_filename("/home/user/docs/file.pdf")
        assert "/" not in result
        assert result == "file.pdf"

    def test_troncatura_lunghezza(self):
        """Nome troppo lungo deve essere troncato"""
        lungo = "a" * 300 + ".pdf"
        result = SecurityManager.sanitize_filename(lungo, max_length=50)
        assert len(result) <= 50

    def test_nome_vuoto_lancia_errore(self):
        with pytest.raises(ValueError, match="vuoto"):
            SecurityManager.sanitize_filename("")

    def test_solo_punti_lancia_errore(self):
        with pytest.raises(ValueError):
            SecurityManager.sanitize_filename("...")

    def test_estensione_preservata_dopo_troncatura(self):
        """L'estensione deve sopravvivere alla troncatura"""
        lungo = "a" * 300 + ".pdf"
        result = SecurityManager.sanitize_filename(lungo, max_length=20)
        assert result.endswith(".pdf")


# ══════════════════════════════════════════════════════════
#  validate_file_upload
# ══════════════════════════════════════════════════════════

class TestValidateFileUpload:
    """Test per validate_file_upload — usa file temporanei reali"""

    def _crea_file_temp(self, suffix=".pdf", size_bytes=1024):
        """Helper: crea file temporaneo con contenuto"""
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(b"X" * size_bytes)
        tmp.close()
        return tmp.name

    def test_file_pdf_valido(self):
        path = self._crea_file_temp(".pdf")
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["valid"] is True
            assert result["extension"] == "pdf"
        finally:
            os.unlink(path)

    def test_file_xlsx_valido(self):
        path = self._crea_file_temp(".xlsx")
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["valid"] is True
        finally:
            os.unlink(path)

    def test_estensione_non_permessa(self):
        path = self._crea_file_temp(".exe")
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["valid"] is False
            assert "estensione" in result["error"].lower() or "permessa" in result["error"].lower()
        finally:
            os.unlink(path)

    def test_file_vuoto(self):
        path = self._crea_file_temp(".pdf", size_bytes=0)
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["valid"] is False
            assert "vuoto" in result["error"].lower()
        finally:
            os.unlink(path)

    def test_file_non_esistente(self):
        result = SecurityManager.validate_file_upload("/path/che/non/esiste/file.pdf")
        assert result["valid"] is False
        assert "trovato" in result["error"].lower()

    def test_file_troppo_grande(self):
        """20MB + 1 byte deve essere rifiutato"""
        path = self._crea_file_temp(".pdf", size_bytes=SecurityManager.MAX_FILE_SIZE + 1)
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["valid"] is False
            assert "grande" in result["error"].lower()
        finally:
            os.unlink(path)

    def test_estensioni_personalizzate(self):
        """Whitelist custom passata come parametro"""
        path = self._crea_file_temp(".csv")
        try:
            result = SecurityManager.validate_file_upload(path, allowed_extensions={"csv"})
            assert result["valid"] is True
        finally:
            os.unlink(path)

    def test_dimensione_corretta_nel_risultato(self):
        path = self._crea_file_temp(".pdf", size_bytes=512)
        try:
            result = SecurityManager.validate_file_upload(path)
            assert result["size"] == 512
        finally:
            os.unlink(path)


# ══════════════════════════════════════════════════════════
#  sanitize_sql_input
# ══════════════════════════════════════════════════════════

class TestSanitizeSqlInput:
    """Test per sanitize_sql_input"""

    def test_input_normale(self):
        result = SecurityManager.sanitize_sql_input("ENEL Energia")
        assert result == "ENEL Energia"

    def test_stringa_vuota_ritorna_vuota(self):
        result = SecurityManager.sanitize_sql_input("")
        assert result == ""

    def test_sql_union_lancia_errore(self):
        with pytest.raises(ValueError, match="SQL"):
            SecurityManager.sanitize_sql_input("UNION SELECT password FROM users")

    def test_sql_drop_lancia_errore(self):
        with pytest.raises(ValueError, match="SQL"):
            SecurityManager.sanitize_sql_input("DROP TABLE transactions")

    def test_sql_select_lancia_errore(self):
        with pytest.raises(ValueError):
            SecurityManager.sanitize_sql_input("SELECT * FROM properties")

    def test_carattere_punto_e_virgola_lancia_errore(self):
        with pytest.raises(ValueError, match="pericolosi"):
            SecurityManager.sanitize_sql_input("valore; DROP TABLE")

    def test_pipe_lancia_errore(self):
        with pytest.raises(ValueError, match="pericolosi"):
            SecurityManager.sanitize_sql_input("valore | comando")

    def test_troppo_lungo_lancia_errore(self):
        with pytest.raises(ValueError, match="lungo"):
            SecurityManager.sanitize_sql_input("a" * 501, max_length=500)

    def test_null_byte_rimosso(self):
        result = SecurityManager.sanitize_sql_input("test\x00value")
        assert "\x00" not in result

    def test_spazi_vengono_rimossi(self):
        result = SecurityManager.sanitize_sql_input("  Fornitore  ")
        assert result == "Fornitore"


# ══════════════════════════════════════════════════════════
#  validate_path
# ══════════════════════════════════════════════════════════

class TestValidatePath:
    """Test per validate_path — path traversal prevention"""

    def test_path_dentro_base_ok(self):
        base = "/home/app/docs"
        path = "/home/app/docs/property_1/file.pdf"
        assert SecurityManager.validate_path(path, base) is True

    def test_path_traversal_lancia_errore(self):
        base = "/home/app/docs"
        path = "/home/app/docs/../../../etc/passwd"
        with pytest.raises(ValueError, match="traversal"):
            SecurityManager.validate_path(path, base)

    def test_path_completamente_fuori_lancia_errore(self):
        base = "/home/app/docs"
        path = "/etc/passwd"
        with pytest.raises(ValueError, match="traversal"):
            SecurityManager.validate_path(path, base)

    def test_path_uguale_a_base_ok(self):
        base = "/home/app/docs"
        assert SecurityManager.validate_path(base, base) is True


# ══════════════════════════════════════════════════════════
#  hash_password / verify_password
# ══════════════════════════════════════════════════════════

class TestPasswordHashing:
    """
    Test per hash_password e verify_password.
    Usa PBKDF2-SHA256 con 100.000 iterazioni — sicuro ma lento.
    I test sono marcati con pytest.mark.slow se necessario.
    """

    def test_hash_genera_stringa_non_vuota(self):
        h, salt = SecurityManager.hash_password("password123")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_genera_salt_non_vuoto(self):
        h, salt = SecurityManager.hash_password("password123")
        assert isinstance(salt, str)
        assert len(salt) > 0

    def test_stesso_input_sale_diverso_produce_hash_diverso(self):
        """Ogni chiamata senza salt esplicito deve produrre hash diversi"""
        h1, _ = SecurityManager.hash_password("stessa_password")
        h2, _ = SecurityManager.hash_password("stessa_password")
        assert h1 != h2

    def test_stesso_input_stesso_sale_produce_hash_uguale(self):
        """Con salt fisso l'hash deve essere deterministico"""
        salt = "salt_fisso_per_test"
        h1, _ = SecurityManager.hash_password("password", salt)
        h2, _ = SecurityManager.hash_password("password", salt)
        assert h1 == h2

    def test_verify_password_corretta(self):
        password = "MiaPassword!123"
        h, salt = SecurityManager.hash_password(password)
        assert SecurityManager.verify_password(password, h, salt) is True

    def test_verify_password_errata(self):
        h, salt = SecurityManager.hash_password("password_corretta")
        assert SecurityManager.verify_password("password_sbagliata", h, salt) is False

    def test_verify_password_vuota(self):
        h, salt = SecurityManager.hash_password("password_corretta")
        assert SecurityManager.verify_password("", h, salt) is False

    def test_password_con_caratteri_speciali(self):
        password = "P@$$w0rd!#%&*()€"
        h, salt = SecurityManager.hash_password(password)
        assert SecurityManager.verify_password(password, h, salt) is True


# ══════════════════════════════════════════════════════════
#  generate_secure_token
# ══════════════════════════════════════════════════════════

class TestGenerateSecureToken:
    """Test per generate_secure_token"""

    def test_lunghezza_default(self):
        """Default 32 byte = 64 caratteri esadecimali"""
        token = SecurityManager.generate_secure_token()
        assert len(token) == 64

    def test_lunghezza_personalizzata(self):
        token = SecurityManager.generate_secure_token(16)
        assert len(token) == 32  # 16 byte = 32 hex chars

    def test_token_e_esadecimale(self):
        token = SecurityManager.generate_secure_token()
        assert all(c in "0123456789abcdef" for c in token)

    def test_due_token_sono_diversi(self):
        """I token devono essere casuali — collisione praticamente impossibile"""
        t1 = SecurityManager.generate_secure_token()
        t2 = SecurityManager.generate_secure_token()
        assert t1 != t2


# ══════════════════════════════════════════════════════════
#  validate_email
# ══════════════════════════════════════════════════════════

class TestValidateEmail:
    """Test per validate_email"""

    def test_email_valida(self):
        assert SecurityManager.validate_email("mario.rossi@email.com") is True

    def test_email_con_sottodominio(self):
        assert SecurityManager.validate_email("utente@mail.esempio.it") is True

    def test_email_senza_at_non_valida(self):
        assert SecurityManager.validate_email("emailsenzaat.com") is False

    def test_email_senza_dominio_non_valida(self):
        assert SecurityManager.validate_email("utente@") is False

    def test_email_senza_tld_non_valida(self):
        assert SecurityManager.validate_email("utente@dominio") is False

    def test_stringa_vuota_non_valida(self):
        assert SecurityManager.validate_email("") is False

    def test_none_non_valido(self):
        assert SecurityManager.validate_email(None) is False

    def test_email_troppo_lunga_non_valida(self):
        lunga = "a" * 320 + "@email.com"
        assert SecurityManager.validate_email(lunga) is False


# ══════════════════════════════════════════════════════════
#  sanitize_html
# ══════════════════════════════════════════════════════════

class TestSanitizeHtml:
    """Test per sanitize_html — prevenzione XSS"""

    def test_testo_normale_invariato(self):
        result = SecurityManager.sanitize_html("Testo normale")
        assert result == "Testo normale"

    def test_tag_script_rimosso(self):
        result = SecurityManager.sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" in result  # Il testo rimane, solo il tag è rimosso

    def test_tag_html_rimosso(self):
        result = SecurityManager.sanitize_html("<b>testo grassetto</b>")
        assert "<b>" not in result
        assert "</b>" not in result

    def test_stringa_vuota(self):
        assert SecurityManager.sanitize_html("") == ""

    def test_none_ritorna_vuoto(self):
        assert SecurityManager.sanitize_html(None) == ""

    def test_caratteri_speciali_escapati(self):
        result = SecurityManager.sanitize_html("5 > 3 & 2 < 4")
        assert "&gt;" in result or ">" not in result
        assert "&lt;" in result or "<" not in result


# ══════════════════════════════════════════════════════════
#  validate_numeric_range
# ══════════════════════════════════════════════════════════

class TestValidateNumericRange:
    """Test per validate_numeric_range"""

    def test_valore_nel_range(self):
        assert SecurityManager.validate_numeric_range(50, 0, 100) is True

    def test_valore_al_minimo(self):
        assert SecurityManager.validate_numeric_range(0, 0, 100) is True

    def test_valore_al_massimo(self):
        assert SecurityManager.validate_numeric_range(100, 0, 100) is True

    def test_valore_sotto_minimo_lancia_errore(self):
        with pytest.raises(ValueError, match="fuori range"):
            SecurityManager.validate_numeric_range(-1, 0, 100)

    def test_valore_sopra_massimo_lancia_errore(self):
        with pytest.raises(ValueError, match="fuori range"):
            SecurityManager.validate_numeric_range(101, 0, 100)

    def test_non_numerico_lancia_errore(self):
        with pytest.raises(ValueError, match="numerico"):
            SecurityManager.validate_numeric_range("cinquanta", 0, 100)

    def test_float_valido(self):
        assert SecurityManager.validate_numeric_range(3.14, 0.0, 10.0) is True
