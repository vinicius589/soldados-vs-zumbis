"""Infraestrutura genérica de animação 2D para projetos Pygame.

O módulo não conhece regras de jogo. Ele oferece apenas blocos reutilizáveis:

* :class:`SpriteSheet` para carregar e recortar folhas de sprites;
* :class:`AnimationClip` e :class:`AnimationManager` para animação por ``dt``;
* :class:`Entity` para associar estados a animações;
* :class:`Camera2D` para posição e screen shake temporal;
* :class:`Particle`, :class:`OneShotVFX` e :class:`VFXManager` para efeitos;
* :func:`apply_color_overlay` para feedback de dano ou seleção.

Todas as grandezas de tempo são expressas em segundos. O módulo nunca usa o
número de quadros renderizados para decidir a velocidade de uma animação.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pygame


Number = int | float
Point = tuple[Number, Number] | pygame.Vector2
Color = tuple[int, int, int] | tuple[int, int, int, int]


def _as_vector(value: Point) -> pygame.Vector2:
    """Retorna uma cópia de ``value`` como ``Vector2``."""
    return pygame.Vector2(float(value[0]), float(value[1]))


def _validate_dt(dt: float) -> float:
    """Normaliza um delta time e rejeita valores que esconderiam bugs."""
    value = float(dt)
    if not math.isfinite(value) or value < 0:
        raise ValueError("dt deve ser um número finito maior ou igual a zero")
    return value


def load_frames(
    paths: Iterable[str | Path],
    *,
    convert_alpha: bool = True,
    scale: tuple[int, int] | None = None,
) -> list[pygame.Surface]:
    """Carrega uma sequência ordenada de imagens.

    ``convert_alpha`` só é aplicado quando já existe uma superfície de vídeo,
    o que mantém a função utilizável em testes headless antes de ``set_mode``.
    ``scale`` usa ``smoothscale`` e não altera os arquivos originais.
    """
    frames: list[pygame.Surface] = []
    for raw_path in paths:
        path = Path(raw_path)
        image = pygame.image.load(str(path))
        if convert_alpha and pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        if scale is not None:
            if scale[0] <= 0 or scale[1] <= 0:
                raise ValueError("scale deve conter largura e altura positivas")
            image = pygame.transform.smoothscale(image, scale)
        frames.append(image)
    if not frames:
        raise ValueError("a lista de quadros não pode estar vazia")
    return frames


class SpriteSheet:
    """Fonte genérica para recortar uma folha de sprites regular ou irregular."""

    def __init__(self, surface: pygame.Surface) -> None:
        if surface.get_width() <= 0 or surface.get_height() <= 0:
            raise ValueError("a folha de sprites precisa ter dimensões positivas")
        self.surface = surface

    @classmethod
    def from_file(cls, path: str | Path, *, convert_alpha: bool = True) -> "SpriteSheet":
        """Carrega uma folha do disco sem exigir um formato de grade específico."""
        image = pygame.image.load(str(Path(path)))
        if convert_alpha and pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        return cls(image)

    def slice_grid(
        self,
        frame_size: tuple[int, int],
        *,
        columns: int | None = None,
        rows: int | None = None,
        margin: tuple[int, int] = (0, 0),
        spacing: tuple[int, int] = (0, 0),
        limit: int | None = None,
        scale: tuple[int, int] | None = None,
    ) -> list[pygame.Surface]:
        """Recorta quadros regulares em ordem de leitura.

        ``margin`` define o primeiro ponto útil. ``spacing`` é a distância
        entre células. Quando linhas ou colunas são omitidas, a quantidade é
        calculada a partir da área disponível. ``limit`` permite ignorar
        células vazias no final da folha.
        """
        frame_w, frame_h = frame_size
        margin_x, margin_y = margin
        spacing_x, spacing_y = spacing
        if frame_w <= 0 or frame_h <= 0:
            raise ValueError("frame_size deve conter valores positivos")
        if margin_x < 0 or margin_y < 0 or spacing_x < 0 or spacing_y < 0:
            raise ValueError("margin e spacing não podem ser negativos")

        available_w = self.surface.get_width() - margin_x
        available_h = self.surface.get_height() - margin_y
        inferred_columns = max(0, (available_w + spacing_x) // (frame_w + spacing_x))
        inferred_rows = max(0, (available_h + spacing_y) // (frame_h + spacing_y))
        columns = inferred_columns if columns is None else int(columns)
        rows = inferred_rows if rows is None else int(rows)
        if columns <= 0 or rows <= 0:
            raise ValueError("a grade calculada não contém quadros")

        frames: list[pygame.Surface] = []
        for row in range(rows):
            for column in range(columns):
                x = margin_x + column * (frame_w + spacing_x)
                y = margin_y + row * (frame_h + spacing_y)
                rect = pygame.Rect(x, y, frame_w, frame_h)
                if not self.surface.get_rect().contains(rect):
                    raise ValueError(f"quadro {column},{row} ultrapassa a folha: {rect}")
                frame = self.surface.subsurface(rect).copy()
                if scale is not None:
                    if scale[0] <= 0 or scale[1] <= 0:
                        raise ValueError("scale deve conter valores positivos")
                    frame = pygame.transform.smoothscale(frame, scale)
                frames.append(frame)
                if limit is not None and len(frames) >= limit:
                    return frames
        return frames

    def slice_rects(
        self,
        rects: Iterable[pygame.Rect | tuple[int, int, int, int]],
        *,
        scale: tuple[int, int] | None = None,
    ) -> list[pygame.Surface]:
        """Recorta quadros irregulares usando retângulos explícitos."""
        frames: list[pygame.Surface] = []
        for raw_rect in rects:
            rect = pygame.Rect(raw_rect)
            if rect.width <= 0 or rect.height <= 0:
                raise ValueError(f"retângulo inválido: {rect}")
            if not self.surface.get_rect().contains(rect):
                raise ValueError(f"retângulo fora da folha: {rect}")
            frame = self.surface.subsurface(rect).copy()
            if scale is not None:
                frame = pygame.transform.smoothscale(frame, scale)
            frames.append(frame)
        if not frames:
            raise ValueError("rects não pode estar vazio")
        return frames

    def slice_equal(
        self,
        columns: int,
        rows: int = 1,
        *,
        scale: tuple[int, int] | None = None,
    ) -> list[pygame.Surface]:
        """Divide toda a folha em células proporcionais.

        Diferentemente de :meth:`slice_grid`, esta função também aceita uma
        largura que não seja divisível exatamente pela quantidade de colunas.
        As fronteiras são calculadas como frações da dimensão total, evitando
        perder a última coluna por arredondamento.
        """
        columns, rows = int(columns), int(rows)
        if columns <= 0 or rows <= 0:
            raise ValueError("columns e rows devem ser positivos")
        width, height = self.surface.get_size()
        frames: list[pygame.Surface] = []
        for row in range(rows):
            top = row * height // rows
            bottom = (row + 1) * height // rows
            for column in range(columns):
                left = column * width // columns
                right = (column + 1) * width // columns
                frame = self.surface.subsurface((left, top, right - left, bottom - top)).copy()
                if scale is not None:
                    frame = pygame.transform.smoothscale(frame, scale)
                frames.append(frame)
        return frames


@dataclass(frozen=True, slots=True)
class AnimationClip:
    """Uma animação imutável com duração individual por quadro."""

    frames: tuple[pygame.Surface, ...]
    frame_durations: tuple[float, ...]
    loop: bool = True
    name: str = ""

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("AnimationClip precisa de pelo menos um quadro")
        if len(self.frames) != len(self.frame_durations):
            raise ValueError("cada quadro precisa de exatamente uma duração")
        if any(not math.isfinite(value) or value <= 0 for value in self.frame_durations):
            raise ValueError("as durações dos quadros devem ser finitas e positivas")

    @classmethod
    def uniform(
        cls,
        frames: Sequence[pygame.Surface],
        *,
        fps: float,
        loop: bool = True,
        name: str = "",
    ) -> "AnimationClip":
        """Cria um clipe com velocidade uniforme expressa em quadros/segundo."""
        fps = float(fps)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("fps deve ser finito e positivo")
        frame_tuple = tuple(frames)
        return cls(frame_tuple, (1.0 / fps,) * len(frame_tuple), loop, name)

    @classmethod
    def timed(
        cls,
        frames: Sequence[pygame.Surface],
        durations: Sequence[float],
        *,
        loop: bool = True,
        name: str = "",
    ) -> "AnimationClip":
        """Cria um clipe com timing desenhado quadro a quadro."""
        return cls(tuple(frames), tuple(float(value) for value in durations), loop, name)

    @property
    def duration(self) -> float:
        return sum(self.frame_durations)


class AnimationManager:
    """Máquina de reprodução que associa nomes de estado a clipes.

    A reprodução acumula segundos reais. Se um frame demora mais que o normal,
    o laço consome quantas durações forem necessárias; por isso a animação não
    fica lenta em um computador com FPS baixo.
    """

    def __init__(
        self,
        animations: Mapping[str, AnimationClip] | None = None,
        *,
        initial_state: str | None = None,
    ) -> None:
        self.animations: dict[str, AnimationClip] = dict(animations or {})
        self.state: str | None = None
        self.frame_index = 0
        self.frame_elapsed = 0.0
        self.finished = False
        self.paused = False
        self.playback_rate = 1.0
        self.loop_count = 0
        if initial_state is not None:
            self.play(initial_state)
        elif self.animations:
            self.play(next(iter(self.animations)))

    def add(self, state: str, clip: AnimationClip, *, replace: bool = False) -> None:
        """Registra um estado; substituição exige autorização explícita."""
        if not state:
            raise ValueError("o nome do estado não pode ser vazio")
        if state in self.animations and not replace:
            raise KeyError(f"o estado {state!r} já existe")
        self.animations[state] = clip

    @property
    def clip(self) -> AnimationClip:
        if self.state is None:
            raise RuntimeError("nenhuma animação está ativa")
        return self.animations[self.state]

    @property
    def frame(self) -> pygame.Surface:
        """Quadro atual, pronto para ser transformado ou desenhado."""
        return self.clip.frames[self.frame_index]

    @property
    def normalized_progress(self) -> float:
        """Progresso temporal do ciclo atual entre 0 e 1."""
        clip = self.clip
        elapsed_before = sum(clip.frame_durations[: self.frame_index])
        progress = (elapsed_before + self.frame_elapsed) / clip.duration
        return max(0.0, min(1.0, progress))

    def play(self, state: str, *, restart: bool = False) -> bool:
        """Transiciona para ``state`` e reinicia corretamente o primeiro quadro.

        Retorna ``True`` quando houve transição ou reinício. Pedir novamente o
        estado atual não provoca saltos, a menos que ``restart=True``.
        """
        if state not in self.animations:
            available = ", ".join(sorted(self.animations)) or "nenhum"
            raise KeyError(f"estado {state!r} inexistente; disponíveis: {available}")
        if self.state == state and not restart:
            return False
        self.state = state
        self.frame_index = 0
        self.frame_elapsed = 0.0
        self.finished = False
        self.loop_count = 0
        return True

    def restart(self) -> None:
        if self.state is None:
            raise RuntimeError("não há estado para reiniciar")
        self.play(self.state, restart=True)

    def seek_frame(self, frame_index: int) -> None:
        """Vai diretamente a um quadro, útil para depuração e editores."""
        if self.state is None:
            raise RuntimeError("não há animação ativa")
        index = int(frame_index)
        if not 0 <= index < len(self.clip.frames):
            raise IndexError(f"quadro {index} fora do intervalo 0..{len(self.clip.frames) - 1}")
        self.frame_index = index
        self.frame_elapsed = 0.0
        self.finished = not self.clip.loop and index == len(self.clip.frames) - 1

    def step(self, amount: int = 1) -> int:
        """Avança manualmente quadros sem usar relógio, para inspeção pausada."""
        if self.state is None:
            raise RuntimeError("não há animação ativa")
        count = len(self.clip.frames)
        target = self.frame_index + int(amount)
        if self.clip.loop:
            target %= count
        else:
            target = max(0, min(count - 1, target))
        self.seek_frame(target)
        return self.frame_index

    def update(self, dt: float) -> None:
        """Avança a animação usando apenas tempo real acumulado."""
        dt = _validate_dt(dt)
        if self.state is None or self.paused or self.finished or dt == 0:
            return
        rate = float(self.playback_rate)
        if not math.isfinite(rate) or rate < 0:
            raise ValueError("playback_rate deve ser finito e não negativo")
        remaining = dt * rate
        if remaining == 0:
            return

        clip = self.clip
        self.frame_elapsed += remaining
        while self.frame_elapsed >= clip.frame_durations[self.frame_index]:
            self.frame_elapsed -= clip.frame_durations[self.frame_index]
            if self.frame_index + 1 < len(clip.frames):
                self.frame_index += 1
                continue
            if clip.loop:
                self.frame_index = 0
                self.loop_count += 1
                continue
            self.frame_index = len(clip.frames) - 1
            self.frame_elapsed = 0.0
            self.finished = True
            break


def apply_color_overlay(
    source: pygame.Surface,
    color: Color = (255, 64, 64),
    strength: float = 0.65,
) -> pygame.Surface:
    """Cria uma cópia do sprite com um overlay colorido preservando o alfa."""
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0:
        return source.copy()
    rgb = tuple(int(max(0, min(255, channel))) for channel in color[:3])
    tinted = source.copy()
    multiplier = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    multiplier.fill((*rgb, 255))
    tinted.blit(multiplier, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    tinted.set_alpha(round(255 * strength))

    result = source.copy()
    result.blit(tinted, (0, 0))
    return result


class Entity(pygame.sprite.Sprite):
    """Entidade visual genérica controlada por uma máquina de estados."""

    VALID_ANCHORS: Final = frozenset(
        {"topleft", "topright", "bottomleft", "bottomright", "center", "midtop", "midbottom", "midleft", "midright"}
    )

    def __init__(
        self,
        animations: Mapping[str, AnimationClip],
        *,
        initial_state: str,
        position: Point = (0, 0),
        anchor: str = "midbottom",
        auto_kill_state: str | None = "destroy",
    ) -> None:
        super().__init__()
        if anchor not in self.VALID_ANCHORS:
            raise ValueError(f"âncora inválida: {anchor}")
        self.animation = AnimationManager(animations, initial_state=initial_state)
        self.position = _as_vector(position)
        self.velocity = pygame.Vector2()
        self.anchor = anchor
        self.auto_kill_state = auto_kill_state
        self.flip_x = False
        self.flip_y = False
        self.angle = 0.0
        self.scale = 1.0
        self.visible = True
        self._flash_color: Color = (255, 64, 64)
        self._flash_strength = 0.0
        self._flash_remaining = 0.0
        self._flash_duration = 0.0
        self.image = self.animation.frame
        self.rect = self._anchored_rect(self.image)

    @property
    def state(self) -> str:
        assert self.animation.state is not None
        return self.animation.state

    def set_state(self, state: str, *, restart: bool = False) -> bool:
        """Troca o estado; estados novos sempre começam no quadro zero."""
        return self.animation.play(state, restart=restart)

    def flash(
        self,
        *,
        color: Color = (255, 64, 64),
        duration: float = 0.12,
        strength: float = 0.70,
    ) -> None:
        """Ativa um feedback temporário, normalmente usado ao receber dano."""
        duration = float(duration)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration deve ser finita e positiva")
        self._flash_color = color
        self._flash_duration = duration
        self._flash_remaining = duration
        self._flash_strength = max(0.0, min(1.0, float(strength)))

    @property
    def flash_active(self) -> bool:
        return self._flash_remaining > 0

    def _anchored_rect(self, image: pygame.Surface) -> pygame.Rect:
        rect = image.get_rect()
        setattr(rect, self.anchor, (round(self.position.x), round(self.position.y)))
        return rect

    def _render_image(self) -> pygame.Surface:
        image = self.animation.frame
        if self.flip_x or self.flip_y:
            image = pygame.transform.flip(image, self.flip_x, self.flip_y)
        if self.angle or self.scale != 1.0:
            image = pygame.transform.rotozoom(image, self.angle, self.scale)
        if self.flash_active:
            falloff = self._flash_remaining / max(0.0001, self._flash_duration)
            image = apply_color_overlay(image, self._flash_color, self._flash_strength * falloff)
        return image

    def update(self, dt: float) -> None:
        dt = _validate_dt(dt)
        self.position += self.velocity * dt
        self.animation.update(dt)
        self._flash_remaining = max(0.0, self._flash_remaining - dt)
        self.image = self._render_image()
        self.rect = self._anchored_rect(self.image)
        if self.auto_kill_state == self.state and self.animation.finished:
            self.kill()

    def draw(self, target: pygame.Surface, camera: "Camera2D | None" = None) -> pygame.Rect | None:
        """Desenha a entidade respeitando âncora e deslocamento da câmera."""
        if not self.visible:
            return None
        position = self.position if camera is None else camera.world_to_screen(self.position)
        rect = self.image.get_rect()
        setattr(rect, self.anchor, (round(position.x), round(position.y)))
        target.blit(self.image, rect)
        return rect


class Camera2D:
    """Câmera 2D com tremor temporal suave e independente de FPS."""

    def __init__(self, position: Point = (0, 0)) -> None:
        self.position = _as_vector(position)
        self.shake_offset = pygame.Vector2()
        self._shake_elapsed = 0.0
        self._shake_duration = 0.0
        self._shake_amplitude = 0.0
        self._shake_frequency = 28.0
        self._shake_seed = 0.0

    @property
    def shaking(self) -> bool:
        return self._shake_elapsed < self._shake_duration

    def trigger_shake(
        self,
        amplitude: float,
        duration: float,
        *,
        frequency: float = 28.0,
        additive: bool = False,
    ) -> None:
        """Inicia um tremor; por padrão, o impacto mais forte substitui o atual."""
        amplitude = float(amplitude)
        duration = float(duration)
        frequency = float(frequency)
        if amplitude < 0 or duration <= 0 or frequency <= 0:
            raise ValueError("amplitude >= 0, duration > 0 e frequency > 0 são obrigatórios")
        if not all(math.isfinite(value) for value in (amplitude, duration, frequency)):
            raise ValueError("parâmetros de shake devem ser finitos")

        if additive and self.shaking:
            self._shake_amplitude += amplitude
            self._shake_duration = max(self._shake_duration, self._shake_elapsed + duration)
        else:
            self._shake_amplitude = max(amplitude, self._shake_amplitude if self.shaking else 0.0)
            self._shake_duration = max(duration, self._shake_duration - self._shake_elapsed if self.shaking else 0.0)
            self._shake_elapsed = 0.0
        self._shake_frequency = frequency
        self._shake_seed = (self._shake_seed + 1.61803398875) % math.tau

    def update(self, dt: float) -> None:
        dt = _validate_dt(dt)
        if not self.shaking:
            self.shake_offset.update(0, 0)
            return
        self._shake_elapsed = min(self._shake_duration, self._shake_elapsed + dt)
        progress = self._shake_elapsed / self._shake_duration
        envelope = (1.0 - progress) ** 2
        phase = self._shake_elapsed * self._shake_frequency * math.tau
        self.shake_offset.x = math.sin(phase * 1.07 + self._shake_seed) * self._shake_amplitude * envelope
        self.shake_offset.y = math.sin(phase * 1.31 + self._shake_seed * 1.7) * self._shake_amplitude * 0.72 * envelope
        if not self.shaking:
            self.shake_offset.update(0, 0)

    def world_to_screen(self, world_position: Point) -> pygame.Vector2:
        """Converte coordenadas de mundo para tela, já incluindo o shake."""
        return _as_vector(world_position) - self.position + self.shake_offset

    def apply_screen_shake(
        self,
        source: pygame.Surface,
        destination: pygame.Surface,
        *,
        clear_color: Color = (0, 0, 0),
    ) -> None:
        """Aplica o tremor a uma cena pronta, inclusive HUD quando desejado."""
        destination.fill(clear_color)
        destination.blit(source, (round(self.shake_offset.x), round(self.shake_offset.y)))


class OneShotVFX(pygame.sprite.Sprite):
    """Animação de uso único que se remove ao reproduzir o último quadro."""

    def __init__(
        self,
        clip: AnimationClip,
        position: Point,
        *,
        anchor: str = "center",
        follow: Entity | None = None,
        offset: Point = (0, 0),
    ) -> None:
        super().__init__()
        if clip.loop:
            raise ValueError("OneShotVFX exige um AnimationClip com loop=False")
        if anchor not in Entity.VALID_ANCHORS:
            raise ValueError(f"âncora inválida: {anchor}")
        self.animation = AnimationManager({"play": clip}, initial_state="play")
        self.position = _as_vector(position)
        self.anchor = anchor
        self.follow = follow
        self.offset = _as_vector(offset)
        self.image = self.animation.frame
        self.rect = self.image.get_rect()

    @property
    def finished(self) -> bool:
        return self.animation.finished

    def update(self, dt: float) -> None:
        if self.follow is not None:
            self.position = self.follow.position + self.offset
        self.animation.update(dt)
        self.image = self.animation.frame
        self.rect = self.image.get_rect()
        setattr(self.rect, self.anchor, (round(self.position.x), round(self.position.y)))
        if self.animation.finished:
            self.kill()

    def draw(self, target: pygame.Surface, camera: Camera2D | None = None) -> pygame.Rect:
        position = self.position if camera is None else camera.world_to_screen(self.position)
        rect = self.image.get_rect()
        setattr(rect, self.anchor, (round(position.x), round(position.y)))
        target.blit(self.image, rect)
        return rect


class Particle:
    """Partícula baseada em imagem, com física e interpolação temporal simples."""

    def __init__(
        self,
        image: pygame.Surface,
        position: Point,
        *,
        velocity: Point = (0, 0),
        acceleration: Point = (0, 0),
        lifetime: float = 0.5,
        start_scale: float = 1.0,
        end_scale: float = 1.0,
        start_alpha: int = 255,
        end_alpha: int = 0,
        angle: float = 0.0,
        angular_velocity: float = 0.0,
        anchor: str = "center",
    ) -> None:
        lifetime = float(lifetime)
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise ValueError("lifetime deve ser finito e positivo")
        if start_scale <= 0 or end_scale <= 0:
            raise ValueError("as escalas devem ser positivas")
        if anchor not in Entity.VALID_ANCHORS:
            raise ValueError(f"âncora inválida: {anchor}")
        self.source = image
        self.position = _as_vector(position)
        self.velocity = _as_vector(velocity)
        self.acceleration = _as_vector(acceleration)
        self.lifetime = lifetime
        self.age = 0.0
        self.start_scale = float(start_scale)
        self.end_scale = float(end_scale)
        self.start_alpha = int(max(0, min(255, start_alpha)))
        self.end_alpha = int(max(0, min(255, end_alpha)))
        self.angle = float(angle)
        self.angular_velocity = float(angular_velocity)
        self.anchor = anchor
        self.alive = True

    @property
    def progress(self) -> float:
        return max(0.0, min(1.0, self.age / self.lifetime))

    def update(self, dt: float) -> None:
        dt = _validate_dt(dt)
        if not self.alive:
            return
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.angle += self.angular_velocity * dt
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False

    def draw(self, target: pygame.Surface, camera: Camera2D | None = None) -> pygame.Rect | None:
        if not self.alive:
            return None
        t = self.progress
        scale = self.start_scale + (self.end_scale - self.start_scale) * t
        alpha = round(self.start_alpha + (self.end_alpha - self.start_alpha) * t)
        image = pygame.transform.rotozoom(self.source, self.angle, scale)
        image.set_alpha(alpha)
        position = self.position if camera is None else camera.world_to_screen(self.position)
        rect = image.get_rect()
        setattr(rect, self.anchor, (round(position.x), round(position.y)))
        target.blit(image, rect)
        return rect


class VFXManager:
    """Contêiner independente para efeitos animados e partículas temporárias."""

    def __init__(self) -> None:
        self.animations: list[OneShotVFX] = []
        self.particles: list[Particle] = []

    def spawn_animation(
        self,
        clip: AnimationClip,
        position: Point,
        **kwargs: object,
    ) -> OneShotVFX:
        effect = OneShotVFX(clip, position, **kwargs)
        self.animations.append(effect)
        return effect

    def emit(self, particle: Particle) -> Particle:
        self.particles.append(particle)
        return particle

    def update(self, dt: float) -> None:
        dt = _validate_dt(dt)
        for effect in self.animations[:]:
            effect.update(dt)
            if effect.finished:
                self.animations.remove(effect)
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.alive:
                self.particles.remove(particle)

    def draw(self, target: pygame.Surface, camera: Camera2D | None = None) -> None:
        for particle in self.particles:
            particle.draw(target, camera)
        for effect in self.animations:
            effect.draw(target, camera)

    def clear(self) -> None:
        self.animations.clear()
        self.particles.clear()


def _demo_actor_frames(color: tuple[int, int, int], count: int, action: str) -> list[pygame.Surface]:
    """Gera quadros simples apenas para a demonstração sem ativos externos."""
    frames: list[pygame.Surface] = []
    for index in range(count):
        frame = pygame.Surface((96, 112), pygame.SRCALPHA)
        phase = index / max(1, count - 1)
        bob = round(abs(math.sin(phase * math.tau)) * 3) if action == "move" else 0
        lean = round(math.sin(phase * math.pi) * 8) if action == "action" else 0
        fade = 1.0 - phase if action == "destroy" else 1.0
        body = pygame.Rect(30 + lean, 34 + bob, 36, 46)
        pygame.draw.rect(frame, (*color, round(255 * fade)), body, border_radius=8)
        pygame.draw.circle(frame, (225, 207, 181, round(255 * fade)), (48 + lean, 23 + bob), 13)
        stride = round(math.sin(phase * math.tau) * 11) if action == "move" else 0
        pygame.draw.line(frame, (*color, round(255 * fade)), (42 + lean, 78 + bob), (38 - stride, 106), 8)
        pygame.draw.line(frame, (*color, round(255 * fade)), (56 + lean, 78 + bob), (60 + stride, 106), 8)
        pygame.draw.line(frame, (*color, round(255 * fade)), (34 + lean, 49 + bob), (17 + lean, 64 - stride // 3), 7)
        pygame.draw.line(frame, (*color, round(255 * fade)), (62 + lean, 49 + bob), (82 + lean, 58 + stride // 3), 7)
        frames.append(frame)
    return frames


def _demo_vfx_frames() -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    for index in range(6):
        frame = pygame.Surface((96, 96), pygame.SRCALPHA)
        radius = 8 + index * 7
        alpha = max(0, 230 - index * 36)
        pygame.draw.circle(frame, (255, 202, 90, alpha), (48, 48), radius, max(2, 9 - index))
        frames.append(frame)
    return frames


def run_demo() -> None:
    """Demonstra estados, ``dt``, flash, shake, VFX e partículas.

    Controles: setas movimentam, Espaço executa ação, clique aplica dano e
    tremor, D toca ``destroy`` e R reinicia a entidade.
    """
    pygame.init()
    screen = pygame.display.set_mode((900, 520))
    pygame.display.set_caption("animation2d.py — demonstração genérica")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    animations = {
        "idle": AnimationClip.uniform(_demo_actor_frames((70, 145, 220), 4, "idle"), fps=5),
        "move": AnimationClip.uniform(_demo_actor_frames((70, 145, 220), 8, "move"), fps=12),
        "action": AnimationClip.uniform(_demo_actor_frames((238, 169, 62), 6, "action"), fps=14, loop=False),
        "destroy": AnimationClip.uniform(_demo_actor_frames((180, 65, 65), 7, "destroy"), fps=11, loop=False),
    }
    vfx_clip = AnimationClip.uniform(_demo_vfx_frames(), fps=18, loop=False, name="impact")
    particle_image = pygame.Surface((8, 8), pygame.SRCALPHA)
    pygame.draw.polygon(particle_image, (255, 214, 112), ((4, 0), (8, 8), (0, 8)))

    def create_entity() -> Entity:
        return Entity(animations, initial_state="idle", position=(450, 365))

    entity = create_entity()
    camera = Camera2D()
    vfx = VFXManager()
    running = True
    while running:
        # A única origem de tempo do exemplo. Nenhum contador depende do FPS.
        dt = min(clock.tick(144) / 1000.0, 0.1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and entity.state != "destroy":
                    entity.set_state("action", restart=True)
                elif event.key == pygame.K_d:
                    entity.velocity.update(0, 0)
                    entity.set_state("destroy", restart=True)
                elif event.key == pygame.K_r:
                    entity = create_entity()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                entity.flash()
                camera.trigger_shake(11, 0.32)
                vfx.spawn_animation(vfx_clip, entity.position + pygame.Vector2(42, -50))
                for direction in range(8):
                    angle = direction * math.tau / 8
                    velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * 85
                    vfx.emit(
                        Particle(
                            particle_image,
                            entity.position + pygame.Vector2(42, -50),
                            velocity=velocity,
                            acceleration=(0, 95),
                            lifetime=0.42,
                            end_scale=0.35,
                            angular_velocity=220,
                        )
                    )

        keys = pygame.key.get_pressed()
        direction = float(keys[pygame.K_RIGHT]) - float(keys[pygame.K_LEFT])
        if entity.state not in {"action", "destroy"}:
            entity.velocity.x = direction * 170
            entity.flip_x = direction < 0
            entity.set_state("move" if direction else "idle")
        else:
            entity.velocity.x = 0
            if entity.state == "action" and entity.animation.finished:
                entity.set_state("idle")

        entity.update(dt)
        camera.update(dt)
        vfx.update(dt)

        screen.fill((18, 23, 31))
        pygame.draw.line(screen, (80, 92, 102), (0, 366), (900, 366), 2)
        entity.draw(screen, camera)
        vfx.draw(screen, camera)
        lines = (
            "SETAS: mover | ESPAÇO: ação | CLIQUE: dano + shake + VFX",
            "D: destruir | R: reiniciar | ESC: sair",
            f"estado={entity.state} quadro={entity.animation.frame_index} dt={dt:.4f}s",
        )
        for index, text in enumerate(lines):
            screen.blit(font.render(text, True, (225, 232, 238)), (22, 20 + index * 26))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_demo()
