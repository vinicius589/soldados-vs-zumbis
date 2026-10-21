"""Contratos de dependências, cache e persistência da versão modular."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from svz.assets import Assets
from svz.cache import SurfaceCache
from svz.persistence import load_save, make_save, normalize_save, save_campaign


class PersistenceTests(unittest.TestCase):
    def test_round_trip_and_legacy_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'save.json'
            data = {'unlocked': ['city'], 'completed': ['city'], 'best_wave': {'city': 12, 'beach': 7}}
            self.assertTrue(save_campaign(data, path))
            loaded = load_save(path)
            self.assertEqual(loaded['completed'], ['city'])
            self.assertEqual(loaded['best_wave'], data['best_wave'])
            self.assertEqual(len(loaded['unlocked']), 3)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_invalid_schema_cannot_break_campaign_screen(self):
        for data in (None, [], {'completed': 4, 'best_wave': []}):
            self.assertEqual(normalize_save(data), make_save())
        data = normalize_save({'completed': ['city', 'city', {}, 'unknown'], 'best_wave': {'city': 900, 'beach': True, 'desert': '12'}})
        self.assertEqual(data['completed'], ['city'])
        self.assertEqual(data['best_wave'], {'city': 12})

    def test_corrupted_file_is_not_overwritten_on_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'save.json'
            path.write_bytes(b'\xffbroken')
            with self.assertLogs('svz.persistence', level='WARNING'):
                self.assertEqual(load_save(path), make_save())
            self.assertEqual(path.read_bytes(), b'\xffbroken')

    def test_failed_replace_preserves_previous_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'save.json'
            previous = json.dumps(make_save())
            path.write_text(previous, encoding='utf-8')
            with patch('svz.persistence.os.replace', side_effect=PermissionError('simulated')), self.assertLogs('svz.persistence', level='ERROR'):
                self.assertFalse(save_campaign({'completed': ['city']}, path))
            self.assertEqual(path.read_text(encoding='utf-8'), previous)
            self.assertEqual(list(Path(directory).iterdir()), [path])


class CacheTests(unittest.TestCase):
    def test_lru_keeps_recent_entry_and_evicts_oldest(self):
        cache = SurfaceCache(max_entries=2)
        surfaces = [pygame.Surface((4, 4)) for _ in range(3)]
        cache[surfaces[0]] = (1, 2)
        cache[surfaces[1]] = (3, 4)
        self.assertEqual(cache.get(surfaces[0]), (1, 2))
        cache[surfaces[2]] = (5, 6)
        self.assertIsNone(cache.get(surfaces[1]))
        self.assertEqual(cache.get(surfaces[0]), (1, 2))
        self.assertEqual(cache.evictions, 1)

    def test_buffer_budget_under_many_distinct_sizes(self):
        cache = SurfaceCache(max_bytes=4096, max_entries=500)
        source = pygame.Surface((8, 8))
        for side in range(1, 100):
            cache[(source, side)] = pygame.Surface((side, side))
            self.assertLessEqual(cache.bytes_used, 4096)
        self.assertGreater(cache.evictions, 0)
        cache.clear()
        self.assertEqual(cache.bytes_used, 0)
        self.assertEqual(len(cache), 0)

    def test_scale_reuses_same_surface_without_confusing_distinct_sources(self):
        assets = Assets()
        red, blue = pygame.Surface((8, 8)), pygame.Surface((8, 8))
        red.fill('red')
        blue.fill('blue')
        first = assets.scaled(red, 16, 16)
        self.assertIs(first, assets.scaled(red, 16, 16))
        second = assets.scaled(blue, 16, 16)
        self.assertEqual(first.get_at((0, 0)), pygame.Color('red'))
        self.assertEqual(second.get_at((0, 0)), pygame.Color('blue'))


class ArchitectureTests(unittest.TestCase):
    def test_no_runtime_import_cycles_or_dependency_on_entrypoint(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        graph = {}
        for path in root.glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            graph[path.stem] = set()
            # Runtime imports are module-level; TYPE_CHECKING blocks are excluded.
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, 'main', path.name)
                    if node.level == 1:
                        graph[path.stem].add(node.module)
                if isinstance(node, ast.Import):
                    self.assertNotIn('main', [n.name for n in node.names], path.name)
        done = set()
        def visit(name, stack):
            self.assertNotIn(name, stack, f'Ciclo: {stack} -> {name}')
            if name not in done:
                for dependency in graph.get(name, ()):
                    visit(dependency, stack + [name])
                done.add(name)
        for name in graph:
            visit(name, [])
        self.assertNotIn('app', graph['battle'])
        self.assertNotIn('rendering', graph['battle'])
        self.assertNotIn('battle', graph['content'])

    def test_no_duplicate_methods_in_core(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        for path in root.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.ClassDef):
                    names = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    self.assertEqual(len(names), len(set(names)), f'{path.name}:{node.name}')

    def test_enemy_ability_rules_are_isolated_from_battle(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        battle_tree = ast.parse((root / 'battle.py').read_text(encoding='utf-8'))
        abilities_tree = ast.parse((root / 'enemy_abilities.py').read_text(encoding='utf-8'))

        battle_class = next(node for node in battle_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'Battle')
        abilities_class = next(node for node in abilities_tree.body
                               if isinstance(node, ast.ClassDef) and node.name == 'EnemyAbilityMixin')
        battle_methods = {node.name for node in battle_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        ability_methods = {node.name for node in abilities_class.body
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'boss_skill', 'enemy_special', 'boss_entrance'}
        self.assertTrue(required <= ability_methods)
        self.assertTrue(required.isdisjoint(battle_methods))
        base_names = {name.id for base in battle_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('EnemyAbilityMixin', base_names)
        self.assertNotIn('battle', {
            node.module for node in abilities_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })

    def test_menu_screens_live_in_separate_mixin(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        menu_tree = ast.parse((root / 'menu_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        menu_class = next(node for node in menu_tree.body
                          if isinstance(node, ast.ClassDef) and node.name == 'MenuRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        menu_methods = {node.name for node in menu_class.body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        menu_entry_points = {'draw_loading', 'draw_title', 'draw_difficulty',
                             'draw_campaign', 'draw_characters', 'draw_story',
                             'draw_profile', 'draw_settings', 'draw_howto',
                             'draw_session_confirmation'}

        self.assertIn('MenuRenderingMixin', {
            name.id for base in renderer_class.bases for name in ast.walk(base)
            if isinstance(name, ast.Name)
        })
        self.assertTrue(menu_entry_points <= menu_methods)
        self.assertTrue(menu_entry_points.isdisjoint(renderer_methods))
        draw_method = next(node for node in renderer_class.body
                           if isinstance(node, ast.FunctionDef) and node.name == 'draw')
        dispatch_text = ast.unparse(draw_method)
        self.assertIn("scene == 'profile'", dispatch_text)
        self.assertIn('self.draw_profile()', dispatch_text)
        self.assertNotIn('rendering', {
            node.module for node in menu_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_enemy_motion_rules_are_isolated_from_battle(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        battle_tree = ast.parse((root / 'battle.py').read_text(encoding='utf-8'))
        motion_tree = ast.parse((root / 'enemy_motion.py').read_text(encoding='utf-8'))

        battle_class = next(node for node in battle_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'Battle')
        motion_class = next(node for node in motion_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'EnemyMotionMixin')
        battle_methods = {node.name for node in battle_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        motion_methods = {node.name for node in motion_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'blocker_for', 'swept_blocker_for', 'begin_jump',
                    'begin_dig', 'update_enemy_motion'}
        self.assertTrue(required <= motion_methods)
        self.assertTrue(required.isdisjoint(battle_methods))
        base_names = {name.id for base in battle_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('EnemyMotionMixin', base_names)
        self.assertNotIn('battle', {
            node.module for node in motion_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_combat_actions_are_isolated_from_battle(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        battle_tree = ast.parse((root / 'battle.py').read_text(encoding='utf-8'))
        actions_tree = ast.parse((root / 'combat_actions.py').read_text(encoding='utf-8'))

        battle_class = next(node for node in battle_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'Battle')
        actions_class = next(node for node in actions_tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'CombatActionsMixin')
        battle_methods = {node.name for node in battle_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        action_methods = {node.name for node in actions_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'damage_channel', 'take_enemy_damage', 'damage_defender',
                    'kill_defender', 'kill_enemy', 'fire_defender',
                    'utility_defender', 'update_self_reload'}
        self.assertTrue(required <= action_methods)
        self.assertTrue(required.isdisjoint(battle_methods))
        base_names = {name.id for base in battle_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('CombatActionsMixin', base_names)
        self.assertNotIn('battle', {
            node.module for node in actions_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_effect_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        effects_tree = ast.parse((root / 'effects_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        effects_class = next(node for node in effects_tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'EffectsRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        effects_methods = {node.name for node in effects_class.body
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'draw_linked_skill_effect', 'draw_gas_cloud', 'draw_visual_effects',
                    'blit_effect_frame', 'blit_muzzle_cycle', 'frame_has_muzzle_flash'}
        self.assertTrue(required <= effects_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('EffectsRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in effects_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_entity_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        entity_tree = ast.parse((root / 'entity_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        entity_class = next(node for node in entity_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'EntityRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        entity_methods = {node.name for node in entity_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'defender_sprite', 'enemy_sprite', 'draw_actor_sprite',
                    'draw_fallen', 'draw_defender', 'draw_enemy'}
        self.assertTrue(required <= entity_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('EntityRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in entity_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_status_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        status_tree = ast.parse((root / 'status_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        status_class = next(node for node in status_tree.body
                            if isinstance(node, ast.ClassDef) and node.name == 'StatusRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        status_methods = {node.name for node in status_class.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'draw_battle_status', 'draw_scores', 'draw_result_overlay'}
        self.assertTrue(required <= status_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('StatusRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in status_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_projectile_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        projectile_tree = ast.parse((root / 'projectile_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        projectile_class = next(node for node in projectile_tree.body
                                if isinstance(node, ast.ClassDef) and node.name == 'ProjectileRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        projectile_methods = {node.name for node in projectile_class.body
                              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'draw_pressurized_water', 'draw_combustion_flame',
                    'draw_elemental_stream', 'draw_gas_grenade_projectile',
                    'draw_projectiles'}
        self.assertTrue(required <= projectile_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('ProjectileRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in projectile_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_battle_hud_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        hud_tree = ast.parse((root / 'battle_hud_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        hud_class = next(node for node in hud_tree.body
                         if isinstance(node, ast.ClassDef) and node.name == 'BattleHudRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        hud_methods = {node.name for node in hud_class.body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        self.assertIn('draw_battle_top', hud_methods)
        self.assertNotIn('draw_battle_top', renderer_methods)
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('BattleHudRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in hud_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_card_rendering_helpers_are_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        cards_tree = ast.parse((root / 'card_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        cards_class = next(node for node in cards_tree.body
                           if isinstance(node, ast.ClassDef) and node.name == 'CardRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        cards_methods = {node.name for node in cards_class.body
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'blit_actor_in_rect', 'draw_portrait_backdrop', 'card_sprite',
                    'card_metrics', 'draw_wrapped'}
        self.assertTrue(required <= cards_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('CardRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in cards_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_rendering_primitives_are_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        primitives_tree = ast.parse((root / 'rendering_primitives.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        primitives_class = next(node for node in primitives_tree.body
                                if isinstance(node, ast.ClassDef) and node.name == 'RenderingPrimitivesMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        primitives_methods = {node.name for node in primitives_class.body
                              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'button_rect', 'draw_text', 'panel', 'button'}
        self.assertTrue(required <= primitives_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('RenderingPrimitivesMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in primitives_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_battle_overlay_rendering_is_isolated_from_main_renderer(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        overlay_tree = ast.parse((root / 'battle_overlay_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        overlay_class = next(node for node in overlay_tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'BattleOverlayRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        overlay_methods = {node.name for node in overlay_class.body
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'draw_lane_bombs', 'draw_particles'}
        self.assertTrue(required <= overlay_methods)
        self.assertTrue(required.isdisjoint(renderer_methods))
        base_names = {name.id for base in renderer_class.bases for name in ast.walk(base)
                      if isinstance(name, ast.Name)}
        self.assertIn('BattleOverlayRenderingMixin', base_names)
        self.assertNotIn('rendering', {
            node.module for node in overlay_tree.body
            if isinstance(node, ast.ImportFrom) and node.level == 1
        })


    def test_health_and_ammo_bars_live_with_battle_hud(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'svz'
        renderer_tree = ast.parse((root / 'rendering.py').read_text(encoding='utf-8'))
        hud_tree = ast.parse((root / 'battle_hud_rendering.py').read_text(encoding='utf-8'))

        renderer_class = next(node for node in renderer_tree.body
                              if isinstance(node, ast.ClassDef) and node.name == 'GameRenderer')
        hud_class = next(node for node in hud_tree.body
                         if isinstance(node, ast.ClassDef) and node.name == 'BattleHudRenderingMixin')
        renderer_methods = {node.name for node in renderer_class.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        hud_methods = {node.name for node in hud_class.body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        required = {'draw_battle_top', 'health_bar', 'ammo_bar'}
        self.assertTrue(required <= hud_methods)
        self.assertTrue({'health_bar', 'ammo_bar'}.isdisjoint(renderer_methods))


if __name__ == '__main__':
    unittest.main()
