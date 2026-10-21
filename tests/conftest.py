"""Configuração comum dos testes.

Precisa ser importado **antes** de ``src.main`` para que o SDL use drivers
nulos — assim os testes rodam em CI e em máquina sem vídeo/som.
"""

from __future__ import annotations

import os

# Driver nulo: nenhum driver de vídeo/som real é aberto durante os testes.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
