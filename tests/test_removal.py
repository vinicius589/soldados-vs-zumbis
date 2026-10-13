"""Regressões do botão REMOVER em todos os mapas e dificuldades."""
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")
import pygame

from svz.app import Game
from svz.content import REGIONS
from svz.session_store import SessionStore


class RemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.game = Game(save_path=Path(cls.directory.name) / "campaign.json")
        while not cls.game.assets.complete:
            cls.game.assets.load_next()
        cls.game.assets.prepare_production_animations()
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.directory.cleanup()

    def battles(self):
        for region in REGIONS:
            for difficulty in ("easy", "medium", "hard"):
                g = self.game
                g.difficulty = difficulty
                g.control_mode = "mouse"
                g.enter_selection(region)
                b = g.battle
                b.supplies = 999
                b.place(0, 2)
                b.defenders[0].deployment_x = None
                yield region, difficulty, b

    def test_button_is_visible_and_does_not_overlap_other_buttons(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                renderer = self.game.renderer
                with patch.object(renderer, "button", wraps=renderer.button) as drawn:
                    self.game.draw()
                buttons = [call.args for call in drawn.call_args_list if call.args[0] == "REMOVER"]
                self.assertEqual(len(buttons), 1)
                self.assertEqual(buttons[0][1], b.remove_rect())
                for rect in (b.menu_rect(), b.pause_rect(), b.next_wave_rect()):
                    self.assertFalse(b.remove_rect().colliderect(rect))

    def test_mouse_removes_only_selected_unit_and_refunds_once(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                removed = b.defenders[0]
                b.place(0, 4)
                self.assertEqual(len(b.defenders), 2)
                other = b.defenders[-1]
                before = b.supplies
                refund = math.ceil(removed.stats["cost"] * .35)
                self.game.handle_click(b.remove_rect().center)
                self.assertTrue(b.remove_mode)
                self.game.handle_click(b.ground_cell_rect(0, 2).center)
                self.assertEqual(b.defenders, [other])
                self.assertEqual(b.supplies, before + refund)
                self.game.handle_click(b.ground_cell_rect(0, 2).center)
                self.assertEqual(b.supplies, before + refund)

    def test_keyboard_shortcut_and_confirmation_remove_unit(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                self.game.control_mode = "keyboard"
                b.keyboard_row, b.keyboard_col = 0, 2
                self.game.handle_key(pygame.K_r)
                self.assertTrue(b.remove_mode)
                self.game.handle_key(pygame.K_RETURN)
                self.assertEqual(b.defenders, [])

    def test_button_toggles_off_and_card_selection_cancels_removal(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                self.game.handle_click(b.remove_rect().center)
                self.assertTrue(b.remove_mode)
                self.game.handle_click(b.remove_rect().center)
                self.assertFalse(b.remove_mode)
                self.game.handle_key(pygame.K_r)
                self.assertTrue(b.remove_mode)
                self.game.handle_key(pygame.K_2)
                self.assertFalse(b.remove_mode)
                self.assertEqual(len(b.defenders), 1)

    def test_mouse_does_not_remove_while_paused_or_finished(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                self.game.handle_click(b.remove_rect().center)
                self.assertTrue(b.remove_mode)
                before = b.supplies
                b.paused = True
                self.game.handle_click(b.ground_cell_rect(0, 2).center)
                b.paused, b.finished = False, True
                b.handle_click(b.ground_cell_rect(0, 2).center)
                self.assertEqual(len(b.defenders), 1)
                self.assertEqual(b.supplies, before)

    def test_disk_resume_preserves_removal_and_saved_removal_stays_removed(self):
        for region, difficulty, b in self.battles():
            with self.subTest(region=region, difficulty=difficulty):
                g = self.game
                g.handle_click(b.remove_rect().center)
                self.assertTrue(b.remove_mode)
                g.leave_battle_to_title()
                g.battle = None
                g.pending_snapshot = SessionStore(g.save_path).load()
                self.assertTrue(g.resume_battle())
                b = g.battle
                self.assertTrue(b.paused)
                self.assertTrue(b.remove_mode)
                g.handle_click(b.pause_rect().center)
                g.handle_click(b.ground_cell_rect(0, 2).center)
                self.assertEqual(b.defenders, [])
                supplies = b.supplies
                g.leave_battle_to_title()
                g.battle = None
                g.pending_snapshot = SessionStore(g.save_path).load()
                self.assertTrue(g.resume_battle())
                self.assertEqual(g.battle.defenders, [])
                self.assertEqual(g.battle.supplies, supplies)


if __name__ == "__main__":
    unittest.main()

