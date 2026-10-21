"""Primitivos de desenho compartilhados pelas telas do jogo."""
from __future__ import annotations

import pygame

from .config import GRAY, INK


class RenderingPrimitivesMixin:
    def button_rect(self, label: str, x: int, y: int, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(x, y, w, h)

    def draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[float, float], anchor: str = "topleft", shadow: bool = False) -> pygame.Rect:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        if shadow:
            shadow_surface = font.render(text, True, (0, 0, 0))
            shadow_rect = shadow_surface.get_rect()
            setattr(shadow_rect, anchor, (int(pos[0] + 2), int(pos[1] + 2)))
            self.owner.screen.blit(shadow_surface, shadow_rect)
        self.owner.screen.blit(surface, rect)
        return rect

    def panel(self, rect: pygame.Rect, alpha: int = 210, border: tuple[int, int, int] = (91, 106, 112), radius: int = 10) -> None:
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (12, 20, 25, alpha), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, (*border, min(255, alpha + 25)), surface.get_rect(), width=2, border_radius=radius)
        self.owner.screen.blit(surface, rect)

    @staticmethod
    def _fit_button_font(label: str, rect: pygame.Rect) -> pygame.font.Font:
        """Mantém os rótulos dentro do botão, inclusive nos controles estreitos do HUD."""
        max_width = max(8, rect.width - 14)
        preferred_size = 20
        for size in (preferred_size, 18, 16, 14, 13, 12, 11, 10):
            font = pygame.font.SysFont("arial", size, bold=True)
            if font.size(label)[0] <= max_width:
                return font
        return pygame.font.SysFont("arial", 10, bold=True)

    def button(self, label: str, rect: pygame.Rect, accent: tuple[int, int, int], enabled: bool = True) -> None:
        hover = rect.collidepoint(self.owner.video.mouse_position()) and enabled
        outer = tuple(min(255, c + 25) for c in accent) if hover else accent
        color = outer if enabled else (67, 73, 76)
        pygame.draw.rect(self.owner.screen, (8, 13, 17), rect.inflate(4, 4), border_radius=8)
        pygame.draw.rect(self.owner.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.owner.screen, (228, 235, 228), rect, width=1, border_radius=7)
        font = self._fit_button_font(label, rect)
        self.draw_text(label, font, INK if enabled else GRAY, rect.center, "center")
