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

    def get_property_folder(self, property_name, sub_directory=None):
        """Ottiene il percorso della cartella di una proprietà"""
        base_path = os.path.join(DOCS_DIR, property_name)
        if sub_directory:
            return os.path.join(base_path, sub_directory)
        return base_path

    def list_documents(self, property_name, sub_directory=None):
        """Lista i documenti di una proprietà"""
        folder = self.get_property_folder(property_name, sub_directory)

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

    def save_document(self, source_path, property_name, sub_directory=None):
        """Salva un documento nella cartella della proprietà"""
        folder = self.get_property_folder(property_name, sub_directory)
        os.makedirs(folder, exist_ok=True)

        filename = os.path.basename(source_path)
        dest_path = os.path.join(folder, filename)

        try:
            shutil.copy(source_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"Errore salvataggio documento: {e}")
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

    def create_folder(self, property_name, folder_name, sub_directory=None):
        """Crea una nuova cartella"""
        folder = self.get_property_folder(property_name, sub_directory)
        new_folder = os.path.join(folder, folder_name)

        try:
            os.makedirs(new_folder, exist_ok=True)
            return new_folder
        except Exception as e:
            print(f"Errore creazione cartella: {e}")
            return None