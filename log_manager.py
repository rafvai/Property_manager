import logging
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


class LogManager:
    """Gestisce la creazione, rotazione e archiviazione dei log"""

    def __init__(self, log_dir="logs", archive_dir="logs/archives", max_log_size_mb=10, max_age_days=30):
        """
        Inizializza il gestore dei log

        Args:
            log_dir: Directory principale dei log
            archive_dir: Directory per gli archivi zip
            max_log_size_mb: Dimensione massima del file log prima della rotazione (MB)
            max_age_days: Età massima dei log prima dell'archiviazione (giorni)
        """
        self.log_dir = Path(log_dir)
        self.archive_dir = Path(archive_dir)
        self.max_log_size = max_log_size_mb * 1024 * 1024  # Converti in byte
        self.max_age_days = max_age_days

        # Crea le directory se non esistono
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # File log correnti
        self.app_log = self.log_dir / "app.log"
        self.error_log = self.log_dir / "error.log"
        self.transaction_log = self.log_dir / "transactions.log"

    def setup_logging(self):
        """
        Configura il sistema di logging dell'applicazione
        Ritorna il logger principale
        """
        # Logger principale
        logger = logging.getLogger("PropertyManager")
        logger.setLevel(logging.DEBUG)

        # Rimuovi handler esistenti per evitare duplicati
        logger.handlers.clear()

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler per app.log (INFO e superiori)
        app_handler = logging.FileHandler(self.app_log, encoding='utf-8')
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(formatter)
        logger.addHandler(app_handler)

        # Handler per error.log (solo ERROR e CRITICAL)
        error_handler = logging.FileHandler(self.error_log, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        # Handler console (opzionale, per debug)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def rotate_logs(self):
        """
        Ruota i log se superano la dimensione massima
        I log vecchi vengono rinominati con timestamp
        """
        rotated_files = []

        for log_file in [self.app_log, self.error_log, self.transaction_log]:
            if not log_file.exists():
                continue

            # Controlla dimensione
            if log_file.stat().st_size > self.max_log_size:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{log_file.stem}_{timestamp}.log"
                rotated_path = log_file.parent / rotated_name

                # Rinomina il file corrente
                log_file.rename(rotated_path)
                rotated_files.append(rotated_path)

                print(f"✅ Log ruotato: {log_file.name} → {rotated_name}")

        return rotated_files

    def archive_old_logs(self):
        """
        Archivia in zip tutti i log più vecchi di max_age_days
        Ritorna il numero di file archiviati
        """
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        archived_count = 0

        # Trova tutti i file .log nella directory
        log_files = list(self.log_dir.glob("*.log"))

        # Escludi i file correnti
        current_files = {self.app_log.name, self.error_log.name, self.transaction_log.name}
        old_logs = [f for f in log_files if f.name not in current_files]

        if not old_logs:
            print("ℹ️ Nessun log vecchio da archiviare")
            return 0

        # Crea archive zip con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"logs_archive_{timestamp}.zip"
        archive_path = self.archive_dir / archive_name

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for log_file in old_logs:
                # Controlla se è più vecchio del limite
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)

                if file_time < cutoff_date:
                    # Aggiungi al zip
                    zipf.write(log_file, arcname=log_file.name)
                    archived_count += 1

                    # Elimina il file originale
                    log_file.unlink()
                    print(f"📦 Archiviato: {log_file.name}")

        # Se non abbiamo archiviato nulla, elimina il zip vuoto
        if archived_count == 0:
            archive_path.unlink()
            print("ℹ️ Nessun log abbastanza vecchio da archiviare")
        else:
            print(f"✅ Archiviati {archived_count} file in {archive_name}")

        return archived_count

    def compress_log(self, log_file_path):
        """
        Comprimi un singolo file log in zip

        Args:
            log_file_path: Path del file da comprimere

        Returns:
            Path del file zip creato
        """
        log_path = Path(log_file_path)

        if not log_path.exists():
            raise FileNotFoundError(f"File log non trovato: {log_file_path}")

        # Nome del file zip
        zip_name = f"{log_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.archive_dir / zip_name

        # Comprimi
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(log_path, arcname=log_path.name)

        print(f"✅ File compresso: {zip_path}")
        return zip_path

    def compress_multiple_logs(self, log_files, archive_name=None):
        """
        Comprimi più file log in un unico zip

        Args:
            log_files: Lista di Path o stringhe con i file da comprimere
            archive_name: Nome personalizzato per l'archivio (opzionale)

        Returns:
            Path del file zip creato
        """
        if not log_files:
            raise ValueError("Nessun file da comprimere")

        # Nome archivio
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"logs_batch_{timestamp}.zip"

        if not archive_name.endswith('.zip'):
            archive_name += '.zip'

        zip_path = self.archive_dir / archive_name

        # Comprimi tutti i file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for log_file in log_files:
                log_path = Path(log_file)
                if log_path.exists():
                    zipf.write(log_path, arcname=log_path.name)
                    print(f"📦 Aggiunto al zip: {log_path.name}")
                else:
                    print(f"⚠️ File non trovato, saltato: {log_file}")

        print(f"✅ Archivio creato: {zip_path}")
        return zip_path

    def clean_old_archives(self, max_archive_age_days=90):
        """
        Elimina gli archivi zip più vecchi di max_archive_age_days

        Args:
            max_archive_age_days: Età massima degli archivi (giorni)

        Returns:
            Numero di archivi eliminati
        """
        cutoff_date = datetime.now() - timedelta(days=max_archive_age_days)
        deleted_count = 0

        # Trova tutti i file .zip nella directory archivi
        archive_files = list(self.archive_dir.glob("*.zip"))

        for archive in archive_files:
            file_time = datetime.fromtimestamp(archive.stat().st_mtime)

            if file_time < cutoff_date:
                archive.unlink()
                deleted_count += 1
                print(f"🗑️ Archivio eliminato: {archive.name}")

        if deleted_count == 0:
            print("ℹ️ Nessun archivio da eliminare")
        else:
            print(f"✅ Eliminati {deleted_count} archivi vecchi")

        return deleted_count

    def get_log_stats(self):
        """
        Ottiene statistiche sui log

        Returns:
            Dizionario con statistiche
        """
        stats = {
            "log_files": 0,
            "total_log_size_mb": 0,
            "archives": 0,
            "total_archive_size_mb": 0,
            "oldest_log": None,
            "newest_log": None
        }

        # Statistiche log attivi
        log_files = list(self.log_dir.glob("*.log"))
        stats["log_files"] = len(log_files)

        if log_files:
            total_size = sum(f.stat().st_size for f in log_files)
            stats["total_log_size_mb"] = round(total_size / (1024 * 1024), 2)

            # Trova più vecchio e più recente
            times = [(f, f.stat().st_mtime) for f in log_files]
            oldest = min(times, key=lambda x: x[1])
            newest = max(times, key=lambda x: x[1])

            stats["oldest_log"] = {
                "name": oldest[0].name,
                "date": datetime.fromtimestamp(oldest[1]).strftime("%Y-%m-%d %H:%M:%S")
            }
            stats["newest_log"] = {
                "name": newest[0].name,
                "date": datetime.fromtimestamp(newest[1]).strftime("%Y-%m-%d %H:%M:%S")
            }

        # Statistiche archivi
        archive_files = list(self.archive_dir.glob("*.zip"))
        stats["archives"] = len(archive_files)

        if archive_files:
            total_size = sum(f.stat().st_size for f in archive_files)
            stats["total_archive_size_mb"] = round(total_size / (1024 * 1024), 2)

        return stats

    def maintenance(self):
        """
        Esegue manutenzione completa:
        1. Ruota i log troppo grandi
        2. Archivia i log vecchi
        3. Pulisce gli archivi molto vecchi

        Returns:
            Dizionario con report della manutenzione
        """
        print("\n🔧 Avvio manutenzione log...")

        report = {
            "rotated": 0,
            "archived": 0,
            "cleaned_archives": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 1. Rotazione
        rotated = self.rotate_logs()
        report["rotated"] = len(rotated)

        # 2. Archiviazione
        report["archived"] = self.archive_old_logs()

        # 3. Pulizia archivi vecchi
        report["cleaned_archives"] = self.clean_old_archives()

        print(f"\n✅ Manutenzione completata!")
        print(f"   - Log ruotati: {report['rotated']}")
        print(f"   - File archiviati: {report['archived']}")
        print(f"   - Archivi eliminati: {report['cleaned_archives']}")

        return report