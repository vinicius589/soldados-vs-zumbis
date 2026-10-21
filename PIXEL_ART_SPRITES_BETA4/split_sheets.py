"""Recorta as folhas finais em quadros individuais preservando o chroma key."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parent
FINAL = ROOT / "final"
FRAMES = ROOT / "frames"
MANIFEST = ROOT / "sheet_manifest.json"
CHROMA = (0, 255, 0, 255)
COMPONENT_AWARE_KEYS = {"zumbi_classico", "zumbi_mergulhador"}


def _remove_chroma(source: pygame.Surface) -> pygame.Surface:
    output = source.copy()
    pygame.transform.threshold(
        output,
        source,
        CHROMA,
        threshold=(112, 112, 112, 255),
        set_color=(0, 0, 0, 0),
        set_behavior=1,
        inverse_set=True,
    )
    return output


def _component_crop(source: pygame.Surface, component: pygame.Mask) -> pygame.Surface:
    boxes = component.get_bounding_rects()
    if not boxes:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    bounds = boxes[0]
    isolated = source.copy()
    component_alpha = component.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    isolated.blit(component_alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return isolated.subsurface(bounds).copy()


def split_component_aware(path: Path, key: str, columns: int, rows: list[str]) -> int:
    """Recorta pelo personagem, não pela célula onde ele vazou.

    Geradores de sprite sheet às vezes desenham uma lança ou uma perna alguns
    pixels dentro da célula anterior. Aqui cada uma das seis silhuetas completas
    é identificada como um componente, extraída inteira e recentralizada dentro
    de sua célula de destino com escala constante ao longo da mesma animação.
    """
    image = pygame.image.load(str(path)).convert_alpha()
    width, height = image.get_size()
    count = 0

    for row_index, action in enumerate(rows):
        y0 = round(row_index * height / len(rows))
        y1 = round((row_index + 1) * height / len(rows))
        row = _remove_chroma(image.subsurface((0, y0, width, y1 - y0)).copy())
        components = pygame.mask.from_surface(row, threshold=1).connected_components(minimum=80)
        if len(components) < columns:
            raise RuntimeError(
                f"{key}/{action}: apenas {len(components)} silhuetas; esperadas {columns}."
            )
        primary = sorted(components, key=pygame.mask.Mask.count, reverse=True)[:columns]
        primary.sort(key=lambda item: item.get_bounding_rects()[0].centerx)
        crops = [_component_crop(row, component) for component in primary]

        destination = FRAMES / key / action
        destination.mkdir(parents=True, exist_ok=True)
        cell_widths = [
            round((column + 1) * width / columns) - round(column * width / columns)
            for column in range(columns)
        ]
        cell_height = y1 - y0
        largest_width = max(crop.get_width() for crop in crops)
        largest_height = max(crop.get_height() for crop in crops)
        factor = min(
            (min(cell_widths) - 16) / largest_width,
            (cell_height - 12) / largest_height,
        )

        for column, crop in enumerate(crops):
            frame = pygame.Surface((cell_widths[column], cell_height), pygame.SRCALPHA)
            frame.fill(CHROMA)
            size = (
                max(1, round(crop.get_width() * factor)),
                max(1, round(crop.get_height() * factor)),
            )
            scaled = pygame.transform.scale(crop, size)
            frame.blit(scaled, scaled.get_rect(midbottom=(frame.get_width() // 2, frame.get_height() - 4)))
            pygame.image.save(frame, str(destination / f"frame_{column:02d}.png"))
            count += 1
    return count


def split_sheet(path: Path, key: str, columns: int, rows: list[str]) -> int:
    if key in COMPONENT_AWARE_KEYS:
        return split_component_aware(path, key, columns, rows)
    image = pygame.image.load(str(path)).convert_alpha()
    width, height = image.get_size()
    count = 0

    for row_index, action in enumerate(rows):
        y0 = round(row_index * height / len(rows))
        y1 = round((row_index + 1) * height / len(rows))
        destination = FRAMES / key / action
        destination.mkdir(parents=True, exist_ok=True)

        for column in range(columns):
            x0 = round(column * width / columns)
            x1 = round((column + 1) * width / columns)
            frame = image.subsurface((x0, y0, x1 - x0, y1 - y0)).copy()
            pygame.image.save(frame, str(destination / f"frame_{column:02d}.png"))
            count += 1
    return count


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total = 0

    for spec in data["sheets"]:
        path = FINAL / spec["file"]
        if not path.is_file():
            raise FileNotFoundError(f"Folha ausente: {path}")
        count = split_sheet(path, spec["key"], int(spec["columns"]), list(spec["rows"]))
        total += count
        print(f"{spec['key']}: {count} quadros")

    pygame.quit()
    print(f"Total: {total} quadros salvos em {FRAMES}")


if __name__ == "__main__":
    main()
