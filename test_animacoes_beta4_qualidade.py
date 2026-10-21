"""Regressões visuais para escala, pivô e invasão de célula da Beta 4."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from beta4_production_animations import (
    ACTOR_SHEETS,
    ENEMY_ROSTER_ROWS,
    SOLDIER_TIMING,
    _main_figure,
    build_production_clips,
)
from main import (
    ActorMotion,
    Assets,
    DEFENDER_ACTOR_BY_KEY,
    ENEMY_ACTOR_BY_KEY,
    PRODUCTION_ASSET_DIR,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
    actor_pose,
)


class QualidadeAnimacoesBeta4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.clips = build_production_clips()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_todos_os_atores_tem_caixa_e_pivo_fixos(self) -> None:
        for actor, states in self.clips.items():
            sizes = {frame.get_size() for clip in states.values() for frame in clip.frames}
            self.assertEqual(1, len(sizes), actor)
            for state, clip in states.items():
                feet = {_main_figure(frame).bottom for frame in clip.frames}
                self.assertEqual(1, len(feet), f"{actor}:{state}")

    def test_nenhum_quadro_ativo_invade_a_celula_vizinha(self) -> None:
        for actor, states in self.clips.items():
            for state, clip in states.items():
                for index, frame in enumerate(clip.frames):
                    width, height = frame.get_size()
                    for component in pygame.mask.from_surface(frame, threshold=8).get_bounding_rects():
                        self.assertGreater(component.left, 1, f"{actor}:{state}:{index}")
                        self.assertGreater(component.top, 1, f"{actor}:{state}:{index}")
                        self.assertLess(component.right, width - 1, f"{actor}:{state}:{index}")

    def test_zumbis_base_nao_misturam_duas_silhuetas_no_mesmo_quadro(self) -> None:
        actors = (
            "city_zombie_v2", "city_runner_v2", "city_crawler_v2",
            "desert_zombie_v2", "desert_runner_v2", "desert_crawler_v2",
            "beach_zombie_v2", "beach_runner_v2", "beach_crawler_v2",
        )
        for actor in actors:
            for state in ("move", "bite", "skill"):
                clip = self.clips[actor][state]
                # Oito poses intermediárias evitam o salto de apoio que fazia
                # a caminhada parecer um trote.
                self.assertEqual(8, len(clip.frames), f"{actor}:{state}")
                unique = {pygame.image.tobytes(frame, "RGBA") for frame in clip.frames}
                self.assertGreaterEqual(len(unique), 6, f"{actor}:{state}")
                for index, frame in enumerate(clip.frames):
                    components = pygame.mask.from_surface(frame, threshold=8).connected_components(minimum=16)
                    sizes = sorted((component.count() for component in components), reverse=True)
                    self.assertTrue(sizes, f"{actor}:{state}:{index}")
                    if len(sizes) > 1:
                        self.assertLess(
                            sizes[1],
                            sizes[0] * 0.34,
                            f"possível avanço de frame em {actor}:{state}:{index}",
                        )

    def test_soldados_nunca_deslocam_o_corpo_inteiro_para_cima(self) -> None:
        for state in ("walk", "idle", "attack", "reload", "hit", "support"):
            motion = ActorMotion(state=state, state_elapsed=0.137, event_left=0.2)
            self.assertEqual(
                0.0,
                actor_pose(motion, enemy=False, profile="rifle", progress=0.4)[1],
                state,
            )

    def test_todas_as_folhas_ativas_existem(self) -> None:
        from beta4_production_animations import ASSETS

        missing = [filename for filename, _kind in ACTOR_SHEETS.values() if not (ASSETS / filename).is_file()]
        missing.extend(
            filename
            for filename, _row, _kind in ENEMY_ROSTER_ROWS.values()
            if not (ASSETS / filename).is_file()
        )
        self.assertEqual([], missing)

    def test_elenco_inimigo_novo_tem_todos_os_estados_visiveis(self) -> None:
        for actor in ENEMY_ROSTER_ROWS:
            states = self.clips[actor]
            self.assertEqual({"move", "idle", "bite", "hit", "skill"}, set(states), actor)
            # A base aprovada conserva oito passos intermediários para não
            # transformar caminhada em trote. O restante do elenco mantém no
            # mínimo quatro poses autênticas por ação.
            expected_minimum = 8
            self.assertGreaterEqual(len(states["move"].frames), expected_minimum, actor)
            self.assertGreaterEqual(len(states["bite"].frames), expected_minimum, actor)
            self.assertGreaterEqual(len(states["hit"].frames), expected_minimum, actor)
            self.assertGreaterEqual(len(states["skill"].frames), expected_minimum, actor)
            for state, clip in states.items():
                for index, frame in enumerate(clip.frames):
                    mask = pygame.mask.from_surface(frame, threshold=8)
                    self.assertGreater(mask.count(), 90, f"{actor}:{state}:{index}")
                    bounds = frame.get_bounding_rect(min_alpha=8)
                    self.assertGreater(bounds.width, 8, f"{actor}:{state}:{index}")
                    self.assertGreater(bounds.height, 8, f"{actor}:{state}:{index}")

    def test_folhas_de_producao_cobrem_todo_o_elenco_regional(self) -> None:
        rebuilt = {
            filename
            for filename, _row, _kind in ENEMY_ROSTER_ROWS.values()
        }
        self.assertEqual(
            {
                "city_zombies_hd_16x6_v3.png",
                "city_elites_rebuilt_16x6_v1.png",
                "desert_zombies_hd_16x6_v3.png",
                "desert_elites_rebuilt_16x6_v1.png",
                "beach_zombies_hd_16x6_v3.png",
                "beach_elites_rebuilt_16x6_v1.png",
            },
            rebuilt,
        )

    def test_corredores_mantem_a_mesma_altura_em_toda_a_passada(self) -> None:
        for region in ("city", "desert", "beach"):
            actor = f"{region}_runner_v2"
            heights = [_main_figure(frame).height for frame in self.clips[actor]["move"].frames]
            self.assertEqual(1, len(set(heights)), f"escala pulsando: {actor} {heights}")

    def test_submarino_tem_um_unico_casco_e_um_unico_tubo_de_disparo(self) -> None:
        for state in ("idle", "move", "shoot", "reload"):
            for index, frame in enumerate(self.clips["beach_sub"][state].frames):
                parts = pygame.mask.from_surface(frame, threshold=8).connected_components(minimum=3)
                self.assertEqual(1, len(parts), f"efeito traseiro solto: {state}:{index}")

    def test_habilidade_tem_gesto_proprio_sem_repetir_mordida(self) -> None:
        base_actors = {
            f"{region}_{kind}_v2"
            for region in ("city", "desert", "beach")
            for kind in ("zombie", "runner", "crawler")
        }
        for actor in set(ENEMY_ROSTER_ROWS) - base_actors:
            bite = self.clips[actor]["bite"].frames
            skill = self.clips[actor]["skill"].frames
            self.assertNotEqual(
                [pygame.image.tobytes(frame, "RGBA") for frame in bite],
                [pygame.image.tobytes(frame, "RGBA") for frame in skill],
                actor,
            )

    def test_sacerdote_e_pescador_usam_corpos_inteiros(self) -> None:
        for actor in ("desert_plague_priest", "beach_fisher"):
            for state in ("bite", "hit", "skill"):
                for index, frame in enumerate(self.clips[actor][state].frames):
                    body = _main_figure(frame)
                    self.assertGreater(body.height, 100, f"corpo cortado {actor}:{state}:{index}")

    def test_elenco_regional_tem_intermediarios_em_todas_as_acoes(self) -> None:
        for actor in ENEMY_ROSTER_ROWS:
            for state in ("move", "bite", "hit", "skill"):
                clip = self.clips[actor][state]
                self.assertGreaterEqual(len(clip.frames), 8, f"animação rala {actor}:{state}")
                self.assertGreaterEqual(
                    len({pygame.image.tobytes(frame, "RGBA") for frame in clip.frames}),
                    6,
                    f"quadros repetidos demais {actor}:{state}",
                )

    def test_cada_soldado_tem_ritmo_proprio_de_arma_registrado(self) -> None:
        soldier_actors = {
            actor for actor, (_filename, kind) in ACTOR_SHEETS.items() if kind == "soldier"
        }
        self.assertEqual(soldier_actors, set(SOLDIER_TIMING))
        self.assertLess(
            self.clips["desert_heavy"]["shoot"].duration,
            self.clips["desert_mortar"]["shoot"].duration,
        )

    def test_disparo_nao_carrega_clarao_ou_bala_soltos_na_sprite(self) -> None:
        for actor, (_filename, kind) in ACTOR_SHEETS.items():
            if kind != "soldier":
                continue
            for index, frame in enumerate(self.clips[actor]["shoot"].frames):
                components = pygame.mask.from_surface(
                    frame, threshold=8
                ).connected_components(minimum=2)
                self.assertEqual(
                    1,
                    len(components),
                    f"tiro duplicado ou resíduo em {actor}:{index}",
                )

    def test_bombeiro_nao_embute_espuma_no_corpo(self) -> None:
        """A água deve existir só no sistema de fluxo, nunca na sprite."""
        for index, frame in enumerate(self.clips["beach_waterjet"]["shoot"].frames):
            rgb = pygame.surfarray.array3d(frame)
            alpha = pygame.surfarray.array_alpha(frame)
            start = round(frame.get_width() * 0.65)
            self.assertEqual(
                0,
                int((alpha[start:, :] > 8).sum()),
                f"espuma/clarão ainda preso ao Bombeiro:{index}",
            )

    def test_escudeiro_e_laminas_nao_herdam_o_quadro_vizinho(self) -> None:
        for actor in ("city_shield", "desert_blade"):
            for state, clip in self.clips[actor].items():
                for index, frame in enumerate(clip.frames):
                    components = pygame.mask.from_surface(
                        frame, threshold=8
                    ).connected_components(minimum=2)
                    self.assertEqual(1, len(components), f"{actor}:{state}:{index}")

    def test_zumbis_tem_leitura_lenta_e_previsivel(self) -> None:
        for actor in ENEMY_ROSTER_ROWS:
            clips = self.clips[actor]
            self.assertGreaterEqual(min(clips["move"].frame_durations), 0.10, actor)
            self.assertGreaterEqual(min(clips["bite"].frame_durations), 0.10, actor)
            self.assertGreaterEqual(min(clips["hit"].frame_durations), 0.10, actor)

    def test_boss_e_maior_sem_ficar_desproporcional(self) -> None:
        samples = {
            actor: sum(_main_figure(frame).height for frame in states["move"].frames)
            / len(states["move"].frames)
            for actor, states in self.clips.items()
            if actor in ENEMY_ROSTER_ROWS
        }
        for region in ("city", "desert", "beach"):
            common = samples[f"{region}_technician" if region == "city" else (f"{region}_looter" if region == "desert" else f"{region}_fisher")]
            boss = samples[f"{region}_boss_alpha" if region == "city" else (f"{region}_boss_colossus" if region == "desert" else f"{region}_boss_colossus")]
            self.assertGreater(boss, common * 1.04, region)
            self.assertLess(boss, common * 1.24, region)

    def test_vfx_simples_tem_alfa_real_e_grade_regular(self) -> None:
        from main import ASSET_DIR

        for filename in (
            "projectile_sprites_sheet_beta4_clean.png",
            "combat_effects_sheet_beta4_clean.png",
            "elemental_effects_sheet_beta4_clean.png",
            "ability_effects_sheet_beta4_clean.png",
        ):
            surface = pygame.image.load(str(ASSET_DIR / filename))
            self.assertEqual((1024, 768), surface.get_size(), filename)
            alpha = pygame.surfarray.array_alpha(surface)
            self.assertEqual(0, int(alpha.min()), filename)
            self.assertEqual(255, int(alpha.max()), filename)

    def test_todo_o_elenco_jogavel_usa_as_folhas_de_producao(self) -> None:
        for region, roster in REGION_ROSTERS.items():
            for key, _display in roster:
                actor = DEFENDER_ACTOR_BY_KEY.get(key)
                self.assertIsNotNone(actor, f"soldado sem ator: {region}:{key}")
                self.assertIn(actor, self.clips, f"soldado sem folha: {region}:{key}")
                states = set(self.clips[actor])
                self.assertIn("move", states, key)
                self.assertIn("hit", states, key)
                self.assertTrue(
                    {"shoot", "reload"}.issubset(states) or "support" in states,
                    f"soldado sem ação própria: {region}:{key}",
                )

        for region in REGION_ENEMIES:
            keys = (
                tuple(REGION_ENEMIES[region])
                + tuple(REGION_SUBBOSSES[region])
                + tuple(REGION_BOSSES[region])
            )
            self.assertEqual(12, len(keys), region)
            for key in keys:
                actor = ENEMY_ACTOR_BY_KEY.get(key)
                self.assertIsNotNone(actor, f"zumbi sem ator: {region}:{key}")
                self.assertIn(actor, self.clips, f"zumbi sem folha: {region}:{key}")
                self.assertTrue(
                    {"move", "bite", "hit", "skill"}.issubset(self.clips[actor]),
                    f"zumbi sem ação completa: {region}:{key}",
                )

    def test_retratos_dos_nove_chefes_sao_inteiros_e_sem_fragmentos(self) -> None:
        for region in ("city", "desert", "beach"):
            sheet = pygame.image.load(
                str(PRODUCTION_ASSET_DIR / f"{region}_boss_portraits_3x1_v1.png")
            ).convert_alpha()
            portraits = [
                Assets.portrait_actor(frame)
                for frame in Assets.slice_grid(sheet, 3, 1)
            ]
            self.assertEqual(3, len(portraits))
            for index, portrait in enumerate(portraits):
                bounds = portrait.get_bounding_rect(min_alpha=8)
                self.assertGreater(bounds.width, 120, f"{region}:{index}")
                self.assertGreater(bounds.height, 170, f"{region}:{index}")
                self.assertLess(bounds.width / bounds.height, 1.45, f"{region}:{index}")

    def test_ciclo_de_disparo_tem_oito_momentos_sem_fundo_opaco(self) -> None:
        sheet = pygame.image.load(
            str(PRODUCTION_ASSET_DIR / "muzzle_cycle_source_v1.png")
        ).convert_alpha()
        frames = Assets.slice_grid(sheet, 8, 1)
        self.assertEqual(8, len(frames))
        self.assertLess(pygame.mask.from_surface(frames[0], threshold=8).count(), 20)
        for index in range(1, 7):
            self.assertGreater(
                pygame.mask.from_surface(frames[index], threshold=8).count(),
                120,
                index,
            )


if __name__ == "__main__":
    unittest.main()
