"""Geometria pura dos efeitos de fluxo e água do renderizador.

As funções retornam vértices; não desenham superfícies nem dependem do estado
da partida. Isso permite testá-las sem inicializar a janela do jogo.
"""
from __future__ import annotations

import math

from .math_utils import clamp, lerp


def flow_points(
    start: tuple[float, float],
    end: tuple[float, float],
    elapsed: float,
    amplitude: float,
    count: int = 18,
) -> list[tuple[int, int]]:
    """Constrói um jato contínuo ondulado entre bocal e frente do fluxo."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1.0, math.hypot(dx, dy))
    normal_x, normal_y = -dy / length, dx / length
    points: list[tuple[int, int]] = []
    sample_count = max(3, count)
    for index in range(sample_count):
        q = index / (sample_count - 1)
        envelope = math.sin(q * math.pi)
        wave = math.sin(q * math.tau * 2.1 - elapsed * 31.0) * amplitude * envelope
        points.append(
            (
                int(lerp(start[0], end[0], q) + normal_x * wave),
                int(lerp(start[1], end[1], q) + normal_y * wave),
            )
        )
    points[0] = (int(start[0]), int(start[1]))
    points[-1] = (int(end[0]), int(end[1]))
    return points


def ribbon_polygon(
    points: list[tuple[int, int]],
    start_width: float,
    end_width: float,
    *,
    taper_tip: bool = False,
) -> list[tuple[int, int]]:
    """Cria as duas bordas de um fluxo para evitar o efeito de bolinhas."""
    if len(points) < 2:
        return points
    upper: list[tuple[int, int]] = []
    lower: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        before = points[max(0, index - 1)]
        after = points[min(len(points) - 1, index + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = max(1.0, math.hypot(dx, dy))
        normal_x, normal_y = -dy / length, dx / length
        q = index / max(1, len(points) - 1)
        width = lerp(start_width, end_width, q)
        if taper_tip:
            tip = clamp((q - 0.68) / 0.32, 0.0, 1.0)
            smooth_tip = tip * tip * (3.0 - 2.0 * tip)
            width *= lerp(1.0, 0.08, smooth_tip)
        upper.append((int(point[0] + normal_x * width), int(point[1] + normal_y * width)))
        lower.append((int(point[0] - normal_x * width), int(point[1] - normal_y * width)))
    return upper + list(reversed(lower))


def water_ribbon_polygon(
    points: list[tuple[int, int]],
    start_width: float,
    end_width: float,
    elapsed: float,
    phase: float = 0.0,
) -> list[tuple[int, int]]:
    """Bordas irregulares de uma coluna de água sob pressão."""
    if len(points) < 2:
        return points
    upper: list[tuple[int, int]] = []
    lower: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        before = points[max(0, index - 1)]
        after = points[min(len(points) - 1, index + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = max(1.0, math.hypot(dx, dy))
        normal_x, normal_y = -dy / length, dx / length
        q = index / max(1, len(points) - 1)
        pressure_loss = q * q
        ripple = math.sin(q * math.tau * 3.2 - elapsed * 22.0 + phase)
        width = lerp(start_width, end_width, pressure_loss) * (1.0 + ripple * 0.12)
        upper.append((int(point[0] + normal_x * width), int(point[1] + normal_y * width)))
        lower.append((int(point[0] - normal_x * width), int(point[1] - normal_y * width)))
    return upper + list(reversed(lower))
