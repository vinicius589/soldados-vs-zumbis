import math,os,tempfile,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SVZ_RENDERER','software')
import pygame
from svz.app import Game
from svz.content import DEFENSES,DIFFICULTIES,REGION_ENEMIES,REGION_SUBBOSSES,REGION_BOSSES,ENEMIES,BOSSES
from svz.entities import Enemy
from svz.snapshot import capture,restore

class UnlimitedSuppliesTests(unittest.TestCase):
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
        self.game.battle.supplies=10**15
        return self.game.battle
    def test_generator_delivers_full_amount_above_old_caps(self):
        for region in REGION_ENEMIES:
            for difficulty in DIFFICULTIES:
                b=self.battle(region,difficulty)
                b.selected_card=next(i for i,(key,_) in enumerate(b.selected) if DEFENSES[key]['role']=='radio')
                b.place(0,2);d=b.defenders[0];d.utility_timer=0
                before=b.supplies;b.utility_defender(d,0)
                self.assertEqual(b.supplies,before+12)
                self.assertEqual(d.utility_timer,12)
    def test_common_subboss_and_boss_rewards_have_no_cap(self):
        for difficulty in DIFFICULTIES:
            for kind,keys in [('common',REGION_ENEMIES),('sub',REGION_SUBBOSSES),('boss',REGION_BOSSES)]:
                b=self.battle(difficulty=difficulty);b.wave=4
                key=keys['city'][0];enemy=Enemy(key,0,BOSSES.get(key) or ENEMIES[key],'city',4,difficulty=difficulty)
                b.enemies.append(enemy);before=b.supplies
                gain=1 if kind=='common' else round((18 if kind=='sub' else 54)*b.difficulty_data['supply_gain'])
                b.kill_enemy(enemy);self.assertEqual(b.supplies,before+gain)
    def test_wave_completion_delivers_full_reward_once(self):
        for difficulty in DIFFICULTIES:
            b=self.battle(difficulty=difficulty);b.wave=4;b.started_wave=True
            before=b.supplies;gain=round(23*b.difficulty_data['supply_gain'])+round(14*b.difficulty_data['supply_gain'])
            b.update_wave(0);self.assertEqual(b.supplies,before+gain)
            b.update_wave(0);self.assertEqual(b.supplies,before+gain)
    def test_large_reserve_survives_resume_and_still_pays_costs(self):
        b=self.battle();resumed,_=restore(capture(b),self.game)
        self.assertEqual(resumed.supplies,10**15)
        key=resumed.selected[0][0];resumed.place(0,2)
        self.assertEqual(resumed.supplies,10**15-DEFENSES[key]['cost'])
        resumed.remove_defender(0,2)
        self.assertEqual(resumed.supplies,10**15-DEFENSES[key]['cost']+math.ceil(DEFENSES[key]['cost']*.35))
    def test_invalid_reserves_are_rejected(self):
        b=self.battle()
        for value in (-1,True,1.5):
            data=capture(b);data['battle']['supplies']=value
            with self.assertRaises(ValueError):restore(data,self.game)
    def test_hud_renders_large_reserve_in_both_text_sizes(self):
        from svz.assets import FontBook
        self.battle()
        for large in (False,True):
            self.game.fonts=FontBook(large);self.game.draw()
        self.assertTrue(all('supply_cap' not in profile for profile in DIFFICULTIES.values()))
