"""
Utilità per la validazione sicura degli input utente
VERSIONE POTENZIATA con protezione SQL Injection e XSS
"""
from decimal import Decimal, InvalidOperation
import re
from security_manager import SecurityManager


class ValidationError(Exception):
    """Eccezione personalizzata per errori di validazione"""
    pass


def parse_decimal(value_str, field_name="Importo"):
    """
    Converte una stringa in numero decimale gestendo sia virgola che punto.
    CON VALIDAZIONE SICUREZZA

    Args:
        value_str: Stringa da convertire
        field_name: Nome del campo per messaggi di errore

    Returns:
        float: Valore numerico convertito

    Raises:
        ValidationError: Se la conversione fallisce o valore non sicuro
    """
    if not value_str or not value_str.strip():
        raise ValidationError(f"{field_name} è obbligatorio")

    clean_str = value_str.strip()

    # SICUREZZA: Verifica lunghezza massima
    if len(clean_str) > 20:
        raise ValidationError(f"{field_name}: valore troppo lungo")

    # SICUREZZA: Verifica che contenga solo cifre, punto, virgola e spazi
    if not re.match(r'^[\d\s.,]+$', clean_str):
        raise ValidationError(f"{field_name}: contiene caratteri non validi")

    try:
        # Rimuovi spazi
        clean_str = clean_str.replace(' ', '')

        # Sostituisci virgola con punto
        clean_str = clean_str.replace(',', '.')

        # Rimuovi eventuali separatori delle migliaia
        parts = clean_str.split('.')
        if len(parts) > 2:
            clean_str = ''.join(parts[:-1]) + '.' + parts[-1]

        # Converte in float
        value = float(clean_str)

        # SICUREZZA: Valida range ragionevole
        if value < 0:
            raise ValidationError(f"{field_name} non può essere negativo")

        if value == 0:
            raise ValidationError(f"{field_name} deve essere maggiore di zero")

        # SICUREZZA: Limite massimo ragionevole (1 miliardo)
        if value > 1_000_000_000:
            raise ValidationError(f"{field_name}: valore troppo grande")

        # SICUREZZA: Massimo 2 decimali
        if round(value, 2) != value:
            # Arrotonda automaticamente
            value = round(value, 2)

        return value

    except ValueError:
        raise ValidationError(
            f"{field_name} non è un numero valido. "
            "Usa il formato: 123.45 o 123,45"
        )
    except InvalidOperation:
        raise ValidationError(f"{field_name} non è un numero valido")


def validate_required_text(value_str, field_name, min_length=1, max_length=None):
    """
    Valida un campo di testo obbligatorio CON SANITIZZAZIONE

    Args:
        value_str: Stringa da validare
        field_name: Nome del campo
        min_length: Lunghezza minima
        max_length: Lunghezza massima (opzionale)

    Returns:
        str: Testo validato e pulito

    Raises:
        ValidationError: Se la validazione fallisce
    """
    if not value_str or not value_str.strip():
        raise ValidationError(f"{field_name} è obbligatorio")

    clean_text = value_str.strip()

    # SICUREZZA: Rimuovi null bytes
    clean_text = clean_text.replace('\x00', '')

    # SICUREZZA: Rimuovi HTML/JavaScript (XSS protection)
    security = SecurityManager()
    clean_text = security.sanitize_html(clean_text)

    if len(clean_text) < min_length:
        raise ValidationError(
            f"{field_name} deve contenere almeno {min_length} caratteri"
        )

    if max_length and len(clean_text) > max_length:
        raise ValidationError(
            f"{field_name} non può superare {max_length} caratteri"
        )

    # SICUREZZA: Verifica pattern SQL injection
    try:
        security.sanitize_sql_input(clean_text, max_length or 500)
    except ValueError as e:
        raise ValidationError(
            f"{field_name} contiene caratteri o pattern non permessi: {e}"
        )

    return clean_text


def validate_date(date_obj, field_name="Data"):
    """
    Valida un oggetto QDate.

    Args:
        date_obj: QDate da validare
        field_name: Nome del campo

    Raises:
        ValidationError: Se la data non è valida
    """
    if not date_obj or not date_obj.isValid():
        raise ValidationError(f"{field_name} non è valida")

    # SICUREZZA: Verifica range date ragionevole
    year = date_obj.year()

    if year < 1900 or year > 2100:
        raise ValidationError(
            f"{field_name}: anno {year} fuori range permesso (1900-2100)"
        )


def validate_property_id(property_id):
    """
    Valida che property_id sia un intero positivo valido

    Args:
        property_id: ID da validare

    Returns:
        int: ID validato

    Raises:
        ValidationError: Se ID non valido
    """
    try:
        prop_id = int(property_id)
    except (ValueError, TypeError):
        raise ValidationError(f"ID proprietà non valido: {property_id}")

    if prop_id <= 0:
        raise ValidationError(f"ID proprietà deve essere positivo: {prop_id}")

    # SICUREZZA: Limite massimo ragionevole
    if prop_id > 2_147_483_647:  # Max INT in SQL
        raise ValidationError(f"ID proprietà troppo grande: {prop_id}")

    return prop_id


def validate_transaction_type(trans_type):
    """
    Valida tipo transazione

    Args:
        trans_type: Tipo da validare

    Returns:
        str: Tipo validato

    Raises:
        ValidationError: Se tipo non valido
    """
    if not trans_type:
        raise ValidationError("Tipo transazione obbligatorio")

    trans_type = trans_type.strip()

    # SICUREZZA: Whitelist strict
    valid_types = {'Entrata', 'Uscita'}

    if trans_type not in valid_types:
        raise ValidationError(
            f"Tipo transazione non valido: '{trans_type}'. "
            f"Valori permessi: {', '.join(valid_types)}"
        )

    return trans_type


def validate_date_string(date_str, field_name="Data"):
    """
    Valida una stringa data in formato dd/MM/yyyy

    Args:
        date_str: Stringa data
        field_name: Nome campo

    Returns:
        str: Data validata

    Raises:
        ValidationError: Se data non valida
    """
    if not date_str:
        raise ValidationError(f"{field_name} è obbligatoria")

    date_str = date_str.strip()

    # SICUREZZA: Verifica formato
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        raise ValidationError(
            f"{field_name} deve essere in formato dd/MM/yyyy"
        )

    try:
        day, month, year = date_str.split('/')
        day, month, year = int(day), int(month), int(year)
    except ValueError:
        raise ValidationError(f"{field_name}: formato non valido")

    # Valida range
    if not (1 <= day <= 31):
        raise ValidationError(f"{field_name}: giorno non valido ({day})")

    if not (1 <= month <= 12):
        raise ValidationError(f"{field_name}: mese non valido ({month})")

    if not (1900 <= year <= 2100):
        raise ValidationError(
            f"{field_name}: anno non valido ({year})"
        )

    return date_str


def format_currency(value, decimals=2):
    """
    Formatta un valore numerico come valuta (es: 1.234,56 €)
    CON VALIDAZIONE

    Args:
        value: Valore numerico
        decimals: Numero di decimali

    Returns:
        str: Stringa formattata
    """
    if value is None:
        return "0,00 €"

    try:
        # SICUREZZA: Assicura che sia float
        value = float(value)

        # SICUREZZA: Range check
        if value < -1_000_000_000 or value > 1_000_000_000:
            return "VALORE NON VALIDO"

        # Formatta con separatore migliaia e decimali
        formatted = f"{value:,.{decimals}f}"

        # Inverti separatori per formato italiano
        formatted = formatted.replace(',', 'TEMP')
        formatted = formatted.replace('.', ',')
        formatted = formatted.replace('TEMP', '.')

        return f"{formatted} €"

    except (ValueError, TypeError):
        return "0,00 €"


def sanitize_filename(filename, max_length=200):
    """
    Rimuove caratteri non validi dai nomi file.
    WRAPPER per SecurityManager

    Args:
        filename: Nome file da sanitizzare
        max_length: Lunghezza massima

    Returns:
        str: Nome file sicuro

    Raises:
        ValidationError: Se nome file non valido
    """
    security = SecurityManager()

    try:
        return security.sanitize_filename(filename, max_length)
    except ValueError as e:
        raise ValidationError(f"Nome file non valido: {e}")


def validate_amount_range(amount, field_name="Importo"):
    """
    Valida che un importo sia in un range ragionevole

    Args:
        amount: Importo da validare
        field_name: Nome campo

    Raises:
        ValidationError: Se fuori range
    """
    if not isinstance(amount, (int, float)):
        raise ValidationError(f"{field_name} deve essere numerico")

    # SICUREZZA: Range ragionevole per transazioni immobiliari
    if amount < 0.01:
        raise ValidationError(f"{field_name} deve essere almeno 0.01€")

    if amount > 10_000_000:  # 10 milioni di euro max
        raise ValidationError(
            f"{field_name} supera il limite massimo (10.000.000€)"
        )


def validate_metadata(metadata):
    """
    Valida metadati documento completi

    Args:
        metadata: Dict con metadati

    Returns:
        dict: Metadati validati

    Raises:
        ValidationError: Se metadati non validi
    """
    required_keys = {'tipo', 'provider', 'service', 'importo', 'data_fattura'}

    # Verifica chiavi obbligatorie
    missing = required_keys - set(metadata.keys())
    if missing:
        raise ValidationError(
            f"Metadati mancanti: {', '.join(missing)}"
        )

    validated = {}

    # Valida tipo
    validated['tipo'] = validate_transaction_type(metadata['tipo'])

    # Valida provider
    validated['provider'] = validate_required_text(
        metadata['provider'],
        "Fornitore",
        min_length=2,
        max_length=100
    )

    # Valida service
    validated['service'] = validate_required_text(
        metadata['service'],
        "Servizio",
        min_length=2,
        max_length=100
    )

    # Valida importo
    amount = parse_decimal(metadata['importo'], "Importo")
    validate_amount_range(amount)
    validated['importo'] = amount

    # Valida data
    validated['data_fattura'] = validate_date_string(
        metadata['data_fattura'],
        "Data fattura"
    )

    return validated