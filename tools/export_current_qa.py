"""Renderiza as telas exatas alteradas nesta revisão visual da Beta 4."""

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

from main import CELL_W, Game, SpawnOrder


OUTPUT = ROOT / "visual_qa_beta4" / "revisao_atual"


def save(game: Game, name: str) -> None:
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / name))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game(integration_preview=True)
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()

    game.difficulty = "medium"
    game.enter_selection("beach")
    assert game.battle is not None
    battle = game.battle
    battle.intermission = 9999.0
    battle.supplies = 9999
    battle.selected_card = 0
    battle.place(0, 2)
    defender = battle.defenders[-1]
    defender.deployment_x = None
    defender.deployment_target_x = None
    for row in (0, 3):
        battle.spawn_enemy(SpawnOrder(0.0, "afogado_cachoeira", row))
        enemy = battle.enemies[-1]
        enemy.entry_reveal = 0.0
        enemy.age = 2.0
        enemy.x = defender.x + CELL_W * (3.1 if row == 0 else 4.1)
    # 1,3 s coincide com o quadro de susto e deixam a onomatopeia visível na
    # captura, permitindo validar posição ao lado da boca.
    for _ in range(80):
        game.scenario_runtime.update(1 / 60, battle)
        battle.update_production_animations(1 / 60)
    save(game, "cachoeira_alinhamento_escala.png")

    for kind, key, filename in (
        ("units", "marinheiro", "menu_marinheiro_inteiro.png"),
        ("zombies", "afogado_cachoeira", "menu_afogado_inteiro.png"),
        ("zombies", "corredor_cachoeira", "menu_corredor_inteiro.png"),
    ):
        game.scene = "characters"
        game.character_region = "beach"
        game.dossier_kind = kind
        game.character_index = game.character_keys().index(key)
        save(game, filename)

    pygame.quit()
    print(f"QA_ATUAL_EXPORTADA: {OUTPUT}")


if __name__ == "__main__":
    main()
