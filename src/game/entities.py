"""Entidades e objetos de combate do jogo."""
from __future__ import annotations

from src.game.runtime import *  # noqa: F403

@dataclass
class Defender:
    key: str
    display_name: str
    row: int
    col: int
    stats: dict
    sprite_index: int
    hp: float = field(init=False)
    ammo: int = field(init=False)
    attack_timer: float = 0.0
    utility_timer: float = 0.0
    reload_timer: float = 0.0
    reload_total: float = 0.0
    stun: float = 0.0
    corrosion: float = 0.0
    ascended: float = 0.0
    drone_timer: float = 0.0
    turret_timer: float = 0.0
    pulse: float = 0.0
    region: str = "city"
    motion: ActorMotion = field(default_factory=ActorMotion)
    visual_animation: AnimationManager | None = field(default=None, repr=False)
    deployment_x: float | None = None
    deployment_target_x: float | None = None
    deployment_speed: float = 260.0

    def __post_init__(self) -> None:
        self.hp = float(self.stats["hp"])
        self.ammo = int(self.stats["ammo"])
        if self.stats["role"] in {"promoter", "radio", "sonar"}:
            self.utility_timer = float(self.stats["cooldown"])

    @property
    def x(self) -> float:
        return cell_center(self.row, self.col, self.region)[0]

    @property
    def y(self) -> float:
        return cell_center(self.row, self.col, self.region)[1]

    @property
    def max_hp(self) -> float:
        return float(self.stats["hp"])

    @property
    def max_ammo(self) -> int:
        return int(self.stats["ammo"])

    def has_ammo(self) -> bool:
        return self.max_ammo == 0 or self.ammo > 0

    @property
    def reloading(self) -> bool:
        return self.max_ammo > 0 and self.ammo <= 0 and self.reload_timer > 0

    def hitbox(self) -> pygame.Rect:
        width, height = defender_render_scale(self)
        return pygame.Rect(
            int(self.x - width / 2), int(self.y - height), int(width), int(height + 12)
        )

    @property
    def deployed(self) -> bool:
        return self.deployment_x is None

    @property
    def render_x(self) -> float:
        return self.x if self.deployment_x is None else self.deployment_x

@dataclass
class Enemy:
    key: str
    row: int
    data: dict
    region: str
    wave: int
    difficulty: str = "medium"
    x: float = field(default_factory=lambda: BOARD.right + 100)
    hp: float = field(init=False)
    attack_timer: float = 0.0
    attack_windup: float = 0.0
    attack_target: Defender | None = None
    attack_damage: float = 0.0
    first_attack_done: bool = False
    skill_timer: float = 1.8
    age: float = 0.0
    stun: float = 0.0
    burn: float = 0.0
    poisoned: float = 0.0
    soaked: float = 0.0
    corrosion: float = 0.0
    quarantine_mark: float = 0.0
    defense_broken: float = 0.0
    jump_used: bool = False
    burrowed: bool = False
    jump_state: str = ""
    jump_timer: float = 0.0
    jump_duration: float = 0.0
    jump_start_x: float = 0.0
    jump_end_x: float = 0.0
    dig_used: bool = False
    dig_state: str = ""
    dig_timer: float = 0.0
    dig_duration: float = 0.0
    dig_start_x: float = 0.0
    dig_end_x: float = 0.0
    stolen: float = 0.0
    revived: bool = False
    rage: float = 0.0
    boss_announced: bool = False
    step_timer: float = 0.0
    dot_timer: float = 0.0
    motion: ActorMotion = field(default_factory=ActorMotion)
    visual_animation: AnimationManager | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        profile = difficulty_profile(self.difficulty)
        scale = (
            boss_wave_scale(self.wave)
            if self.key in BOSSES
            else enemy_wave_scale(self.wave)
        )
        scale *= float(profile["boss_hp" if self.key in BOSSES else "enemy_hp"])
        self.hp = float(self.data["hp"]) * scale

    @property
    def y(self) -> float:
        return terrain_y(self.region, self.row, self.x)

    @property
    def max_hp(self) -> float:
        profile = difficulty_profile(self.difficulty)
        scale = (
            boss_wave_scale(self.wave) if self.is_boss else enemy_wave_scale(self.wave)
        )
        scale *= float(profile["boss_hp" if self.is_boss else "enemy_hp"])
        return float(self.data["hp"]) * scale

    @property
    def is_boss(self) -> bool:
        return self.key in BOSSES

    @property
    def tags(self) -> tuple:
        return tuple(self.data.get("tags", ()))

    def hitbox(self) -> pygame.Rect:
        width, height = enemy_render_scale(self, self.region)
        return pygame.Rect(
            int(self.x - width / 2), int(self.y - height), int(width), int(height + 10)
        )

@dataclass
class Projectile:
    x: float
    y: float
    target: Enemy | Defender | None
    target_x: float
    target_y: float
    damage: float
    kind: str
    owner: Defender | Enemy | None
    radius: float = 0.0
    friendly: bool = True
    travel: float = 0.22
    elapsed: float = 0.0
    effect: str = ""

    def __post_init__(self) -> None:
        # Protege o loop de animação contra chamadas antigas que passaram o
        # efeito como último argumento posicional (onde elapsed ficava string).
        if isinstance(self.elapsed, str):
            if not self.effect:
                self.effect = self.elapsed
            self.elapsed = 0.0
        self.elapsed = float(self.elapsed)
        self.travel = max(0.01, float(self.travel))
        gap = PROJECTILE_LAUNCH_GAPS.get(self.kind, 0.0)
        if gap > 0 and isinstance(self.owner, (Defender, Enemy)):
            direction = 1.0 if isinstance(self.owner, Defender) else -1.0
            depth = lane_depth(self.owner.region, self.owner.row)
            # A origem lógica continua sendo a borda correta do equipamento.
            # Só a munição visível começa depois do clarão, sem ficar metade
            # enterrada no cano. Fluxos contínuos não possuem gap.
            self.x += direction * gap * depth

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    ttl: float
    size: float
    color: tuple[int, int, int]
    gravity: float = 0.0

@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    ttl: float = 1.0

@dataclass
class SpawnOrder:
    wait: float
    key: str
    row: int
    boss: bool = False

@dataclass
class LaneBomb:
    """Carrinho-bomba de emergência, um por faixa de combate."""

    row: int
    x: float = field(default_factory=lambda: float(LANE_BOMB_HOME_X))
    state: str = "armed"  # armed -> rolling -> spent
    kills: int = 0
    motion: ActorMotion = field(default_factory=ActorMotion)
