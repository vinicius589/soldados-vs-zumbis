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
MAX_CAMPAIGN_BYTES = 64 * 1024


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
    records = data.get("by_difficulty", {})
    if isinstance(records, dict):
        clean = {}
        for difficulty, regions in records.items():
            if difficulty not in ("easy","medium","hard") or not isinstance(regions,dict):
                continue
            selected = {}
            for region, stats in regions.items():
                if region in REGIONS and isinstance(stats,dict) and type(stats.get("best_wave")) is int and type(stats.get("victory")) is bool:
                    selected[region] = {"best_wave": min(TOTAL_WAVES,max(0,stats["best_wave"])), "victory": stats["victory"]}
            if selected:
                clean[difficulty] = selected
        if clean:
            result["by_difficulty"] = clean
    return result


def load_save(path: Path | None = None, notices: list | None = None) -> dict:
    path = Path(path) if path is not None else SAVE_PATH
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_CAMPAIGN_BYTES + 1)
        if len(payload) > MAX_CAMPAIGN_BYTES:
            raise ValueError("Campanha excede o limite de tamanho.")
        return normalize_save(json.loads(payload))
    except FileNotFoundError:
        return make_save()
    except (OSError, ValueError, TypeError, RecursionError):
        logger.warning('Não foi possível ler a campanha em %s; usando progresso inicial.', path)
        if notices is not None:
            notices.append('Campanha inválida: progresso inicial carregado; arquivo preservado.')
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
    except (OSError, ValueError, TypeError, RecursionError):
        logger.exception('Não foi possível salvar a campanha em %s.', path)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.warning('Não foi possível remover o temporário %s.', temporary)
