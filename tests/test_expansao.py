"""Garante que o novo lote regional não entre incompleto ou reciclado."""

import unittest

from svz.roster import EXPANSION_DEFENDERS


class ExpansaoBeta4Tests(unittest.TestCase):
    def test_elenco_de_soldados_completo(self) -> None:
        expected = {"city": 5, "desert": 5, "beach": 7}
        for region in ("city", "desert", "beach"):
            self.assertEqual(expected[region], len(EXPANSION_DEFENDERS[region]))

    def test_soldados_estao_integrados(self) -> None:
        defenders = [data for region in EXPANSION_DEFENDERS.values() for data in region.values()]
        self.assertTrue(all(data["requires_new_sheet"] is False for data in defenders))
        self.assertTrue(all(data["status"] == "integrated" for data in defenders))


if __name__ == "__main__":
    unittest.main()
