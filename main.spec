# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all

# 收集 flet 所有资源
flet_datas, flet_binaries, flet_imports = collect_all('flet')
datas = flet_datas
binaries = flet_binaries
hiddenimports = flet_imports

if sys.platform == 'win32':
    datas += [('data/flet-windows.zip', 'flet_desktop/app')]

hiddenimports += [
    'netifaces',
    'paramiko',
    'cryptography',
    'bcrypt',
    'nacl',
    'asyncio',
    'pyautogui',
    'requests',
    'hydroApp',
]
if sys.platform == 'win32':
    hiddenimports.append('winsdk')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'pydoc'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico' if sys.platform == 'win32' else ('RemoteTerminal.icns' if sys.platform == 'darwin' else None),
)
