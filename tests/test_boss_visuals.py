"""Testes para a configuração compartilhada dos efeitos visuais dos chefes."""

from __future__ import annotations

from src.game.battle import BOSS_SKILL_VISUALS, Battle


def test_tabela_visual_cobre_todos_os_tipos_de_chefe() -> None:
    assert set(BOSS_SKILL_VISUALS) == {
        "bruto_demolidor",
        "comandante",
        "alfa",
        "mutante",
        "necromante",
        "colosso",
        "tide",
        "hunter",
        "leviathan",
    }


def test_tipos_de_chefe_aquaticos_compartilham_efeito() -> None:
    esperado = ("tidal_surge", (95, 195, 239))
    assert BOSS_SKILL_VISUALS["tide"] == esperado
    assert BOSS_SKILL_VISUALS["hunter"] == esperado
    assert BOSS_SKILL_VISUALS["leviathan"] == esperado


def test_helper_preserva_dados_e_escala_do_efeito() -> None:
    class EffectRecorder:
        def __init__(self) -> None:
            self.effects = []

        @staticmethod
        def enemy_effect_origin(_enemy: object, _visual_kind: str) -> tuple[int, int]:
            return 120, 240

    recorder = EffectRecorder()
    enemy = object()

    Battle._append_boss_visual_effect(
        recorder,
        enemy,
        "ground_slam",
        (230, 91, 61),
        0.72,
        scale=1.45,
    )

    assert len(recorder.effects) == 1
    effect = recorder.effects[0]
    assert (effect.kind, effect.x, effect.y) == ("ground_slam", 120, 240)
    assert effect.color == (230, 91, 61)
    assert effect.duration == 0.72
    assert effect.scale == 1.45
    assert effect.owner is enemy
    assert effect.anchor_kind == "ground_slam"
