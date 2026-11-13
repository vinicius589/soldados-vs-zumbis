"""Compatibilidade com salvamentos reais das duas linhas e isolamento de dados."""
from contextlib import closing
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")
import pygame
from svz.app import Game
from svz.data_migration import migrate_legacy_data, prepare_default_data
from svz.paths import data_dir
from svz.scoring import ScoreStore
from svz.session_store import SessionStore
from svz.snapshot import SCHEMA, capture, restore

FIXTURES = Path(__file__).parent / "fixtures"


class SnapshotMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.game = Game(save_path=Path(cls.temp.name) / "campanha.json")
        while cls.game.scene == "loading":
            cls.game.update(1 / 60)
        cls.game.audio.set_enabled(False)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.temp.cleanup()

    def test_original_fixtures_preserve_progress_health_and_consumables(self):
        for filename, timer, ammo in (("alfa_schema1.json", 0, 12), ("v153_schema2.json", 3, 0)):
            with self.subTest(filename=filename):
                snapshot = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
                original = copy.deepcopy(snapshot)
                battle, _ = restore(snapshot, self.game)
                self.assertEqual(snapshot, original)
                self.assertEqual(battle.score, 140)
                self.assertEqual(battle.match_id, snapshot["battle"]["match_id"])
                self.assertEqual(battle.supplies, snapshot["battle"]["supplies"])
                self.assertEqual(battle.first_wave_countdown, timer)
                self.assertEqual(battle.defenders[0].tactical_ammo_timer, ammo)
                self.assertAlmostEqual(battle.enemies[0].hp / battle.enemies[0].max_hp, .4)
                if filename == "alfa_schema1.json":
                    self.assertEqual(battle.player_name, "Ana")
                current = capture(battle)
                self.assertEqual(current["schema"], 3)
                again, _ = restore(current, self.game)
                self.assertEqual(capture(again), current)

    def test_legacy_documents_load_and_resave_with_current_schema(self):
        for filename in ("alfa_schema1.json", "v153_schema2.json"):
            with tempfile.TemporaryDirectory() as folder:
                store = SessionStore(Path(folder) / "campanha.json")
                old = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
                raw = json.dumps({"schema": old["schema"], "snapshot": old})
                store.path.write_text(raw, encoding="utf-8")
                battle, _ = restore(store.load(), self.game)
                self.assertEqual(store.path.read_text(encoding="utf-8"), raw)
                self.assertTrue(store.save(capture(battle)))
                self.assertEqual(store.read_document(store.path)["schema"], SCHEMA)
                self.assertEqual(store.read_document(store.backup_path)["snapshot"], old)

    def test_current_schema_does_not_silently_fill_missing_fields(self):
        old = json.loads((FIXTURES / "alfa_schema1.json").read_text(encoding="utf-8"))
        battle, _ = restore(old, self.game)
        current = capture(battle)
        del current["battle"]["first_wave_countdown"]
        with self.assertRaises(ValueError):
            restore(current, self.game)
        current = capture(battle)
        defender = next(o for o in current["objects"] if o["type"] == "Defender")
        del defender["fields"]["tactical_ammo_timer"]
        with self.assertRaises(ValueError):
            restore(current, self.game)

    def test_future_and_mismatched_document_schemas_are_rejected(self):
        old = json.loads((FIXTURES / "alfa_schema1.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            store = SessionStore(Path(folder) / "campanha.json")
            for outer, inner in ((3, 2), (4, 4), (True, True)):
                old["schema"] = inner
                store.path.write_text(json.dumps({"schema": outer, "snapshot": old}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    store.read_document(store.path)

    def test_resume_diagnostic_accepts_both_legacy_fixtures_without_rewriting(self):
        from svz.diagnostics import verify_resume
        for filename in ("alfa_schema1.json", "v153_schema2.json"):
            with tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                store = SessionStore(folder / "campanha.json")
                old = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
                raw = json.dumps({"schema": old["schema"], "snapshot": old})
                store.path.write_text(raw, encoding="utf-8")
                verify_resume(str(folder / "diagnostico.json"), str(folder / "campanha.json"))
                result = json.loads((folder / "diagnostico.json").read_text(encoding="utf-8"))
                self.assertTrue(result["ok"])
                self.assertTrue(result["migration_applied"])
                self.assertEqual(result["schema"], 3)
                self.assertEqual(store.path.read_text(encoding="utf-8"), raw)


class DataMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root / "SoldadosVsZumbis"
        self.new = self.root / "SoldadosVsZumbis-Beta5"
        self.old.mkdir()

    def legacy_database(self):
        path = self.old / "campanha.pontuacoes.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE scores (id TEXT PRIMARY KEY, date TEXT, region TEXT, difficulty TEXT, wave INTEGER, victory INTEGER, points INTEGER)")
            db.execute("INSERT INTO scores VALUES ('legacy', '2026-10-30', 'city', 'medium', 4, 0, 140)")
        return path

    def test_old_database_upgrades_only_in_new_directory(self):
        source = self.legacy_database()
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertIn(source.name, migrate_legacy_data(self.old, self.new))
        store = ScoreStore(self.new / "campanha.json")
        rows, total = store.page()
        self.assertEqual(total, 1)
        self.assertEqual((rows[0][1], rows[0][-1]), ("Jogador", 140))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        with closing(sqlite3.connect(source)) as db:
            self.assertEqual(len(db.execute("PRAGMA table_info(scores)").fetchall()), 7)
        # A versão antiga continua podendo usar sua tabela de sete colunas.
        with closing(sqlite3.connect(source)) as db, db:
            db.execute("INSERT INTO scores VALUES ('another', '2026-10-30', 'city', 'medium', 2, 0, 10)")

    def test_alfa_profile_and_inventory_survive_copy(self):
        store = ScoreStore(self.old / "campanha.json")
        self.assertTrue(store.ensure_profile("Ana"))
        with closing(store.connect()) as db, db:
            db.execute("UPDATE player_profiles SET credits=120, medkits=2, tactical_ammo=3")
        migrate_legacy_data(self.old, self.new)
        self.assertEqual(ScoreStore(self.new / "campanha.json").profile("Ana"), store.profile("Ana"))

    def test_backup_includes_committed_wal_transactions(self):
        source = self.legacy_database()
        with closing(sqlite3.connect(source)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("INSERT INTO scores VALUES ('wal', '2026-10-30', 'city', 'medium', 2, 0, 10)")
            db.commit()
            self.assertTrue(Path(str(source) + "-wal").exists())
            migrate_legacy_data(self.old, self.new)
        self.assertEqual(ScoreStore(self.new / "campanha.json").page()[1], 2)

    def test_copy_is_once_only_and_does_not_overwrite_current_progress(self):
        (self.old / "campanha.json").write_text('{"old": true}')
        (self.old / "other.txt").write_text("not game data")
        self.assertEqual(migrate_legacy_data(self.old, self.new), ["campanha.json"])
        self.assertFalse((self.new / "other.txt").exists())
        (self.new / "campanha.json").write_text('{"new": true}')
        self.assertEqual(migrate_legacy_data(self.old, self.new), [])
        self.assertEqual((self.new / "campanha.json").read_text(), '{"new": true}')
        self.assertTrue((self.new / "migracao-legado.json").is_file())

    def test_failed_copy_does_not_publish_partial_data(self):
        (self.old / "campanha.json").write_text("original")
        with patch("svz.data_migration.shutil.copy2", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                migrate_legacy_data(self.old, self.new)
        self.assertFalse(self.new.exists())
        self.assertEqual((self.old / "campanha.json").read_text(), "original")
        self.assertFalse(list(self.root.glob(".svz-migration-*")))

    def test_corrupt_database_is_preserved_and_not_published(self):
        (self.old / "campanha.pontuacoes.sqlite3").write_bytes(b"invalid database")
        with self.assertRaises(sqlite3.DatabaseError):
            migrate_legacy_data(self.old, self.new)
        self.assertFalse(self.new.exists())
        self.assertEqual((self.old / "campanha.pontuacoes.sqlite3").read_bytes(), b"invalid database")

    def test_default_paths_and_explicit_overrides(self):
        (self.old / "campanha.json").write_text("{}")
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}, clear=True):
            self.assertEqual(data_dir(), self.new)
            self.assertEqual(prepare_default_data(), ["campanha.json"])
        for key in ("SVZ_DATA_DIR", "SVZ_SAVE_PATH"):
            with patch.dict(os.environ, {key: str(self.root / "custom")}, clear=True):
                with patch("svz.data_migration.migrate_legacy_data") as migrate:
                    self.assertEqual(prepare_default_data(), [])
                    migrate.assert_not_called()

    def test_missing_or_empty_source_does_not_create_destination(self):
        self.assertEqual(migrate_legacy_data(self.old, self.new), [])
        self.assertEqual(migrate_legacy_data(self.root / "missing", self.new), [])
        self.assertFalse(self.new.exists())
