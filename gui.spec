# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui\\build\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[('scripts', 'scripts'), ('gui\\build\\assets', 'gui\\build\\assets'), ('config', 'config'), ('backend', 'backend')],
    hiddenimports=['backend.config_manager', 'backend.single_parser', 'backend.batch_parser', 'backend.up_manager', 'pandas', 'openpyxl', 'requests', 'PIL', 'step1_fetch_videos', 'backend.llm_client', 'backend.time_price_judge', 'backend.task_queue_manager', 'backend.valley_scheduler', 'backend.single_summary_client'],
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
