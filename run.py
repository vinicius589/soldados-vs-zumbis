#!/usr/bin/env python3
"""Ponto de entrada para executar Soldados vs Zumbis a partir da raiz do repositório.

Uso:
    python run.py

Equivalente a ``python -m src.main``, mas não exige que o usuário conheça
a estrutura interna de pacotes.
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto está no sys.path para que os imports
# absolutos do pacote ``src`` funcionem independentemente de onde o
# usuário chama o script.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.main import main

if __name__ == "__main__":
    main()
