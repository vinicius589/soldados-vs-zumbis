"""Funções pequenas sem estado de jogo."""
from __future__ import annotations





def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def title_case(value: str) -> str:
    return value.replace("_", " ").title()
