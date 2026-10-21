"""Partida atômica com cópia anterior e recuperação sem apagar arquivo inválido."""
from pathlib import Path
import json
import logging
from .config import SAVE_PATH
from .persistence import write_json
from .snapshot import SCHEMA

logger = logging.getLogger(__name__)
MAX_BYTES = 4 * 1024 * 1024

class SessionStore:
    def __init__(self, campaign_path=None):
        path = Path(campaign_path) if campaign_path is not None else SAVE_PATH
        self.path = path.with_name(path.stem + ".partida.json")
        self.backup_path = self.path.with_suffix(".anterior.json")
        self.error = ""
        self.recovered_backup = False

    @staticmethod
    def read_document(path):
        with path.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError("Arquivo de partida muito grande.")
        document = json.loads(content)
        if (type(document) is not dict or set(document) != {"schema", "snapshot"}
                or type(document.get("schema")) is not int or document["schema"] != SCHEMA):
            raise ValueError("Formato de partida incompatível.")
        snapshot = document["snapshot"]
        if snapshot is not None and (type(snapshot) is not dict or snapshot.get("schema") != SCHEMA):
            raise ValueError("Dados da partida inválidos.")
        return document

    def load_backup(self):
        try:
            snapshot = self.read_document(self.backup_path)["snapshot"]
            if snapshot is not None:
                self.recovered_backup = True
                self.error = "Recuperada a cópia anterior. O arquivo com problema foi preservado."
            return snapshot
        except (OSError, ValueError, TypeError, RecursionError):
            return None

    def load(self):
        try:
            document = self.read_document(self.path)
            self.error = ""
            return document["snapshot"]
        except FileNotFoundError:
            return self.load_backup()
        except (OSError, ValueError, TypeError, RecursionError):
            logger.exception("Não foi possível ler a partida em %s.", self.path)
            self.error = "Não foi possível carregar a partida salva. O arquivo foi preservado."
            return self.load_backup()

    def save(self, snapshot):
        document = {"schema": SCHEMA, "snapshot": snapshot}
        try:
            if len(json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")) > MAX_BYTES:
                raise ValueError("Arquivo de partida muito grande.")
            try:
                previous = self.read_document(self.path)
            except (OSError, ValueError, TypeError, RecursionError):
                previous = None
            # Após a recuperação, a cópia atual pode ter JSON válido e grafo
            # inválido. Não a promova sobre a cópia anterior que foi recuperada.
            if (not self.recovered_backup and previous is not None
                    and previous["snapshot"] is not None and snapshot is not None):
                if not write_json(previous, self.backup_path):
                    raise OSError("Não foi possível proteger a cópia anterior.")
            ok = write_json(document, self.path)
        except (OSError, ValueError, TypeError, RecursionError):
            logger.exception("Falha ao gravar partida.")
            ok = False
        self.error = "" if ok else "Não foi possível salvar. A partida continua disponível nesta janela."
        if ok:
            self.recovered_backup = False
        return ok

    def clear(self):
        if not self.save(None):
            return False
        if not write_json({"schema": SCHEMA, "snapshot": None}, self.backup_path):
            self.error = "Não foi possível descartar a cópia anterior."
            return False
        return True

