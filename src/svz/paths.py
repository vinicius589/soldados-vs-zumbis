"""Caminhos independentes do diretório de abertura; saves fora dos recursos."""
from pathlib import Path
import os
import sys

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / 'assets'


def data_dir() -> Path:
    override = os.environ.get('SVZ_DATA_DIR')
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    return base / 'SoldadosVsZumbis'


def save_path() -> Path:
    override = os.environ.get('SVZ_SAVE_PATH')
    return Path(override).expanduser().resolve() if override else data_dir() / 'campanha.json'
