"""Exporta GIFs separados para julgar tiro/recarga e mordida/dano."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from prototipo_combate import CombatPrototype


ROOT = Path(__file__).resolve().parent


def export(mode: str, filename: str, seconds: float) -> Path:
    destination = ROOT / filename
    prototype = CombatPrototype(headless=True, mode=mode)
    frames: list[Image.Image] = []
    dt = 0.1
    for _ in range(round(seconds / dt)):
        prototype.update(dt)
        prototype.draw()
        pixels = pygame.image.tobytes(prototype.screen, "RGB")
        frame = Image.frombytes("RGB", prototype.screen.get_size(), pixels)
        frame = frame.resize((800, 450), Image.Resampling.LANCZOS)
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=160))
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=False,
        disposal=2,
    )
    pygame.quit()
    return destination


def main() -> int:
    outputs = (
        export("fire", "preview_tiro_recarga_dano_zumbi.gif", 9.2),
        export("bite", "preview_mordida_dano_soldado.gif", 7.2),
    )
    for path in outputs:
        print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
