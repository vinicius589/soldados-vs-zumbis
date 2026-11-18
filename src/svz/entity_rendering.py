"""Desenho de soldados, inimigos e poses em campo.

O mixin concentra a apresentação das entidades. HUD, menu e efeitos continuam
em seus próprios componentes, acessados pelos métodos do renderizador composto.
"""
from __future__ import annotations

import math
import pygame

from svz.presenter import ActorCommand
from svz.visual_layout import DEFENDER_WEAPON_PROFILES, ENEMY_BODY_LAYOUTS

from .actor_visuals import (
    actor_pose,
    animated_actor_render_scale,
    defender_animation_profile,
    defender_render_scale,
    defender_visual_layout,
    defender_weapon_origin,
    enemy_animation_profile,
    enemy_render_scale,
)
from .battle import Battle
from .board import lane_bounds, lane_depth
from .config import RED
from .content import CRAWLER_ENEMIES, REGIONS
from .entities import Defender, Enemy
from .math_utils import clamp
from .motion import ActorMotion


class EntityRenderingMixin:
    def defender_sprite(self, battle: Battle, defender: Defender) -> pygame.Surface:
        """Fonte visual da defesa ativa e da animação de derrota."""
        if defender.visual_animation is not None:
            return defender.visual_animation.frame
        return self.card_sprite(battle.region, defender.key, defender.sprite_index)

    def enemy_sprite(self, battle: Battle, enemy: Enemy) -> pygame.Surface:
        """Fonte visual do inimigo, centralizando os retratos especiais."""
        if enemy.visual_animation is not None:
            return enemy.visual_animation.frame
        if enemy.is_boss:
            frames = self.owner.assets.animation_frames.get(f"{battle.region}_boss_actions", [])
            if len(frames) >= 12:
                boss_row = REGIONS[battle.region]["bosses"].index(enemy.key)
                row_frames = frames[boss_row * 4:boss_row * 4 + 4]
                if enemy.motion.state == "skill":
                    return row_frames[3]
                if enemy.motion.state == "attack":
                    return row_frames[2]
                if enemy.motion.state in {"hit", "stunned"}:
                    return row_frames[1]
                return row_frames[enemy.motion.phase(fps=4.6, frames=2)]
        sheet_key = {
            ("city", "caminhante"): "city_walker_walk",
            ("desert", "digger"): "desert_digger_states",
            ("beach", "nadador"): "beach_swimmer_walk",
        }.get((battle.region, enemy.key))
        if sheet_key:
            frames = self.owner.assets.animation_frames.get(sheet_key, [])
            if frames:
                if enemy.key == "digger" and enemy.motion.state == "walk":
                    frame_index = enemy.motion.phase(fps=5.5, frames=2)
                elif enemy.key == "digger" and enemy.motion.state == "dig_enter":
                    frame_index = min(4, 2 + int(enemy.motion.state_elapsed / 0.16))
                elif enemy.key == "digger" and enemy.motion.state == "dig_tunnel":
                    frame_index = 4
                elif enemy.key == "digger" and enemy.motion.state == "dig_emerge":
                    frame_index = 5
                elif enemy.key == "digger" and enemy.motion.state == "attack":
                    frame_index = 6
                elif enemy.motion.state == "walk":
                    frame_index = enemy.motion.phase(fps=10.0, frames=len(frames))
                elif enemy.motion.state == "attack":
                    frame_index = 2
                elif enemy.motion.state in {"hit", "stunned"}:
                    frame_index = 4
                else:
                    frame_index = 0
                return frames[frame_index % len(frames)]
        if enemy.key == "saltador" and "zombie_jumper_beta3" in self.owner.assets.images:
            return self.owner.assets.images["zombie_jumper_beta3"]
        if enemy.key == "rastejante" and battle.region == "city" and "zombie_crawler_beta3" in self.owner.assets.images:
            return self.owner.assets.images["zombie_crawler_beta3"]
        return self.owner.assets.zombie(battle.region, int(enemy.data["sprite"]))

    def draw_actor_sprite(
        self,
        sprite: pygame.Surface,
        x: float,
        ground_y: float,
        width: float,
        height: float,
        motion: ActorMotion,
        *,
        enemy: bool,
        vertical_offset: float = 0.0,
        alpha: int = 255,
        progress: float = 0.0,
        state_override: str | None = None,
        profile: str = "generic",
        frame_animated: bool = False,
    ) -> pygame.Rect:
        """Desenha uma pose articulada preservando os pés no terreno real."""
        if sprite.get_width() <= 1:
            return pygame.Rect(int(x), int(ground_y), 1, 1)
        # Animações de produção já compartilham uma caixa e um pivô fixos. O
        # trim por quadro recentralizava cada pose e fazia corpo, mangueira e
        # efeitos saltarem alguns pixels. Artes estáticas antigas ainda usam o
        # recorte tradicional.
        if not frame_animated:
            sprite = self.owner.assets.trimmed(sprite)
        action_progress = clamp(float(progress), 0.0, 1.0)
        if action_progress <= 0.0 and motion.event_left > 0:
            action_progress = clamp(
                motion.state_elapsed / max(0.001, motion.state_elapsed + motion.event_left),
                0.0,
                1.0,
            )
        if self.owner.presenter is not None:
            self.owner.actor_commands.append(
                ActorCommand(
                    sprite=sprite,
                    x=float(x),
                    ground_y=float(ground_y),
                    width=max(1.0, float(width)),
                    height=max(1.0, float(height)),
                    state="sprite_sequence" if frame_animated else (state_override or motion.state),
                    elapsed=motion.state_elapsed,
                    enemy=enemy,
                    vertical_offset=vertical_offset,
                    alpha=max(0, min(255, int(alpha))),
                    hit_flash=0.0 if frame_animated else motion.hit_flash,
                    progress=action_progress,
                    profile="sprite_sequence" if frame_animated else profile,
                )
            )
            return pygame.Rect(
                int(x - width / 2),
                int(ground_y + vertical_offset - height),
                max(1, int(width)),
                max(1, int(height)),
            )
        if frame_animated:
            dx, dy, angle, scale_x, scale_y = 0.0, 0.0, 0.0, 1.0, 1.0
        else:
            dx, dy, angle, scale_x, scale_y = actor_pose(
                motion,
                enemy=enemy,
                profile=profile,
                progress=action_progress,
            )
        size = (max(1, int(width * scale_x)), max(1, int(height * scale_y)))
        rendered = pygame.transform.rotate(self.owner.assets.scaled(sprite, *size), angle)
        if alpha < 255:
            rendered.set_alpha(max(0, alpha))
        if motion.hit_flash > 0 and not frame_animated:
            flash_alpha = int(105 * clamp(motion.hit_flash / 0.13, 0.0, 1.0))
            flash = pygame.Surface(rendered.get_size(), pygame.SRCALPHA)
            flash.fill((255, 238, 210, flash_alpha))
            rendered.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        rect = rendered.get_rect(midbottom=(int(x + dx), int(ground_y + dy + vertical_offset)))
        self.owner.screen.blit(rendered, rect)
        return rect

    def draw_fallen(self, battle: Battle) -> None:
        """Mostra uma queda curta antes de a silhueta sumir em partículas."""
        for fallen in battle.fallen:
            progress = clamp(fallen.elapsed / max(0.01, fallen.duration), 0.0, 1.0)
            alpha = int(255 * (1.0 - progress))
            motion = ActorMotion(state="dead", state_elapsed=fallen.elapsed, event_left=fallen.duration)
            self.draw_actor_sprite(
                fallen.sprite,
                fallen.x,
                fallen.y,
                fallen.width,
                fallen.height,
                motion,
                enemy=fallen.enemy,
                alpha=alpha,
                progress=progress,
            )

    def draw_defender(self, defender: Defender) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        x, y = defender.render_x, defender.y
        role = defender.stats["role"]
        depth = lane_depth(battle.region, defender.row)
        sprite = self.defender_sprite(battle, defender)
        frame_animated = defender.visual_animation is not None
        if frame_animated:
            layout = defender_visual_layout(defender)
            scale = animated_actor_render_scale(
                sprite,
                depth,
                body_height=layout.body_height,
                source_body_height=layout.source_height,
            )
        else:
            scale = defender_render_scale(defender)
        shadow_width = max(28, int(scale[0] * (0.82 if role in {"barrier", "boat", "sub"} else 0.68)))
        shadow_height = max(6, int(13 * depth))
        shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        if battle.cell_is_water(defender.row, defender.col):
            pygame.draw.ellipse(shadow, (90, 220, 235, 105), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (7, 36, 52, 85), shadow.get_rect().inflate(-10, -4))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        self.owner.screen.blit(shadow, shadow.get_rect(midbottom=(int(x), int(y + 3))))
        # A mesma fonte de arte atende carta, campo e queda. A pose em si
        # muda conforme o estado emitido pela lógica de combate.
        reload_progress = (
            1.0 - defender.reload_timer / max(0.01, defender.reload_total)
            if defender.reloading
            else 0.0
        )
        rect = self.draw_actor_sprite(
            sprite,
            x,
            y,
            *scale,
            defender.motion,
            enemy=False,
            progress=reload_progress,
            profile=defender_animation_profile(defender),
            frame_animated=frame_animated,
        )
        world_target = self.owner.screen
        if self.owner.overlay_surface is not None:
            self.owner.screen = self.owner.overlay_surface
        if defender.motion.state == "attack":
            if frame_animated and defender.visual_animation is not None:
                attack_progress = defender.visual_animation.normalized_progress
            else:
                total = max(0.001, defender.motion.state_elapsed + defender.motion.event_left)
                attack_progress = clamp(defender.motion.state_elapsed / total, 0.0, 1.0)
            stage = min(7, int(attack_progress * 8.0))
            # O cano está à frente do peito, nunca no centro/perna do ator.
            # Água, fogo e veneno não ganham uma segunda figura colada na
            # arma. O fluxo real é desenhado pelo projétil contínuo, usando a
            # mesma origem física do cano durante toda a ação.
            # Se a folha já contém um clarão conectado, ele é preservado. Se
            # não contém, desenhamos um único clarão no mesmo ponto usado pelo
            # projétil. O tamanho vem da arma real da carta, nunca da SWAT como
            # molde universal; água e fogo não passam por esta camada.
            weapon_profile = DEFENDER_WEAPON_PROFILES.get(defender.key)
            if (
                weapon_profile is not None
                and weapon_profile.flash_size[0] > 0
                and not self.frame_has_muzzle_flash(sprite, defender)
            ):
                muzzle_x, muzzle_y = defender_weapon_origin(defender)
                flash_width, flash_height = weapon_profile.flash_size
                self.blit_muzzle_cycle(
                    stage,
                    muzzle_x,
                    muzzle_y,
                    width=flash_width * depth,
                    height=flash_height * depth,
                )
        if defender.corrosion > 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(defender.corrosion * 5.0) % 4,
                x, y - scale[1] * 0.38, scale[0] * 0.72, scale[1] * 0.62,
                alpha=168,
            )
        bar_width = max(32, int(44 * depth))
        self.health_bar(x - bar_width / 2, y + 5, bar_width, defender.hp / defender.max_hp, (89, 214, 144))
        if defender.max_ammo:
            ammo_width = max(28, int(38 * depth))
            ammo_ratio = (
                1.0 - defender.reload_timer / max(0.01, defender.reload_total)
                if defender.reloading
                else defender.ammo / max(1, defender.max_ammo)
            )
            self.ammo_bar(x - ammo_width / 2, y + 11, ammo_width, ammo_ratio)
        self.owner.screen = world_target

    def draw_enemy(self, enemy: Enemy) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        water_enemy = battle.region == "beach" and enemy.row in battle.water_rows
        depth = lane_depth(battle.region, enemy.row)
        sprite = self.enemy_sprite(battle, enemy)
        frame_animated = enemy.visual_animation is not None
        render_x = enemy.x
        if frame_animated:
            animation = enemy.visual_animation
            assert animation is not None
            if animation.state == "bite":
                offsets = (
                    (0, 1, 2, 4, 7, 6, 3, 0)
                    if "runner" in enemy.tags
                    else (0, 2, 7, 14, 23, 21, 11, 0)
                )
                render_x -= offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            elif animation.state == "hit":
                offsets = (0, 3, 7, 10, 8, 5, 2, 0)
                render_x += offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            crawler = enemy.key in CRAWLER_ENEMIES
            if crawler:
                category = "crawler"
            elif enemy.is_boss:
                # O chefe é reconhecivelmente maior, mas não cresce a ponto de
                # invadir a pista vizinha ou ter cabeça/pés cortados.
                category = "boss"
            elif enemy.data.get("subboss"):
                category = "subboss"
            else:
                # Humanoides comuns compartilham a mesma altura corporal dos
                # soldados. A ameaça vem da animação e dos atributos, não de
                # um zumbi comum artificialmente gigante.
                category = "common"
            body_height, source_height = ENEMY_BODY_LAYOUTS[category]
            scale = animated_actor_render_scale(
                sprite,
                depth,
                body_height=body_height,
                source_body_height=source_height,
            )
        else:
            scale = enemy_render_scale(enemy, battle.region)
        shadow_width = max(28, int(scale[0] * (0.86 if enemy.is_boss else 0.68)))
        shadow_height = max(6, int(13 * depth))
        shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        if water_enemy:
            pygame.draw.ellipse(shadow, (91, 221, 238, 112), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (8, 37, 50, 88), shadow.get_rect().inflate(-10, -4))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 115), shadow.get_rect())
        self.owner.screen.blit(shadow, shadow.get_rect(midbottom=(int(render_x), int(enemy.y + 3))))

        vertical_offset = 0.0
        alpha = 255
        top, bottom = lane_bounds(battle.region, enemy.row)
        lane_height = bottom - top
        if enemy.jump_state:
            progress = clamp(1.0 - enemy.jump_timer / max(0.01, enemy.jump_duration), 0.0, 1.0)
            vertical_offset = -math.sin(progress * math.pi) * lane_height * 0.78
        elif enemy.dig_state == "enter":
            progress = clamp(1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0)
            vertical_offset = lane_height * 0.42 * progress
            alpha = int(255 * (1.0 - progress * 0.42))
        elif enemy.dig_state == "emerge":
            progress = clamp(1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0)
            vertical_offset = lane_height * 0.42 * (1.0 - progress)
            alpha = int(146 + 109 * progress)
        entry_reveal = float(getattr(enemy, "entry_reveal", 0.0))
        if entry_reveal > 0 and enemy.age < entry_reveal:
            reveal = clamp(enemy.age / entry_reveal, 0.0, 1.0)
            reveal = reveal * reveal * (3.0 - 2.0 * reveal)
            alpha = min(alpha, max(0, int(255 * reveal)))
        state_override = (
            "swim"
            if water_enemy and enemy.motion.state == "walk"
            else None
        )
        rect = self.draw_actor_sprite(
            sprite,
            render_x,
            enemy.y,
            *scale,
            enemy.motion,
            enemy=True,
            vertical_offset=vertical_offset,
            alpha=alpha,
            state_override=state_override,
            profile=enemy_animation_profile(enemy),
            frame_animated=frame_animated,
        )
        world_target = self.owner.screen
        if self.owner.overlay_surface is not None:
            self.owner.screen = self.owner.overlay_surface
        if enemy.burn > 0:
            self.blit_effect_frame(
                "elemental_effects", 0, int(enemy.age * 11.0) % 4,
                render_x, enemy.y + 1, scale[0] * 0.94, scale[1] * 0.78,
                alpha=205, midbottom=True,
            )
        if enemy.poisoned > 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(enemy.age * 8.0) % 4,
                render_x, enemy.y - scale[1] * 0.42,
                scale[0] * 1.04, scale[1] * 0.72, alpha=176,
            )
        if enemy.soaked > 0:
            self.blit_effect_frame(
                "elemental_effects", 1, int(enemy.age * 9.0) % 4,
                render_x, enemy.y + 2, scale[0] * 1.15, scale[1] * 0.58,
                alpha=182, midbottom=True,
            )
        if enemy.corrosion > 0 and enemy.poisoned <= 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(enemy.age * 7.0) % 4,
                render_x, enemy.y - scale[1] * 0.46,
                scale[0] * 0.76, scale[1] * 0.54, alpha=154,
            )
        # Roubo, cura e demais habilidades só exibem efeito durante o gesto
        # correspondente. Uma aura permanente aqui parecia veneno aleatório.
        width = (74 if enemy.is_boss else 44) * depth
        self.health_bar(render_x - width / 2, enemy.y + 5, width, enemy.hp / enemy.max_hp, RED)
        self.owner.screen = world_target
