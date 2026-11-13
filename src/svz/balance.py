"""Atributos fixos por tipo; a onda não multiplica vida nem dano."""


def enemy_wave_scale(wave: int) -> float:
    """Compatibilidade com os chamadores existentes: vida básica integral."""
    return 1.0


def enemy_damage_scale(wave: int) -> float:
    return 1.0


def boss_wave_scale(wave: int) -> float:
    return 1.0


def boss_damage_scale(wave: int) -> float:
    return 1.0
