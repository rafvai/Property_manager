import os
import shutil
from pathlib import Path
from security_manager import SecurityManager
from config import Config
from datetime import date as date_type


def get_docs_dir() -> Path:
    """
    Ritorna la directory documenti corretta in base all'ambiente.
    Unica fonte di verità: Config.DOCS_DIR.
    """
    if Config.DOCS_DIR:
        return Path(Config.DOCS_DIR)
    # Fallback difensivo (non dovrebbe mai scattare)
    return Path('docs').absolute()


class DocumentService:
    """Gestisce le operazioni sui documenti CON SICUREZZA"""

    def __init__(self, logger):
        self.logger   = logger
        self.security = SecurityManager()
        self.docs_dir = get_docs_dir()

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.abs_docs_dir = str(self.docs_dir.resolve())

    def get_property_folder(self, property_id, sub_directory=None):
        """
        Ottiene il percorso SICURO della cartella di una proprietà.

        Args:
            property_id  : ID proprietà (deve essere int o stringa numerica)
            sub_directory: Sottocartella opzionale

        Returns:
            Path stringa sicuro

        Raises:
            ValueError: Se property_id non valido o path traversal rilevato
        """
        try:
            property_id = int(property_id)
        except (ValueError, TypeError):
            raise ValueError(f"property_id non valido: {property_id}")

        base_path = self.docs_dir / Config.CURRENT_TENANT_ID / f"property_{property_id}"

        if sub_directory:
            parts           = sub_directory.split(os.sep)
            sanitized_parts = []
            for part in parts:
                if not part or part in ('.', '..'):
                    continue
                try:
                    sanitized_parts.append(self.security.sanitize_filename(part))
                except ValueError as e:
                    self.logger.error(f"Path pericoloso rilevato: {sub_directory}")
                    raise ValueError(f"Sottocartella non valida: {e}")
            if sanitized_parts:
                base_path = base_path / Path(*sanitized_parts)

        abs_path = str(Path(base_path).resolve())
        try:
            self.security.validate_path(abs_path, self.abs_docs_dir)
        except ValueError:
            self.logger.critical(f"PATH TRAVERSAL RILEVATO: {base_path}")
            raise ValueError("Path traversal rilevato!")

        return str(base_path)

    def list_documents(self, property_id, sub_directory=None):
        """Lista i documenti di una proprietà in modo sicuro"""
        try:
            folder = self.get_property_folder(property_id, sub_directory)
        except ValueError as e:
            self.logger.error(f"get_property_folder fallito: {e}")
            return []

        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            return []

        try:
            files = sorted(os.listdir(folder))
        except PermissionError:
            self.logger.error(f"Permesso negato per: {folder}")
            return []

        documents = []
        for f in files:
            file_path = os.path.join(folder, f)
            try:
                self.security.validate_path(file_path, folder)
            except ValueError:
                self.logger.warning(f"File ignorato (fuori path): {f}")
                continue
            documents.append({
                "name"     : f,
                "path"     : file_path,
                "is_folder": os.path.isdir(file_path)
            })
        return documents

    def save_document(self, source_path, property_id, metadata):
        """Salva un documento in modo sicuro con validazione completa"""
        validation = self.security.validate_file_upload(source_path)
        if not validation['valid']:
            self.logger.error(f"File non valido: {validation['error']}")
            raise ValueError(f"File non sicuro: {validation['error']}")

        self.logger.info(
            f"File validato: {os.path.basename(source_path)} "
            f"({validation['size'] / 1024:.1f} KB, {validation['mime_type']})"
        )

        try:
            data_fattura = metadata['data_fattura']
            service      = metadata['service']
            service      = self.security.sanitize_sql_input(service, max_length=100)
        except KeyError as e:
            raise ValueError(f"Metadata mancante: {e}")

        if not isinstance(data_fattura, date_type):
            raise ValueError(
                f"data_fattura deve essere un oggetto datetime.date, "
                f"ricevuto: {type(data_fattura).__name__}. "
                f"Usa QDate.toPython() nel dialog."
            )
        giorno = str(data_fattura.day).zfill(2)
        mese = str(data_fattura.month).zfill(2)
        anno = str(data_fattura.year)

        trimestre    = str((int(mese) - 1) // 3 + 1)
        sub_directory = os.path.join(service, anno, f"{trimestre}T")

        try:
            folder = self.get_property_folder(property_id, sub_directory)
        except ValueError as e:
            self.logger.error(f"Cartella non sicura: {e}")
            raise

        os.makedirs(folder, exist_ok=True)

        original_filename = os.path.basename(source_path)
        file_extension    = os.path.splitext(original_filename)[1]

        try:
            safe_service = self.security.sanitize_filename(service)
        except ValueError as e:
            raise ValueError(f"Nome servizio non valido: {e}")

        new_filename = f"{mese}_{anno}_{safe_service}{file_extension}"
        try:
            new_filename = self.security.sanitize_filename(new_filename)
        except ValueError as e:
            raise ValueError(f"Nome file risultante non valido: {e}")

        dest_path = os.path.join(folder, new_filename)
        try:
            self.security.validate_path(dest_path, self.abs_docs_dir)
        except ValueError:
            self.logger.critical(f"PATH TRAVERSAL in save: {dest_path}")
            raise ValueError("Operazione bloccata: path non sicuro")

        counter = 1
        while os.path.exists(dest_path):
            new_filename = f"{mese}_{anno}_{safe_service}_{counter}{file_extension}"
            dest_path    = os.path.join(folder, new_filename)
            counter     += 1
            if counter > 999:
                raise ValueError("Troppi file con lo stesso nome")

        try:
            shutil.copy2(source_path, dest_path)
            if not os.path.exists(dest_path):
                raise IOError("File non copiato")
            if os.path.getsize(dest_path) != validation['size']:
                os.remove(dest_path)
                raise IOError("Dimensione file copiato non corrisponde")
            self.logger.info(f"Documento salvato: {new_filename}")
            return dest_path
        except Exception as e:
            self.logger.error(f"Errore salvataggio documento: {e}")
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return None

    def delete_document(self, file_path):
        """Elimina un documento in modo sicuro"""
        try:
            abs_path = os.path.abspath(file_path)
            self.security.validate_path(abs_path, self.abs_docs_dir)
        except ValueError:
            self.logger.critical(f"Tentativo eliminazione path non sicuro: {file_path}")
            return False

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            self.logger.info(f"Documento eliminato: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Errore eliminazione documento: {e}")
            return False

    def create_folder(self, property_id, folder_name, sub_directory=None):
        """Crea una nuova cartella in modo sicuro"""
        try:
            safe_folder_name = self.security.sanitize_filename(folder_name)
        except ValueError as e:
            self.logger.error(f"Nome cartella non valido: {e}")
            return None

        try:
            folder     = self.get_property_folder(property_id, sub_directory)
            new_folder = os.path.join(folder, safe_folder_name)
            self.security.validate_path(new_folder, self.abs_docs_dir)
            os.makedirs(new_folder, exist_ok=True)
            self.logger.info(f"Cartella creata: {new_folder}")
            return new_folder
        except ValueError as e:
            self.logger.error(f"Creazione cartella fallita: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Errore creazione cartella: {e}")
            return None

    def delete_property_folder(self, property_id):
        """Elimina la cartella documenti di una proprietà in modo sicuro"""
        result = {
            'success'         : False,
            'folder_path'     : None,
            'files_deleted'   : 0,
            'folders_deleted' : 0,
            'error'           : None
        }

        try:
            folder_path = self.get_property_folder(property_id)
            result['folder_path'] = folder_path
        except ValueError as e:
            result['error'] = f"Path non valido: {e}"
            return result

        if not os.path.exists(folder_path):
            result['success'] = True
            return result

        try:
            self.security.validate_path(folder_path, self.abs_docs_dir)
        except ValueError:
            result['error'] = "Operazione bloccata: path non sicuro"
            self.logger.critical(f"Tentativo eliminazione path pericoloso: {folder_path}")
            return result

        try:
            for root, dirs, files in os.walk(folder_path):
                result['files_deleted']   += len(files)
                result['folders_deleted'] += len(dirs)
            shutil.rmtree(folder_path)
            result['success'] = True
            self.logger.info(
                f"Cartella eliminata: {folder_path} "
                f"({result['files_deleted']} file, {result['folders_deleted']} cartelle)"
            )
        except PermissionError as e:
            result['error'] = f"Permessi insufficienti: {str(e)}"
            self.logger.error(result['error'])
        except Exception as e:
            result['error'] = f"Errore: {str(e)}"
            self.logger.error(result['error'])

        return result

    def get_property_folder_size(self, property_id):
        """Calcola dimensione cartella documenti"""
        try:
            folder_path = self.get_property_folder(property_id)
        except ValueError:
            return 0

        if not os.path.exists(folder_path):
            return 0

        total_size = 0
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            self.logger.error(f"Errore calcolo dimensione: {e}")
        return total_size

    def format_size(self, size_bytes):
        """Formatta dimensione in formato leggibile"""
        if size_bytes == 0:
            return "0 B"
        units      = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size       = float(size_bytes)
        while size >= 1024 and unit_index < len(units) - 1:
            size      /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"