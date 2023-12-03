# -*- mode: python ; coding: utf-8 -*-

options = [('O','','OPTION')]

a = Analysis(
    ['PyQt6_Application.py'],
    pathex=[],
    binaries=[],
    datas=[('StyleSheets.css', '.'), ('icon_16.png', '.'), ('icon_24.png', '.'), ('icon_32.png', '.'), ('icon_48.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools', 'PyQt5.QtSvg', 'PyQt5.QtOpenGL', 'PyQt5.QtTest', 'pyqtgraph.opengl', 'PyQt5.QtOpenGLWidgets', 'hooks', 'hook', 'pywintypes', 'flask', 'opengl32sw.dll'],
    noarchive=False,
)
a.datas += [('icon.ico','D:\\Work\\Gyro2023_Git\\icon_48.png','DATA')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    options,
    a.binaries,
    a.datas,
    [],
    name='Gyro_Application',
    icon='D:\\Work\\Gyro2023_Git\\icon.ico',
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
)