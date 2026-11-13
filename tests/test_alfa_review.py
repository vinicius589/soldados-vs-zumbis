"""Regressões dos fluxos de perfil, consumíveis e retomada da Alfa Beta 5."""
import os
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")
import pygame
from svz.app import Game
from svz.scoring import ScoreStore
from svz.session_store import SessionStore
from svz.settings import Settings
from svz.snapshot import capture, restore


class AlfaReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.game = Game(save_path=Path(cls.storage.name) / "boot.json")
        while cls.game.scene == "loading":
            cls.game.update(1 / 60)
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.storage.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        g = self.game
        g.save_path = Path(self.temp.name) / "campanha.json"
        g.settings = Settings(g.save_path)
        g.score_store = ScoreStore(g.save_path)
        g.session_store = SessionStore(g.save_path)
        g.player_name = "Ana"
        g.running = True
        g.suspended_random = None
        g.navigation.scene = None
        g.enter_selection("city")
        self.b = g.battle
        self.b.supplies = 999
        self.assertTrue(self.b.place(0, 2))
        self.target = self.b.defenders[0]
        self.target.deployment_x = None
        self.target.hp = self.target.max_hp / 2

    def stock(self, item):
        store = self.game.score_store
        store.ensure_profile("Ana")
        with closing(store.connect()) as db, db:
            db.execute("UPDATE player_profiles SET credits = 1000")
        self.assertTrue(store.buy("Ana", item))

    def test_empty_inventory_click_reports_error_without_crashing(self):
        for key in (pygame.K_h, pygame.K_t):
            with self.subTest(key=key):
                self.game.handle_key(key)
                self.game.handle_click(self.target.hitbox().center)
                self.assertIsNone(self.game.pending_powerup)
                self.assertIn("não tem", self.game.score_store.error)

    def test_medkit_heals_once_and_snapshot_preserves_health(self):
        self.stock("medkit")
        before = self.target.hp
        self.game.handle_key(pygame.K_h)
        self.game.handle_click(self.target.hitbox().center)
        self.assertGreater(self.target.hp, before)
        self.assertEqual(self.game.score_store.profile("Ana")["medkits"], 0)
        resumed, _ = restore(capture(self.b), self.game)
        self.assertEqual(resumed.defenders[0].hp, self.target.hp)

    def test_ammo_is_applied_and_persists_in_snapshot(self):
        self.stock("tactical_ammo")
        self.game.handle_key(pygame.K_t)
        self.game.handle_click(self.target.hitbox().center)
        self.assertEqual(self.target.tactical_ammo_timer, 30)
        self.assertEqual(self.game.score_store.profile("Ana")["tactical_ammo"], 0)
        resumed, _ = restore(capture(self.b), self.game)
        self.assertEqual(resumed.defenders[0].tactical_ammo_timer, 30)

    def test_paused_or_finished_battle_cannot_consume_item(self):
        self.stock("medkit")
        self.game.pending_powerup = "medkit"
        before = self.target.hp
        for field in ("paused", "finished"):
            setattr(self.b, field, True)
            self.assertFalse(self.game.try_use_powerup(self.target.hitbox().center))
            setattr(self.b, field, False)
        self.assertEqual(self.target.hp, before)
        self.assertEqual(self.game.score_store.profile("Ana")["medkits"], 1)

    def test_resume_uses_active_profile_in_memory_and_on_disk(self):
        self.game.checkpoint()
        self.game.player_name = "Beto"
        self.assertTrue(self.game.resume_battle())
        self.assertEqual(self.game.battle.player_name, "Beto")
        self.game.battle = None
        self.assertTrue(self.game.resume_battle())
        self.assertEqual(self.game.battle.player_name, "Beto")

    def test_profile_registration_does_not_bypass_replace_confirmation(self):
        self.game.player_name = ""
        match_id = self.b.match_id
        self.game.request_new_game()
        self.assertEqual(self.game.scene, "profile")
        self.game.profile_name_draft = "Beto"
        self.assertTrue(self.game.save_profile())
        self.assertEqual(self.game.scene, "confirm_new")
        self.game.handle_key(pygame.K_RETURN)
        self.assertEqual(self.game.scene, "title")
        self.assertEqual(self.game.battle.match_id, match_id)

    def test_powerup_selection_clears_when_leaving_or_starting_battle(self):
        self.game.pending_powerup = "medkit"
        self.game.leave_battle_to_title()
        self.assertIsNone(self.game.pending_powerup)
        self.game.pending_powerup = "tactical_ammo"
        self.game.enter_selection("city")
        self.assertIsNone(self.game.pending_powerup)

    def test_consumable_shortcuts_cannot_be_assigned_to_other_actions(self):
        for key in (pygame.K_h, pygame.K_t):
            self.assertFalse(self.game.settings.assign("pause", key))
        self.game.settings.bindings["pause"] = pygame.K_h
        self.game.settings.save()
        self.assertNotEqual(Settings(self.game.save_path).bindings["pause"], pygame.K_h)

    def test_invalid_stored_profile_does_not_skip_registration(self):
        self.game.settings.player_name = "!!!"
        self.game.settings.save()
        self.assertEqual(Settings(self.game.save_path).player_name, "")

    def test_scores_keyboard_can_switch_view_and_return(self):
        self.game.scene = "scores"
        self.game.score_view = "ranking"
        self.game.handle_key(pygame.K_TAB)
        self.game.handle_key(pygame.K_RETURN)
        self.assertEqual(self.game.score_view, "history")
        self.game.handle_key(pygame.K_UP)
        self.game.handle_key(pygame.K_RETURN)
        self.assertEqual(self.game.scene, "title")

    def test_checkpoint_reports_score_failure_but_keeps_recoverable_snapshot(self):
        self.b.finished = True
        self.game.score_store.error = "Banco indisponível"
        with patch.object(self.game.score_store, "record", return_value=False):
            self.assertFalse(self.game.checkpoint())
        self.assertEqual(self.game.session_notice, "Banco indisponível")
        self.assertIsNotNone(self.game.session_store.load())
