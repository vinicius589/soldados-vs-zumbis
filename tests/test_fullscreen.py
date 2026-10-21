"""Exibição real com SDL dummy, cliques transformados e persistência isolada."""
import json
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
from svz.config import WIDTH, HEIGHT
from svz.content import REGIONS
from svz.snapshot import capture
from svz.video import VideoDisplay, fit_viewport, logical_position


class GeometryTests(unittest.TestCase):
    def test_aspect_ratio_and_center_at_common_resolutions(self):
        cases = {(1920,1080):(0,0,1920,1080), (1024,768):(0,96,1024,576),
                 (2560,1080):(320,0,1920,1080), (3840,2160):(0,0,3840,2160),
                 (800,600):(0,75,800,450), (1280,1024):(0,152,1280,720)}
        for size, rect in cases.items():
            with self.subTest(size=size):
                self.assertEqual(tuple(fit_viewport(size)), rect)
                self.assertEqual(logical_position(fit_viewport(size).center, size), (640,360))

    def test_black_bars_and_right_bottom_edges_are_not_clickable(self):
        for size in ((1024,768), (2560,1080)):
            r = fit_viewport(size)
            for point in ((-1,0), (0,-1), (r.right,r.centery), (r.centerx,r.bottom)):
                self.assertEqual(logical_position(point,size), (-1,-1))
            self.assertEqual(logical_position(r.topleft,size), (0,0))
        self.assertEqual(logical_position((10,10),(1024,768)), (-1,-1))
        self.assertEqual(logical_position((10,500),(2560,1080)), (-1,-1))


class FullscreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name) / "campaign.json"
        cls.game = Game(save_path=cls.path)
        while not cls.game.assets.complete:
            cls.game.assets.load_next()
        cls.game.assets.prepare_production_animations()
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.directory.cleanup()

    def setUp(self):
        g = self.game
        if g.video.fullscreen:
            g.toggle_fullscreen()
        g.video_notice = ""
        g.scene = "title"
        g.running = True
        pygame.event.clear()

    def click_physical(self, point):
        r = fit_viewport(pygame.display.get_window_size())
        physical = (r.x + round(point[0]*r.width/WIDTH),
                    r.y + round(point[1]*r.height/HEIGHT))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=physical))
        self.game.handle_events()

    def test_f11_settings_button_and_alt_enter(self):
        g = self.game
        g.scene = "settings"
        self.click_physical(g.settings_video_rect().center)
        self.assertTrue(g.video.fullscreen)
        self.assertTrue(pygame.display.is_fullscreen())
        g.handle_key(pygame.K_F11)
        self.assertFalse(g.video.fullscreen)
        g.handle_key(pygame.K_RETURN, pygame.KMOD_ALT)
        self.assertTrue(g.video.fullscreen)
        self.assertEqual(g.scene, "settings")

    def test_toggling_preserves_entire_battle_in_all_nine_combinations(self):
        g = self.game
        for region in REGIONS:
            for difficulty in ("easy","medium","hard"):
                with self.subTest(region=region, difficulty=difficulty):
                    g.difficulty = difficulty
                    g.enter_selection(region)
                    b = g.battle
                    b.supplies = 500
                    b.place(0,2)
                    b.start_next_wave()
                    b.update(.25)
                    b.remove_mode = True
                    before = capture(b)
                    for _ in range(2):
                        g.handle_key(pygame.K_F11)
                        self.assertIs(g.battle,b)
                        self.assertEqual(capture(b),before)
                        self.assertEqual(g.world_surface.get_size(), (WIDTH,HEIGHT))
                        g.draw()
                        g.present_frame()

    def test_clicks_place_remove_pause_and_return_to_menu_in_fullscreen(self):
        g = self.game
        for region in REGIONS:
            with self.subTest(region=region):
                g.enter_selection(region)
                if not g.video.fullscreen:
                    g.toggle_fullscreen()
                b = g.battle
                self.click_physical(b.ground_cell_rect(0,2).center)
                self.assertEqual(len(b.defenders),1)
                self.click_physical(b.remove_rect().center)
                self.assertTrue(b.remove_mode)
                self.click_physical(b.ground_cell_rect(0,2).center)
                self.assertEqual(b.defenders,[])
                self.click_physical(b.pause_rect().center)
                self.assertTrue(b.paused)
                self.click_physical(b.menu_rect().center)
                self.assertEqual(g.scene,"title")
                self.assertTrue(g.resume_battle())
                self.assertTrue(g.battle.paused)

    def test_hover_and_click_use_the_same_coordinate_mapping(self):
        g = self.game
        with patch("pygame.display.get_window_size",return_value=(2560,1080)), patch("pygame.mouse.get_pos",return_value=(1280,540)):
            self.assertEqual(g.video.mouse_position(), (640,360))
            self.assertEqual(g.video.mouse_position((1280,540)), (640,360))
        with patch("pygame.display.get_window_size",return_value=(1024,768)), patch.object(g,"handle_click") as click:
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(1,1)))
            g.handle_events()
            click.assert_not_called()

    def test_preference_roundtrip_and_malformed_files(self):
        g = self.game
        g.toggle_fullscreen()
        self.assertTrue(VideoDisplay(self.path).fullscreen)
        g.toggle_fullscreen()
        self.assertFalse(VideoDisplay(self.path).fullscreen)
        for raw in ('{"fullscreen":"false"}','[]','null','{bad','x'*5000):
            g.video.path.write_text(raw,encoding="utf-8")
            self.assertFalse(VideoDisplay(self.path).fullscreen)

    def test_mode_failure_restores_window_and_does_not_change_preference(self):
        g = self.game
        original = g.video.create_mode
        def unavailable(flags=0):
            if g.video.fullscreen:
                raise pygame.error("Simulação: modo indisponível")
            return original(flags)
        before = g.video.path.read_bytes() if g.video.path.exists() else None
        with patch.object(g.video,"create_mode",side_effect=unavailable), self.assertLogs("svz.app",level="ERROR"):
            self.assertFalse(g.toggle_fullscreen())
        self.assertFalse(g.video.fullscreen)
        self.assertIn("Não foi possível",g.video_notice)
        self.assertEqual(g.video.path.read_bytes() if g.video.path.exists() else None,before)
        g.draw()
        g.present_frame()

    def test_preference_write_failure_does_not_crash_or_cancel_mode(self):
        g = self.game
        with patch("svz.video.write_json",return_value=False):
            self.assertTrue(g.toggle_fullscreen())
        self.assertTrue(g.video.fullscreen)
        self.assertIn("guardar a preferência",g.video_notice)

    def test_held_f11_does_not_toggle_repeatedly(self):
        g = self.game
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F11,repeat=True))
        g.handle_events()
        self.assertFalse(g.video.fullscreen)

    def test_software_scales_without_cropping_and_reuses_buffer(self):
        g = self.game
        pygame.display.set_mode((800,600))
        g.world_surface.fill((20,80,160))
        g.video.present(g.world_surface)
        screen = pygame.display.get_surface()
        self.assertEqual(screen.get_at((0,0))[:3], (0,0,0))
        for point in ((0,75), (799,524)):
            for actual, expected in zip(screen.get_at(point)[:3], (20,80,160)):
                self.assertLessEqual(abs(actual-expected), 2)  # Arredondamento SIMD do SDL.
        buffer = g.video.scaled_surface
        g.video.present(g.world_surface)
        self.assertIs(g.video.scaled_surface,buffer)
        g.world_surface = g._create_display()
        g.screen = g.world_surface


class StartupVideoTests(unittest.TestCase):
    def test_monitor_query_initializes_video_even_after_partial_pygame_init(self):
        pygame.display.quit()
        with tempfile.TemporaryDirectory() as directory:
            try:
                video = VideoDisplay(Path(directory)/"campaign.json")
                self.assertTrue(pygame.display.get_init())
                self.assertGreater(video.desktop_size[0],0)
            finally:
                pygame.quit()

    def test_saved_fullscreen_is_applied_on_next_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"campaign.json"
            path.with_name("campaign.video.json").write_text('{"fullscreen":true}',encoding="utf-8")
            try:
                game = Game(save_path=path)
                self.assertTrue(game.video.fullscreen)
                self.assertTrue(pygame.display.is_fullscreen())
                self.assertEqual(game.world_surface.get_size(),(1280,720))
            finally:
                pygame.quit()

    def test_unavailable_saved_mode_falls_back_to_window(self):
        original = VideoDisplay.create_mode
        def unavailable(video, flags=0):
            if video.fullscreen:
                raise pygame.error("Simulação de modo indisponível ao iniciar")
            return original(video,flags)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"campaign.json"
            path.with_name("campaign.video.json").write_text('{"fullscreen":true}',encoding="utf-8")
            try:
                with patch.object(VideoDisplay,"create_mode",new=unavailable), self.assertLogs("svz.app",level="ERROR"):
                    game = Game(save_path=path)
                self.assertFalse(game.video.fullscreen)
                self.assertFalse(pygame.display.is_fullscreen())
                self.assertIn("iniciou em janela",game.video_notice)
            finally:
                pygame.quit()


if __name__ == "__main__":
    unittest.main()

