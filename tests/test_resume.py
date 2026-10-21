"""Regressões reais do salvamento, da navegação e dos três mapas."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('SVZ_RENDERER', 'software')
import pygame
from svz.app import Game, AUTOSAVE_SECONDS
from svz.content import REGIONS, REGION_ENEMIES, REGION_BOSSES, ENEMIES, BOSSES
from svz.entities import Enemy, Projectile, SpawnOrder
from svz.session_store import SessionStore, MAX_BYTES
from svz.snapshot import capture, activate, restore


class ResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.game = Game(save_path=Path(cls.directory.name) / 'initial.json')
        while not cls.game.assets.complete:
            cls.game.assets.load_next()
        cls.game.assets.prepare_production_animations()
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.directory.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'campaign.json'
        g = self.game
        g.session_store = SessionStore(self.path)
        g.save_path = self.path
        g.pending_snapshot = None
        g.battle = None
        g.save_error = False
        g.session_notice = ''
        g.suspended_random = None
        g.autosave_elapsed = 0
        g.running = True
        g.scene_elapsed = 0
        g.integration_preview = False
        g.difficulty = 'medium'
        g.scene = 'title'
        pygame.event.clear()

    def battle(self, region='city', difficulty='medium'):
        g = self.game
        g.difficulty = difficulty
        random.seed(992)
        g.enter_selection(region)
        b = g.battle
        b.supplies = 300
        b.place(0, 2)
        d = b.defenders[0]
        d.deployment_x = None
        b.start_next_wave()
        key = REGION_ENEMIES[region][0]
        e = Enemy(key, 0, ENEMIES[key], region, b.wave, difficulty=difficulty, x=d.x + 110)
        b.enemies.append(e)
        b.fire_defender(d, e)
        e.attack_target = d
        e.attack_windup = .18
        e.attack_damage = 7
        b.card_cooldowns[0] = 2.3
        b.supplies = 87
        return b

    def test_roundtrip_all_maps_and_difficulties(self):
        for region in REGIONS:
            for difficulty in ('easy', 'medium', 'hard'):
                with self.subTest(region=region, difficulty=difficulty):
                    b = self.battle(region, difficulty)
                    before = capture(b)
                    self.assertTrue(self.game.checkpoint())
                    loaded = self.game.session_store.load()
                    restored = activate(loaded, self.game)
                    self.assertEqual(capture(restored), before)
                    self.assertIs(restored.enemies[0].attack_target, restored.defenders[0])
                    self.assertIs(restored.projectiles[0].target, restored.enemies[0])
                    self.assertIs(restored.projectiles[0].owner, restored.defenders[0])

    def test_simulation_after_loading_matches_uninterrupted_combat(self):
        for region in REGIONS:
            with self.subTest(region=region):
                b = self.battle(region)
                initial = capture(b)
                for _ in range(180):
                    b.update(1/60)
                expected = capture(b)
                restored = activate(initial, self.game)
                self.game.battle = restored
                for _ in range(180):
                    restored.update(1/60)
                self.assertEqual(capture(restored), expected)

    def test_menu_click_keeps_match_and_continue_uses_same_instance(self):
        b = self.battle()
        before = capture(b)
        self.game.handle_click(b.menu_rect().center)
        self.assertEqual(self.game.scene, 'title')
        self.game.update(20)
        self.assertEqual(capture(b)['battle'], before['battle'])
        self.assertEqual(capture(b)['objects'], before['objects'])
        button = dict(self.game.title_buttons())['CONTINUAR']
        self.game.handle_click(button.center)
        self.assertIs(self.game.battle, b)
        self.assertTrue(b.paused)
        self.assertEqual(self.game.scene, 'battle')

    def test_escape_then_enter_resumes(self):
        b = self.battle('desert')
        self.game.handle_key(pygame.K_ESCAPE)
        self.game.handle_key(pygame.K_RETURN)
        self.assertIs(self.game.battle, b)
        self.assertEqual(self.game.scene, 'battle')

    def test_disk_resume_uses_the_active_profile_for_future_scores(self):
        b = self.battle('desert', 'medium')
        b.player_name = 'Jogador antigo'
        self.assertTrue(self.game.checkpoint())
        self.game.battle = None
        self.game.player_name = 'Jogadora atual'
        self.game.pending_snapshot = SessionStore(self.path).load()

        self.assertTrue(self.game.resume_battle())
        self.assertEqual(self.game.battle.player_name, 'Jogadora atual')
        # A retomada continua sendo a mesma partida; só a identidade ativa muda.
        self.assertEqual(self.game.battle.match_id, b.match_id)

    def test_disk_resume_without_in_memory_battle(self):
        b = self.battle('beach', 'hard')
        self.game.leave_battle_to_title()
        expected = capture(b)
        self.game.battle = None
        self.game.difficulty = 'easy'
        self.game.pending_snapshot = SessionStore(self.path).load()
        self.assertTrue(self.game.resume_battle())
        actual = capture(self.game.battle)
        expected['battle']['paused'] = True
        self.assertEqual(actual, expected)
        self.assertEqual(self.game.difficulty, 'hard')

    def test_autosave_and_window_close_save_latest_state(self):
        b = self.battle()
        b.paused = False
        self.game.autosave_elapsed = AUTOSAVE_SECONDS
        self.game.update(.01)
        self.assertEqual(self.game.session_store.load()['battle']['supplies'], b.supplies)
        b.supplies = 71
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.game.handle_events()
        self.assertFalse(self.game.running)
        self.assertEqual(self.game.session_store.load()['battle']['supplies'], 71)

    def test_new_game_cancel_preserves_match_and_confirm_clears(self):
        b = self.battle()
        self.game.leave_battle_to_title()
        self.game.handle_click(dict(self.game.title_buttons())['NOVA PARTIDA'].center)
        self.assertEqual(self.game.scene, 'confirm_new')
        self.game.handle_key(pygame.K_RETURN)
        self.assertIs(self.game.battle, b)
        self.game.handle_click(self.game.confirm_cancel_rect().center)
        self.assertTrue(self.game.can_continue())
        self.game.request_new_game()
        self.game.handle_click(self.game.confirm_accept_rect().center)
        self.assertIsNone(self.game.battle)
        self.assertIsNone(SessionStore(self.path).load())
        self.assertEqual(self.game.scene, 'difficulty')

    def test_failed_save_keeps_previous_file_and_in_memory_match(self):
        b = self.battle()
        self.assertTrue(self.game.checkpoint())
        previous = self.game.session_store.path.read_bytes()
        b.supplies = 99
        with patch('svz.persistence.os.replace', side_effect=PermissionError('simulated')), self.assertLogs('svz.persistence', level='ERROR'):
            self.game.leave_battle_to_title()
        self.assertEqual(self.game.session_store.path.read_bytes(), previous)
        self.assertIs(self.game.battle, b)
        self.assertTrue(self.game.resume_battle())
        self.assertEqual(b.supplies, 99)
        self.assertIn('Não foi possível', self.game.session_notice)
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_failed_close_requires_explicit_exit_without_save(self):
        self.battle()
        with patch.object(self.game.session_store, 'save', return_value=False):
            self.game.request_quit()
        self.assertTrue(self.game.running)
        self.assertEqual(self.game.scene, 'confirm_exit')
        self.game.handle_click(self.game.confirm_cancel_rect().center)
        self.assertTrue(self.game.running)
        with patch.object(self.game.session_store, 'save', return_value=False):
            self.game.request_quit()
        self.game.handle_click(self.game.confirm_accept_rect().center)
        self.assertFalse(self.game.running)

    def test_failed_discard_retains_continue(self):
        b = self.battle()
        self.game.request_new_game()
        with patch.object(self.game.session_store, 'clear', return_value=False):
            self.game.handle_click(self.game.confirm_accept_rect().center)
        self.assertIs(self.game.battle, b)
        self.assertEqual(self.game.scene, 'confirm_new')

    def test_finished_matches_and_victory_progress(self):
        for victory in (False, True):
            b = self.battle()
            b.finished, b.victory, b.lost = True, victory, not victory
            b.wave = 12
            self.game.checkpoint()
            self.game.battle = activate(self.game.session_store.load(), self.game)
            self.game.finish_battle()
            self.assertIsNone(self.game.session_store.load())
            self.assertFalse(self.game.can_continue())
            self.assertEqual(self.game.scene, 'campaign')
            if victory:
                self.assertIn('city', json.loads(self.path.read_text())['completed'])

    def test_failed_result_clear_keeps_result_available(self):
        b = self.battle()
        b.finished, b.lost = True, True
        with patch.object(self.game.session_store, 'clear', return_value=False):
            self.game.finish_battle()
        self.assertIs(self.game.battle, b)
        self.assertTrue(self.game.can_continue())

    def test_previous_progress_error_does_not_block_defeat_acknowledgement(self):
        b = self.battle()
        b.finished, b.lost = True, True
        self.game.save_error = True
        self.game.finish_battle()
        self.assertIsNone(self.game.battle)
        self.assertEqual(self.game.scene, 'campaign')

    def test_boss_warning_reload_mine_and_detached_references(self):
        b = self.battle('beach')
        b.wave = 4
        b.boss_alert_pending = True
        b.boss_warning = 2.8
        key = REGION_BOSSES['beach'][0]
        b.orders = [SpawnOrder(.5, key, 1, True)]
        b.dead_history = [(key, 1, 800.5)]
        b.defenders[0].ammo = 0
        b.defenders[0].reload_timer = 2.5
        b.defenders[0].reload_total = 3
        b.lane_bombs[1].state = 'rolling'
        b.lane_bombs[1].x = 550
        b.enemies.clear()  # Um projétil ainda referencia o inimigo retirado.
        before = capture(b)
        restored = activate(before, self.game)
        self.assertEqual(capture(restored), before)
        self.assertIsNotNone(restored.projectiles[0].target)
        self.assertNotIn(restored.projectiles[0].target, restored.enemies)

    def test_corrupted_or_incompatible_file_does_not_crash_or_overwrite(self):
        p = self.game.session_store.path
        cases = [b'broken', b'\xff', b'[]', b'{"schema":99}', b'{"schema":true}',
                 b'{"schema":1,"snapshot":42}', b'x' * (MAX_BYTES + 1)]
        for raw in cases:
            with self.subTest(prefix=raw[:25]):
                p.write_bytes(raw)
                with self.assertLogs('svz.session_store', level='ERROR'):
                    self.assertIsNone(self.game.session_store.load())
                self.assertEqual(p.read_bytes(), raw)

    def test_invalid_graph_is_rejected_without_altering_current_rng(self):
        before = capture(self.battle())
        mutations = [
            lambda s: s.update(schema=99),
            lambda s: s['battle'].update(wave=99),
            lambda s: s['battle'].update(selected_card=99),
            lambda s: s['battle'].update(supplies=float('nan')),
            lambda s: s['battle'].update(defenders=[{'ref': 99999}]),
            lambda s: s['objects'][0].update(type='eval'),
            lambda s: s['objects'][0]['fields'].update(row=999),
            lambda s: s['objects'][0]['fields'].update(hp='bad'),
            lambda s: s['battle'].update(card_cooldowns=[]),
        ]
        for mutation in mutations:
            corrupt = copy.deepcopy(before)
            mutation(corrupt)
            rng = random.getstate()
            with self.assertRaises((ValueError, TypeError, KeyError)):
                restore(corrupt, self.game)
            self.assertEqual(random.getstate(), rng)

    def test_all_regional_actors_and_bosses_survive_save_load(self):
        from svz.content import REGION_ROSTERS, REGION_SUBBOSSES
        from svz.entities import Defender
        from svz.content import DEFENSES, DEFENDER_ACTOR_BY_KEY, ENEMY_ACTOR_BY_KEY
        for region in REGIONS:
            b = self.battle(region)
            b.defenders.clear()
            for i, (key, display) in enumerate(REGION_ROSTERS[region]):
                d = Defender(key, display, i // 4, 2 + i % 4, DEFENSES[key], i, region=region)
                actor = DEFENDER_ACTOR_BY_KEY.get(key)
                d.visual_animation = self.game.assets.new_production_animation(actor) if actor else None
                b.defenders.append(d)
            b.enemies.clear()
            keys = REGION_ENEMIES[region] + REGION_SUBBOSSES[region] + REGION_BOSSES[region]
            for i, key in enumerate(keys):
                e = Enemy(key, i % 4, BOSSES.get(key) or ENEMIES[key], region, 12)
                actor = ENEMY_ACTOR_BY_KEY.get(key)
                e.visual_animation = self.game.assets.new_production_animation(actor) if actor else None
                b.enemies.append(e)
            state = capture(b)
            restored = activate(state, self.game)
            self.assertEqual(capture(restored), state)
            self.game.battle = restored
            self.game.draw()
            restored.update(.01)

    def test_invalid_resume_shows_notice_preserves_file(self):
        self.battle()
        self.game.checkpoint()
        raw = self.game.session_store.path.read_bytes()
        self.game.session_store.backup_path.unlink(missing_ok=True)
        self.game.pending_snapshot['objects'][0]['fields']['row'] = 300
        self.game.battle = None
        self.game.scene = 'title'
        with self.assertLogs('svz.app', level='ERROR'):
            self.assertFalse(self.game.resume_battle())
        self.assertEqual(self.game.session_store.path.read_bytes(), raw)
        self.assertFalse(self.game.can_continue())

    def test_menu_and_confirmation_render_with_resume(self):
        self.battle()
        self.game.leave_battle_to_title()
        self.game.draw()
        buttons = self.game.title_buttons()
        self.assertTrue(all(not a[1].colliderect(b[1]) for i,a in enumerate(buttons) for b in buttons[i+1:]))
        for scene in ('confirm_new', 'confirm_exit'):
            self.game.scene = scene
            self.game.draw()

    def test_campaign_file_is_independent_and_legacy_progress_is_preserved(self):
        self.path.write_text('{"completed":["desert"],"best_wave":{"desert":12}}')
        before = self.path.read_bytes()
        self.battle()
        self.game.leave_battle_to_title()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotEqual(self.path, self.game.session_store.path)

if __name__ == '__main__':
    unittest.main()

