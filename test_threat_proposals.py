"""Valida que a proposta de ameaças fecha exatamente o escopo pedido."""

import unittest

from beta4_threat_proposals import BOSSES, COMMON_THREATS, SUBBOSSES


class ThreatProposalTests(unittest.TestCase):
    def test_quantidades_e_distribuicao_regional(self) -> None:
        self.assertEqual(18, sum(map(len, COMMON_THREATS.values())))
        self.assertEqual(6, sum(map(len, SUBBOSSES.values())))
        self.assertEqual(3, sum(map(len, BOSSES.values())))
        for region in ("city", "desert", "beach"):
            self.assertEqual(6, len(COMMON_THREATS[region]))
            self.assertEqual(2, len(SUBBOSSES[region]))
            self.assertEqual(1, len(BOSSES[region]))

    def test_toda_ameaca_tem_lore_comportamento_habilidade_e_contraponto(self) -> None:
        for collection in (COMMON_THREATS, SUBBOSSES, BOSSES):
            for entries in collection.values():
                for key, data in entries.items():
                    with self.subTest(key=key):
                        self.assertTrue(data["lore"])
                        self.assertTrue(data["behavior"])
                        self.assertTrue(data["ability"])
                        self.assertTrue(data["counterplay"])
                        self.assertEqual("proposal", data["status"])


if __name__ == "__main__":
    unittest.main()
