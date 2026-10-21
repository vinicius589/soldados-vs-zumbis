"""Animações ambientais e contenções aprovadas dos três cenários Beta 4."""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import pygame

from src.engine.animation2d import SpriteSheet
from src.engine.asset_paths import game_root

ROOT = game_root()
SCENARIO_ROOT = ROOT / "tools" / "cenarios"
AMBIENT = SCENARIO_ROOT / "animacao_ambiental"
PIXEL = ROOT / "tools" / "sprites" / "frames_sem_chroma"

COMMAND_ANCHORS = {
    # Ambos ficam no piso livre da base, abaixo das cabanas, sem encostar em
    # caixas, telhados ou nas quatro faixas. O representante naval aprovado
    # permanece exatamente no ponto anterior.
    "city": (35, 455),
    "desert": (80, 400),
    "beach": (80, 312),
}

CITY_WHISTLE_TIMELINE = (0, 0, 0, 1, 2, 3, 4, 5, 5, 6, 7, 7, 0, 0, 0, 0)
REGIONAL_SALUTE_TIMELINE = (0, 0, 1, 2, 3, 4, 4, 4, 5, 6, 7, 7, 0, 0)
BEACH_ALARM_TIMELINE = (0, 0, 1, 2, 3, 4, 5, 5, 4, 3, 6, 7, 0, 0, 0)
DESERT_BRAZIER_ANCHORS = ((997, 208), (1239, 354))


def _trim(source: pygame.Surface, padding: int = 2) -> pygame.Surface:
    rect = source.get_bounding_rect(min_alpha=8)
    if rect.width <= 0 or rect.height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    rect = rect.inflate(padding * 2, padding * 2).clip(source.get_rect())
    return source.subsurface(rect).copy()


def _fit(source: pygame.Surface, width: int, height: int) -> pygame.Surface:
    return pygame.transform.scale(source, (max(1, int(width)), max(1, int(height))))


def _fit_actor(source: pygame.Surface, body_height: int) -> pygame.Surface:
    """Preserva a anatomia do personagem e dimensiona pelo corpo visível."""
    components = pygame.mask.from_surface(source, threshold=8).get_bounding_rects()
    if not components:
        return source
    body = max(components, key=lambda rect: rect.width * rect.height)
    factor = body_height / max(1, body.height)
    return pygame.transform.scale(
        source,
        (
            max(1, round(source.get_width() * factor)),
            max(1, round(source.get_height() * factor)),
        ),
    )


def _frames(folder: Path) -> list[pygame.Surface]:
    return [
        pygame.image.load(str(path)).convert_alpha()
        for path in sorted(folder.glob("frame_*.png"))
    ]


def _normalize_sequence(
    frames: list[pygame.Surface], padding: int = 3
) -> list[pygame.Surface]:
    """Mantém a mesma caixa em todos os quadros para o corpo não pulsar."""
    bounds = [frame.get_bounding_rect(min_alpha=8) for frame in frames]
    union = bounds[0].unionall(bounds[1:])
    union.inflate_ip(padding * 2, padding * 2)
    union = union.clip(frames[0].get_rect())
    return [frame.subsurface(union).copy() for frame in frames]


def _base_point(surface: pygame.Surface, min_alpha: int = 8) -> tuple[int, int]:
    """Prende o fogo pelo centro opaco de sua base, não pelo quadro inteiro."""
    rect = surface.get_bounding_rect(min_alpha=8)
    if rect.width <= 0:
        return surface.get_width() // 2, surface.get_height()
    alpha = pygame.surfarray.array_alpha(surface)
    band_height = max(3, round(rect.height * 0.08))
    band_top = max(rect.top, rect.bottom - band_height)
    band = alpha[rect.left : rect.right, band_top : rect.bottom]
    opaque_x, opaque_y = np.nonzero(band >= min_alpha)
    if opaque_x.size == 0:
        return rect.centerx, rect.bottom
    absolute_y = opaque_y + band_top
    weights = 1.0 + (absolute_y - band_top)
    base_x = rect.left + round(float(np.average(opaque_x, weights=weights)))
    return base_x, rect.bottom


class ScenarioRuntime:
    """Estado visual por ``dt`` compartilhado com a partida real."""

    def __init__(self) -> None:
        general_cells = SpriteSheet.from_file(
            AMBIENT / "general_saudacao_3x8_v1.png"
        ).slice_equal(8, 3)
        self.generals = [
            _normalize_sequence(general_cells[row * 8 : (row + 1) * 8])
            for row in range(3)
        ]
        lieutenant_cells = SpriteSheet.from_file(
            AMBIENT / "tenente_policia_apito_1x8_v1.png"
        ).slice_equal(8, 1)
        self.city_lieutenant = _normalize_sequence(lieutenant_cells)
        beach_alarm_cells = SpriteSheet.from_file(
            AMBIENT / "mulher_banhista_assustada_1x8_v2.png"
        ).slice_equal(8, 1)
        self.beach_alarm = _normalize_sequence(beach_alarm_cells)
        self.whistle_font = pygame.font.Font(None, 28)
        self.brazier = [
            _trim(frame)
            for frame in SpriteSheet.from_file(
                AMBIENT / "pira_toxica_verde_1x8_v1.png"
            ).slice_equal(8, 1)
        ]
        self.aquatic_mine = [
            _trim(frame)
            for frame in SpriteSheet.from_file(
                AMBIENT / "mina_aquatica_v2_1x8.png"
            ).slice_equal(8, 1)
        ]
        self.land_charge = [
            _trim(frame)
            for frame in SpriteSheet.from_file(
                AMBIENT / "carga_terrestre_minas_v2_1x8.png"
            ).slice_equal(8, 1)
        ]
        self.tractor = _frames(PIXEL / "veiculos" / "trator_esteiras")
        self.drone = _frames(PIXEL / "veiculos" / "drone_helices")
        self.splash = _frames(PIXEL / "vfx" / "respingo_agua")
        self.elapsed = 0.0
        self.horde_flame = 0.0
        self._was_horde = False
        self._last_city_whistle_cycle = -1
        self._last_beach_alarm_cycle = -1
        self._last_storm_cycle = -1
        rng = random.Random(731)
        self.rain = [
            (
                rng.randrange(1280),
                rng.randrange(720),
                rng.randrange(380, 560),
                rng.randrange(8, 17),
            )
            for _ in range(90)
        ]

    def update(self, dt: float, battle: Any | None) -> None:
        self.elapsed += dt
        horde = bool(
            battle
            and battle.started_wave
            and (battle.orders or battle.enemies or battle.spawn_timer > 0)
        )
        target = 1.0 if horde else 0.0
        rate = 1.15 if target > self.horde_flame else 0.80
        step = rate * dt
        if self.horde_flame < target:
            self.horde_flame = min(target, self.horde_flame + step)
        else:
            self.horde_flame = max(target, self.horde_flame - step)
        if battle is None:
            self._was_horde = False
            return
        audio = getattr(getattr(battle, "app", None), "audio", None)
        if audio is None:
            return
        if horde and not self._was_horde:
            # A chama das piras cresce junto com este sinal grave; não existe
            # uma chama ou um ruído solto fora da taça.
            audio.play("wave", min_interval_ms=700)
        self._was_horde = horde
        if battle.region == "city":
            tick = int(self.elapsed * 3.6)
            frame = CITY_WHISTLE_TIMELINE[tick % len(CITY_WHISTLE_TIMELINE)]
            cycle = tick // len(CITY_WHISTLE_TIMELINE)
            if frame == 3 and cycle != self._last_city_whistle_cycle:
                self._last_city_whistle_cycle = cycle
                audio.play("whistle", min_interval_ms=900)
        elif battle.region == "beach":
            tick = int(self.elapsed * 3.2)
            frame = BEACH_ALARM_TIMELINE[tick % len(BEACH_ALARM_TIMELINE)]
            cycle = tick // len(BEACH_ALARM_TIMELINE)
            if frame == 3 and cycle != self._last_beach_alarm_cycle:
                self._last_beach_alarm_cycle = cycle
                audio.play("alarm_scream", min_interval_ms=1300)
            if self._boss_active(battle):
                storm_cycle = int(self.elapsed // 3.8)
                if storm_cycle != self._last_storm_cycle:
                    self._last_storm_cycle = storm_cycle
                    audio.play("thunder", min_interval_ms=2400)

    @staticmethod
    def _boss_active(battle: Any) -> bool:
        return any(
            getattr(enemy, "is_boss", False) and enemy.hp > 0
            for enemy in battle.enemies
        )

    def _draw_whistle_sfx(
        self, screen: pygame.Surface, officer_rect: pygame.Rect
    ) -> None:
        """Onomatopeia curta, sincronizada somente com o apito na boca."""
        pulse = 1.0 + 0.05 * math.sin(self.elapsed * 18.0)
        fill = self.whistle_font.render("FIIIU!", True, (255, 222, 82))
        outline = self.whistle_font.render("FIIIU!", True, (16, 23, 30))
        if pulse != 1.0:
            size = (round(fill.get_width() * pulse), round(fill.get_height() * pulse))
            fill = pygame.transform.scale(fill, size)
            outline = pygame.transform.scale(outline, size)
        center = (officer_rect.right + 22, officer_rect.top + 18)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)):
            screen.blit(
                outline, outline.get_rect(center=(center[0] + dx, center[1] + dy))
            )
        screen.blit(fill, fill.get_rect(center=center))

    def _draw_alarm_sfx(self, screen: pygame.Surface, actor_rect: pygame.Rect) -> None:
        """Grito curto ao lado da boca, sem cobrir rosto ou cabeça."""
        pulse = 1.0 + 0.06 * math.sin(self.elapsed * 20.0)
        fill = self.whistle_font.render("AA!  AA!", True, (255, 225, 92))
        outline = self.whistle_font.render("AA!  AA!", True, (38, 18, 15))
        size = (round(fill.get_width() * pulse), round(fill.get_height() * pulse))
        fill = pygame.transform.scale(fill, size)
        outline = pygame.transform.scale(outline, size)
        center = (actor_rect.right + 34, actor_rect.top + 37)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            screen.blit(
                outline, outline.get_rect(center=(center[0] + dx, center[1] + dy))
            )
        screen.blit(fill, fill.get_rect(center=center))

    def _draw_commander(self, screen: pygame.Surface, region: str) -> None:
        if region == "city":
            index = CITY_WHISTLE_TIMELINE[
                int(self.elapsed * 3.6) % len(CITY_WHISTLE_TIMELINE)
            ]
            source = self.city_lieutenant[index]
        elif region == "desert":
            index = REGIONAL_SALUTE_TIMELINE[
                int(self.elapsed * 3.0) % len(REGIONAL_SALUTE_TIMELINE)
            ]
            source = self.generals[1][index]
        else:
            index = BEACH_ALARM_TIMELINE[
                int(self.elapsed * 3.2) % len(BEACH_ALARM_TIMELINE)
            ]
            source = self.beach_alarm[index]
        # Mesma altura corporal nas três regiões, mantendo a razão original da
        # arte. A versão anterior forçava 84x126 e deformava braços, quepe e
        # pernas no meio da continência.
        frame = _fit_actor(source, 96)
        x, baseline = COMMAND_ANCHORS[region]
        rect = frame.get_rect(bottomleft=(x, baseline))
        screen.blit(frame, rect)
        if region == "city" and index in (3, 4, 5):
            self._draw_whistle_sfx(screen, rect)
        elif region == "beach" and index in (3, 4, 5):
            self._draw_alarm_sfx(screen, rect)

    def _draw_city_boss_rain(self, screen: pygame.Surface) -> None:
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill((20, 42, 50, 34))
        screen.blit(veil, (0, 0))
        for index, (start_x, start_y, speed, length) in enumerate(self.rain):
            x = (
                int((start_x - self.elapsed * (speed * 0.33 + index % 7 * 9)) % 1360)
                - 40
            )
            y = int((start_y + self.elapsed * speed) % 790) - 35
            pygame.draw.line(
                screen, (168, 222, 221, 115), (x, y), (x - 4, y + length), 1
            )

    def _draw_desert(self, screen: pygame.Surface, boss_active: bool) -> None:
        glow = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 0.45)
        glow.fill((255, 154, 48, int(5 + pulse * 11)))
        screen.blit(glow, (0, 0))
        growth = self.horde_flame * self.horde_flame * (3.0 - 2.0 * self.horde_flame)
        fps = 6.5 + growth * 3.5
        frame_index = int(self.elapsed * fps) % len(self.brazier)
        # Coordenadas medidas diretamente nas marcações do usuário. Cada par
        # representa o centro da boca da taça no fundo aprovado.
        # Pedido final: as duas chamas usam exatamente a mesma caixa visual.
        depth_scales = (1.0, 1.0)
        width = round(54 + 30 * growth)
        height = round(84 + 48 * growth)
        for offset, (anchor, depth) in enumerate(
            zip(DESERT_BRAZIER_ANCHORS, depth_scales, strict=False)
        ):
            flame = _fit(
                self.brazier[(frame_index + offset * 3) % 8],
                round(width * depth),
                round(height * depth),
            )
            flame.set_alpha(round(220 + 24 * growth))
            base_x, base_y = _base_point(flame)
            screen.blit(flame, (anchor[0] - base_x, anchor[1] - base_y))
        if boss_active:
            # A fumaça tóxica fica contida na entrada, sem ocupar a pista.
            fog = pygame.Surface((190, 360), pygame.SRCALPHA)
            for index in range(9):
                x = 90 + int(math.sin(self.elapsed * 0.8 + index) * 34)
                y = 330 - index * 34 - int((self.elapsed * 18 + index * 13) % 42)
                pygame.draw.ellipse(
                    fog, (91, 205, 79, 22 + index * 2), (x - 55, y - 30, 110, 72)
                )
            screen.blit(fog, (1085, 110))

    def _draw_beach_boss_storm(self, screen: pygame.Surface) -> None:
        storm = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        storm.fill((4, 17, 25, 42))
        screen.blit(storm, (0, 0))
        cycle = self.elapsed % 3.8
        if cycle < 0.16:
            flash = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            flash.fill((164, 236, 224, int(76 * (1.0 - cycle / 0.16))))
            screen.blit(flash, (0, 0))

    def draw(self, screen: pygame.Surface, battle: Any) -> None:
        boss_active = self._boss_active(battle)
        if battle.region == "city" and boss_active:
            self._draw_city_boss_rain(screen)
        elif battle.region == "desert":
            self._draw_desert(screen, boss_active)
        elif battle.region == "beach" and boss_active:
            self._draw_beach_boss_storm(screen)
        self._draw_commander(screen, battle.region)

    def lane_defense_frame(
        self, region: str, row: int, *, moving: bool, water: bool
    ) -> tuple[pygame.Surface, tuple[int, int]]:
        if region == "city":
            frames, size, fps = (
                self.tractor,
                (67, 52) if not moving else (116, 92),
                10.0,
            )
        elif region == "desert":
            frames, size, fps = self.drone, (62, 46) if not moving else (104, 78), 12.0
        else:
            frames = self.aquatic_mine if water else self.land_charge
            size, fps = ((74, 48) if water else (66, 44)), 4.0
            # Os quatro primeiros quadros são o pulso armado. Os quadros de
            # explosão só pertencem ao disparo da cadeia, nunca ao repouso.
            if not moving and len(frames) >= 4:
                return frames[int(self.elapsed * fps) % 4], size
        # Um pacote incompleto de distribuição não deve derrubar a partida.
        # O fallback transparente mantém o loop vivo e permite que a tela de
        # diagnóstico seja alcançada; a versão oficial inclui os quadros reais.
        if not frames:
            return pygame.Surface((1, 1), pygame.SRCALPHA), (1, 1)
        return frames[int(self.elapsed * fps) % len(frames)], size
