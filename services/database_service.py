import sqlite3

TESTING = True
# TESTING = False

if TESTING:
    DB_NAME = "property_manager.db"
else:
    DB_NAME = "property_manager_official.db"


class DatabaseService:
    """Gestisce la connessione al database"""

    def __init__(self, logger, db_name=DB_NAME):
        self.db_name = db_name
        self.conn = None
        self.logger = logger

    def connect(self):
        """Crea connessione al database"""
        try:
            self.conn = sqlite3.connect(self.db_name)
        except Exception as e:
            self.logger.error(f"Connessione al DB: {e}")
            self.conn = None
        return self.conn

    def initialize(self):
        """Inizializza le tabelle del database"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        # Tabella proprietà
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                owner TEXT NOT NULL
            )
            """)
            self.logger.info("Tabella proprieta creata correttamente")
        except Exception as e:
            self.logger.error(f"Creazione Tabella proprieta: {e}")
        else:
            try:
                # Tabella transazioni
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    type TEXT CHECK(type IN ('Entrata','Uscita')) NOT NULL,
                    amount REAL NOT NULL,
                    provider TEXT NOT NULL,
                    service TEXT NOT NULL,
                    FOREIGN KEY (property_id) REFERENCES properties(id)
                )
                """)
                self.logger.info("Tabella transazioni creata correttamente")
            except Exception as e:
                self.logger.error(f"Creazione Tabella transazioni: {e}")
            else:
                try:
                    # Tabella scadenze
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS deadlines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        property_id INTEGER,
                        title TEXT NOT NULL,
                        description TEXT,
                        due_date TEXT NOT NULL,
                        completed INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (property_id) REFERENCES properties(id)
                    )
                    """)
                    self.logger.info("Tabella scadenze creata correttamente")
                except Exception as e:
                    self.logger.error(f"Creazione Tabella scadenze: {e}")
                else:
                    self.conn.commit()
                    return self.conn

    def close(self):
        """Chiude la connessione"""
        if self.conn:
            self.conn.close()
