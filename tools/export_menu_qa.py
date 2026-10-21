"""Exporta as telas críticas do menu sem abrir uma janela interativa."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import Game


OUTPUT = ROOT / "visual_qa_beta4" / "menu_e_personagens"


def save(game: Game, filename: str) -> None:
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / filename))


def show_character(
    game: Game,
    region: str,
    kind: str,
    key: str,
    filename: str,
) -> None:
    game.scene = "characters"
    game.character_region = region
    game.dossier_kind = kind
    keys = game.character_keys()
    game.character_index = keys.index(key)
    save(game, filename)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game()
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()

    game.enter_selection("beach")
    save(game, "selecao_cachoeira.png")
    game.selection_inspect_key = "homem_bomba"
    save(game, "detalhes_homem_bomba.png")

    show_character(game, "city", "units", "escudeiro_tropa_choque", "personagem_escudeiro.png")
    show_character(game, "beach", "units", "homem_bomba", "personagem_homem_bomba.png")
    show_character(game, "beach", "units", "operador_sonar", "personagem_sonar.png")
    show_character(game, "beach", "units", "submarino_tatico", "personagem_submarino.png")

    for region, keys in {
        "city": ("infectado_urbano", "bruto", "bruto_demolidor"),
        "desert": ("desperto_khepra", "parasita", "mutante_ruinas"),
        "beach": ("afogado_cachoeira", "baiacu_mutante", "leviata"),
    }.items():
        for key in keys:
            show_character(
                game,
                region,
                "zombies",
                key,
                f"personagem_{region}_{key}.png",
            )

    pygame.quit()
    print(f"QA_MENU_EXPORTADA: {OUTPUT}")


if __name__ == "__main__":
    main()
