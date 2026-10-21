"""Contrato da campanha Beta 4: ciclo, economia, espaço e doutrinas."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from main import (
    CITY_TACTICAL_UNITS,
    DEFENSES,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
    TOTAL_WAVES,
    Battle,
    Game,
)


class Campanha12OndasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.game = Game(integration_preview=False)
        while not cls.game.assets.complete:
            cls.game.assets.load_next()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_ciclo_exato_duas_comuns_subboss_boss(self) -> None:
        self.assertEqual(12, TOTAL_WAVES)
        battle = Battle(self.game, "city", list(REGION_ROSTERS["city"][:3]))
        for wave in range(1, 13):
            orders = battle.build_wave(wave)
            keys = [order.key for order in orders]
            slot = (wave - 1) % 4 + 1
            chapter = (wave - 1) // 4
            if slot in {1, 2}:
                self.assertFalse(any(order.boss for order in orders))
                self.assertFalse(any(key in REGION_SUBBOSSES["city"] for key in keys))
            elif slot == 3:
                self.assertIn(REGION_SUBBOSSES["city"][chapter], keys)
                self.assertFalse(any(order.boss for order in orders))
            else:
                self.assertEqual(REGION_BOSSES["city"][chapter], orders[-1].key)
                self.assertTrue(orders[-1].boss)

    def test_elenco_e_variedade_crescem_nas_ondas_comuns(self) -> None:
        for region in ("city", "desert", "beach"):
            self.assertEqual(6, len(REGION_ENEMIES[region]))
            self.assertEqual(3, len(REGION_SUBBOSSES[region]))
            self.assertEqual(3, len(REGION_BOSSES[region]))
            battle = Battle(self.game, region, list(REGION_ROSTERS[region][:3]))
            first = battle.build_wave(1)
            second = battle.build_wave(2)
            self.assertGreaterEqual(len({order.key for order in first}), 2, region)
            self.assertGreaterEqual(len({order.key for order in second}), 3, region)

    def test_cartas_pesadas_ocupam_duas_casas(self) -> None:
        battle = Battle(self.game, "city", [("lancador_foguetes", "Lançador")])
        battle.supplies = 999
        battle.place(1, 2)
        self.assertFalse(battle.can_place("xerife_rua", 1, 3)[0])
        self.assertTrue(battle.can_place("xerife_rua", 1, 4)[0])

    def test_xerife_nao_e_pre_requisito_para_o_radio(self) -> None:
        self.assertEqual("Patrulha Básica", CITY_TACTICAL_UNITS["xerife_rua"][0])
        self.assertEqual(1, DEFENSES["xerife_rua"]["footprint"])
        self.assertEqual(2, DEFENSES["especialista_antipraga"]["footprint"])
        self.assertNotIn("rádio", DEFENSES["xerife_rua"]["situational_advantage"].lower())
        battle = Battle(self.game, "city", [("operador_radio_policial", "Rádio")])
        battle.supplies = 999
        battle.place(1, 2)
        radio = battle.defenders[0]
        radio.deployment_x = None
        radio.utility_timer = 0
        battle.supplies = 0
        battle.utility_defender(radio, 0.0)
        self.assertGreater(battle.supplies, 0)


if __name__ == "__main__":
    unittest.main()
