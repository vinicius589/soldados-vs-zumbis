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
    PROMOTIONS,
    REGION_ROSTERS,
    REGIONS,
    Assets,
    Battle,
    Defender,
    Enemy,
    Game,
    Projectile,
    SpawnOrder,
    boss_damage_scale,
    boss_wave_scale,
    cell_center,
    enemy_damage_scale,
    enemy_wave_scale,
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

    # The reconstructed package preloads its menu, three scenes, six regional
    # atlases (N1 and N2) and four scenario-specific containment devices before the menu
    # is made interactive.
    assert game.assets.total == 17
    assert all(f"{region}_bg" in game.assets.images for region in REGIONS)
    assert {"lane_bomb_cart", "desert_lane_bomb_cart", "beach_land_bomb_cart", "beach_water_bomb"} <= set(game.assets.images)
    assert all(region in game.assets.unit_sprites for region in REGIONS)
    assert all(region in game.assets.unit_l2_sprites for region in REGIONS)
    assert all(region in game.assets.zombie_sprites for region in REGIONS)
    assert all(len(sprites) == 12 for sprites in game.assets.unit_sprites.values())
    assert all(len(sprites) == 12 for sprites in game.assets.unit_l2_sprites.values())
    assert all(len(sprites) == 12 for sprites in game.assets.zombie_sprites.values())
    assert game.assets.unit("city", 3, 1) is not game.assets.unit("city", 3, 2)

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
    assert game.save["unlocked"] == list(REGIONS)
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
    # to the single central canal on the Beach. Four sand lanes remain usable
    # for ordinary troops, so sprites never stand on an unmarked water row.
    city.selected = [("lancha", "Lancha Patrulha")]
    assert not city.can_place("lancha", 0, 0)[0]
    beach = Battle(game, "beach", [("lancha", "Lancha Patrulha"), ("recruta", "Guarda-Costa Recruta")])
    beach.supplies = 999
    assert beach.can_place("lancha", 2, 2)[0]
    assert not beach.can_place("lancha", 0, 2)[0]
    assert not beach.can_place("lancha", 4, 2)[0]
    assert not beach.can_place("recruta", 2, 2)[0]
    assert beach.can_place("recruta", 0, 2)[0]

    # Containment is themed per region: City retains its urban cart, Desert
    # gets a dune charge, and Beach uses land carts plus a floating water buoy.
    desert = Battle(game, "desert", list(REGION_ROSTERS["desert"][:8]))
    assert city.lane_bomb_asset_key(0) == "lane_bomb_cart"
    assert desert.lane_bomb_asset_key(0) == "desert_lane_bomb_cart"
    assert beach.lane_bomb_asset_key(0) == "beach_land_bomb_cart"
    assert beach.lane_bomb_asset_key(2) == "beach_water_bomb"

    # A placed defender can be deliberately recovered by the removal tool,
    # and every lane starts with a one-use bomb cart as final protection.
    beach.selected_card = 1
    beach.place(0, 2)
    placed = beach.defenders[0]
    supplies_before_remove = beach.supplies
    beach.remove_defender(0, 2)
    assert not beach.defenders and beach.supplies > supplies_before_remove
    emergency = Enemy("caminhante", 0, ENEMIES["caminhante"], "beach", 1, x=BOARD.left + 5)
    beach.enemies = [emergency]
    beach.update_enemies(0.1)
    beach.update_lane_bombs(0.1)
    assert len(beach.lane_bombs) == 5 and beach.lane_bombs[0].state == "rolling"
    assert emergency not in beach.enemies

    # Pause freezes the simulation but remains immediately reversible through
    # the consolidated command shelf. The tactical-next button starts only an
    # intermission, never a second concurrent horde.
    frozen_intermission = beach.intermission
    beach.paused = True
    beach.update(0.5)
    assert beach.intermission == frozen_intermission
    beach.handle_click(beach.pause_rect().center)
    assert not beach.paused
    beach.handle_click(beach.next_wave_rect().center)
    assert beach.started_wave and beach.wave == 1

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

    # The new promotion card upgrades a nearby, real N1 card into the mapped
    # N2 card after its timer completes. It never grants the boss-only N3.
    promotion_field = Battle(game, "city", selection)
    instructor = Defender("instrutor", "Sargento", 1, 1, DEFENSES["instrutor"], 2)
    candidate = Defender("recruta", "Patrulheiro", 1, 2, DEFENSES["recruta"], 0)
    promotion_field.defenders = [instructor, candidate]
    instructor.utility_timer = 0
    promotion_field.update_defenders(0.1)
    assert PROMOTIONS["recruta"] == "soldado"
    assert candidate.key == "soldado" and candidate.stats["level"] == 2 and candidate.ascended == 0

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

    # The first City boss has a powerful arrival but cannot stun-lock the game:
    # its repeat is confined to its own lane, lasts 1.2 seconds, and waits 18 s.
    boss_city = Battle(game, "city", selection)
    lane_troop = Defender("recruta", "Patrulheiro", 1, 1, DEFENSES["recruta"], 0)
    other_troop = Defender("recruta", "Patrulheiro", 2, 1, DEFENSES["recruta"], 0)
    fixed_barrier = Defender("barreira", "Barreira", 1, 0, DEFENSES["barreira"], 10)
    hammer_boss = Enemy("bruto_demolidor", 1, BOSSES["bruto_demolidor"], "city", 5)
    boss_city.defenders = [lane_troop, other_troop, fixed_barrier]
    boss_city.enemies = [hammer_boss]
    boss_city.boss_entrance(hammer_boss)
    assert lane_troop.stun >= 3 and other_troop.stun >= 3 and fixed_barrier.stun == 0
    assert hammer_boss.skill_timer == 18.0
    lane_troop.stun = other_troop.stun = 0
    boss_city.boss_skill(hammer_boss)
    assert lane_troop.stun >= 1.2 and other_troop.stun == 0 and hammer_boss.skill_timer == 18.0

    # The centered red warning happens directly before a queued boss. The
    # spawn order remains held during the announcement, then the boss enters.
    alert_city = Battle(game, "city", selection)
    alert_city.wave = 5
    alert_city.started_wave = True
    alert_city.orders = [SpawnOrder(0.0, "bruto_demolidor", 1, True)]
    alert_city.spawn_timer = 0.0
    alert_city.update_wave(0.1)
    assert alert_city.boss_alert_pending and alert_city.boss_warning == 3.0 and not alert_city.enemies
    alert_city.boss_warning = 0.0
    alert_city.update_wave(0.1)
    assert not alert_city.boss_alert_pending and len(alert_city.enemies) == 1 and alert_city.enemies[0].is_boss

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

    # Difficulty starts below baseline and becomes more punishing by wave 15
    # in both durability and harm, rather than becoming easier after a few
    # rounds from excess supplies.
    early_walker = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 1)
    late_walker = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 15)
    assert early_walker.max_hp < ENEMIES["caminhante"]["hp"] < late_walker.max_hp

    # Bosses use their own gentler progression. Even the final boss remains
    # a meaningful encounter, rather than scaling as a normal horde sponge.
    assert boss_wave_scale(15) < enemy_wave_scale(15)
    assert boss_damage_scale(15) < enemy_damage_scale(15)
    boss_limits = {
        "bruto_demolidor": 1500,
        "comandante_mortos": 2100,
        "cuspidor_alfa": 3200,
        "mutante_ruinas": 1600,
        "necromante": 2300,
        "colosso_mutante": 3800,
        "tide_brute": 1550,
        "cacador_abissal": 2400,
        "leviata": 4200,
    }
    for boss_key, maximum_hp in boss_limits.items():
        wave = 5 if boss_key in {"bruto_demolidor", "mutante_ruinas", "tide_brute"} else (10 if boss_key in {"comandante_mortos", "necromante", "cacador_abissal"} else 15)
        assert Enemy(boss_key, 0, BOSSES[boss_key], "city", wave).max_hp <= maximum_hp

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
    game.handle_click(city.remove_rect().center)
    assert city.remove_mode
    game.handle_click(city.menu_rect().center)
    assert game.scene == "title" and game.battle is None

    pygame.quit()
    print("OK: reconstrução v7.4 inicializa, diferencia N1/N2, promove tropas e passa nas verificações táticas.")


if __name__ == "__main__":
    main()
