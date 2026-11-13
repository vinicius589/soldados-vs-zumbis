"""Cópia inicial dos dados legados, sem modificar a instalação anterior."""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from .paths import data_dir

LEGACY_FILES = (
    "campanha.json", "campanha.partida.json", "campanha.partida.anterior.json",
    "campanha.settings.json", "campanha.video.json", "campanha.pontuacoes.sqlite3",
)


def migrate_legacy_data(source: Path, destination: Path) -> list[str]:
    """Publica a cópia inteira por rename; uma pasta existente nunca é mesclada.

    SQLite usa backup online para incluir transações presentes no WAL. Falhas
    deixam os originais intactos e não publicam uma migração parcial.
    """
    source, destination = Path(source), Path(destination)
    if destination.exists() or not source.is_dir():
        return []
    files = [name for name in LEGACY_FILES if (source / name).is_file()]
    if not files:
        return []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".svz-migration-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        for name in files:
            original, copied = source / name, stage / name
            if name.endswith(".sqlite3"):
                uri = original.resolve().as_uri() + "?mode=ro"
                with closing(sqlite3.connect(uri, uri=True, timeout=3)) as old:
                    with closing(sqlite3.connect(copied)) as new:
                        old.backup(new)
                        if new.execute("PRAGMA quick_check").fetchone() != ("ok",):
                            raise sqlite3.DatabaseError("Banco de pontuações inválido; original preservado.")
            else:
                shutil.copy2(original, copied)
        (stage / "migracao-legado.json").write_text(
            json.dumps({"source": str(source.resolve()), "copied": files}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            # No Windows rename falha se outra execução já criou o destino.
            stage.rename(destination)
        except FileExistsError:
            return []
    return files


def prepare_default_data() -> list[str]:
    # Diagnósticos, testes e caminhos escolhidos explicitamente não importam
    # dados pessoais nem alteram outras pastas por efeito colateral.
    if os.environ.get("SVZ_DATA_DIR") or os.environ.get("SVZ_SAVE_PATH"):
        return []
    destination = data_dir()
    return migrate_legacy_data(destination.with_name("SoldadosVsZumbis"), destination)
