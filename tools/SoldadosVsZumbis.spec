from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pytest', 'PIL', 'unittest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='SoldadosVsZumbis', debug=False,
    bootloader_ignore_signals=False, strip=False,
    upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SoldadosVsZumbis')
