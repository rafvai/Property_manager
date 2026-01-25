"""
Gestione connessione database universale
Supporta TUTTI i DB cambiando solo CONNECTION_STRING
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base
import os
from pathlib import Path


class DatabaseConnection:
    """Singleton per gestione connessione DB"""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, logger):
        """Inizializza engine e session factory"""
        if self._engine is not None:
            return  # Già inizializzato

        connection_string = self._get_connection_string()
        logger.info(f"🔗 Connessione DB: {self._sanitize_connection_string(connection_string)}")

        # Crea engine
        self._engine = create_engine(
            connection_string,
            echo=False,  # True per debug SQL
            pool_pre_ping=True,  # Verifica connessione prima di usarla
            pool_recycle=3600  # Ricicla connessioni dopo 1h (importante per cloud)
        )

        # Crea tabelle se non esistono
        Base.metadata.create_all(self._engine)
        logger.info("✅ Tabelle database verificate/create")

        # Session factory thread-safe
        self._session_factory = scoped_session(
            sessionmaker(bind=self._engine, expire_on_commit=False)
        )

    def _get_connection_string(self):
        """
        Ritorna stringa connessione basata su environment

        ESEMPI:
        - SQLite locale: sqlite:///path/to/database.db
        - PostgreSQL: postgresql://user:pass@localhost:5432/dbname
        - MySQL: mysql+pymysql://user:pass@localhost:3306/dbname
        - AWS RDS PostgreSQL: postgresql://user:pass@xxx.rds.amazonaws.com:5432/dbname
        - Azure SQL: mssql+pyodbc://user:pass@server.database.windows.net/dbname?driver=ODBC+Driver+17+for+SQL+Server
        """
        env = os.getenv('APP_ENV', 'development')

        if env == 'development':
            # 🆕 USA DB NELLA DIRECTORY CORRENTE (directory del progetto)
            db_path = Path('property_manager.db').absolute()

            print(f"🔍 Database path: {db_path}")
            print(f"📁 DB esiste? {db_path.exists()}")
            if db_path.exists():
                print(f"📊 Dimensione DB: {db_path.stat().st_size} bytes")
            else:
                print(f"⚠️ DB non trovato, verrà creato nuovo")

            return f'sqlite:///{db_path}'

        elif env == 'production':
            # Desktop production: usa AppData per sicurezza
            if os.name == 'nt':
                base_dir = Path(os.getenv('APPDATA')) / 'PropertyManager'
            else:
                base_dir = Path.home() / '.propertymanager'
            base_dir.mkdir(parents=True, exist_ok=True)

            db_path = base_dir / 'property_manager_prod.db'
            return f'sqlite:///{db_path}'

        elif env == 'saas':
            # Cloud database - legge da variabili ambiente
            db_type = os.getenv('DB_TYPE', 'postgresql')  # postgresql, mysql, mssql
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_pass = os.getenv('DB_PASSWORD')

            if db_type == 'postgresql':
                return f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
            elif db_type == 'mysql':
                return f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
            elif db_type == 'mssql':
                # Azure SQL / SQL Server
                driver = os.getenv('DB_DRIVER', 'ODBC+Driver+17+for+SQL+Server')
                return f'mssql+pyodbc://{db_user}:{db_pass}@{db_host}/{db_name}?driver={driver}'

        # Fallback
        return 'sqlite:///property_manager_fallback.db'

    def _sanitize_connection_string(self, conn_str):
        """Nasconde password nei log"""
        if '://' in conn_str:
            parts = conn_str.split('://')
            if '@' in parts[1]:
                credentials, rest = parts[1].split('@', 1)
                if ':' in credentials:
                    user = credentials.split(':')[0]
                    return f"{parts[0]}://{user}:***@{rest}"
        return conn_str

    def get_session(self):
        """Ritorna sessione database thread-safe"""
        if self._session_factory is None:
            raise RuntimeError("Database non inizializzato! Chiama initialize() prima.")
        return self._session_factory()

    def close_session(self, session):
        """Chiude sessione"""
        if session:
            session.close()

    def shutdown(self):
        """Chiude tutte le connessioni"""
        if self._session_factory:
            self._session_factory.remove()
        if self._engine:
            self._engine.dispose()