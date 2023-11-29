# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.building.datastruct import TOC, Tree
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import EXE, PYZ, COLLECT, PKG, MERGE

a = Analysis(
    ['PyQt6_Application.py'],
    pathex=[],
    binaries=[],
    datas=[('StyleSheets.css', '.'), ('icon_16.png', '.'), ('icon_24.png', '.'), ('icon_32.png', '.'), ('icon_48.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'setuptools', 'DateTime', 'pandas', 'PyQt6.QtOpenGL', 'PyQt6.QtTest', 
    'pyqtgraph.opengl', 'PyQt6.QtOpenGLWidgets', 'hook', 'pywintypes', 'flask', 'opengl32sw.dll'],
    noarchive=False,
)
a.binaries -= TOC([
    ('opengl32sw.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Network.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Test.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Pdf.dll', None, None)
])
a.datas += [('icon.ico','D:\\Gyro2023_Git\\icon_48.png','DATA')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Gyro_Application',
    icon='D:\\Gyro2023_Git\\icon.ico',
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
a.binaries -= TOC([
    ('opengl32sw.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Network.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Test.dll', None, None)
])
a.binaries -= TOC([
    ('Qt6Pdf.dll', None, None)
])