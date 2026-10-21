from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

from main import (
    AUDIO_DIR,
    Battle,
    DIFFICULTIES,
    Game,
    REGION_ROSTERS,
    boss_wave_scale,
    enemy_damage_scale,
    enemy_wave_scale,
)


class ControlesAudioDificuldadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = Game(integration_preview=True)
        while not cls.app.assets.complete:
            cls.app.assets.load_next()
        cls.app.assets.prepare_production_animations()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_mouse_e_o_controle_padrao(self) -> None:
        self.assertEqual("mouse", self.app.control_mode)

    def test_configuracoes_alternam_mouse_e_teclado(self) -> None:
        self.app.scene = "settings"
        self.app.control_mode = "mouse"
        self.app.handle_click(self.app.settings_control_rect().center)
        self.assertEqual("keyboard", self.app.control_mode)
        self.app.handle_click(self.app.settings_control_rect().center)
        self.assertEqual("mouse", self.app.control_mode)

    def test_teclado_move_cursor_escolhe_carta_e_posiciona(self) -> None:
        self.app.control_mode = "keyboard"
        self.app.scene = "battle"
        battle = Battle(self.app, "city", list(REGION_ROSTERS["city"]))
        battle.supplies = 999
        battle.intermission = 999
        self.app.battle = battle
        self.app.handle_key(pygame.K_2)
        self.assertEqual(1, battle.selected_card)
        self.app.handle_key(pygame.K_d)
        self.app.handle_key(pygame.K_s)
        self.assertEqual((1, 2), (battle.keyboard_row, battle.keyboard_col))
        self.app.handle_key(pygame.K_RETURN)
        self.assertEqual(1, len(battle.defenders))
        self.assertEqual((1, 2), (battle.defenders[0].row, battle.defenders[0].col))

    def test_medio_e_base_real_e_dificil_supera_vinte_por_cento(self) -> None:
        medium = DIFFICULTIES["medium"]
        hard = DIFFICULTIES["hard"]
        self.assertEqual(1.0, medium["enemy_hp"])
        self.assertEqual(1.0, medium["enemy_damage"])
        self.assertGreaterEqual(hard["enemy_hp"], 1.20)
        self.assertGreaterEqual(hard["enemy_damage"], 1.20)
        self.assertLess(hard["defender_damage"], medium["defender_damage"])
        self.assertLess(hard["spawn_wait"], medium["spawn_wait"])

    def test_biblioteca_de_audio_tem_todos_os_eventos(self) -> None:
        if not self.app.audio.ready:
            self.skipTest(self.app.audio.error or "mixer indisponível")
        expected = {
            "ambience", "ui", "place", "shot", "heavy_shot", "explosion",
            "zombie_hit", "soldier_hit", "bite", "supply", "wave", "boss",
            "ability",
        }
        self.assertTrue(expected.issubset(self.app.audio.sounds))
        self.app.audio.set_volume(2.0)
        self.assertEqual(1.0, self.app.audio.volume)
        self.app.audio.set_volume(-1.0)
        self.assertEqual(0.0, self.app.audio.volume)
        self.app.audio.set_volume(0.65)

    def test_audio_fisico_cobre_recarga_criaturas_cenarios_e_musica(self) -> None:
        required = {
            "music_menu", "ambience_city", "ambience_desert", "ambience_beach",
            "shot_pistol", "shot_rifle", "shot_heavy", "reload",
            "zombie_groan", "zombie_hit", "bite", "zombie_skill",
            "whistle", "alarm_scream", "thunder",
        }
        self.assertTrue(required.issubset(self.app.audio.FILES))
        for name in required:
            filename = self.app.audio.FILES[name][0]
            path = Path(AUDIO_DIR) / filename
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 8_000, path)

    def test_curva_comeca_mais_leve_e_termina_muito_mais_forte(self) -> None:
        self.assertLess(enemy_wave_scale(1), 0.70)
        self.assertLess(enemy_damage_scale(1), 0.70)
        self.assertGreater(enemy_wave_scale(12), enemy_wave_scale(1) * 3.0)
        self.assertGreater(enemy_damage_scale(12), enemy_damage_scale(1) * 2.6)
        self.assertGreater(boss_wave_scale(12), boss_wave_scale(4) * 1.9)


if __name__ == "__main__":
    unittest.main()
