"""Testes do ensaio de carta, implantação e chegada na mesma linha."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
PROTOTYPE_ROOT = ROOT / "PROTOTIPO_CARTA_CAMPO"
sys.path.insert(0, str(PROTOTYPE_ROOT))

from prototipo_carta_campo import GRID_X, Prototype  # noqa: E402


class PrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prototype = Prototype(headless=True)

    def tearDown(self) -> None:
        import pygame

        pygame.quit()

    def test_assets_have_complete_eight_frame_sequences(self) -> None:
        for clips in (self.prototype.guard_clips, self.prototype.zombie_clips):
            self.assertEqual({"move", "idle"}, set(clips))
            self.assertTrue(all(len(clip.frames) == 8 for clip in clips.values()))

    def test_move_to_idle_never_changes_canvas_or_foot_line(self) -> None:
        for clips in (self.prototype.guard_clips, self.prototype.zombie_clips):
            frames = [frame for clip in clips.values() for frame in clip.frames]
            self.assertEqual(1, len({frame.get_size() for frame in frames}))
            self.assertEqual(
                1,
                len({frame.get_bounding_rect(min_alpha=8).bottom for frame in frames}),
            )

    def test_deployment_stops_at_selected_column(self) -> None:
        self.prototype.deploy(3, 2)
        for _ in range(90):
            self.prototype.update(0.05)
        assert self.prototype.guard is not None
        assert self.prototype.deployment is not None
        self.assertTrue(self.prototype.deployment.arrived)
        self.assertAlmostEqual(GRID_X[3], self.prototype.guard.position.x)
        self.assertEqual("idle", self.prototype.guard.state)

    def test_zombie_uses_exactly_the_selected_lane(self) -> None:
        self.prototype.deploy(2, 3)
        for _ in range(120):
            self.prototype.update(0.05)
        assert self.prototype.guard is not None
        assert self.prototype.zombie is not None
        self.assertEqual(self.prototype.guard.position.y, self.prototype.zombie.position.y)
        self.assertLess(self.prototype.zombie.velocity.x, 0.0)

    def test_reset_removes_both_entities(self) -> None:
        self.prototype.deploy(1, 0)
        self.prototype.update(0.2)
        self.prototype.reset()
        self.assertIsNone(self.prototype.guard)
        self.assertIsNone(self.prototype.zombie)
        self.assertIsNone(self.prototype.deployment)


if __name__ == "__main__":
    unittest.main()
