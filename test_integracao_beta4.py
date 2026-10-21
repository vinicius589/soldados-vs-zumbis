"""Testes do primeiro recorte integrado da Beta 4."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from main import (
    BEACH_WATER_ENEMIES,
    BEACH_WATER_DEFENDERS,
    BASIC_ENEMY_BY_REGION,
    DEFENSES,
    ENEMIES,
    ENEMY_ENTRY_X,
    LAST_PLACEABLE_COLUMN,
    REGION_ENEMIES,
    REGION_ROSTERS,
    Battle,
    Game,
    SpawnOrder,
    animated_actor_render_scale,
    cell_center,
    lane_bounds,
    wave_enemy_pool,
)


class IntegracaoBeta4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = Game(integration_preview=True)
        while not cls.app.assets.complete:
            cls.app.assets.load_next()
        cls.app.update(0.0)
        cls.preview_scene = cls.app.scene
        cls.preview_battle = cls.app.battle

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def new_battle(self) -> Battle:
        battle = Battle(self.app, "city", [("xerife_rua", "Xerife de Rua")])
        battle.intermission = 9999.0
        battle.supplies = 999
        return battle

    def test_launcher_sempre_entra_no_menu_iniciar(self) -> None:
        self.assertEqual(self.preview_scene, "title")
        self.assertIsNone(self.preview_battle)

    def test_atores_usam_o_centro_optico_e_fim_da_pista_nao_e_clicavel(self) -> None:
        for region in ("city", "desert", "beach"):
            battle = Battle(self.app, region, [REGION_ROSTERS[region][0]])
            for row in range(4):
                top, bottom = lane_bounds(region, row)
                _x, ground = cell_center(row, 3, region)
                ratio = (ground - top) / (bottom - top)
                self.assertAlmostEqual(0.60, ratio, places=2)
            allowed, _reason = battle.can_place(
                REGION_ROSTERS[region][0][0], 0, LAST_PLACEABLE_COLUMN
            )
            self.assertTrue(allowed)
            allowed, _reason = battle.can_place(
                REGION_ROSTERS[region][0][0], 0, LAST_PLACEABLE_COLUMN + 1
            )
            self.assertFalse(allowed)

    def test_carta_implanta_guarda_sem_mudar_caixa_ou_pe(self) -> None:
        battle = self.new_battle()
        battle.place(1, 3)
        guard = battle.defenders[0]
        self.assertIsNotNone(guard.visual_animation)
        sizes = {
            frame.get_size()
            for clip in guard.visual_animation.animations.values()
            for frame in clip.frames
        }
        self.assertEqual(len(sizes), 1)
        # A escala é aplicada à caixa normalizada inteira, não ao conteúdo
        # recortado de cada pose. Assim um braço estendido ou um agachamento
        # não redimensiona o corpo no quadro seguinte.
        render_sizes = {
            tuple(round(value, 5) for value in animated_actor_render_scale(frame, 1.0))
            for clip in guard.visual_animation.animations.values()
            for frame in clip.frames
        }
        self.assertEqual(len(render_sizes), 1)
        foot_lines = {
            frame.get_bounding_rect(min_alpha=8).bottom
            for clip in guard.visual_animation.animations.values()
            for frame in clip.frames
        }
        self.assertLessEqual(max(foot_lines) - min(foot_lines), 2)
        self.assertFalse(guard.deployed)
        for _ in range(180):
            battle.update(1 / 60)
        self.assertTrue(guard.deployed)
        self.assertEqual(guard.visual_animation.state, "idle")

    def test_dano_mordida_tiro_recarga_e_desaparecimento(self) -> None:
        battle = self.new_battle()
        battle.place(1, 2)
        guard = battle.defenders[0]
        for _ in range(180):
            battle.update(1 / 60)
        battle.spawn_enemy(SpawnOrder(0.0, "infectado_urbano", 1))
        walker = battle.enemies[0]
        walker.x = guard.x + 45
        walker.attack_timer = 0.0
        battle.update(1 / 60)
        self.assertEqual(walker.visual_animation.state, "bite")
        for _ in range(40):
            battle.update(1 / 60)
        self.assertLess(guard.hp, guard.max_hp)

        battle.take_enemy_damage(walker, walker.max_hp + 1, source=guard)
        self.assertNotIn(walker, battle.enemies)
        self.assertEqual(battle.fallen, [])

        battle.damage_defender(guard, guard.max_hp + 1)
        self.assertNotIn(guard, battle.defenders)
        self.assertEqual(battle.fallen, [])

    def test_contencao_dispara_no_contato_e_some_ao_sair(self) -> None:
        battle = self.new_battle()
        battle.spawn_enemy(SpawnOrder(0.0, "infectado_urbano", 2))
        walker = battle.enemies[0]
        cart = battle.lane_bombs[2]
        walker.x = cart.x + 28.5
        battle.update_enemies(0.10)
        self.assertEqual(cart.state, "rolling")
        battle.update_lane_bombs(0.10)
        self.assertNotIn(walker, battle.enemies)
        for _ in range(30):
            battle.update_lane_bombs(0.10)
        self.assertEqual(cart.state, "spent")

    def test_cada_mapa_expoe_defensores_e_seis_infectados_comuns(self) -> None:
        expected = {
            "city": (
                ("xerife_rua", "agente_swat", "operador_radio_policial",
                 "atirador_precisao_swat", "agente_entrada",
                 "especialista_antipraga", "lancador_foguetes", "escudeiro_tropa_choque"),
                ("infectado_urbano", "corredor_cidade", "rastejador_cidade",
                 "policial_helix", "cientista_helix", "tecnico_subestacao"),
            ),
            "desert": (
                ("pistoleiro_deserto", "fuzileiro_deserto", "torre_radio_egito",
                 "atirador_horizonte", "tenente_artilheiro",
                 "incinerador_deserto", "nomade_morteiro", "guardiao_laminas"),
                ("desperto_khepra", "corredor_deserto", "rastejador_deserto",
                 "arqueiro_necropole", "hospedeiro_escaravelhos", "saqueador_canopico"),
            ),
            "beach": (
                ("marinheiro", "fuzileiro_marinha", "estacao_comunicacao_cachoeira",
                 "atirador_precisao_marinha", "bombeiro_hidraulico",
                 "granadeiro_profundidades", "barco_patrulha", "submarino_tatico"),
                ("afogado_cachoeira", "corredor_cachoeira", "rastejador_cachoeira",
                 "surfista", "mergulhador", "pescador_praga"),
            ),
        }
        for region, (defender_keys, zombie_keys) in expected.items():
            with self.subTest(region=region):
                self.app.enter_selection(region)
                self.assertEqual("battle", self.app.scene)
                self.assertEqual(tuple(key for key, _ in self.app.selection), defender_keys)
                self.assertEqual(tuple(key for key, _ in REGION_ROSTERS[region]), defender_keys)
                self.assertEqual(REGION_ENEMIES[region], zombie_keys)
                battle = Battle(self.app, region, self.app.selection.copy())
                battle.supplies = 999
                row = 0 if region == "beach" else 1
                for zombie_key in zombie_keys:
                    battle.spawn_enemy(
                        SpawnOrder(0.0, zombie_key, battle.spawn_row_for(zombie_key))
                    )
                self.assertTrue(all(enemy.visual_animation is not None for enemy in battle.enemies))
                for defender_key in defender_keys:
                    display = next(display for key, display in REGION_ROSTERS[region] if key == defender_key)
                    preview = Battle(self.app, region, [(defender_key, display)])
                    preview.supplies = 9999
                    preview_row = 1 if defender_key in {"barco_patrulha", "submarino_tatico"} else row
                    preview.place(preview_row, 2)
                    self.assertEqual(1, len(preview.defenders), defender_key)
                    self.assertIsNotNone(preview.defenders[0].visual_animation, defender_key)

    def test_ensaio_cria_o_zumbi_correto_em_cada_mapa(self) -> None:
        for region, zombie_keys in REGION_ENEMIES.items():
            with self.subTest(region=region):
                self.app.enter_selection(region)
                battle = Battle(self.app, region, self.app.selection.copy())
                orders = battle.build_wave(1)
                self.assertTrue(orders)
                self.assertEqual({order.key for order in orders}, set(wave_enemy_pool(region, 1)))
                if region == "beach":
                    self.assertTrue(all(order.row in {0, 3} for order in orders))
                battle.spawn_enemy(orders[0])
                animation = battle.enemies[0].visual_animation
                self.assertIsNotNone(animation)
                self.assertGreater(animation.frame.get_bounding_rect(min_alpha=8).width, 1)
                self.assertEqual(battle.enemies[0].x, ENEMY_ENTRY_X[region])

    def test_cachoeira_separa_terra_e_agua_sem_excecao_generica(self) -> None:
        self.assertEqual(
            BEACH_WATER_ENEMIES,
            frozenset({"surfista", "mergulhador", "pescador_praga", "baiacu_mutante", "cacador"}),
        )
        self.assertEqual(BEACH_WATER_DEFENDERS, frozenset({"lancha", "submarino", "barco_patrulha", "submarino_tatico"}))
        self.app.enter_selection("beach")
        battle = Battle(self.app, "beach", self.app.selection.copy())
        battle.supplies = 999
        self.assertFalse(battle.can_place("marinheiro", 1, 2)[0])
        self.assertFalse(battle.can_place("marinheiro", 2, 2)[0])
        self.assertTrue(battle.can_place("marinheiro", 0, 2)[0])
        self.assertTrue(battle.can_place("marinheiro", 3, 2)[0])
        self.assertFalse(battle.can_place("fuzileiro_marinha", 1, 2)[0])
        self.assertFalse(battle.can_place("estacao_comunicacao_cachoeira", 2, 2)[0])
        self.assertFalse(battle.can_place("atirador_lancha", 1, 2)[0])
        self.assertFalse(battle.can_place("bomba_agua", 1, 2)[0])
        self.assertTrue(battle.can_place("lancha", 1, 2)[0])
        self.assertTrue(battle.can_place("submarino", 2, 2)[0])
        self.assertTrue(battle.can_place("barco_patrulha", 1, 2)[0])
        self.assertTrue(battle.can_place("submarino_tatico", 2, 2)[0])
        for _ in range(30):
            self.assertIn(battle.spawn_row_for("afogado_cachoeira"), {0, 3})
            self.assertIn(battle.spawn_row_for("corredor_cachoeira"), {0, 3})
            self.assertIn(battle.spawn_row_for("rastejador_cachoeira"), {0, 3})
            self.assertIn(battle.spawn_row_for("surfista"), {1, 2})
            self.assertIn(battle.spawn_row_for("mergulhador"), {1, 2})
            self.assertIn(battle.spawn_row_for("pescador_praga"), {1, 2})
            self.assertIn(battle.spawn_row_for("baiacu_mutante"), {1, 2})
            self.assertIn(battle.spawn_row_for("cacador"), {1, 2})

    def test_basico_nao_atira_atraves_de_aliado_mas_automatico_pode(self) -> None:
        battle = self.new_battle()
        battle.place(1, 1)
        battle.place(1, 2)
        rear, front = battle.defenders
        rear.deployment_x = None
        front.deployment_x = None
        battle.spawn_enemy(SpawnOrder(0.0, "infectado_urbano", 1))
        enemy = battle.enemies[0]
        enemy.x = cell_center(1, 3, "city")[0]
        self.assertIsNone(battle.target_in_range(rear))
        self.assertIs(battle.target_in_range(front), enemy)
        automatic = dict(DEFENSES["xerife_rua"])
        automatic.update(range=4, shoot_through_allies=True)
        rear.stats = automatic
        self.assertIs(battle.target_in_range(rear), enemy)

    def test_automaticos_trocam_recarga_curta_por_rajada_e_pente_maiores(self) -> None:
        pairs = (
            ("xerife_rua", "agente_swat"),
            ("pistoleiro_deserto", "fuzileiro_deserto"),
            ("marinheiro", "fuzileiro_marinha"),
        )
        for basic_key, automatic_key in pairs:
            basic, automatic = DEFENSES[basic_key], DEFENSES[automatic_key]
            with self.subTest(automatic=automatic_key):
                self.assertGreater(automatic["hp"], basic["hp"])
                self.assertGreater(automatic["ammo"], basic["ammo"])
                self.assertLess(automatic["cooldown"], basic["cooldown"])
                self.assertGreater(automatic["reload"], basic["reload"])
                self.assertEqual(automatic["range"], 3)
                self.assertTrue(automatic["shoot_through_allies"])

    def test_suportes_regionais_geram_suprimentos_sem_atacar(self) -> None:
        support_keys = (
            ("city", "operador_radio_policial"),
            ("desert", "torre_radio_egito"),
            ("beach", "estacao_comunicacao_cachoeira"),
        )
        for region, key in support_keys:
            with self.subTest(region=region):
                self.app.enter_selection(region)
                battle = Battle(self.app, region, self.app.selection.copy())
                battle.supplies = 999
                battle.selected_card = 2
                battle.place(0, 2)
                support = battle.defenders[0]
                support.deployment_x = None
                support.deployment_target_x = None
                battle.supplies = 0
                before = battle.supplies
                support.utility_timer = 0.0
                battle.update_defenders(1 / 60)
                self.assertEqual(battle.supplies - before, 12)
                self.assertEqual(support.utility_timer, 12.0)
                self.assertEqual(support.motion.state, "support")
                self.assertEqual(DEFENSES[key]["damage"], 0)

    def test_corredor_e_rastejador_tem_funcoes_opostas_em_cada_regiao(self) -> None:
        for region, keys in REGION_ENEMIES.items():
            basic, runner, crawler = (ENEMIES[key] for key in keys[:3])
            with self.subTest(region=region):
                self.assertGreater(runner["speed"], basic["speed"])
                self.assertGreater(runner["damage"], basic["damage"])
                self.assertIn("runner", runner["tags"])
                self.assertIn("constant_speed", runner["tags"])
                self.assertIn("unstaggerable", runner["tags"])
                self.assertNotIn("dash", runner["tags"])
                self.assertLess(crawler["speed"], basic["speed"])
                self.assertGreater(crawler["hp"], runner["hp"])
                self.assertGreater(crawler["damage"], basic["damage"])

    def test_minas_detona_a_faixa_inteira_no_primeiro_contato(self) -> None:
        self.app.enter_selection("beach")
        battle = Battle(self.app, "beach", self.app.selection.copy())
        for x in (420.0, 710.0, 980.0):
            battle.spawn_enemy(SpawnOrder(0.0, "mergulhador", 1))
            battle.enemies[-1].x = x
        cart = battle.lane_bombs[1]
        self.assertTrue(battle.trigger_lane_bomb(1))
        self.assertEqual(cart.state, "spent")
        self.assertFalse([enemy for enemy in battle.enemies if enemy.row == 1])
        self.assertGreaterEqual(len(battle.effects), 7)


if __name__ == "__main__":
    unittest.main()
