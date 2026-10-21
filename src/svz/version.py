"""Metadados únicos do projeto, incluídos também no executável."""
from pathlib import Path
import sys
import json
import tomllib

METADATA_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
PROJECT = tomllib.loads((METADATA_ROOT / "project.toml").read_text(encoding="utf-8"))
VERSION = PROJECT["project"]["version"]
try:
    BUILD_INFO = json.loads((METADATA_ROOT / "revision.json").read_text(encoding="utf-8"))
except FileNotFoundError:
    BUILD_INFO = {}

