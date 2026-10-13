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


if __name__ == '__main__':
    unittest.main()
