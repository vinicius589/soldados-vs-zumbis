"""Testes headless do laboratório de aprovação visual."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from animation_lab import AnimationLab, PREVIEWS


class AnimationLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lab = AnimationLab(headless=True)

    def tearDown(self) -> None:
        pygame.quit()

    def test_all_prototypes_and_actions_render(self) -> None:
        self.assertEqual(len(PREVIEWS), 4)
        for preview_index, spec in enumerate(PREVIEWS):
            self.lab.select(preview_index)
            for action_index, (action, _) in enumerate(spec.actions):
                self.lab.action_index = action_index
                self.lab.manager.play(action, restart=True)
                self.assertEqual(len(self.lab.manager.clip.frames), 8)
                for _ in range(24):
                    self.lab.update(1.0 / 60.0)
                self.lab.draw()
                self.assertGreater(self.lab.manager.frame.get_bounding_rect().width, 0)

    def test_review_keys_are_action_specific(self) -> None:
        self.lab.select(0)
        self.assertEqual(self.lab.action, "andar")
        walk_key = f"{self.lab.spec.key}:{self.lab.action}"
        self.lab.action_index = 1
        self.lab.manager.play(self.lab.action, restart=True)
        bite_key = f"{self.lab.spec.key}:{self.lab.action}"
        self.assertNotEqual(walk_key, bite_key)


if __name__ == "__main__":
    unittest.main()
