"""Links locais do README precisam apontar para arquivos versionados."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationLinkTests(unittest.TestCase):
    def test_readme_internal_links_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)

        for target in targets:
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            path = target.split("#", maxsplit=1)[0]
            self.assertTrue(
                (ROOT / path).is_file(),
                f"Link interno quebrado no README.md: {target}",
            )


if __name__ == "__main__":
    unittest.main()
