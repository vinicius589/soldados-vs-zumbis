"""Exporta as três entradas finais animadas para revisão visual."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from visualizar_cenarios import LANE_CENTERS, ScenarioGallery


ROOT = Path(__file__).resolve().parent


def export_scene(
    scene: int,
    filename: str,
    *,
    horde_active: bool = False,
    animate_horde: bool = False,
    boss_active: bool = False,
    animate_arrival: bool = False,
) -> Path:
    destination = ROOT / "qa" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    gallery = ScenarioGallery(headless=True, scene=scene)
    gallery.horde_active = horde_active or boss_active
    gallery.horde_flame = 0.0 if animate_horde else float(gallery.horde_active)
    gallery.boss_active = boss_active
    gallery.boss_timer = 0.0
    frames: list[Image.Image] = []
    for index in range(48):
        gallery.elapsed = index / 8.0
        if animate_horde:
            gallery.horde_flame = min(1.0, gallery.elapsed * 1.15)
        if animate_arrival:
            gallery.boss_timer = max(0.0, 3.2 - gallery.elapsed)
        gallery.draw()
        pixels = pygame.image.tobytes(gallery.screen, "RGB")
        image = Image.frombytes("RGB", gallery.screen.get_size(), pixels)
        # O recorte vertical completo mostra a entrada e seus efeitos próprios.
        # Minas mantém a água pintada no fundo, sem sobreposição animada.
        frames.append(image.crop((880, 68, 1280, 650)).convert("P", palette=Image.Palette.ADAPTIVE, colors=192))
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
    return destination


def export_generals(filename: str) -> Path:
    """Mostra lado a lado os três generais e a continência completa."""
    destination = ROOT / "qa" / filename
    gallery = ScenarioGallery(headless=True, scene=1)
    frames: list[Image.Image] = []
    for frame_index in range(48):
        strip = Image.new("RGB", (690, 362), (8, 10, 12))
        for scene_index in range(3):
            gallery.index = scene_index
            gallery.elapsed = frame_index / 8.0
            gallery.draw()
            pixels = pygame.image.tobytes(gallery.screen, "RGB")
            image = Image.frombytes("RGB", gallery.screen.get_size(), pixels)
            strip.paste(image.crop((0, 68, 230, 430)), (scene_index * 230, 0))
        frames.append(strip.convert("P", palette=Image.Palette.ADAPTIVE, colors=192))
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
    return destination


def export_defense_limits(filename: str) -> Path:
    """Prova que trator, drone, mina e VFX morrem no fim do terreno útil."""
    destination = ROOT / "qa" / filename
    frames: list[Image.Image] = []
    galleries = [ScenarioGallery(headless=True, scene=scene) for scene in (1, 2, 3)]
    for gallery in galleries:
        gallery.selected_lane = 1
    for frame_index in range(50):
        t = frame_index / 10.0
        strip = Image.new("RGB", (970, 300), (7, 8, 10))
        for scene_index, gallery in enumerate(galleries):
            gallery.elapsed = t
            gallery.defense_timer = t
            gallery.draw()
            pixels = pygame.image.tobytes(gallery.screen, "RGB")
            image = Image.frombytes("RGB", gallery.screen.get_size(), pixels)
            lane_y = LANE_CENTERS[gallery.kind][gallery.selected_lane]
            strip.paste(image.crop((150, lane_y - 50, 1120, lane_y + 50)), (0, scene_index * 100))
        frames.append(strip.convert("P", palette=Image.Palette.ADAPTIVE, colors=192))
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
        export_scene(1, "cidade_sem_fumaca_animada.gif"),
        export_scene(2, "piras_egito_animadas.gif", horde_active=True, animate_horde=True),
        export_scene(
            2,
            "chefe_egito_nevoa_piras.gif",
            horde_active=True,
            animate_horde=True,
            boss_active=True,
            animate_arrival=True,
        ),
        export_scene(3, "cenario_minas_sem_animacao_agua.gif"),
        export_scene(3, "chefe_minas_tempestade.gif", boss_active=True, animate_arrival=True),
        export_generals("generais_saudacao_regional.gif"),
        export_defense_limits("defesas_encerram_no_fim_da_pista.gif"),
    )
    for path in outputs:
        print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
