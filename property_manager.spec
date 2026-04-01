block_cipher = None

a = Analysis(
    ['Main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('icons',               'icons'),
        ('shared',              'shared'),
        ('dialogs.py',          '.'),
        ('dialogs_import.py',   '.'),
        ('styles.py',           '.'),
        ('validation_utils.py', '.'),
        ('transaction_types.py','.'),
        ('security_manager.py', '.'),
        ('log_manager.py',      '.'),
        ('config.py',           '.'),
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.ext.declarative',
        'reportlab.graphics',
        'reportlab.platypus',
        'matplotlib.backends.backend_qtagg',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'openpyxl.styles',
        'openpyxl.utils',
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