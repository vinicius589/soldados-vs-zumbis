"""Desenho das telas e da partida, composto pela aplicação."""
from __future__ import annotations

import math
import pygame

from .config import (
    GOLD,
    HEIGHT,
    RED,
    WHITE,
    WIDTH,
)


from .ui_panels import bindings_panel
from .menu_rendering import MenuRenderingMixin
from .effects_rendering import EffectsRenderingMixin
from .entity_rendering import EntityRenderingMixin
from .status_rendering import StatusRenderingMixin
from .projectile_rendering import ProjectileRenderingMixin
from .battle_hud_rendering import BattleHudRenderingMixin
from .card_rendering import CardRenderingMixin
from .rendering_primitives import RenderingPrimitivesMixin
from .battle_overlay_rendering import BattleOverlayRenderingMixin


class GameRenderer(MenuRenderingMixin, EffectsRenderingMixin, ProjectileRenderingMixin, EntityRenderingMixin, StatusRenderingMixin, BattleHudRenderingMixin, CardRenderingMixin, RenderingPrimitivesMixin, BattleOverlayRenderingMixin):
    """Apresentação composta pela aplicação; alterações de tela ficam aqui."""

    def __init__(self, owner: "Game") -> None:
        self.owner = owner

    def draw_battle(self) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        background = self.owner.assets.images[f"{battle.region}_bg"]
        shake_x = int(math.sin(self.owner.scene_elapsed * 55) * 4 * battle.shake * (not self.owner.settings.reduced_motion))
        shake_y = int(math.cos(self.owner.scene_elapsed * 37) * 3 * battle.shake * (not self.owner.settings.reduced_motion))
        self.owner.screen.blit(background, (shake_x, shake_y))
        # Generais, piras, efeitos de horda e clima de chefe são exatamente
        # as animações aprovadas no visualizador de cenários.
        self.owner.scenario_runtime.draw(self.owner.screen, battle)
        # As quatro pistas já estão pintadas no próprio cenário. Nenhuma faixa
        # sintética é sobreposta à arte: pés, água, asfalto e areia coincidem.
        ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if battle.global_toxic > 0:
            ambient.fill((92, 202, 86, int(30 + battle.global_toxic * 8)))
        self.owner.screen.blit(ambient, (0, 0))
        self.draw_lane_bombs(battle)
        mouse = self.owner.video.mouse_position()
        hovered_cell = (
            (battle.keyboard_row, battle.keyboard_col)
            if self.owner.control_mode == "keyboard"
            else battle.board_cell_at(mouse)
        )
        if hovered_cell and not battle.finished:
            row, col = hovered_cell
            outline = battle.ground_cell_rect(row, col)
            color = RED if battle.remove_mode else battle.region_color()
            pygame.draw.rect(self.owner.screen, color, outline, 2, border_radius=12)
            if self.owner.control_mode == "keyboard":
                pygame.draw.rect(self.owner.screen, WHITE, outline.inflate(-6, -6), 1, border_radius=10)
            if battle.cell_is_water(row, col):
                pygame.draw.arc(self.owner.screen, (110, 213, 250), outline.inflate(-22, -28), 0, math.pi, 2)
        for defender in battle.defenders:
            self.draw_defender(defender)
        for enemy in battle.enemies:
            self.draw_enemy(enemy)
        self.draw_fallen(battle)
        if self.owner.overlay_surface is not None:
            self.owner.screen = self.owner.overlay_surface
        self.draw_projectiles(battle)
        self.draw_visual_effects(battle)
        self.draw_particles(battle)
        self.draw_battle_top()
        self.draw_battle_status()
        if battle.finished:
            self.draw_result_overlay()

    def draw(self) -> None:
        # Atores OpenGL ficam entre o mundo e o HUD. A cada quadro as duas
        # superfícies são reconstruídas; nenhuma animação deixa rastros.
        self.owner.screen = self.owner.world_surface
        self.owner.world_surface.fill((0, 0, 0, 255))
        self.owner.actor_commands.clear()
        if self.owner.overlay_surface is not None:
            self.owner.overlay_surface.fill((0, 0, 0, 0))
        if self.owner.scene == "loading":
            self.draw_loading()
        elif self.owner.scene == "title":
            self.draw_title()
        elif self.owner.scene in ("confirm_new", "confirm_exit"):
            self.draw_session_confirmation()
        elif self.owner.scene == "difficulty":
            self.draw_difficulty()
        elif self.owner.scene == "campaign":
            self.draw_campaign()
        elif self.owner.scene == "characters":
            self.draw_characters()
        elif self.owner.scene == "story":
            self.draw_story()
        elif self.owner.scene == "profile":
            self.draw_profile()
        elif self.owner.scene == "settings":
            self.draw_settings()
        elif self.owner.scene == "bindings":
            bindings_panel(self)
        elif self.owner.scene == "scores":
            self.draw_scores()
        elif self.owner.scene == "howto":
            self.draw_howto()
        elif self.owner.scene == "battle" and self.owner.battle:
            self.draw_battle()
        focus = self.owner.navigation.rect()
        if focus is not None and self.owner.scene != "battle":
            pygame.draw.rect(self.owner.screen, GOLD, focus.inflate(6,6), 3, border_radius=7)
        if self.owner.video_notice:
            self.panel(pygame.Rect(180, 172, 920, 40), 245, GOLD, 6)
            self.draw_text(self.owner.video_notice, self.owner.fonts.small, WHITE,
                           (WIDTH // 2, 192), "center")
        if self.owner.session_notice:
            self.panel(pygame.Rect(180, HEIGHT - 65, 920, 40), 245, RED, 6)
            self.draw_text(self.owner.session_notice, self.owner.fonts.small, WHITE,
                           (WIDTH // 2, HEIGHT - 45), "center")

