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
