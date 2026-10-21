"""Contratos do carrossel, inicialização segura e counters da Beta 4."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from main import DEFENSES, ENEMIES, REGION_ROSTERS, Battle, Defender, Enemy, Game


class CarrosselECountersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.game = Game(integration_preview=False)
        while not cls.game.assets.complete:
            cls.game.assets.load_next()
        cls.game.assets.prepare_production_animations()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_mapa_inicia_direto_com_as_oito_cartas_regionais(self) -> None:
        for region, roster in REGION_ROSTERS.items():
            self.game.enter_selection(region)
            self.assertEqual("battle", self.game.scene)
            self.assertIsNotNone(self.game.battle)
            self.assertEqual(list(roster), self.game.battle.selected)

    def test_toda_carta_tem_ficha_completa_e_utilidade_unica(self) -> None:
        active = [key for roster in REGION_ROSTERS.values() for key, _ in roster]
        utilities = []
        for key in active:
            data = DEFENSES[key]
            for field in ("lore", "tactical_function", "mechanical_need", "unique_utility"):
                self.assertTrue(str(data[field]).strip(), (key, field))
            utilities.append(data["unique_utility"])
        self.assertEqual(len(utilities), len(set(utilities)))

    def test_batalha_repara_selecao_vazia_ou_invalida_sem_crash(self) -> None:
        battle = Battle(self.game, "city", [("nao_existe", "Inválida")])
        self.assertEqual([REGION_ROSTERS["city"][0]], battle.selected)
        self.assertEqual(1, len(battle.card_cooldowns))
        self.assertEqual(REGION_ROSTERS["city"][0], battle.card())

    def test_dano_em_area_nao_vence_bruto_sem_tropa_de_choque(self) -> None:
        battle = Battle(self.game, "city", [("lancador_foguetes", "Foguete")])
        bruto = Enemy("bruto", 1, ENEMIES["bruto"], "city", 3)
        rocket = Defender("lancador_foguetes", "Foguete", 1, 2, DEFENSES["lancador_foguetes"], 0, region="city")
        battle.enemies.append(bruto)
        initial = bruto.hp
        battle.take_enemy_damage(bruto, 500, "mortar", rocket)
        self.assertEqual(initial, bruto.hp)

        shock = Defender("agente_entrada", "Entrada", 1, 2, DEFENSES["agente_entrada"], 0, region="city")
        battle.take_enemy_damage(bruto, 10, source=shock)
        self.assertGreater(bruto.defense_broken, 0)
        battle.take_enemy_damage(bruto, 100, "mortar", rocket)
        self.assertLess(bruto.hp, initial)

    def test_zumbi_de_lamina_exige_guardiao(self) -> None:
        battle = Battle(self.game, "desert", [("guardiao_laminas", "Guardião")])
        blade = Enemy("parasita", 1, ENEMIES["parasita"], "desert", 7)
        rifle = Defender("fuzileiro_deserto", "Fuzileiro", 1, 2, DEFENSES["fuzileiro_deserto"], 0, region="desert")
        guard = Defender("guardiao_laminas", "Guardião", 1, 2, DEFENSES["guardiao_laminas"], 0, region="desert")
        battle.enemies.append(blade)
        initial = blade.hp
        battle.take_enemy_damage(blade, 200, source=rifle)
        self.assertEqual(initial, blade.hp)
        battle.take_enemy_damage(blade, 10, source=guard)
        self.assertGreater(blade.defense_broken, 0)
        self.assertLess(blade.hp, initial)

    def test_mergulhador_e_rompido_por_precisao_naval(self) -> None:
        battle = Battle(self.game, "beach", [("atirador_precisao_marinha", "Precisão")])
        diver = Enemy("mergulhador", 1, ENEMIES["mergulhador"], "beach", 7)
        marksman = Defender("atirador_precisao_marinha", "Precisão", 1, 2, DEFENSES["atirador_precisao_marinha"], 0, region="beach")
        battle.enemies.append(diver)
        battle.take_enemy_damage(diver, 10, source=marksman)
        self.assertGreater(diver.defense_broken, 0)

    def test_especialistas_priorizam_a_ameaca_da_propria_funcao(self) -> None:
        battle = Battle(self.game, "desert", [("guardiao_laminas", "Guardião")])
        guard = Defender("guardiao_laminas", "Guardião", 1, 2, DEFENSES["guardiao_laminas"], 0, region="desert")
        normal = Enemy("desperto_khepra", 1, ENEMIES["desperto_khepra"], "desert", 7)
        blade = Enemy("parasita", 1, ENEMIES["parasita"], "desert", 7)
        normal.x = guard.x + 45
        blade.x = guard.x + 90
        battle.defenders.append(guard)
        battle.enemies.extend((normal, blade))
        self.assertIs(blade, battle.target_in_range(guard))


if __name__ == "__main__":
    unittest.main()
