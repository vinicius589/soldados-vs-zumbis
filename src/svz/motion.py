"""Estado temporal de animações e efeitos."""
from __future__ import annotations

from dataclasses import dataclass
import pygame



@dataclass
class ActorMotion:
    """Estado visual temporizado de uma unidade em campo.

    A referência técnica analisada separava os sprites em sequências de
    caminhada e ataque. Aqui o mesmo princípio é refeito sem depender de uma
    contagem fixa de arquivos ou de um frame mágico: a simulação informa um
    estado, o estado avança com ``dt`` e o desenho calcula a pose correspondente.
    Isso mantém combate e animação sincronizados inclusive quando a taxa de
    quadros varia.
    """

    state: str = "spawn"
    state_elapsed: float = 0.0
    event_left: float = 0.28
    hit_flash: float = 0.0

    def advance(self, dt: float, fallback: str) -> None:
        self.state_elapsed += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.event_left > 0:
            self.event_left = max(0.0, self.event_left - dt)
            if self.event_left > 0:
                return
        if self.state != fallback:
            self.state = fallback
            self.state_elapsed = 0.0

    def trigger(self, state: str, duration: float) -> None:
        """Inicia uma ação curta (tiro, golpe, habilidade ou impacto)."""
        if self.state != state:
            self.state = state
            self.state_elapsed = 0.0
            # Uma ação nova não deve herdar o tempo que restava de outra
            # pose (por exemplo, o nascer da unidade não pode alongar um
            # disparo que acabou de acontecer).
            self.event_left = max(0.0, duration)
            return
        self.event_left = max(self.event_left, max(0.0, duration))

    def loop(self, state: str) -> None:
        """Troca para um estado contínuo que deve prevalecer neste quadro."""
        if self.state != state:
            self.state = state
            self.state_elapsed = 0.0
        self.event_left = 0.0

    def flash(self, seconds: float = 0.13) -> None:
        self.hit_flash = max(self.hit_flash, seconds)

    def phase(self, fps: float = 8.0, frames: int = 4) -> int:
        """Índice estável de um ciclo visual, independente do FPS real."""
        return int(self.state_elapsed * fps) % max(1, frames)


@dataclass
class VisualEffect:
    """Efeito curto de impacto/atividade, separado da lógica do projétil."""

    kind: str
    x: float
    y: float
    color: tuple[int, int, int]
    duration: float = 0.34
    elapsed: float = 0.0
    scale: float = 1.0
    # Efeitos emitidos por uma habilidade acompanham o ator até o fim do
    # gesto. Impactos deixam ``owner`` vazio e permanecem no ponto atingido.
    owner: object | None = None
    anchor_kind: str = ""


@dataclass
class DefeatAnimation:
    """Mantém a silhueta por alguns quadros depois da morte lógica."""

    sprite: pygame.Surface
    x: float
    y: float
    width: float
    height: float
    water: bool = False
    duration: float = 0.48
    elapsed: float = 0.0
    enemy: bool = False
