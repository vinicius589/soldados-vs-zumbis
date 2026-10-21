"""Testes do laboratório de tiro, recarga, mordida e dano."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parent
COMBAT_ROOT = ROOT / "PROTOTIPO_COMBATE"
sys.path.insert(0, str(COMBAT_ROOT))

from prototipo_combate import (  # noqa: E402
    ATTACK_RANGE,
    CARD_ASSETS,
    MAGAZINE_SIZE,
    CombatPrototype,
    SpriteSheet,
)


class CombatPrototypeTests(unittest.TestCase):
    def tearDown(self) -> None:
        import pygame

        pygame.quit()

    def test_regular_units_do_not_register_death_states(self) -> None:
        prototype = CombatPrototype(headless=True)
        self.assertNotIn("death", prototype.guard_clips)
        self.assertNotIn("death", prototype.zombie_clips)
        self.assertNotIn("destroy", prototype.guard_clips)
        self.assertNotIn("destroy", prototype.zombie_clips)

    def test_every_guard_state_uses_one_fixed_canvas_and_foot_line(self) -> None:
        prototype = CombatPrototype(headless=True)
        frames = [frame for clip in prototype.guard_clips.values() for frame in clip.frames]
        self.assertEqual(1, len({frame.get_size() for frame in frames}))
        self.assertEqual(1, len({frame.get_bounding_rect(min_alpha=8).bottom for frame in frames}))
        # Uma pose pode inclinar o corpo, mas nenhuma folha pode reaparecer em
        # outra escala, como ocorreu no vídeo enviado pelo usuário.
        state_heights = [
            sum(frame.get_bounding_rect(min_alpha=8).height for frame in clip.frames)
            / len(clip.frames)
            for clip in prototype.guard_clips.values()
        ]
        self.assertLessEqual(max(state_heights) - min(state_heights), 8.0)

    def test_shoot_and_reload_keep_the_approved_idle_body_scale(self) -> None:
        prototype = CombatPrototype(headless=True)

        def actor_heights(state: str) -> list[int]:
            result: list[int] = []
            for frame in prototype.guard_clips[state].frames:
                components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
                main = max(components, key=lambda rect: rect.width * rect.height)
                result.append(main.height)
            return result

        idle_average = sum(actor_heights("idle")) / len(prototype.guard_clips["idle"].frames)
        for state in ("shoot", "reload"):
            heights = actor_heights(state)
            self.assertLessEqual(max(heights) - min(heights), 2)
            self.assertLessEqual(abs(sum(heights) / len(heights) - idle_average), 2.0)

    def test_every_zombie_state_uses_one_fixed_canvas_and_foot_line(self) -> None:
        prototype = CombatPrototype(headless=True)
        frames = [frame for clip in prototype.zombie_clips.values() for frame in clip.frames]
        self.assertEqual(1, len({frame.get_size() for frame in frames}))
        self.assertEqual(1, len({frame.get_bounding_rect(min_alpha=8).bottom for frame in frames}))

    def test_bite_and_hit_have_dedicated_generated_frames(self) -> None:
        prototype = CombatPrototype(headless=True)
        walk_pixels = {pygame.image.tobytes(frame, "RGBA") for frame in prototype.zombie_clips["move"].frames}
        for state in ("bite", "hit"):
            self.assertTrue(
                all(
                    pygame.image.tobytes(frame, "RGBA") not in walk_pixels
                    for frame in prototype.zombie_clips[state].frames
                )
            )

    def test_zombie_combat_frames_have_no_neighbor_invasion(self) -> None:
        prototype = CombatPrototype(headless=True)
        for state in ("bite", "hit"):
            for frame in prototype.zombie_clips[state].frames:
                substantial = [
                    rect
                    for rect in pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
                    if rect.width * rect.height > 20
                ]
                self.assertEqual(1, len(substantial))
                bounds = frame.get_bounding_rect(min_alpha=8)
                self.assertGreater(bounds.left, 0)
                self.assertLess(bounds.right, frame.get_width())

    def test_bite_source_has_full_figures_inside_spacious_cells(self) -> None:
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
        cells = SpriteSheet.from_file(
            CARD_ASSETS / "caminhante_urbano_mordida_4x2_v4_pronto.png"
        ).slice_equal(4, 2)
        self.assertEqual(8, len(cells))
        for frame in cells:
            bounds = frame.get_bounding_rect(min_alpha=8)
            self.assertGreater(bounds.left, 0)
            self.assertGreater(bounds.top, 0)
            self.assertLess(bounds.right, frame.get_width())
            self.assertLess(bounds.bottom, frame.get_height())
            substantial = [
                rect
                for rect in pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
                if rect.width * rect.height > 20
            ]
            self.assertEqual(1, len(substantial))

    def test_guard_waits_until_enemy_enters_range(self) -> None:
        prototype = CombatPrototype(headless=True, mode="fire")
        prototype.zombie.position.x = prototype.guard.position.x + ATTACK_RANGE + 40
        prototype.zombie.velocity.x = 0.0
        prototype.update(0.1)
        self.assertEqual(MAGAZINE_SIZE, prototype.ammo)
        self.assertEqual("idle", prototype.guard.state)

    def test_shot_causes_zombie_damage(self) -> None:
        prototype = CombatPrototype(headless=True, mode="fire")
        prototype.zombie.position.x = prototype.guard.position.x + ATTACK_RANGE - 2
        prototype.zombie.velocity.x = 0.0
        for _ in range(20):
            prototype.update(0.05)
        self.assertGreater(prototype.zombie_damage, 0)
        self.assertLess(prototype.ammo, MAGAZINE_SIZE)

    def test_empty_magazine_runs_full_reload(self) -> None:
        prototype = CombatPrototype(headless=True, mode="fire")
        prototype.zombie.position.x = prototype.guard.position.x + ATTACK_RANGE - 2
        prototype.zombie.velocity.x = 0.0
        prototype.ammo = 0
        prototype.update(0.05)
        self.assertEqual("reload", prototype.guard.state)
        for _ in range(39):
            prototype.update(0.05)
        self.assertEqual(MAGAZINE_SIZE, prototype.ammo)

    def test_bite_causes_guard_damage_on_same_lane(self) -> None:
        prototype = CombatPrototype(headless=True, mode="bite")
        prototype.zombie.position.x = prototype.guard.position.x + 110
        prototype.zombie.velocity.x = 0.0
        for _ in range(25):
            prototype.update(0.05)
        self.assertGreater(prototype.guard_damage, 0)
        self.assertEqual(prototype.guard.position.y, prototype.zombie.position.y)


if __name__ == "__main__":
    unittest.main()
