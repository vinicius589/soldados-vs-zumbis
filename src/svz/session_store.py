"""Arquivo de retomada separado das conquistas; gravação por substituição."""
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
        self.path = path.with_name(path.stem + '.partida.json')
        self.error = ''

    def load(self):
        try:
            with self.path.open('rb') as stream:
                content = stream.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError('Arquivo de partida muito grande.')
            document = json.loads(content)
            if type(document) is not dict or set(document) != {'schema', 'snapshot'} or type(document.get('schema')) is not int or document['schema'] != SCHEMA:
                raise ValueError('Formato de partida incompatível.')
            snapshot = document.get('snapshot')
            if snapshot is not None and (type(snapshot) is not dict or snapshot.get('schema') != SCHEMA):
                raise ValueError('Dados da partida inválidos.')
            self.error = ''
            return snapshot
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, RecursionError):
            logger.exception('Não foi possível ler a partida em %s.', self.path)
            self.error = 'Não foi possível carregar a partida salva. O arquivo foi preservado.'
            return None

    def save(self, snapshot):
        document = {'schema': SCHEMA, 'snapshot': snapshot}
        try:
            if len(json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')) > MAX_BYTES:
                raise ValueError('Arquivo de partida muito grande.')
            ok = write_json(document, self.path)
        except (ValueError, TypeError, RecursionError):
            logger.exception('Estado de partida inválido para gravação.')
            ok = False
        self.error = '' if ok else 'Não foi possível salvar. A partida continua disponível nesta janela.'
        return ok

    def clear(self):
        # Tombstone evita reabrir uma partida descartada ou já concluída.
        return self.save(None)

