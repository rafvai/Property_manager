# ============================================
# SISTEMA TRADUZIONI SEMPLIFICATO CON CACHE
# Database separato: id, category, key, it, en, es
# ============================================

import sqlite3
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, List


# ============================================
# 1. DATABASE SCHEMA
# ============================================

TRANSLATIONS_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    it TEXT,
    en TEXT,
    es TEXT,
    UNIQUE(category, key)
);

CREATE INDEX IF NOT EXISTS idx_category ON translations(category);
CREATE INDEX IF NOT EXISTS idx_key ON translations(key);
"""


# ============================================
# 2. TRANSLATION DATABASE
# ============================================

class TranslationDatabase:
    """Gestisce il database SQLite delle traduzioni"""
    
    def __init__(self, db_path='shared/translations.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Inizializza database se non esiste"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(TRANSLATIONS_DB_SCHEMA)
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Ottiene connessione al DB"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Accesso per nome colonna
        return conn
    
    def get_all(self) -> List[Dict]:
        """Recupera tutte le traduzioni"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM translations ORDER BY category, key")
        
        translations = []
        for row in cursor.fetchall():
            translations.append({
                'id': row['id'],
                'category': row['category'],
                'key': row['key'],
                'it': row['it'],
                'en': row['en'],
                'es': row['es']
            })
        
        conn.close()
        return translations
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Recupera traduzioni per categoria"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM translations WHERE category = ? ORDER BY key",
            (category,)
        )
        
        translations = []
        for row in cursor.fetchall():
            translations.append({
                'id': row['id'],
                'category': row['category'],
                'key': row['key'],
                'it': row['it'],
                'en': row['en'],
                'es': row['es']
            })
        
        conn.close()
        return translations
    
    def get_translation(self, category: str, key: str) -> Optional[Dict]:
        """Recupera singola traduzione"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM translations WHERE category = ? AND key = ?",
            (category, key)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'category': row['category'],
                'key': row['key'],
                'it': row['it'],
                'en': row['en'],
                'es': row['es']
            }
        return None
    
    def set_translation(self, category: str, key: str, it: str = None, 
                       en: str = None, es: str = None) -> bool:
        """Imposta/aggiorna traduzione"""
        conn = self.get_connection()
        
        try:
            conn.execute("""
                INSERT INTO translations (category, key, it, en, es)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category, key) 
                DO UPDATE SET it = ?, en = ?, es = ?
            """, (category, key, it, en, es, it, en, es))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error setting translation: {e}")
            return False
        finally:
            conn.close()
    
    def delete_translation(self, category: str, key: str) -> bool:
        """Elimina traduzione"""
        conn = self.get_connection()
        
        try:
            conn.execute(
                "DELETE FROM translations WHERE category = ? AND key = ?",
                (category, key)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting translation: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_categories(self) -> List[str]:
        """Ottiene lista categorie"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT DISTINCT category FROM translations ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def search(self, search_term: str) -> List[Dict]:
        """Cerca traduzioni per termine"""
        conn = self.get_connection()
        cursor = conn.execute("""
            SELECT * FROM translations 
            WHERE category LIKE ? OR key LIKE ? OR it LIKE ? OR en LIKE ? OR es LIKE ?
            ORDER BY category, key
        """, (f'%{search_term}%',) * 5)
        
        translations = []
        for row in cursor.fetchall():
            translations.append({
                'id': row['id'],
                'category': row['category'],
                'key': row['key'],
                'it': row['it'],
                'en': row['en'],
                'es': row['es']
            })
        
        conn.close()
        return translations
    
    def get_statistics(self) -> Dict:
        """Statistiche database"""
        conn = self.get_connection()
        
        # Totale traduzioni
        cursor = conn.execute("SELECT COUNT(*) as total FROM translations")
        total = cursor.fetchone()['total']
        
        # Per categoria
        cursor = conn.execute("""
            SELECT category, COUNT(*) as count 
            FROM translations 
            GROUP BY category 
            ORDER BY count DESC
        """)
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Traduzioni mancanti
        cursor = conn.execute("""
            SELECT 
                SUM(CASE WHEN it IS NULL OR it = '' THEN 1 ELSE 0 END) as missing_it,
                SUM(CASE WHEN en IS NULL OR en = '' THEN 1 ELSE 0 END) as missing_en,
                SUM(CASE WHEN es IS NULL OR es = '' THEN 1 ELSE 0 END) as missing_es
            FROM translations
        """)
        missing = cursor.fetchone()
        
        conn.close()
        
        return {
            'total': total,
            'by_category': by_category,
            'missing': {
                'it': missing['missing_it'],
                'en': missing['missing_en'],
                'es': missing['missing_es']
            }
        }


# ============================================
# 3. TRANSLATION MANAGER CON CACHE
# ============================================

class TranslationManager:
    """
    Gestione traduzioni con cache in-memory per performance ottimali.
    Thread-safe per uso in ambiente multi-tenant.
    """
    
    def __init__(self, db_path='shared/translations.db', default_language='it'):
        self.db = TranslationDatabase(db_path)
        self.current_language = default_language
        self._cache = {}  # {category: {key: {it: "", en: "", es: ""}}}
        self._cache_lock = Lock()
        self._load_cache()
    
    def _load_cache(self):
        """Carica tutte le traduzioni in cache"""
        with self._cache_lock:
            self._cache = {}
            
            translations = self.db.get_all()
            for t in translations:
                if t['category'] not in self._cache:
                    self._cache[t['category']] = {}
                
                self._cache[t['category']][t['key']] = {
                    'it': t['it'],
                    'en': t['en'],
                    'es': t['es']
                }
    
    def get(self, category: str, key: str, language: str = None, fallback: str = None) -> str:
        """
        Recupera traduzione con fallback automatico.
        
        Args:
            category: Categoria (es: 'ETICHETTE', 'PULSANTI')
            key: Chiave (es: 'FORNITORE', 'AGGIUNGI')
            language: Lingua specifica (None = usa corrente)
            fallback: Valore di fallback se non trovato
        
        Returns:
            Traduzione o fallback o placeholder
        
        Usage:
            tm.get('ETICHETTE', 'FORNITORE')  # "Fornitore" (IT)
            tm.get('PULSANTI', 'AGGIUNGI', language='en')  # "Add"
        """
        lang = language or self.current_language
        
        try:
            translation = self._cache[category][key][lang]
            
            # Se traduzione è None o vuota, usa fallback a IT
            if not translation and lang != 'it':
                translation = self._cache[category][key]['it']
            
            return translation or fallback or f"[{category}.{key}]"
            
        except KeyError:
            # Cache miss: prova a recuperare dal DB e aggiorna cache
            db_trans = self.db.get_translation(category, key)
            
            if db_trans:
                # Aggiorna cache
                with self._cache_lock:
                    if category not in self._cache:
                        self._cache[category] = {}
                    self._cache[category][key] = {
                        'it': db_trans['it'],
                        'en': db_trans['en'],
                        'es': db_trans['es']
                    }
                
                # Ritorna traduzione
                translation = db_trans[lang]
                if not translation and lang != 'it':
                    translation = db_trans['it']
                
                return translation or fallback or f"[{category}.{key}]"
            
            # Non trovato nemmeno nel DB
            return fallback or f"[{category}.{key}]"
    
    def __getitem__(self, category: str):
        """
        Supporto sintassi dizionario.
        
        Usage:
            tm['ETICHETTE']['FORNITORE']  # "Fornitore"
        """
        class CategoryProxy:
            def __init__(self, manager, category):
                self.manager = manager
                self.category = category
            
            def __getitem__(self, key):
                return self.manager.get(self.category, key)
        
        return CategoryProxy(self, category)
    
    def set_language(self, language: str):
        """Cambia lingua corrente"""
        if language in ['it', 'en', 'es']:
            self.current_language = language
        else:
            raise ValueError(f"Lingua non supportata: {language}")
    
    def get_current_language(self) -> str:
        """Ritorna lingua corrente"""
        return self.current_language
    
    def get_available_languages(self) -> List[str]:
        """Ritorna lingue disponibili"""
        return ['it', 'en', 'es']
    
    def reload(self):
        """Ricarica cache dal database"""
        self._load_cache()
    
    def add_translation(self, category: str, key: str, it: str = None, 
                       en: str = None, es: str = None) -> bool:
        """Aggiunge/aggiorna traduzione"""
        success = self.db.set_translation(category, key, it, en, es)
        if success:
            self.reload()
        return success
    
    def delete_translation(self, category: str, key: str) -> bool:
        """Elimina traduzione"""
        success = self.db.delete_translation(category, key)
        if success:
            self.reload()
        return success
    
    def get_statistics(self) -> Dict:
        """Statistiche traduzioni"""
        return self.db.get_statistics()


# ============================================
# 4. SEEDER - POPOLAMENTO INIZIALE
# ============================================

def seed_translations_db(db_path='shared/translations.db'):
    """Popola database con traduzioni iniziali"""
    
    db = TranslationDatabase(db_path)
    
    # Traduzioni base
    base_translations = [
        # ETICHETTE
        ('ETICHETTE', 'FORNITORE', 'Fornitore', 'Supplier', 'Proveedor'),
        ('ETICHETTE', 'FORNITORI', 'Fornitori', 'Suppliers', 'Proveedores'),
        ('ETICHETTE', 'PROPRIETÀ', 'Proprietà', 'Property', 'Propiedad'),
        ('ETICHETTE', 'NUOVA_PROPRIETÀ', 'Nuova Proprietà', 'New Property', 'Nueva Propiedad'),
        ('ETICHETTE', 'TRANSAZIONE', 'Transazione', 'Transaction', 'Transacción'),
        ('ETICHETTE', 'TRANSAZIONI', 'Transazioni', 'Transactions', 'Transacciones'),
        ('ETICHETTE', 'CATEGORIA', 'Categoria', 'Category', 'Categoría'),
        ('ETICHETTE', 'NOME', 'Nome', 'Name', 'Nombre'),
        ('ETICHETTE', 'TELEFONO', 'Telefono', 'Phone', 'Teléfono'),
        ('ETICHETTE', 'EMAIL', 'Email', 'Email', 'Email'),
        ('ETICHETTE', 'INDIRIZZO', 'Indirizzo', 'Address', 'Dirección'),
        ('ETICHETTE', 'NOTE', 'Note', 'Notes', 'Notas'),
        ('ETICHETTE', 'VALUTAZIONE', 'Valutazione', 'Rating', 'Calificación'),
        ('ETICHETTE', 'DATA', 'Data', 'Date', 'Fecha'),
        ('ETICHETTE', 'IMPORTO', 'Importo', 'Amount', 'Importe'),
        ('ETICHETTE', 'TIPO', 'Tipo', 'Type', 'Tipo'),
        ('ETICHETTE', 'STATO', 'Stato', 'Status', 'Estado'),
        
        # PULSANTI
        ('PULSANTI', 'AGGIUNGI', 'Aggiungi', 'Add', 'Añadir'),
        ('PULSANTI', 'MODIFICA', 'Modifica', 'Edit', 'Editar'),
        ('PULSANTI', 'ELIMINA', 'Elimina', 'Delete', 'Eliminar'),
        ('PULSANTI', 'SALVA', 'Salva', 'Save', 'Guardar'),
        ('PULSANTI', 'ANNULLA', 'Annulla', 'Cancel', 'Cancelar'),
        ('PULSANTI', 'CHIUDI', 'Chiudi', 'Close', 'Cerrar'),
        ('PULSANTI', 'CERCA', 'Cerca', 'Search', 'Buscar'),
        ('PULSANTI', 'FILTRA', 'Filtra', 'Filter', 'Filtrar'),
        ('PULSANTI', 'ESPORTA', 'Esporta', 'Export', 'Exportar'),
        ('PULSANTI', 'IMPORTA', 'Importa', 'Import', 'Importar'),
        ('PULSANTI', 'CONFERMA', 'Conferma', 'Confirm', 'Confirmar'),
        
        # MESSAGGI
        ('MESSAGGI', 'SUCCESSO', 'Operazione completata con successo!', 'Operation completed successfully!', '¡Operación completada con éxito!'),
        ('MESSAGGI', 'ERRORE', 'Si è verificato un errore.', 'An error occurred.', 'Se produjo un error.'),
        ('MESSAGGI', 'CONFERMA_ELIMINA', 'Sei sicuro di voler eliminare?', 'Are you sure you want to delete?', '¿Estás seguro de que quieres eliminar?'),
        ('MESSAGGI', 'NESSUN_DATO', 'Nessun dato disponibile', 'No data available', 'No hay datos disponibles'),
        ('MESSAGGI', 'CARICAMENTO', 'Caricamento...', 'Loading...', 'Cargando...'),
        ('MESSAGGI', 'SALVATO', 'Salvato con successo!', 'Saved successfully!', '¡Guardado con éxito!'),
        ('MESSAGGI', 'ELIMINATO', 'Eliminato con successo!', 'Deleted successfully!', '¡Eliminado con éxito!'),
        
        # PLACEHOLDER
        ('PLACEHOLDER', 'CERCA', 'Cerca...', 'Search...', 'Buscar...'),
        ('PLACEHOLDER', 'INSERISCI_NOME', 'Inserisci nome', 'Enter name', 'Introducir nombre'),
        ('PLACEHOLDER', 'SELEZIONA', 'Seleziona...', 'Select...', 'Seleccionar...'),
        ('PLACEHOLDER', 'INSERISCI_EMAIL', 'Inserisci email', 'Enter email', 'Introducir email'),
        
        # MENU
        ('MENU', 'DASHBOARD', 'Dashboard', 'Dashboard', 'Panel'),
        ('MENU', 'PROPRIETÀ', 'Proprietà', 'Properties', 'Propiedades'),
        ('MENU', 'TRANSAZIONI', 'Transazioni', 'Transactions', 'Transacciones'),
        ('MENU', 'FORNITORI', 'Fornitori', 'Suppliers', 'Proveedores'),
        ('MENU', 'REPORT', 'Report', 'Reports', 'Informes'),
        ('MENU', 'IMPOSTAZIONI', 'Impostazioni', 'Settings', 'Configuración'),
        ('MENU', 'TRADUZIONI', 'Traduzioni', 'Translations', 'Traducciones'),
        
        # VALIDAZIONE
        ('VALIDAZIONE', 'CAMPO_OBBLIGATORIO', 'Campo obbligatorio', 'Required field', 'Campo obligatorio'),
        ('VALIDAZIONE', 'EMAIL_NON_VALIDA', 'Email non valida', 'Invalid email', 'Email no válido'),
        ('VALIDAZIONE', 'IMPORTO_NON_VALIDO', 'Importo non valido', 'Invalid amount', 'Importe no válido'),
        ('VALIDAZIONE', 'DATA_NON_VALIDA', 'Data non valida', 'Invalid date', 'Fecha no válida'),
    ]
    
    count = 0
    for category, key, it, en, es in base_translations:
        if db.set_translation(category, key, it, en, es):
            count += 1
    
    print(f"✅ Database popolato con {count} traduzioni")
    return count


# ============================================
# 5. ESEMPIO UTILIZZO
# ============================================

if __name__ == "__main__":
    # Inizializza e popola database
    print("🌐 Inizializzazione sistema traduzioni...")
    seed_translations_db()
    
    # Crea manager
    tm = TranslationManager(default_language='it')
    
    # Esempi uso
    print("\n📝 Esempi utilizzo:")
    
    # Metodo 1: get()
    print(f"Fornitore (IT): {tm.get('ETICHETTE', 'FORNITORE')}")
    print(f"Aggiungi (IT): {tm.get('PULSANTI', 'AGGIUNGI')}")
    
    # Metodo 2: dizionario
    print(f"Proprietà (IT): {tm['ETICHETTE']['PROPRIETÀ']}")
    print(f"Salva (IT): {tm['PULSANTI']['SALVA']}")
    
    # Metodo 3: lingua specifica
    print(f"Fornitore (EN): {tm.get('ETICHETTE', 'FORNITORE', language='en')}")
    print(f"Fornitore (ES): {tm.get('ETICHETTE', 'FORNITORE', language='es')}")
    
    # Cambio lingua
    tm.set_language('en')
    print(f"\n🇬🇧 English:")
    print(f"Supplier: {tm.get('ETICHETTE', 'FORNITORE')}")
    print(f"Add: {tm.get('PULSANTI', 'AGGIUNGI')}")
    
    tm.set_language('es')
    print(f"\n🇪🇸 Español:")
    print(f"Proveedor: {tm.get('ETICHETTE', 'FORNITORE')}")
    print(f"Añadir: {tm.get('PULSANTI', 'AGGIUNGI')}")
    
    # Statistiche
    stats = tm.get_statistics()
    print(f"\n📊 Statistiche:")
    print(f"Totale: {stats['total']}")
    print(f"Per categoria: {stats['by_category']}")
    print(f"Traduzioni mancanti: {stats['missing']}")
