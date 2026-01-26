import os
import shutil
from pathlib import Path
from security_manager import SecurityManager


def get_docs_dir():
    """Ottiene directory documenti basata su environment"""
    from config import Config
    if Config.DOCS_DIR:
        return Config.DOCS_DIR
    return Path("docs")


class DocumentService:
    """Gestisce le operazioni sui documenti CON SICUREZZA"""

    def __init__(self, logger):
        self.logger = logger
        self.security = SecurityManager()
        self.docs_dir = get_docs_dir()

        # Crea cartella documenti se non esiste
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)

        # CRITICO: Salva path assoluto della docs_dir per validazione
        self.abs_docs_dir = os.path.abspath(self.docs_dir)

    def get_property_folder(self, property_id, sub_directory=None):
        """
        Ottiene il percorso SICURO della cartella di una proprietà

        Args:
            property_id: ID proprietà (DEVE essere int)
            sub_directory: Sottocartella opzionale

        Returns:
            Path sicuro

        Raises:
            ValueError: Se property_id non è valido o path traversal rilevato
        """
        # VALIDAZIONE CRITICA: property_id deve essere int
        try:
            property_id = int(property_id)
        except (ValueError, TypeError):
            raise ValueError(f"property_id non valido: {property_id}")

        # Costruisci path base
        base_path = os.path.join(self.docs_dir, f"property_{property_id}")

        # Se c'è una sottocartella, sanitizzala
        if sub_directory:
            # CRITICO: Sanitizza OGNI componente del path
            parts = sub_directory.split(os.sep)
            sanitized_parts = []

            for part in parts:
                if not part or part in ('.', '..'):
                    continue  # Ignora . e ..

                # Sanitizza ogni parte
                try:
                    safe_part = self.security.sanitize_filename(part)
                    sanitized_parts.append(safe_part)
                except ValueError as e:
                    self.logger.error(f"Path pericoloso rilevato: {sub_directory}")
                    raise ValueError(f"Sottocartella non valida: {e}")

            if sanitized_parts:
                base_path = os.path.join(base_path, *sanitized_parts)

        # VALIDAZIONE FINALE: Verifica che il path non esca da docs_dir
        abs_path = os.path.abspath(base_path)

        try:
            self.security.validate_path(abs_path, self.abs_docs_dir)
        except ValueError as e:
            self.logger.critical(f"PATH TRAVERSAL RILEVATO: {base_path}")
            raise ValueError("Path traversal rilevato!")

        return base_path

    def list_documents(self, property_id, sub_directory=None):
        """
        Lista i documenti di una proprietà in modo SICURO

        Args:
            property_id: ID proprietà
            sub_directory: Sottocartella opzionale

        Returns:
            Lista di dizionari con info file
        """
        try:
            folder = self.get_property_folder(property_id, sub_directory)
        except ValueError as e:
            self.logger.error(f"get_property_folder fallito: {e}")
            return []

        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            return []

        try:
            files = os.listdir(folder)
            files.sort()
        except PermissionError:
            self.logger.error(f"Permesso negato per: {folder}")
            return []

        documents = []
        for f in files:
            file_path = os.path.join(folder, f)

            # VALIDAZIONE: Verifica che file_path sia dentro folder
            try:
                self.security.validate_path(file_path, folder)
            except ValueError:
                self.logger.warning(f"File ignorato (fuori path): {f}")
                continue

            documents.append({
                "name": f,
                "path": file_path,
                "is_folder": os.path.isdir(file_path)
            })

        return documents

    def save_document(self, source_path, property_id, metadata):
        """
        Salva un documento in modo SICURO con validazione completa

        Args:
            source_path: Path del file sorgente
            property_id: ID proprietà
            metadata: Metadati documento

        Returns:
            Path destinazione o None se fallisce
        """
        # VALIDAZIONE 1: File upload sicuro
        validation = self.security.validate_file_upload(source_path)

        if not validation['valid']:
            self.logger.error(f"File non valido: {validation['error']}")
            raise ValueError(f"File non sicuro: {validation['error']}")

        self.logger.info(
            f"File validato: {os.path.basename(source_path)} "
            f"({validation['size'] / 1024:.1f} KB, {validation['mime_type']})"
        )

        # Estrai e valida metadati
        try:
            data_fattura = metadata['data_fattura']
            service = metadata['service']

            # VALIDAZIONE: Sanitizza service
            service = self.security.sanitize_sql_input(service, max_length=100)

        except KeyError as e:
            raise ValueError(f"Metadata mancante: {e}")

        # Parsing data
        try:
            parts = data_fattura.split("/")
            if len(parts) != 3:
                raise ValueError("Data formato non valido")

            giorno = parts[0]
            mese = parts[1]
            anno = parts[2]

            # Valida numeri
            int(giorno), int(mese), int(anno)

        except (ValueError, IndexError) as e:
            raise ValueError(f"Data non valida: {e}")

        # Costruisci struttura cartelle sicura
        trimestre = str((int(mese) - 1) // 3 + 1)
        sub_directory = os.path.join(service, anno, f"{trimestre}T")

        try:
            folder = self.get_property_folder(property_id, sub_directory)
        except ValueError as e:
            self.logger.error(f"Cartella non sicura: {e}")
            raise

        os.makedirs(folder, exist_ok=True)

        # SANITIZZA nome file
        original_filename = os.path.basename(source_path)
        file_extension = os.path.splitext(original_filename)[1]

        try:
            safe_service = self.security.sanitize_filename(service)
        except ValueError as e:
            raise ValueError(f"Nome servizio non valido: {e}")

        # Nuovo nome sicuro
        new_filename = f"{mese}_{anno}_{safe_service}{file_extension}"

        try:
            new_filename = self.security.sanitize_filename(new_filename)
        except ValueError as e:
            raise ValueError(f"Nome file risultante non valido: {e}")

        dest_path = os.path.join(folder, new_filename)

        # VALIDAZIONE FINALE: Verifica path destinazione
        try:
            self.security.validate_path(dest_path, self.abs_docs_dir)
        except ValueError:
            self.logger.critical(f"PATH TRAVERSAL in save: {dest_path}")
            raise ValueError("Operazione bloccata: path non sicuro")

        # Gestisci duplicati
        counter = 1
        while os.path.exists(dest_path):
            base_name = f"{mese}_{anno}_{safe_service}_{counter}"
            new_filename = f"{base_name}{file_extension}"
            dest_path = os.path.join(folder, new_filename)
            counter += 1

            if counter > 999:  # Safety limit
                raise ValueError("Troppi file con lo stesso nome")

        # COPIA FILE (NON move per sicurezza)
        try:
            shutil.copy2(source_path, dest_path)

            # Verifica che il file sia stato copiato correttamente
            if not os.path.exists(dest_path):
                raise IOError("File non copiato")

            copied_size = os.path.getsize(dest_path)
            if copied_size != validation['size']:
                os.remove(dest_path)  # Rimuovi file corrotto
                raise IOError("Dimensione file copiato non corrisponde")

            self.logger.info(f"Documento salvato: {new_filename}")
            return dest_path

        except Exception as e:
            self.logger.error(f"Errore salvataggio documento: {e}")
            # Cleanup in caso di errore
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except:
                    pass
            return None

    def delete_document(self, file_path):
        """
        Elimina un documento in modo SICURO

        Args:
            file_path: Path del file da eliminare

        Returns:
            True se successo
        """
        # VALIDAZIONE: Path deve essere dentro docs_dir
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
        """
        Crea una nuova cartella in modo SICURO

        Args:
            property_id: ID proprietà
            folder_name: Nome cartella
            sub_directory: Sottocartella opzionale

        Returns:
            Path della nuova cartella o None
        """
        # SANITIZZA nome cartella
        try:
            safe_folder_name = self.security.sanitize_filename(folder_name)
        except ValueError as e:
            self.logger.error(f"Nome cartella non valido: {e}")
            return None

        try:
            folder = self.get_property_folder(property_id, sub_directory)
            new_folder = os.path.join(folder, safe_folder_name)

            # Valida path finale
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
        """
        Elimina la cartella documenti di una proprietà in modo SICURO

        Args:
            property_id: ID proprietà

        Returns:
            dict con risultato operazione
        """
        result = {
            'success': False,
            'folder_path': None,
            'files_deleted': 0,
            'folders_deleted': 0,
            'error': None
        }

        try:
            folder_path = self.get_property_folder(property_id)
            result['folder_path'] = folder_path
        except ValueError as e:
            result['error'] = f"Path non valido: {e}"
            return result

        # Se non esiste, considera successo
        if not os.path.exists(folder_path):
            result['success'] = True
            return result

        # VALIDAZIONE FINALE prima di eliminare
        try:
            self.security.validate_path(folder_path, self.abs_docs_dir)
        except ValueError:
            result['error'] = "Operazione bloccata: path non sicuro"
            self.logger.critical(f"Tentativo eliminazione path pericoloso: {folder_path}")
            return result

        try:
            # Conta file
            for root, dirs, files in os.walk(folder_path):
                result['files_deleted'] += len(files)
                result['folders_deleted'] += len(dirs)

            # Elimina ricorsivamente
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

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"