# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['gui_main.py'],
             pathex=[],
             binaries=[],
             datas=[('resources/custom.qss', 'resources'),
                    ('resources/GenSenRounded-M.ttc', 'resources'),
                    ('resources/ceiba.ico', 'resources')],
             hiddenimports=[],
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

import sys
platform = sys.platform if sys.platform != 'darwin' else 'mac'
exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='ceiba-downloader-'+platform,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='resources/ceiba.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='gui_main')
