# -*- mode: python ; coding: utf-8 -*-

options = [('O','','OPTION')]
block_cipher = None

a = Analysis(
    ['PyQt_ApplicationClass.py'],
    pathex=[],
    binaries=[],
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
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

a.datas += [('res/StyleSheets.css', 'res/StyleSheets.css', 'DATA'),]
a.datas += [('res/StyleSheets2.css', 'res/StyleSheets2.css', 'DATA'),]
a.datas += [('res/icon_16.png', 'res/icon_16.png', 'DATA'),]
a.datas += [('res/icon_24.png', 'res/icon_24.png', 'DATA'),]
a.datas += [('res/icon_32.png', 'res/icon_32.png', 'DATA'),]
a.datas += [('res/icon_48.png', 'res/icon_48.png', 'DATA'),]
a.datas += [('res/icon.ico', 'res/icon.ico', 'DATA'),]
a.datas += [('res/add.png', 'res/add.png', 'DATA'),]
a.datas += [('res/edit.png', 'res/edit.png', 'DATA'),]
a.datas += [('res/open_folder.png', 'res/open_folder.png', 'DATA'),]
a.datas += [('res/open_folder_blue.png', 'res/open_folder_blue.png', 'DATA'),]
a.datas += [('res/open_folder_red.png', 'res/open_folder_red.png', 'DATA'),]
a.datas += [('res/open_folder_green.png', 'res/open_folder_green.png', 'DATA'),]
a.datas += [('res/red.png', 'res/red.png', 'DATA'),]
a.datas += [('res/green.png', 'res/green.png', 'DATA'),]
a.datas += [('res/blue.png', 'res/blue.png', 'DATA')]
a.datas += [('res/G.png', 'res/G.png', 'DATA')]


exe = EXE(
    pyz,
    a.scripts,
    options,
    [],
    exclude_binaries=True,
    name='Gyro_Application',
    icon='res/icon.ico',
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
    name='GyroVibroTest new',
)