"""Bloqueia pacote com código novo e binário antigo ou DLL residual."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

tool = Path(__file__).resolve().parents[1] / "tools/release_metadata.py"
spec = importlib.util.spec_from_file_location("release_metadata_test", tool)
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("main.py", "project.toml", "requirements-build-lock.txt", "assets/manifest.json",
                     "src/game.py", "tools/build.py", "tools/game.spec", "SoldadosVsZumbis.exe"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        (self.root / "_internal").mkdir()
        self.revision = metadata.source_revision(self.root)
        (self.root / "_internal/revision.json").write_text(json.dumps(self.revision), encoding="utf-8")
        stamp = {"revision": self.revision, "runtime": metadata.runtime_hashes(self.root)}
        (self.root / "build-info.json").write_text(json.dumps(stamp), encoding="utf-8")

    def test_identical_build_passes(self):
        self.assertEqual(self.revision, metadata.verify_build(self.root)["revision"])

    def test_source_change_rejected(self):
        (self.root / "src/game.py").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Código alterado"):
            metadata.verify_build(self.root)

    def test_stale_runtime_file_rejected(self):
        (self.root / "_internal/old.dll").write_bytes(b"stale")
        with self.assertRaisesRegex(ValueError, "bibliotecas divergentes"):
            metadata.verify_build(self.root)

    def test_modified_executable_rejected(self):
        (self.root / "SoldadosVsZumbis.exe").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "bibliotecas divergentes"):
            metadata.verify_build(self.root)
