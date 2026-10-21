"""Identifica os fontes e confere cada arquivo do executável distribuído."""
from pathlib import Path
import hashlib
import json
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "project.toml").read_text(encoding="utf-8"))["project"]["version"]

def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def source_revision(root=ROOT):
    paths = [root / name for name in ("main.py", "project.toml", "requirements-build-lock.txt", "assets/manifest.json")]
    paths += list((root / "src").rglob("*.py"))
    paths += list((root / "tools").glob("*.py")) + list((root / "tools").glob("*.spec"))
    files = {p.relative_to(root).as_posix(): sha256(p) for p in sorted(paths)}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"version": VERSION, "source_sha256": digest, "files": files}

def runtime_hashes(root=ROOT):
    paths = [root / "SoldadosVsZumbis.exe"] + sorted((root / "_internal").rglob("*"))
    return {p.relative_to(root).as_posix(): sha256(p) for p in paths if p.is_file()}

def verify_build(root=ROOT):
    recorded = json.loads((root / "build-info.json").read_text(encoding="utf-8"))
    if recorded["revision"] != source_revision(root):
        raise ValueError("Código alterado desde a construção. Construa novamente antes de empacotar.")
    if recorded["runtime"] != runtime_hashes(root):
        raise ValueError("Executável ou bibliotecas divergentes. Construa novamente.")
    embedded = json.loads((root / "_internal/revision.json").read_text(encoding="utf-8"))
    if embedded != recorded["revision"]:
        raise ValueError("Identificação interna divergente.")
    return recorded

def write_version_resource(destination):
    numbers = tuple(int(n) for n in VERSION.split(".")) + (0,)
    text = f"""VSVersionInfo(
      ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r},
        mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
      kids=[StringFileInfo([StringTable('041604b0', [
        StringStruct('FileDescription', 'Soldados vs Zumbis'),
        StringStruct('FileVersion', '{VERSION}'),
        StringStruct('ProductName', 'Soldados vs Zumbis'),
        StringStruct('ProductVersion', '{VERSION}'),
        StringStruct('OriginalFilename', 'SoldadosVsZumbis.exe')])]),
        VarFileInfo([VarStruct('Translation', [1046, 1200])])])"""
    destination.write_text(text, encoding="utf-8")
