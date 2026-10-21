"""Non-interactive gameplay checks for a fresh Soldados vs Zumbis package."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from main import (
    BOARD_X,
    BOARD_Y,
    CELL_H,
    CELL_W,
    BOSS_DATA,
    Defender,
    Game,
    MISSIONS,
    STARTING_SUPPLIES,
    UNIT_DATA,
    WAVE_PROFILES,
    ZOMBIE_DATA,
    Zombie,
)


def main():
    game = Game()

    # The campaign intentionally contains only City, Desert and Beach.  Their
    # scenes, containment mine and generated direct regional sprites load.
    assert len(MISSIONS) == 3
    assert [mission["code"] for mission in MISSIONS] == ["city", "desert", "beach"]
    assert "operador_criogenico" not in UNIT_DATA
    assert "frostborn" not in ZOMBIE_DATA
    assert len(game.assets["units"]) == 26
    assert len(game.assets["zombies"]) == 22
    assert all(game.assets["scenes"].get(key) for key in ("city", "desert", "beach"))
    assert game.assets.get("menu_hero")
    assert all(game.assets["regional_units"]["recruta"].get(code) for code in ("city", "desert", "beach"))
    assert all(game.assets["regional_zombies"]["caminhante"].get(code) for code in ("city", "desert", "beach"))
    assert all(layer.get_size() == (CELL_W * 9, CELL_H * 5) for layer in game.ground_layers.values())
    assert game.assets["props"].get("mina_contencao")
    assert all(game.assets["effects"].get(key) for key in ("muzzle", "grenade", "explosion", "flame", "heal", "water_splash"))

    # Generic pre-match upgrades no longer exist. Every operation has 15
    # waves and exactly three named boss milestones instead.
    assert not hasattr(game, "upgrades")
    assert not hasattr(Game, "draw_upgrades")
    assert len(WAVE_PROFILES) == 15
    assert all(set(mission["bosses"]) == {5, 10, 15} for mission in MISSIONS)
    assert all(boss_id in BOSS_DATA for mission in MISSIONS for boss_id in mission["bosses"].values())
    assert WAVE_PROFILES[0]["count"] < WAVE_PROFILES[-1]["count"]
    assert WAVE_PROFILES[0]["hp"] < WAVE_PROFILES[-1]["hp"]
    assert WAVE_PROFILES[0]["damage"] < WAVE_PROFILES[-1]["damage"]

    # The opening is a real loading screen, followed by the menu. Each map
    # offers more than ten contextual cards, while a player chooses only 8.
    assert game.scene == "loading"
    game.update(game.loading_duration + .1)
    assert game.scene == "title"
    assert all(len(mission["units"]) >= 10 for mission in MISSIONS)
    assert all(all(key in mission["unit_names"] for key in mission["units"]) for mission in MISSIONS)
    assert all(all(key in mission["zombie_abilities"] for key in mission["pool"]) for mission in MISSIONS)
    for stage in range(len(MISSIONS)):
        game.start_selection(stage)
        assert all(game.unit_image(key).get_width() > 0 for key in game.available_units())
        assert all(game.zombie_image(key).get_width() > 0 for key in game.mission()["pool"])
        game.draw()
    game.start_selection(0)
    for key in game.available_units()[:9]:
        game.click_selection(game.selection_rect(game.available_units().index(key)).center)
    assert len(game.selection) == 8
    assert game.selection == game.available_units()[:8]

    # The city placement cells follow the narrowing avenue. Aquatic cards
    # stay invalid there and work only on a Beach tide lane.
    game.stage = 0
    top_left = game.cell_rect(0, 0)
    bottom_left = game.cell_rect(4, 0)
    assert top_left.left > bottom_left.left and top_left.right < game.cell_rect(4, 8).right
    assert game.board_cell(top_left.center) == (0, 0)
    assert game.board_cell(bottom_left.center) == (4, 0)
    assert "lancha_patrulha" not in game.available_units()
    game.selection = ["lancha_patrulha"]
    game.begin_game()
    assert game.supplies == STARTING_SUPPLIES[0]
    game.selected_card = "lancha_patrulha"
    game.click_game((BOARD_X + CELL_W // 2, BOARD_Y + CELL_H // 2))
    assert not game.defenders

    game.stage = 2
    assert "lancha_patrulha" in game.available_units()
    game.selection = ["lancha_patrulha", "fuzileiro"]
    game.begin_game()
    game.selected_card = "lancha_patrulha"
    game.click_game((BOARD_X + CELL_W // 2, BOARD_Y + CELL_H + CELL_H // 2))
    assert len(game.defenders) == 1 and game.defenders[0].key == "lancha_patrulha"
    assert game.defenders[0].hp == UNIT_DATA["lancha_patrulha"]["hp"]

    # Supply cards keep their deliberate economic tiers; the basic radio is
    # affordable rather than a mandatory expensive purchase.
    assert UNIT_DATA["operador_radio"]["cost"] == 85
    assert UNIT_DATA["batedor_suprimentos"]["income"] < UNIT_DATA["operador_radio"]["income"] < UNIT_DATA["torre_radio"]["income"] < UNIT_DATA["central_comando"]["income"]
    game.stage = 0
    game.selection = ["operador_radio"]
    game.begin_game()
    game.defenders = [Defender("operador_radio", 0, 0, UNIT_DATA["operador_radio"]["hp"], cooldown=0)]
    before_income = game.supplies
    game.update_defenders(0)
    assert game.supplies == before_income + UNIT_DATA["operador_radio"]["income"]

    # A low-cost recruit begins as a slow two-cell defender. Its actual range
    # changes only after a visible field promotion.
    game.stage = 0
    recruit = Defender("recruta", 0, 0, UNIT_DATA["recruta"]["hp"], cooldown=0)
    origin_x = game.cell_center(0, 0)[0]
    game.defenders, game.projectiles = [recruit], []
    game.zombies = [game.make_zombie("caminhante", 0, origin_x + 260)]
    game.update_defenders(0)
    assert not game.projectiles
    game.zombies = [game.make_zombie("caminhante", 0, origin_x + 160)]
    game.update_defenders(0)
    assert game.projectiles
    assert UNIT_DATA["vanguardista"]["hp"] > 900 and UNIT_DATA["vanguardista"]["damage"] < UNIT_DATA["fuzileiro"]["damage"]

    # Boss medals flow through the physical Instructor card into a unit rank.
    trainer = Defender("instrutor_tatico", 0, 0, UNIT_DATA["instrutor_tatico"]["hp"], cooldown=0)
    recruit = Defender("recruta", 0, 1, UNIT_DATA["recruta"]["hp"])
    game.defenders = [trainer, recruit]
    game.medals = 1
    game.update_defenders(0)
    assert recruit.rank == 2 and game.medals == 0
    assert game.defender_range(recruit) > UNIT_DATA["recruta"]["range"]

    # The Engineer physically deploys a hidden turret one cell forward and
    # the Engineer card can then reclaim that same turret for supplies.
    game.selection = ["engenheiro"]
    game.begin_game()
    game.supplies = 999
    game.selected_card = "engenheiro"
    engineer_cell = game.cell_rect(0, 0).center
    game.click_game(engineer_cell)
    game.update_defenders(0)
    turret = next((d for d in game.defenders if d.key == "torreta_engenheiro"), None)
    assert turret and (turret.row, turret.col, turret.owner) == (0, 1, (0, 0))
    before_reclaim = game.supplies
    game.selected_card = "engenheiro"
    game.click_game(game.cell_rect(turret.row, turret.col).center)
    assert all(d.key != "torreta_engenheiro" for d in game.defenders)
    assert game.supplies == before_reclaim + 30

    # The first victory unlocks Desert; then Desert unlocks Beach.
    game.stage = 0
    game.progress = 1
    game.save_progress = lambda: None
    game.victory()
    assert game.progress == 2
    game.end_state = None
    game.stage = 1
    game.victory()
    assert game.progress == 3

    # Bombardiers cannot fill a row even with plenty of supplies.
    game.stage = 1
    game.selection = ["bombardeiro"]
    game.begin_game()
    game.supplies = 999
    game.selected_card = "bombardeiro"
    game.click_game((BOARD_X + CELL_W // 2, BOARD_Y + CELL_H // 2))
    game.card_cooldowns["bombardeiro"] = 0
    game.selected_card = "bombardeiro"
    game.click_game((BOARD_X + CELL_W + CELL_W // 2, BOARD_Y + CELL_H // 2))
    assert len(game.defenders) == 1

    # Contextual abilities are mechanical, not only card text: Spitters hit
    # from range and a desert Toxic enemy leaves a poison debuff on contact.
    game.defenders = [Defender("fuzileiro", 0, 0, UNIT_DATA["fuzileiro"]["hp"])]
    spitter = game.make_zombie("cuspidor", 0, BOARD_X + 210)
    game.zombies = [spitter]
    before = game.defenders[0].hp
    game.update_zombies(1.4)
    assert game.defenders[0].hp < before
    game.stage = 1
    game.defenders = [Defender("fuzileiro", 0, 0, UNIT_DATA["fuzileiro"]["hp"])]
    toxic = game.make_zombie("toxico", 0, game.cell_rect(0, 0).right + 40)
    game.zombies = [toxic]
    game.update_zombies(1.0)
    assert game.defenders[0].poison > 0

    # The boss queue reaches wave 5, casts a real debuff, and rewards medals
    # only when killed. Late spawns also retain their larger health scale.
    game.stage = 0
    game.wave = 4
    game.next_wave()
    assert game.wave == 5 and game.queue[0][1] == "city_demolisher"
    boss = game.make_zombie("bruto", 0, game.cell_rect(0, 0).right + 40, boss_id="city_demolisher")
    game.defenders = [Defender("fuzileiro", 0, 0, UNIT_DATA["fuzileiro"]["hp"])]
    game.zombies = [boss]
    boss.boss_power_timer = 0
    game.update_zombies(0)
    assert game.defenders[0].stun > 0
    medal_before = game.medals
    game.kill_zombie(boss)
    assert game.medals == medal_before + BOSS_DATA["city_demolisher"]["medals"]

    # Every boss power in the campaign has an executable in-game effect, not
    # merely a description stored in BOSS_DATA.
    boss_stages = {
        "city_commander": 0, "city_colossus": 0,
        "desert_sandmaw": 1, "desert_oracle": 1, "desert_titan": 1,
        "beach_tidebrute": 2, "beach_captain": 2, "beach_leviathan": 2,
    }
    for boss_id, stage in boss_stages.items():
        game.stage = stage
        spec = BOSS_DATA[boss_id]
        row = 1 if stage == 2 and ZOMBIE_DATA[spec["sprite"]].get("aquatic") else 0
        defender = Defender("fuzileiro", row, 0, UNIT_DATA["fuzileiro"]["hp"])
        enemy = game.make_zombie(spec["sprite"], row, game.cell_rect(row, 0).right + 40, boss_id=boss_id)
        game.defenders, game.zombies = [defender], [enemy]
        if spec["power"] == "rally":
            ally = game.make_zombie("caminhante", row, enemy.x + 35)
            game.zombies.append(ally)
        before_count, before_hp = len(game.zombies), defender.hp
        game.cast_boss_power(enemy)
        if spec["power"] == "rally":
            assert game.zombies[1].rally > 0
        elif spec["power"] == "summon":
            assert len(game.zombies) >= before_count + 2
        elif spec["power"] in {"corrosion"}:
            assert defender.poison > 0 and defender.hp < before_hp
        else:
            assert defender.stun > 0 or defender.hp < before_hp
    game.wave_profile = WAVE_PROFILES[0]
    early = game.make_zombie("feral", 0, BOARD_X + 600)
    game.wave_profile = WAVE_PROFILES[-1]
    late = game.make_zombie("feral", 0, BOARD_X + 700)
    assert early.max_hp < ZOMBIE_DATA["feral"]["hp"] < late.max_hp

    # A breached lane first consumes its dedicated containment mine. A second
    # breach in that lane produces the explicit Game Over state.
    game.stage = 0
    game.selection = ["fuzileiro"]
    game.begin_game()
    game.zombies = [Zombie("caminhante", 0, BOARD_X - 28, ZOMBIE_DATA["caminhante"]["hp"])]
    game.update_zombies(0)
    assert not game.row_mines[0] and not game.zombies and game.end_state is None
    game.zombies = [Zombie("caminhante", 0, BOARD_X - 28, ZOMBIE_DATA["caminhante"]["hp"])]
    game.update_zombies(0)
    assert game.end_state == "defeat" and "Linha 1" in game.defeat_reason

    # Render the city scene, generated regional walker, boss UI, turret and
    # an explosion headlessly.
    game.end_state = None
    game.defenders = [Defender("torreta_engenheiro", 0, 2, UNIT_DATA["torreta_engenheiro"]["hp"])]
    game.zombies = [game.make_zombie("bruto", 0, BOARD_X + 600, boss_id="city_demolisher")]
    game.spawn_effect("explosion", BOARD_X + 4 * CELL_W, BOARD_Y + 2 * CELL_H, .5, 1.0)
    game.update_effects(.1)
    assert game.effects
    game.draw()
    pygame.quit()
    print("HEADLESS_SMOKE_OK")


if __name__ == "__main__":
    main()
