"""
resources.py
============
Percorsi delle risorse incluse nell'app (icone, immagini).

In sviluppo la base è la cartella del progetto; nell'eseguibile PyInstaller
è sys._MEIPASS, cioè la cartella _internal. I percorsi relativi alla
directory corrente non funzionano nel build: la cartella di lavoro è quella
dell'exe, dove le icone non ci sono.
"""
import sys
from pathlib import Path

_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def resource_path(relativo: str) -> str:
    """Percorso assoluto di una risorsa, es. resource_path("assets/splash.png")."""
    return str(_BASE / relativo)


def icon_path(nome_file: str) -> str:
    """Percorso assoluto di un'icona nella cartella icons/."""
    return str(_BASE / "icons" / nome_file)


def icon_url(nome_file: str) -> str:
    """Percorso per url() nei fogli di stile Qt: sempre con le barre dritte."""
    return (_BASE / "icons" / nome_file).as_posix()
