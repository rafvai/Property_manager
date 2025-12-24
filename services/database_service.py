import sqlite3

DB_NAME = "property_manager.db"


class DatabaseService:
    """Gestisce la connessione al database"""

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.conn = None

    def connect(self):
        """Crea connessione al database"""
        self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def initialize(self):
        """Inizializza le tabelle del database"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        # Tabella proprietà
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            owner TEXT NOT NULL
        )
        """)

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

        self.conn.commit()
        return self.conn

    def close(self):
        """Chiude la connessione"""
        if self.conn:
            self.conn.close()
