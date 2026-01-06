"""
Utilità per la validazione degli input utente
Gestisce automaticamente separatori decimali (virgola e punto)
"""
from decimal import Decimal, InvalidOperation


class ValidationError(Exception):
    """Eccezione personalizzata per errori di validazione"""
    pass


def parse_decimal(value_str, field_name="Importo"):
    """
    Converte una stringa in numero decimale gestendo sia virgola che punto.

    Args:
        value_str: Stringa da convertire
        field_name: Nome del campo per messaggi di errore

    Returns:
        float: Valore numerico convertito

    Raises:
        ValidationError: Se la conversione fallisce
    """
    if not value_str or not value_str.strip():
        raise ValidationError(f"{field_name} è obbligatorio")

    try:
        # Rimuovi spazi
        clean_str = value_str.strip()

        # Sostituisci virgola con punto
        clean_str = clean_str.replace(',', '.')

        # Rimuovi eventuali separatori delle migliaia (punto o virgola)
        # Mantieni solo l'ultimo punto (separatore decimale)
        parts = clean_str.split('.')
        if len(parts) > 2:
            # Se ci sono più punti, significa che alcuni sono separatori migliaia
            # Es: 1.234.567,89 diventa 1234567.89
            clean_str = ''.join(parts[:-1]) + '.' + parts[-1]

        # Converte in float
        value = float(clean_str)

        # Verifica che sia un numero valido
        if value < 0:
            raise ValidationError(f"{field_name} non può essere negativo")

        if value == 0:
            raise ValidationError(f"{field_name} deve essere maggiore di zero")

        return value

    except ValueError:
        raise ValidationError(f"{field_name} non è un numero valido. Usa il formato: 123.45 o 123,45")
    except InvalidOperation:
        raise ValidationError(f"{field_name} non è un numero valido")


def validate_required_text(value_str, field_name, min_length=1, max_length=None):
    """
    Valida un campo di testo obbligatorio.

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

    if len(clean_text) < min_length:
        raise ValidationError(f"{field_name} deve contenere almeno {min_length} caratteri")

    if max_length and len(clean_text) > max_length:
        raise ValidationError(f"{field_name} non può superare {max_length} caratteri")

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


def format_currency(value, decimals=2):
    """
    Formatta un valore numerico come valuta (es: 1.234,56 €)

    Args:
        value: Valore numerico
        decimals: Numero di decimali

    Returns:
        str: Stringa formattata
    """
    if value is None:
        return "0,00 €"

    try:
        # Formatta con separatore migliaia e decimali
        formatted = f"{float(value):,.{decimals}f}"

        # Sostituisci separatori per formato italiano
        # Python usa punto per migliaia e virgola per decimali (formato US)
        # Invertiamo per il formato IT
        formatted = formatted.replace(',', 'TEMP')
        formatted = formatted.replace('.', ',')
        formatted = formatted.replace('TEMP', '.')

        return f"{formatted} €"
    except (ValueError, TypeError):
        return "0,00 €"


def sanitize_filename(filename, max_length=200):
    """
    Rimuove caratteri non validi dai nomi file.

    Args:
        filename: Nome file da sanitizzare
        max_length: Lunghezza massima

    Returns:
        str: Nome file sicuro
    """
    # Caratteri non permessi in Windows
    invalid_chars = '<>:"/\\|?*'

    clean_name = filename
    for char in invalid_chars:
        clean_name = clean_name.replace(char, '_')

    # Rimuovi spazi multipli
    clean_name = ' '.join(clean_name.split())

    # Tronca se troppo lungo
    if len(clean_name) > max_length:
        name_part, ext = clean_name.rsplit('.', 1) if '.' in clean_name else (clean_name, '')
        max_name_length = max_length - len(ext) - 1
        clean_name = name_part[:max_name_length] + ('.' + ext if ext else '')

    return clean_name.strip()