"""Cache LRU com orçamento explícito para superfícies derivadas imutáveis."""
from collections import OrderedDict
from typing import Hashable

import pygame


def _surface_bytes(value) -> int:
    if isinstance(value, pygame.Surface):
        return value.get_pitch() * value.get_height()
    if isinstance(value, tuple):
        return sum(_surface_bytes(item) for item in value)
    return 0


class SurfaceCache:
    """Retém a superfície de origem na chave para impedir reutilização de id.

    O orçamento conta buffers de origem e resultado de forma conservadora;
    não representa a memória total do processo nem o overhead de objetos Python.
    As superfícies devem permanecer imutáveis enquanto estiverem em cache.
    """

    def __init__(self, max_bytes: int = 32 * 1024 * 1024, max_entries: int = 512):
        if max_bytes < 0 or max_entries < 1:
            raise ValueError('Orçamento inválido para o cache.')
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.bytes_used = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._items = OrderedDict()

    def get(self, key: Hashable, default=None):
        entry = self._items.get(key)
        if entry is None:
            self.misses += 1
            return default
        self.hits += 1
        self._items.move_to_end(key)
        return entry[0]

    def __setitem__(self, key: Hashable, value) -> None:
        previous = self._items.pop(key, None)
        if previous is not None:
            self.bytes_used -= previous[1]
        size = _surface_bytes(key) + _surface_bytes(value)
        if size > self.max_bytes:
            return
        while self._items and (self.bytes_used + size > self.max_bytes or len(self._items) >= self.max_entries):
            _, (_, old_size) = self._items.popitem(last=False)
            self.bytes_used -= old_size
            self.evictions += 1
        self._items[key] = (value, size)
        self.bytes_used += size

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self.bytes_used = 0
