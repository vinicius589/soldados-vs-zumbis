import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SVZ_RENDERER','software')
import pygame
from svz.app import Game
from svz.balance import enemy_damage_scale,boss_damage_scale
from svz.content import REGION_ENEMIES,REGION_BOSSES,ENEMIES,BOSSES,DIFFICULTIES
from svz.entities import Enemy
from svz.snapshot import capture,restore,SCHEMA
from svz.session_store import SessionStore
from svz.persistence import write_json

class FixedStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.game=Game(save_path=Path(cls.tmp.name)/'campaign.json')
        while not cls.game.assets.complete:cls.game.assets.load_next()
        cls.game.audio.set_enabled(False)
    @classmethod
    def tearDownClass(cls):
        pygame.quit();cls.tmp.cleanup()
    def test_every_type_hp_and_attack_are_fixed_across_all_waves_and_modes(self):
        for difficulty in DIFFICULTIES:
            for key,data in {**ENEMIES,**BOSSES}.items():
                samples=[]
                for wave in range(1,13):
                    enemy=Enemy(key,0,data,'city',wave,difficulty=difficulty)
                    scale=boss_damage_scale(wave) if enemy.is_boss else enemy_damage_scale(wave)
                    samples.append((enemy.hp,enemy.max_hp,float(data['damage'])*scale))
                self.assertTrue(all(s==samples[0] for s in samples),(key,difficulty))
    def test_legacy_health_migrates_once_preserving_fraction(self):
        for key in (REGION_ENEMIES['city'][0],REGION_BOSSES['city'][0]):
            for wave in (1,4,12):
                self.game.enter_selection('city');b=self.game.battle;b.wave=wave
                e=Enemy(key,0,BOSSES.get(key) or ENEMIES[key],'city',wave)
                progress=(wave-1)/11
                old_scale=0.78+1.25*progress**1.40 if e.is_boss else 0.66+1.50*progress**1.55
                e.hp=e.max_hp*old_scale*0.4;b.enemies=[e]
                data=capture(b);data['schema']=1
                resumed,_=restore(data,self.game)
                self.assertAlmostEqual(resumed.enemies[0].hp/resumed.enemies[0].max_hp,0.4)
                again,_=restore(capture(resumed),self.game)
                self.assertAlmostEqual(again.enemies[0].hp,resumed.enemies[0].hp)
    def test_legacy_document_loads_then_writes_current_schema(self):
        self.game.enter_selection('city');data=capture(self.game.battle);data['schema']=1
        store=SessionStore(Path(self.tmp.name)/'legacy.json')
        self.assertTrue(write_json({'schema':1,'snapshot':data},store.path))
        restored,_=restore(store.load(),self.game)
        self.assertTrue(store.save(capture(restored)))
        self.assertEqual(store.read_document(store.path)['schema'],SCHEMA)
    def test_ranged_skills_damage_is_independent_of_wave(self):
        for boss in (False,True):
            catalog=BOSSES if boss else ENEMIES
            for key,data in catalog.items():
                if boss and data.get('type') not in ('comandante','alfa'):continue
                if not boss and not ({'gun','acid'} & set(data.get('tags',()))):continue
                samples=[]
                for wave in (1,12):
                    self.game.enter_selection('city');b=self.game.battle;b.supplies=999;b.place(0,2)
                    d=b.defenders[0];d.deployment_x=None;b.wave=wave
                    enemy=Enemy(key,0,data,'city',wave,x=d.x+100)
                    b.enemies=[enemy]
                    if boss:b.boss_skill(enemy)
                    else:b.enemy_special(enemy)
                    samples.append([p.damage for p in b.projectiles])
                self.assertTrue(samples[0],key)
                self.assertEqual(samples[0],samples[1],key)
