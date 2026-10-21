"""Auditoria técnica da coleção final de sprite sheets."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parent


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    manifest = json.loads((ROOT / "sheet_manifest.json").read_text(encoding="utf-8"))
    chroma = (*manifest["chroma_key"], 255)
    problems: list[str] = []
    expected_frames = 0

    for spec in manifest["sheets"]:
        path = ROOT / "final" / spec["file"]
        if not path.is_file():
            problems.append(f"Folha ausente: {path.name}")
            continue

        image = pygame.image.load(str(path)).convert_alpha()
        width, height = image.get_size()
        corners = (
            image.get_at((0, 0)),
            image.get_at((width - 1, 0)),
            image.get_at((0, height - 1)),
            image.get_at((width - 1, height - 1)),
        )
        if any(tuple(color) != chroma for color in corners):
            problems.append(f"{path.name}: canto fora do chroma {chroma}")

        alpha = pygame.surfarray.array_alpha(image)
        if int(alpha.min()) != 255 or int(alpha.max()) != 255:
            problems.append(f"{path.name}: a folha deveria ser totalmente opaca")

        expected_frames += len(spec["rows"]) * int(spec["columns"])

    actual_frames = len(list((ROOT / "frames").rglob("frame_*.png")))
    if actual_frames != expected_frames:
        problems.append(
            f"Contagem de quadros: esperado {expected_frames}, encontrado {actual_frames}"
        )

    pygame.quit()
    print(f"Folhas verificadas: {len(manifest['sheets'])}")
    print(f"Quadros esperados: {expected_frames}")
    print(f"Quadros encontrados: {actual_frames}")
    print(f"Problemas: {len(problems)}")
    for problem in problems:
        print(f"- {problem}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
