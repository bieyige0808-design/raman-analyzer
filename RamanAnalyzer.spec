from PyInstaller.utils.hooks import collect_submodules


hidden_imports = ["chart_textbox"] + collect_submodules("lmfit")

a = Analysis(
    ["raman_gui.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/raman-analyzer.ico", "assets"),
        ("assets/raman-analyzer-icon.png", "assets"),
    ],
    hiddenimports=hidden_imports,
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
    [],
    exclude_binaries=True,
    name="RamanAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/raman-analyzer.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RamanAnalyzer",
)
