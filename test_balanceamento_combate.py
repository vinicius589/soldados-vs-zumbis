"""Regressões de grid, direção e balanceamento do recorte regional Beta 4."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from main import (
    CELL_W,
    DEFENSES,
    DIFFICULTIES,
    ENEMIES,
    LANE_PROTECTION_COLUMN,
    REGION_ENEMIES,
    REGION_ROSTERS,
    Battle,
    Game,
    Projectile,
    SpawnOrder,
    Defender,
)


class BalanceamentoCombateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = Game(integration_preview=True)
        while not cls.app.assets.complete:
            cls.app.assets.load_next()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def battle(self, region: str = "city", card_index: int = 0, difficulty: str = "medium") -> Battle:
        self.app.difficulty = difficulty
        card = REGION_ROSTERS[region][card_index]
        battle = Battle(self.app, region, [card])
        battle.intermission = 9999.0
        battle.supplies = 9999
        return battle

    @staticmethod
    def deploy(battle: Battle, row: int, col: int = 2):
        battle.place(row, col)
        defender = battle.defenders[-1]
        defender.deployment_x = None
        defender.deployment_target_x = None
        return defender

    @staticmethod
    def duel(battle: Battle, defender, enemy_key: str, seconds: float = 35.0):
        battle.spawn_enemy(SpawnOrder(0.0, enemy_key, defender.row))
        enemy = battle.enemies[-1]
        enemy.entry_reveal = 0.0
        enemy.age = 2.0
        enemy.x = defender.x + float(defender.stats["range"]) * CELL_W - 1.0
        elapsed = 0.0
        while elapsed < seconds and defender in battle.defenders and enemy in battle.enemies:
            dt = 1 / 60
            battle.update_defenders(dt)
            battle.update_enemies(dt)
            battle.update_projectiles(dt)
            battle.update_production_animations(dt)
            elapsed += dt
        return defender, enemy, elapsed

    def test_dificuldade_escala_em_uma_unica_direcao(self) -> None:
        easy, medium, hard = (DIFFICULTIES[key] for key in ("easy", "medium", "hard"))
        self.assertGreater(easy["initial_supplies"], medium["initial_supplies"])
        self.assertGreater(medium["initial_supplies"], hard["initial_supplies"])
        self.assertLess(easy["enemy_hp"], medium["enemy_hp"])
        self.assertLess(medium["enemy_hp"], hard["enemy_hp"])
        self.assertLess(easy["enemy_damage"], medium["enemy_damage"])
        self.assertLess(medium["enemy_damage"], hard["enemy_damage"])
        self.assertLess(easy["spawn_count"], medium["spawn_count"])
        self.assertLess(medium["spawn_count"], hard["spawn_count"])
        self.assertGreater(easy["spawn_wait"], medium["spawn_wait"])
        self.assertGreater(medium["spawn_wait"], hard["spawn_wait"])
        self.assertGreater(easy["supply_gain"], medium["supply_gain"])
        self.assertGreater(medium["supply_gain"], hard["supply_gain"])
        self.assertLess(easy["supply_cycle"], medium["supply_cycle"])
        self.assertLess(medium["supply_cycle"], hard["supply_cycle"])

    def test_projetil_dos_soldados_novos_nasce_na_arma_e_segue_para_frente(self) -> None:
        for region in ("city", "desert", "beach"):
            for card_index in range(3, 7):
                with self.subTest(region=region, card_index=card_index):
                    battle = self.battle(region, card_index)
                    key = REGION_ROSTERS[region][card_index][0]
                    row = 1 if key in {"barco_patrulha", "submarino_tatico"} else 0
                    defender = self.deploy(battle, row, 2)
                    enemy_key = REGION_ENEMIES[region][0]
                    target = self._spawn_for_test(battle, enemy_key, row)
                    target.x = defender.x + max(1.0, float(defender.stats["range"]) - 0.25) * CELL_W
                    # Remove a chance de erro do sniper para validar a origem
                    # geométrica do disparo, não a rolagem de precisão.
                    defender.ascended = 1.0 if defender.stats["role"] == "sniper" else 0.0
                    battle.fire_defender(defender, target)
                    if defender.stats["role"] == "suicide_bomber":
                        self.assertEqual([], battle.projectiles)
                        continue
                    projectile = battle.projectiles[-1]
                    self.assertGreater(projectile.x, defender.x)
                    self.assertLessEqual(projectile.y, defender.y - 40)
                    self.assertGreater(projectile.target_x, projectile.x)

    def test_cachoeira_remove_homem_bomba_e_sonar_e_mantem_oito_cards(self) -> None:
        keys = tuple(key for key, _display in REGION_ROSTERS["beach"])
        self.assertEqual(8, len(keys))
        self.assertNotIn("homem_bomba", keys)
        self.assertNotIn("operador_sonar", keys)

    def test_stagger_para_todos_exceto_corredores(self) -> None:
        battle = self.battle()
        for key in ("infectado_urbano", "rastejador_cidade"):
            enemy = self._spawn_for_test(battle, key, 1)
            battle.take_enemy_damage(enemy, 1.0)
            self.assertGreater(enemy.stun, 0.0, key)
        runner = self._spawn_for_test(battle, "corredor_cidade", 1)
        battle.take_enemy_damage(runner, 1.0)
        self.assertEqual(runner.stun, 0.0)

    def _spawn_for_test(self, battle: Battle, key: str, row: int):
        battle.spawn_enemy(SpawnOrder(0.0, key, row))
        enemy = battle.enemies[-1]
        enemy.entry_reveal = 0.0
        enemy.age = 2.0
        enemy.skill_timer = 999.0
        return enemy

    def test_corredor_tem_velocidade_constante_e_colisao_varrida(self) -> None:
        battle = self.battle()
        runner = self._spawn_for_test(battle, "corredor_cidade", 1)
        runner.x = 900.0
        battle.update_enemies(0.5)
        self.assertAlmostEqual(runner.x, 900.0 - ENEMIES[runner.key]["speed"] * 0.5, places=4)

        # A animação de habilidade não pode reintroduzir o antigo dash.
        # Mesmo quando o ciclo especial dispara, a distância percorrida usa
        # exatamente a velocidade nominal da ficha.
        runner.x = 900.0
        runner.skill_timer = 0.0
        battle.update_enemies(0.5)
        self.assertAlmostEqual(runner.x, 900.0 - ENEMIES[runner.key]["speed"] * 0.5, places=4)
        self.assertEqual(0.0, runner.rage)

        defender = self.deploy(battle, 1, 4)
        runner.x = defender.x + 82.0
        battle.update_enemies(1.0)
        distance = runner.x - defender.x
        self.assertGreaterEqual(distance, 70.0)
        self.assertLessEqual(distance, ENEMIES[runner.key]["contact_distance"] + 0.1)

    def test_primeiro_ataque_do_corredor_e_dobrado_so_uma_vez(self) -> None:
        battle = self.battle()
        defender = self.deploy(battle, 1)
        defender.attack_timer = 999.0
        runner = self._spawn_for_test(battle, "corredor_cidade", 1)
        runner.x = defender.x + ENEMIES[runner.key]["contact_distance"] - 0.25
        battle.update_enemies(1 / 60)
        first = runner.attack_damage
        self.assertTrue(runner.first_attack_done)
        runner.attack_target = None
        runner.attack_windup = 0.0
        runner.attack_timer = 0.0
        battle.update_enemies(1 / 60)
        second = runner.attack_damage
        self.assertAlmostEqual(first, second * 2.0, places=4)

    def test_basico_perde_um_contra_um_e_corredor_vence_nos_tres_mapas(self) -> None:
        for region, enemies in REGION_ENEMIES.items():
            row = 0 if region == "beach" else 1
            with self.subTest(region=region, kind="basic"):
                battle = self.battle(region)
                defender = self.deploy(battle, row)
                defender, enemy, _ = self.duel(battle, defender, enemies[0])
                self.assertIn(defender, battle.defenders)
                self.assertNotIn(enemy, battle.enemies)
            with self.subTest(region=region, kind="runner"):
                battle = self.battle(region)
                defender = self.deploy(battle, row)
                defender, enemy, _ = self.duel(battle, defender, enemies[1])
                self.assertNotIn(defender, battle.defenders)
                self.assertIn(enemy, battle.enemies)

    def test_cinco_zumbis_basicos_vencem_em_grupo_nos_tres_mapas(self) -> None:
        for region, enemies in REGION_ENEMIES.items():
            row = 0 if region == "beach" else 1
            with self.subTest(region=region):
                battle = self.battle(region)
                defender = self.deploy(battle, row)
                group = []
                for index in range(5):
                    enemy = self._spawn_for_test(battle, enemies[0], row)
                    enemy.x = defender.x + CELL_W + index * 7.0
                    group.append(enemy)
                elapsed = 0.0
                while elapsed < 30.0 and defender in battle.defenders:
                    dt = 1 / 60
                    battle.update_defenders(dt)
                    battle.update_enemies(dt)
                    battle.update_projectiles(dt)
                    battle.update_production_animations(dt)
                    elapsed += dt
                self.assertNotIn(defender, battle.defenders)
                self.assertTrue(any(enemy in battle.enemies for enemy in group))

    def test_rastejador_devora_classes_um_e_dois_ao_alcancar(self) -> None:
        for card_index in (0, 1):
            battle = self.battle("city", card_index)
            defender = self.deploy(battle, 1)
            defender.attack_timer = 999.0
            crawler = self._spawn_for_test(battle, "rastejador_cidade", 1)
            crawler.x = defender.x + 50.0
            battle.update_enemies(1 / 60)
            self.assertGreater(crawler.attack_damage, defender.hp)
            battle.update_enemies(1.0)
            self.assertNotIn(defender, battle.defenders)

    def test_primeira_coluna_e_reservada_enquanto_protecao_existe(self) -> None:
        battle = self.battle()
        self.assertEqual(LANE_PROTECTION_COLUMN, 0)
        allowed, reason = battle.can_place("xerife_rua", 1, LANE_PROTECTION_COLUMN)
        self.assertFalse(allowed)
        self.assertIn("contenção", reason)
        battle.lane_bombs[1].state = "spent"
        self.assertTrue(battle.can_place("xerife_rua", 1, LANE_PROTECTION_COLUMN)[0])

    def test_linhas_de_deteccao_e_projeteis_apontam_para_frente(self) -> None:
        battle = self.battle()
        basic = self.deploy(battle, 1)
        behind = self._spawn_for_test(battle, "infectado_urbano", 1)
        behind.x = basic.x - 5.0
        self.assertIsNone(battle.target_in_range(basic))
        behind.x = basic.x + 2 * CELL_W + 1.0
        self.assertIsNone(battle.target_in_range(basic))
        behind.x = basic.x + 2 * CELL_W - 1.0
        self.assertIs(battle.target_in_range(basic), behind)
        battle.fire_defender(basic, behind)
        shot = battle.projectiles[-1]
        self.assertGreater(shot.target_x, shot.x)

        advanced_battle = self.battle("city", 1)
        advanced = self.deploy(advanced_battle, 1)
        target = self._spawn_for_test(advanced_battle, "infectado_urbano", 1)
        target.x = advanced.x + 3 * CELL_W - 1.0
        self.assertIs(advanced_battle.target_in_range(advanced), target)
        target.x = advanced.x + 3 * CELL_W + 1.0
        self.assertIsNone(advanced_battle.target_in_range(advanced))

    def test_dano_em_area_comum_nunca_vaza_para_a_linha_vizinha(self) -> None:
        battle = self.battle("city", 6)
        rocket = self.deploy(battle, 0)
        target = self._spawn_for_test(battle, "infectado_urbano", 0)
        neighbor = self._spawn_for_test(battle, "infectado_urbano", 1)
        target.x = rocket.x + CELL_W * 2
        neighbor.x = target.x
        neighbor_hp = neighbor.hp
        battle.fire_defender(rocket, target)
        shot = battle.projectiles[-1]
        battle.update_projectiles(shot.travel + 0.01)
        self.assertEqual(neighbor_hp, neighbor.hp)

        victim = self.deploy(battle, 0, 4)
        adjacent = self.deploy(battle, 1, 4)
        attacker = self._spawn_for_test(battle, "cientista_helix", 0)
        adjacent_hp = adjacent.hp
        battle.projectiles.append(
            Projectile(
                attacker.x,
                attacker.y - 40,
                victim,
                victim.x,
                victim.y - 20,
                20,
                "acid",
                attacker,
                CELL_W,
                False,
                0.1,
            )
        )
        battle.update_projectiles(0.11)
        self.assertEqual(adjacent_hp, adjacent.hp)

    def test_cura_e_sonar_comuns_nunca_vazam_para_linha_vizinha(self) -> None:
        desert = self.battle("desert")
        healer = self._spawn_for_test(desert, "curandeiro", 1)
        healer.x = 720.0
        same_lane = self._spawn_for_test(desert, "digger", 1)
        other_lane = self._spawn_for_test(desert, "digger", 2)
        same_lane.x = other_lane.x = healer.x + 12.0
        same_lane.hp = same_lane.max_hp - 60.0
        other_lane.hp = other_lane.max_hp - 60.0
        other_lane_before = other_lane.hp
        desert.enemy_special(healer)
        self.assertGreater(same_lane.hp, same_lane.max_hp - 60.0)
        self.assertEqual(other_lane_before, other_lane.hp)

        beach = self.battle("beach")
        sonar_data = DEFENSES["operador_sonar"]
        sonar = Defender(
            "operador_sonar",
            str(sonar_data["base"]),
            1,
            2,
            sonar_data,
            0,
            region="beach",
        )
        sonar.utility_timer = 0.0
        beach.defenders.append(sonar)
        detected = self._spawn_for_test(beach, "mergulhador", 1)
        neighbor = self._spawn_for_test(beach, "mergulhador", 2)
        detected.x = neighbor.x = sonar.x + 100.0
        beach.utility_defender(sonar, 0.0)
        self.assertGreater(detected.soaked, 0.0)
        self.assertEqual(0.0, neighbor.soaked)

    def test_suportes_regionais_geram_exatos_doze_a_cada_doze_segundos(self) -> None:
        for region in ("city", "desert", "beach"):
            for difficulty in ("easy", "medium", "hard"):
                with self.subTest(region=region, difficulty=difficulty):
                    battle = self.battle(region, 2, difficulty)
                    # As duas pistas centrais da Cachoeira são água e ficam
                    # reservadas a embarcações; o gerador ocupa a margem.
                    support = self.deploy(battle, 0)
                    battle.supplies = 0
                    support.utility_timer = 0.0
                    battle.utility_defender(support, 0.0)
                    self.assertEqual(12, battle.supplies)
                    self.assertEqual(12.0, support.utility_timer)

    def test_quadros_dos_tres_corredores_nao_carregam_vizinho_lateral(self) -> None:
        clips = self.app.assets.production_clips
        self.assertIsNotNone(clips)
        for actor in ("city_runner_v2", "desert_runner_v2", "beach_runner_v2"):
            for clip in clips[actor].values():
                for frame in clip.frames:
                    box = frame.get_bounding_rect(min_alpha=8)
                    self.assertGreater(box.left, 0, actor)
                    self.assertLess(box.right, frame.get_width(), actor)


if __name__ == "__main__":
    unittest.main()
