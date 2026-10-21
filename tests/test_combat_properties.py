"""Contratos gerados automaticamente; exemplos reprodutíveis e sem sleeps."""
import copy
import math
import os
import random
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('SVZ_RENDERER', 'software')

from hypothesis import given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from svz.battle import Battle
from svz.board import terrain_y
from svz.content import ENEMIES, DEFENSES, REGION_ROSTERS, BOSSES
from svz.entities import Enemy, Defender, Projectile
from svz.projectile_combat import resolve_impact, update_aim, EXPLOSIVE_KINDS
from svz.timing import FixedStepper

GENERATED = settings(max_examples=150, derandomize=True, deadline=None, database=None)


def enemy(x=500, row=0, region='city'):
    return Enemy('infectado_urbano', row, ENEMIES['infectado_urbano'], region, 1, x=x)


def arena(population, region='city'):
    return SimpleNamespace(region=region, enemies=population, defenders=[], effects=[],
                           take_enemy_damage=Mock(), damage_defender=Mock(), explosion=Mock(), projectiles=[])


def shot(target, **kwargs):
    return Projectile(200, target.y-16, target, target.x, target.y-16, 20,
                      kwargs.pop('kind', 'grenade_40mm'), kwargs.pop('owner', None), **kwargs)


class ImpactProperties(unittest.TestCase):
    @GENERATED
    @given(region=st.sampled_from(['city', 'desert', 'beach']),
           row=st.integers(0, 3), radius=st.integers(1, 150),
           coordinates=st.lists(st.tuples(st.integers(-200, 200), st.integers(0, 3)), min_size=1, max_size=12),
           kind=st.sampled_from(sorted(EXPLOSIVE_KINDS)))
    def test_area_matches_geometric_oracle_without_primary(self, region, row, radius, coordinates, kind):
        target=enemy(row=row, region=region)
        actors=[enemy(500+offset, lane, region) for offset,lane in coordinates]
        b=arena(actors, region)
        p=shot(target, kind=kind, radius=radius)
        resolve_impact(b,p)
        expected=[id(e) for e,(offset,lane) in zip(actors,coordinates) if lane==row and -radius<offset<radius]
        calls=b.take_enemy_damage.call_args_list
        self.assertEqual([id(c.args[0]) for c in calls],expected)
        for call in calls: self.assertAlmostEqual(call.args[1],14.4)

    @GENERATED
    @given(region=st.sampled_from(['city','desert','beach']), row=st.integers(0,3))
    def test_fixed_impact_lane_does_not_follow_actor(self, region, row):
        target=enemy(row=row,region=region)
        p=shot(target,radius=80)
        original_lane_victim=enemy(520,row,region)
        target.row=(row+1)%4
        b=arena([target,original_lane_victim],region)
        resolve_impact(b,p)
        self.assertEqual([id(c.args[0]) for c in b.take_enemy_damage.call_args_list],[id(original_lane_victim)])

    def test_aim_requires_identity_not_equal_dataclass(self):
        target=enemy()
        twin=copy.deepcopy(target)
        self.assertEqual(twin,target)
        b=arena([twin])
        p=shot(target,kind='rifle')
        p.target_x=480
        update_aim(b,p)
        self.assertEqual(p.target_x,480)

    def test_targetless_area_uses_destination_not_owner_lane(self):
        victim=enemy(row=2)
        p=shot(victim,radius=80,owner=enemy(row=0))
        p.target=None
        b=arena([victim])
        resolve_impact(b,p)
        self.assertEqual(b.take_enemy_damage.call_count,1)

    def test_targetless_area_without_owner(self):
        victim=enemy(row=2)
        p=shot(victim,radius=80)
        p.target=None
        b=arena([victim])
        resolve_impact(b,p)
        self.assertEqual(b.take_enemy_damage.call_count,1)

    def test_dead_enemy_is_never_damaged(self):
        target=enemy(); target.hp=0
        b=arena([target]); resolve_impact(b,shot(target,radius=80))
        b.take_enemy_damage.assert_not_called()

    def test_hostile_and_friendly_populations_are_separate(self):
        target=enemy(); b=arena([target])
        resolve_impact(b,shot(target,radius=80,friendly=False))
        b.take_enemy_damage.assert_not_called(); b.damage_defender.assert_not_called()

    def test_direct_shot_and_stream_follow_live_target(self):
        for kind in ('rifle','flame','poison','waterjet'):
            with self.subTest(kind=kind):
                target=enemy(); p=shot(target,kind=kind,radius=30 if kind!='rifle' else 0)
                b=arena([target]); target.x+=100
                update_aim(b,p); resolve_impact(b,p)
                self.assertEqual(p.target_x,target.x)
                self.assertEqual(b.take_enemy_damage.call_args.args[1],20)

    def test_hostile_direct_aim_and_impact_variants(self):
        key,label=REGION_ROSTERS['city'][0]
        target=Defender(key,label,0,2,DEFENSES[key],0)
        for kind,visual in [('acid','toxic_impact'),('torpedo','water_impact'),('rifle','ballistic_impact')]:
            with self.subTest(kind=kind):
                b=arena([]); b.defenders=[target]
                p=shot(target,kind=kind,friendly=False)
                update_aim(b,p); resolve_impact(b,p)
                self.assertEqual(p.target_y,target.y-12)
                self.assertEqual(b.effects[0].kind,visual)
                b.damage_defender.assert_called_once_with(target,20,'')

    def test_boss_splash_preserves_vertical_limit(self):
        key,label=REGION_ROSTERS['city'][0]
        target=Defender(key,label,0,2,DEFENSES[key],0)
        other=Defender(key,label,1,2,DEFENSES[key],0)
        bosskey=next(iter(BOSSES))
        boss=Enemy(bosskey,0,BOSSES[bosskey],'city',4,x=800)
        b=arena([]); b.defenders=[target,other]
        p=shot(target,kind='acid',friendly=False,radius=100,owner=boss)
        p.target_y=target.y-12
        resolve_impact(b,p)
        from svz.config import CELL_H
        expected=2 if abs(other.y-target.y)<CELL_H*.75 else 1
        self.assertEqual(b.damage_defender.call_count,expected)

    @GENERATED
    @given(dt=st.sampled_from([float('nan'),float('inf'),float('-inf'),-.1]))
    def test_invalid_projectile_delta_is_rejected_before_mutation(self,dt):
        target=enemy(); b=arena([target]); p=shot(target,radius=80); b.projectiles=[p]
        with self.assertRaises(ValueError): Battle.update_projectiles(b,dt)
        self.assertEqual(p.elapsed,0)
        self.assertEqual(len(b.projectiles),1)
        b.take_enemy_damage.assert_not_called()


class TimingContracts(unittest.TestCase):
    def test_invalid_configuration(self):
        for step in (0,-1,float('nan'),float('inf')):
            with self.subTest(step=step),self.assertRaises(ValueError): FixedStepper(step=step)
        for maximum in (0,-1,True,1.5):
            with self.subTest(maximum=maximum),self.assertRaises(ValueError): FixedStepper(max_steps=maximum)
        with self.assertRaises(ValueError): FixedStepper(step=1e308,max_steps=10)

    def test_nonfinite_input_does_not_poison_clock(self):
        for seconds in (float('nan'),float('inf'),float('-inf')):
            clock=FixedStepper()
            with self.subTest(seconds=seconds),self.assertRaises(ValueError): clock.advance(seconds,lambda dt:None)
            self.assertEqual(clock.remainder,0)
            self.assertEqual(clock.dropped_seconds,0)


class ClockMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.clock=FixedStepper()
        self.received=0.
        self.delivered=0.

    @rule(milliseconds=st.integers(-100,2000))
    def advance(self,milliseconds):
        seconds=milliseconds/1000
        self.received+=max(0,seconds)
        def consume(step): self.delivered+=step
        count=self.clock.advance(seconds,consume)
        assert 0<=count<=15

    @invariant()
    def time_is_conserved_and_backlog_is_bounded(self):
        assert 0<=self.clock.remainder<self.clock.step+1e-9
        assert math.isclose(self.received,self.delivered+self.clock.remainder+self.clock.dropped_seconds,abs_tol=1e-8)


TestClockMachine=ClockMachine.TestCase
TestClockMachine.settings=settings(max_examples=100,stateful_step_count=60,derandomize=True,deadline=None,database=None)


class SnapshotProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from svz.app import Game
        from svz.snapshot import capture
        cls.app=Game(integration_preview=True)
        while not cls.app.assets.complete: cls.app.assets.load_next()
        cls.app.enter_selection('city')
        b=cls.app.battle
        target=enemy(); b.enemies.append(target); b.projectiles.append(shot(target,radius=80))
        cls.saved=capture(b)

    @classmethod
    def tearDownClass(cls):
        import pygame
        pygame.quit()

    @GENERATED
    @given(field=st.sampled_from(['travel','damage','radius']),value=st.floats(min_value=-1e6,max_value=-1e-6,allow_nan=False,allow_infinity=False))
    def test_negative_projectile_parameters_rejected_without_side_effects(self,field,value):
        from svz.snapshot import restore
        saved=copy.deepcopy(self.saved)
        node=next(n for n in saved['objects'] if n['type']=='Projectile')
        node['fields'][field]=value
        active=self.app.battle; rng=random.getstate()
        with self.assertRaises(ValueError): restore(saved,self.app)
        self.assertIs(self.app.battle,active)
        self.assertEqual(random.getstate(),rng)

    def test_zero_travel_rejected(self):
        from svz.snapshot import restore
        saved=copy.deepcopy(self.saved)
        next(n for n in saved['objects'] if n['type']=='Projectile')['fields']['travel']=0
        with self.assertRaises(ValueError): restore(saved,self.app)

    @GENERATED
    @given(travel=st.floats(min_value=.01,max_value=20,allow_nan=False,allow_infinity=False),
           delay=st.floats(min_value=-5,max_value=0,allow_nan=False,allow_infinity=False))
    def test_valid_delayed_zero_damage_projectile_roundtrip(self,travel,delay):
        from svz.snapshot import restore
        saved=copy.deepcopy(self.saved)
        fields=next(n for n in saved['objects'] if n['type']=='Projectile')['fields']
        fields.update(travel=travel,elapsed=delay,damage=0,radius=0)
        restored,_=restore(saved,self.app)
        p=restored.projectiles[0]
        self.assertEqual((p.travel,p.elapsed,p.damage,p.radius),(travel,delay,0,0))

    @GENERATED
    @given(value=st.one_of(st.none(),st.booleans(),st.text(max_size=15),st.sampled_from([float('nan'),float('inf')]),st.lists(st.integers(),max_size=3)))
    def test_wrong_numeric_types_rejected(self,value):
        from svz.snapshot import restore
        saved=copy.deepcopy(self.saved)
        next(n for n in saved['objects'] if n['type']=='Projectile')['fields']['travel']=value
        with self.assertRaises((ValueError,TypeError)): restore(saved,self.app)
