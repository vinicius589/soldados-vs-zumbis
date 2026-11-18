"""Desenho de efeitos, nuvens e quadros de disparo.

O mixin usa o proprietário do renderizador para acessar a tela e os recursos.
Ele não importa o renderizador principal, evitando dependência circular.
"""
from __future__ import annotations

import math
import pygame

from .actor_visuals import defender_visual_layout, defender_weapon_origin
from .battle import Battle
from .board import lane_bounds, lane_depth, terrain_y
from .config import ROWS, WIDTH
from .entities import Defender, Enemy
from .math_utils import clamp
from .motion import VisualEffect


class EffectsRenderingMixin:
    def draw_linked_skill_effect(
        self,
        effect: VisualEffect,
        x: float,
        y: float,
        progress: float,
    ) -> bool:
        """Desenha sinais próprios que permanecem presos ao personagem.

        Estes gestos não reaproveitam fogo, água ou uma explosão genérica. A
        geometria é pequena e funcional: pulso, rede, cura, roubo ou parasita
        comunicam exatamente a regra executada pelo inimigo.
        """
        supported = {
            "command_aura",
            "signal_pulse",
            "heal_pulse",
            "heal_receive",
            "supply_snatch",
            "net_cast",
            "parasite_burst",
        }
        if effect.kind not in supported:
            return False
        size = max(84, round(180 * effect.scale))
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        center = pygame.Vector2(size / 2, size / 2)
        fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
        alpha = max(0, min(255, round(225 * fade)))
        color = (*effect.color, alpha)
        pale = tuple(min(255, channel + 70) for channel in effect.color) + (alpha,)
        radius = max(12, round((20 + progress * 46) * effect.scale))

        if effect.kind in {"command_aura", "signal_pulse", "heal_pulse"}:
            pygame.draw.circle(layer, color, center, radius, max(2, round(4 * effect.scale)))
            pygame.draw.circle(layer, pale, center, max(5, round(radius * 0.62)), max(1, round(2 * effect.scale)))
        if effect.kind == "command_aura":
            for angle in (-0.72, 0.0, 0.72):
                end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
                pygame.draw.line(layer, pale, center, end, max(2, round(3 * effect.scale)))
        elif effect.kind == "signal_pulse":
            pygame.draw.line(layer, pale, center + (-5, 9), center + (0, -radius * 0.72), max(2, round(3 * effect.scale)))
            for side in (-1, 1):
                arc = pygame.Rect(0, 0, radius * 1.18, radius * 1.18)
                arc.center = center + (side * radius * 0.26, -radius * 0.34)
                pygame.draw.arc(layer, pale, arc, -1.0, 1.0, max(2, round(2 * effect.scale)))
        elif effect.kind == "heal_pulse":
            arm = max(6, round(radius * 0.36))
            thickness = max(3, round(radius * 0.18))
            pygame.draw.rect(layer, pale, (center.x - thickness / 2, center.y - arm, thickness, arm * 2))
            pygame.draw.rect(layer, pale, (center.x - arm, center.y - thickness / 2, arm * 2, thickness))
            # Partículas orbitam o gesto de cura; a cruz deixa de ser a única
            # mudança entre os quadros.
            for index in range(6):
                angle = progress * math.tau * 1.5 + index * math.tau / 6
                orbit = radius * (0.58 + 0.10 * (index % 2))
                point = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit
                pygame.draw.circle(layer, pale, point, max(2, round(2.8 * effect.scale)))
        elif effect.kind == "heal_receive":
            # O aliado curado responde à habilidade: energia sobe do chão ao
            # tronco em tempos diferentes, sempre na mesma pista do emissor.
            for index in range(7):
                phase = (progress + index / 7.0) % 1.0
                px = center.x + math.sin(index * 2.1 + progress * 5.0) * radius * 0.46
                py = center.y + radius * 0.55 - phase * radius * 1.25
                pygame.draw.circle(layer, pale, (round(px), round(py)), max(2, round(3.0 * effect.scale)))
            cross_y = center.y - radius * 0.15
            arm = max(4, round(radius * 0.22))
            thickness = max(2, round(radius * 0.10))
            pygame.draw.rect(layer, color, (center.x - thickness / 2, cross_y - arm, thickness, arm * 2))
            pygame.draw.rect(layer, color, (center.x - arm, cross_y - thickness / 2, arm * 2, thickness))
        elif effect.kind == "supply_snatch":
            for index in range(6):
                angle = index * math.tau / 6 + progress * 0.5
                start = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
                end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * 0.30
                pygame.draw.line(layer, color, start, end, max(2, round(3 * effect.scale)))
                pygame.draw.circle(layer, pale, end, max(2, round(4 * effect.scale)))
        elif effect.kind == "net_cast":
            net_radius = max(16, round(radius * 0.90))
            rect = pygame.Rect(0, 0, net_radius * 2, net_radius * 1.45)
            rect.center = center
            for step in range(-net_radius, net_radius + 1, max(7, net_radius // 4)):
                pygame.draw.line(layer, color, (rect.left, center.y + step * 0.55), (rect.right, center.y - step * 0.55), 2)
                pygame.draw.line(layer, color, (rect.left, center.y - step * 0.55), (rect.right, center.y + step * 0.55), 2)
            pygame.draw.ellipse(layer, pale, rect, 2)
        elif effect.kind == "parasite_burst":
            ground = center + (0, radius * 0.45)
            for index in range(7):
                angle = -2.85 + index * 0.42
                length = radius * (0.60 + (index % 2) * 0.24)
                tip = ground + pygame.Vector2(math.cos(angle), math.sin(angle)) * length
                pygame.draw.line(layer, color, ground, tip, max(2, round(4 * effect.scale)))
                pygame.draw.circle(layer, pale, tip, max(2, round(3 * effect.scale)))

        self.owner.screen.blit(layer, layer.get_rect(center=(round(x), round(y))))
        return True

    def draw_gas_cloud(
        self,
        x: float,
        y: float,
        progress: float,
        scale: float,
    ) -> None:
        """Nuvem baixa de gás anticorrosivo, com expansão e dissipação."""
        # A altura cabe dentro de uma única pista. Assim o recorte de faixa
        # protege as linhas vizinhas sem amputar a parte principal da nuvem.
        width = max(108, round(174 * scale))
        height = max(58, round(70 * scale))
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        center_x = width / 2
        ground_y = height * 0.78
        growth = 0.34 + 0.66 * (1.0 - (1.0 - progress) ** 2)
        fade = 1.0 - clamp((progress - 0.66) / 0.34, 0.0, 1.0)

        ring = pygame.Rect(0, 0, width * 0.72 * growth, height * 0.24 * growth)
        ring.center = (center_x, ground_y)
        pygame.draw.ellipse(
            layer, (146, 231, 77, round(185 * fade)), ring,
            max(1, round(2 * scale)),
        )

        for index in range(11):
            phase = index * 1.73
            horizontal = math.sin(phase) * width * (0.12 + 0.018 * index) * growth
            rise = (5 + (index % 4) * 5 + progress * (10 + index * 0.72)) * scale
            drift = math.sin(progress * 4.2 + phase) * 7 * scale
            blob_x = center_x + horizontal + drift
            blob_y = ground_y - rise
            radius_x = (12 + (index % 4) * 4) * scale * growth
            radius_y = (8 + ((index + 2) % 4) * 2.7) * scale * growth
            outer = pygame.Rect(0, 0, radius_x * 2.0, radius_y * 2.0)
            outer.center = (blob_x, blob_y)
            inner = outer.inflate(-radius_x * 0.62, -radius_y * 0.62)
            pygame.draw.ellipse(
                layer, (50, 112, 35, round((135 + index * 4) * fade)), outer,
            )
            pygame.draw.ellipse(
                layer, (146, 222, 70, round((145 + index * 5) * fade)), inner,
            )

        for index in range(7):
            q = (progress * 0.82 + index / 7.0) % 1.0
            speck_x = center_x + math.sin(index * 2.4) * width * 0.25 * growth
            speck_y = ground_y - (10 + q * 34) * scale
            pygame.draw.circle(
                layer,
                (190, 242, 112, round(170 * fade * (1.0 - q * 0.45))),
                (round(speck_x), round(speck_y)),
                max(1, round(2.1 * scale)),
            )
        self.owner.screen.blit(
            layer, layer.get_rect(midbottom=(round(x), round(y + 18 * scale))),
        )

    def draw_visual_effects(self, battle: Battle) -> None:
        """Exibe somente quadros rasterizados de matéria e impacto reais."""
        styles = {
            "flame_impact": ("elemental_effects", 0, 118, 92),
            "water_impact": ("elemental_effects", 1, 132, 88),
            "toxic_impact": ("elemental_effects", 2, 126, 96),
            "toxic_wave": ("elemental_effects", 2, 212, 136),
            "ground_slam": ("ability_effects", 0, 236, 126),
            "arcane_cast": ("ability_effects", 1, 164, 174),
            "tidal_surge": ("ability_effects", 2, 260, 142),
            "water_splash": ("ability_effects", 2, 138, 82),
            "electric_arc": ("combat_effects", 0, 78, 54),
            "explosion": ("combat_effects", 2, 184, 146),
            "ballistic_impact": ("combat_effects", 0, 92, 66),
        }
        for effect in battle.effects:
            progress = clamp(effect.elapsed / max(0.01, effect.duration), 0.0, 1.0)
            effect_x, effect_y = effect.x, effect.y
            if isinstance(effect.owner, Enemy):
                effect_x, effect_y = battle.enemy_effect_origin(
                    effect.owner,
                    effect.anchor_kind or effect.kind,
                )
            previous_clip = self.owner.screen.get_clip()
            boss_can_cross = isinstance(effect.owner, Enemy) and effect.owner.is_boss
            if not boss_can_cross:
                if isinstance(effect.owner, (Enemy, Defender)):
                    effect_row = effect.owner.row
                else:
                    effect_row = min(
                        range(ROWS),
                        key=lambda row: abs(terrain_y(battle.region, row, effect_x) - effect_y),
                    )
                top, bottom = lane_bounds(battle.region, effect_row)
                self.owner.screen.set_clip(pygame.Rect(0, int(top), WIDTH, max(1, math.ceil(bottom - top))))
            if self.draw_linked_skill_effect(effect, effect_x, effect_y, progress):
                self.owner.screen.set_clip(previous_clip)
                continue
            if effect.kind == "toxic_wave":
                self.draw_gas_cloud(effect_x, effect_y, progress, effect.scale)
                self.owner.screen.set_clip(previous_clip)
                continue
            stage = min(3, int(progress * 4.0))
            sheet, row, base_width, base_height = styles.get(
                effect.kind,
                ("combat_effects", 2, 184, 146),
            )
            growth = 0.80 + progress * 0.36
            fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
            self.blit_effect_frame(
                sheet,
                row,
                stage,
                effect_x,
                effect_y,
                base_width * effect.scale * growth,
                base_height * effect.scale * growth,
                alpha=int(255 * fade),
            )
            self.owner.screen.set_clip(previous_clip)

    def blit_effect_frame(
        self,
        sheet: str,
        row: int,
        stage: int,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        alpha: int = 255,
        angle: float = 0.0,
        midbottom: bool = False,
        flip_x: bool = False,
    ) -> pygame.Rect | None:
        """Desenha um quadro pré-pintado; jamais fabrica um símbolo geométrico."""
        frames = self.owner.assets.effect_frames.get(sheet, [])
        index = row * 4 + max(0, min(3, int(stage)))
        if index >= len(frames) or frames[index].get_width() <= 1:
            return None
        rendered = self.owner.assets.scaled(frames[index], width, height)
        if flip_x:
            rendered = pygame.transform.flip(rendered, True, False)
        if angle:
            rendered = pygame.transform.rotate(rendered, angle)
        elif alpha < 255:
            rendered = rendered.copy()
        if alpha < 255:
            rendered.set_alpha(max(0, min(255, int(alpha))))
        if midbottom:
            rect = rendered.get_rect(midbottom=(int(x), int(y)))
        else:
            rect = rendered.get_rect(center=(int(x), int(y)))
        self.owner.screen.blit(rendered, rect)
        return rect

    def blit_muzzle_cycle(
        self,
        stage: int,
        x: float,
        y: float,
        *,
        width: float,
        height: float,
    ) -> pygame.Rect | None:
        """Desenha somente a ignição e o clarão na boca da arma.

        A folha também possui fumaça e estojos em posições próprias, mas ao
        escalar a célula inteira esses elementos pareciam um segundo projétil
        embaixo do soldado. O recuo da sprite continua visível e a sequência
        usa apenas os três clarões centrados no cano.
        """
        frames = self.owner.assets.animation_frames.get("muzzle_cycle", [])
        if not frames:
            return None
        flash_cycle = (0, 1, 2, 3, 2, 1, 0, 0)
        frame_index = flash_cycle[max(0, min(len(flash_cycle) - 1, int(stage)))]
        frame = frames[min(len(frames) - 1, frame_index)]
        if frame.get_width() <= 1 or frame.get_height() <= 1:
            return None
        rendered = self.owner.assets.scaled(frame, width, height)
        rect = rendered.get_rect(midleft=(int(x), int(y)))
        self.owner.screen.blit(rendered, rect)
        return rect

    @staticmethod
    def frame_has_muzzle_flash(
        sprite: pygame.Surface,
        defender: Defender,
    ) -> bool:
        """Evita duplicar um clarão que já foi pintado junto da arma."""
        layout = defender_visual_layout(defender)
        depth = lane_depth(defender.region, defender.row)
        muzzle_x, muzzle_y = defender_weapon_origin(defender)
        ratio = layout.source_height / max(1.0, layout.body_height)
        source_x = round(
            sprite.get_width() / 2
            + ((muzzle_x - defender.render_x) / max(0.01, depth)) * ratio
        )
        source_y = round(
            sprite.get_height()
            - ((defender.y - muzzle_y) / max(0.01, depth)) * ratio
        )
        area = pygame.Rect(source_x - 18, source_y - 12, 21, 25).clip(sprite.get_rect())
        if area.width <= 0 or area.height <= 0:
            return False
        for x in range(area.left, area.right):
            for y in range(area.top, area.bottom):
                red, green, blue, alpha = sprite.get_at((x, y))
                if alpha > 24 and red >= 190 and green >= 82 and blue <= 125 and red >= blue + 70:
                    return True
        return False
