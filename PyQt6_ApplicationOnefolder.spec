# -*- mode: python ; coding: utf-8 -*-

options = [('O','','OPTION')]
block_cipher = None

a = Analysis(
    ['PyQt6_ApplicationClass.py'],
    pathex=[],
    binaries=[],
    datas=[('StyleSheets.css', '.'), ('icon_16.png', '.'),
    ('icon_24.png', '.'), ('icon_32.png', '.'), ('icon_48.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools', 'PyQt5.QtSvg',
    'PyQt5.QtOpenGL', 'PyQt5.QtTest',
    'pyqtgraph.opengl', 'PyQt5.QtOpenGLWidgets',
    'hooks', 'hook', 'pywintypes', 'flask',
    'opengl32sw.dll'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.datas += [('icon.ico','D:\\Work\\Gyro2023_Git\\icon_48.png','DATA')]
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    options,
    [],
    exclude_binaries=True,
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
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyQt5_App',
)