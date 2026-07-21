import os
import sys
block_cipher = None

# Aggiunge la directory corrente al path di analisi
project_root = os.path.abspath(SPECPATH)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

a = Analysis(
    ['Main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('icons',   'icons'),
        # Seed traduzioni: copiato in BASE_DIR al primo avvio se il sync
        # dal server non è ancora avvenuto (evita UI con chiavi [ETICHETTE.*])
        ('shared/translations.db', 'shared'),
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
        'services.translation_sync_service',
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
        # Codice non-client
        'tests',
        'pytest',
        'license_server',
        'admin_cli',
        # Roba pesante mai usata dal client (riduce dimensione e avvio).
        # NB: NON escludere unittest/doctest/pydoc — matplotlib li importa
        # a runtime e la loro assenza fa crashare l'avvio.
        'tkinter',
        'IPython',
        'jedi',
        # Moduli Qt non usati (l'app usa solo Widgets/Core/Gui)
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtBluetooth',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtWebSockets',
        'PySide6.QtWebChannel',
        'PySide6.QtPositioning',
        'PySide6.QtLocation',
        'PySide6.QtRemoteObjects',
        'PySide6.QtTest',
        'PySide6.QtDesigner',
        'PySide6.QtHelp',
        'PySide6.QtSql',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Splash screen: appare istantaneamente all'avvio mentre Python/Qt caricano.
# Supportato solo su Windows/Linux — su macOS PyInstaller non lo prevede.
splash_target = []
if sys.platform == 'win32':
    splash = Splash(
        'assets/splash.png',
        binaries=a.binaries,
        datas=a.datas,
        text_pos=None,
        always_on_top=True,
    )
    splash_target = [splash, splash.binaries]

exe = EXE(
    pyz,
    a.scripts,
    *( [splash_target[0]] if splash_target else [] ),
    [],
    exclude_binaries=True,
    name='PropertyManager',
    debug=False,
    strip=False,
    # UPX disattivato: la decompressione rallenta l'avvio e causa
    # falsi positivi antivirus (che rallentano ancora di più)
    upx=False,
    console=False,
    icon='assets/app.ico',
)

coll = COLLECT(
    exe,
    *( [splash_target[1]] if splash_target else [] ),
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='PropertyManager',
)
