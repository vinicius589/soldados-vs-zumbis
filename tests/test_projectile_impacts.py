"""Regressões de impacto com entidades reais e persistência da partida."""
import os
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('SVZ_RENDERER', 'software')

import pygame
from svz.app import Game
from svz.battle import Battle
from svz.content import ENEMIES, REGION_ROSTERS, DEFENSES
from svz.entities import Enemy, Defender, Projectile
from svz.projectile_combat import EXPLOSIVE_KINDS
from svz.snapshot import capture, restore


class ProjectileImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Game(integration_preview=True)
        while not cls.app.assets.complete:
            cls.app.assets.load_next()
        cls.app.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.b = Battle(self.app, 'city', REGION_ROSTERS['city'][:1])
        self.b.intermission = 9999
        self.target = self.enemy(500)
        self.neighbor = self.enemy(520)

    def enemy(self, x, row=0):
        e = Enemy('infectado_urbano', row, ENEMIES['infectado_urbano'], 'city', 1, x=x)
        self.b.enemies.append(e)
        return e

    def projectile(self, kind='grenade_40mm', radius=80, target=None, friendly=True):
        target = self.target if target is None else target
        p = Projectile(200, target.y, target, target.x, target.y - (16 if friendly else 12),
                       20, kind, None, radius=radius, friendly=friendly, travel=.2)
        self.b.projectiles.append(p)
        return p

    def test_removed_primary_still_damages_neighbors_for_every_explosive(self):
        for kind in EXPLOSIVE_KINDS:
            with self.subTest(kind=kind):
                self.setUp()
                self.projectile(kind)
                hp = self.neighbor.hp
                self.b.enemies.remove(self.target)
                self.b.update_projectiles(.21)
                self.assertLess(self.neighbor.hp, hp)
                self.assertTrue(self.b.effects)

    def test_empty_explosion_still_has_visual_feedback(self):
        self.projectile()
        self.b.enemies.clear()
        self.b.update_projectiles(.21)
        self.assertTrue(self.b.effects)
        self.assertFalse(self.b.projectiles)

    def test_fixed_explosion_does_not_follow_moved_primary(self):
        p = self.projectile()
        self.target.x += 200
        hp = self.target.hp
        neighbor_hp = self.neighbor.hp
        self.b.update_projectiles(.21)
        self.assertEqual(p.target_x, 500)
        self.assertEqual(self.target.hp, hp)
        self.assertLess(self.neighbor.hp, neighbor_hp)

    def test_direct_shot_tracks_visual_endpoint(self):
        p = self.projectile('rifle', 0)
        self.target.x += 35
        hp = self.target.hp
        self.b.update_projectiles(.1)
        self.assertEqual(p.target_x, self.target.x)
        self.assertEqual(p.target_y, self.target.y - 16)
        self.assertEqual(self.target.hp, hp)
        self.b.update_projectiles(.11)
        self.assertLess(self.target.hp, hp)

    def test_direct_shot_does_not_retarget_removed_enemy(self):
        self.projectile('rifle', 0)
        self.b.enemies.remove(self.target)
        hp = self.neighbor.hp
        self.b.update_projectiles(.21)
        self.assertEqual(self.neighbor.hp, hp)

    def test_area_respects_lane_and_exclusive_radius_boundary(self):
        outside = self.enemy(580)
        adjacent = self.enemy(500, 1)
        before = (outside.hp, adjacent.hp)
        self.projectile()
        self.b.update_projectiles(.21)
        self.assertEqual((outside.hp, adjacent.hp), before)

    def test_primary_is_not_damaged_twice(self):
        self.projectile()
        self.b.take_enemy_damage = Mock()
        self.b.update_projectiles(.21)
        calls = self.b.take_enemy_damage.call_args_list
        self.assertEqual([c.args[0] for c in calls], [self.target, self.neighbor])
        self.assertEqual(calls[0].args[1], 20)
        self.assertAlmostEqual(calls[1].args[1], 14.4)

    def test_killing_primary_does_not_skip_secondary(self):
        self.target.hp = 1
        hp = self.neighbor.hp
        self.projectile()
        self.b.update_projectiles(.21)
        self.assertNotIn(self.target, self.b.enemies)
        self.assertLess(self.neighbor.hp, hp)

    def test_delayed_launch_and_large_frame_resolve_once(self):
        p = self.projectile()
        p.elapsed = -.3
        hp = self.target.hp
        self.b.update_projectiles(.2)
        self.assertEqual(self.target.hp, hp)
        self.b.update_projectiles(10)
        hp = self.target.hp
        self.b.update_projectiles(10)
        self.assertEqual(self.target.hp, hp)
        self.assertFalse(self.b.projectiles)

    def test_pause_freezes_projectile(self):
        p = self.projectile()
        self.b.paused = True
        self.b.update(1)
        self.assertEqual(p.elapsed, 0)
        self.assertIn(p, self.b.projectiles)

    def test_removed_target_explosion_survives_snapshot(self):
        self.projectile()
        self.b.enemies.remove(self.target)
        saved = capture(self.b)
        restored, _ = restore(saved, self.app)
        self.assertEqual(capture(restored), saved)
        hp = restored.enemies[0].hp
        restored.update_projectiles(.21)
        self.assertLess(restored.enemies[0].hp, hp)
        self.assertTrue(restored.effects)

    def test_hostile_area_survives_removed_defender(self):
        key = REGION_ROSTERS['city'][0][0]
        d = Defender(key, key, 0, 2, DEFENSES[key], 0, region='city')
        other = Defender(key, key, 0, 3, DEFENSES[key], 0, region='city')
        self.b.defenders = [other]
        p = self.projectile('acid', 200, d, False)
        hp = other.hp
        self.b.update_projectiles(.21)
        self.assertLess(other.hp, hp)
        self.assertTrue(self.b.effects)

    def test_signal_jammer_effect_matches_skill_duration(self):
        key = next(k for k, data in ENEMIES.items() if 'signal_jammer' in data.get('tags', ()))
        jammer = Enemy(key, 0, ENEMIES[key], 'city', 1, x=500)
        self.b.enemy_special(jammer)
        effect = next(e for e in self.b.effects if e.kind == 'signal_pulse')
        self.assertAlmostEqual(effect.duration, .61)
        self.assertEqual(effect.elapsed, 0)


if __name__ == '__main__':
    unittest.main()
