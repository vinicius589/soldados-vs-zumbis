"""Monta um único 8x5 a partir das animações que já foram aprovadas."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "PROTOTIPO_CARTA_CAMPO" / "assets"
OUTPUT = ROOT / "assets" / "beta4_producao" / "molde_armado_aprovado_8x5_v1.png"
CELL = 256
BODY_HEIGHT = 214
ACTOR_X = 112
GROUND_Y = 238


def cells(path: Path, rows: int) -> list[pygame.Surface]:
    image = pygame.image.load(str(path)).convert_alpha()
    width, height = image.get_size()
    return [
        image.subsurface(
            pygame.Rect(
                column * width // 8,
                row * height // rows,
                (column + 1) * width // 8 - column * width // 8,
                (row + 1) * height // rows - row * height // rows,
            )
        ).copy()
        for row in range(rows)
        for column in range(8)
    ]


def main_rect(frame: pygame.Surface) -> pygame.Rect:
    parts = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
    return max(parts, key=lambda rect: rect.width * rect.height)


def place(canvas: pygame.Surface, frame: pygame.Surface, row: int, column: int) -> None:
    main = main_rect(frame)
    content = frame.get_bounding_rect(min_alpha=8)
    factor = BODY_HEIGHT / max(1, main.height)
    crop = frame.subsurface(content).copy()
    scaled = pygame.transform.smoothscale(
        crop,
        (max(1, round(crop.get_width() * factor)), max(1, round(crop.get_height() * factor))),
    )
    scaled_main = pygame.Rect(
        round((main.left - content.left) * factor),
        round((main.top - content.top) * factor),
        max(1, round(main.width * factor)),
        max(1, round(main.height * factor)),
    )
    destination = (
        column * CELL + ACTOR_X - scaled_main.centerx,
        row * CELL + GROUND_Y - scaled_main.bottom,
    )
    canvas.blit(scaled, destination)


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    movement = cells(ASSETS / "guarda_rua_implantacao_idle_8x2_v1.png", 2)
    combat = cells(ASSETS / "guarda_rua_combate_8x4_v1_limpo.png", 4)
    rows = (
        movement[:8],
        movement[8:16],
        combat[:8],
        combat[8:16],
        combat[16:24],
    )
    canvas = pygame.Surface((CELL * 8, CELL * 5), pygame.SRCALPHA)
    for row, sequence in enumerate(rows):
        for column, frame in enumerate(sequence):
            place(canvas, frame, row, column)
    pygame.image.save(canvas, str(OUTPUT))
    pygame.quit()
    print(OUTPUT)


if __name__ == "__main__":
    main()
