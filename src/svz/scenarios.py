"""Animações ambientais e contenções aprovadas dos três cenários Beta 4."""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import pygame

from svz.animation import SpriteSheet


from .paths import ASSET_ROOT

AMBIENT = ASSET_ROOT / "environment"
PIXEL = ASSET_ROOT / "frames"

DESERT_BRAZIER_ANCHORS = ((997, 208), (1239, 354))


def _trim(source: pygame.Surface, padding: int = 2) -> pygame.Surface:
    rect = source.get_bounding_rect(min_alpha=8)
    if rect.width <= 0 or rect.height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    rect = rect.inflate(padding * 2, padding * 2).clip(source.get_rect())
    return source.subsurface(rect).copy()


def _fit(source: pygame.Surface, width: int, height: int) -> pygame.Surface:
    return pygame.transform.scale(source, (max(1, int(width)), max(1, int(height))))


def _frames(folder: Path) -> list[pygame.Surface]:
    return [pygame.image.load(str(path)).convert_alpha() for path in sorted(folder.glob("frame_*.png"))]


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
        self.brazier = [
            _trim(frame)
            for frame in SpriteSheet.from_file(AMBIENT / "pira_toxica_verde_1x8_v1.png").slice_equal(8, 1)
        ]
        self.aquatic_mine = [
            _trim(frame)
            for frame in SpriteSheet.from_file(AMBIENT / "mina_aquatica_v2_1x8.png").slice_equal(8, 1)
        ]
        self.land_charge = [
            _trim(frame)
            for frame in SpriteSheet.from_file(AMBIENT / "carga_terrestre_minas_v2_1x8.png").slice_equal(8, 1)
        ]
        self.tractor = _trim(pygame.image.load(str(PIXEL / "veiculos/trator_esteiras/frame_00.png")).convert_alpha())
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
            (rng.randrange(1280), rng.randrange(720), rng.randrange(380, 560), rng.randrange(8, 17))
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
        if battle.region == "beach" and self._boss_active(battle):
            storm_cycle = int(self.elapsed // 3.8)
            if storm_cycle != self._last_storm_cycle:
                self._last_storm_cycle = storm_cycle
                audio.play("thunder", min_interval_ms=2400)

    @staticmethod
    def _boss_active(battle: Any) -> bool:
        return any(getattr(enemy, "is_boss", False) and enemy.hp > 0 for enemy in battle.enemies)

    def _draw_city_boss_rain(self, screen: pygame.Surface) -> None:
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill((20, 42, 50, 34))
        screen.blit(veil, (0, 0))
        for index, (start_x, start_y, speed, length) in enumerate(self.rain):
            x = int((start_x - self.elapsed * (speed * 0.33 + index % 7 * 9)) % 1360) - 40
            y = int((start_y + self.elapsed * speed) % 790) - 35
            pygame.draw.line(screen, (168, 222, 221, 115), (x, y), (x - 4, y + length), 1)

    def _draw_desert(self, screen: pygame.Surface) -> None:
        glow = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 0.45)
        glow.fill((255, 154, 48, int(5 + pulse * 11)))
        screen.blit(glow, (0, 0))

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
            self._draw_desert(screen)
        elif battle.region == "beach" and boss_active:
            self._draw_beach_boss_storm(screen)

    def lane_defense_frame(
        self, region: str, row: int, *, moving: bool, water: bool
    ) -> tuple[pygame.Surface, tuple[int, int]]:
        if region == "city":
            width = 105
            return self.tractor, (width, round(width * self.tractor.get_height() / self.tractor.get_width()))
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
