"""Aceite da revisão geral: entradas, estados, progresso e recuperação."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from svz.app import Game
from svz.assets import FontBook
from svz.content import REGIONS, DEFENSES, DIFFICULTIES
from svz.persistence import load_save, make_save, MAX_CAMPAIGN_BYTES
from svz.session_store import SessionStore
from svz.settings import Settings, DEFAULT_BINDINGS
from svz.snapshot import capture
from svz.timing import FixedStepper

class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage=tempfile.TemporaryDirectory()
        cls.game=Game(save_path=Path(cls.storage.name)/"boot.json")
        while cls.game.scene=="loading":cls.game.update(1/60)
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.storage.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        g=self.game
        self.path=Path(self.temp.name)/"campaign.json"
        g.save_path=self.path
        g.session_store=SessionStore(self.path)
        g.settings=Settings(self.path)
        g.navigation.scene=None
        g.navigation.visible=False
        g.binding_action=None
        g.save=make_save()
        g.save_error=False
        g.scene="title"
        g.battle=None
        g.pending_snapshot=None
        g.video_notice=""
        g.session_notice=""
        g.running=True
        g.show_card_info=False
        g.control_mode="mouse"
        g.fonts=FontBook()
        pygame.event.clear()

    def battle(self,region="city",difficulty="medium",mode="mouse"):
        g=self.game
        g.control_mode=mode
        g.difficulty=difficulty
        g.enter_selection(region)
        g.battle.supplies=999
        return g.battle

    def key(self,key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key,mod=0))
        self.game.handle_events()

    def test_mouse_and_keyboard_enforce_cooldown_all_nine(self):
        for region in REGIONS:
            for difficulty in DIFFICULTIES:
                for mode in ("mouse","keyboard"):
                    with self.subTest(region=region,difficulty=difficulty,mode=mode):
                        b=self.battle(region,difficulty,mode)
                        def place(col):
                            if mode=="mouse":self.game.handle_click(b.ground_cell_rect(0,col).center)
                            else:
                                b.keyboard_row,b.keyboard_col=0,col
                                self.key(pygame.K_RETURN)
                        place(2); before=b.supplies
                        place(4)
                        self.assertEqual(1,len(b.defenders))
                        self.assertEqual(before,b.supplies)
                        b.intermission=999
                        b.update(10)
                        place(4)
                        self.assertEqual(2,len(b.defenders))

    def test_paused_commands_have_no_gameplay_effect_all_nine(self):
        for region in REGIONS:
            for difficulty in DIFFICULTIES:
                b=self.battle(region,difficulty,"keyboard")
                b.place(0,2)
                b.keyboard_row,b.keyboard_col=0,2
                self.key(pygame.K_p)
                before=capture(b)["battle"]
                for key in (pygame.K_r,pygame.K_RETURN,pygame.K_n,pygame.K_TAB,pygame.K_f,pygame.K_SPACE,pygame.K_2):
                    self.key(key)
                self.assertFalse(b.place(0,4))
                b.remove_defender(0,2)
                self.assertFalse(b.start_next_wave())
                self.game.control_mode="mouse";self.key(pygame.K_SPACE)
                self.assertEqual(before,capture(b)["battle"])
                self.key(pygame.K_p);self.assertFalse(b.paused)

    def test_enter_finishes_win_and_loss_all_nine(self):
        for region in REGIONS:
            for difficulty in DIFFICULTIES:
                for victory in (True,False):
                    b=self.battle(region,difficulty,"keyboard")
                    b.finished=True;b.victory=victory;b.lost=not victory;b.wave=7 if not victory else 12
                    self.key(pygame.K_r)
                    self.assertFalse(b.remove_mode)
                    self.key(pygame.K_RETURN)
                    self.assertEqual("campaign",self.game.scene)
                    self.assertIsNone(self.game.battle)

    def test_defeat_records_reached_wave_and_preserves_higher_record(self):
        b=self.battle();b.finished=b.lost=True;b.wave=7
        self.game.finish_battle()
        self.assertEqual(7,load_save(self.path)["best_wave"]["city"])
        self.assertEqual(7,load_save(self.path)["by_difficulty"]["medium"]["city"]["best_wave"])
        b=self.battle();b.finished=b.lost=True;b.wave=3
        self.game.finish_battle()
        self.assertEqual(7,load_save(self.path)["best_wave"]["city"])
        self.assertFalse(load_save(self.path)["completed"])

    def test_failed_result_save_keeps_finished_battle(self):
        b=self.battle();b.finished=b.lost=True;b.wave=4
        with patch("svz.app.save_campaign",return_value=False):
            self.game.finish_battle()
        self.assertIs(b,self.game.battle)
        self.assertEqual("battle",self.game.scene)

    def test_new_game_confirmation_defaults_cancel_and_allows_deliberate_keyboard_accept(self):
        self.battle()
        self.game.leave_battle_to_title()
        self.game.request_new_game()
        self.key(pygame.K_RETURN)
        self.assertEqual("title",self.game.scene)
        self.assertTrue(self.game.can_continue())
        self.game.request_new_game()
        self.key(pygame.K_TAB);self.key(pygame.K_RETURN)
        self.assertEqual("difficulty",self.game.scene)
        self.assertFalse(self.game.can_continue())

    def test_title_settings_and_story_are_keyboard_accessible(self):
        # INICIAR, PERSONAGENS, HISTÓRIA, CONFIGURAÇÕES.
        for _ in range(3):self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual("settings",self.game.scene)
        self.key(pygame.K_RETURN)
        self.assertEqual("keyboard",self.game.control_mode)
        self.key(pygame.K_ESCAPE)
        self.assertEqual("title",self.game.scene)
        self.game.scene="story";self.game.story_page=0
        self.key(pygame.K_TAB);self.key(pygame.K_RETURN)
        self.assertEqual(1,self.game.story_page)

    def test_binding_changed_key_works_and_reserved_duplicate_keys_are_rejected(self):
        b=self.battle(mode="keyboard")
        self.assertTrue(self.game.settings.assign("pause",pygame.K_z))
        self.key(pygame.K_p);self.assertFalse(b.paused)
        self.key(pygame.K_z);self.assertTrue(b.paused)
        self.assertFalse(self.game.settings.assign("place",pygame.K_z))
        self.assertFalse(self.game.settings.assign("place",pygame.K_F5))
        self.assertFalse(self.game.settings.assign("place",pygame.K_ESCAPE))

    def test_focus_loss_pauses_and_regaining_focus_does_not_resume(self):
        b=self.battle()
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.game.handle_events()
        self.assertTrue(b.paused)
        before=capture(b)
        self.game.update(2)
        self.assertEqual(before,capture(b))
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.game.handle_events()
        self.assertTrue(b.paused)

    def test_auto_pause_can_be_disabled(self):
        b=self.battle()
        self.game.settings.auto_pause=False
        pygame.event.post(pygame.event.Event(pygame.WINDOWMINIMIZED))
        self.game.handle_events()
        self.assertFalse(b.paused)

    def test_preferences_persist_with_audio_levels_and_bindings(self):
        g=self.game
        g.control_mode="keyboard";g.audio.set_enabled(False);g.audio.set_volume(.2)
        g.settings.music=.4;g.settings.auto_pause=False;g.settings.large_text=True
        g.settings.assign("pause",pygame.K_z)
        g.save_settings()
        settings=Settings(self.path)
        self.assertEqual(("keyboard",False,.2,.4,False,True,pygame.K_z),
                         (settings.control_mode,settings.sound,settings.volume,settings.music,settings.auto_pause,settings.large_text,settings.bindings["pause"]))

    def test_preferences_ignore_corrupt_and_invalid_data(self):
        p=self.game.settings.path
        for data in ('['*6000, '{"version": 1, "volume": "bad", "bindings": {"a": []}}'):
            p.write_text(data,encoding="utf-8")
            s=Settings(self.path)
            self.assertEqual(.65,s.volume)
            self.assertEqual(DEFAULT_BINDINGS,s.bindings)

    def test_campaign_deep_and_oversized_files_are_preserved(self):
        for raw in ("["*5000+"0"+"]"*5000,"x"*(MAX_CAMPAIGN_BYTES+1),"{"):
            self.path.write_text(raw,encoding="utf-8")
            notes=[]
            with self.assertLogs("svz.persistence",level="WARNING"):
                result=load_save(self.path,notes)
            self.assertEqual(make_save(),result)
            self.assertEqual(raw,self.path.read_text(encoding="utf-8"))
            self.assertTrue(notes)

    def test_manual_save_and_continue_metadata(self):
        b=self.battle("desert","hard")
        b.supplies=73
        self.key(pygame.K_F5)
        self.assertEqual(73,self.game.session_store.load()["battle"]["supplies"])
        info=self.game.continue_info()
        self.assertIn("EGITO",info)
        self.assertIn("Difícil",info)
        self.assertIn("onda 0/12",info)

    def test_previous_save_is_recovered_and_clear_cannot_resurrect_it(self):
        b=self.battle()
        b.supplies=53;self.game.checkpoint()
        expected=capture(b)
        b.supplies=29;self.game.checkpoint()
        store=self.game.session_store
        store.path.write_text("{broken",encoding="utf-8")
        with self.assertLogs("svz.session_store",level="ERROR"):
            self.assertEqual(expected,store.load())
        self.assertEqual("{broken",store.path.read_text(encoding="utf-8"))
        self.assertTrue(store.clear())
        store.path.unlink()
        self.assertIsNone(SessionStore(self.path).load())

    def test_invalid_graph_recovers_previous_snapshot(self):
        b=self.battle()
        b.place(0,2)
        b.supplies=53;self.game.checkpoint()
        b.supplies=29;self.game.checkpoint()
        raw=self.game.session_store.path.read_bytes()
        self.game.pending_snapshot["objects"][0]["fields"]["row"]=300
        self.game.battle=None
        with self.assertLogs("svz.app",level="ERROR"):
            self.assertTrue(self.game.resume_battle())
        self.assertEqual(53,self.game.battle.supplies)
        self.assertTrue(self.game.battle.paused)
        self.assertEqual(raw,self.game.session_store.path.read_bytes())

    def test_difficulty_descriptions_use_current_values(self):
        self.game.scene="difficulty"
        with patch.object(self.game.renderer,"draw_wrapped",wraps=self.game.renderer.draw_wrapped) as draw:
            self.game.draw()
        labels=[call.args[0] for call in draw.call_args_list]
        for data in DIFFICULTIES.values():
            self.assertIn(f"{data['initial_supplies']} suprimentos iniciais",labels)
            self.assertIn(f"Limite de reserva: {data['supply_cap']}",labels)

    def test_first_save_after_recovery_keeps_valid_backup(self):
        b=self.battle();b.place(0,2)
        b.supplies=53;self.game.checkpoint()
        b.supplies=29;self.game.checkpoint()
        store=self.game.session_store
        corrupt=store.read_document(store.path)
        corrupt["snapshot"]["objects"][0]["fields"]["row"]=300
        store.path.write_text(json.dumps(corrupt),encoding="utf-8")
        self.game.pending_snapshot=store.load()
        self.game.battle=None
        with self.assertLogs("svz.app",level="ERROR"):
            self.assertTrue(self.game.resume_battle())
        self.game.battle.supplies=31
        self.assertTrue(self.game.checkpoint())
        previous=store.read_document(store.backup_path)["snapshot"]
        self.assertEqual(53,previous["battle"]["supplies"])
        self.assertEqual(0,previous["objects"][0]["fields"]["row"])
        self.game.battle.supplies=32
        self.assertTrue(self.game.checkpoint())
        self.assertEqual(31,store.read_document(store.backup_path)["snapshot"]["battle"]["supplies"])

    def test_compact_hud_cost_and_tooltip_fit_both_text_sizes(self):
        for large in (False,True):
            self.game.fonts=FontBook(large)
            for region in REGIONS:
                b=self.battle(region)
                font=self.game.fonts.tiny
                for (key,_),rect in zip(b.selected,b.card_rects()):
                    # O HUD compacto mostra retrato/custo; métricas ficam na ficha.
                    self.assertLessEqual(font.size(f"{DEFENSES[key]['cost']} SUP")[0],rect.width-8)
                    a,text=self.game.renderer.card_metrics(DEFENSES[key])
                    self.assertLessEqual(font.size(f"{a} • {text}")[0],454)
                self.game.draw()

    def test_help_matches_eight_cards_and_resume_flow(self):
        self.game.scene="howto"
        with patch.object(self.game.renderer,"draw_wrapped",wraps=self.game.renderer.draw_wrapped) as draw:self.game.draw()
        text=" ".join(call.args[0] for call in draw.call_args_list)
        self.assertIn("oito cartas",text)
        self.assertIn("CONTINUAR",text)
        self.assertNotIn("três tropas",text)

    def test_all_menu_focus_rectangles_remain_inside_screen(self):
        for scene in ("title","confirm_new","confirm_exit","difficulty","campaign","characters","settings","bindings","story","howto"):
            self.game.scene=scene
            items=self.game.navigation.items()
            self.assertTrue(items,scene)
            for _,rect in items:self.assertTrue(pygame.Rect(0,0,1280,720).contains(rect),scene)

class TimingTests(unittest.TestCase):
    def test_equal_simulation_for_10_30_and_60_fps(self):
        results=[]
        for fps in (10,30,60):
            steps=[]
            timer=FixedStepper()
            for _ in range(fps*10):timer.advance(1/fps,steps.append)
            self.assertEqual(600,len(steps))
            results.append(sum(steps))
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[1],results[2])

    def test_long_stall_has_bounded_work(self):
        timer=FixedStepper()
        steps=[]
        self.assertEqual(15,timer.advance(120,steps.append))
        self.assertLess(timer.remainder,timer.step)
        self.assertGreater(timer.dropped_seconds,119)

