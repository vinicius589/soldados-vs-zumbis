"""Layout e interações reais do HUD compacto, incluindo texto ampliado."""
import math
import os
import unittest
from itertools import combinations
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SVZ_RENDERER','software')

import pygame
from svz.app import Game
from svz import hud_layout as hud
from svz.board import cell_center
from svz.config import LANE_BOUNDS, TOTAL_WAVES
from svz.content import REGION_ROSTERS


class HudLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=Game(integration_preview=True)
        while not cls.game.assets.complete: cls.game.assets.load_next()
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def battle(self,region='city'):
        self.game.enter_selection(region)
        self.game.control_mode='mouse'
        return self.game.battle

    def test_hud_regions_do_not_overlap_and_stay_on_screen(self):
        screen=pygame.Rect(0,0,1280,720)
        rects=[hud.supplies_rect(),*hud.card_rects(8),hud.remove_rect(),hud.menu_rect(),hud.pause_rect(),hud.waves_rect(),hud.next_wave_rect()]
        for rect in rects:self.assertTrue(screen.contains(rect))
        for left,right in combinations(rects,2):self.assertFalse(left.colliderect(right),(left,right))
        self.assertLess(hud.supplies_rect().right,hud.card_rects(8)[0].left)
        self.assertGreater(hud.menu_rect().left,hud.remove_rect().right)
        self.assertGreater(hud.waves_rect().top,max(bounds[-1] for bounds in LANE_BOUNDS.values()))

    def test_clicks_select_all_eight_cards_in_three_maps(self):
        for region in REGION_ROSTERS:
            b=self.battle(region)
            for index,rect in enumerate(b.card_rects()):
                self.game.handle_click(rect.center)
                self.assertEqual(b.selected_card,index)
                self.assertFalse(b.defenders)

    def test_remove_then_place_and_pause_buttons_use_new_hitboxes(self):
        b=self.battle();b.supplies=999
        self.game.handle_click(cell_center(0,2,'city'))
        self.assertEqual(len(b.defenders),1)
        self.game.handle_click(b.remove_rect().center)
        self.assertTrue(b.remove_mode)
        supplies_before=b.supplies
        expected_refund=math.ceil(float(b.defenders[0].stats['cost'])*0.35)
        self.game.handle_click(cell_center(0,2,'city'))
        self.assertFalse(b.defenders)
        self.assertEqual(b.supplies,supplies_before+expected_refund)
        self.game.handle_click(b.pause_rect().center)
        self.assertTrue(b.paused)
        self.game.handle_click(b.pause_rect().center)
        self.assertFalse(b.paused)

    def test_recall_button_uses_base_language_and_not_shovel_label(self):
        self.battle()
        renderer=self.game.renderer
        with patch.object(renderer,'draw_text',wraps=renderer.draw_text) as text:
            renderer.draw_battle_top()
        labels=[call.args[0] for call in text.call_args_list]
        self.assertIn("VOLTAR À BASE",labels)
        self.assertIn("35% DEVOLVIDO",labels)
        self.assertNotIn("REMOVER",labels)

    def test_long_base_button_label_fits_existing_hud_button(self):
        rect=hud.remove_rect()
        font=self.game.renderer._fit_button_font("VOLTAR À BASE",rect)
        self.assertLessEqual(font.size("VOLTAR À BASE")[0],rect.width-14)
        self.assertLess(font.get_height(),self.game.fonts.h2.get_height())

    def test_recall_mode_uses_base_message(self):
        b=self.battle()
        self.game.handle_click(b.remove_rect().center)
        self.assertTrue(b.remove_mode)
        self.assertIn("Voltar à base",b.message)
        self.game.handle_click(b.remove_rect().center)
        self.assertFalse(b.remove_mode)
        self.assertIn("Retorno à base desativado",b.message)

    def test_menu_keeps_battle_for_continue(self):
        b=self.battle()
        with patch.object(self.game,'checkpoint',return_value=True):
            self.game.handle_click(b.menu_rect().center)
        self.assertEqual(self.game.scene,'title')
        self.assertIs(self.game.battle,b)

    def test_next_wave_advances_once_and_counter_ignores_click(self):
        b=self.battle()
        self.game.handle_click(hud.waves_rect().center)
        self.assertEqual(b.wave,0)
        self.game.handle_click(b.next_wave_rect().center)
        self.assertEqual(b.wave,1)
        self.game.handle_click(b.next_wave_rect().center)
        self.assertEqual(b.wave,1)

    def test_wave_bar_reports_completed_waves_and_victory(self):
        b=self.battle()
        self.assertEqual(hud.wave_progress(b),0)
        b.wave=4;b.started_wave=True
        self.assertEqual(hud.wave_progress(b),3/TOTAL_WAVES)
        b.started_wave=False
        self.assertEqual(hud.wave_progress(b),4/TOTAL_WAVES)
        b.wave=TOTAL_WAVES;b.started_wave=True;b.victory=True
        self.assertEqual(hud.wave_progress(b),1)

    def test_tooltip_keeps_metrics_for_keyboard_and_mouse(self):
        self.battle();self.game.control_mode='keyboard';self.game.show_card_info=True
        renderer=self.game.renderer
        with patch.object(renderer,'draw_text',wraps=renderer.draw_text) as text:
            self.game.draw()
        labels=[call.args[0] for call in text.call_args_list]
        self.assertTrue(any('DANO' in label for label in labels))
        self.game.control_mode='mouse'
        with patch.object(self.game.video,'mouse_position',return_value=self.game.battle.card_rects()[0].center), patch.object(renderer,'draw_text',wraps=renderer.draw_text) as text:
            self.game.draw()
        self.assertTrue(any('DANO' in call.args[0] for call in text.call_args_list))
