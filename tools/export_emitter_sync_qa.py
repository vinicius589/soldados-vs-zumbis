"""Exporta a revisão de origem para todo disparo e habilidade da Beta 4."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import (
    BOSSES,
    DEFENSES,
    ENEMIES,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
    Game,
)
from tools.export_gameplay_roster_qa import (
    REGION_LABELS,
    _defender_review,
    _enemy_review,
    _save_montage,
)


OUTPUT = ROOT / "visual_qa_beta4" / "emissores_sincronizados"
NON_EMITTER_ROLES = {
    "radio", "promoter", "barrier", "mine", "suicide_bomber", "sonar", "shield", "blade",
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game(integration_preview=True)
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()

    for region in ("city", "desert", "beach"):
        soldier_rows = []
        for key, display in REGION_ROSTERS[region]:
            if str(DEFENSES[key]["role"]) in NON_EMITTER_ROLES:
                continue
            _frames, _durations, samples = _defender_review(
                game,
                region,
                key,
                display,
                show_projectile_origin=True,
            )
            soldier_rows.append((display, samples))
        _save_montage(
            f"{REGION_LABELS[region]} — MUNIÇÃO PROPORCIONAL APÓS O CANO",
            soldier_rows,
            OUTPUT / f"soldados_emissores_{region}.png",
        )

        enemy_rows = []
        enemy_keys = (
            tuple((key, False) for key in REGION_ENEMIES[region])
            + tuple((key, False) for key in REGION_SUBBOSSES[region])
            + tuple((key, True) for key in REGION_BOSSES[region])
        )
        for key, boss in enemy_keys:
            _frames, _durations, samples = _enemy_review(
                game,
                region,
                key,
                boss=boss,
                show_target=True,
            )
            display = str((BOSSES if boss else ENEMIES)[key]["name"])
            enemy_rows.append((display, samples))
        _save_montage(
            f"{REGION_LABELS[region]} — CORPO, ALVO E HABILIDADE NA MESMA FAIXA",
            enemy_rows,
            OUTPUT / f"zumbis_habilidades_{region}.png",
        )

    pygame.quit()
    print(f"EMISSORES_SINCRONIZADOS: {OUTPUT}")


if __name__ == "__main__":
    main()
