# -*- mode: python ; coding: utf-8 -*-
from kivy_deps import sdl2, glew

block_cipher = None

added_files = [
	("D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\kv", "kv"),
	("D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\media", "media" ),
	("D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\sources", "sources" ),
	("D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\settings", "settings")]


a = Analysis(['D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\sources\\FileTransferApp.py'],
             pathex=['D:\\MyPython\\FileTransfer'],
             binaries=[],
             datas=added_files,
             hiddenimports=['win32timezone'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='FileTransfer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='D:\\My Documents\\Informatica\\Python\\Projects\\File Transfer\\FileTransfer\\media\\logos\\icons8-refresh-64.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
			   *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],										  
               strip=False,
               upx=True,
               upx_exclude=[],
               name='FileTransfer')
