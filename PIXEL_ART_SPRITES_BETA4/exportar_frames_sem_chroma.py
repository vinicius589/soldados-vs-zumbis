"""Exporta cópias transparentes sem contaminar os sprites originais."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from laboratorio_animacoes import (
    CLEAN_FRAMES_ROOT,
    EXCLUDED_SHEET_KEYS,
    RAW_FRAMES_ROOT,
    load_frame,
    load_manifest,
)


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    manifest = load_manifest()
    exported = 0

    for sheet in manifest.get("sheets", []):
        sheet_key = str(sheet["key"])
        if sheet_key in EXCLUDED_SHEET_KEYS:
            continue
        for action in sheet["rows"]:
            source_dir = RAW_FRAMES_ROOT / sheet_key / str(action)
            destination = CLEAN_FRAMES_ROOT / sheet_key / str(action)
            destination.mkdir(parents=True, exist_ok=True)
            for source_path in sorted(source_dir.glob("frame_*.png")):
                cleaned = load_frame(source_path)
                # Os veículos originais estavam virados para a esquerda. No
                # jogo eles pertencem ao lado defensor; o trator avança e os
                # demais apontam da esquerda para a direita.
                if sheet_key == "veiculos":
                    cleaned = pygame.transform.flip(cleaned, True, False)
                pygame.image.save(cleaned, str(destination / source_path.name))
                exported += 1

    pygame.quit()
    print(f"OK: {exported} quadros transparentes exportados em {CLEAN_FRAMES_ROOT}.")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
