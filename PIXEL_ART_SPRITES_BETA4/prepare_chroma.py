"""Padroniza fundos de sprite sheets para chroma key RGB(0, 255, 0).

Imagens com transparência são compostas sobre verde puro. Imagens geradas com
um verde aproximado têm somente os grandes componentes verdes do fundo
normalizados, preservando cores verdes pequenas e isoladas dentro dos sprites.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame


CHROMA = (0, 255, 0, 255)


def _large_green_background(source: pygame.Surface) -> pygame.Mask:
    rgb = pygame.surfarray.array3d(source).astype(np.int16)
    alpha = pygame.surfarray.array_alpha(source)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    candidate = (
        (alpha >= 245)
        & (green >= 20)
        & (green >= red + 10)
        & (green >= blue + 10)
        & (green >= red * 2)
        & (green >= blue * 2)
    )

    mask_surface = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    mask_alpha = pygame.surfarray.pixels_alpha(mask_surface)
    mask_alpha[:] = candidate.astype(np.uint8) * 255
    del mask_alpha

    candidate_mask = pygame.mask.from_surface(mask_surface, threshold=127)
    background = pygame.Mask(source.get_size())
    # Cada célula pode estar cercada por uma linha escura. Por isso mantemos
    # todos os componentes grandes de verde, não apenas o que toca os cantos.
    for component in candidate_mask.connected_components(minimum=900):
        background.draw(component, (0, 0))
    return background


def normalize(source_path: Path, destination_path: Path) -> dict[str, float | int]:
    source = pygame.image.load(str(source_path)).convert_alpha()
    original_alpha = pygame.surfarray.array_alpha(source)

    output = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    output.fill(CHROMA)
    output.blit(source, (0, 0))

    background = _large_green_background(source)
    if background.count():
        overlay = background.to_surface(
            setcolor=CHROMA,
            unsetcolor=(0, 0, 0, 0),
        )
        output.blit(overlay, (0, 0))

    # Uma borda técnica de um pixel garante que ferramentas de chroma possam
    # amostrar qualquer canto da folha sem capturar uma linha de grade escura.
    pygame.draw.rect(output, CHROMA, output.get_rect(), width=1)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(output, str(destination_path))

    rgb = pygame.surfarray.array3d(output)
    alpha = pygame.surfarray.array_alpha(output)
    exact = (
        (rgb[:, :, 0] == 0)
        & (rgb[:, :, 1] == 255)
        & (rgb[:, :, 2] == 0)
        & (alpha == 255)
    )
    return {
        "width": output.get_width(),
        "height": output.get_height(),
        "source_transparent_percent": float((original_alpha < 8).mean() * 100.0),
        "exact_green_percent": float(exact.mean() * 100.0),
        "opaque_percent": float((alpha == 255).mean() * 100.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_mode((1, 1))
    stats = normalize(args.source, args.destination)
    pygame.quit()
    print(
        f"{args.destination.name}: {stats['width']}x{stats['height']} "
        f"green={stats['exact_green_percent']:.1f}% opaque={stats['opaque_percent']:.1f}%"
    )


if __name__ == "__main__":
    main()
