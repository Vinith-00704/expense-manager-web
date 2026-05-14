# desktop_app.spec
# Build a standalone .exe with: pyinstaller desktop_app.spec
# Install pyinstaller first: .venv\Scripts\pip install pyinstaller

import os
from pathlib import Path

BASE = Path(os.path.abspath(SPECPATH))
SRC  = BASE

block_cipher = None

a = Analysis(
    [str(SRC / 'desktop_app.py')],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # Include the entire frontend folder
        (str(SRC / 'frontend'), 'frontend'),
        # Include .env (optional — remove if you don't want secrets in .exe)
        # (str(SRC / '.env'), '.'),
    ],
    hiddenimports=[
        'app',
        'app.routes.auth',
        'app.routes.expenses',
        'app.routes.dashboard',
        'app.routes.subscriptions',
        'app.routes.rooms',
        'app.routes.trips',
        'app.routes.analytics',
        'app.routes.reports',
        'app.routes.settings',
        'app.routes.imports',
        'app.routes.sms_sync',
        'app.routes.devices',
        'app.routes.goals',
        'app.routes.budgets',
        'app.routes.ocr',
        'pymysql',
        'pdfplumber',
        'openpyxl',
        'pandas',
        'webview',
        'webview.platforms.winforms',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FinanceOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # No terminal window
    icon=None,           # Add: icon='frontend/icons/icon-192.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FinanceOS',
)
