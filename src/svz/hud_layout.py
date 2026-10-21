"""Geometria única do HUD: desenho e hitboxes usam as mesmas coordenadas."""
import pygame
from .config import TOTAL_WAVES


def supplies_rect():
    return pygame.Rect(18, 18, 104, 102)


def card_rects(count):
    return [pygame.Rect(132 + index * 100, 18, 94, 102) for index in range(min(8, count))]


def remove_rect():
    return pygame.Rect(940, 18, 112, 102)


def menu_rect():
    return pygame.Rect(1116, 16, 148, 38)


def pause_rect():
    return pygame.Rect(1116, 64, 148, 34)


def waves_rect():
    return pygame.Rect(946, 638, 318, 70)


def next_wave_rect():
    return pygame.Rect(790, 670, 142, 34)


def wave_progress(battle):
    """Ondas concluídas, sem fingir conhecer a fração de vida dos inimigos."""
    completed = TOTAL_WAVES if battle.victory else battle.wave - (1 if battle.started_wave else 0)
    return max(0, min(TOTAL_WAVES, completed)) / TOTAL_WAVES
