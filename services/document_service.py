import os
import shutil

DOCS_DIR = "docs"


class DocumentService:
    """Gestisce le operazioni sui documenti"""

    def __init__(self, conn, logger):
        self.conn = conn
        self.cursor = conn.cursor()
        self.logger = logger

        # Crea cartella documenti se non esiste
        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

    def get_property_folder(self, property_id, sub_directory=None):
        """Ottiene il percorso della cartella di una proprietà usando l'ID"""

        # Usa property_id per associare cartella a quella proprietà
        base_path = os.path.join(DOCS_DIR, f"property_{property_id}")
        if sub_directory:
            return os.path.join(base_path, sub_directory)
        return base_path

    def list_documents(self, property_id, sub_directory=None):
        """Lista i documenti di una proprietà usando l'ID"""

        folder = self.get_property_folder(property_id, sub_directory)

        if not os.path.exists(folder):
            os.makedirs(folder)
            return []

        files = os.listdir(folder)
        files.sort()

        documents = []
        for f in files:
            file_path = os.path.join(folder, f)
            documents.append({
                "name": f,
                "path": file_path,
                "is_folder": os.path.isdir(file_path)
            })

        return documents

    def save_document(self, source_path, property_id, metadata):
        """Salva un documento nella cartella della proprietà con rinomina automatica"""

        # Estrai data fattura e servizio dai metadati
        data_fattura = metadata['data_fattura']  # Formato: dd/MM/yyyy
        service = metadata['service']

        # Estrai mese e anno dalla data (formato: dd/MM/yyyy)
        parts = data_fattura.split("/")
        giorno = parts[0]
        mese = parts[1]
        anno = parts[2]

        # Crea struttura cartelle: servizio/anno/trimestre
        trimestre = str((int(mese) - 1) // 3 + 1)
        sub_directory = os.path.join(service, anno, f"{trimestre}T")

        folder = self.get_property_folder(property_id, sub_directory)
        os.makedirs(folder, exist_ok=True)

        # RINOMINA FILE: mese_anno_servizio.estensione
        original_filename = os.path.basename(source_path)
        file_extension = os.path.splitext(original_filename)[1]

        # rimuovi caratteri non validi dal nome del servizio
        safe_service = "".join(c for c in service if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_service = safe_service.replace(' ', '_')

        # Nuovo nome: mese_anno_servizio.estensione
        new_filename = f"{mese}_{anno}_{safe_service}{file_extension}"
        dest_path = os.path.join(folder, new_filename)

        # Gestisci file duplicati (se esiste già, aggiungi un numero)
        counter = 1
        while os.path.exists(dest_path):
            new_filename = f"{mese}_{anno}_{safe_service}_{counter}{file_extension}"
            dest_path = os.path.join(folder, new_filename)
            counter += 1

        try:
            shutil.copy(source_path, dest_path)

            self.logger.info(f"Document_service: Documento salvato come: {new_filename}")
            return dest_path
        except Exception as e:
            self.logger.error(f"Document_service:Errore salvataggio documento: {e}")
            return None

    def delete_document(self, file_path):
        """Elimina un documento"""
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            self.logger.info(f"Document_service: Documento eliminato correttamente: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Document_service:Errore eliminazione documento: {e}")
            return False

    def create_folder(self, property_id, folder_name, sub_directory=None):
        """Crea una nuova cartella usando l'ID proprietà"""
        folder = self.get_property_folder(property_id, sub_directory)
        new_folder = os.path.join(folder, folder_name)

        try:
            os.makedirs(new_folder, exist_ok=True)
            self.logger.info(f"Document_service: Cartella creata con successo: {new_folder}")
            return new_folder
        except Exception as e:
            self.logger.error(f"Document_service:Errore creazione cartella: {e}")
            return None

    def delete_property_folder(self, property_id):
        """Elimina la cartella documenti di una proprietà"""

        folder_path = self.get_property_folder(property_id)

        result = {
            'success': False,
            'folder_path': folder_path,
            'files_deleted': 0,
            'folders_deleted': 0,
            'error': None
        }

        # Se la cartella non esiste, considera come successo
        if not os.path.exists(folder_path):
            result['success'] = True
            return result

        try:
            # Conta file e sottocartelle prima di eliminare
            for root, dirs, files in os.walk(folder_path):
                result['files_deleted'] += len(files)
                result['folders_deleted'] += len(dirs)

            # Elimina ricorsivamente
            shutil.rmtree(folder_path)
            result['success'] = True

            self.logger.info(f"️DocumentService:Cartella eliminata: {folder_path}")
            self.logger.info(f"️DocumentService:File eliminati: {result['files_deleted']}")
            self.logger.info(f"️DocumentService:Cartelle eliminate: {result['folders_deleted']}")

        except PermissionError as e:
            result['error'] = f"Permessi insufficienti: {str(e)}"
            self.logger.error(f"DocumentService: {result['error']}")
        except Exception as e:
            result['error'] = f"Errore generico: {str(e)}"
            self.logger.error(f"DocumentService: {result['error']}")

        return result

    def get_property_folder_size(self, property_id):
        """Calcola la dimensione totale della cartella documenti"""
        folder_path = self.get_property_folder(property_id)

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
            self.logger.error(f"DocumentService:Errore calcolo dimensione: {e}")

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
