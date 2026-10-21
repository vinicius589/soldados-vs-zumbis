"""Pontuação real, retomada, resultados persistentes e navegação do histórico."""
import copy
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SVZ_RENDERER','software')
import pygame
from svz.app import Game
from svz.content import ENEMIES, BOSSES
from svz.entities import Enemy
from svz.scoring import SCORE_TABLE, ScoreStore, points_for
from svz.session_store import SessionStore
from svz.snapshot import capture, restore

class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.game = Game(save_path=Path(cls.temp.name)/'initial.json')
        while not cls.game.assets.complete: cls.game.assets.load_next()
        cls.game.audio.set_enabled(False)
    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.temp.cleanup()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        g=self.game
        g.save_path=Path(self.tmp.name)/'campanha.json'
        g.score_store=ScoreStore(g.save_path)
        g.session_store=SessionStore(g.save_path)
        g.enter_selection('city')
        self.b=g.battle
    def test_each_regional_type_awards_10_through_120_once(self):
        for region,table in SCORE_TABLE.items():
            self.assertEqual(list(table.values()),list(range(10,121,10)))
            self.game.enter_selection(region)
            b=self.game.battle
            for key,points in table.items():
                enemy=Enemy(key,0,BOSSES.get(key) or ENEMIES[key],region,1)
                b.enemies.append(enemy)
                before=b.score
                b.kill_enemy(enemy)
                self.assertEqual(b.score,before+points)
                b.kill_enemy(enemy)
                self.assertEqual(b.score,before+points)
            self.assertEqual(b.score,780)
    def test_summons_are_basic_ten_points(self):
        for key in ('necromante_minion','caminhante','boia'):
            self.assertEqual(points_for('city',key),10)
    def test_resume_preserves_score_and_match_identity(self):
        self.b.score=570
        resumed,_=restore(capture(self.b),self.game)
        self.assertEqual((resumed.score,resumed.match_id),(570,self.b.match_id))
    def test_old_save_migrates_to_zero_with_stable_identity(self):
        data=capture(self.b)
        del data['battle']['score'];del data['battle']['match_id']
        a,_=restore(data,self.game);b,_=restore(data,self.game)
        self.assertEqual(a.score,0)
        self.assertEqual(a.match_id,b.match_id)
        self.assertNotIn('score',data['battle'])
    def test_malformed_score_and_id_rejected(self):
        for field,values in (('score',(-1,True,2.5,10**13)),('match_id',('', 'z'*32,42))):
            for value in values:
                data=capture(self.b);data['battle'][field]=value
                with self.assertRaises(ValueError):restore(data,self.game)
    def test_partial_score_fields_are_rejected(self):
        data=capture(self.b);del data['battle']['score']
        with self.assertRaises(ValueError):restore(data,self.game)
    def test_unfinished_match_is_not_recorded(self):
        self.assertFalse(self.game.score_store.record(self.b))
        self.assertEqual(self.game.score_store.page(),([],0))
    def test_victory_and_defeat_persist_once_even_after_restart(self):
        store=self.game.score_store
        for victory in (False,True):
            self.game.enter_selection('city');b=self.game.battle
            b.finished=True;b.victory=victory;b.score=780;b.wave=12
            self.assertTrue(store.record(b));self.assertTrue(store.record(b))
            self.assertTrue(ScoreStore(self.game.save_path).record(b))
        rows,total=ScoreStore(self.game.save_path).page()
        self.assertEqual(total,2)
        self.assertEqual([r[5] for r in rows],[1,0])
        self.assertTrue(all(r[6]==780 for r in rows))
    def test_record_failure_is_reported_and_retry_succeeds(self):
        self.b.finished=True
        store=self.game.score_store
        with patch.object(store,'connect',side_effect=sqlite3.OperationalError('locked')):
            self.assertFalse(store.record(self.b))
            self.assertTrue(store.error)
        self.assertTrue(store.record(self.b));self.assertEqual(store.error,'')
    def test_corrupt_history_is_preserved(self):
        store=self.game.score_store;store.path.write_bytes(b'corrompido')
        self.assertEqual(store.page(),([],0));self.assertTrue(store.error)
        self.b.finished=True;self.assertFalse(store.record(self.b))
        self.assertEqual(store.path.read_bytes(),b'corrompido')
    def test_checkpoint_saves_finished_score_before_leaving_result(self):
        self.b.score=330;self.b.finished=True
        self.assertTrue(self.game.checkpoint())
        self.assertEqual(self.game.score_store.page()[0][0][6],330)
    def test_finish_keeps_battle_when_score_write_fails(self):
        self.b.finished=True
        with patch.object(self.game.score_store,'record',return_value=False):
            self.game.finish_battle()
        self.assertIs(self.game.battle,self.b)
    def test_pagination_and_menu_navigation(self):
        for i in range(11):
            self.game.enter_selection('city')
            b = self.game.battle
            b.finished = True
            b.score = i * 10
            # Give each result its own player, so the ranking has more than one row.
            self.game.score_store.record(b, player_name=f'Jogador {i:02d}')
        self.game.scene = 'title'
        rect = next(r for label, r in self.game.title_buttons() if label == 'RANKING')
        self.game.handle_click(rect.center)
        self.assertEqual(self.game.scene, 'scores')
        self.assertEqual(self.game.score_view, 'ranking')
        self.assertEqual(len(self.game.score_rows), 10)
        self.game.handle_click((1100, 666))
        self.assertEqual(self.game.score_page, 1)
        self.assertEqual(len(self.game.score_rows), 1)
        # Switch to history and verify the row shape used by the renderer.
        self.game.handle_click((560, 666))
        self.assertEqual(self.game.score_view, 'history')
        self.assertEqual(self.game.score_page, 0)
        self.assertEqual(len(self.game.score_rows), 10)
        self.assertEqual(len(self.game.score_rows[0]), 7)
        self.game.handle_click((1100, 666))
        self.assertEqual(self.game.score_page, 1)
        self.assertEqual(len(self.game.score_rows), 1)
        self.game.handle_click((800, 666))
        self.assertEqual(self.game.score_page, 0)
        self.game.handle_click((100, 666))
        self.assertEqual(self.game.scene, 'title')

    def test_leaderboard_aggregates_points_per_player(self):
        from types import SimpleNamespace
        store = self.game.score_store
        base = dict(finished=True, region='city', difficulty='medium', wave=4, victory=False)
        matches = (
            (SimpleNamespace(**base, match_id='score-ana-1', score=120), 'Ana'),
            (SimpleNamespace(**base, match_id='score-ana-2', score=80), 'Ana'),
            (SimpleNamespace(**base, match_id='score-beto-1', score=150), 'Beto'),
        )
        for match, name in matches:
            self.assertTrue(store.record(match, player_name=name))
        ranking, total = store.leaderboard()
        self.assertEqual(total, 2)
        self.assertEqual(ranking[0][1:4], ('Ana', 200, 2))
        self.assertEqual(ranking[1][1:4], ('Beto', 150, 1))

    def test_ranking_and_history_screens_render_their_own_row_shapes(self):
        self.game.score_store.record(
            type("FinishedMatch", (), {
                "finished": True, "match_id": "ui-score-1", "region": "city",
                "difficulty": "medium", "wave": 4, "victory": True, "score": 240,
            })(),
            player_name="Jogadora UI",
        )
        self.game.score_view = 'ranking'
        self.game.score_page = 0
        self.game.refresh_scores()
        self.assertEqual(len(self.game.score_rows[0]), 6)
        self.game.renderer.draw_scores()

        self.game.score_view = 'history'
        self.game.score_page = 0
        self.game.refresh_scores()
        self.assertEqual(len(self.game.score_rows[0]), 7)
        self.game.renderer.draw_scores()

    def test_profile_and_shop_screen_can_be_drawn_before_first_player_exists(self):
        self.game.player_name = ''
        self.game.profile_name_draft = ''
        self.game.profile_data = {
            "player_name": "", "credits": 0, "medkits": 0, "tactical_ammo": 0,
        }
        self.game.scene = 'profile'
        self.game.renderer.draw_profile()

    def test_shop_card_body_does_not_trigger_purchase(self):
        from unittest.mock import patch
        self.game.player_name = 'Teste da Loja'
        self.game.profile_name_draft = self.game.player_name
        self.game.open_profile('title')
        with patch.object(self.game, 'buy_shop_item', return_value=True) as buy:
            # A área de descrição não deve comprar; só o botão desenhado compra.
            self.game.click_profile((400, 440))
            buy.assert_not_called()
            self.game.click_profile(self.game.profile_medkit_buy_rect().center)
            buy.assert_called_once_with('medkit')

    def test_shop_uses_earned_credits_without_changing_ranking_points(self):
        from types import SimpleNamespace
        store = self.game.score_store
        match = SimpleNamespace(
            finished=True, match_id='shop-match-1', region='city', difficulty='easy',
            wave=12, victory=True, score=1000,
        )
        self.assertTrue(store.record(match, player_name='Loja Tester'))
        self.assertTrue(store.record(match, player_name='Loja Tester'))
        self.assertEqual(store.profile('Loja Tester')['credits'], 100)
        self.assertTrue(store.buy('Loja Tester', 'medkit'))
        self.assertEqual(store.profile('Loja Tester')['medkits'], 1)
        self.assertEqual(store.profile('Loja Tester')['credits'], 40)
        self.assertTrue(store.consume('Loja Tester', 'medkit'))
        self.assertEqual(store.profile('Loja Tester')['medkits'], 0)
        ranking, _ = store.leaderboard()
        row = next(entry for entry in ranking if entry[1] == 'Loja Tester')
        self.assertEqual(row[2], 1000)
    def test_hud_and_both_results_show_points(self):
        self.b.score=1230
        for finished,victory in ((False,False),(True,False),(True,True)):
            self.b.finished=finished;self.b.victory=victory
            with patch.object(self.game.renderer,'draw_text',wraps=self.game.renderer.draw_text) as draw:
                self.game.draw()
            labels=[call.args[0] for call in draw.call_args_list]
            self.assertIn('PONTOS: 1230',labels)
            if finished:self.assertIn('PONTUAÇÃO: 1230',labels)
