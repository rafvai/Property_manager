import os
block_cipher = None

# Aggiunge la directory corrente al path di analisi
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

a = Analysis(
    ['Main.py'],
    pathex=['.', os.path.abspath('.')],
    binaries=[],
    datas=[
        ('icons',   'icons'),
        ('shared',  'shared'),
    ],
    hiddenimports=[
        # Moduli root del progetto
        'dialogs',
        'dialogs_import',
        'styles',
        'validation_utils',
        'transaction_types',
        'security_manager',
        'log_manager',
        'config',
        'ui_main',
        'ui_login',
        'ui_register',
        # Services
        'services.auth_service',
        'services.database_service',
        'services.deadline_service',
        'services.document_service',
        'services.export_service',
        'services.import_service',
        'services.preferences_service',
        'services.property_service',
        'services.supplier_service',
        'services.transaction_service',
        'services.translation_system_simple',
        'services.user_preference_service',
        # Database
        'database.connection',
        'database.models',
        # Views
        'views.base_view',
        'views.accounting_view',
        'views.calendar_view',
        'views.dashboard_view',
        'views.documents_view',
        'views.properties_view',
        'views.report_view',
        'views.settings_view',
        'views.suppliers_view',
        'views.translations_admin_view_simple',
        # SQLAlchemy
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.ext.declarative',
        # Reportlab
        'reportlab.graphics',
        'reportlab.platypus',
        # Matplotlib
        'matplotlib.backends.backend_qtagg',
        # Cryptography
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        # Openpyxl
        'openpyxl.styles',
        'openpyxl.utils',
        # Keyring
        'keyring.backends.Windows',
        'keyring.backends.macOS',
    ],
    excludes=[
        'tests',
        'pytest',
        'license_server',
        'admin_cli',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PropertyManager',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='icons/homepage.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='PropertyManager',
)
