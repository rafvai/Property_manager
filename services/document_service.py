import os
import shutil

DOCS_DIR = "docs"


class DocumentService:
    """Gestisce le operazioni sui documenti"""

    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

        # Crea cartella documenti se non esiste
        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

    def get_property_folder(self, property_id, sub_directory=None):
        """Ottiene il percorso della cartella di una proprietà usando l'ID"""
        # 🔧 FIX: Usa property_id invece del nome
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

        # 🆕 RINOMINA FILE: mese_anno_servizio.estensione
        original_filename = os.path.basename(source_path)
        file_extension = os.path.splitext(original_filename)[1]  # Es: .pdf

        # Sanitizza il nome del servizio (rimuovi caratteri non validi)
        safe_service = "".join(c for c in service if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_service = safe_service.replace(' ', '_')

        # Nuovo nome: mese_anno_servizio.estensione
        new_filename = f"{mese}_{anno}_{safe_service}{file_extension}"
        dest_path = os.path.join(folder, new_filename)

        # 🔧 Gestisci file duplicati (se esiste già, aggiungi un numero)
        counter = 1
        while os.path.exists(dest_path):
            new_filename = f"{mese}_{anno}_{safe_service}_{counter}{file_extension}"
            dest_path = os.path.join(folder, new_filename)
            counter += 1

        try:
            shutil.copy(source_path, dest_path)
            print(f"✅ Documento salvato come: {new_filename}")
            return dest_path
        except Exception as e:
            print(f"❌ Errore salvataggio documento: {e}")
            return None

    def delete_document(self, file_path):
        """Elimina un documento"""
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            return True
        except Exception as e:
            print(f"Errore eliminazione documento: {e}")
            return False

    def create_folder(self, property_id, folder_name, sub_directory=None):
        """Crea una nuova cartella usando l'ID proprietà"""
        folder = self.get_property_folder(property_id, sub_directory)
        new_folder = os.path.join(folder, folder_name)

        try:
            os.makedirs(new_folder, exist_ok=True)
            return new_folder
        except Exception as e:
            print(f"Errore creazione cartella: {e}")
            return None

    def rename_property_folder(self, old_name, property_id):
        """
        🆕 METODO DI MIGRAZIONE
        Rinomina una cartella esistente con nome testuale al nuovo formato con ID.
        Usalo UNA VOLTA per migrare le cartelle esistenti.
        """
        old_path = os.path.join(DOCS_DIR, old_name)
        new_path = os.path.join(DOCS_DIR, f"property_{property_id}")

        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                shutil.move(old_path, new_path)
                print(f"✅ Migrata cartella: {old_name} → property_{property_id}")
                return True
            except Exception as e:
                print(f"❌ Errore migrazione cartella {old_name}: {e}")
                return False
        return False
