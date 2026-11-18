"""Desenho de projéteis, trajetórias e fluxos elementais da batalha."""
from __future__ import annotations

import math
import pygame

from svz.visual_layout import PROJECTILE_LAYOUTS

from .actor_visuals import defender_weapon_origin
from .battle import Battle
from .board import lane_depth
from .config import HEIGHT, WIDTH
from .entities import Defender, Enemy, Projectile
from .math_utils import clamp, lerp
from .rendering_geometry import flow_points, ribbon_polygon, water_ribbon_polygon


class ProjectileRenderingMixin:
    def draw_pressurized_water(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        elapsed: float,
        depth: float,
        palette: tuple[tuple[int, int, int, int], ...],
    ) -> None:
        """Água sob pressão com massa, transparência e atomização na ponta."""
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = max(1.0, math.hypot(dx, dy))
        direction = pygame.Vector2(dx / distance, dy / distance)
        normal = pygame.Vector2(-direction.y, direction.x)
        count = max(14, min(30, int(distance / 5.5)))
        points: list[pygame.Vector2] = []
        for index in range(count):
            q = index / max(1, count - 1)
            wave = (
                math.sin(q * math.pi * 1.35 - elapsed * 9.0) * 0.72
                + math.sin(q * math.pi * 4.7 + elapsed * 7.0) * 0.20
            ) * depth
            fall = q * q * 5.2 * depth
            base = pygame.Vector2(lerp(start[0], end[0], q), lerp(start[1], end[1], q))
            points.append(base + normal * wave + pygame.Vector2(0, fall))

        tuples = [(round(point.x), round(point.y)) for point in points]
        outer = water_ribbon_polygon(
            tuples, 5.7 * depth, 3.3 * depth, elapsed, phase=0.0,
        )
        body = water_ribbon_polygon(
            tuples, 3.9 * depth, 2.0 * depth, elapsed, phase=1.4,
        )
        core = water_ribbon_polygon(
            tuples[: max(4, round(len(tuples) * 0.82))],
            1.65 * depth, 0.55 * depth, elapsed, phase=2.2,
        )
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if len(outer) >= 3:
            pygame.draw.polygon(layer, (19, 91, 145, 192), outer)
            pygame.draw.aalines(layer, (78, 181, 224, 205), True, outer)
        if len(body) >= 3:
            pygame.draw.polygon(layer, (48, 158, 210, 220), body)
        if len(core) >= 3:
            pygame.draw.polygon(layer, (183, 232, 244, 225), core)

        # Reflexos curtos percorrem a água em velocidades diferentes. Eles
        # comunicam vazão sem transformar o jato numa linha branca contínua.
        for index in range(4):
            q0 = (elapsed * (1.65 + index * 0.11) + index * 0.23) % 0.72
            q1 = min(0.84, q0 + 0.09 + index * 0.012)
            p0 = points[min(len(points) - 1, round(q0 * (len(points) - 1)))]
            p1 = points[min(len(points) - 1, round(q1 * (len(points) - 1)))]
            pygame.draw.aaline(
                layer, (224, 249, 252, 210),
                (round(p0.x), round(p0.y - depth)),
                (round(p1.x), round(p1.y - depth)),
            )
        pygame.draw.ellipse(
            layer, (102, 205, 235, 235),
            pygame.Rect(0, 0, max(4, round(8 * depth)), max(3, round(6 * depth))).move(
                round(start[0] - 4 * depth), round(start[1] - 3 * depth)
            ),
        )

        # A ponta atomiza em gotas de tamanhos diferentes. Todas continuam na
        # direção do mesmo alvo e no mesmo relógio, sem camada desencontrada.
        for index in range(14):
            q = 0.70 + index * 0.021
            base_index = min(len(points) - 1, round(q * (len(points) - 1)))
            base = points[base_index]
            side = math.sin(index * 2.31 + elapsed * 15.0) * (2.0 + index * 0.31) * depth
            forward = (2.0 + (index % 5) * 2.4) * depth
            drop = base + normal * side + direction * forward + pygame.Vector2(0, index * 0.34 * depth)
            radius = max(1, round((2.2 - index * 0.075) * depth))
            pygame.draw.circle(
                layer,
                (212, 245, 250, 220) if index % 3 == 0 else (66, 174, 219, 205),
                (round(drop.x), round(drop.y)),
                radius,
            )
        self.owner.screen.blit(layer, (0, 0))

    def draw_combustion_flame(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        elapsed: float,
        travel: float,
        depth: float,
    ) -> None:
        """Chama cônica em ignição curta, abertura média e combustão plena.

        Cada quadro é redesenhado do zero. A fase anterior, portanto, some
        enquanto a próxima ocupa mais comprimento e volume. Isso evita tanto
        o acúmulo de quadros quanto o aspecto de uma fita líquida vermelha.
        """
        vector = pygame.Vector2(end[0] - start[0], end[1] - start[1])
        distance = vector.length()
        if distance < 2.0:
            return
        direction = vector.normalize()
        normal = pygame.Vector2(-direction.y, direction.x)
        phase = clamp(elapsed / max(0.01, travel), 0.0, 1.0)
        # Três poses materiais com transição suave: a anterior apaga enquanto
        # a seguinte assume o volume. Não há uma fita que cresce como água.
        stage = min(2, int(phase * 3.0))
        local = phase * 3.0 - stage
        stage_widths = (9.0, 20.0, 34.0)
        previous_width = stage_widths[max(0, stage - 1)]
        width = lerp(previous_width, stage_widths[stage], local) * depth
        flicker = math.sin(elapsed * 31.0) * 1.1 * depth
        tip = pygame.Vector2(end) + normal * flicker
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        def flame_polygon(length_ratio: float, width_ratio: float, wobble: float) -> list[pygame.Vector2]:
            """Pluma orgânica: volume contínuo com bordas vivas e assimétricas."""
            sample_count = 20
            upper: list[pygame.Vector2] = []
            lower: list[pygame.Vector2] = []
            for index in range(sample_count):
                q = index / (sample_count - 1)
                center = pygame.Vector2(start) + direction * distance * length_ratio * q
                envelope = math.sin(math.pi * q) ** 0.70
                # A pluma abre mais na metade final e fecha numa ponta fina.
                envelope *= 0.62 + 0.48 * q
                upper_noise = (
                    math.sin(index * 1.73 + elapsed * 24.0) * wobble
                    + math.sin(index * 0.61 - elapsed * 17.0) * wobble * 0.55
                )
                lower_noise = (
                    math.sin(index * 1.29 - elapsed * 21.0 + 1.4) * wobble
                    + math.sin(index * 0.47 + elapsed * 13.0) * wobble * 0.48
                )
                upper_half = width * width_ratio * envelope * (1.0 + upper_noise)
                lower_half = width * width_ratio * envelope * (0.82 + lower_noise)
                upper.append(center - normal * max(0.0, upper_half))
                lower.append(center + normal * max(0.0, lower_half))
            return upper + list(reversed(lower))

        outer = flame_polygon(1.0, 1.0, 0.12)
        middle = flame_polygon(0.90, 0.67, 0.10)
        hot = flame_polygon(0.64, 0.34, 0.07)
        pygame.draw.polygon(layer, (177, 43, 12, 188), outer)
        pygame.draw.aalines(layer, (233, 71, 15, 218), True, outer)
        pygame.draw.polygon(layer, (244, 89, 13, 232), middle)
        pygame.draw.polygon(layer, (255, 178, 36, 246), hot)

        # Línguas independentes quebram a borda do cone e dão combustão, não
        # líquido tingido. A ponta de cada língua pulsa, mas nunca volta.
        for index in range(6):
            q0 = 0.08 + index * 0.13
            q1 = min(0.94, q0 + 0.24 + (index % 3) * 0.09)
            center = pygame.Vector2(start) + direction * distance * q0
            tongue_tip = pygame.Vector2(start) + direction * distance * q1
            side = math.sin(elapsed * (21.0 + index) + index * 1.8) * width * 0.42
            tongue_tip += normal * side
            half = max(1.8, width * max(0.10, 0.27 - index * 0.025))
            color = (
                (255, 190, 43, 240)
                if index < 4
                else (244, 92, 20, 230)
            )
            pygame.draw.polygon(
                layer,
                color,
                [center - normal * half, tongue_tip, center + normal * half],
            )

        inner_tip = pygame.Vector2(start) + direction * distance * (0.32 + 0.07 * local)
        inner_half = max(1.8, width * 0.22)
        pygame.draw.polygon(
            layer,
            (255, 221, 92, 248),
            [pygame.Vector2(start) - normal * 1.5, inner_tip,
             pygame.Vector2(start) + normal * 1.5,
             pygame.Vector2(start) + direction * distance * 0.22 + normal * inner_half],
        )
        hot_tip = pygame.Vector2(start) + direction * distance * 0.30
        pygame.draw.line(
            layer, (255, 247, 198, 248), start,
            (round(hot_tip.x), round(hot_tip.y)), max(2, round(3.2 * depth)),
        )

        if stage == 2:
            for index in range(7):
                ember = tip - direction * (5 + index * 7) * depth
                ember += normal * math.sin(elapsed * 17.0 + index * 2.0) * (4 + index * 0.7) * depth
                pygame.draw.circle(
                    layer, (255, 131, 35, 170),
                    (round(ember.x), round(ember.y - index * 0.7 * depth)),
                    max(1, round(1.5 * depth)),
                )
            # Fumaça somente na combustão plena, deslocada para cima e já
            # perdendo opacidade; ela não nasce no bocal nem cobre o soldado.
            for index in range(3):
                smoke = tip - direction * (3 + index * 10) * depth
                smoke += normal * math.sin(elapsed * 8.0 + index) * 4.0 * depth
                smoke.y -= (5 + index * 3) * depth
                pygame.draw.circle(
                    layer, (54, 47, 42, 72 - index * 14),
                    (round(smoke.x), round(smoke.y)),
                    max(2, round((4.5 - index * 0.6) * depth)),
                )
        self.owner.screen.blit(layer, (0, 0))

    def draw_elemental_stream(self, projectile: Projectile, x: float, y: float) -> None:
        """Desenha um fluxo contínuo preso ao emissor, sem sprite duplicada.

        A origem é recalculada no equipamento a cada quadro. Duas fitas
        suaves formam matéria e brilho; assim o jato cresce do bocal até o
        alvo sem virar uma mancha separada na frente do personagem.
        """
        if isinstance(projectile.owner, Defender):
            start_x, start_y = defender_weapon_origin(projectile.owner)
        elif isinstance(projectile.owner, Enemy):
            start_x, start_y = Battle.enemy_projectile_origin(
                projectile.owner,
                "acid" if projectile.kind == "poison" else "torpedo",
            )
        else:
            start_x, start_y = float(projectile.x), float(projectile.y)
        dx, dy = float(x) - start_x, float(y) - start_y
        distance = math.hypot(dx, dy)
        if distance < 3.0:
            return
        source_row = int(getattr(projectile.owner, "row", 0))
        depth = lane_depth(self.owner.battle.region if self.owner.battle else "city", source_row)
        palette = {
            "flame": ((125, 43, 24, 225), (239, 91, 31, 245), (255, 213, 72, 255)),
            "waterjet": ((24, 91, 142, 218), (57, 157, 202, 242), (178, 224, 234, 238)),
            "poison": ((38, 89, 42, 225), (83, 174, 50, 245), (180, 226, 81, 255)),
        }[projectile.kind]
        is_water = projectile.kind == "waterjet"
        if is_water:
            self.draw_pressurized_water(
                (start_x, start_y),
                (x, y),
                projectile.elapsed,
                depth,
                palette,
            )
            return
        if projectile.kind == "flame":
            self.draw_combustion_flame(
                (start_x, start_y), (x, y), projectile.elapsed,
                projectile.travel, depth,
            )
            return
        points = flow_points(
            (start_x, start_y),
            (x, y),
            projectile.elapsed,
            # Alta pressão oscila pouco. O desenho anterior ondulava como um
            # cabo elétrico e deixava três linhas separadas em vez de água.
            amplitude={"flame": 3.0, "poison": 3.5}[projectile.kind] * depth,
            count=max(9, min(24, int(distance / 7))),
        )
        outer = ribbon_polygon(points, 8.0 * depth, 5.0 * depth, taper_tip=True)
        middle = ribbon_polygon(points, 5.2 * depth, 2.8 * depth, taper_tip=True)
        core = ribbon_polygon(points, 2.1 * depth, 0.8 * depth, taper_tip=True)
        if len(outer) >= 3:
            pygame.draw.polygon(self.owner.screen, palette[0], outer)
            pygame.draw.polygon(self.owner.screen, palette[1], middle)
            pygame.draw.polygon(self.owner.screen, palette[2], core)
        # Uma única gota/faísca de contato acompanha a ponta; não há clarão
        # adicional no bocal nem segunda animação concorrendo com o corpo.
        tip_radius = max(2, round(3.0 * depth))
        pygame.draw.circle(self.owner.screen, palette[2], (round(x), round(y)), tip_radius)

    def draw_gas_grenade_projectile(
        self,
        x: float,
        y: float,
        angle: float,
        depth: float,
        progress: float,
        previous: tuple[float, float],
    ) -> None:
        """Cápsula química legível, pequena e distinta de uma bala comum."""
        width = max(12, round(15 * depth))
        height = max(8, round(9 * depth))
        capsule = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
        body = pygame.Rect(4, 4, width, height)
        pygame.draw.ellipse(capsule, (31, 42, 31, 235), body)
        pygame.draw.ellipse(capsule, (112, 131, 72, 255), body, max(1, round(depth)))
        band = pygame.Rect(
            body.centerx - max(1, round(2 * depth)), body.y + 1,
            max(2, round(4 * depth)), body.height - 2,
        )
        pygame.draw.rect(
            capsule, (148, 221, 78, 255), band,
            border_radius=max(1, round(depth)),
        )
        pygame.draw.circle(
            capsule, (213, 245, 139, 245),
            (body.right - max(2, round(3 * depth)), body.centery),
            max(1, round(1.4 * depth)),
        )
        rotated = pygame.transform.rotate(capsule, angle + progress * 720.0)

        # Uma esteira curta ajuda a leitura do arco, mas termina antes da
        # cápsula e jamais nasce como um segundo projétil.
        trail_alpha = round(135 * (1.0 - clamp((progress - 0.62) / 0.38, 0.0, 1.0)))
        trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.aaline(
            trail, (155, 215, 108, trail_alpha), previous,
            (lerp(previous[0], x, 0.58), lerp(previous[1], y, 0.58)),
        )
        self.owner.screen.blit(trail, (0, 0))
        self.owner.screen.blit(rotated, rotated.get_rect(center=(round(x), round(y))))

    def draw_projectiles(self, battle: Battle) -> None:
        arcing_kinds = {
            "grenade", "grenade_40mm", "gas_grenade", "mortar",
            "mortar_shell", "bazooka", "rpg7_rocket",
        }
        for projectile in battle.projectiles:
            if projectile.elapsed < 0:
                continue
            t = clamp(projectile.elapsed / projectile.travel, 0, 1)
            x = lerp(projectile.x, projectile.target_x, t)
            y = lerp(projectile.y, projectile.target_y, t) - (
                math.sin(t * math.pi) * 46 if projectile.kind in arcing_kinds else 0
            )
            if projectile.kind in {"flame", "poison", "waterjet"}:
                self.draw_elemental_stream(projectile, x, y)
                continue
            art = PROJECTILE_LAYOUTS.get(projectile.kind)
            if not art:
                continue
            row, column, width, height = art
            next_t = min(1.0, t + 0.025)
            next_x = lerp(projectile.x, projectile.target_x, next_t)
            next_y = lerp(projectile.y, projectile.target_y, next_t) - (
                math.sin(next_t * math.pi) * 46
                if projectile.kind in arcing_kinds
                else 0
            )
            angle = -math.degrees(math.atan2(next_y - y, next_x - x))
            source_row = int(getattr(projectile.owner, "row", 0))
            depth = lane_depth(battle.region, source_row)
            if projectile.kind == "gas_grenade":
                previous_t = max(0.0, t - 0.045)
                previous_x = lerp(projectile.x, projectile.target_x, previous_t)
                previous_y = lerp(projectile.y, projectile.target_y, previous_t) - (
                    math.sin(previous_t * math.pi) * 46
                )
                self.draw_gas_grenade_projectile(
                    x, y, angle, depth, t, (previous_x, previous_y),
                )
                continue
            self.blit_effect_frame(
                "projectile_sprites",
                row,
                column,
                x,
                y,
                width * depth,
                height * depth,
                alpha=176 if projectile.kind == "tracer" else 255,
                angle=angle,
            )
