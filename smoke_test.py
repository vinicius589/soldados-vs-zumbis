"""Checks without opening a visible window.

Run with: python smoke_test.py
"""

import hashlib
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from main import (
    ASSET_DIR,
    BOARD,
    CARD_RECHARGE_SECONDS,
    CELL_W,
    BOSSES,
    CARD_ART_ASSETS,
    CARD_ATLAS_INDEX,
    DEFENSES,
    DIFFICULTIES,
    ENEMIES,
    PROMOTIONS,
    REGION_ROSTERS,
    REGION_ENEMIES,
    REGIONS,
    VERSION,
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
    regional_sprite_index,
    wave_enemy_pool,
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
    # atlases (N1 and N2), four containment devices, five standalone mine
    # sprites, two bespoke coastal-unit sprites and ten dedicated card
    # sprites (including the coastal water pair and urban poison pair), the exact
    # Beta 3 loading reference plus standalone portraits for Saltador and
    # the urban Rastejante.
    # before the menu is made interactive.
    assert VERSION == "BETA 3"
    assert game.assets.total == 37
    assert {"loading_beta3", "zombie_jumper_beta3", "zombie_crawler_beta3"} <= set(game.assets.images)
    assert game.assets.images["loading_beta3"].get_size() == (1280, 720)
    assert hashlib.sha256((ASSET_DIR / "loading_beta3_reference.png").read_bytes()).hexdigest() == "39f4406767231aed591a1738d12c67be1d60b220ba782d58ad9f4edc275f548f"
    assert hashlib.sha256((ASSET_DIR / "zombie_jumper_beta3.png").read_bytes()).hexdigest() == "0364d9c3510540f2acc419a0b38fd59555c5b758c9b2d02b6f76e9d47364c262"
    assert hashlib.sha256((ASSET_DIR / "zombie_crawler_beta3.png").read_bytes()).hexdigest() == "a8cba9727cd36f606cdd5ae21534201caa1463dfbe11c7033e2d7a9606a635a5"
    assert game.assets.images["zombie_crawler_beta3"] is not game.assets.images["zombie_jumper_beta3"]
    assert all(f"{region}_bg" in game.assets.images for region in REGIONS)
    assert {"lane_bomb_cart", "desert_lane_bomb_cart", "beach_land_bomb_cart", "beach_water_bomb"} <= set(game.assets.images)
    assert {
        "city_mine_n1",
        "city_mine_n2",
        "beach_mine_land_n1",
        "beach_mine_land_n2",
        "beach_mine_water",
        "beach_drone_operator_n1",
        "beach_boat_shooter",
        "beach_water_launcher_n1",
        "beach_water_cannon_n2",
        "city_poison_sprayer_n1",
        "city_poison_cannon_n2",
    } <= set(game.assets.images)
    assert set(CARD_ART_ASSETS.values()) <= set(game.assets.images)
    assert all(region in game.assets.unit_sprites for region in REGIONS)
    assert all(region in game.assets.unit_l2_sprites for region in REGIONS)
    assert all(region in game.assets.zombie_sprites for region in REGIONS)
    assert all(len(sprites) == 12 for sprites in game.assets.unit_sprites.values())
    assert all(len(sprites) == 12 for sprites in game.assets.unit_l2_sprites.values())
    assert all(len(sprites) == 12 for sprites in game.assets.zombie_sprites.values())
    assert game.assets.unit("city", 3, 1) is not game.assets.unit("city", 3, 2)
    assert game.card_sprite("city", "mina", 11) is game.assets.images["city_mine_n1"]
    assert game.card_sprite("city", "mina_segura", 11) is game.assets.images["city_mine_n2"]
    assert game.card_sprite("beach", "mina", 11) is game.assets.images["beach_mine_land_n1"]
    assert game.card_sprite("beach", "mina_segura", 11) is game.assets.images["beach_mine_land_n2"]
    assert game.card_sprite("beach", "bomba_agua", 11) is game.assets.images["beach_mine_water"]
    assert game.card_sprite("beach", "mecanico", 8) is game.assets.images["beach_drone_operator_n1"]
    assert game.card_sprite("beach", "atirador_lancha", 5) is game.assets.images["beach_boat_shooter"]
    assert game.card_sprite("beach", "lancador_agua", 9) is game.assets.images["beach_water_launcher_n1"]
    assert game.card_sprite("beach", "canhao_mare", 9) is game.assets.images["beach_water_cannon_n2"]
    assert game.card_sprite("city", "lancador_veneno", 9) is game.assets.images["city_poison_sprayer_n1"]
    assert game.card_sprite("city", "canhao_veneno", 9) is game.assets.images["city_poison_cannon_n2"]
    for (region, key), asset_key in CARD_ART_ASSETS.items():
        assert game.card_sprite(region, key, regional_sprite_index(region, key)) is game.assets.images[asset_key]
    for region, mapping in CARD_ATLAS_INDEX.items():
        for key, expected_index in mapping.items():
            assert regional_sprite_index(region, key) == expected_index

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
    # O dossiê e as ondas usam o mesmo elenco: o primeiro encontro tem só a
    # ameaça-base, e até a onda 15 nenhum personagem regional fica de fora.
    for region, roster in REGION_ENEMIES.items():
        assert wave_enemy_pool(region, 1) == roster[:1]
        assert wave_enemy_pool(region, 15) == roster
        progression = [len(wave_enemy_pool(region, wave)) for wave in range(1, 16)]
        assert progression == sorted(progression)
    water_cards = {"atirador_lancha", "lancha", "submarino", "bomba_agua"}
    for ground_region in ("city", "desert"):
        assert water_cards.isdisjoint(game.regional_card_keys(ground_region))
        assert water_cards.isdisjoint(game.available_selection_keys(ground_region))
    assert water_cards <= set(game.regional_card_keys("beach"))
    assert water_cards <= set(game.available_selection_keys("beach"))
    fire_cards = {"lanca_chamas_bolso", "lanca_chamas"}
    poison_cards = {"lancador_veneno", "canhao_veneno"}
    assert fire_cards <= set(game.regional_card_keys("desert"))
    assert fire_cards.isdisjoint(game.regional_card_keys("city"))
    assert fire_cards.isdisjoint(game.regional_card_keys("beach"))
    assert poison_cards <= set(game.regional_card_keys("city"))
    assert poison_cards.isdisjoint(game.regional_card_keys("desert"))
    assert poison_cards.isdisjoint(game.regional_card_keys("beach"))
    game.region, game.dossier_kind = "city", "units"
    assert all(item.get("l1") not in water_cards and item.get("l2") not in water_cards for item in game.dossier_items())
    game.region = "beach"
    assert any(item.get("l1") == "atirador_lancha" and item.get("l2") == "lancha" for item in game.dossier_items())
    assert any(item.get("l1") == "lancador_agua" and item.get("l2") == "canhao_mare" for item in game.dossier_items())
    game.region = "beach"
    card_layout = {key: rect for key, _display, rect in game.selection_cards()}
    assert "atirador_lancha" in card_layout and "lancha" in card_layout
    assert card_layout["atirador_lancha"].x == card_layout["lancha"].x
    assert card_layout["atirador_lancha"].y + 126 == card_layout["lancha"].y
    assert len({(rect.x, rect.y, rect.width, rect.height) for rect in card_layout.values()}) == len(card_layout)

    # A escolha de modo acontece antes do mapa. Ela limita as cartas de fato,
    # não apenas o texto da interface; além disso, nenhuma grade mistura N1
    # com N1 ou sobrepõe cartas nos três cenários.
    game.scene = "title"
    game.click_title(game.title_buttons()[0][1].center)
    assert game.scene == "difficulty"
    game.click_difficulty(game.difficulty_buttons()[0][1].center)
    assert game.difficulty == "easy" and game.scene == "campaign"
    expected_levels = {"easy": {2}, "medium": {1, 2}, "hard": {1}}
    mode_wave_sizes = {}
    mode_opening_sizes = {}
    for mode, levels in expected_levels.items():
        game.difficulty = mode
        game.scene = "difficulty"
        game.draw()
        for region in REGIONS:
            selectable = game.available_selection_keys(region)
            assert selectable
            # O Sargento N2 é a única exceção deliberada do modo Difícil:
            # não existe nas telas de Fácil/Médio e compensa o elenco só N1.
            assert ("instrutor" in selectable) == (mode == "hard")
            assert {DEFENSES[key]["level"] for key in selectable if key != "instrutor"} <= levels
            game.enter_selection(region)
            assert len(game.selection) == 8
            assert {DEFENSES[key]["level"] for key, _display in game.selection if key != "instrutor"} <= levels
            cards = game.selection_cards()
            assert len({key for key, _display, _rect in cards}) == len(cards)
            for index, (_key, _display, rect) in enumerate(cards):
                assert all(not rect.colliderect(other) for _other_key, _other_display, other in cards[index + 1:])

            # Cada nível recebe uma silhueta própria. Este teste falha se uma
            # N2 voltar a apontar para a mesma superfície de outra carta, que
            # foi exatamente o defeito relatado na montagem dos três mapas.
            for level in levels:
                level_sprites = [
                    game.card_sprite(region, key, regional_sprite_index(region, key))
                    for key in selectable
                    if DEFENSES[key]["level"] == level
                ]
                assert len({id(sprite) for sprite in level_sprites}) == len(level_sprites)

            # A chave, o retrato, a ficha de hover e a unidade posicionada
            # precisam continuar sendo a mesma carta. Testamos todas as
            # cartas visíveis, não só as oito pré-selecionadas.
            for key, display, rect in cards:
                game.selection = []
                game.click_selection(rect.center)
                assert game.selection == [(key, display)]
                pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, {"pos": rect.center}))
                game.handle_events()
                assert game.hover_card == (key, display)
                assert DEFENSES[game.hover_card[0]]["ability"] == DEFENSES[key]["ability"]
                game.click_selection(rect.center)
                assert not game.selection

                card_surface = game.card_sprite(region, key, regional_sprite_index(region, key))
                placement = Battle(game, region, [(key, display)])
                placement.supplies = 9999
                placement.handle_click(placement.card_rects()[0].center)
                assert placement.card() == (key, display)
                assert placement.message.startswith(f"Selecionado: {display}")
                row = 2 if region == "beach" and DEFENSES[key].get("water_only") else 0
                allowed, _reason = placement.can_place(key, row, 2)
                # Uma carta visível agora sempre pertence ao mapa selecionado.
                # As marítimas aparecem somente na Praia e recebem a faixa de
                # canal; Cidade e Deserto nunca chegam a tentar uma carta de água.
                assert allowed
                placement.place(row, 2)
                assert placement.card_cooldowns[0] == CARD_RECHARGE_SECONDS == 10.0
                defender = placement.defenders[0]
                assert defender.key == key and defender.stats is DEFENSES[key]
                assert defender.sprite_index == regional_sprite_index(region, key)
                assert game.card_sprite(region, defender.key, defender.sprite_index) is card_surface
            if mode == "medium":
                layout = {key: rect for key, _display, rect in cards}
                for level_one, level_two in PROMOTIONS.items():
                    if level_one in layout and level_two in layout:
                        assert layout[level_one].x == layout[level_two].x
                        assert layout[level_two].y == layout[level_one].y + 126
        mode_selection = [
            (key, game.card_display_name("city", key))
            for key in game.available_selection_keys("city")[:8]
        ]
        mode_battle = Battle(game, "city", mode_selection)
        assert mode_battle.supplies == DIFFICULTIES[mode]["initial_supplies"]
        assert mode_battle.cores == DIFFICULTIES[mode]["initial_cores"]
        mode_opening_sizes[mode] = len(mode_battle.build_wave(1))
        mode_wave_sizes[mode] = len(mode_battle.build_wave(15))
    assert mode_wave_sizes["easy"] < mode_wave_sizes["medium"] < mode_wave_sizes["hard"]
    # A curva precisa continuar estritamente crescente, mas sem depender de
    # números congelados: os perfis podem ser refinados sem inverter Médio e
    # Difícil novamente.
    # A primeira onda usa quantidade inteira: Médio e Difícil podem ambos
    # arredondar para quatro invasores, mas nunca invertem a progressão.
    assert mode_opening_sizes["easy"] < mode_opening_sizes["medium"] <= mode_opening_sizes["hard"]
    easy_walker = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 8, difficulty="easy")
    medium_walker = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 8, difficulty="medium")
    hard_walker = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 8, difficulty="hard")
    assert easy_walker.max_hp < medium_walker.max_hp < hard_walker.max_hp
    difficulty_damage = {}
    for mode in expected_levels:
        game.difficulty = mode
        mode_damage_field = Battle(game, "city", mode_selection)
        mode_enemy = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 8, difficulty=mode)
        difficulty_damage[mode] = mode_damage_field.scaled_enemy_damage(mode_enemy, 100)
    difficulty_boss_hp = {
        mode: Enemy("bruto_demolidor", 0, BOSSES["bruto_demolidor"], "city", 5, difficulty=mode).max_hp
        for mode in expected_levels
    }
    assert difficulty_damage["easy"] < difficulty_damage["medium"] < difficulty_damage["hard"]
    assert difficulty_boss_hp["easy"] < difficulty_boss_hp["medium"] < difficulty_boss_hp["hard"]
    # Fácil recebe a antiga pressão do Médio, mas continua mais acessível
    # pelo pacote N2/N3. Médio torna-se a faixa central real e Difícil não
    # é tocado por esta calibração.
    assert DIFFICULTIES["easy"]["initial_supplies"] == 390
    assert DIFFICULTIES["easy"]["enemy_hp"] == 1.20
    assert DIFFICULTIES["medium"]["initial_supplies"] == 128
    assert 1.30 < DIFFICULTIES["medium"]["enemy_hp"] < 1.40
    assert 1.20 < DIFFICULTIES["medium"]["boss_hp"] < 1.30
    assert DIFFICULTIES["easy"]["skill_cooldown"] == 0.85
    assert DIFFICULTIES["hard"]["enemy_hp"] > 1.5
    assert DIFFICULTIES["hard"]["enemy_damage"] > 1.5
    # Os poderes seguem a nova escala final: Médio 14%, Fácil 15%, Difícil 16%.
    assert DIFFICULTIES["hard"]["skill_cooldown"] < DIFFICULTIES["easy"]["skill_cooldown"] < DIFFICULTIES["medium"]["skill_cooldown"]
    game.difficulty = "medium"
    game.region = "city"

    # All regions have a 15-wave director and boss milestones at 5, 10, 15.
    selection = list(REGION_ROSTERS["city"][:8])
    city = Battle(game, "city", selection)
    first_wave = city.build_wave(1)
    final_wave = city.build_wave(15)
    assert len(first_wave) < len(final_wave)
    assert len(final_wave) >= 30 and enemy_wave_scale(15) > 2.0
    for wave, boss_key in zip((5, 10, 15), REGIONS["city"]["bosses"]):
        wave_orders = city.build_wave(wave)
        assert any(order.boss and order.key == boss_key for order in wave_orders)
        assert boss_key in BOSSES

    # Marítimos são exclusivos da Praia e a faixa central é o único lugar
    # onde embarcações e bomba naval podem ser instaladas. As quatro faixas
    # de areia seguem reservadas às tropas terrestres, inclusive ao novo
    # Lançador de Água, que combate da areia e não flutua no canal.
    assert "lancha" not in game.available_selection_keys("city")
    assert "lancha" not in game.available_selection_keys("desert")
    beach = Battle(game, "beach", [("lancha", "Lancha Patrulha"), ("recruta", "Guarda-Costa Recruta")])
    beach.supplies = 999
    assert beach.can_place("lancha", 2, 2)[0]
    assert not beach.can_place("lancha", 0, 2)[0]
    assert not beach.can_place("lancha", 4, 2)[0]
    assert not beach.can_place("recruta", 2, 2)[0]
    assert beach.can_place("recruta", 0, 2)[0]
    assert not beach.can_place("mina", 2, 2)[0]
    assert not beach.can_place("mina_segura", 2, 2)[0]
    assert beach.can_place("mina", 0, 2)[0]
    assert beach.can_place("bomba_agua", 2, 2)[0]
    assert not beach.can_place("bomba_agua", 0, 2)[0]
    assert beach.can_place("atirador_lancha", 2, 2)[0]
    assert not beach.can_place("atirador_lancha", 0, 2)[0]
    assert beach.can_place("lancador_agua", 0, 2)[0]
    assert not beach.can_place("lancador_agua", 2, 2)[0]
    boat_test = Battle(game, "beach", [("atirador_lancha", "Atirador de Lancha")])
    boat_test.supplies = 999
    boat_test.place(2, 2)
    assert boat_test.defenders[0].key == "atirador_lancha" and boat_test.defenders[0].stats["water_only"]

    # Containment is themed per region: City retains its urban cart, Desert
    # gets a dune charge, and Beach uses land carts plus a floating water mine.
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
    coastal_promotion = Battle(game, "beach", [("atirador_lancha", "Atirador de Lancha")])
    coastal_instructor = Defender("instrutor", "Sargento", 1, 1, DEFENSES["instrutor"], 2, region="beach")
    coastal_shooter = Defender("atirador_lancha", "Atirador de Lancha", 2, 2, DEFENSES["atirador_lancha"], 5, region="beach")
    coastal_promotion.defenders = [coastal_instructor, coastal_shooter]
    coastal_instructor.utility_timer = 0
    coastal_promotion.update_defenders(0.1)
    assert PROMOTIONS["atirador_lancha"] == "lancha"
    assert coastal_shooter.key == "lancha" and coastal_shooter.stats["level"] == 2

    # A Praia não recebe lança-chamas: sua dupla temática é Lançador de Água
    # -> Canhão de Maré. O jato extingue o fogo e aplica lentidão temporária,
    # sem alterar as cartas incendiárias de Cidade e Deserto.
    water_promotion = Battle(game, "beach", [("lancador_agua", "Lançador de Água")])
    water_instructor = Defender("instrutor", "Sargento", 1, 1, DEFENSES["instrutor"], 2, region="beach")
    water_recruit = Defender("lancador_agua", "Lançador de Água", 1, 2, DEFENSES["lancador_agua"], 9, region="beach")
    water_promotion.defenders = [water_instructor, water_recruit]
    water_instructor.utility_timer = 0
    water_promotion.update_defenders(0.1)
    assert PROMOTIONS["lancador_agua"] == "canhao_mare"
    assert water_recruit.key == "canhao_mare" and water_recruit.stats["role"] == "waterjet"

    water_field = Battle(game, "beach", [("lancador_agua", "Lançador de Água")])
    water_launcher = Defender("lancador_agua", "Lançador de Água", 0, 2, DEFENSES["lancador_agua"], 9, region="beach")
    soaked_enemy = Enemy("caminhante", 0, ENEMIES["caminhante"], "beach", 4, x=water_launcher.x + CELL_W * 0.6)
    soaked_enemy.burn = 2.0
    water_field.defenders = [water_launcher]
    water_field.enemies = [soaked_enemy]
    water_field.update_defenders(0.1)
    assert any(projectile.kind == "waterjet" and projectile.effect == "water" for projectile in water_field.projectiles)
    water_field.update_projectiles(0.3)
    assert soaked_enemy.burn == 0 and soaked_enemy.soaked > 0
    soaked_x = soaked_enemy.x
    water_field.update_enemies(1.0)
    assert 0 < soaked_x - soaked_enemy.x < float(soaked_enemy.data["speed"]) * 0.70

    # A Cidade possui agora uma dupla química independente. O projétil aplica
    # Envenenado, causa dano periódico e reduz o avanço em 12%, enquanto as
    # cartas de fogo ficam exclusivas do Deserto e receberam dano reforçado.
    assert PROMOTIONS["lancador_veneno"] == "canhao_veneno"
    assert DEFENSES["lanca_chamas_bolso"]["damage"] == 14
    assert DEFENSES["lanca_chamas"]["damage"] == 20
    poison_field = Battle(game, "city", [("lancador_veneno", "Pulverizador de Veneno")])
    poisoner = Defender("lancador_veneno", "Pulverizador de Veneno", 0, 2, DEFENSES["lancador_veneno"], 9, region="city")
    poisoned_enemy = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 4, x=poisoner.x + CELL_W * 0.6)
    poison_field.defenders = [poisoner]
    poison_field.enemies = [poisoned_enemy]
    poison_field.update_defenders(0.1)
    assert any(projectile.kind == "poison" and projectile.effect == "poison" for projectile in poison_field.projectiles)
    poison_field.update_projectiles(0.3)
    assert poisoned_enemy.poisoned > 4.0
    poisoned_hp = poisoned_enemy.hp
    poisoned_x = poisoned_enemy.x
    poison_field.defenders = []
    poison_field.update_enemies(0.5)
    assert poisoned_enemy.hp < poisoned_hp
    assert 0 < poisoned_x - poisoned_enemy.x < float(poisoned_enemy.data["speed"]) * 0.46

    flame_field = Battle(game, "desert", [("lanca_chamas_bolso", "Lança-Chamas de Mão")])
    burner = Defender("lanca_chamas_bolso", "Lança-Chamas de Mão", 0, 2, DEFENSES["lanca_chamas_bolso"], 10, region="desert")
    burning_enemy = Enemy("caminhante", 0, ENEMIES["caminhante"], "desert", 4, x=burner.x + CELL_W * 0.6)
    flame_field.defenders = [burner]
    flame_field.enemies = [burning_enemy]
    flame_field.update_defenders(0.1)
    assert any(projectile.kind == "flame" and projectile.effect == "flame" for projectile in flame_field.projectiles)
    flame_field.update_projectiles(0.3)
    burn_time = burning_enemy.burn
    flame_field.defenders = []
    flame_field.update_enemies(0.5)
    assert 0 < burning_enemy.burn < burn_time

    # A melee contact cannot make a close-range weapon forget the target.
    # The enemy has slipped a few pixels past the defender's center, yet the
    # shotgun must still fire while the blocker is being attacked.
    contact_field = Battle(game, "city", selection)
    shotgun = Defender("escopeteiro", "Escopeteiro", 0, 2, DEFENSES["escopeteiro"], 3)
    engaged_enemy = Enemy("caminhante", 0, ENEMIES["caminhante"], "city", 4, x=shotgun.x - 35)
    contact_field.defenders = [shotgun]
    contact_field.enemies = [engaged_enemy]
    assert contact_field.target_in_range(shotgun) is engaged_enemy
    contact_field.update_defenders(0.1)
    assert any(projectile.friendly and projectile.target is engaged_enemy for projectile in contact_field.projectiles)
    mortar = Defender("morteiro_basico", "Morteiro", 0, 2, DEFENSES["morteiro_basico"], 5)
    contact_field.defenders = [mortar]
    assert contact_field.target_in_range(mortar, BOARD.width / 9 * 1.05) is None

    # Saltador e Escavador não podem mais trocar de lugar instantaneamente.
    # O primeiro descreve um arco visível; o segundo entra, percorre o solo e
    # emerge após apenas a primeira defesa, sem causar dano grátis no salto.
    jump_field = Battle(game, "city", selection)
    jump_front = Defender("recruta", "Patrulheiro", 0, 6, DEFENSES["recruta"], 0)
    jumper = Enemy("saltador", 0, ENEMIES["saltador"], "city", 8, x=jump_front.x + 42)
    jump_field.defenders = [jump_front]
    jump_field.enemies = [jumper]
    jump_field.update_enemies(0.01)
    assert jumper.jump_state == "vault" and jumper.jump_used
    jump_start, jump_end = jumper.jump_start_x, jumper.jump_end_x
    assert jumper.x == jump_start
    game.battle, game.scene = jump_field, "battle"
    game.draw()
    jump_field.update_enemies(0.24)
    assert jump_end < jumper.x < jump_start
    jump_field.update_enemies(0.40)
    assert jumper.jump_state == "" and jumper.x == jump_end

    dig_field = Battle(game, "desert", list(REGION_ROSTERS["desert"][:8]))
    dig_front = Defender("recruta", "Batedor", 0, 6, DEFENSES["recruta"], 0, region="desert")
    dig_rear = Defender("recruta", "Batedor", 0, 3, DEFENSES["recruta"], 0, region="desert")
    digger = Enemy("digger", 0, ENEMIES["digger"], "desert", 8, x=dig_front.x + 42)
    dig_field.defenders = [dig_front, dig_rear]
    dig_field.enemies = [digger]
    front_hp, rear_hp = dig_front.hp, dig_rear.hp
    dig_field.update_enemies(0.01)
    assert digger.dig_state == "enter" and digger.dig_used and digger.burrowed
    assert dig_front.hp == front_hp and dig_rear.hp == rear_hp
    game.battle, game.scene = dig_field, "battle"
    game.draw()
    for _ in range(20):
        dig_field.update_enemies(0.10)
    assert digger.dig_state == "" and not digger.burrowed
    assert digger.x < dig_front.x - 55
    assert dig_front.hp == front_hp and dig_rear.hp == rear_hp

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
    assert lane_troop.stun >= 1.2 and other_troop.stun == 0 and hammer_boss.skill_timer == 18.0 * DIFFICULTIES["medium"]["skill_cooldown"]

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
    # a meaningful encounter, rather than scaling as a normal horde sponge
    # that can only be solved by spending the final-containment cart.
    assert boss_wave_scale(15) < enemy_wave_scale(15)
    assert boss_damage_scale(15) < enemy_damage_scale(15)
    boss_limits = {
        "bruto_demolidor": 1175,
        "comandante_mortos": 1650,
        "cuspidor_alfa": 2500,
        "mutante_ruinas": 1300,
        "necromante": 1850,
        "colosso_mutante": 2900,
        "tide_brute": 1250,
        "cacador_abissal": 2000,
        "leviata": 3200,
    }
    for boss_key, maximum_hp in boss_limits.items():
        wave = 5 if boss_key in {"bruto_demolidor", "mutante_ruinas", "tide_brute"} else (10 if boss_key in {"comandante_mortos", "necromante", "cacador_abissal"} else 15)
        assert Enemy(boss_key, 0, BOSSES[boss_key], "city", wave).max_hp <= maximum_hp

    # Blindados, subchefes e ameaças marítimas resistentes perderam parte da
    # vida, mas os zumbis básicos permanecem com sua identidade inicial.
    assert ENEMIES["conehead"]["hp"] == 185
    assert ENEMIES["bruto"]["hp"] == 450
    assert ENEMIES["mutante"]["hp"] == 400
    assert ENEMIES["mergulhador"]["hp"] == 275

    # Enemy themes contain concrete abilities rather than display-only names.
    assert "acid" in ENEMIES["cuspidor"]["tags"]
    assert "dig" in ENEMIES["digger"]["tags"]
    assert "steal" in ENEMIES["ladrao"]["tags"]
    assert "dash" in ENEMIES["surfista"]["tags"]
    assert "leviathan" == BOSSES["leviata"]["type"]

    # Every visible screen can render after the staged cache is ready.
    game.scene = "difficulty"
    game.draw()
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

    # Fácil mantém N2/N3 e suprimentos, mas não oferece a ferramenta de
    # remoção: o botão some, o atalho R é ignorado e a API não devolve a tropa.
    game.difficulty = "easy"
    easy_field = Battle(game, "city", [("soldado", "Fuzileiro")])
    easy_field.defenders = [Defender("soldado", "Fuzileiro", 0, 1, DEFENSES["soldado"], 1)]
    supplies_before_easy_remove = easy_field.supplies
    easy_field.remove_defender(0, 1)
    assert len(easy_field.defenders) == 1 and easy_field.supplies == supplies_before_easy_remove
    game.battle = easy_field
    game.scene = "battle"
    game.handle_click(easy_field.remove_rect().center)
    assert not easy_field.remove_mode

    pygame.quit()
    print("OK: Beta 3 pré-carrega a arte de carregamento, libera todo o elenco regional e passa nas verificações táticas, de animação e dificuldade.")


if __name__ == "__main__":
    main()
