import os, unittest, copy, random
from unittest.mock import Mock
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from svz.app import Game
from svz.developer_lab import DeveloperLab
import pygame

class DeveloperLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=Game(integration_preview=True)
        while not cls.app.assets.complete: cls.app.assets.load_next()
    @classmethod
    def tearDownClass(cls): pygame.quit()
    def test_all_units_spawn_and_animate_in_all_scenarios(self):
        app=self.app
        for region in ('city','desert','beach'):
            lab=DeveloperLab(app);lab.region=region;lab.reset()
            for team in ('soldiers','enemies'):
                lab.team=team
                for i,entry in enumerate(lab.entries()):
                    with self.subTest(region=region,unit=entry[0]):
                        lab.reset();lab.index=i;lab.spawn(1,4)
                        lab.animate('move');lab.update(.1)
                        app.developer_lab=lab;app.scene='developer';app.draw()
            lab.close()
    def test_campaign_and_session_untouched(self):
        app=self.app
        campaign=copy.deepcopy(app.save); pending=app.pending_snapshot; battle=app.battle
        state=random.getstate()
        save=Mock();record=Mock()
        original_save=app.session_store.save;original_record=app.score_store.record
        app.session_store.save=save;app.score_store.record=record
        try:
            lab=DeveloperLab(app);app.developer_lab=lab;app.scene='developer'
            lab.spawn(1,2);lab.team='enemies';lab.spawn(1,6)
            lab.paused=False
            for _ in range(180): lab.update(1/60)
            app.checkpoint();app.draw();lab.close()
            save.assert_not_called();record.assert_not_called()
            self.assertEqual(app.save,campaign)
            self.assertIs(app.pending_snapshot,pending)
            self.assertIs(app.battle,battle)
            self.assertEqual(random.getstate(),state)
        finally:
            app.session_store.save=original_save;app.score_store.record=original_record
    def test_catalog_selection_and_unit_controls(self):
        lab=DeveloperLab(self.app)
        lab.action('catalog');lab.action('page_next')
        self.assertLess(lab.index,len(lab.entries()))
        lab.action('pick:0');self.assertFalse(lab.catalog)
        lab.spawn(1,2);unit=lab.selected
        lab.action('damage');self.assertLess(unit.hp,unit.max_hp)
        lab.action('heal');self.assertEqual(unit.hp,unit.max_hp)
        self.assertEqual(unit.ammo,unit.max_ammo)
        lab.action('remove');self.assertFalse(lab.battle.defenders)
        lab.spawn(1,2);lab.action('death');self.assertIsNone(lab.selected)
        lab.action('clear');self.assertTrue(lab.paused)
        self.assertFalse(lab.battle.defenders)
        lab.close()

    def test_step_is_independent_of_speed_and_escape_closes_catalog(self):
        lab=DeveloperLab(self.app);lab.spawn(1,2);lab.animate('idle')
        anim=lab.selected.visual_animation
        anim.update=Mock()
        lab.speed=2;lab.action('step')
        anim.update.assert_called_once_with(1/60)
        self.assertTrue(lab.paused)
        lab.catalog=True;lab.key(pygame.K_ESCAPE)
        self.assertFalse(lab.catalog)
        lab.close()
    def test_demolisher_requires_soldier_within_two_cells(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('bruto')
        lab.spawn(1,6);enemy=lab.selected;b=lab.battle
        for distance,row,hp in ((2*CELL_W+1,1,100),(CELL_W,2,100),(-CELL_W,1,100),(CELL_W,1,0)):
            soldier.row=row;soldier.hp=hp;enemy.x=soldier.x+distance
            b.effects.clear();b.enemy_special(enemy)
            self.assertFalse(b.effects)
            self.assertNotEqual(enemy.motion.state,'skill')
        soldier.row=1;soldier.hp=soldier.max_hp;enemy.x=soldier.x+2*CELL_W
        b.enemy_special(enemy)
        self.assertEqual(enemy.motion.state,'skill')
        self.assertFalse(any(e.kind=='ground_slam' for e in b.effects))
        self.assertEqual(soldier.hp,soldier.max_hp)
        delay=enemy.slam_windup
        b.update_enemies(delay-.01)
        self.assertFalse(any(e.kind=='ground_slam' for e in b.effects))
        b.update_enemies(.011)
        self.assertTrue(any(e.kind=='ground_slam' for e in b.effects))
        self.assertLess(soldier.hp,soldier.max_hp)
        lab.close()
    def test_scientist_launches_only_on_release_pose(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('cientista_helix')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        enemy.x=soldier.x+2*CELL_W
        b.enemy_special(enemy)
        self.assertFalse(b.projectiles)
        delay=enemy.acid_windup
        self.assertGreater(delay,0)
        x=enemy.x
        b.update_enemies(delay-.01)
        self.assertFalse(b.projectiles)
        self.assertEqual(enemy.x,x)
        b.update_enemies(.011)
        self.assertEqual(len(b.projectiles),1)
        self.assertEqual(b.projectiles[0].kind,'acid')
        b.update_enemies(.02)
        self.assertEqual(len(b.projectiles),1)
        lab.close()

    def test_commander_fires_only_on_aim_pose(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('policial')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        enemy.x=soldier.x+2*CELL_W
        b.enemy_special(enemy)
        self.assertFalse(b.projectiles)
        delay=enemy.gun_windup
        self.assertGreater(delay,0)
        x=enemy.x
        b.update_enemies(delay-.01)
        self.assertFalse(b.projectiles)
        self.assertEqual(enemy.x,x)
        b.update_enemies(.011)
        self.assertEqual(len(b.projectiles),1)
        self.assertEqual(b.projectiles[0].kind,'enemy_bullet')
        b.update_enemies(.02)
        self.assertEqual(len(b.projectiles),1)
        lab.close()

    def test_scientist_requires_live_target_within_two_cells(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('cientista_helix')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        try:
            for distance,row,hp in ((2*CELL_W+1,1,100),(CELL_W,2,100),(-CELL_W,1,100),(CELL_W,1,0)):
                soldier.row=row;soldier.hp=hp;enemy.x=soldier.x+distance
                b.enemy_special(enemy)
                self.assertNotEqual(enemy.motion.state,'skill')
                self.assertEqual(enemy.acid_windup,0)
                b.release_enemy_acid(enemy)
                self.assertFalse(b.projectiles)
            soldier.row=1;soldier.hp=soldier.max_hp;enemy.x=soldier.x+2*CELL_W
            b.enemy_special(enemy)
            self.assertEqual(enemy.motion.state,'skill')
            self.assertGreater(enemy.acid_windup,0)
            # Revalidate when the release pose arrives, not only at windup.
            enemy.x+=1
            b.update_enemies(enemy.acid_windup+.001)
            self.assertFalse(b.projectiles)
        finally:
            lab.close()


    def test_commander_requires_live_target_within_two_cells(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('policial')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        try:
            for distance,row,hp in ((2*CELL_W+1,1,100),(CELL_W,2,100),(-CELL_W,1,100),(CELL_W,1,0)):
                soldier.row=row;soldier.hp=hp;enemy.x=soldier.x+distance
                b.enemy_special(enemy)
                self.assertNotEqual(enemy.motion.state,'skill')
                self.assertEqual(enemy.gun_windup,0)
                b.release_enemy_gun(enemy)
                self.assertFalse(b.projectiles)
            soldier.row=1;soldier.hp=soldier.max_hp;enemy.x=soldier.x+2*CELL_W
            b.enemy_special(enemy)
            self.assertEqual(enemy.motion.state,'skill')
            self.assertGreater(enemy.gun_windup,0)
            # Revalidate when the release pose arrives, not only at windup.
            enemy.x+=1
            b.update_enemies(enemy.gun_windup+.001)
            self.assertFalse(b.projectiles)
        finally:
            lab.close()


    def test_commander_and_quarantine_death_have_no_explosion(self):
        for key in ('policial', 'divisor'):
            with self.subTest(unit=key):
                lab=DeveloperLab(self.app)
                try:
                    lab.team='enemies'
                    lab.index=[k for k,n in lab.entries()].index(key)
                    lab.spawn(1,5);enemy=lab.selected;b=lab.battle
                    b.explosion=Mock()
                    b.kill_enemy(enemy)
                    b.explosion.assert_not_called()
                    self.assertNotIn(enemy,b.enemies)
                    self.assertEqual(len(b.fallen),1)
                    self.assertGreater(b.score,0)
                finally:
                    lab.close()

    def test_director_entrance_stuns_without_special_attack(self):
        from svz.content import BOSSES
        self.assertEqual(BOSSES['bruto_demolidor']['hp'],1250)
        self.assertEqual(BOSSES['bruto_demolidor']['speed'],7.5)
        lab=DeveloperLab(self.app)
        try:
            lab.spawn(1,2);soldier=lab.selected
            lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('bruto_demolidor')
            lab.spawn(1,5);enemy=lab.selected;b=lab.battle
            b.effects.clear();soldier.stun=0
            b.boss_entrance(enemy)
            self.assertEqual(soldier.stun,3.0)
            self.assertNotEqual(enemy.motion.state,'skill')
            self.assertFalse(b.effects)
            soldier.stun=0
            b.boss_skill(enemy)
            self.assertEqual(soldier.stun,0)
            self.assertNotEqual(enemy.motion.state,'skill')
            self.assertFalse(b.effects)
        finally: lab.close()

    def test_isotopic_burst_matches_aim_pose(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('comandante_mortos')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        enemy.x=soldier.x+2*CELL_W
        b.enemy_special(enemy)
        self.assertFalse(b.projectiles)
        delay=enemy.gun_windup
        self.assertGreater(delay,0)
        x=enemy.x
        b.update_enemies(delay-.01)
        self.assertFalse(b.projectiles)
        self.assertEqual(enemy.x,x)
        b.update_enemies(.011)
        self.assertEqual(len(b.projectiles),2)
        self.assertEqual(b.projectiles[0].kind,'enemy_bullet')
        b.update_enemies(.02)
        self.assertEqual(len(b.projectiles),2)
        lab.close()

    def test_isotopic_has_no_red_command_circles(self):
        lab=DeveloperLab(self.app)
        try:
            lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('comandante_mortos')
            lab.spawn(1,5);enemy=lab.selected;b=lab.battle
            b.effects.clear()
            b.boss_entrance(enemy)
            self.assertFalse(any(e.kind=='command_aura' for e in b.effects))
            b.release_isotopic_burst(enemy)
            self.assertFalse(any(e.kind=='command_aura' for e in b.effects))
        finally: lab.close()

    def test_isotopic_only_fires_within_four_cells(self):
        from svz.config import CELL_W
        lab=DeveloperLab(self.app);lab.spawn(1,2);soldier=lab.selected
        lab.team='enemies';lab.index=[k for k,n in lab.entries()].index('comandante_mortos')
        lab.spawn(1,5);enemy=lab.selected;b=lab.battle
        try:
            b.boss_entrance(enemy)
            self.assertNotEqual(enemy.motion.state,'skill')
            for distance,row,hp in ((4*CELL_W+1,1,100),(CELL_W,2,100),(-CELL_W,1,100),(CELL_W,1,0)):
                soldier.row=row;soldier.hp=hp;enemy.x=soldier.x+distance
                b.boss_skill(enemy)
                self.assertNotEqual(enemy.motion.state,'skill')
                self.assertEqual(enemy.gun_windup,0)
                b.release_isotopic_burst(enemy)
                self.assertFalse(b.projectiles)
            soldier.row=1;soldier.hp=soldier.max_hp;enemy.x=soldier.x+4*CELL_W
            b.boss_skill(enemy)
            self.assertEqual(enemy.motion.state,'skill')
            b.update_enemies(enemy.gun_windup+.001)
            self.assertEqual(len(b.projectiles),2)
            b.projectiles.clear()
            b.boss_skill(enemy)
            enemy.x+=1
            b.update_enemies(enemy.gun_windup+.001)
            self.assertFalse(b.projectiles)
        finally: lab.close()
