# -*- mode: python ; coding: utf-8 -*-

# Empaquetamos el ffmpeg de imageio-ffmpeg (trae libx264) para comprimir videos a <=16 MB.
import imageio_ffmpeg as _iio
_ffmpeg_bin = _iio.get_ffmpeg_exe()

a = Analysis(
    ['interfaz.py'],
    pathex=[],
    binaries=[(_ffmpeg_bin, 'imageio_ffmpeg/binaries')],
    datas=[('Imagenes', 'Imagenes'), ('credenciales.json', '.')],
    hiddenimports=['pandas', 'gspread', 'oauth2client', 'google_auth_oauthlib', 'PIL', 'openpyxl', 'imageio_ffmpeg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Gestor de Mensajes Difusion',
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
    icon=['Imagenes\\logo.ico'],
)
