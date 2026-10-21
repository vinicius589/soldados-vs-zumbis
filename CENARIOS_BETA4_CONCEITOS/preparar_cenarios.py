"""Prepara cópias 1280x720 dos conceitos sem deformar o pixel art."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "prontos_1280x720"
SIZE = (1280, 720)


def cover_crop(source: pygame.Surface) -> pygame.Surface:
    target_w, target_h = SIZE
    width, height = source.get_size()
    factor = max(target_w / width, target_h / height)
    scaled = pygame.transform.smoothscale(
        source,
        (round(width * factor), round(height * factor)),
    )
    x = max(0, (scaled.get_width() - target_w) // 2)
    y = max(0, (scaled.get_height() - target_h) // 2)
    return scaled.subsurface((x, y, target_w, target_h)).copy()


def minas_playfield_crop(source: pygame.Surface) -> pygame.Surface:
    """Recorta a queda lateral que interrompia as pistas terrestres.

    O conceito original tem 1672x941. O retângulo 1450x816 preserva 16:9,
    mantém o visual anterior e encerra o campo antes da queda que cortava a
    quarta pista. A cachoeira distante permanece no fundo do cenário.
    """
    width, height = source.get_size()
    crop_w = min(width, round(height * 16 / 9))
    crop_w = min(crop_w, 1450)
    crop_h = min(height, round(crop_w * 9 / 16))
    cropped = source.subsurface((0, 0, crop_w, crop_h)).copy()
    return pygame.transform.smoothscale(cropped, SIZE)


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    total = 0
    # As versões anteriores continuam no disco para comparação.
    selected = (
        ROOT / "01_nova_york_terminal_helix_entrada_unica_v4.png",
        ROOT / "02_egito_escavacao_helix_entrada_unica_v4.png",
        ROOT / "03_minas_cachoeira_helix_entrada_unica_v4.png",
    )
    for path in selected:
        image = pygame.image.load(str(path)).convert_alpha()
        prepared = cover_crop(image)
        pygame.image.save(prepared, str(OUTPUT / path.name))
        total += 1
    pygame.quit()
    print(f"OK: {total} cenários preparados em 1280x720.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
