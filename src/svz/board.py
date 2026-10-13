"""Coordenadas, terreno e células do tabuleiro."""
from __future__ import annotations

import pygame

from .config import (
    BOARD,
    CELL_W,
    LANE_BOMB_HOME_X,
    LANE_BOUNDS,
    ROWS,
)
from .math_utils import (
    clamp,
    lerp,
)


def lane_bounds(region: str, row: int) -> tuple[float, float]:
    """Limites reais da faixa desenhada no cenário selecionado."""
    bounds = LANE_BOUNDS.get(region, LANE_BOUNDS["city"])
    index = int(clamp(row, 0, ROWS - 1))
    return float(bounds[index]), float(bounds[index + 1])


def terrain_y(region: str, row: int, x: float) -> float:
    """Retorna a linha de contato dos pés, rodas ou casco com o terreno.

    ``x`` permanece na assinatura porque inimigos móveis consultam esta
    função a cada quadro. As rotas desta versão são horizontais: assim um
    zumbi nunca deriva verticalmente nem abandona a linha em que nasceu.
    """
    top, bottom = lane_bounds(region, row)
    # O contato fica no centro óptico da pista. Como o corpo cresce para cima,
    # 60% deixa a silhueta visualmente centrada sem apoiar o pé na mureta de
    # cima nem na borda de pedra/asfalto de baixo.
    return lerp(top, bottom, 0.60)


def lane_depth(region: str, row: int) -> float:
    """Escala de perspectiva: faixas distantes menores, frente maior."""
    first = terrain_y(region, 0, BOARD.left)
    last = terrain_y(region, ROWS - 1, BOARD.left)
    position = terrain_y(region, row, BOARD.left)
    progress = 0.0 if last == first else (position - first) / (last - first)
    # O novo litoral foi pintado com projeção quase ortográfica; nele uma
    # variação extrema fazia a primeira faixa parecer miniatura e a última,
    # gigante. Cidade e Deserto preservam a perspectiva mais profunda.
    # A primeira faixa fica logo abaixo da aba superior: 0,58 também garante
    # que cabeça/arma não sejam cortadas pelo HUD. Na frente, 0,96 evita o
    # efeito de gigante observado no cenário costeiro anterior.
    rear, front = (0.86, 0.98) if region == "beach" else (0.84, 1.0)
    return lerp(rear, front, clamp(progress, 0.0, 1.0))


def cell_center(row: int, col: int, region: str = "city") -> tuple[float, float]:
    x = BOARD.left + (col + 0.5) * CELL_W
    return x, terrain_y(region, row, x)


def lane_bomb_home_x(region: str, row: int) -> float:
    """Corrige opticamente a contenção sem deslocar as demais faixas."""
    return float(LANE_BOMB_HOME_X)


def lane_bomb_ground_y(region: str, row: int) -> float:
    """Centraliza visualmente a contenção dentro da faixa transitável.

    Personagens usam o contato dos pés no terço inferior. Uma bomba apoiada
    nesse mesmo ponto, porém, cai sobre a borda de pedras. A contenção fica no
    centro óptico da pista, mantendo terra, água e sprite no mesmo eixo.
    """
    top, bottom = lane_bounds(region, row)
    return lerp(top, bottom, 0.60)


def cell_rect(row: int, col: int, region: str = "city") -> pygame.Rect:
    top, bottom = lane_bounds(region, row)
    return pygame.Rect(
        int(BOARD.left + col * CELL_W),
        int(top),
        int(CELL_W),
        int(bottom - top),
    )
