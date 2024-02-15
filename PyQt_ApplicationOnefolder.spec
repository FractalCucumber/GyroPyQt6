# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['PyQt_ApplicationClass.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['setuptools', 'PyQt5.QtSvg', 'PyQt5.Qt5Qml', 'PyQt5.Qt5QmlModels',
    'PyQt5.QtOpenGL', 'PyQt5.QtOpenGLWidgets', 'PyQt5.Qt5Quick', 'PyQt5.QtTest',
    'PyQt5.Qt5WebSockets', 'PyQt5.Qt5Network', 'pyqtgraph.opengl',
    'hooks', 'hook', 'flask'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

subfolder = 'res/'
a.datas += [(subfolder + 'StyleSheets.css', subfolder + 'StyleSheets.css', 'DATA'),]
a.datas += [(subfolder + 'StyleSheetsDialog.css', subfolder + 'StyleSheetsDialog.css', 'DATA'),]
a.datas += [(subfolder + 'icon_16.png', subfolder + 'icon_16.png', 'DATA'),]
a.datas += [(subfolder + 'icon_24.png', subfolder + 'icon_24.png', 'DATA'),]
a.datas += [(subfolder + 'icon_32.png', subfolder + 'icon_32.png', 'DATA'),]
a.datas += [(subfolder + 'icon_48.png', subfolder + 'icon_48.png', 'DATA'),]
a.datas += [(subfolder + 'icon.ico', subfolder + 'icon.ico', 'DATA'),]
a.datas += [(subfolder + 'add.png', subfolder + 'add.png', 'DATA'),]
a.datas += [(subfolder + 'edit.png', subfolder + 'edit.png', 'DATA'),]
a.datas += [(subfolder + 'open_folder.png', subfolder + 'open_folder.png', 'DATA'),]
a.datas += [(subfolder + 'open_folder_blue.png', subfolder + 'open_folder_blue.png', 'DATA'),]
a.datas += [(subfolder + 'open_folder_red.png', subfolder + 'open_folder_red.png', 'DATA'),]
a.datas += [(subfolder + 'open_folder_green.png', subfolder + 'open_folder_green.png', 'DATA'),]
a.datas += [(subfolder + 'red.png', subfolder + 'red.png', 'DATA'),]
a.datas += [(subfolder + 'green.png', subfolder + 'green.png', 'DATA'),]
a.datas += [(subfolder + 'blue.png', subfolder + 'blue.png', 'DATA')]
a.datas += [(subfolder + 'load_icon.png', subfolder + 'load_icon.png', 'DATA')]
a.datas += [('settings/config.ini', 'PyQt_ConfigDefault.ini', 'DATA')]
a.datas += [('settings/projects.json', 'settings/projects.json', 'DATA')]
a.datas += [('settings/fft_options.json', 'settings/fft_options.json', 'DATA')]


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GyroVibroTest',
    icon=subfolder + 'icon.ico',
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
    name='GyroVibroTest',
)


import os
print('\nDelete useless dll files:')
print('opengl32sw, Qt5Network, Qt5WebSockets, Qt5Quick, Qt5DBus, Qt5Qml, Qt5QmlModels, Qt5Svg')
path = os.getcwd() + '/dist' + '/GyroVibroTest/'
os.mkdir(path + 'logs')
if os.path.isfile(path + 'opengl32sw.dll'):
    os.remove(path + 'opengl32sw.dll') 
if os.path.isfile(path + 'Qt5Network.dll'):
    os.remove(path + 'Qt5Network.dll')
if os.path.isfile(path + 'Qt5WebSockets.dll'):
    os.remove(path + 'Qt5WebSockets.dll')
if os.path.isfile(path + 'Qt5Quick.dll'):
    os.remove(path + 'Qt5Quick.dll')
if os.path.isfile(path + 'Qt5DBus.dll'):
    os.remove(path + 'Qt5DBus.dll')
if os.path.isfile(path + 'Qt5Qml.dll'):
    os.remove(path + 'Qt5Qml.dll')
if os.path.isfile(path + 'Qt5QmlModels.dll'):
    os.remove(path + 'Qt5QmlModels.dll')
if os.path.isfile(path + 'Qt5Svg.dll'):
    os.remove(path + 'Qt5Svg.dll')
print('Finished!')