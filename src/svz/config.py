"""Dimensões, cores e caminhos da versão ativa."""
from __future__ import annotations

from pathlib import Path
import os
import pygame



from .paths import ROOT, ASSET_ROOT, save_path

ASSET_DIR = ASSET_ROOT / "interface"
PRODUCTION_ASSET_DIR = ASSET_ROOT / "actors"
AUDIO_DIR = ASSET_ROOT / "audio"
SAVE_PATH = save_path()
WIDTH, HEIGHT = 1280, 720
FPS = 60
from .version import VERSION
TOTAL_WAVES = 12
CARD_RECHARGE_SECONDS = 10.0
ROWS, COLS = 4, 9
# A arte comporta a contenção inicial e seis casas de tropa. As colunas 7 e 8
# coincidiam com o fim pintado da pista e com a boca de entrada dos zumbis;
# elas deixam de existir para clique, teclado, ocupação e footprint.
LAST_PLACEABLE_COLUMN = 6
# Limite horizontal comum e extensão vertical total das três arenas. As
# faixas não usam uma grade vertical genérica: cada cenário possui limites
# calibrados a partir das pistas realmente pintadas na arte.
BOARD = pygame.Rect(164, 170, 1090, 540)
CELL_W = BOARD.width / COLS
CELL_H = BOARD.height / ROWS
LANE_BOUNDS: dict[str, tuple[int, int, int, int, int]] = {
    # Limites medidos diretamente nas três artes finais. A posição lógica não
    # tenta mais encaixar uma grade genérica sobre pistas desenhadas em alturas
    # diferentes; por isso soldados, zumbis e contenções compartilham o mesmo
    # chão visível em cada região.
    "city": (239, 326, 428, 514, 619),
    "desert": (226, 316, 410, 503, 604),
    "beach": (207, 285, 383, 480, 585),
}
BEACH_WATER_ROWS = frozenset({1, 2})
BEACH_WATER_DEFENDERS = frozenset({"lancha", "submarino", "barco_patrulha", "submarino_tatico"})
LANE_BOMB_HOME_X = 215
# A contenção inicial ocupa a primeira casa de cada faixa. Manter a coluna
# explícita evita depender de uma função declarada mais abaixo no módulo.
LANE_PROTECTION_COLUMN = 0
LANE_PROTECTION_END_X = {
    "city": 1082,
    "desert": 1040,
    "beach": 1088,
}
# Ponto visual dentro de cada entrada da direita. O primeiro quadro nasce
# encoberto pela passagem e ganha opacidade enquanto avança para a pista.
ENEMY_ENTRY_X = {
    "city": 1182.0,
    "desert": 1168.0,
    "beach": 1190.0,
}
ENEMY_ENTRY_REVEAL_SECONDS = 0.55
WHITE = (242, 244, 239)
INK = (15, 20, 25)
GOLD = (240, 187, 72)
RED = (218, 68, 57)
TEAL = (72, 198, 192)
GRAY = (148, 160, 166)
