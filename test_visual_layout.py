import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import main
from visual_layout import (
    DEFENDER_INTERACTIONS,
    DEFENDER_LAYOUTS,
    DEFENDER_WEAPON_PROFILES,
    ENEMY_ACTIVE_INTERACTIONS,
    ENEMY_PASSIVE_TRAITS,
    PROJECTILE_LAUNCH_GAPS,
    PROJECTILE_LAYOUTS,
)


class VisualLayoutTests(unittest.TestCase):
    def test_todo_ator_jogavel_tem_tamanho_explicito(self) -> None:
        self.assertTrue(
            set(main.DEFENDER_ACTOR_BY_KEY.values()).issubset(DEFENDER_LAYOUTS),
            "há ator jogável sem tamanho e âncora registrados",
        )

    def test_arma_de_tiro_tem_origem_fisica(self) -> None:
        ignored = {"radio", "promoter", "barrier", "mine", "suicide_bomber", "sonar"}
        for key, actor in main.DEFENDER_ACTOR_BY_KEY.items():
            if main.DEFENSES[key]["role"] in ignored:
                continue
            layout = DEFENDER_LAYOUTS[actor]
            self.assertGreater(layout.muzzle_forward, 0, key)
            self.assertGreater(layout.muzzle_height, 0, key)
            self.assertLess(layout.muzzle_height, layout.body_height, key)

    def test_projeteis_cabem_na_propria_celula(self) -> None:
        for kind, (_row, _column, width, height) in PROJECTILE_LAYOUTS.items():
            self.assertGreater(width, 0, kind)
            self.assertGreater(height, 0, kind)
            self.assertLessEqual(width, 64, kind)
            self.assertLessEqual(height, 32, kind)

    def test_municao_balistica_e_pequena_e_comeca_depois_do_cano(self) -> None:
        ballistic = (
            "rifle", "tracer", "shotgun", "sniper", "fuzileiro", "boat",
            "turret", "enemy_bullet", "pistol_9mm", "pistol_50ae",
            "revolver_357", "smg_9mm", "rifle_556_scar", "rifle_556_m16",
            "mg_762", "sniper_awm", "sniper_762", "sniper_338",
            "buckshot_12g", "naval_round",
        )
        for kind in ballistic:
            _row, _column, width, height = PROJECTILE_LAYOUTS[kind]
            self.assertLessEqual(width, 17, kind)
            self.assertLessEqual(height, 5, kind)
            self.assertGreater(PROJECTILE_LAUNCH_GAPS[kind], 0, kind)
        self.assertNotIn("waterjet", PROJECTILE_LAUNCH_GAPS)
        self.assertNotIn("flame", PROJECTILE_LAUNCH_GAPS)
        self.assertNotIn("poison", PROJECTILE_LAUNCH_GAPS)

        defender = main.Defender(
            "agente_swat", "SWAT", 1, 2, main.DEFENSES["agente_swat"], 0, region="city"
        )
        clips = main.build_production_clips()
        defender.visual_animation = main.new_production_animation(clips, "city_auto")
        defender.visual_animation.play("shoot", restart=True)
        muzzle_x, muzzle_y = main.defender_weapon_origin(defender)
        projectile = main.Projectile(
            muzzle_x, muzzle_y, None, muzzle_x + 100, muzzle_y, 1,
            DEFENDER_WEAPON_PROFILES["agente_swat"].projectile_kind,
            defender,
        )
        self.assertGreater(projectile.x, muzzle_x)
        self.assertLess(projectile.x - muzzle_x, 10)

    def test_cada_arma_do_elenco_final_tem_perfil_proprio(self) -> None:
        armed_roles = {
            "rifle", "heavy", "shotgun", "sniper", "grenade",
            "gas_grenade", "mortar", "rocket", "flame", "waterjet",
            "boat", "sub",
        }
        armed_keys = {
            key
            for roster in main.REGION_ROSTERS.values()
            for key, _display in roster
            if str(main.DEFENSES[key]["role"]) in armed_roles
        }
        self.assertEqual(armed_keys, set(DEFENDER_WEAPON_PROFILES))
        valid_kinds = set(PROJECTILE_LAYOUTS) | {"flame", "waterjet"}
        for key, profile in DEFENDER_WEAPON_PROFILES.items():
            self.assertIn(profile.projectile_kind, valid_kinds, key)

    def test_calibres_nao_reutilizam_tamanho_unico_da_swat(self) -> None:
        widths = {
            kind: PROJECTILE_LAYOUTS[kind][2]
            for kind in (
                "pistol_9mm", "pistol_50ae", "smg_9mm",
                "rifle_556_m16", "mg_762", "sniper_338",
            )
        }
        self.assertLess(widths["pistol_9mm"], widths["pistol_50ae"])
        self.assertLess(widths["smg_9mm"], widths["rifle_556_m16"])
        self.assertLess(widths["rifle_556_m16"], widths["mg_762"])
        self.assertLess(widths["mg_762"], widths["sniper_338"])

    def test_recuo_e_recarga_sao_especificos_da_arma(self) -> None:
        swat = DEFENDER_WEAPON_PROFILES["agente_swat"]
        shotgun = DEFENDER_WEAPON_PROFILES["agente_entrada"]
        sniper = DEFENDER_WEAPON_PROFILES["atirador_precisao_marinha"]
        revolver = DEFENDER_WEAPON_PROFILES["pistoleiro_deserto"]

        self.assertEqual(swat.projectile_kind, "smg_9mm")
        self.assertEqual(shotgun.projectile_kind, "buckshot_12g")
        self.assertNotEqual(shotgun.flash_size, swat.flash_size)
        self.assertGreater(shotgun.recoil, swat.recoil)
        self.assertEqual(shotgun.reload_motion, "shotgun_shells")
        self.assertEqual(revolver.reload_motion, "revolver_cylinder")
        self.assertEqual(sniper.reload_motion, "bolt_action")

    def test_todo_personagem_tem_interacao_classificada(self) -> None:
        defender_roles = {str(data["role"]) for data in main.DEFENSES.values()}
        self.assertEqual(defender_roles, set(DEFENDER_INTERACTIONS))

        enemy_tags = {
            str(tag)
            for data in main.ENEMIES.values()
            for tag in data.get("tags", ())
        }
        classified = set(ENEMY_ACTIVE_INTERACTIONS) | set(ENEMY_PASSIVE_TRAITS)
        self.assertEqual(enemy_tags, classified)
        self.assertEqual(
            set(main.ACTIVE_ENEMY_SKILL_TAGS),
            set(ENEMY_ACTIVE_INTERACTIONS),
        )

    def test_perspectiva_aplica_a_mesma_ancora_ao_cano(self) -> None:
        data = main.DEFENSES["agente_entrada"]
        rear = main.Defender("agente_entrada", "Agente", 0, 2, data, 0, region="city")
        front = main.Defender("agente_entrada", "Agente", 3, 2, data, 0, region="city")
        rear_origin = main.defender_weapon_origin(rear)
        front_origin = main.defender_weapon_origin(front)
        self.assertLess(rear_origin[0] - rear.x, front_origin[0] - front.x)
        self.assertLess(rear.y - rear_origin[1], front.y - front_origin[1])

    def test_bombeiro_acompanha_o_bocal_em_cada_quadro(self) -> None:
        data = main.DEFENSES["bombeiro_hidraulico"]
        defender = main.Defender(
            "bombeiro_hidraulico",
            "Bombeiro",
            0,
            2,
            data,
            0,
            region="beach",
        )
        defender.visual_animation = self._water_animation()
        defender.visual_animation.play("shoot", restart=True)
        origins = []
        for index in range(8):
            defender.visual_animation.seek_frame(index)
            origins.append(main.defender_weapon_origin(defender))
        self.assertLess(max(x for x, _y in origins) - min(x for x, _y in origins), 6.0)
        layout = DEFENDER_LAYOUTS["beach_waterjet"]
        for index, frame in enumerate(defender.visual_animation.animations["shoot"].frames):
            forward, height = layout.muzzle_cycle[index]
            source_x = round(frame.get_width() / 2 + forward * layout.source_height / layout.body_height)
            source_y = round(frame.get_height() - height * layout.source_height / layout.body_height)
            neighborhood = pygame.Rect(source_x - 2, source_y - 2, 5, 5).clip(frame.get_rect())
            self.assertGreater(
                pygame.mask.from_surface(frame.subsurface(neighborhood), threshold=8).count(),
                0,
                f"água começa fora do bocal no quadro {index}",
            )

    def test_todo_disparo_de_soldado_encosta_no_equipamento(self) -> None:
        clips = main.build_production_clips()
        ignored = {"radio", "promoter", "barrier", "mine", "suicide_bomber", "sonar", "shield", "blade"}
        region_by_key = {
            key: region
            for region, roster in main.REGION_ROSTERS.items()
            for key, _display in roster
        }
        for key, actor in main.DEFENDER_ACTOR_BY_KEY.items():
            role = str(main.DEFENSES[key]["role"])
            if role in ignored:
                continue
            defender = main.Defender(
                key,
                key,
                1,
                2,
                main.DEFENSES[key],
                0,
                region=region_by_key[key],
            )
            defender.visual_animation = main.new_production_animation(clips, actor)
            defender.visual_animation.play("shoot", restart=True)
            layout = DEFENDER_LAYOUTS[actor]
            depth = main.lane_depth(defender.region, defender.row)
            for index, frame in enumerate(defender.visual_animation.animations["shoot"].frames):
                defender.visual_animation.seek_frame(index)
                world_x, world_y = main.defender_weapon_origin(defender)
                ratio = layout.source_height / layout.body_height
                source_x = round(frame.get_width() / 2 + (world_x - defender.render_x) / depth * ratio)
                source_y = round(frame.get_height() - (defender.y - world_y) / depth * ratio)
                neighborhood = pygame.Rect(source_x - 2, source_y - 2, 5, 5).clip(frame.get_rect())
                self.assertGreater(neighborhood.width * neighborhood.height, 0, f"origem fora da caixa: {key}:{index}")
                self.assertGreater(
                    pygame.mask.from_surface(frame.subsurface(neighborhood), threshold=8).count(),
                    0,
                    f"projétil fora do equipamento: {key}:{index}",
                )

    def test_projeteis_de_zumbis_encostam_na_pose_de_habilidade(self) -> None:
        clips = main.build_production_clips()
        region_by_key = {
            key: region
            for region in main.REGION_ENEMIES
            for key in (
                main.REGION_ENEMIES[region]
                + main.REGION_SUBBOSSES[region]
                + main.REGION_BOSSES[region]
            )
        }
        cases: list[tuple[str, str]] = []
        for key, data in main.ENEMIES.items():
            tags = set(data.get("tags", ()))
            if "acid" in tags:
                cases.append((key, "acid"))
            elif "gun" in tags:
                cases.append((key, "enemy_bullet"))
        for key, data in main.BOSSES.items():
            kind = {
                "comandante": "enemy_bullet",
                "alfa": "acid",
                "colosso": "mortar",
                "leviathan": "torpedo",
            }.get(str(data.get("type", "")))
            if kind:
                cases.append((key, kind))
        for key, kind in cases:
            if key not in region_by_key or key not in main.ENEMY_ACTOR_BY_KEY:
                continue
            data = main.BOSSES[key] if key in main.BOSSES else main.ENEMIES[key]
            enemy = main.Enemy(key, 1, data, region_by_key[key], 8, x=820)
            actor = main.ENEMY_ACTOR_BY_KEY[key]
            enemy.visual_animation = main.new_production_animation(clips, actor)
            enemy.visual_animation.play("skill", restart=True)
            category = "boss" if enemy.is_boss else ("subboss" if data.get("subboss") else "common")
            body_height, source_height = main.ENEMY_BODY_LAYOUTS[category]
            depth = main.lane_depth(enemy.region, enemy.row)
            for index, frame in enumerate(enemy.visual_animation.animations["skill"].frames):
                enemy.visual_animation.seek_frame(index)
                world_x, world_y = main.Battle.enemy_projectile_origin(enemy, kind)
                ratio = source_height / body_height
                source_x = round(frame.get_width() / 2 + (world_x - enemy.x) / depth * ratio)
                source_y = round(frame.get_height() - (enemy.y - world_y) / depth * ratio)
                neighborhood = pygame.Rect(source_x - 2, source_y - 2, 5, 5).clip(frame.get_rect())
                self.assertGreater(neighborhood.width * neighborhood.height, 0, f"origem fora da caixa: {key}:{kind}:{index}")
                self.assertGreater(
                    pygame.mask.from_surface(frame.subsurface(neighborhood), threshold=8).count(),
                    0,
                    f"habilidade fora do zumbi: {key}:{kind}:{index}",
                )

    @staticmethod
    def _water_animation():
        clips = main.build_production_clips()
        return main.new_production_animation(clips, "beach_waterjet")


if __name__ == "__main__":
    unittest.main()
