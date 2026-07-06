# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all

# 自动收集 flet 所有数据
datas = collect_data_files('flet', include_py_files=True)
binaries = collect_dynamic_libs('flet')

# 收集 flet_desktop（桌面客户端，避免运行时下载）
try:
    fld_datas, fld_binaries, fld_imports = collect_all('flet_desktop')
    datas += fld_datas
    binaries += fld_binaries
except ImportError:
    fld_imports = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'paramiko',
        'cryptography',
        'bcrypt',
        'pynacl',
        'invoke',
        'flet',
        'flet.controls',
        'flet.core',
        'flet.connection',
        'flet_desktop',
        'winsdk',
        'asyncio',
    ] + fld_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
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
    icon=['app.ico'],
)