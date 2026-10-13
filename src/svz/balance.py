"""Curvas de dificuldade por onda."""
from __future__ import annotations



from .config import (
    TOTAL_WAVES,
)
from .math_utils import (
    clamp,
)


def enemy_wave_scale(wave: int) -> float:
    """Mantém as primeiras ondas acolhedoras e endurece a reta final.

    A versão anterior começava com vida cheia e liberava ameaças depressa;
    assim, o primeiro contato parecia mais duro que a metade da campanha.
    """
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.66 + 1.50 * progress ** 1.55


def enemy_damage_scale(wave: int) -> float:
    """Escala separada para que o fim não seja só uma esponja de vida."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.62 + 1.10 * progress ** 1.50


def boss_wave_scale(wave: int) -> float:
    """Chefes escalam com a campanha sem virar paredes de vida.

    Um chefe deve mudar a montagem da linha, não exigir uma composição
    perfeita ou prender o jogador numa sequência infinita de atordoamentos.
    Por isso sua vida cresce mais devagar que a de uma horda comum.
    """
    # Chefes mantêm sua identidade, mas precisam cair com uma montagem boa
    # antes que a contenção de última linha vire o único plano viável.
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.78 + 1.25 * progress ** 1.40


def boss_damage_scale(wave: int) -> float:
    """Contém o dano físico dos chefes nas ondas altas."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.70 + 0.95 * progress ** 1.45
