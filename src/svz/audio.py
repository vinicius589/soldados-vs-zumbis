"""Carregamento e reprodução de áudio."""
from __future__ import annotations

import pygame

from .config import (
    AUDIO_DIR,
)
from .math_utils import (
    clamp,
)


class AudioSystem:
    """Pacote sonoro original, físico e sincronizado com a ação.

    Os antigos bipes procedurais foram removidos. Armas, recarga, mordida,
    criaturas e cenários agora usam arquivos WAV próprios gerados para o
    projeto. A ausência de um dispositivo de áudio continua sem derrubar o
    jogo ou os testes headless.
    """

    SAMPLE_RATE = 44_100

    FILES: dict[str, tuple[str, float]] = {
        "ui": ("ui_click.wav", 0.54),
        "place": ("place.wav", 0.70),
        "shot": ("shot_pistol.wav", 0.72),
        "shot_pistol": ("shot_pistol.wav", 0.72),
        "shot_rifle": ("shot_rifle.wav", 0.74),
        "heavy_shot": ("shot_heavy.wav", 0.78),
        "shot_heavy": ("shot_heavy.wav", 0.78),
        "reload": ("reload.wav", 0.58),
        "explosion": ("explosion.wav", 0.86),
        "zombie_groan": ("zombie_groan.wav", 0.52),
        "zombie_hit": ("zombie_hit.wav", 0.55),
        "soldier_hit": ("soldier_hit.wav", 0.56),
        "bite": ("bite.wav", 0.66),
        "supply": ("supply.wav", 0.48),
        "wave": ("wave.wav", 0.62),
        "boss": ("boss.wav", 0.74),
        "ability": ("zombie_skill.wav", 0.62),
        "zombie_skill": ("zombie_skill.wav", 0.62),
        "whistle": ("whistle.wav", 0.52),
        "alarm_scream": ("alarm_scream.wav", 0.52),
        "thunder": ("thunder.wav", 0.68),
        "music_menu": ("music_menu.wav", 0.24),
        "ambience_city": ("ambience_city.wav", 0.28),
        "ambience_desert": ("ambience_desert.wav", 0.30),
        "ambience_beach": ("ambience_beach.wav", 0.32),
        # Compatibilidade com verificações antigas: agora aponta para a cidade,
        # mas a reprodução real escolhe o ambiente da região ativa.
        "ambience": ("ambience_city.wav", 0.28),
    }

    def __init__(self) -> None:
        self.enabled = True
        self.volume = 0.65
        self.ready = False
        self.error = ""
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.base_volumes: dict[str, float] = {}
        self.last_played: dict[str, int] = {}
        self.music_channel: pygame.mixer.Channel | None = None
        self.ambience_channel: pygame.mixer.Channel | None = None
        self.current_ambience: str | None = None
        self.music_started = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=self.SAMPLE_RATE,
                    size=-16,
                    channels=2,
                    buffer=512,
                )
            self.ready = True
            self._load_library()
            self.set_volume(self.volume)
            self.music_channel = pygame.mixer.Channel(6)
            self.ambience_channel = pygame.mixer.Channel(7)
            self.music_channel.play(self.sounds["music_menu"], loops=-1, fade_ms=600)
            self.music_started = True
        except (pygame.error, OSError, ValueError) as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.ready = False

    def _load_library(self) -> None:
        for name, (filename, base_volume) in self.FILES.items():
            path = AUDIO_DIR / filename
            if not path.exists():
                raise OSError(f"arquivo sonoro ausente: {path.name}")
            self.sounds[name] = pygame.mixer.Sound(str(path))
            self.base_volumes[name] = base_volume

    def set_volume(self, value: float) -> None:
        self.volume = clamp(float(value), 0.0, 1.0)
        for name, sound in self.sounds.items():
            sound.set_volume(self.base_volumes.get(name, 0.3) * self.volume)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.ready:
            return
        if self.enabled:
            if self.music_channel is not None and not self.music_channel.get_busy():
                self.music_channel.play(self.sounds["music_menu"], loops=-1, fade_ms=350)
                self.music_started = True
        else:
            pygame.mixer.stop()
            self.current_ambience = None
            self.music_started = False

    def sync(self, scene: str, region: str | None = None) -> None:
        """Mantém música e paisagem sonora coerentes com a tela atual."""
        if not self.ready or not self.enabled:
            return
        if self.music_channel is not None and not self.music_channel.get_busy():
            self.music_channel.play(self.sounds["music_menu"], loops=-1, fade_ms=450)
        wanted = f"ambience_{region}" if scene == "battle" and region else None
        if wanted == self.current_ambience:
            return
        if self.ambience_channel is not None:
            self.ambience_channel.fadeout(300)
        self.current_ambience = wanted if wanted in self.sounds else None
        if self.current_ambience and self.ambience_channel is not None:
            self.ambience_channel.play(
                self.sounds[self.current_ambience], loops=-1, fade_ms=450
            )

    def play(self, name: str, *, min_interval_ms: int = 0) -> None:
        if not self.ready or not self.enabled or name not in self.sounds:
            return
        now = pygame.time.get_ticks()
        if now - self.last_played.get(name, -100000) < min_interval_ms:
            return
        self.last_played[name] = now
        self.sounds[name].play()
