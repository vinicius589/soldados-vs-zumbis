"""Passagem entre poses de combate no relógio do próprio ator."""
from dataclasses import dataclass, field

import numpy as np
import pygame

from .animation import AnimationClip, AnimationManager


@dataclass(frozen=True, slots=True)
class ActorClip(AnimationClip):
    """Guarda um desenho intermediário por par de poses, compartilhado pelo elenco."""

    inbetweens: dict[int, pygame.Surface] = field(default_factory=dict, compare=False, repr=False)

    def intermediate(self, index: int) -> pygame.Surface:
        if index not in self.inbetweens:
            following = (index + 1) % len(self.frames)
            self.inbetweens[index] = _between_poses(self.frames[index], self.frames[following])
        return self.inbetweens[index]


def _between_poses(first: pygame.Surface, second: pygame.Surface) -> pygame.Surface:
    """Desloca as faixas do desenho até metade do caminho para a pose seguinte."""
    if first is second or first.get_size() != second.get_size():
        return first
    width, height = first.get_size()
    # As duas poses já compartilham o pivô. A cor vem de uma única pose para
    # conservar os detalhes de armas e membros sem criar uma segunda silhueta.
    a = pygame.surfarray.array_alpha(first).T > 8
    b = pygame.surfarray.array_alpha(second).T > 8
    if not a.any() or not b.any():
        return first
    top_a, bottom_a = np.flatnonzero(a.any(axis=1))[[0, -1]]
    top_b, bottom_b = np.flatnonzero(b.any(axis=1))[[0, -1]]
    top = (top_a + top_b) / 2
    bottom = (bottom_a + bottom_b) / 2
    phase = (np.arange(height) - top) / max(1, bottom - top)
    ya = np.rint(top_a + phase * (bottom_a - top_a)).astype(int).clip(0, height - 1)
    yb = np.rint(top_b + phase * (bottom_b - top_b)).astype(int).clip(0, height - 1)
    left_a = a.argmax(axis=1)[ya]
    right_a = width - 1 - a[:, ::-1].argmax(axis=1)[ya]
    left_b = b.argmax(axis=1)[yb]
    right_b = width - 1 - b[:, ::-1].argmax(axis=1)[yb]
    occupied = b.any(axis=1)[yb]
    left = np.where(occupied, (left_a + left_b) / 2, left_a)
    right = np.where(occupied, (right_a + right_b) / 2, right_a)
    x = np.arange(width)[None, :]
    fraction = (x - left[:, None]) / np.maximum(1, right - left)[:, None]
    source_x = np.rint(left_a[:, None] + fraction * (right_a - left_a)[:, None]).astype(int)
    rgba = np.frombuffer(pygame.image.tobytes(first, "RGBA"), dtype=np.uint8).reshape(height, width, 4)
    pixels = rgba[ya[:, None], source_x.clip(0, width - 1)]
    pixels[(x < left[:, None] - 0.5) | (x > right[:, None] + 0.5)] = 0
    pixels[(phase < 0) | (phase > 1) | ~a.any(axis=1)[ya]] = 0
    return pygame.image.frombytes(pixels.tobytes(), (width, height), "RGBA")


class ActorAnimation(AnimationManager):
    @property
    def frame(self) -> pygame.Surface:
        clip = self.clip
        if not isinstance(clip, ActorClip):
            return super().frame
        if len(clip.frames) == 1:
            return super().frame
        if not clip.loop and self.frame_index == len(clip.frames) - 1:
            return super().frame
        # Interpolar apenas ciclos lentos. Nas ações, preservar os desenhos
        # de contato e recarga em vez de deformar mãos, armas ou mandíbulas.
        if self.state not in {"move", "idle"}:
            return super().frame
        duration = clip.frame_durations[self.frame_index]
        if duration < 0.30 * self.playback_rate or self.frame_elapsed < duration * 0.5:
            return super().frame
        return clip.intermediate(self.frame_index)
