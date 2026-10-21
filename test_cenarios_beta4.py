"""Verificações estruturais da galeria isolada de cenários da Beta 4."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = ROOT / "CENARIOS_BETA4_CONCEITOS"
sys.path.insert(0, str(SCENARIO_ROOT))

from visualizar_cenarios import (  # noqa: E402
    AMBIENT_ANCHORS,
    DEFENSE_END_X,
    DEFENSE_START_X,
    DESERT_BRAZIER_ANCHORS,
    SCENES,
    ZOMBIE_ENTRY_X,
    ScenarioGallery,
)


class ScenarioGalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gallery = ScenarioGallery(headless=True, scene=1)

    @classmethod
    def tearDownClass(cls) -> None:
        import pygame

        pygame.quit()

    def test_all_active_backgrounds_exist(self) -> None:
        for _, filename, _ in SCENES:
            self.assertTrue((SCENARIO_ROOT / "prontos_1280x720" / filename).is_file())

    def test_egypt_uses_clean_brazier_background(self) -> None:
        egypt = next(filename for _, filename, kind in SCENES if kind == "egito")
        self.assertIn("piras_apagadas", egypt)

    def test_egypt_command_and_flames_use_marked_points(self) -> None:
        self.assertEqual((80, 400), AMBIENT_ANCHORS["egito"])
        self.assertEqual(((997, 208), (1239, 354)), DESERT_BRAZIER_ANCHORS)

    def test_generals_have_three_complete_sequences(self) -> None:
        self.assertEqual(3, len(self.gallery.general))
        for sequence in self.gallery.general:
            self.assertEqual(8, len(sequence))
            self.assertEqual(1, len({frame.get_size() for frame in sequence}))
            self.assertTrue(all(frame.get_bounding_rect(min_alpha=10).width > 0 for frame in sequence))

    def test_city_lieutenant_has_complete_whistle_sequence(self) -> None:
        self.assertEqual(8, len(self.gallery.city_lieutenant))
        self.assertEqual(1, len({frame.get_size() for frame in self.gallery.city_lieutenant}))
        self.assertTrue(
            all(frame.get_bounding_rect(min_alpha=10).width > 0 for frame in self.gallery.city_lieutenant)
        )

    def test_brazilian_navy_officer_has_complete_sequence(self) -> None:
        self.assertEqual(8, len(self.gallery.beach_officer))
        self.assertEqual(1, len({frame.get_size() for frame in self.gallery.beach_officer}))
        self.assertTrue(
            all(frame.get_bounding_rect(min_alpha=10).width > 0 for frame in self.gallery.beach_officer)
        )

    def test_defenses_end_before_enemy_entry(self) -> None:
        for kind, starts in DEFENSE_START_X.items():
            for start, end in zip(starts, DEFENSE_END_X[kind]):
                self.assertLess(start, end)
                self.assertLess(end, ZOMBIE_ENTRY_X[kind])

    def test_rejected_water_and_city_fog_layers_are_absent(self) -> None:
        self.assertFalse(hasattr(self.gallery, "draw_waterfall"))
        self.assertFalse(hasattr(self.gallery, "draw_minas_enemy_cave"))
        self.assertFalse(hasattr(self.gallery, "draw_city_fog"))
        self.assertFalse(hasattr(self.gallery, "draw_city_enemy_breach"))

    def test_egypt_flames_grow_with_horde_using_delta_time(self) -> None:
        gallery = ScenarioGallery(headless=True, scene=2)
        self.assertEqual(0.0, gallery.horde_flame)
        gallery.toggle_horde()
        gallery.update(0.25)
        self.assertAlmostEqual(0.2875, gallery.horde_flame)
        gallery.update(1.0)
        self.assertEqual(1.0, gallery.horde_flame)
        gallery.toggle_horde()
        gallery.update(0.25)
        self.assertAlmostEqual(0.8, gallery.horde_flame)

    def test_boss_arrival_also_starts_a_horde(self) -> None:
        gallery = ScenarioGallery(headless=True, scene=2)
        gallery.toggle_boss()
        self.assertTrue(gallery.boss_active)
        self.assertTrue(gallery.horde_active)


if __name__ == "__main__":
    unittest.main()
