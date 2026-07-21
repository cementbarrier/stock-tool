# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui\\build\\gui.py'],
    pathex=['E:\\stock-tool', 'E:\\stock-tool\\scripts'],
    binaries=[],
    datas=[('config', 'config'), ('gui\\build\\assets', 'gui\\build\\assets'), ('scripts', 'scripts'), ('backend', 'backend')],
    hiddenimports=['backend', 'backend.single_parser', 'backend.batch_parser', 'backend.config_manager', 'backend.up_manager', 'backend.llm_client', 'backend.notifier', 'backend.parsed_records', 'backend.single_summary_client', 'backend.task_queue_manager', 'backend.time_price_judge', 'backend.valley_scheduler', 'openpyxl', 'pandas', 'requests'],
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
    icon=['gui\\build\\assets\\app_icon.ico'],
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
