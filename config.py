import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configurazione ambiente-agnostica"""

    # Determina ambiente
    ENV = os.getenv('APP_ENV', 'development')  # development | production | saas

    # Directory base
    if ENV == 'saas':
        # SaaS: dati su cloud, niente locale (tranne logs temporanei)
        BASE_DIR = None
        DOCS_DIR = None  # Documenti su S3/Azure Blob
        EXPORTS_DIR = None  # Export temporanei
        LOGS_DIR = Path('/tmp/propertymanager/logs') if os.name != 'nt' else Path(
            os.getenv('TEMP')) / 'propertymanager' / 'logs'
    else:
        # Desktop: usa AppData (Windows) o equivalente
        if os.name == 'nt':  # Windows
            BASE_DIR = Path(os.getenv('APPDATA')) / 'PropertyManager'
        else:  # Linux/Mac
            BASE_DIR = Path.home() / '.propertymanager'

        BASE_DIR.mkdir(parents=True, exist_ok=True)

        #DOCS_DIR = BASE_DIR / 'docs'
        #EXPORTS_DIR = BASE_DIR / 'exports'
        #LOGS_DIR = BASE_DIR / 'logs'
        # todo commentare quando si deciderà cartella
        DOCS_DIR = Path('docs').absolute()
        EXPORTS_DIR = Path('exports').absolute()
        LOGS_DIR = Path('logs').absolute()

        # Crea directories
        for dir_path in [DOCS_DIR, EXPORTS_DIR, LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    # Database configuration
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Ritorna configurazione DB basata su ambiente"""

        if Config.ENV in ['development', 'production']:
            # Desktop: SQLite
            db_name = 'property_manager.db' if Config.ENV == 'development' else 'property_manager_prod.db'
            return {
                'type': 'sqlite',
                'path': str(Config.BASE_DIR / db_name)
            }

        elif Config.ENV == 'saas':
            # SaaS: Database cloud (PostgreSQL, MySQL, etc.)
            db_type = os.getenv('DB_TYPE', 'postgresql')

            return {
                'type': db_type,
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
            }
