"""Progresso validado e gravação por substituição, sem truncar o save anterior."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from .config import (
    SAVE_PATH,
    TOTAL_WAVES,
)

from .content import (
    REGIONS,
)

logger = logging.getLogger(__name__)


def make_save() -> dict:
    # As regiões são escolhas de estilo e desafio, não uma trava de conteúdo.
    return {"unlocked": list(REGIONS), "completed": [], "best_wave": {}}


def normalize_save(data: object) -> dict:
    """Aceita saves antigos e descarta campos malformados, preservando os válidos."""
    result = make_save()
    if not isinstance(data, dict):
        return result
    completed = data.get('completed', [])
    if isinstance(completed, list):
        result['completed'] = list(dict.fromkeys(r for r in completed if isinstance(r, str) and r in REGIONS))
    waves = data.get('best_wave', {})
    if isinstance(waves, dict):
        result['best_wave'] = {
            region: min(TOTAL_WAVES, max(0, wave))
            for region, wave in waves.items()
            if region in REGIONS and type(wave) is int
        }
    return result


def load_save(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else SAVE_PATH
    try:
        return normalize_save(json.loads(path.read_text(encoding='utf-8')))
    except FileNotFoundError:
        return make_save()
    except (OSError, ValueError):
        logger.warning('Não foi possível ler a campanha em %s; usando progresso inicial.', path)
        return make_save()


def save_campaign(data: dict, path: Path | None = None) -> bool:
    """Escreve um temporário vizinho e substitui após flush/fsync.

    Falhas antes da substituição preservam o arquivo anterior. O retorno permite
    avisar o jogador; não garante durabilidade contra toda falha de hardware.
    """
    return write_json(normalize_save(data), Path(path) if path is not None else SAVE_PATH)


def write_json(data: dict, path: Path) -> bool:
    """Grava JSON completo num temporário vizinho e só então substitui o destino."""
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return True
    except (OSError, ValueError, TypeError):
        logger.exception('Não foi possível salvar a campanha em %s.', path)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.warning('Não foi possível remover o temporário %s.', temporary)
