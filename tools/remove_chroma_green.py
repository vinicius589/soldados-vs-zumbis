"""Converte um fundo verde técnico conectado às bordas em transparência."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame


def clean(source: Path, destination: Path) -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    image = pygame.image.load(str(source)).convert_alpha()
    rgb = pygame.surfarray.array3d(image).astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    candidate = (green >= 150) & (green - red >= 72) & (green - blue >= 54)

    surface = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    alpha = pygame.surfarray.pixels_alpha(surface)
    alpha[:] = candidate.astype(np.uint8) * 255
    del alpha
    candidates = pygame.mask.from_surface(surface, threshold=127)
    background = pygame.Mask(image.get_size())
    seeds = (
        (0, 0),
        (image.get_width() - 1, 0),
        (0, image.get_height() - 1),
        (image.get_width() - 1, image.get_height() - 1),
    )
    for seed in seeds:
        if candidates.get_at(seed):
            background.draw(candidates.connected_component(seed), (0, 0))

    background_surface = background.to_surface(
        setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)
    )
    remove = pygame.surfarray.array_alpha(background_surface) > 127
    image_alpha = pygame.surfarray.pixels_alpha(image)
    image_alpha[remove] = 0
    del image_alpha
    destination.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(image, str(destination))
    pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    clean(args.source, args.destination)


if __name__ == "__main__":
    main()
