"""
test_validation_utils.py
========================
Test unitari per validation_utils.py

Copertura:
- parse_decimal: conversione stringhe numeriche (virgola/punto, edge cases, errori)
- validate_required_text: lunghezza, caratteri, SQL injection, XSS
- validate_date: range anni, date invalide
- validate_property_id: interi positivi, overflow
- validate_transaction_type: whitelist Entrata/Uscita
- validate_date_string: formato dd/MM/yyyy
- format_currency: formattazione italiana
- validate_amount_range: limiti min/max

Esecuzione:
    pytest tests/test_validation_utils.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation_utils import (
    ValidationError,
    format_currency,
    parse_decimal,
    validate_amount_range,
    validate_date_string,
    validate_property_id,
    validate_required_text,
    validate_transaction_type,
)

# ══════════════════════════════════════════════════════════
#  parse_decimal
# ══════════════════════════════════════════════════════════

class TestParseDecimal:

    def test_intero_semplice(self):
        assert parse_decimal("100") == 100.0

    def test_decimale_con_punto(self):
        assert parse_decimal("123.45") == 123.45

    def test_decimale_con_virgola(self):
        assert parse_decimal("123,45") == 123.45

    def test_migliaia_con_punto_e_virgola(self):
        assert parse_decimal("1.234,56") == 1234.56

    def test_spazi_vengono_rimossi(self):
        assert parse_decimal("1 000,00") == 1000.0

    def test_valore_zero_lancia_errore(self):
        with pytest.raises(ValidationError, match="maggiore di zero"):
            parse_decimal("0")

    def test_valore_negativo_lancia_errore(self):
        """
        Il '-' non è tra i caratteri permessi dal regex di parse_decimal,
        quindi viene bloccato con 'caratteri non validi' prima del check segno.
        """
        with pytest.raises(ValidationError, match="caratteri non validi"):
            parse_decimal("-50")

    def test_stringa_vuota_lancia_errore(self):
        with pytest.raises(ValidationError, match="obbligatorio"):
            parse_decimal("")

    def test_stringa_none_lancia_errore(self):
        with pytest.raises(ValidationError):
            parse_decimal(None)

    def test_testo_non_numerico_lancia_errore(self):
        with pytest.raises(ValidationError):
            parse_decimal("abc")

    def test_troppo_lungo_lancia_errore(self):
        with pytest.raises(ValidationError, match="troppo lungo"):
            parse_decimal("1" * 21)

    def test_valore_enormemente_grande_lancia_errore(self):
        with pytest.raises(ValidationError, match="troppo grande"):
            parse_decimal("1000000001")

    def test_arrotondamento_automatico(self):
        result = parse_decimal("10.999")
        assert result == round(10.999, 2)

    def test_nome_campo_personalizzato_nel_messaggio(self):
        with pytest.raises(ValidationError, match="Importo Fattura"):
            parse_decimal("", "Importo Fattura")


# ══════════════════════════════════════════════════════════
#  validate_required_text
# ══════════════════════════════════════════════════════════

class TestValidateRequiredText:

    def test_testo_valido(self):
        result = validate_required_text("Mario Rossi", "Nome")
        assert result == "Mario Rossi"

    def test_spazi_vengono_rimossi(self):
        result = validate_required_text("  ENEL  ", "Fornitore")
        assert result == "ENEL"

    def test_stringa_vuota_lancia_errore(self):
        with pytest.raises(ValidationError, match="obbligatorio"):
            validate_required_text("", "Campo")

    def test_solo_spazi_lancia_errore(self):
        with pytest.raises(ValidationError, match="obbligatorio"):
            validate_required_text("   ", "Campo")

    def test_troppo_corto_lancia_errore(self):
        with pytest.raises(ValidationError, match="almeno 3"):
            validate_required_text("AB", "Nome", min_length=3)

    def test_troppo_lungo_lancia_errore(self):
        with pytest.raises(ValidationError, match="superare 10"):
            validate_required_text("A" * 11, "Nome", max_length=10)

    def test_lunghezza_esatta_minima_ok(self):
        result = validate_required_text("AB", "Nome", min_length=2)
        assert result == "AB"

    def test_lunghezza_esatta_massima_ok(self):
        result = validate_required_text("A" * 10, "Nome", max_length=10)
        assert len(result) == 10

    def test_testo_con_keyword_sql_accettato(self):
        """Le keyword SQL nel testo sono dati legittimi: la protezione
        dall'injection sono le query parametrizzate, non una blacklist."""
        result = validate_required_text("UNION SELECT * FROM users", "Campo")
        assert result == "UNION SELECT * FROM users"

    def test_nome_fornitore_con_e_commerciale_accettato(self):
        result = validate_required_text("Rossi & Figli S.r.l.", "Fornitore")
        assert result == "Rossi & Figli S.r.l."

    def test_null_byte_viene_rimosso(self):
        try:
            result = validate_required_text("test\x00value", "Campo")
            assert "\x00" not in result
        except ValidationError:
            pass


# ══════════════════════════════════════════════════════════
#  validate_date_string
# ══════════════════════════════════════════════════════════

class TestValidateDateString:

    def test_data_valida(self):
        assert validate_date_string("15/03/2024") == "15/03/2024"

    def test_primo_gennaio(self):
        assert validate_date_string("01/01/2023") == "01/01/2023"

    def test_formato_errato_lancia_errore(self):
        with pytest.raises(ValidationError, match="dd/MM/yyyy"):
            validate_date_string("2024-03-15")

    def test_giorno_non_valido_lancia_errore(self):
        with pytest.raises(ValidationError, match="giorno"):
            validate_date_string("32/01/2024")

    def test_mese_non_valido_lancia_errore(self):
        with pytest.raises(ValidationError, match="mese"):
            validate_date_string("15/13/2024")

    def test_anno_troppo_vecchio_lancia_errore(self):
        with pytest.raises(ValidationError, match="anno"):
            validate_date_string("15/03/1800")

    def test_anno_futuro_troppo_lontano_lancia_errore(self):
        with pytest.raises(ValidationError, match="anno"):
            validate_date_string("15/03/2200")

    def test_stringa_vuota_lancia_errore(self):
        with pytest.raises(ValidationError, match="obbligatoria"):
            validate_date_string("")

    def test_stringa_non_data_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_date_string("non-una-data")

    def test_anno_limite_inferiore_ok(self):
        assert validate_date_string("01/01/1900") == "01/01/1900"

    def test_anno_limite_superiore_ok(self):
        assert validate_date_string("31/12/2100") == "31/12/2100"


# ══════════════════════════════════════════════════════════
#  validate_property_id
# ══════════════════════════════════════════════════════════

class TestValidatePropertyId:

    def test_id_valido(self):
        assert validate_property_id(1) == 1

    def test_id_grande_valido(self):
        assert validate_property_id(999999) == 999999

    def test_stringa_numerica_convertita(self):
        assert validate_property_id("42") == 42

    def test_zero_lancia_errore(self):
        with pytest.raises(ValidationError, match="positivo"):
            validate_property_id(0)

    def test_negativo_lancia_errore(self):
        with pytest.raises(ValidationError, match="positivo"):
            validate_property_id(-1)

    def test_stringa_testo_lancia_errore(self):
        with pytest.raises(ValidationError, match="non valido"):
            validate_property_id("abc")

    def test_none_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_property_id(None)

    def test_overflow_lancia_errore(self):
        with pytest.raises(ValidationError, match="troppo grande"):
            validate_property_id(2_147_483_648)


# ══════════════════════════════════════════════════════════
#  validate_transaction_type
# ══════════════════════════════════════════════════════════

class TestValidateTransactionType:

    def test_entrata_valida(self):
        assert validate_transaction_type("Entrata") == "Entrata"

    def test_uscita_valida(self):
        assert validate_transaction_type("Uscita") == "Uscita"

    def test_spazi_vengono_rimossi(self):
        assert validate_transaction_type("  Entrata  ") == "Entrata"

    def test_case_sensitive_minuscolo_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_transaction_type("entrata")

    def test_valore_arbitrario_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_transaction_type("Bonifico")

    def test_stringa_vuota_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_transaction_type("")

    def test_none_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_transaction_type(None)


# ══════════════════════════════════════════════════════════
#  format_currency
# ══════════════════════════════════════════════════════════

class TestFormatCurrency:

    def test_zero(self):
        assert format_currency(0) == "0,00 €"

    def test_intero(self):
        result = format_currency(100)
        assert "100" in result
        assert "€" in result

    def test_decimale(self):
        result = format_currency(1234.56)
        assert "," in result
        assert "€" in result

    def test_none_ritorna_zero(self):
        assert format_currency(None) == "0,00 €"

    def test_valore_negativo(self):
        result = format_currency(-50.0)
        assert "€" in result

    def test_valore_enorme_ritorna_non_valido(self):
        result = format_currency(2_000_000_000)
        assert "NON VALIDO" in result


# ══════════════════════════════════════════════════════════
#  validate_amount_range
# ══════════════════════════════════════════════════════════

class TestValidateAmountRange:

    def test_importo_valido(self):
        validate_amount_range(100.0)

    def test_minimo_valido(self):
        validate_amount_range(0.01)

    def test_massimo_valido(self):
        validate_amount_range(9_999_999.99)

    def test_troppo_piccolo_lancia_errore(self):
        with pytest.raises(ValidationError, match="almeno"):
            validate_amount_range(0.001)

    def test_troppo_grande_lancia_errore(self):
        with pytest.raises(ValidationError, match="limite massimo"):
            validate_amount_range(10_000_001.0)

    def test_non_numerico_lancia_errore(self):
        with pytest.raises(ValidationError, match="numerico"):
            validate_amount_range("cento")

    def test_zero_lancia_errore(self):
        with pytest.raises(ValidationError):
            validate_amount_range(0.0)
