"""Contratos dos elencos ativos e das fichas regionais da Beta 4."""

from __future__ import annotations

import unittest

from svz.api import (
    CARD_DETAILS,
    DEFENDER_ACTOR_BY_KEY,
    DEFENSES,
    REGIONS,
    REGION_ROSTERS,
)


class ActiveContentContractTests(unittest.TestCase):
    def test_each_region_has_eight_distinct_active_cards(self) -> None:
        self.assertEqual(set(REGIONS), set(REGION_ROSTERS))

        for region, roster in REGION_ROSTERS.items():
            with self.subTest(region=region):
                keys = [key for key, _display_name in roster]
                self.assertEqual(8, len(keys))
                self.assertEqual(len(keys), len(set(keys)))

                for key in keys:
                    with self.subTest(region=region, key=key):
                        self.assertIn(key, DEFENSES)
                        self.assertIn(key, CARD_DETAILS)
                        self.assertIn(key, DEFENDER_ACTOR_BY_KEY)


if __name__ == "__main__":
    unittest.main()
