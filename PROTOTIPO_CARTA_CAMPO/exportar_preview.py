"""Exporta uma prévia acelerada do ensaio sem alterar sua física por dt."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from prototipo_carta_campo import Prototype


ROOT = Path(__file__).resolve().parent


def main() -> int:
    destination = ROOT / "preview_carta_tropa_zumbi.gif"
    prototype = Prototype(headless=True)
    frames: list[Image.Image] = []
    # Doze segundos reais representados em 96 quadros: a cadência do jogo não
    # muda e a prévia continua leve o bastante para abrir no explorador.
    dt = 0.125
    for _ in range(96):
        prototype.update_demo(dt)
        prototype.update(dt)
        prototype.draw()
        pixels = pygame.image.tobytes(prototype.screen, "RGB")
        frame = Image.frombytes("RGB", prototype.screen.get_size(), pixels)
        # Redução apenas para a prévia; a janela executável permanece 1280x720.
        frame = frame.resize((800, 450), Image.Resampling.LANCZOS)
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=160))
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=125,
        loop=0,
        optimize=False,
        disposal=2,
    )
    pygame.quit()
    print(f"OK: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
