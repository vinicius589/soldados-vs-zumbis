"""Janela física, quadro lógico e preferência de vídeo independentes da partida."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pygame

from .config import WIDTH, HEIGHT, SAVE_PATH
from .persistence import write_json

LOGICAL_SIZE = (WIDTH, HEIGHT)


def fit_viewport(size: tuple[int, int]) -> pygame.Rect:
    """Centraliza 16:9 sem recortar ou deformar o quadro."""
    width, height = max(1, size[0]), max(1, size[1])
    scale = min(width / WIDTH, height / HEIGHT)
    fitted = (max(1, int(WIDTH * scale)), max(1, int(HEIGHT * scale)))
    return pygame.Rect((width - fitted[0]) // 2, (height - fitted[1]) // 2, *fitted)


def logical_position(pos: tuple[int, int], size: tuple[int, int]) -> tuple[int, int]:
    rect = fit_viewport(size)
    if not rect.collidepoint(pos):
        return (-1, -1)
    return ((pos[0] - rect.x) * WIDTH // rect.width,
            (pos[1] - rect.y) * HEIGHT // rect.height)


class VideoDisplay:
    def __init__(self, campaign_path: Path | None = None):
        path = Path(campaign_path) if campaign_path is not None else SAVE_PATH
        self.path = path.with_name(path.stem + ".video.json")
        self.fullscreen = self.load_preference()
        # pygame.init() pode retornar falhas parciais sem lançar exceção.
        # Inicialize explicitamente antes de consultar os monitores.
        pygame.display.init()
        desktops = pygame.display.get_desktop_sizes()
        try:
            self.display_index = int(os.environ.get("PYGAME_DISPLAY", "0"))
        except ValueError:
            self.display_index = 0
        if not 0 <= self.display_index < len(desktops):
            self.display_index = 0
        self.desktop_size = desktops[self.display_index] if desktops else LOGICAL_SIZE
        available = (max(320, self.desktop_size[0] - 40),
                     max(180, self.desktop_size[1] - 80))
        self.window_size = fit_viewport((min(WIDTH, available[0]),
                                        min(HEIGHT, available[1]))).size
        self.scaled_surface = None

    def load_preference(self) -> bool:
        try:
            if self.path.stat().st_size > 4096:
                return False
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return isinstance(data, dict) and data.get("fullscreen") is True
        except (OSError, ValueError):
            return False

    def save_preference(self) -> bool:
        return write_json({"version": 1, "fullscreen": self.fullscreen}, self.path)

    def create_mode(self, flags: int = 0) -> pygame.Surface:
        size = self.desktop_size if self.fullscreen else self.window_size
        surface = pygame.display.set_mode(
            size, flags | (pygame.FULLSCREEN if self.fullscreen else 0),
            display=self.display_index,
        )
        self.scaled_surface = None
        return surface

    def mouse_position(self, pos: tuple[int, int] | None = None) -> tuple[int, int]:
        return logical_position(pygame.mouse.get_pos() if pos is None else pos,
                                pygame.display.get_window_size())

    def present(self, frame: pygame.Surface) -> None:
        target = pygame.display.get_surface()
        rect = fit_viewport(target.get_size())
        if rect.size == LOGICAL_SIZE:
            scaled = frame
        else:
            if self.scaled_surface is None or self.scaled_surface.get_size() != rect.size:
                self.scaled_surface = pygame.Surface(rect.size).convert(frame)
            pygame.transform.smoothscale(frame, rect.size, self.scaled_surface)
            scaled = self.scaled_surface
        if rect.size != target.get_size():
            target.fill((0, 0, 0))
        target.blit(scaled, rect)
        pygame.display.flip()

