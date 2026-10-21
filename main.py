"""Entrada para o código-fonte e para o executável Windows."""
from pathlib import Path
import sys

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from svz.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
