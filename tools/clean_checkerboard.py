"""Remove um fundo xadrez claro que foi rasterizado em um PNG.

O script não tenta adivinhar o objeto pelo nome. Ele classifica pixels claros e
quase neutros, mantém apenas o componente conectado às bordas da imagem e torna
esse componente transparente. Assim, áreas claras fechadas dentro do objeto
continuam preservadas.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame


def clean(source_path: Path, destination_path: Path) -> tuple[int, int, int]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    image = pygame.image.load(str(source_path)).convert_alpha()
    rgb = pygame.surfarray.array3d(image).astype(np.int16)
    brightness = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)

    # O fundo do gerador varia entre branco e cinza azulado. A combinação de
    # brilho e baixa saturação o identifica sem apagar pele, ferrugem ou algas.
    candidate = (brightness >= 138) & (chroma <= 34)
    candidate_surface = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    candidate_alpha = pygame.surfarray.pixels_alpha(candidate_surface)
    candidate_alpha[:] = candidate.astype(np.uint8) * 255
    del candidate_alpha

    candidate_mask = pygame.mask.from_surface(candidate_surface, threshold=127)
    seeds = (
        (0, 0),
        (image.get_width() - 1, 0),
        (0, image.get_height() - 1),
        (image.get_width() - 1, image.get_height() - 1),
    )
    background = pygame.Mask(image.get_size())
    for seed in seeds:
        if candidate_mask.get_at(seed):
            background.draw(candidate_mask.connected_component(seed), (0, 0))

    background_surface = background.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(0, 0, 0, 0),
    )
    background_alpha = pygame.surfarray.array_alpha(background_surface)
    alpha = pygame.surfarray.pixels_alpha(image)
    removed = int((background_alpha > 127).sum())
    alpha[background_alpha > 127] = 0
    del alpha

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(image, str(destination_path))
    opaque = int((pygame.surfarray.array_alpha(image) > 8).sum())
    pygame.quit()
    return image.get_width() * image.get_height(), removed, opaque


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    total, removed, opaque = clean(args.source, args.destination)
    print(f"total={total} removed={removed} opaque={opaque} output={args.destination}")


if __name__ == "__main__":
    main()
