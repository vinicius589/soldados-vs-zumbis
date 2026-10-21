"""Preferências pequenas, validadas e independentes da partida."""
from pathlib import Path
import json
import math
import pygame
from .config import SAVE_PATH
from .persistence import write_json

DEFAULT_BINDINGS = {
    "up": pygame.K_w, "down": pygame.K_s, "left": pygame.K_a, "right": pygame.K_d,
    "place": pygame.K_RETURN, "previous": pygame.K_q, "next": pygame.K_e,
    "remove": pygame.K_r, "wave": pygame.K_n, "pause": pygame.K_p,
}
ACTION_LABELS = {"up": "Mover acima", "down": "Mover abaixo", "left": "Mover à esquerda",
                 "right": "Mover à direita", "place": "Posicionar / remover",
                 "previous": "Carta anterior", "next": "Próxima carta", "remove": "Recolher tropa / voltar à base",
                 "wave": "Próxima onda", "pause": "Pausar / retomar"}
ALIASES = {"up": (pygame.K_UP,), "down": (pygame.K_DOWN,), "left": (pygame.K_LEFT,),
           "right": (pygame.K_RIGHT,), "place": (pygame.K_f, pygame.K_SPACE), "wave": (pygame.K_TAB,)}
RESERVED = {pygame.K_ESCAPE, pygame.K_F11, pygame.K_F5, pygame.K_F1, *range(pygame.K_1, pygame.K_8 + 1)}

class Settings:
    def __init__(self, campaign_path=None):
        path = Path(campaign_path) if campaign_path is not None else SAVE_PATH
        self.path = path.with_name(path.stem + ".settings.json")
        self.control_mode = "mouse"
        self.sound = True
        self.volume = .65
        self.music = 1.0
        self.ambience = 1.0
        self.effects = 1.0
        self.large_text = False
        self.auto_pause = True
        self.reduced_motion = False
        self.bindings = DEFAULT_BINDINGS.copy()
        self.player_name = ""
        try:
            with self.path.open("rb") as f:
                data = json.loads(f.read(16385))
            if type(data) is not dict or self.path.stat().st_size > 16384:
                return
            if data.get("version") != 1:
                return
            if data.get("control_mode") in ("mouse", "keyboard"):
                self.control_mode = data["control_mode"]
            player_name = data.get("player_name", "")
            if type(player_name) is str and len(player_name.strip()) <= 20 and player_name.strip().isprintable():
                self.player_name = player_name.strip()
            for name in ("sound", "large_text", "auto_pause", "reduced_motion"):
                if type(data.get(name)) is bool:
                    setattr(self, name, data[name])
            for name in ("volume", "music", "ambience", "effects"):
                value = data.get(name)
                if type(value) in (float, int) and math.isfinite(value):
                    setattr(self, name, min(1., max(0., value)))
            bindings = data.get("bindings")
            if (type(bindings) is dict and set(bindings) == set(DEFAULT_BINDINGS)
                    and len(set(bindings.values())) == len(bindings)
                    and all(type(k) is int and 0 < k < 2**31 and pygame.key.name(k) and k not in RESERVED
                            for k in bindings.values())):
                self.bindings = bindings
        except (OSError, ValueError, TypeError, RecursionError):
            pass

    def save(self):
        return write_json({"version": 1, **{k: v for k, v in vars(self).items() if k != "path"}}, self.path)

    def action(self, key):
        for action, assigned in self.bindings.items():
            if assigned == key:
                return action
        for action, aliases in ALIASES.items():
            if self.bindings[action] == DEFAULT_BINDINGS[action] and key in aliases:
                return action
        return None

    def assign(self, action, key):
        if (action not in DEFAULT_BINDINGS or type(key) is not int
                or not 0 < key < 2**31 or not pygame.key.name(key)):
            return False
        if key in RESERVED or key in (pygame.K_LALT, pygame.K_RALT,
                pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT):
            return False
        if key in (v for a, v in self.bindings.items() if a != action):
            return False
        self.bindings[action] = key
        return True

    def label(self, action):
        return pygame.key.name(self.bindings[action]).upper()

