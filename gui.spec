# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# 自动收集 backend 包的所有子模块
backend_hidden = collect_submodules('backend')
# 自动收集 gui 包（含 gui.build.pages 下的拆分模块）
gui_hidden = collect_submodules('gui')

a = Analysis(
    ['gui\\build\\gui.py'],
    pathex=['.', 'scripts'],
    binaries=[],
    datas=[('scripts', 'scripts')],
    hiddenimports=backend_hidden + gui_hidden + [
        # gui/build/pages 下的拆分模块（绝对导入，需确保被收集）
        'gui.build.utils',
        'gui.build.pages',
        'gui.build.pages.page_parse',
        'gui.build.pages.page_batch',
        'gui.build.pages.page_config',
        'gui.build.pages.tray',
        # scripts/ 下的独立模块（不在包内，需手动声明）
        'step1_fetch_videos',
        'step2_download_audio',
        'step3_transcribe',
        'step4_extract_stocks',
        'step5_analyze',
        'run_pipeline',
        # pystray 托盘
        'pystray',
        'pystray._win32',
        'pystray._base',
        'pystray._util',
        'pystray._util.win32',
        'six',
        'six.moves.queue',
        'PIL.Image',
        'PIL.ImageDraw',
        # 第三方依赖（script 中用到但可能未被自动追踪）
        'requests',
        'json',
        're',
        'datetime',
        'subprocess',
        'shutil',
        'threading',
        'queue',
        'time',
        'sys',
        'os',
        'pathlib',
        'collections',
        'typing',
        'traceback',
        'argparse',
        'logging',
        'hashlib',
        'urllib',
        'urllib.parse',
        'csv',
        'io',
        'math',
        'functools',
        'itertools',
    ],
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
    name='gui',
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
