"""
transaction_types.py
====================
Valori canonici (invarianti) per il tipo di transazione.
Questi sono i valori salvati nel DB — MAI tradurli prima di salvare.
La traduzione avviene solo al momento della visualizzazione.
"""

INCOME = "Entrata"   # canonical / DB value
EXPENSE = "Uscita"   # canonical / DB value

VALID_TYPES = {INCOME, EXPENSE}


def label_to_canonical(label: str, tm) -> str:
    """
    Converte un'etichetta tradotta nel valore canonico.
    Usare nel get_data() dei dialog prima di salvare.

    Args:
        label: testo visualizzato (es. "Guadagno", "Income", "Ganancia")
        tm: TranslationManager attivo

    Returns:
        "Entrata" o "Uscita"

    Raises:
        ValueError se il label non corrisponde a nessun tipo noto
    """
    income_labels = {
        tm.get("ETICHETTE", "GUADAGNO", language=lang)
        for lang in tm.get_available_languages()
    }
    expense_labels = {
        tm.get("ETICHETTE", "SPESA", language=lang)
        for lang in tm.get_available_languages()
    }

    if label in income_labels:
        return INCOME
    if label in expense_labels:
        return EXPENSE

    # fallback: se già canonico, accettalo
    if label == INCOME:
        return INCOME
    if label == EXPENSE:
        return EXPENSE

    raise ValueError(f"Tipo transazione non riconosciuto: '{label}'")


def canonical_to_label(canonical: str, tm) -> str:
    """
    Converte il valore canonico nell'etichetta tradotta per la lingua corrente.
    Usare solo per la visualizzazione.

    Args:
        canonical: "Entrata" o "Uscita"
        tm: TranslationManager attivo

    Returns:
        Stringa tradotta
    """
    if canonical == INCOME:
        return tm.get("ETICHETTE", "GUADAGNO")
    if canonical == EXPENSE:
        return tm.get("ETICHETTE", "SPESA")
    return canonical  # passthrough se già sconosciuto
