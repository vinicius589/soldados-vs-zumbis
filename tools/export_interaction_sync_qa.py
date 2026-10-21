"""Prévia curta das interações sincronizadas no renderizador real."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import Game
from tools.export_gameplay_roster_qa import (
    _defender_review,
    _enemy_review,
    _save_gif,
    _save_montage,
)


OUTPUT = ROOT / "visual_qa_beta4" / "interacoes_sincronizadas"


def _save_large_gif(
    frames: list[Image.Image], durations: list[int], path: Path,
) -> None:
    """Amplia a prévia com suavização sem modificar os quadros do jogo."""
    enlarged = [
        frame.resize((frame.width * 2, frame.height * 2), Image.Resampling.LANCZOS)
        for frame in frames
    ]
    _save_gif(enlarged, durations, path)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game(integration_preview=True)
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()

    frames, durations, samples = _defender_review(
        game,
        "beach",
        "bombeiro_hidraulico",
        "Bombeiro Hidráulico",
    )
    _save_gif(frames, durations, OUTPUT / "bombeiro_agua_conectada.gif")
    _save_large_gif(
        frames, durations, OUTPUT / "bombeiro_agua_conectada_ampliado.gif",
    )
    # Quadro pequeno e direto para revisar o ponto mais importante sem
    # depender do mosaico completo: a água precisa nascer no bocal da mangueira.
    samples[1].save(OUTPUT / "bombeiro_jato_revisado.png")
    move_count = len(game.assets.production_clips["beach_waterjet"]["move"].frames)
    shoot_count = len(game.assets.production_clips["beach_waterjet"]["shoot"].frames)
    shoot_frames = frames[move_count:move_count + shoot_count]
    _save_montage(
        "BOMBEIRO — CONTATO DO BOCAL NOS OITO QUADROS",
        [("1–4", shoot_frames[:4]), ("5–8", shoot_frames[4:8])],
        OUTPUT / "bombeiro_bocal_8_quadros.png",
    )
    rows = [("Bombeiro Hidráulico", samples)]

    for region, key, display, filename in (
        ("desert", "incinerador_deserto", "Incinerador do Deserto", "incinerador_chama_combustao.gif"),
        ("city", "especialista_antipraga", "Especialista Antipraga", "antipraga_granada_gas.gif"),
    ):
        unit_frames, unit_durations, unit_samples = _defender_review(
            game, region, key, display,
        )
        _save_gif(unit_frames, unit_durations, OUTPUT / filename)
        _save_large_gif(
            unit_frames,
            unit_durations,
            OUTPUT / f"{Path(filename).stem}_ampliado.gif",
        )
        actor_key = {
            "incinerador_deserto": "desert_incinerator",
            "especialista_antipraga": "city_antiplague",
        }[key]
        unit_move_count = len(game.assets.production_clips[actor_key]["move"].frames)
        unit_shoot_count = len(game.assets.production_clips[actor_key]["shoot"].frames)
        unit_shoot_frames = unit_frames[
            unit_move_count:unit_move_count + unit_shoot_count
        ]
        _save_montage(
            f"{display.upper()} — OITO QUADROS DE DISPARO",
            [("1–4", unit_shoot_frames[:4]), ("5–8", unit_shoot_frames[4:8])],
            OUTPUT / f"{key}_disparo_8_quadros.png",
        )
        rows.append((display, unit_samples))

    cases = (
        ("city", "cientista_helix", False, "Ácido nasce no equipamento"),
        ("desert", "curandeiro", False, "Cura acompanha o Curandeiro"),
        ("beach", "pescador_praga", False, "Rede permanece na própria faixa"),
        ("city", "bruto_demolidor", True, "Boss: impacto entre pistas autorizado"),
    )
    for region, key, boss, label in cases:
        frames, durations, samples = _enemy_review(
            game,
            region,
            key,
            boss=boss,
            show_target=True,
        )
        _save_gif(frames, durations, OUTPUT / f"{key}_interacao.gif")
        rows.append((label, samples))

    _save_montage(
        "INTERAÇÕES SINCRONIZADAS — CORPO, ORIGEM E EFEITO",
        rows,
        OUTPUT / "interacoes_sincronizadas.png",
    )
    pygame.quit()
    print(f"INTERACOES_SINCRONIZADAS: {OUTPUT}")


if __name__ == "__main__":
    main()
