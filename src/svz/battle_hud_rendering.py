"""Desenho da bandeja de cartas, suprimentos e HUD superior da batalha."""
from __future__ import annotations

import math
import pygame

from . import hud_layout
from .config import CARD_RECHARGE_SECONDS, GOLD, GRAY, HEIGHT, INK, RED, TEAL, TOTAL_WAVES, WHITE, WIDTH
from .content import DEFENSES
from .math_utils import clamp


class BattleHudRenderingMixin:
    def draw_battle_top(self) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        rects = battle.card_rects()
        screen = self.owner.screen
        # Bandeja de recrutamento: recurso à esquerda, oito retratos e retorno à base.
        tray = pygame.Rect(10, 10, 1052, 118)
        pygame.draw.rect(screen, (8, 15, 21), tray.move(0, 4), border_radius=10)
        pygame.draw.rect(screen, (17, 31, 39), tray, border_radius=10)
        pygame.draw.rect(screen, (74, 111, 122), tray, 2, border_radius=10)
        for x in (16, 1053):
            for y in (17, 119):
                pygame.draw.circle(screen, (119, 158, 165), (x, y), 2)
        supply = hud_layout.supplies_rect()
        self.panel(supply, 245, (69, 139, 146), 7)
        self.draw_text("SUPRIMENTOS", self.owner.fonts.tiny, TEAL, (supply.centerx, 24), "midtop")
        crate = pygame.Rect(supply.centerx - 18, 47, 36, 23)
        pygame.draw.rect(screen, (73, 119, 101), crate, border_radius=3)
        pygame.draw.rect(screen, (153, 194, 166), crate, 2, border_radius=3)
        pygame.draw.line(screen, (34, 71, 65), (crate.left+8, crate.top), (crate.left+8, crate.bottom), 3)
        pygame.draw.line(screen, (34, 71, 65), (crate.right-8, crate.top), (crate.right-8, crate.bottom), 3)
        self.draw_text(str(battle.supplies), self.owner.fonts.h2, GOLD, (supply.centerx, 84), "center")
        self.draw_text(f"LIMITE {int(battle.difficulty_data['supply_cap'])}", self.owner.fonts.tiny, GRAY, (supply.centerx, 108), "center")
        for index, ((key, display), rect) in enumerate(zip(battle.selected, rects)):
            data = DEFENSES[key]
            active = index == battle.selected_card and not battle.remove_mode
            affordable = battle.supplies >= int(data["cost"])
            accent = TEAL if active else (76, 105, 114)
            self.panel(rect, 248, accent, 5)
            portrait = pygame.Rect(rect.x+3, rect.y+4, rect.width-6, 70)
            pygame.draw.rect(screen, (34, 52, 62), portrait, border_radius=4)
            self.blit_actor_in_rect(self.card_sprite(battle.region, key, int(data["sprite"])), portrait, 64)
            if not affordable:
                shade = pygame.Surface(portrait.size, pygame.SRCALPHA)
                shade.fill((15, 18, 22, 115))
                screen.blit(shade, portrait)
            cooldown = battle.card_cooldowns[index]
            if cooldown > 0:
                shade = pygame.Surface(portrait.size, pygame.SRCALPHA)
                height = math.ceil(portrait.height * clamp(cooldown / CARD_RECHARGE_SECONDS, 0, 1))
                pygame.draw.rect(shade, (4, 10, 15, 170), (0, 0, portrait.width, height))
                screen.blit(shade, portrait)
                self.draw_text(f"{math.ceil(cooldown)}s", self.owner.fonts.h2, WHITE, portrait.center, "center", True)
            self.draw_text(str(index+1), self.owner.fonts.tiny, TEAL, (rect.x+6, rect.y+5), shadow=True)
            pygame.draw.rect(screen, (185, 205, 204), (rect.x+4, rect.bottom-26, rect.width-8, 21), border_radius=3)
            self.draw_text(f"{data['cost']} SUP", self.owner.fonts.tiny, (20, 58, 58) if affordable else (135, 34, 28), (rect.centerx, rect.bottom-15), "center")
            if active:
                pygame.draw.rect(screen, GOLD, rect, 3, border_radius=5)
        base_button = battle.remove_rect()
        self.button("VOLTAR À BASE", base_button, (231, 133, 79) if battle.remove_mode else (47, 91, 105))
        # Ícone simples de quartel: a ação recolhe a tropa e devolve parte do custo.
        cx = base_button.centerx
        pygame.draw.polygon(screen, (167, 196, 185), [(cx-21, 37), (cx, 22), (cx+21, 37)])
        pygame.draw.rect(screen, (39, 66, 75), (cx-17, 36, 34, 20), border_radius=2)
        pygame.draw.rect(screen, (130, 178, 169), (cx-17, 36, 34, 20), 2, border_radius=2)
        pygame.draw.rect(screen, (16, 35, 43), (cx-4, 44, 8, 12), border_radius=1)
        pygame.draw.rect(screen, (205, 222, 210), (cx-12, 40, 5, 5), border_radius=1)
        pygame.draw.rect(screen, (205, 222, 210), (cx+7, 40, 5, 5), border_radius=1)
        self.draw_text("35% DEVOLVIDO", self.owner.fonts.tiny, TEAL, (cx, 105), "center")
        self.button("MENU", battle.menu_rect(), (65, 119, 130))
        self.button("PAUSA", battle.pause_rect(), GOLD)
        ticker = battle.message if battle.message_timer > 0 else "Selecione um soldado e escolha uma casa livre."
        self.draw_wrapped(ticker, self.owner.fonts.tiny, GOLD, pygame.Rect(18, 137, 1040, 30), 1)
        self.panel(pygame.Rect(18,638,260,48), 242, GOLD, 8)
        self.draw_text(f"PONTOS: {battle.score}", self.owner.fonts.h2, GOLD, (32,649))
        self.draw_text(f"F1: FICHA  •  F5: SALVAR  •  {self.owner.settings.label('pause')}: PAUSA", self.owner.fonts.tiny, WHITE, (18, HEIGHT-24), shadow=True)
        waves = hud_layout.waves_rect()
        self.panel(waves, 242, (70, 117, 126), 9)
        self.draw_text(f"ONDA {battle.wave}/{TOTAL_WAVES}", self.owner.fonts.small, GOLD, (waves.x+14, waves.y+8))
        self.draw_text(f"{len(battle.enemies)+len(battle.orders)} INVASORES", self.owner.fonts.tiny, WHITE, (waves.right-14, waves.y+11), "topright")
        bar = pygame.Rect(waves.x+14, waves.y+34, waves.width-28, 14)
        pygame.draw.rect(screen, (17, 31, 37), bar, border_radius=4)
        fill = bar.copy(); fill.width = round(bar.width * hud_layout.wave_progress(battle))
        if fill.width:
            pygame.draw.rect(screen, TEAL, fill, border_radius=4)
        pygame.draw.rect(screen, (117, 158, 163), bar, 1, border_radius=4)
        for milestone in (4, 8, 12):
            x = bar.x + round((bar.width-1)*milestone/TOTAL_WAVES)
            pygame.draw.line(screen, (147, 165, 158), (x, bar.bottom+2), (x, bar.bottom+16), 2)
            pygame.draw.polygon(screen, (211, 128, 79), [(x, bar.bottom+2), (x-9, bar.bottom+2), (x-9, bar.bottom+9), (x, bar.bottom+7)])
        self.draw_text("CONCLUÍDAS", self.owner.fonts.tiny, GRAY, (bar.x, bar.bottom+4))
        self.button("PRÓXIMA", battle.next_wave_rect(), battle.region_color(), not battle.started_wave and not battle.finished)
        status = "EM COMBATE" if battle.started_wave else f"INTERVALO {max(0, math.ceil(battle.intermission))}s"
        self.draw_text(status, self.owner.fonts.tiny, WHITE, (battle.next_wave_rect().centerx, 649), "center", True)

        # Ficha completa por hover ou F1 para comparar as cartas.
        mouse = self.owner.video.mouse_position()
        hovered = next(((key, display, rect) for (key, display), rect in zip(battle.selected, rects) if rect.collidepoint(mouse)), None)
        if self.owner.control_mode == "keyboard" and self.owner.show_card_info:
            key,display = battle.selected[battle.selected_card]
            hovered = (key,display,rects[battle.selected_card])
        if hovered:
            key, display, rect = hovered
            data = DEFENSES[key]
            tooltip_x = int(clamp(rect.centerx - 240, 154, WIDTH - 490))
            tooltip = pygame.Rect(tooltip_x, 174, 480, 142)
            self.panel(tooltip, 239, battle.region_color(), 8)
            self.draw_text(display, self.owner.fonts.small, GOLD, (tooltip.x + 13, tooltip.y + 9))
            self.draw_wrapped(data["ability"], self.owner.fonts.tiny, WHITE, pygame.Rect(tooltip.x + 13, tooltip.y + 35, tooltip.width - 26, 69), 3)
            metric_a, metric_b = self.card_metrics(data)
            self.draw_text(f"{metric_a} • {metric_b}", self.owner.fonts.tiny, TEAL, (tooltip.x+13, tooltip.bottom-25))

    def health_bar(self, x: float, y: float, width: float, ratio: float, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 4)
        pygame.draw.rect(self.owner.screen, (18, 21, 23), rect, border_radius=2)
        fill_width = int(rect.width * clamp(ratio, 0, 1))
        if fill_width > 0:
            pygame.draw.rect(self.owner.screen, color, (rect.x, rect.y, fill_width, rect.height), border_radius=2)

    def ammo_bar(self, x: float, y: float, width: float, ratio: float) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 3)
        pygame.draw.rect(self.owner.screen, (19, 28, 33), rect, border_radius=2)
        pygame.draw.rect(self.owner.screen, TEAL, (rect.x, rect.y, int(rect.width * clamp(ratio, 0, 1)), rect.height), border_radius=2)
