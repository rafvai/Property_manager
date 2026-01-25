from database.connection import DatabaseConnection


class DatabaseService:
    """Wrapper per inizializzazione database"""

    def __init__(self, logger):
        self.logger = logger
        self.db_connection = DatabaseConnection()

    def initialize(self):
        """Inizializza connessione e crea tabelle"""
        try:
            self.db_connection.initialize(self.logger)
            return self.db_connection
        except Exception as e:
            self.logger.error(f"Errore inizializzazione DB: {e}")
            raise

    def close(self):
        """Chiude tutte le connessioni"""
        self.db_connection.shutdown()