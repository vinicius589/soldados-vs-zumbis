"""Checks without opening a visible window.

Run with: python smoke_test.py
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from main import (
    BOARD,
    BOSSES,
    DEFENSES,
    ENEMIES,
    REGION_ROSTERS,
    REGIONS,
    Assets,
    Battle,
    Defender,
    Enemy,
    Game,
    Projectile,
    cell_center,
)


def load_to_title(game: Game) -> None:
    assert game.scene == "loading"
    for _ in range(game.assets.total + 3):
        game.update(1 / 60)
        game.draw()
        if game.scene == "title":
            break
    assert game.scene == "title"
    assert game.assets.complete


def main() -> None:
    game = Game()
    load_to_title(game)

    # The reconstructed package preloads exactly its new menu, three scenes
    # and the six regional atlases before the menu is made interactive.
    assert game.assets.total == 10
    assert all(f"{region}_bg" in game.assets.images for region in REGIONS)
    assert all(region in game.assets.unit_sprites for region in REGIONS)
    assert all(region in game.assets.zombie_sprites for region in REGIONS)
    assert all(len(sprites) == 12 for sprites in game.assets.unit_sprites.values())
    assert all(len(sprites) == 12 for sprites in game.assets.zombie_sprites.values())

    # Ground anchors keep every combat lane over terrain rather than the sky.
    city_left = cell_center(0, 0, "city")
    city_right = cell_center(0, 8, "city")
    beach_top = cell_center(0, 4, "beach")
    assert city_left[1] >= 300 and city_right[1] == city_left[1]
    assert beach_top[1] >= 300

    # The campaign intentionally has City, Desert and Beach only. Snow and
    # grass are not part of its regions, enemy families or asset loading.
    assert tuple(REGIONS) == ("city", "desert", "beach")
    assert "snow" not in REGIONS and "grass" not in REGIONS
    assert all(len(roster) >= 10 for roster in REGION_ROSTERS.values())
    assert all(key in DEFENSES for roster in REGION_ROSTERS.values() for key, _ in roster)

    # All regions have a 15-wave director and boss milestones at 5, 10, 15.
    selection = list(REGION_ROSTERS["city"][:8])
    city = Battle(game, "city", selection)
    first_wave = city.build_wave(1)
    final_wave = city.build_wave(15)
    assert len(first_wave) < len(final_wave)
    for wave, boss_key in zip((5, 10, 15), REGIONS["city"]["bosses"]):
        wave_orders = city.build_wave(wave)
        assert any(order.boss and order.key == boss_key for order in wave_orders)
        assert boss_key in BOSSES

    # Aquatic cards are selectable anywhere but placement remains restricted
    # to the beach's water rows; ordinary land troops cannot occupy that water.
    city.selected = [("lancha", "Lancha Patrulha")]
    assert not city.can_place("lancha", 0, 0)[0]
    beach = Battle(game, "beach", [("lancha", "Lancha Patrulha"), ("recruta", "Guarda-Costa Recruta")])
    beach.supplies = 999
    assert beach.can_place("lancha", 2, 2)[0]
    assert not beach.can_place("lancha", 4, 2)[0]
    assert not beach.can_place("recruta", 2, 2)[0]

    # Gun ammunition is finite and comes back only through a neighboring
    # support role. This checks the rigid external-reload rule directly.
    recruit = Defender("recruta", "Recruta", 0, 1, DEFENSES["recruta"], 0)
    mechanic = Defender("mecanico", "Mecânico", 0, 0, DEFENSES["mecanico"], 6)
    recruit.ammo = 0
    city.defenders = [recruit, mechanic]
    city.update_defenders(0.1)
    assert recruit.ammo > 0
    city.defenders = [recruit]
    recruit.ammo = 0
    before = recruit.ammo
    city.update_defenders(0.1)
    assert recruit.ammo == before

    # A boss drops a bounded temporary N3 core, which then refills ammunition
    # and sets a timed ascension rather than permanently changing a card.
    boss = Enemy("bruto_demolidor", 0, BOSSES["bruto_demolidor"], "city", 5)
    city.enemies = [boss]
    city.kill_enemy(boss)
    assert city.cores == 1
    city.defenders = [recruit]
    city.use_core = True
    recruit.ammo = 0
    city.apply_core(0, 1)
    assert recruit.ascended > 0 and recruit.ammo == recruit.max_ammo and city.cores == 0

    # Ascended N2 engineering deploys an infinite-ammo turret in front of the
    # engineer while also retaining the external-reload role.
    engineer = Defender("engenheiro", "Engenheiro", 1, 1, DEFENSES["engenheiro"], 6)
    engineer.ascended = 5.0
    engineering_target = Enemy("caminhante", 1, ENEMIES["caminhante"], "city", 5, x=engineer.x + 3 * (BOARD.width / 9))
    city.defenders = [engineer]
    city.enemies = [engineering_target]
    city.projectiles = []
    city.update_defenders(0.1)
    assert any(projectile.kind == "turret" for projectile in city.projectiles)

    # Regression for the crash reported during live play: a legacy positional
    # effect must never turn projectile.elapsed into a string.
    legacy = Projectile(100, 320, None, 300, 320, 10, "mortar", None, 40, True, 0.2, "mortar")
    assert legacy.elapsed == 0.0 and legacy.effect == "mortar"
    city.projectiles = [legacy]
    city.update_projectiles(0.1)
    assert legacy.elapsed == 0.1

    # Enemy themes contain concrete abilities rather than display-only names.
    assert "acid" in ENEMIES["cuspidor"]["tags"]
    assert "dig" in ENEMIES["digger"]["tags"]
    assert "steal" in ENEMIES["ladrao"]["tags"]
    assert "dash" in ENEMIES["surfista"]["tags"]
    assert "leviathan" == BOSSES["leviata"]["type"]

    # Every visible screen can render after the staged cache is ready.
    game.scene = "campaign"
    game.draw()
    game.enter_selection("city")
    game.draw()
    game.scene, game.dossier_kind = "dossier_units", "units"
    game.draw()
    game.scene, game.dossier_kind = "dossier_zombies", "zombies"
    game.draw()
    game.scene = "howto"
    game.draw()
    game.battle = city
    game.scene = "battle"
    game.draw()

    pygame.quit()
    print("OK: reconstrução v7.1 inicializa, carrega artes e passa nas verificações táticas.")


if __name__ == "__main__":
    main()
