import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SVZ_RENDERER','software')
import pygame
from svz.app import Game
from svz.snapshot import capture,restore
from svz.content import REGION_ENEMIES,DIFFICULTIES

class FirstWaveCountdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.game=Game(save_path=Path(cls.tmp.name)/'campaign.json')
        while not cls.game.assets.complete:cls.game.assets.load_next()
        cls.game.audio.set_enabled(False)
    @classmethod
    def tearDownClass(cls):pygame.quit();cls.tmp.cleanup()
    def battle(self,region='city',difficulty='medium'):
        self.game.difficulty=difficulty;self.game.enter_selection(region)
        return self.game.battle
    def test_auto_start_and_first_zombie_only_after_five_seconds_all_modes(self):
        for region in REGION_ENEMIES:
            for difficulty in DIFFICULTIES:
                b=self.battle(region,difficulty);b.update_wave(0)
                self.assertEqual(b.wave,1);self.assertEqual(b.first_wave_countdown,5)
                for _ in range(49):b.update_wave(.1)
                self.assertFalse(b.enemies)
                b.update_wave(.1)
                self.assertEqual(len(b.enemies),1)
                self.assertEqual(b.first_wave_countdown,0)
    def test_manual_start_cannot_skip_or_restart_countdown(self):
        b=self.battle();self.assertTrue(b.start_next_wave())
        b.update_wave(2);remaining=b.first_wave_countdown
        self.assertFalse(b.start_next_wave())
        self.game.handle_click(b.next_wave_rect().center)
        self.assertEqual(b.first_wave_countdown,remaining)
        self.assertFalse(b.enemies)
    def test_pause_freezes_countdown(self):
        b=self.battle();b.start_next_wave();b.update_wave(2)
        b.paused=True;b.update(10)
        self.assertEqual(b.first_wave_countdown,3)
        self.assertFalse(b.enemies)
        b.paused=False;b.update_wave(3)
        self.assertEqual(len(b.enemies),1)
    def test_resume_preserves_remaining_time_without_reset(self):
        b=self.battle();b.start_next_wave();b.update_wave(2)
        resumed,_=restore(capture(b),self.game)
        self.assertEqual(resumed.first_wave_countdown,3)
        resumed.update_wave(2.9);self.assertFalse(resumed.enemies)
        resumed.update_wave(.1);self.assertEqual(len(resumed.enemies),1)
    def test_later_waves_keep_original_spawn_timing(self):
        b=self.battle();b.wave=1;b.start_next_wave()
        self.assertEqual(b.wave,2);self.assertEqual(b.first_wave_countdown,0)
        b.update_wave(.34);self.assertFalse(b.enemies)
        b.update_wave(.02);self.assertEqual(len(b.enemies),1)
    def test_old_save_does_not_restart_already_running_wave(self):
        b=self.battle();b.start_next_wave();b.first_wave_countdown=0
        data=capture(b);data['schema']=1;del data['battle']['first_wave_countdown']
        resumed,_=restore(data,self.game)
        self.assertEqual(resumed.first_wave_countdown,0)
    def test_invalid_countdown_is_rejected(self):
        b=self.battle()
        for value in (-1,6,True,'5'):
            data=capture(b);data['battle']['first_wave_countdown']=value
            with self.assertRaises(ValueError):restore(data,self.game)
    def test_hud_shows_countdown(self):
        b=self.battle();b.start_next_wave()
        with patch.object(self.game.renderer,'draw_text',wraps=self.game.renderer.draw_text) as text:self.game.draw()
        self.assertIn('ONDA 1 EM 5s',[call.args[0] for call in text.call_args_list])
