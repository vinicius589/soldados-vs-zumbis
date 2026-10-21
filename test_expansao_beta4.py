"""Garante que o novo lote regional não entre incompleto ou reciclado."""

import unittest

from beta4_expansion_roster import EXPANSION_DEFENDERS, EXPANSION_ENEMIES


class ExpansaoBeta4Tests(unittest.TestCase):
    def test_elenco_de_soldados_completo_e_quatro_zumbis_propostos(self) -> None:
        expected = {"city": 5, "desert": 5, "beach": 7}
        for region in ("city", "desert", "beach"):
            self.assertEqual(expected[region], len(EXPANSION_DEFENDERS[region]))
            self.assertEqual(4, len(EXPANSION_ENEMIES[region]))

    def test_soldados_estao_integrados_e_zumbis_continuam_fora(self) -> None:
        defenders = [data for region in EXPANSION_DEFENDERS.values() for data in region.values()]
        enemies = [data for region in EXPANSION_ENEMIES.values() for data in region.values()]
        self.assertTrue(all(data["requires_new_sheet"] is False for data in defenders))
        self.assertTrue(all(data["status"] == "integrated" for data in defenders))
        self.assertTrue(all(data["requires_new_sheet"] is True for data in enemies))
        self.assertTrue(all(data["status"] == "in_production" for data in enemies))


if __name__ == "__main__":
    unittest.main()
