"""Exporta a tempestade de areia usando o próprio render do testador."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from visualizar_cenarios import ScenarioGallery


def main() -> int:
    destination = Path(__file__).resolve().parent / "qa" / "animacao_deserto_tempestade.gif"
    destination.parent.mkdir(parents=True, exist_ok=True)
    gallery = ScenarioGallery(headless=True, scene=2)
    frames: list[Image.Image] = []
    for index in range(40):
        gallery.elapsed = index / 8.0
        gallery.draw()
        pixels = pygame.image.tobytes(gallery.screen, "RGB")
        raw = Image.frombytes("RGB", gallery.screen.get_size(), pixels)
        raw = raw.crop((720, 68, 1280, 290))
        frames.append(raw.convert("P", palette=Image.Palette.ADAPTIVE, colors=192))
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=125,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"OK: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
