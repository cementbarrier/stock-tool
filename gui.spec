# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\stock-tool\\gui\\build\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[('backend', 'backend'), ('scripts', 'scripts')],
    hiddenimports=['step1_fetch_videos', 'step2_download_audio', 'step3_transcribe', 'step4_extract_stocks', 'step5_analyze', 'backend.config_manager', 'backend.llm_client', 'backend.single_parser', 'backend.batch_parser', 'backend.up_manager', 'backend.single_summary_client', 'backend.task_queue_manager', 'backend.time_price_judge', 'backend.valley_scheduler'],
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
