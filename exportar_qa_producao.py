"""Exporta quadros reais dos três mapas para revisão visual da produção."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame
from PIL import Image

from main import Battle, Game, REGION_ENEMIES, REGION_ROSTERS, SpawnOrder


OUTPUT = Path(__file__).resolve().parent / "visual_qa_beta4" / "producao_regional"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game()
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()

    for region in ("city", "desert", "beach"):
        selected = list(REGION_ROSTERS[region])
        battle = Battle(game, region, selected)
        battle.supplies = 999
        battle.intermission = 9999
        review_rows = (0, 3, 0) if region == "beach" else (0, 1, 2)
        for index, (row, col) in enumerate(zip(review_rows, (2, 3, 5))):
            battle.selected_card = index
            battle.place(row, col)
        for _ in range(210):
            battle.update(1 / 60)
            game.scenario_runtime.update(1 / 60, battle)
        for row, x, enemy_key in zip(
            review_rows,
            (805.0, 940.0, 1080.0),
            REGION_ENEMIES[region],
        ):
            battle.spawn_enemy(SpawnOrder(0.0, enemy_key, row))
            battle.enemies[-1].x = x
        # Passa do véu curto de entrada para que o quadro estático prove a
        # arte em opacidade total. O GIF continua registrando o movimento.
        for _ in range(42):
            battle.update(1 / 60)
            game.scenario_runtime.update(1 / 60, battle)
        game.region = region
        game.battle = battle
        game.scene = "battle"
        if region == "city":
            # O quadro oficial da cidade registra o apito na boca e a
            # onomatopeia sincronizada, não apenas a pose ociosa.
            game.scenario_runtime.elapsed = 2.05
        game.draw()
        pygame.image.save(game.world_surface, str(OUTPUT / f"partida_{region}.png"))

        # Prova animada de que o par regional permanece visível, proporcional
        # e preso às linhas durante vários quadros — não apenas numa captura.
        regional_frames: list[Image.Image] = []
        for _frame_number in range(24):
            battle.update(0.08)
            game.scenario_runtime.update(0.08, battle)
            game.draw()
            raw = pygame.image.tobytes(game.world_surface, "RGB")
            image = Image.frombytes("RGB", game.world_surface.get_size(), raw)
            regional_frames.append(image.resize((960, 540), Image.Resampling.LANCZOS))
        regional_frames[0].save(
            OUTPUT / f"integracao_{region}.gif",
            save_all=True,
            append_images=regional_frames[1:],
            duration=80,
            loop=0,
            optimize=False,
            disposal=2,
        )

        if region == "city":
            preview_frames: list[Image.Image] = []
            for frame_number in range(56):
                game.scenario_runtime.elapsed = frame_number * 0.08
                game.draw()
                raw = pygame.image.tobytes(game.world_surface, "RGB")
                image = Image.frombytes("RGB", game.world_surface.get_size(), raw)
                preview_frames.append(image.crop((0, 255, 250, 535)))
            preview_frames[0].save(
                OUTPUT / "tenente_cidade_apito.gif",
                save_all=True,
                append_images=preview_frames[1:],
                duration=80,
                loop=0,
                optimize=False,
                disposal=2,
            )

        game.battle = None
        game.scene = "characters"
        game.character_region = region
        for kind in ("units", "zombies"):
            game.dossier_kind = kind
            for index in range(len(game.character_keys())):
                game.character_index = index
                game.draw()
                pygame.image.save(
                    game.world_surface,
                    str(OUTPUT / f"personagem_{region}_{kind}_{index + 1}.png"),
                )

        # Segundo ensaio: somente os quatro soldados recém-integrados. O GIF
        # prova que as folhas novas chegam ao combate real, mantendo pés,
        # tamanho, recarga, dano e origem do projétil coerentes com o cenário.
        new_cards = list(REGION_ROSTERS[region])[3:]
        new_battle = Battle(game, region, new_cards)
        new_battle.supplies = 9999
        new_battle.intermission = 9999
        placements = (
            ((0, 2), (1, 2), (2, 2), (3, 2))
            if region != "beach"
            else ((0, 2), (0, 4), (3, 2), (3, 4))
        )
        for index, (row, col) in enumerate(placements):
            new_battle.selected_card = index
            new_battle.place(row, col)
            new_battle.defenders[-1].deployment_x = None
            new_battle.defenders[-1].deployment_target_x = None
        for index, defender in enumerate(new_battle.defenders):
            zombie_key = REGION_ENEMIES[region][index % 3]
            new_battle.spawn_enemy(SpawnOrder(0.0, zombie_key, defender.row))
            enemy = new_battle.enemies[-1]
            enemy.entry_reveal = 0.0
            enemy.age = 2.0
            if defender.stats["role"] == "suicide_bomber":
                enemy.x = defender.x + 112.0
            else:
                enemy.x = defender.x + min(float(defender.stats["range"]), 2.5) * 118
        game.battle = new_battle
        game.scene = "battle"
        new_frames: list[Image.Image] = []
        for _frame_number in range(72):
            new_battle.update(0.08)
            game.scenario_runtime.update(0.08, new_battle)
            game.draw()
            raw = pygame.image.tobytes(game.world_surface, "RGB")
            new_frames.append(
                Image.frombytes("RGB", game.world_surface.get_size(), raw).resize(
                    (960, 540), Image.Resampling.LANCZOS
                )
            )
        new_frames[0].save(
            OUTPUT / f"quatro_novos_soldados_{region}.gif",
            save_all=True,
            append_images=new_frames[1:],
            duration=80,
            loop=0,
            optimize=False,
            disposal=2,
        )

    game.scene = "title"
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / "menu_principal.png"))
    game.scene = "difficulty"
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / "dificuldades.png"))
    game.scene = "campaign"
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / "mapas.png"))
    game.enter_selection("city")
    game.draw()
    pygame.image.save(game.world_surface, str(OUTPUT / "selecao_cidade.png"))
    for page in range(3):
        game.story_page = page
        game.scene = "story"
        game.draw()
        pygame.image.save(game.world_surface, str(OUTPUT / f"historia_{page + 1}.png"))

    pygame.quit()
    print(f"QA_EXPORTADA: {OUTPUT}")


if __name__ == "__main__":
    main()
