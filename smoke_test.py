"""Validação headless da integração mínima de produção da Beta 4."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from beta4_production_animations import ACTOR_SHEETS, ENEMY_ROSTER_ROWS
from main import (
    DEFENSES,
    DIFFICULTIES,
    ENEMIES,
    LANE_PROTECTION_END_X,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGIONS,
    VERSION,
    Battle,
    Game,
    SpawnOrder,
    cell_center,
)


EXPECTED = {
    "city": (
        ("xerife_rua", "agente_swat", "operador_radio_policial",
         "atirador_precisao_swat", "agente_entrada", "especialista_antipraga", "lancador_foguetes",
         "escudeiro_tropa_choque"),
        ("infectado_urbano", "corredor_cidade", "rastejador_cidade",
         "policial_helix", "cientista_helix", "tecnico_subestacao"),
        ("city_guard", "city_auto", "city_radio", "city_sniper", "city_entry", "city_antiplague", "city_rocket", "city_shield"),
        ("city_zombie_v2", "city_runner_v2", "city_crawler_v2",
         "city_police_infected", "city_scientist", "city_technician"),
    ),
    "desert": (
        ("pistoleiro_deserto", "fuzileiro_deserto", "torre_radio_egito",
         "atirador_horizonte", "tenente_artilheiro", "incinerador_deserto", "nomade_morteiro", "guardiao_laminas"),
        ("desperto_khepra", "corredor_deserto", "rastejador_deserto",
         "arqueiro_necropole", "hospedeiro_escaravelhos", "saqueador_canopico"),
        ("desert_guard", "desert_auto", "desert_radio", "desert_sniper", "desert_heavy", "desert_incinerator", "desert_mortar", "desert_blade"),
        ("desert_zombie_v2", "desert_runner_v2", "desert_crawler_v2",
         "desert_archer", "desert_beetle_host", "desert_looter"),
    ),
    "beach": (
        ("marinheiro", "fuzileiro_marinha", "estacao_comunicacao_cachoeira",
         "atirador_precisao_marinha", "bombeiro_hidraulico", "granadeiro_profundidades",
         "barco_patrulha", "submarino_tatico"),
        ("afogado_cachoeira", "corredor_cachoeira", "rastejador_cachoeira",
         "surfista", "mergulhador", "pescador_praga"),
        ("beach_guard", "beach_auto", "beach_radio", "beach_sniper", "beach_waterjet", "beach_grenadier",
         "beach_boat", "beach_sub"),
        ("beach_zombie_v2", "beach_runner_v2", "beach_crawler_v2",
         "beach_surfer", "beach_diver", "beach_fisher"),
    ),
}


def load_game() -> Game:
    game = Game()
    for _ in range(game.assets.total + 8):
        game.update(1 / 60)
        game.draw()
        if game.scene == "title":
            break
    assert game.scene == "title"
    assert game.assets.complete
    assert game.assets.production_clips is not None
    return game


def validate_animation_boxes(game: Game) -> None:
    clips = game.assets.production_clips
    assert clips is not None
    assert set(clips) == set(ACTOR_SHEETS) | set(ENEMY_ROSTER_ROWS)
    for actor, states in clips.items():
        kind = ACTOR_SHEETS[actor][1] if actor in ACTOR_SHEETS else ENEMY_ROSTER_ROWS[actor][2]
        if kind == "soldier":
            expected_states = {"move", "idle", "shoot", "reload", "hit"}
        elif kind == "support":
            expected_states = {"move", "idle", "support", "hit"}
        elif actor in ACTOR_SHEETS:
            expected_states = {"move", "idle", "bite", "hit"}
        else:
            expected_states = {"move", "idle", "bite", "hit", "skill"}
        assert set(states) == expected_states
        sizes = {
            frame.get_size()
            for clip in states.values()
            for frame in clip.frames
        }
        assert len(sizes) == 1, f"{actor} muda a caixa entre estados"
        for clip in states.values():
            assert len(clip.frames) in {2, 4, 8, 16}
            assert clip.duration > 0
            assert all(frame.get_bounding_rect(min_alpha=8).width > 0 for frame in clip.frames)


def validate_region(game: Game, region: str) -> None:
    defender_keys, zombie_keys, defender_actors, zombie_actors = EXPECTED[region]
    assert tuple(key for key, _display in REGION_ROSTERS[region]) == defender_keys
    assert REGION_ENEMIES[region] == zombie_keys
    assert len(REGIONS[region]["bosses"]) == 3

    game.enter_selection(region)
    assert game.scene == "battle"
    assert game.battle is not None
    assert tuple(key for key, _display in game.selection) == defender_keys
    assert tuple(game.battle.selected) == tuple(REGION_ROSTERS[region])
    for key in defender_keys:
        assert DEFENSES[key]["lore"]
        assert DEFENSES[key]["tactical_function"]
        assert DEFENSES[key]["mechanical_need"]
    battle = Battle(game, region, list(REGION_ROSTERS[region]))
    battle.supplies = 999
    battle.intermission = 9999
    row = 0 if region == "beach" else 1
    for index in range(3):
        battle.selected_card = index
        battle.place(row, 1 + index * 2)
    for index, zombie_key in enumerate(zombie_keys):
        enemy_row = battle.spawn_row_for(zombie_key)
        battle.spawn_enemy(SpawnOrder(0.0, zombie_key, enemy_row))
        battle.enemies[-1].x = 790.0 + index * 105
    defender, enemy = battle.defenders[0], battle.enemies[0]
    for index, actor in enumerate(defender_actors):
        key, display = REGION_ROSTERS[region][index]
        preview = Battle(game, region, [(key, display)])
        preview.supplies = 999
        target_row = 1 if key in {"barco_patrulha", "submarino_tatico"} else row
        preview.place(target_row, 2)
        assert preview.defenders[0].visual_animation is not None
        assert preview.defenders[0].visual_animation.animations == game.assets.production_clips[actor]
    for index, actor in enumerate(zombie_actors):
        assert battle.enemies[index].visual_animation is not None
        assert battle.enemies[index].visual_animation.animations == game.assets.production_clips[actor]
    expected_y = cell_center(row, 1, region)[1]
    assert defender.y == expected_y
    assert enemy.y == cell_center(enemy.row, 1, region)[1]

    for _ in range(190):
        battle.update(1 / 60)
    assert defender.deployed

    # A mordida é provada isoladamente para que os soldados do ensaio de
    # carga não eliminem o alvo antes de a máquina de estados ser observada.
    bite_battle = Battle(game, region, [REGION_ROSTERS[region][0]])
    bite_battle.supplies = 999
    bite_battle.selected_card = 0
    bite_battle.place(row, 2)
    bite_defender = bite_battle.defenders[0]
    bite_defender.deployment_x = None
    bite_defender.deployment_target_x = None
    bite_defender.attack_timer = 999
    bite_battle.spawn_enemy(SpawnOrder(0.0, zombie_keys[0], row))
    bite_enemy = bite_battle.enemies[0]
    bite_enemy.entry_reveal = 0.0
    bite_enemy.age = 2.0
    bite_enemy.x = bite_defender.x + 44
    bite_enemy.attack_timer = 0
    bite_battle.update_enemies(1 / 60)
    bite_battle.update_production_animations(1 / 60)
    assert bite_enemy.visual_animation.state == "bite"

    target = LANE_PROTECTION_END_X[region]
    if region != "beach":
        cart = battle.lane_bombs[0]
        battle.trigger_lane_bomb(0)
        for _ in range(180):
            battle.update_lane_bombs(1 / 60)
        assert cart.state == "spent"
        assert cart.x > target

    game.battle = battle
    game.scene = "battle"
    game.scenario_runtime.update(1 / 60, battle)
    game.draw()


def main() -> None:
    game = load_game()
    assert VERSION == "BETA 4"
    assert all("initial_cores" not in profile for profile in DIFFICULTIES.values())
    assert not hasattr(Battle, "core_rect")
    validate_animation_boxes(game)
    for region in EXPECTED:
        validate_region(game, region)

    game.enter_selection("beach")
    beach = Battle(game, "beach", game.selection.copy())
    for x in (410.0, 690.0, 950.0):
        beach.spawn_enemy(SpawnOrder(0.0, "mergulhador", 1))
        beach.enemies[-1].x = x
    assert beach.trigger_lane_bomb(1)
    assert beach.lane_bombs[1].state == "spent"
    assert not beach.enemies
    assert len(beach.effects) >= 7

    for scene in ("title", "difficulty", "campaign", "characters", "story", "settings", "howto"):
        game.scene = scene
        game.battle = None
        game.draw()

    pygame.quit()
    print("SMOKE_OK: Beta 4 regional, grade e inspeção validadas, counters ativos e gameplay estável.")


if __name__ == "__main__":
    main()
