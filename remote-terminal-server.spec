# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('/home/float/.local/lib/python3.14/site-packages/flet', 'flet'),
        ('/home/float/桌面/Projects/RemoteTerminal/server/RemoteTerminal.png', '.'),
    ],
    hiddenimports=['PIL', 'paramiko', 'cryptography'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gi', 'gi.repository.Gtk', 'gi.repository.GLib', 'gi.repository.GObject',
             'gi.repository.Gio', 'gi.repository.Gdk', 'gi.repository.Pango',
             'gi.repository.GdkPixbuf', 'gi.repository.Atk', 'gi.repository.cairo',
             'gi.repository.xlib', 'gi.repository.freetype2', 'gi.repository.HarfBuzz',
             'gi.repository.GModule', 'gi.repository.GioUnix', 'gi.repository.GLibUnix',
             'gi._gi', 'gi.overrides'],
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
    name='remote-terminal-server',
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
