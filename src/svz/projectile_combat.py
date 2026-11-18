"""Contratos de impacto compartilhados pelo combate e pela apresentação.

Explosivos atingem o ponto escolhido no disparo; tiros diretos e fluxos
acompanham seu alvo enquanto ele existir. Não há aquisição de um novo alvo.
O estado serializado de Projectile permanece compatível com a versão 1.3.1.
"""
from __future__ import annotations

from .board import terrain_y
from .config import CELL_H, GOLD, ROWS
from .entities import Defender, Enemy
from .motion import VisualEffect


EXPLOSIVE_KINDS = frozenset({
    "grenade", "grenade_40mm", "mortar", "mortar_shell", "bazooka",
    "rpg7_rocket", "torpedo", "compact_torpedo", "gas_grenade",
})


def fixed_impact(projectile) -> bool:
    return projectile.radius > 0 and (projectile.kind in EXPLOSIVE_KINDS or not projectile.friendly)


def update_aim(battle, projectile) -> None:
    """Mantém o destino desenhado coerente com o acerto de tiros dirigidos."""
    if fixed_impact(projectile):
        return
    target = projectile.target
    population = battle.enemies if projectile.friendly else battle.defenders
    expected = Enemy if projectile.friendly else Defender
    if isinstance(target, expected) and any(actor is target for actor in population) and target.hp > 0:
        projectile.target_x = target.x
        projectile.target_y = target.y - (16 if projectile.friendly else 12)


def resolve_impact(battle, projectile) -> None:
    """Resolve uma chegada: captura as vítimas antes de aplicar qualquer dano."""
    target = projectile.target
    friendly = projectile.friendly
    expected = Enemy if friendly else Defender
    population = tuple(battle.enemies if friendly else battle.defenders)
    source = projectile.owner if isinstance(projectile.owner, Defender) else None
    # Referências a entidades removidas são preservadas pelo snapshot. O
    # fallback também cobre projéteis sem alvo, sem adicionar campos ao save.
    center_x = projectile.target_x
    center_y = projectile.target_y + (16 if friendly else 12)
    # Um impacto fixo pertence ao destino, não à posição atual do alvo/dono.
    # A faixa é reconstruível do destino já salvo; não muda o schema do save.
    row = target.row if not fixed_impact(projectile) and isinstance(target, expected) else min(
        range(ROWS), key=lambda r: abs(terrain_y(battle.region, r, center_x) - center_y)
    )
    cross_lanes = not friendly and isinstance(projectile.owner, Enemy) and projectile.owner.is_boss
    victims = []
    for other in population:
        if not isinstance(other, expected) or other.hp <= 0:
            continue
        primary = other is target
        in_lane = other.row == row or (cross_lanes and abs(other.y - center_y) < CELL_H * .75)
        in_area = projectile.radius > 0 and in_lane and abs(other.x - center_x) < projectile.radius
        if primary and (not fixed_impact(projectile) or in_area):
            victims.append((other, projectile.damage))
        elif in_area:
            victims.append((other, projectile.damage * (.72 if friendly else .5)))
    for victim, damage in victims:
        if friendly:
            battle.take_enemy_damage(victim, damage, projectile.effect, source)
        else:
            battle.damage_defender(victim, damage, projectile.effect)
    # A chegada e sua apresentação independem da sobrevivência do alvo.
    x, y = projectile.target_x, projectile.target_y
    if friendly:
        if projectile.kind == "gas_grenade":
            battle.effects.append(VisualEffect("toxic_wave", x, y - 10, (132, 239, 80), 1.05, scale=1.08))
        elif projectile.kind in EXPLOSIVE_KINDS:
            scale = 1.35 if projectile.kind in {"bazooka", "rpg7_rocket"} else 1.12 if projectile.kind in {"mortar", "mortar_shell"} else .96
            battle.explosion(x, y, GOLD, 16, scale=scale)
    else:
        kind, color, duration, scale = {
            "acid": ("toxic_impact", (132, 239, 80), .30, .78),
            "torpedo": ("water_impact", (102, 224, 244), .32, .92),
        }.get(projectile.kind, ("ballistic_impact", (241, 198, 122), .18, .30))
        battle.effects.append(VisualEffect(kind, x, y, color, duration, scale=scale))
