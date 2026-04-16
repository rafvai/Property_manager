"""
services/translation_sync_service.py
Scarica translations.db dal license server se obsoleto.
Funziona anche offline: usa il file locale come fallback silenzioso.
"""
import hashlib
import os
import requests
from pathlib import Path


CONNECT_TIMEOUT = 5
READ_TIMEOUT    = 15


class TranslationSyncService:

    def __init__(self, server_url: str, local_path: Path, logger):
        self.server_url = server_url.rstrip("/")
        self.local_path = Path(local_path)
        self.logger     = logger

    def sync(self) -> bool:
        """
        Ritorna True se il file locale è aggiornato (già ok o scaricato ora).
        Ritorna False solo se non c'è nessun file locale E il server non è raggiungibile.
        Mai solleva eccezioni: l'app deve sempre avviarsi.
        """
        if not self.server_url:
            self.logger.warning("TranslationSync: LICENSE_SERVER_URL non impostato — skip sync")
            return self.local_path.exists()

        try:
            resp = requests.get(
                f"{self.server_url}/translations/version",
                timeout=CONNECT_TIMEOUT
            )
            if resp.status_code != 200:
                self.logger.warning(f"TranslationSync: version check fallito ({resp.status_code})")
                return self.local_path.exists()

            remote_hash = resp.json().get("hash", "")

            if self.local_path.exists() and self._local_hash() == remote_hash:
                self.logger.info("TranslationSync: già aggiornato, skip download")
                return True

            self.logger.info("TranslationSync: download in corso...")
            dl = requests.get(
                f"{self.server_url}/translations/download",
                timeout=READ_TIMEOUT
            )
            if dl.status_code == 200:
                self.local_path.parent.mkdir(parents=True, exist_ok=True)
                self.local_path.write_bytes(dl.content)
                self.logger.info(f"TranslationSync: aggiornato ({len(dl.content)} bytes)")
                return True
            else:
                self.logger.warning(f"TranslationSync: download fallito ({dl.status_code})")
                return self.local_path.exists()

        except requests.exceptions.ConnectionError:
            self.logger.warning("TranslationSync: server non raggiungibile — uso locale")
            return self.local_path.exists()
        except Exception as e:
            self.logger.warning(f"TranslationSync: errore inatteso: {e} — uso locale")
            return self.local_path.exists()

    def _local_hash(self) -> str:
        sha = hashlib.sha256()
        with open(self.local_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()[:16]