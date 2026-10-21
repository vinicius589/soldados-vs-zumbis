"""Remonta as folhas finais usando somente quadros com transparência real."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames_sem_chroma"
OUTPUT = ROOT / "final_sem_chroma"
MANIFEST = ROOT / "sheet_manifest.json"
EXCLUDED = {"ambiente"}


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sheet_count = 0
    frame_count = 0

    for spec in data["sheets"]:
        key = str(spec["key"])
        if key in EXCLUDED:
            continue
        actions = [str(action) for action in spec["rows"]]
        columns = int(spec["columns"])
        rows: list[list[pygame.Surface]] = []
        for action in actions:
            paths = sorted((FRAMES / key / action).glob("frame_*.png"))
            if len(paths) != columns:
                raise RuntimeError(f"{key}/{action}: {len(paths)} quadros; esperados {columns}.")
            rows.append([pygame.image.load(str(path)).convert_alpha() for path in paths])

        cell_width = max(frame.get_width() for row in rows for frame in row)
        cell_height = max(frame.get_height() for row in rows for frame in row)
        sheet = pygame.Surface((cell_width * columns, cell_height * len(rows)), pygame.SRCALPHA)
        sheet.fill((0, 0, 0, 0))
        for row_index, row in enumerate(rows):
            for column, frame in enumerate(row):
                cell = pygame.Rect(
                    column * cell_width,
                    row_index * cell_height,
                    cell_width,
                    cell_height,
                )
                sheet.blit(frame, frame.get_rect(midbottom=(cell.centerx, cell.bottom)))
                frame_count += 1

        filename = Path(str(spec["file"])).stem + "_transparente.png"
        OUTPUT.mkdir(parents=True, exist_ok=True)
        pygame.image.save(sheet, str(OUTPUT / filename))
        sheet_count += 1

    pygame.quit()
    print(f"OK: {sheet_count} folhas transparentes, {frame_count} quadros.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
