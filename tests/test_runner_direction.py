"""Direção visual dos corredores nas folhas regionais realmente usadas."""
import os
import unittest
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from svz.production_animations import build_production_clips


class RunnerDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.clips = build_production_clips()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def assert_faces_left(self, frame, label):
        # Nas três folhas aprovadas a cabeça ocupa o quarto superior e se
        # projeta para a frente. Medimos a silhueta final, não flags de flip.
        bounds = frame.get_bounding_rect(min_alpha=8)
        head = frame.subsurface(pygame.Rect(bounds.x, bounds.y, bounds.width, bounds.height // 4))
        mask = pygame.mask.from_surface(head, threshold=8)
        self.assertGreater(mask.count(), 20, label)
        self.assertLess(mask.centroid()[0], bounds.width / 2, label)

    def test_desert_runs_facing_the_base_in_every_frame(self):
        self.check_region("desert")

    def test_beach_never_turns_around_mid_stride(self):
        self.check_region("beach")

    def test_city_keeps_its_correct_direction(self):
        self.check_region("city")

    def check_region(self, region):
        for actor in (f"{region}_runner", f"{region}_runner_v2"):
            for state in ("move", "skill"):
                if state not in self.clips[actor]:
                    continue
                clip = self.clips[actor][state]
                self.assertEqual(8, len(clip.frames))
                for index, frame in enumerate(clip.frames):
                    with self.subTest(actor=actor, state=state, frame=index):
                        self.assert_faces_left(frame, f"{actor}/{state}/{index}")


class RunnerGameplayTests(unittest.TestCase):
    def test_runner_moves_forward_in_all_maps_and_difficulties(self):
        from svz.app import Game
        from svz.diagnostics import verify_runners
        with tempfile.TemporaryDirectory() as directory:
            game = Game(save_path=Path(directory) / "campaign.json")
            try:
                while game.scene == "loading":
                    game.update(1/60)
                report = verify_runners(game, Path(directory))
                self.assertEqual(9, len(report))
            finally:
                pygame.quit()


if __name__ == "__main__":
    unittest.main()
