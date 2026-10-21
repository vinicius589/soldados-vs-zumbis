"""Testes determinísticos do módulo genérico de animação."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from animation2d import (
    AnimationClip,
    AnimationManager,
    Camera2D,
    Entity,
    OneShotVFX,
    Particle,
    SpriteSheet,
    VFXManager,
    apply_color_overlay,
)


def frames(count: int, size: tuple[int, int] = (12, 16)) -> list[pygame.Surface]:
    result: list[pygame.Surface] = []
    for index in range(count):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((40 + index * 20, 120, 180, 255))
        result.append(surface)
    return result


class Animation2DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((64, 64))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_delta_time_is_independent_of_render_frequency(self) -> None:
        clip = AnimationClip.uniform(frames(8), fps=10)
        one_update = AnimationManager({"move": clip}, initial_state="move")
        many_updates = AnimationManager({"move": clip}, initial_state="move")

        one_update.update(0.673)
        for _ in range(673):
            many_updates.update(0.001)

        self.assertEqual(one_update.frame_index, many_updates.frame_index)
        self.assertEqual(one_update.loop_count, many_updates.loop_count)
        self.assertAlmostEqual(one_update.frame_elapsed, many_updates.frame_elapsed, places=7)

    def test_state_transition_restarts_first_frame_without_restarting_same_state(self) -> None:
        clips = {
            "idle": AnimationClip.uniform(frames(3), fps=6),
            "action": AnimationClip.uniform(frames(5), fps=12, loop=False),
        }
        manager = AnimationManager(clips, initial_state="idle")
        manager.update(0.40)
        current = manager.frame_index
        self.assertFalse(manager.play("idle"))
        self.assertEqual(manager.frame_index, current)

        self.assertTrue(manager.play("action"))
        self.assertEqual(manager.frame_index, 0)
        self.assertEqual(manager.frame_elapsed, 0)
        self.assertFalse(manager.finished)

    def test_non_loop_clip_finishes_and_holds_last_frame(self) -> None:
        clip = AnimationClip.uniform(frames(4), fps=8, loop=False)
        manager = AnimationManager({"destroy": clip}, initial_state="destroy")
        manager.update(2.0)
        self.assertTrue(manager.finished)
        self.assertEqual(manager.frame_index, 3)
        manager.update(1.0)
        self.assertEqual(manager.frame_index, 3)

    def test_manual_seek_and_step_are_predictable(self) -> None:
        clip = AnimationClip.uniform(frames(4), fps=8)
        manager = AnimationManager({"move": clip}, initial_state="move")
        manager.seek_frame(2)
        self.assertEqual(manager.frame_index, 2)
        self.assertEqual(manager.step(1), 3)
        self.assertEqual(manager.step(1), 0)
        self.assertEqual(manager.step(-1), 3)

    def test_sprite_sheet_equal_slice_accepts_non_divisible_width(self) -> None:
        sheet = pygame.Surface((2170, 25), pygame.SRCALPHA)
        sliced = SpriteSheet(sheet).slice_equal(8)
        self.assertEqual(len(sliced), 8)
        self.assertEqual(sum(frame.get_width() for frame in sliced), 2170)
        self.assertTrue(all(frame.get_height() == 25 for frame in sliced))

    def test_entity_moves_with_dt_and_flash_expires(self) -> None:
        clip = AnimationClip.uniform(frames(2), fps=4)
        entity = Entity({"idle": clip}, initial_state="idle", position=(10, 20))
        entity.velocity.update(50, -10)
        entity.flash(duration=0.2)
        entity.update(0.1)
        self.assertEqual(entity.position, pygame.Vector2(15, 19))
        self.assertTrue(entity.flash_active)
        entity.update(0.11)
        self.assertFalse(entity.flash_active)

    def test_color_overlay_does_not_mutate_source(self) -> None:
        source = pygame.Surface((4, 4), pygame.SRCALPHA)
        source.fill((100, 120, 140, 200))
        before = source.get_at((1, 1))
        result = apply_color_overlay(source, (255, 0, 0), 0.7)
        self.assertEqual(source.get_at((1, 1)), before)
        self.assertNotEqual(result.get_at((1, 1)), before)

    def test_camera_shake_ends_and_returns_to_zero(self) -> None:
        camera = Camera2D((10, 15))
        camera.trigger_shake(12, 0.30, frequency=24)
        camera.update(0.10)
        self.assertTrue(camera.shaking)
        self.assertNotEqual(camera.shake_offset, pygame.Vector2())
        camera.update(0.25)
        camera.update(0.01)
        self.assertFalse(camera.shaking)
        self.assertEqual(camera.shake_offset, pygame.Vector2())

    def test_one_shot_vfx_and_particle_self_remove(self) -> None:
        effect_clip = AnimationClip.uniform(frames(3), fps=10, loop=False)
        manager = VFXManager()
        effect = manager.spawn_animation(effect_clip, (10, 10))
        particle = manager.emit(Particle(frames(1)[0], (4, 4), lifetime=0.2))
        self.assertIsInstance(effect, OneShotVFX)
        self.assertIsInstance(particle, Particle)
        manager.update(0.5)
        self.assertEqual(manager.animations, [])
        self.assertEqual(manager.particles, [])

    def test_validation_rejects_bad_time_values(self) -> None:
        clip = AnimationClip.uniform(frames(2), fps=5)
        manager = AnimationManager({"idle": clip}, initial_state="idle")
        with self.assertRaises(ValueError):
            manager.update(-0.01)
        with self.assertRaises(ValueError):
            AnimationClip.uniform(frames(1), fps=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
