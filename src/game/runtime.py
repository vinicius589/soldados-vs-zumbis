"""Soldados vs Zumbis — Beta 4.

Um tower defense original em Pygame. A Beta 4 preserva campanha, cartas,
munição com recarga própria, chefes, Núcleos de Ascensão e elencos temáticos por
região, mas introduz um sistema próprio de animação orientado por estados.
Nenhum código ou arte externa é incorporado: cada estado é atualizado por
tempo real e renderizado a partir dos recursos originais do projeto.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from src.engine.animation2d import AnimationManager
from src.engine.asset_paths import game_root
from src.engine.opengl_presenter import ActorCommand, OpenGLPresenter
from src.game.beta4_expansion_roster import EXPANSION_DEFENDERS
from src.game.beta4_production_animations import (
    build_production_clips,
    new_production_animation,
)
from src.game.beta4_scenario_runtime import ScenarioRuntime
from src.game.visual_layout import (
    DEFENDER_WEAPON_PROFILES,
    ENEMY_ATTACK_ORIGINS,
    ENEMY_BODY_LAYOUTS,
    PROJECTILE_LAUNCH_GAPS,
    PROJECTILE_LAYOUTS,
    defender_layout,
)

ROOT = game_root()
ASSET_DIR = ROOT / "assets" / "v7"
PRODUCTION_ASSET_DIR = ROOT / "assets" / "beta4_producao"
AUDIO_DIR = ROOT / "assets" / "audio_beta4"
if getattr(sys, "frozen", False):
    if os.name == "nt":
        user_data = (
            Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SoldadosVsZumbis"
        )
    elif sys.platform == "darwin":
        user_data = Path.home() / "Library" / "Application Support" / "SoldadosVsZumbis"
    else:
        user_data = (
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            / "SoldadosVsZumbis"
        )
    SAVE_PATH = user_data / "campanha_v7.json"
else:
    SAVE_PATH = ROOT / "campanha_v7.json"
WIDTH, HEIGHT = 1280, 720
FPS = 60
VERSION = "BETA 4"
TOTAL_WAVES = 12
CARD_RECHARGE_SECONDS = 10.0
ROWS, COLS = 4, 9
# A arte comporta a contenção inicial e seis casas de tropa. As colunas 7 e 8
# coincidiam com o fim pintado da pista e com a boca de entrada dos zumbis;
# elas deixam de existir para clique, teclado, ocupação e footprint.
LAST_PLACEABLE_COLUMN = 6
# Limite horizontal comum e extensão vertical total das três arenas. As
# faixas não usam uma grade vertical genérica: cada cenário possui limites
# calibrados a partir das pistas realmente pintadas na arte.
BOARD = pygame.Rect(164, 170, 1090, 540)
CELL_W = BOARD.width / COLS
CELL_H = BOARD.height / ROWS
LANE_BOUNDS: dict[str, tuple[int, int, int, int, int]] = {
    # Limites medidos diretamente nas três artes finais. A posição lógica não
    # tenta mais encaixar uma grade genérica sobre pistas desenhadas em alturas
    # diferentes; por isso soldados, zumbis e contenções compartilham o mesmo
    # chão visível em cada região.
    "city": (239, 326, 428, 514, 619),
    "desert": (226, 316, 410, 503, 604),
    "beach": (207, 285, 383, 480, 585),
}
BEACH_WATER_ROWS = frozenset({1, 2})
BEACH_WATER_DEFENDERS = frozenset(
    {"lancha", "submarino", "barco_patrulha", "submarino_tatico"}
)
LANE_BOMB_HOME_X = 215
# A contenção inicial ocupa a primeira casa de cada faixa. Manter a coluna
# explícita evita depender de uma função declarada mais abaixo no módulo.
LANE_PROTECTION_COLUMN = 0
LANE_PROTECTION_END_X = {
    "city": 1082,
    "desert": 1040,
    "beach": 1088,
}
# Ponto visual dentro de cada entrada da direita. O primeiro quadro nasce
# encoberto pela passagem e ganha opacidade enquanto avança para a pista.
ENEMY_ENTRY_X = {
    "city": 1182.0,
    "desert": 1168.0,
    "beach": 1190.0,
}
ENEMY_ENTRY_REVEAL_SECONDS = 0.55
WHITE = (242, 244, 239)
INK = (15, 20, 25)
GOLD = (240, 187, 72)
RED = (218, 68, 57)
TEAL = (72, 198, 192)
GRAY = (148, 160, 166)


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
                self.music_channel.play(
                    self.sounds["music_menu"], loops=-1, fade_ms=350
                )
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


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


RUNNER_HIT_SECONDS = 0.42
ZOMBIE_HIT_SECONDS = 0.52
SOLDIER_HIT_SECONDS = 0.45


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
    hit_recovery_left: float = 0.0

    def advance(self, dt: float, fallback: str) -> None:
        self.state_elapsed += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.hit_recovery_left = max(0.0, self.hit_recovery_left - dt)
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

    def react_to_hit(self, duration: float, recovery: float) -> bool:
        """Exibe um impacto por ciclo, sem travar no último quadro sob rajadas.

        Novos danos ainda reduzem HP e piscam, mas não prolongam a mesma pose
        sem fim. O intervalo reserva uma passagem visível pela locomoção antes
        de outra reação corporal.
        """
        if self.hit_recovery_left > 0:
            return False
        duration = max(0.01, float(duration))
        self.trigger("hit", duration)
        self.hit_recovery_left = duration + max(0.0, float(recovery))
        return True

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


def enemy_wave_scale(wave: int) -> float:
    """Mantém as primeiras ondas acolhedoras e endurece a reta final.

    A versão anterior começava com vida cheia e liberava ameaças depressa;
    assim, o primeiro contato parecia mais duro que a metade da campanha.
    """
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.66 + 1.50 * progress**1.55


def enemy_damage_scale(wave: int) -> float:
    """Escala separada para que o fim não seja só uma esponja de vida."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.62 + 1.10 * progress**1.50


def boss_wave_scale(wave: int) -> float:
    """Chefes escalam com a campanha sem virar paredes de vida.

    Um chefe deve mudar a montagem da linha, não exigir uma composição
    perfeita ou prender o jogador numa sequência infinita de atordoamentos.
    Por isso sua vida cresce mais devagar que a de uma horda comum.
    """
    # Chefes mantêm sua identidade, mas precisam cair com uma montagem boa
    # antes que a contenção de última linha vire o único plano viável.
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.78 + 1.25 * progress**1.40


def boss_damage_scale(wave: int) -> float:
    """Contém o dano físico dos chefes nas ondas altas."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.70 + 0.95 * progress**1.45


def lane_bounds(region: str, row: int) -> tuple[float, float]:
    """Limites reais da faixa desenhada no cenário selecionado."""
    bounds = LANE_BOUNDS.get(region, LANE_BOUNDS["city"])
    index = int(clamp(row, 0, ROWS - 1))
    return float(bounds[index]), float(bounds[index + 1])


def terrain_y(region: str, row: int, x: float) -> float:
    """Retorna a linha de contato dos pés, rodas ou casco com o terreno.

    ``x`` permanece na assinatura porque inimigos móveis consultam esta
    função a cada quadro. As rotas desta versão são horizontais: assim um
    zumbi nunca deriva verticalmente nem abandona a linha em que nasceu.
    """
    top, bottom = lane_bounds(region, row)
    # O contato fica no centro óptico da pista. Como o corpo cresce para cima,
    # 60% deixa a silhueta visualmente centrada sem apoiar o pé na mureta de
    # cima nem na borda de pedra/asfalto de baixo.
    return lerp(top, bottom, 0.60)


def lane_depth(region: str, row: int) -> float:
    """Escala de perspectiva: faixas distantes menores, frente maior."""
    first = terrain_y(region, 0, BOARD.left)
    last = terrain_y(region, ROWS - 1, BOARD.left)
    position = terrain_y(region, row, BOARD.left)
    progress = 0.0 if last == first else (position - first) / (last - first)
    # O novo litoral foi pintado com projeção quase ortográfica; nele uma
    # variação extrema fazia a primeira faixa parecer miniatura e a última,
    # gigante. Cidade e Deserto preservam a perspectiva mais profunda.
    # A primeira faixa fica logo abaixo da aba superior: 0,58 também garante
    # que cabeça/arma não sejam cortadas pelo HUD. Na frente, 0,96 evita o
    # efeito de gigante observado no cenário costeiro anterior.
    rear, front = (0.86, 0.98) if region == "beach" else (0.84, 1.0)
    return lerp(rear, front, clamp(progress, 0.0, 1.0))


def cell_center(row: int, col: int, region: str = "city") -> tuple[float, float]:
    x = BOARD.left + (col + 0.5) * CELL_W
    return x, terrain_y(region, row, x)


def lane_bomb_home_x(region: str, row: int) -> float:
    """Corrige opticamente a contenção sem deslocar as demais faixas."""
    return float(LANE_BOMB_HOME_X)


def lane_bomb_ground_y(region: str, row: int) -> float:
    """Centraliza visualmente a contenção dentro da faixa transitável.

    Personagens usam o contato dos pés no terço inferior. Uma bomba apoiada
    nesse mesmo ponto, porém, cai sobre a borda de pedras. A contenção fica no
    centro óptico da pista, mantendo terra, água e sprite no mesmo eixo.
    """
    top, bottom = lane_bounds(region, row)
    return lerp(top, bottom, 0.60)


def cell_rect(row: int, col: int, region: str = "city") -> pygame.Rect:
    top, bottom = lane_bounds(region, row)
    return pygame.Rect(
        int(BOARD.left + col * CELL_W),
        int(top),
        int(CELL_W),
        int(bottom - top),
    )


def title_case(value: str) -> str:
    return value.replace("_", " ").title()


REGIONS = {
    "city": {
        "name": "Nova York — Terminal Félix",
        "short": "NOVA YORK",
        "tag": "Contaminação urbana",
        "bg": "city_beta4_integrated_v4.png",
        "soldiers": "city_soldiers_atlas.png",
        "soldiers_l2": "city_soldiers_l2_atlas_v74.png",
        "zombies": "city_zombies_atlas.png",
        "accent": (90, 207, 166),
        "unlock_after": None,
        "description": "Uma avenida de quarentena com quatro pistas largas de asfalto, base de emergência e ruínas tóxicas nas bordas.",
        # Chefes voltam quando suas novas folhas forem aprovadas.
        "bosses": (),
    },
    "desert": {
        "name": "Egito — Escavação Félix",
        "short": "EGITO",
        "tag": "Necrópole contaminada",
        "bg": "desert_beta4_integrated_v4.png",
        "soldiers": "desert_soldiers_atlas.png",
        "soldiers_l2": "desert_soldiers_l2_atlas_v74.png",
        "zombies": "desert_zombies_atlas.png",
        "accent": (235, 179, 76),
        "unlock_after": "city",
        "description": "Quatro trilhas largas de areia compactada cruzam uma expedição militar rumo às ruínas e pirâmides antigas.",
        "bosses": (),
    },
    "beach": {
        "name": "Minas Gerais — Cachoeira Contaminada",
        "short": "CACHOEIRA",
        "tag": "Água contaminada",
        "bg": "beach_beta4_integrated_v6.png",
        "soldiers": "beach_soldiers_beta4_rebuilt.png",
        "soldiers_l2": "beach_soldiers_l2_beta4_rebuilt.png",
        "zombies": "beach_zombies_beta4_rebuilt.png",
        "accent": (78, 177, 232),
        "unlock_after": "desert",
        "description": "Duas trilhas terrestres e dois canais contaminados defendem a base diante da cachoeira de Minas Gerais.",
        "bosses": (),
    },
}


# Catálogo legado preservado somente como dados internos. A produção ativa
# abaixo expõe um único protótipo novo por mapa, sem níveis ou promoções.
DEFENSES = {
    "xerife_rua": {
        "base": "Xerife de Rua",
        "role": "rifle",
        "level": 1,
        "cost": 42,
        "hp": 100,
        "damage": 22,
        "range": 2,
        "cooldown": 0.82,
        "ammo": 7,
        "reload": 2.0,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Desert Eagle de serviço. Alcance de dois blocos, recarga ágil e linha de tiro limpa: não dispara através de outra defesa.",
    },
    "pistoleiro_deserto": {
        "base": "Pistoleiro do Deserto",
        "role": "rifle",
        "level": 1,
        "cost": 44,
        "hp": 102,
        "damage": 26,
        "range": 2,
        "cooldown": 0.94,
        "ammo": 6,
        "reload": 2.2,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Magnum .357. Alcance de dois blocos, tiro pesado, recarga ágil e linha de tiro limpa: não dispara através de outra defesa.",
    },
    "marinheiro": {
        "base": "Marinheiro",
        "role": "rifle",
        "level": 1,
        "cost": 42,
        "hp": 101,
        "damage": 14,
        "range": 2,
        "cooldown": 0.68,
        "ammo": 15,
        "reload": 1.8,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Glock 19 de serviço. Alcance de dois blocos, recarga ágil e linha de tiro limpa. É uma tropa terrestre; os canais ficam reservados a barco e submarino.",
    },
    "agente_swat": {
        "base": "Agente Tático da SWAT",
        "role": "rifle",
        "level": 1,
        "cost": 72,
        "hp": 108,
        "damage": 8,
        "range": 3,
        "cooldown": 0.34,
        "ammo": 30,
        "reload": 3.4,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "MP5 automática. Dispara depressa por três blocos e pode cobrir aliados à frente; o pente maior cobra uma recarga mais longa.",
    },
    "fuzileiro_deserto": {
        "base": "Fuzileiro do Deserto",
        "role": "rifle",
        "level": 1,
        "cost": 78,
        "hp": 110,
        "damage": 15,
        "range": 3,
        "cooldown": 0.46,
        "ammo": 24,
        "reload": 3.7,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "SCAR preparada para areia. Rajadas precisas por três blocos atravessam a formação aliada; a arma pesada demora mais para recarregar.",
    },
    "fuzileiro_marinha": {
        "base": "Fuzileiro da Marinha",
        "role": "rifle",
        "level": 1,
        "cost": 74,
        "hp": 109,
        "damage": 12,
        "range": 3,
        "cooldown": 0.39,
        "ammo": 30,
        "reload": 3.6,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "M16 naval. Mantém fogo rápido por três blocos e cobre quem está à frente; uniforme e equipamento são próprios da Marinha do Brasil.",
    },
    "operador_radio_policial": {
        "base": "Operador de Rádio Policial",
        "role": "radio",
        "level": 1,
        "cost": 58,
        "hp": 94,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Aciona a central pelo rádio portátil e entrega exatamente 12 suprimentos a cada 12 segundos. Não ataca e precisa ser protegido.",
    },
    "torre_radio_egito": {
        "base": "Torre de Rádio do Egito",
        "role": "radio",
        "level": 1,
        "cost": 72,
        "hp": 165,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Retransmissor militar fixo da escavação Khepra. Gera exatamente 12 suprimentos a cada 12 segundos e resiste mais que os operadores humanos.",
    },
    "estacao_comunicacao_cachoeira": {
        "base": "Estação Móvel da Cachoeira",
        "role": "radio",
        "level": 1,
        "cost": 68,
        "hp": 150,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Maleta-relé impermeável da Defesa Civil e da Marinha. Abre antenas e libera exatamente 12 suprimentos a cada 12 segundos; não é um personagem reciclado.",
    },
    "recruta": {
        "base": "Recruta",
        "role": "rifle",
        "level": 1,
        "cost": 45,
        "hp": 92,
        "damage": 11,
        "range": 2,
        "cooldown": 1.05,
        "ammo": 10,
        "sprite": 0,
        "ability": "Pistola: tiro cadenciado em até 2 blocos. Dez tiros derrubam um Caminhante.",
    },
    "soldado": {
        "base": "Soldado",
        "role": "rifle",
        "level": 2,
        "cost": 95,
        "hp": 128,
        "damage": 20,
        "range": 4,
        "cooldown": 0.60,
        "ammo": 18,
        "sprite": 1,
        "ability": "M16: quatro blocos de alcance e fogo sustentado. Ao esvaziar, executa uma recarga própria temporizada.",
    },
    "escopeteiro": {
        "base": "Espingarda de Mão",
        "role": "shotgun",
        "level": 1,
        "cost": 55,
        "hp": 122,
        "damage": 43,
        "range": 1,
        "cooldown": 1.10,
        "ammo": 2,
        "sprite": 3,
        "ability": "Dois cartuchos e alcance curto. Quanto mais perto, mais pellets acertam.",
    },
    "escopeteiro_regular": {
        "base": "Escopeteiro Regular",
        "role": "shotgun",
        "level": 2,
        "cost": 105,
        "hp": 150,
        "damage": 52,
        "range": 3,
        "cooldown": 0.95,
        "ammo": 5,
        "sprite": 3,
        "ability": "Espingarda regular de três blocos; segura os corredores antes da linha.",
    },
    "sniper": {
        "base": "Atirador de Vigia",
        "role": "sniper",
        "level": 1,
        "cost": 75,
        "hp": 82,
        "damage": 58,
        "range": 9,
        "cooldown": 2.10,
        "ammo": 5,
        "sprite": 4,
        "ability": "Mira instável: pode errar. Dano alto, sem execução instantânea.",
    },
    "sniper_regular": {
        "base": "Sniper Regular",
        "role": "sniper",
        "level": 2,
        "cost": 135,
        "hp": 95,
        "damage": 88,
        "range": 9,
        "cooldown": 1.85,
        "ammo": 6,
        "sprite": 4,
        "ability": "Mira garantida e dano alto; ainda não é um hit-kill.",
    },
    "bombardeiro": {
        "base": "Bombardeiro",
        "role": "grenade",
        "level": 1,
        "cost": 100,
        "hp": 112,
        "damage": 70,
        "range": 2,
        "cooldown": 2.25,
        "ammo": 3,
        "sprite": 5,
        "ability": "Granada curta em área. A explosão pode ferir aliados próximos.",
    },
    "granadeiro": {
        "base": "Granadeiro",
        "role": "grenade",
        "level": 2,
        "cost": 150,
        "hp": 124,
        "damage": 88,
        "range": 4,
        "cooldown": 1.75,
        "ammo": 5,
        "sprite": 5,
        "ability": "Lançador de granadas de quatro blocos; controla grupos, mas gasta muita munição.",
    },
    "morteiro": {
        "base": "Morteiro de Campo",
        "role": "mortar",
        "level": 2,
        "cost": 165,
        "hp": 105,
        "damage": 105,
        "range": 3,
        "cooldown": 2.30,
        "ammo": 4,
        "sprite": 5,
        "ability": "Bomba de arco com área ampla. Não mira o primeiro bloco da própria posição.",
    },
    "lanca_chamas": {
        "base": "Lança-Chamas",
        "role": "flame",
        "level": 2,
        "cost": 128,
        "hp": 144,
        "damage": 20,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Exclusivo do Deserto. Cone de fogo reforçado até três blocos; aplica Queimadura contínua.",
    },
    "lanca_chamas_bolso": {
        "base": "Lança-Chamas de Mão",
        "role": "flame",
        "level": 1,
        "cost": 78,
        "hp": 108,
        "damage": 14,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Exclusivo do Deserto. Jato de fogo curto de um bloco; causa dano maior e aplica Queimadura.",
    },
    "lancador_veneno": {
        "base": "Lançador de Veneno",
        "role": "poison",
        "level": 1,
        "cost": 82,
        "hp": 110,
        "damage": 12,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Exclusivo da Cidade. Pulveriza veneno a um bloco e aplica Envenenado: dano contínuo e avanço 12% menor.",
    },
    "canhao_veneno": {
        "base": "Canhão de Veneno",
        "role": "poison",
        "level": 2,
        "cost": 132,
        "hp": 146,
        "damage": 18,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Exclusivo da Cidade. Nuvem tóxica em área até três blocos; mantém grupos Envenenados e mais lentos.",
    },
    "lancador_agua": {
        "base": "Lançador de Água",
        "role": "waterjet",
        "level": 1,
        "cost": 78,
        "hp": 108,
        "damage": 9,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Jato de água curto e pressurizado. Encharca o alvo, apaga queima e reduz o avanço por alguns segundos.",
    },
    "canhao_mare": {
        "base": "Canhão de Maré",
        "role": "waterjet",
        "level": 2,
        "cost": 128,
        "hp": 144,
        "damage": 12,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Canhão de água de três blocos. Pulveriza pequenos grupos, apaga fogo e reduz a velocidade dos encharcados.",
    },
    "morteiro_basico": {
        "base": "Morteiro de Uma Bomba",
        "role": "mortar",
        "level": 1,
        "cost": 82,
        "hp": 88,
        "damage": 66,
        "range": 2,
        "cooldown": 4.35,
        "ammo": 1,
        "sprite": 5,
        "ability": "Lança uma única bomba em área e recarrega muito devagar. É o estágio inicial do morteiro.",
    },
    "radio": {
        "base": "Operador de Rádio",
        "role": "radio",
        "level": 1,
        "cost": 72,
        "hp": 90,
        "damage": 0,
        "range": 0,
        "cooldown": 7.00,
        "ammo": 0,
        "sprite": 7,
        "ability": "Pede suprimento à base: pouca quantidade e entrega lenta. É barato de manter.",
    },
    "torre_radio": {
        "base": "Torre de Rádio",
        "role": "radio",
        "level": 2,
        "cost": 128,
        "hp": 118,
        "damage": 0,
        "range": 0,
        "cooldown": 4.80,
        "ammo": 0,
        "sprite": 7,
        "ability": "Sinal reforçado: suprimento e ritmo médios, sem travar a economia no início.",
    },
    "barreira": {
        "base": "Barreira de Contenção",
        "role": "barrier",
        "level": 1,
        "cost": 58,
        "hp": 360,
        "damage": 0,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 10,
        "ability": "Veículo estático com muita vida para atrasar a horda. Não possui armas.",
    },
    "barreira_reativa": {
        "base": "Barreira Reativa",
        "role": "barrier",
        "level": 2,
        "cost": 104,
        "hp": 470,
        "damage": 70,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 10,
        "ability": "Ao ser destruída, explode e atinge inimigos adjacentes. Continua sem arma.",
    },
    "mina": {
        "base": "Mina de Pressão",
        "role": "mine",
        "level": 1,
        "cost": 42,
        "hp": 1,
        "damage": 105,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "ability": "Elimina um alvo, mas possui chance de falha. Um Núcleo transforma-a em limpeza de linha.",
    },
    "mina_segura": {
        "base": "Mina Segura",
        "role": "mine",
        "level": 2,
        "cost": 74,
        "hp": 1,
        "damage": 150,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "ability": "Disparo garantido contra um único invasor. Reage quando ele pisa na célula.",
    },
    "lancha": {
        "base": "Lancha Patrulha",
        "role": "boat",
        "level": 2,
        "cost": 125,
        "hp": 275,
        "damage": 38,
        "range": 4,
        "cooldown": 0.70,
        "ammo": 16,
        "sprite": 5,
        "water_only": True,
        "ability": "Carta marítima exclusiva da Praia; só pode ser posicionada nas faixas de água do canal.",
    },
    "atirador_lancha": {
        "base": "Atirador de Lancha",
        "role": "boat",
        "level": 1,
        "cost": 78,
        "hp": 158,
        "damage": 22,
        "range": 3,
        "cooldown": 0.86,
        "ammo": 10,
        "sprite": 5,
        "water_only": True,
        "ability": "Barquinho leve com rifle: cobre até três blocos do canal. Tem dez disparos e evolui para a Lancha Patrulha.",
    },
    "submarino": {
        "base": "Submarino",
        "role": "sub",
        "level": 2,
        "cost": 175,
        "hp": 235,
        "damage": 90,
        "range": 6,
        "cooldown": 1.80,
        "ammo": 6,
        "sprite": 6,
        "water_only": True,
        "ability": "Torpedos de grande alcance. Carta marítima exclusiva da Praia: fica indisponível em solo seco.",
    },
    "bomba_agua": {
        "base": "Bomba de Água",
        "role": "mine",
        "level": 2,
        "cost": 80,
        "hp": 1,
        "damage": 190,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "water_only": True,
        "ability": "Mina marítima segura: só pode ficar submersa e explode em pequenos grupos.",
    },
    "instrutor": {
        "base": "Sargento de Promoção",
        "role": "promoter",
        "level": 2,
        "cost": 135,
        "hp": 120,
        "damage": 0,
        "range": 3,
        "cooldown": 90.0,
        "ammo": 0,
        "sprite": 2,
        "ability": "Personagem legado fora da produção atual.",
    },
}


# Os quatro novos soldados de cada região agora fazem parte da Beta 4 ativa.
# O registro de produção continua sendo a fonte de balanceamento, mas o jogo
# completa aqui os campos comuns usados por seleção, combate e dossiê.
_EXPANSION_COMBAT_CLASS = {
    "sniper": 2,
    "shotgun": 2,
    "poison": 2,
    "gas_grenade": 2,
    "rocket": 3,
    "heavy": 3,
    "flame": 2,
    "mortar": 3,
    "waterjet": 2,
    "grenade": 3,
    "suicide_bomber": 3,
    "shield": 2,
    "blade": 2,
    "sonar": 2,
    "boat": 2,
    "sub": 3,
}
for _region_entries in EXPANSION_DEFENDERS.values():
    for _key, _source in _region_entries.items():
        _data = dict(_source)
        _data["base"] = _data.pop("name")
        _data.setdefault("level", 1)
        _data.setdefault("sprite", 0)
        _data.setdefault("combat_class", _EXPANSION_COMBAT_CLASS[_data["role"]])
        _data.setdefault(
            "shoot_through_allies",
            _data["role"]
            not in {
                "shotgun",
                "flame",
                "waterjet",
                "suicide_bomber",
                "shield",
                "blade",
            },
        )
        _data.setdefault("footprint", 1)
        DEFENSES[_key] = _data


# Tempo de troca de carregador/cano por família de arma. A recarga automática
# só começa depois da última pose de disparo e deixa a unidade sem atacar. O
# intervalo intencional de 8 a 15 segundos substitui por completo a antiga
# dependência de Mecânico/Engenheiro de munição.
WEAPON_RELOAD_SECONDS: dict[str, tuple[float, float]] = {
    "rifle": (9.0, 8.0),
    "shotgun": (11.5, 9.5),
    "sniper": (13.0, 11.0),
    "grenade": (13.5, 11.5),
    "mortar": (15.0, 13.0),
    "flame": (10.5, 9.0),
    "poison": (10.5, 9.0),
    "gas_grenade": (12.0, 10.5),
    "waterjet": (10.0, 8.5),
    "boat": (10.5, 9.0),
    "sub": (14.5, 13.0),
}


def weapon_reload_seconds(stats: dict, ascended: bool = False) -> float:
    """Retorna a recarga da ficha atual, preservando o catálogo legado."""
    if "reload" in stats and int(stats.get("ammo", 0)) > 0:
        seconds = max(0.1, float(stats["reload"]))
        return seconds * (0.82 if ascended else 1.0)
    role = str(stats.get("role", ""))
    level = 2 if int(stats.get("level", 1)) >= 2 else 1
    pair = WEAPON_RELOAD_SECONDS.get(role)
    if pair is None or int(stats.get("ammo", 0)) <= 0:
        return 0.0
    seconds = pair[level - 1]
    if ascended:
        seconds = max(8.0, seconds * 0.82)
    return float(clamp(seconds, 8.0, 15.0))


# O sistema de evolução foi desligado integralmente nesta reconstrução.
PROMOTIONS: dict[str, str] = {}


# Cada degrau de dificuldade cresce na mesma direção: menos economia para o
# jogador, mais vida/dano/densidade para os infectados e intervalos menores.
# Assim não existe mais o caso antigo em que o Fácil tinha inimigos mais fortes
# que o Médio e compensava isso apenas despejando suprimentos no início.
DIFFICULTIES = {
    "easy": {
        "label": "FÁCIL",
        "levels": (2,),
        "initial_supplies": 320,
        "enemy_hp": 0.76,
        "enemy_damage": 0.66,
        "boss_hp": 0.80,
        "boss_damage": 0.70,
        "spawn_count": 0.78,
        "spawn_wait": 1.28,
        "escort_count": 0.70,
        "skill_cooldown": 1.28,
        "defender_damage": 1.18,
        "supply_gain": 1.40,
        "supply_cycle": 0.74,
        "supply_cap": 650,
        "accent": (112, 212, 139),
        "summary": "320 SUP e começo acolhedor; a pressão cresce de forma contínua até a onda 12.",
    },
    "medium": {
        "label": "MÉDIO",
        "levels": (1, 2),
        "initial_supplies": 240,
        "enemy_hp": 1.00,
        "enemy_damage": 1.00,
        "boss_hp": 1.00,
        "boss_damage": 0.98,
        "spawn_count": 1.00,
        "spawn_wait": 1.00,
        "escort_count": 1.00,
        "skill_cooldown": 1.00,
        "defender_damage": 1.00,
        "supply_gain": 1.00,
        "supply_cycle": 1.00,
        "supply_cap": 430,
        "accent": GOLD,
        "summary": "240 SUP; início ensinável, meio exigente e reta final de alta pressão.",
    },
    "hard": {
        "label": "DIFÍCIL",
        "levels": (1,),
        "initial_supplies": 190,
        "enemy_hp": 1.20,
        "enemy_damage": 1.20,
        "boss_hp": 1.25,
        "boss_damage": 1.20,
        "spawn_count": 1.18,
        "spawn_wait": 0.88,
        "escort_count": 1.20,
        "skill_cooldown": 0.82,
        "defender_damage": 0.94,
        "supply_gain": 0.86,
        "supply_cycle": 1.12,
        "supply_cap": 330,
        "accent": RED,
        "summary": "190 SUP; dá para montar a defesa inicial, mas a onda 12 exige counters e economia.",
    },
}


def difficulty_profile(key: str) -> dict:
    """Retorna sempre um modo válido, inclusive em salvamentos antigos."""
    return DIFFICULTIES.get(key, DIFFICULTIES["medium"])


REGION_ROSTERS = {
    "city": (
        ("xerife_rua", "Xerife de Rua"),
        ("agente_swat", "Agente Tático da SWAT"),
        ("operador_radio_policial", "Operador de Rádio Policial"),
        ("atirador_precisao_swat", "Atirador de Precisão"),
        ("agente_entrada", "Agente de Entrada"),
        ("especialista_antipraga", "Especialista Antipraga"),
        ("lancador_foguetes", "Lançador de Foguetes"),
        ("escudeiro_tropa_choque", "Escudeiro da Tropa de Choque"),
    ),
    "desert": (
        ("pistoleiro_deserto", "Pistoleiro do Deserto"),
        ("fuzileiro_deserto", "Fuzileiro do Deserto"),
        ("torre_radio_egito", "Torre de Rádio do Egito"),
        ("atirador_horizonte", "Atirador do Horizonte"),
        ("tenente_artilheiro", "Tenente Artilheiro"),
        ("incinerador_deserto", "Incinerador do Deserto"),
        ("nomade_morteiro", "Nômade do Morteiro"),
        ("guardiao_laminas", "Guardião de Lâminas"),
    ),
    "beach": (
        ("marinheiro", "Marinheiro"),
        ("fuzileiro_marinha", "Fuzileiro da Marinha"),
        ("estacao_comunicacao_cachoeira", "Estação Móvel da Cachoeira"),
        ("atirador_precisao_marinha", "Atirador de Precisão Naval"),
        ("bombeiro_hidraulico", "Bombeiro Hidráulico"),
        ("granadeiro_profundidades", "Granadeiro das Profundidades"),
        ("barco_patrulha", "Barco de Patrulha"),
        ("submarino_tatico", "Submarino Tático"),
    ),
}


# Cada carta ativa possui uma identidade narrativa e, principalmente, uma
# razão mecânica própria para existir. O carrossel usa esta fonte única; assim
# a seleção não promete uma função que o combate desconhece.
CARD_DETAILS = {
    "xerife_rua": {
        "lore": "Primeiro policial a isolar o Terminal Félix-13, manteve as ruas abertas com uma arma curta e decisões rápidas.",
        "function": "Patrulha econômica de dois blocos, tiro forte e recarga curta.",
        "need": "É a resposta barata para segurar as primeiras linhas sem consumir a economia das cartas pesadas.",
    },
    "agente_swat": {
        "lore": "Agente da equipe de contenção de Nova York, treinado para sustentar corredores estreitos sob pressão contínua.",
        "function": "Supressão rápida a três blocos, atravessando a formação aliada.",
        "need": "Mantém Corredores sob fogo sem bloquear a própria linha; troca potência por cadência.",
    },
    "operador_radio_policial": {
        "lore": "Ligação móvel entre as patrulhas isoladas e o depósito de emergência da cidade.",
        "function": "Geração periódica de suprimentos, sem capacidade ofensiva.",
        "need": "Sustenta formações caras nas ondas longas; sem ele a reserva acaba antes dos chefes.",
    },
    "atirador_precisao_swat": {
        "lore": "Observador da SWAT posicionado nos telhados que ainda não cederam à contaminação.",
        "function": "Perfuração de armadura e eliminação prioritária de alvos resistentes.",
        "need": "O tiro de precisão contorna imunidade a munição convencional de coletes infectados.",
    },
    "agente_entrada": {
        "lore": "Especialista de entrada da Tropa de Choque, acostumado a romper portas e formações compactas.",
        "function": "Escopeta de impacto a curta distância e quebra de guarda.",
        "need": "Com o Escudeiro, é a única doutrina capaz de abrir a defesa dos Brutos urbanos.",
    },
    "especialista_antipraga": {
        "lore": "Pesquisador de campo que converteu reagentes confiscados da Félix em composto anticontaminação.",
        "function": "Granadas de gás venenoso e reagente anticorrosivo que abrem uma nuvem química em área.",
        "need": "Remove a blindagem biológica do Policial Infectado, imune a balas comuns enquanto protegido.",
    },
    "lancador_foguetes": {
        "lore": "Operador pesado chamado quando veículos e estruturas da quarentena viraram cobertura para a horda.",
        "function": "Demolição estrutural em área, lenta e de alto impacto.",
        "need": "Quebra alvos estruturais; inimigos anti-explosão impedem que seja uma solução universal.",
    },
    "escudeiro_tropa_choque": {
        "lore": "Vanguarda da Tropa de Choque, responsável por receber a primeira colisão e manter o corredor aberto.",
        "function": "Bloqueio corpo a corpo e ruptura de investidas pesadas.",
        "need": "Neutraliza a guarda dos Brutos e impede que a primeira carga atravesse soldados frágeis.",
    },
    "pistoleiro_deserto": {
        "lore": "Batedor egípcio da escavação Khepra, habituado a conservar munição durante patrulhas no deserto.",
        "function": "Magnum de dois blocos, tiro forte e recarga curta.",
        "need": "Interrompe conjurações menores sem consumir o grande pente das tropas automáticas.",
    },
    "fuzileiro_deserto": {
        "lore": "Fuzileiro das forças egípcias adaptado à areia e aos corredores estreitos das ruínas.",
        "function": "Rajada de três blocos que cobre aliados posicionados à frente.",
        "need": "Suprime enxames de múmias e protege as unidades de counter enquanto trabalham.",
    },
    "torre_radio_egito": {
        "lore": "Retransmissor blindado erguido quando as paredes da necrópole bloquearam o contato com o comando.",
        "function": "Economia resistente e estável, porém fixa e sem ataque.",
        "need": "Financia armamento pesado no deserto sem expor um operador humano às maldições.",
    },
    "atirador_horizonte": {
        "lore": "Vigia de longo alcance que identifica o núcleo luminoso por trás das faixas contaminadas.",
        "function": "Precisão contra curandeiros e hospedeiros protegidos.",
        "need": "Perfura núcleos que ignoram balas convencionais e impede a recuperação da horda.",
    },
    "tenente_artilheiro": {
        "lore": "Oficial que manteve a metralhadora da expedição funcionando depois da queda do comboio.",
        "function": "Fixação de subchefes por fogo pesado contínuo.",
        "need": "Mantém Mutantes sob supressão para que counters corpo a corpo consigam alcançá-los.",
    },
    "incinerador_deserto": {
        "lore": "Especialista criado após a equipe descobrir que as faixas funerárias continuavam se regenerando.",
        "function": "Dano térmico contínuo e bloqueio de regeneração.",
        "need": "É a resposta direta às múmias regenerativas e aos Curandeiros da necrópole.",
    },
    "nomade_morteiro": {
        "lore": "Artilheiro móvel que calcula disparos por cima das dunas e das colunas destruídas.",
        "function": "Bombardeio indireto contra concentrações e inimigos entrincheirados.",
        "need": "Atinge ameaças enterradas, mas a resistência explosiva dos elites exige apoio especializado.",
    },
    "guardiao_laminas": {
        "lore": "Duelista da guarda de Khepra que estudou o ritmo das lâminas reanimadas dentro da pirâmide.",
        "function": "Aparo corpo a corpo e desarme de inimigos laminados.",
        "need": "Única unidade que rompe a guarda do Zumbi de Lâmina; sem ela o alvo rejeita tiro e explosão.",
    },
    "marinheiro": {
        "lore": "Marinheiro da base mineira que organizou a primeira defesa terrestre após a água mudar de cor.",
        "function": "Pistola de dois blocos, econômica e de recarga rápida.",
        "need": "Segura as margens com baixo consumo e libera recursos para a defesa cara dos canais.",
    },
    "fuzileiro_marinha": {
        "lore": "Fuzileiro naval destacado para impedir que a infestação suba da cachoeira até as cidades próximas.",
        "function": "Cobertura automática terrestre de três blocos.",
        "need": "Protege operadores aquáticos e derruba corredores antes que alcancem a margem.",
    },
    "estacao_comunicacao_cachoeira": {
        "lore": "Estação móvel construída com rádio naval e sensores locais, sem reciclar equipamento de Nova York ou do Egito.",
        "function": "Geração de suprimentos para a força brasileira.",
        "need": "Mantém Barco e Submarino operacionais; ambos têm custo incompatível com uma economia sem suporte.",
    },
    "atirador_precisao_marinha": {
        "lore": "Observador naval treinado para enxergar cilindros, válvulas e pontos fracos sob a água turva.",
        "function": "Perfuração precisa contra mergulhadores e criaturas infladas.",
        "need": "Acerta componentes que munição convencional espalhada não consegue atravessar.",
    },
    "bombeiro_hidraulico": {
        "lore": "Bombeiro de resgate que transformou a bomba de alta pressão em ferramenta de descontaminação.",
        "function": "Jato hidráulico que desacelera e remove cobertura tóxica.",
        "need": "Lava a proteção química dos infectados e cria tempo para as armas terrestres finalizarem o alvo.",
    },
    "granadeiro_profundidades": {
        "lore": "Granadeiro naval equipado para lançar cargas sobre pedras e curvas do canal.",
        "function": "Controle explosivo de grupos na água e nas margens.",
        "need": "Interrompe enxames aquáticos, mas elites resistentes a explosão exigem Sonar ou precisão.",
    },
    "homem_bomba": {
        "lore": "Voluntário da contenção que permanece imóvel junto à carga para impedir uma ruptura inevitável da linha.",
        "function": "Armadilha humana fixa com detonação instantânea por contato.",
        "need": "Último bloqueio contra um alvo que atravessou o fogo; não pode perseguir nem ser reutilizado.",
    },
    "operador_sonar": {
        "lore": "Hidrografista naval que adaptou um sonar portátil para localizar mutações abaixo da superfície.",
        "function": "Revelação do canal e ruptura de camuflagem submersa.",
        "need": "Única unidade que expõe a blindagem do Mergulhador antes que tiros e torpedos possam feri-lo.",
    },
    "barco_patrulha": {
        "lore": "Lancha leve enviada por um canal de manutenção até a zona isolada da cachoeira.",
        "function": "Fogo sustentado exclusivo das duas linhas de água.",
        "need": "Oferece cadência onde tropas terrestres não podem ser colocadas e segura nadadores numerosos.",
    },
    "submarino_tatico": {
        "lore": "Submersível compacto de inspeção convertido para caçar organismos grandes na água contaminada.",
        "function": "Torpedo de perfuração contra blindados e chefes aquáticos.",
        "need": "É a resposta pesada do canal: pouca cadência, mas multiplicador contra carapaças e chefes submersos.",
    },
}

for _region, _roster in REGION_ROSTERS.items():
    for _card_key, _display in _roster:
        _detail = CARD_DETAILS[_card_key]
        DEFENSES[_card_key]["lore"] = _detail["lore"]
        DEFENSES[_card_key]["tactical_function"] = _detail["function"]
        DEFENSES[_card_key]["mechanical_need"] = _detail["need"]
        # Identificador estável usado por testes e pela interface. Nenhuma
        # carta ativa pode compartilhar a mesma utilidade mecânica.
        DEFENSES[_card_key]["unique_utility"] = _card_key


# Doutrinas da força urbana de Nova York. A Unidade não é somente um rótulo:
# ela define ocupação, alvo preferencial e uma vantagem com contrapartida.
CITY_TACTICAL_UNITS = {
    "xerife_rua": (
        "Patrulha Básica",
        1,
        "Tiro forte e recarga curta por baixo custo.",
        "Alcance curto e não atravessa aliados.",
    ),
    "agente_swat": (
        "SWAT de Supressão",
        1,
        "Rajada atravessa a formação aliada.",
        "Dano por projétil baixo e recarga longa.",
    ),
    "operador_radio_policial": (
        "Comando e Logística",
        1,
        "Gera suprimentos durante a onda sem exigir outra carta.",
        "Não ataca e precisa ser protegido.",
    ),
    "atirador_precisao_swat": (
        "SWAT de Observação",
        1,
        "Prioriza alvos de maior vida.",
        "Cadência baixa e fraco contra enxames.",
    ),
    "agente_entrada": (
        "Tropa de Choque",
        1,
        "Leque devastador à queima-roupa.",
        "Só cobre a casa imediatamente à frente.",
    ),
    "especialista_antipraga": (
        "Unidade Antipraga",
        2,
        "A nuvem química corrói blindagem biológica e contamina grupos.",
        "Ocupa duas casas, usa tambor de seis granadas e recarrega lentamente.",
    ),
    "lancador_foguetes": (
        "Resposta Pesada",
        2,
        "Explosão quebra grupos e blindados.",
        "Ocupa duas casas, um disparo e recarga longa.",
    ),
    "escudeiro_tropa_choque": (
        "Tropa de Choque",
        1,
        "Interrompe a primeira investida recebida.",
        "Corpo a corpo e sem resposta a atacantes distantes.",
    ),
}
for _key, (_unit, _space, _advantage, _disadvantage) in CITY_TACTICAL_UNITS.items():
    DEFENSES[_key]["tactical_unit"] = _unit
    DEFENSES[_key]["footprint"] = _space
    DEFENSES[_key]["situational_advantage"] = _advantage
    DEFENSES[_key]["situational_disadvantage"] = _disadvantage
    DEFENSES[_key][
        "ability"
    ] = f"{DEFENSES[_key]['ability']} Unidade {_unit}: {_advantage} Limite: {_disadvantage}"


# Índices de atlas por carta, região e nível. Eles não podem ser inferidos
# apenas pelo "papel" da unidade: as três folhas de arte têm ordens próprias
# e uma célula N1 não representa automaticamente sua evolução N2. Esta é a
# única fonte usada pela seleção, pelo HUD, pelo dossiê e pela tropa em campo.
CARD_ATLAS_INDEX = {
    "city": {
        "recruta": 0,
        "soldado": 1,
        "instrutor": 2,
        "escopeteiro": 3,
        "escopeteiro_regular": 3,
        "sniper": 4,
        "sniper_regular": 4,
        "bombardeiro": 5,
        "granadeiro": 5,
        "morteiro_basico": 5,
        "morteiro": 5,
        "radio": 7,
        "torre_radio": 7,
        "lanca_chamas_bolso": 9,
        "lanca_chamas": 9,
        "lancador_veneno": 9,
        "canhao_veneno": 9,
        "barreira": 10,
        "barreira_reativa": 10,
        "mina": 11,
        "mina_segura": 11,
    },
    "desert": {
        "recruta": 0,
        "soldado": 1,
        "instrutor": 2,
        "escopeteiro": 3,
        "escopeteiro_regular": 3,
        "sniper": 4,
        "sniper_regular": 4,
        "morteiro_basico": 5,
        "morteiro": 5,
        "bombardeiro": 6,
        "granadeiro": 5,
        "radio": 8,
        "torre_radio": 7,
        "lanca_chamas_bolso": 10,
        "lanca_chamas": 9,
        "barreira": 11,
        "barreira_reativa": 10,
        "mina": 11,
        "mina_segura": 11,
    },
    "beach": {
        "recruta": 0,
        "soldado": 1,
        "instrutor": 2,
        "escopeteiro": 3,
        "escopeteiro_regular": 3,
        "sniper": 4,
        "sniper_regular": 4,
        "morteiro_basico": 5,
        "morteiro": 5,
        "bombardeiro": 7,
        "granadeiro": 5,
        "radio": 9,
        "torre_radio": 7,
        "lancador_agua": 9,
        "canhao_mare": 9,
        "barreira": 11,
        "barreira_reativa": 10,
        "mina": 11,
        "mina_segura": 11,
    },
}


# Estas cartas não possuíam um retrato exclusivo na folha regional. Cada uma
# recebe uma arte v7.8 que representa precisamente a classe indicada, em vez
# de reutilizar uma arte de outra carta só por ocupar a mesma célula do atlas.
CARD_ART_ASSETS = {
    ("city", "lancador_veneno"): "city_poison_sprayer_n1",
    ("city", "canhao_veneno"): "city_poison_cannon_n2",
    ("city", "morteiro_basico"): "city_mortar_n1",
    ("city", "morteiro"): "city_mortar_n2",
    ("desert", "mina"): "desert_mine_n1",
    ("desert", "morteiro"): "desert_mortar_n2",
    ("beach", "lancador_agua"): "beach_water_launcher_n1",
    ("beach", "canhao_mare"): "beach_water_cannon_n2",
    ("beach", "morteiro_basico"): "beach_mortar_n1",
    ("beach", "morteiro"): "beach_mortar_n2",
}


def regional_sprite_index(region: str, key: str) -> int:
    """Escolhe a célula correta da folha de artes para a região e o nível.

    A grade de seleção e o objeto posicionado usam esta mesma regra. Antes,
    a carta usava o índice genérico enquanto a tropa no campo recebia um
    remapeamento regional separado; daí surgiam N1 e N2 com artes trocadas
    em alguns mapas. Uma única fonte elimina essa mistura.
    """
    return int(CARD_ATLAS_INDEX.get(region, {}).get(key, DEFENSES[key]["sprite"]))


ENEMIES = {
    "infectado_urbano": {
        "name": "Infectado Urbano",
        "hp": 124,
        "speed": 11,
        "damage": 17,
        "attack": 1.2,
        "sprite": 0,
        "ability": "Infectado básico de Nova York. Avança mancando e ataca com uma mordida curta.",
    },
    "desperto_khepra": {
        "name": "Desperto de Khepra",
        "hp": 130,
        "speed": 10.5,
        "damage": 17,
        "attack": 1.18,
        "sprite": 0,
        "ability": "Múmia básica despertada pela contaminação. É um pouco mais resistente, mas não possui poder especial.",
    },
    "afogado_cachoeira": {
        "name": "Afogado da Cachoeira",
        "hp": 126,
        "speed": 11,
        "damage": 16,
        "attack": 1.16,
        "sprite": 0,
        "ability": "Infectado terrestre da área da cachoeira. Avança somente pelas margens; não ocupa os canais.",
    },
    "corredor_cidade": {
        "name": "Corredor do Metrô",
        "hp": 340,
        "speed": 24,
        "damage": 46,
        "attack": 0.78,
        "sprite": 1,
        "armor": 0.25,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed", "signal_jammer"),
        "ability": "Infectado urbano resistente. Corre em velocidade constante, ignora interrupções por tiro e causa dano dobrado somente na primeira mordida.",
    },
    "corredor_deserto": {
        "name": "Corredor da Necrópole",
        "hp": 360,
        "speed": 22,
        "damage": 54,
        "attack": 0.82,
        "sprite": 1,
        "armor": 0.26,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed"),
        "ability": "Múmia leve e resistente. Mantém corrida constante, não sofre interrupção por dano e abre o combate com um golpe dobrado.",
    },
    "corredor_cachoeira": {
        "name": "Corredor da Trilha",
        "hp": 350,
        "speed": 23,
        "damage": 39,
        "attack": 0.80,
        "sprite": 1,
        "armor": 0.25,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed"),
        "ability": "Turista contaminado das trilhas. Corre sem dash, ignora stagger e desfere um primeiro ataque dobrado antes de voltar ao dano normal.",
    },
    "rastejador_cidade": {
        "name": "Rastejador dos Túneis",
        "hp": 420,
        "speed": 6,
        "damage": 34,
        "attack": 1.30,
        "sprite": 1,
        "armor": 0.18,
        "devour_classes": (1, 2),
        "ability": "Ex-funcionário dos túneis, com as duas pernas amputadas. É lento e muito resistente; ao alcançar tropas de Classe 1 ou 2, devora o alvo.",
    },
    "rastejador_deserto": {
        "name": "Rastejador Mumificado",
        "hp": 450,
        "speed": 5.5,
        "damage": 38,
        "attack": 1.40,
        "sprite": 1,
        "armor": 0.20,
        "devour_classes": (1, 2),
        "ability": "Múmia sem as pernas, coberta por faixas e areia contaminada. É extremamente resistente e devora tropas de Classe 1 ou 2 ao alcançá-las.",
    },
    "rastejador_cachoeira": {
        "name": "Rastejador do Cânion",
        "hp": 435,
        "speed": 6,
        "damage": 36,
        "attack": 1.35,
        "sprite": 1,
        "armor": 0.19,
        "devour_classes": (1, 2),
        "ability": "Antigo guia de resgate de Minas, com as duas pernas amputadas. Avança lentamente e devora tropas de Classe 1 ou 2 ao alcançar a defesa.",
    },
    "caminhante": {
        "name": "Caminhante",
        "hp": 108,
        "speed": 12,
        "damage": 12,
        "attack": 1.2,
        "sprite": 0,
        "ability": "Lento, pouca vida e pouco dano. Pressiona apenas pelo número.",
    },
    "corredor": {
        "name": "Corredor",
        "hp": 94,
        "speed": 24,
        "damage": 27,
        "attack": 0.75,
        "sprite": 1,
        "ability": "Dá um arranque inicial; pune linhas sem escopeta, mina ou barreira.",
        "tags": ("dash",),
    },
    "rastejante": {
        "name": "Rastejante",
        "hp": 158,
        "speed": 9,
        "damage": 29,
        "attack": 1.05,
        "sprite": 1,
        "ability": "Mais lento que o Caminhante, mas morde com força quando alcança uma defesa.",
    },
    "conehead": {
        "name": "Blindado de Cone",
        "hp": 185,
        "speed": 11,
        "damage": 15,
        "attack": 1.0,
        "sprite": 2,
        "ability": "Cone e colete reflexivo absorvem fogo leve. Força foco ou explosão.",
        "armor": 0.18,
    },
    "policial": {
        "name": "Policial Infectado",
        "hp": 220,
        "speed": 10,
        "damage": 17,
        "attack": 1.0,
        "sprite": 3,
        "ability": "Colete balístico e tiros curtos contra a linha de defesa.",
        "armor": 0.25,
        "tags": ("gun",),
    },
    "militar": {
        "name": "Militar Infectado",
        "hp": 300,
        "speed": 9,
        "damage": 25,
        "attack": 0.9,
        "sprite": 4,
        "ability": "Armadura reforçada e arma de fogo. Exige dano concentrado ou corrosão controlada.",
        "armor": 0.38,
        "tags": ("gun",),
    },
    "escudo": {
        "name": "Porta-Escudo",
        "hp": 260,
        "speed": 8,
        "damage": 33,
        "attack": 1.05,
        "sprite": 5,
        "ability": "Escudo bloqueia boa parte do fogo frontal; a granada e o lança-chamas ajudam a quebrar a coluna.",
        "armor": 0.48,
        "tags": ("shield",),
    },
    "cuspidor": {
        "name": "Cuspidor Ácido",
        "hp": 178,
        "speed": 12,
        "damage": 14,
        "attack": 1.1,
        "sprite": 6,
        "ability": "Cospe até três blocos: corrosão reduz o desempenho e o ácido causa dano contínuo.",
        "tags": ("acid",),
    },
    "divisor": {
        "name": "Divisor",
        "hp": 300,
        "speed": 7,
        "damage": 34,
        "attack": 1.05,
        "sprite": 7,
        "ability": "Robusto e lento; sua morte explode em área, com dano físico e corrosivo.",
        "tags": ("acid", "explode_death"),
    },
    "gritador": {
        "name": "Gritador",
        "hp": 160,
        "speed": 11,
        "damage": 14,
        "attack": 1.1,
        "sprite": 8,
        "ability": "Acelera infectados próximos e pode chamar uma pequena horda.",
        "tags": ("scream",),
    },
    "saltador": {
        "name": "Saltador",
        "hp": 152,
        "speed": 16,
        "damage": 24,
        "attack": 0.9,
        "sprite": 9,
        "ability": "Ultrapassa somente a primeira defesa que bloquear seu caminho; depois precisa enfrentar a próxima.",
        "tags": ("jump",),
    },
    "bruto": {
        "name": "Bruto de Demolição",
        "hp": 450,
        "speed": 7,
        "damage": 48,
        "attack": 0.9,
        "sprite": 10,
        "ability": "Sub-chefe pesado; seus impactos deixam a linha vulnerável.",
        "tags": ("stomp",),
    },
    "digger": {
        "name": "Escavador",
        "hp": 185,
        "speed": 13,
        "damage": 42,
        "attack": 0.88,
        "sprite": 2,
        "ability": "Cava visivelmente sob o terreno e atravessa apenas a primeira defesa da frente, como um salto subterrâneo.",
        "tags": ("dig",),
    },
    "ladrao": {
        "name": "Ladrão de Suprimentos",
        "hp": 135,
        "speed": 14,
        "damage": 10,
        "attack": 1.2,
        "sprite": 3,
        "ability": "Mago das ruínas: rouba créditos. Clique nele antes que alcance a linha para recuperar a carga.",
        "tags": ("steal",),
    },
    "curandeiro": {
        "name": "Curandeiro Mortal",
        "hp": 190,
        "speed": 10,
        "damage": 12,
        "attack": 1.1,
        "sprite": 4,
        "ability": "Arremessa poções que curam aliados e pode devolver um derrotado à luta uma vez.",
        "tags": ("heal",),
    },
    "parasita": {
        "name": "Parasita das Dunas",
        "hp": 255,
        "speed": 9,
        "damage": 30,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Agarra uma tropa, corta seu ataque e atordoa até dois blocos à frente.",
        "tags": ("parasite",),
    },
    "mutante": {
        "name": "Mutante de Ruínas",
        "hp": 400,
        "speed": 7,
        "damage": 42,
        "attack": 0.9,
        "sprite": 6,
        "ability": "Sub-chefe com hospedeiro armado nas costas e soco que atordoa uma área.",
        "tags": ("stomp", "gun"),
    },
    "necromante_minion": {
        "name": "Múmia Invocada",
        "hp": 130,
        "speed": 15,
        "damage": 18,
        "attack": 1.0,
        "sprite": 7,
        "ability": "Múmia fraca convocada pelo Necromante; existe para consumir munição e cobertura.",
    },
    "boia": {
        "name": "Turista de Boia",
        "hp": 135,
        "speed": 9,
        "damage": 15,
        "attack": 1.1,
        "sprite": 0,
        "ability": "Lento na água, mas a boia o protege de uma parte do dano.",
        "armor": 0.12,
    },
    "surfista": {
        "name": "Surfista Infectado",
        "hp": 122,
        "speed": 25,
        "damage": 25,
        "attack": 0.8,
        "sprite": 1,
        "ability": "A prancha cria um dash aquático, obrigando reação rápida nas faixas molhadas.",
        "tags": ("dash",),
    },
    "salva_vidas": {
        "name": "Salva-Vidas de Escudo",
        "hp": 225,
        "speed": 10,
        "damage": 25,
        "attack": 1.0,
        "sprite": 2,
        "ability": "Boia-escudo reduz o dano frontal e protege a maré atrás dele.",
        "armor": 0.40,
        "tags": ("shield",),
    },
    "mergulhador": {
        "name": "Mergulhador Blindado",
        "hp": 275,
        "speed": 10,
        "damage": 33,
        "attack": 0.92,
        "sprite": 3,
        "ability": "Armadura de mergulho espessa; pode atingir embarcações com força.",
        "armor": 0.30,
        "tags": ("naval_hunter",),
    },
    "cacador": {
        "name": "Caçador da Costa",
        "hp": 180,
        "speed": 15,
        "damage": 32,
        "attack": 0.85,
        "sprite": 4,
        "ability": "Persegue a defesa mais próxima com investida de arpão.",
        "tags": ("jump",),
    },
    "cowboy": {
        "name": "Cowboy da Maré",
        "hp": 205,
        "speed": 12,
        "damage": 18,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Dispara de longe na costa e pressiona o rádio e a retaguarda.",
        "tags": ("gun",),
    },
    "sal_cuspidor": {
        "name": "Cuspidor de Sal",
        "hp": 182,
        "speed": 12,
        "damage": 15,
        "attack": 1.0,
        "sprite": 6,
        "ability": "Sal pressurizado corrói metal e descarrega as armas em contato.",
        "tags": ("acid",),
    },
    "mar_gritador": {
        "name": "Gritador de Maré",
        "hp": 175,
        "speed": 11,
        "damage": 15,
        "attack": 1.0,
        "sprite": 7,
        "ability": "O grito acelera nadadores e chama reforços vindos da arrebentação.",
        "tags": ("scream",),
    },
    "nadador": {
        "name": "Nadador",
        "hp": 180,
        "speed": 18,
        "damage": 25,
        "attack": 0.92,
        "sprite": 8,
        "ability": "Movimenta-se bem nas faixas de água e passa por minas terrestres.",
    },
}

# Três ameaças adicionais por região completam seis zumbis comuns próprios.
# Nenhuma delas depende de magia: toda habilidade nasce de equipamento
# contaminado, mutação biológica ou das condições físicas do desastre.
ENEMIES.update(
    {
        "policial_helix": {
            "name": "Policial Infectado da Félix",
            "hp": 218,
            "speed": 9.2,
            "damage": 18,
            "attack": 1.05,
            "sprite": 3,
            "armor": 0.34,
            "tags": ("shield",),
            "ability": "Colete e capacete absorvem os primeiros tiros; corrosão e precisão quebram a proteção.",
        },
        "cientista_helix": {
            "name": "Cientista da Félix",
            "hp": 164,
            "speed": 9.5,
            "damage": 15,
            "attack": 1.15,
            "sprite": 6,
            "tags": ("acid",),
            "ability": "O cilindro rompido lança composto corrosivo a até três blocos, sem qualquer poder sobrenatural.",
        },
        "tecnico_subestacao": {
            "name": "Técnico da Subestação",
            "hp": 176,
            "speed": 11.0,
            "damage": 16,
            "attack": 1.05,
            "sprite": 8,
            "tags": ("shock",),
            "ability": "Baterias presas ao corpo descarregam um pulso curto que atrasa a tropa mais próxima.",
        },
        "arqueiro_necropole": {
            "name": "Arqueiro da Necrópole",
            "hp": 152,
            "speed": 10.8,
            "damage": 17,
            "attack": 1.08,
            "sprite": 3,
            "tags": ("gun",),
            "ability": "Ataca à distância com um arco físico preservado; é perigoso, mas possui pouca vida.",
        },
        "hospedeiro_escaravelhos": {
            "name": "Hospedeiro de Escaravelhos",
            "hp": 238,
            "speed": 8.2,
            "damage": 21,
            "attack": 1.12,
            "sprite": 7,
            "armor": 0.16,
            "tags": ("explode_death",),
            "ability": "A colônia alterada no torso se espalha no impacto final e pune tropas amontoadas.",
        },
        "saqueador_canopico": {
            "name": "Saqueador Canópico",
            "hp": 146,
            "speed": 13.0,
            "damage": 12,
            "attack": 1.18,
            "sprite": 3,
            "tags": ("steal",),
            "ability": "Prioriza a retaguarda e rouba uma pequena carga de suprimentos usando recipientes da escavação.",
        },
        "pescador_praga": {
            "name": "Pescador da Praga",
            "hp": 186,
            "speed": 10.4,
            "damage": 18,
            "attack": 1.10,
            "sprite": 6,
            "tags": ("net",),
            "amphibious": True,
            "ability": "Lança uma rede contaminada que reduz por instantes a cadência da defesa mais próxima.",
        },
        "baiacu_mutante": {
            "name": "Baiacu Mutante",
            "hp": 520,
            "speed": 6.8,
            "damage": 36,
            "attack": 1.12,
            "sprite": 9,
            "armor": 0.28,
            "tags": ("explode_death", "stomp"),
            "ability": "Subchefe aquático: infla sob fogo e espalha espinhos somente na própria faixa ao ser abatido.",
        },
    }
)

ENEMIES["bruto"].update(
    {
        "name": "Demolidor do Metrô",
        "ability": "Subchefe industrial: marreta duas casas próximas e exige contenção antes do contato.",
    }
)
ENEMIES["divisor"].update(
    {
        "name": "Bruto da Quarentena",
        "ability": "Subchefe dentro de um traje Félix rompido; as placas reduzem explosões frontais.",
    }
)
ENEMIES["policial"].update(
    {
        "name": "Comandante Infectado",
        "ability": "Subchefe policial mutado: coordena a faixa e dispara rajadas curtas contra a retaguarda.",
    }
)
ENEMIES["parasita"].update(
    {
        "name": "Guardião do Sarcófago",
        "ability": "Escudo funerário contaminado desvia fogo frontal até o Guardião de Lâminas abrir sua postura.",
    }
)
ENEMIES["curandeiro"].update(
    {
        "name": "Sacerdote da Praga",
        "ability": "Incensário químico restaura tecido infectado próximo; o Incinerador interrompe a regeneração.",
    }
)
ENEMIES["mutante"].update(
    {
        "name": "Executor da Escavação",
        "ability": "Subchefe pesado fundido a ferramentas do sítio; golpeia o chão e quebra formações compactas.",
    }
)
ENEMIES["salva_vidas"].update(
    {
        "name": "Salva-Vidas Colossal",
        "ability": "Subchefe anfíbio: investida de resgate mutada derruba a cadência das tropas na própria faixa.",
    }
)
ENEMIES["cacador"].update(
    {
        "name": "Caçador das Profundidades",
        "ability": "Subchefe de mergulho blindado que avança com arpão; sonar e precisão naval expõem suas placas.",
    }
)


BOSSES = {
    "bruto_demolidor": {
        "name": "BRUTO DEMOLIDOR",
        "hp": 1000,
        "speed": 6,
        "damage": 30,
        "attack": 1.05,
        "sprite": 10,
        "ability": "Entrada: paralisa militares por 3 s. Depois, o Martelo fecha só a própria faixa por 1,2 s a cada 18 s.",
        "type": "bruto_demolidor",
    },
    "comandante_mortos": {
        "name": "COMANDANTE DOS MORTOS",
        "hp": 1200,
        "speed": 9,
        "damage": 26,
        "attack": 0.88,
        "sprite": 11,
        "ability": "Entrada: dá fúria breve à escolta. Depois, dispara rajadas duplas leves e reacelera somente aliados próximos.",
        "type": "comandante",
    },
    "cuspidor_alfa": {
        "name": "CUSPIDADOR ALFA",
        "hp": 1600,
        "speed": 11,
        "damage": 28,
        "attack": 0.95,
        "sprite": 11,
        "ability": "Entrada: névoa ácida global de 1,2 s. Depois, cospe em um alvo na própria faixa, com corrosão curta.",
        "type": "alfa",
    },
    "mutante_ruinas": {
        "name": "MUTANTE DAS RUÍNAS",
        "hp": 1100,
        "speed": 6,
        "damage": 32,
        "attack": 0.98,
        "sprite": 6,
        "ability": "Entrada: abalo leve nas faixas vizinhas. Depois, golpeia somente tropas próximas por 1 s de atordoamento.",
        "type": "mutante",
    },
    "necromante": {
        "name": "NECROMANTE",
        "hp": 1350,
        "speed": 7,
        "damage": 23,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: invoca uma múmia. Depois, invoca uma por ciclo e cura pouco os aliados próximos.",
        "type": "necromante",
    },
    "colosso_mutante": {
        "name": "COLOSSO MUTANTE",
        "hp": 1850,
        "speed": 4,
        "damage": 38,
        "attack": 1.05,
        "sprite": 11,
        "ability": "Entrada: tremor global de 1,2 s. Depois, arremessa uma rocha leve contra uma faixa-alvo.",
        "type": "colosso",
    },
    "tide_brute": {
        "name": "BRUTO DA MARÉ",
        "hp": 1050,
        "speed": 6,
        "damage": 34,
        "attack": 1.0,
        "sprite": 9,
        "ability": "Entrada: uma onda leve abala a faixa de água. Depois, golpeia boias e embarcações apenas perto da maré.",
        "type": "tide",
    },
    "cacador_abissal": {
        "name": "CAÇADOR ABISSAL",
        "hp": 1450,
        "speed": 11,
        "damage": 26,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: avança uma distância curta no canal. Depois, mergulha pouco e ataca uma embarcação próxima.",
        "type": "hunter",
    },
    "leviata": {
        "name": "LEVIATÃ",
        "hp": 2050,
        "speed": 5,
        "damage": 42,
        "attack": 1.0,
        "sprite": 11,
        "ability": "Entrada: uma maré moderada atinge o canal. Depois, lança um jato concentrado numa embarcação da própria faixa.",
        "type": "leviathan",
    },
}

BOSSES["bruto_demolidor"]["name"] = "DIRETOR DEMOLIDOR DA FÉLIX"
BOSSES["comandante_mortos"]["name"] = "COMANDANTE ISOTÓPICO"
BOSSES["cuspidor_alfa"]["name"] = "DIRETOR ZERO CORROSIVO"
BOSSES["mutante_ruinas"]["name"] = "GUARDIÃO ANÚBIS CONTAMINADO"
BOSSES["necromante"]["name"] = "COMANDANTE DA NECRÓPOLE"
BOSSES["colosso_mutante"]["name"] = "COLOSSO DA PIRÂMIDE"
BOSSES["tide_brute"]["name"] = "BRUTO DA CACHOEIRA"
BOSSES["cacador_abissal"]["name"] = "CAÇADOR ABISSAL"
BOSSES["leviata"]["name"] = "COLOSSO DO VÉU VERDE"

REGION_SUBBOSSES = {
    "city": ("bruto", "divisor", "policial"),
    "desert": ("parasita", "curandeiro", "mutante"),
    "beach": ("baiacu_mutante", "salva_vidas", "cacador"),
}
REGION_BOSSES = {
    "city": ("bruto_demolidor", "comandante_mortos", "cuspidor_alfa"),
    "desert": ("mutante_ruinas", "necromante", "colosso_mutante"),
    "beach": ("tide_brute", "cacador_abissal", "leviata"),
}
for _region, _bosses in REGION_BOSSES.items():
    REGIONS[_region]["bosses"] = _bosses
for _subbosses in REGION_SUBBOSSES.values():
    for _subboss_key in _subbosses:
        ENEMIES[_subboss_key]["subboss"] = True


# Defesas especiais fazem composição importar. ``immunities`` bloqueia um
# canal até que a carta-counter rompa a proteção; ``resistances`` reduz dano
# sem anulá-lo. Assim RPG, granada e morteiro continuam úteis, mas não vencem
# sozinhos todas as doze ondas.
ENEMY_DEFENSE_TRAITS = {
    "policial": {
        "immunities": ("ballistic",),
        "counter_keys": ("especialista_antipraga", "atirador_precisao_swat"),
        "counter_label": "Antipraga ou tiro de precisão",
        "defense_name": "colete Félix selado",
    },
    "divisor": {
        "resistances": {"explosive": 0.82},
        "weaknesses": {"chemical": 1.45, "thermal": 1.30},
        "counter_label": "Especialista Antipraga",
        "defense_name": "bolsa de dispersão explosiva",
    },
    "bruto": {
        "immunities": ("explosive",),
        "resistances": {"ballistic": 0.48},
        "counter_keys": ("agente_entrada", "escudeiro_tropa_choque"),
        "counter_label": "Tropa de Choque",
        "defense_name": "guarda de demolição",
    },
    "parasita": {
        "immunities": ("ballistic", "explosive"),
        "counter_keys": ("guardiao_laminas",),
        "counter_label": "Guardião de Lâminas",
        "defense_name": "guarda de lâminas amaldiçoadas",
    },
    "curandeiro": {
        "resistances": {"explosive": 0.78, "ballistic": 0.30},
        "weaknesses": {"thermal": 1.55},
        "counter_label": "Incinerador do Deserto",
        "defense_name": "faixas regenerativas",
    },
    "mutante": {
        "resistances": {"explosive": 0.76},
        "weaknesses": {"ballistic": 1.15},
        "counter_label": "Tenente Artilheiro",
        "defense_name": "placas de ruína",
    },
    "mergulhador": {
        "immunities": ("ballistic", "explosive"),
        "counter_keys": ("atirador_precisao_marinha", "submarino_tatico"),
        "counter_label": "Precisão naval ou Submarino Tático",
        "defense_name": "camuflagem submersa",
    },
    "salva_vidas": {
        "resistances": {"explosive": 0.78, "ballistic": 0.42},
        "weaknesses": {"hydraulic": 1.55},
        "counter_label": "Bombeiro Hidráulico",
        "defense_name": "boia contaminada pressurizada",
    },
    "cacador": {
        "resistances": {"explosive": 0.72},
        "weaknesses": {"precision": 1.50, "piercing": 1.35},
        "counter_label": "Precisão naval ou Submarino",
        "defense_name": "placas abissais",
    },
}

for _enemy_key, _traits in ENEMY_DEFENSE_TRAITS.items():
    ENEMIES[_enemy_key].update(_traits)

# O Zumbi de Lâmina é a leitura final do antigo Parasita: agora sua ficha e a
# regra de combate comunicam a mesma ameaça e o mesmo counter obrigatório.
ENEMIES["parasita"]["name"] = "Zumbi de Lâmina"
ENEMIES["parasita"]["ability"] = (
    "As lâminas amaldiçoadas desviam balas e explosões. Somente o Guardião "
    "de Lâminas consegue aparar o golpe e abrir sua defesa por alguns segundos."
)

for _boss_key, _boss_data in BOSSES.items():
    _boss_data.setdefault("resistances", {})["explosive"] = 0.68
    _boss_data.setdefault("defense_name", "massa mutante anti-impacto")

BOSSES["bruto_demolidor"].update(
    {
        "counter_keys": ("agente_entrada", "escudeiro_tropa_choque"),
        "counter_label": "Tropa de Choque",
    }
)
BOSSES["necromante"].update(
    {
        "weaknesses": {"thermal": 1.45},
        "counter_label": "Incinerador do Deserto",
    }
)
BOSSES["leviata"].update(
    {
        "weaknesses": {"piercing": 1.55},
        "counter_label": "Submarino Tático",
    }
)


REGION_ENEMIES = {
    "city": (
        "infectado_urbano",
        "corredor_cidade",
        "rastejador_cidade",
        "policial_helix",
        "cientista_helix",
        "tecnico_subestacao",
    ),
    "desert": (
        "desperto_khepra",
        "corredor_deserto",
        "rastejador_deserto",
        "arqueiro_necropole",
        "hospedeiro_escaravelhos",
        "saqueador_canopico",
    ),
    "beach": (
        "afogado_cachoeira",
        "corredor_cachoeira",
        "rastejador_cachoeira",
        "surfista",
        "mergulhador",
        "pescador_praga",
    ),
}

# Fonte única para o protótipo regional. O ensaio de integração antigo
# criava sempre o infectado urbano, mesmo quando o cenário ativo era Egito ou
# Cachoeira; como não existia animação cruzada para esse par, o ator acabava
# transparente. Todas as entradas (campanha, ensaio e testes) usam este mapa.
BASIC_DEFENDER_BY_REGION = {
    "city": "xerife_rua",
    "desert": "pistoleiro_deserto",
    "beach": "marinheiro",
}
BASIC_ENEMY_BY_REGION = {
    "city": "infectado_urbano",
    "desert": "desperto_khepra",
    "beach": "afogado_cachoeira",
}
DEFENDER_ACTOR_BY_KEY = {
    "xerife_rua": "city_guard",
    "agente_swat": "city_auto",
    "operador_radio_policial": "city_radio",
    "pistoleiro_deserto": "desert_guard",
    "fuzileiro_deserto": "desert_auto",
    "torre_radio_egito": "desert_radio",
    "marinheiro": "beach_guard",
    "fuzileiro_marinha": "beach_auto",
    "estacao_comunicacao_cachoeira": "beach_radio",
    "atirador_precisao_swat": "city_sniper",
    "agente_entrada": "city_entry",
    "especialista_antipraga": "city_antiplague",
    "lancador_foguetes": "city_rocket",
    "escudeiro_tropa_choque": "city_shield",
    "atirador_horizonte": "desert_sniper",
    "tenente_artilheiro": "desert_heavy",
    "incinerador_deserto": "desert_incinerator",
    "nomade_morteiro": "desert_mortar",
    "guardiao_laminas": "desert_blade",
    "atirador_precisao_marinha": "beach_sniper",
    "bombeiro_hidraulico": "beach_waterjet",
    "granadeiro_profundidades": "beach_grenadier",
    "barco_patrulha": "beach_boat",
    "submarino_tatico": "beach_sub",
}
ENEMY_ACTOR_BY_KEY = {
    "infectado_urbano": "city_zombie_v2",
    "corredor_cidade": "city_runner_v2",
    "rastejador_cidade": "city_crawler_v2",
    "policial_helix": "city_police_infected",
    "cientista_helix": "city_scientist",
    "tecnico_subestacao": "city_technician",
    "bruto": "city_demolisher",
    "divisor": "city_quarantine_brute",
    "policial": "city_mutant_commander",
    "bruto_demolidor": "city_boss_director",
    "comandante_mortos": "city_boss_commander",
    "cuspidor_alfa": "city_boss_alpha",
    "desperto_khepra": "desert_zombie_v2",
    "corredor_deserto": "desert_runner_v2",
    "rastejador_deserto": "desert_crawler_v2",
    "arqueiro_necropole": "desert_archer",
    "hospedeiro_escaravelhos": "desert_beetle_host",
    "saqueador_canopico": "desert_looter",
    "parasita": "desert_sarcophagus_guard",
    "curandeiro": "desert_plague_priest",
    "mutante": "desert_mutant_enforcer",
    "mutante_ruinas": "desert_boss_anubis",
    "necromante": "desert_boss_commander",
    "colosso_mutante": "desert_boss_colossus",
    "afogado_cachoeira": "beach_zombie_v2",
    "corredor_cachoeira": "beach_runner_v2",
    "rastejador_cachoeira": "beach_crawler_v2",
    "surfista": "beach_surfer",
    "mergulhador": "beach_diver",
    "pescador_praga": "beach_fisher",
    "baiacu_mutante": "beach_puffer",
    "salva_vidas": "beach_lifeguard",
    "cacador": "beach_deep_hunter",
    "tide_brute": "beach_boss_brute",
    "cacador_abissal": "beach_boss_hunter",
    "leviata": "beach_boss_colossus",
}
CRAWLER_ENEMIES = frozenset(
    {"rastejador_cidade", "rastejador_deserto", "rastejador_cachoeira"}
)
ACTIVE_ENEMY_SKILL_TAGS = frozenset(
    {
        "dash",
        "naval_hunter",
        "gun",
        "acid",
        "shock",
        "net",
        "scream",
        "heal",
        "parasite",
        "stomp",
        "steal",
        "signal_jammer",
    }
)

# A Praia tem um canal real na terceira faixa. Criaturas de maré não podem
# simplesmente reaproveitar qualquer linha terrestre, pois isso quebraria a
# leitura do cenário e faria nadadores parecerem caminhar sobre a areia.
# Cowboy e Saltador são ameaças costeiras terrestres; o restante desta lista
# nasce exclusivamente no canal.
BEACH_WATER_ENEMIES = frozenset(
    {
        "surfista",
        "mergulhador",
        "pescador_praga",
        "baiacu_mutante",
        "cacador",
    }
)


def wave_enemy_pool(region: str, wave: int) -> tuple[str, ...]:
    """Retorna o elenco regional já liberado em uma onda, sem sorteio.

    A função é usada pela diretoria e pelo teste de regressão. Isso garante
    que um inimigo apresentado no dossiê regional não fique preso fora da
    campanha por uma fórmula de aleatoriedade escondida.
    """
    roster = REGION_ENEMIES[region]
    clamped_wave = int(clamp(wave, 1, TOTAL_WAVES))
    # As duas ondas comuns de cada ato nunca repetem um único zumbi. A estreia
    # já mistura dois tipos; a segunda apresenta um terceiro e a variedade
    # chega aos seis antes do ato final.
    unlock_curve = (2, 3, 3, 3, 4, 5, 5, 5, 6, 6, 6, 6)
    unlocked_count = min(len(roster), unlock_curve[clamped_wave - 1])
    return tuple(roster[:unlocked_count])


def make_save() -> dict:
    # As regiões são escolhas de estilo e desafio, não uma trava de conteúdo.
    return {"unlocked": list(REGIONS), "completed": [], "best_wave": {}}


def load_save() -> dict:
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "unlocked" not in data:
            raise ValueError
        data.setdefault("completed", [])
        data.setdefault("best_wave", {})
        # Atualiza saves antigos sem apagar os melhores resultados já gravados.
        data["unlocked"] = list(REGIONS)
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return make_save()


def save_campaign(data: dict) -> None:
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def defender_render_scale(defender: Defender) -> tuple[float, float]:
    """Tamanho visual único para a tropa ativa e sua animação de queda."""
    role = defender.stats["role"]
    if role == "mine":
        base = (76, 62) if defender.stats.get("water_only") else (82, 68)
        depth = lane_depth(defender.region, defender.row)
        return base[0] * depth, base[1] * depth
    if role in {"barrier", "boat", "sub"}:
        base = (105, 82)
    else:
        base = (86, 98)
    depth = lane_depth(defender.region, defender.row)
    return base[0] * depth, base[1] * depth


def enemy_render_scale(enemy: Enemy, region: str) -> tuple[float, float]:
    """Mantém infectados e soldados na mesma escala física do cenário.

    Os atlases terrestres têm mais respiro transparente e silhuetas mais
    estreitas que os atlases de tropas. Por isso o tamanho nominal anterior
    fazia um Caminhante parecer uma miniatura mesmo usando quase a mesma caixa
    de um soldado. Água já tinha uma leitura correta e preserva sua escala.
    """
    water_actor = region == "beach" and enemy.row in BEACH_WATER_ROWS
    if enemy.is_boss:
        base = (132, 142) if water_actor else (148, 158)
    elif enemy.key == "rastejante" or enemy.key in CRAWLER_ENEMIES:
        base = (126, 88)
    elif enemy.key == "saltador":
        base = (100, 116)
    elif enemy.key == "nadador" and region == "beach":
        base = (126, 72)
    elif water_actor:
        base = (82, 96)
    else:
        # Um zumbi terrestre comum fica cerca de 14% mais alto que um
        # combatente humano, sem ultrapassar a altura da pista dianteira.
        base = (98, 112)
    depth = lane_depth(region, enemy.row)
    return base[0] * depth, base[1] * depth


def animated_actor_render_scale(
    sprite: pygame.Surface,
    depth: float,
    *,
    body_height: float = 102.0,
    source_body_height: float = 130.0,
) -> tuple[float, float]:
    """Aplica escala física fixa à caixa normalizada de uma animação.

    Medir cada pose individualmente fazia quadros agachados crescerem e
    quadros esticados encolherem. As folhas de produção já foram normalizadas
    com 130 px para humanos e 136 px para infectados; por isso o fator não
    muda quando a animação troca de estado.
    """
    factor = (body_height * depth) / max(1.0, source_body_height)
    if sprite.get_width() <= 0 or sprite.get_height() <= 0:
        return 1.0, 1.0
    # As folhas já foram recompostas numa caixa única com os pés no mesmo
    # eixo. Recortar cada pose outra vez desfazia esse contrato: o corpo
    # mudava de centro e efeitos deixavam de acompanhar mãos/bocais.
    return sprite.get_width() * factor, sprite.get_height() * factor


_EMITTER_CONTACT_CACHE: dict[
    tuple[int, float, float, float, float, int], tuple[float, float]
] = {}


def sprite_emitter_contact(
    sprite: pygame.Surface,
    nominal_forward: float,
    nominal_height: float,
    *,
    body_height: float,
    source_body_height: float,
    facing: int,
) -> tuple[float, float]:
    """Encosta uma origem nominal na borda opaca real do equipamento.

    As tabelas continuam dizendo aproximadamente onde fica cano, boca ou
    ferramenta. A pose corrente fornece a posição final: procuramos a borda
    opaca mais próxima na direção do disparo. Assim braços e armas podem se
    mover entre quadros sem deixar bala, água ou habilidade nascer no vazio.
    O retorno permanece em coordenadas lógicas relativas ao centro dos pés.
    """
    cache_key = (
        id(sprite),
        round(float(nominal_forward), 3),
        round(float(nominal_height), 3),
        round(float(body_height), 3),
        round(float(source_body_height), 3),
        1 if facing >= 0 else -1,
    )
    cached = _EMITTER_CONTACT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    width, height = sprite.get_size()
    if width <= 1 or height <= 1:
        return nominal_forward, nominal_height
    ratio = source_body_height / max(1.0, body_height)
    seed_x = width / 2 + nominal_forward * ratio
    seed_y = height - nominal_height * ratio
    mask = pygame.mask.from_surface(sprite, threshold=8)
    radius = max(18, round(source_body_height * 0.24))
    left = max(0, math.floor(seed_x - radius))
    right = min(width - 1, math.ceil(seed_x + radius))
    top = max(0, math.floor(seed_y - radius))
    bottom = min(height - 1, math.ceil(seed_y + radius))
    direction = 1 if facing >= 0 else -1
    edge_candidates: list[tuple[float, int, int]] = []
    opaque_candidates: list[tuple[float, int, int]] = []
    for source_y in range(top, bottom + 1):
        for source_x in range(left, right + 1):
            if not mask.get_at((source_x, source_y)):
                continue
            distance = (source_x - seed_x) ** 2 + (source_y - seed_y) ** 2
            opaque_candidates.append((distance, source_x, source_y))
            next_x = source_x + direction
            if next_x < 0 or next_x >= width or not mask.get_at((next_x, source_y)):
                edge_candidates.append((distance, source_x, source_y))
    candidates = edge_candidates or opaque_candidates
    if not candidates:
        # Veículos largos (especialmente o submarino) podem ter a estimativa
        # antiga completamente fora da caixa da sprite. Nesse caso a busca se
        # amplia para a silhueta inteira e ainda exige a borda frontal.
        bounds = mask.get_bounding_rects()
        if bounds:
            union = bounds[0].copy()
            for component in bounds[1:]:
                union.union_ip(component)
            for source_y in range(union.top, union.bottom):
                for source_x in range(union.left, union.right):
                    if not mask.get_at((source_x, source_y)):
                        continue
                    next_x = source_x + direction
                    if 0 <= next_x < width and mask.get_at((next_x, source_y)):
                        continue
                    distance = (source_x - seed_x) ** 2 + (source_y - seed_y) ** 2
                    edge_candidates.append((distance, source_x, source_y))
        candidates = edge_candidates
    if not candidates:
        result = (nominal_forward, nominal_height)
        _EMITTER_CONTACT_CACHE[cache_key] = result
        return result
    _distance, source_x, source_y = min(candidates, key=lambda item: item[0])
    logical_forward = (source_x - width / 2) / ratio
    logical_height = (height - source_y) / ratio
    result = (logical_forward, logical_height)
    _EMITTER_CONTACT_CACHE[cache_key] = result
    return result


def defender_visual_layout(defender: Defender):
    """Recupera a medida física pela identidade, não por uma pose isolada."""
    return defender_layout(DEFENDER_ACTOR_BY_KEY.get(defender.key))


def defender_weapon_origin(defender: Defender) -> tuple[float, float]:
    """Boca do equipamento no mundo, já corrigida pela perspectiva da faixa."""
    layout = defender_visual_layout(defender)
    depth = lane_depth(defender.region, defender.row)
    muzzle_forward = layout.muzzle_forward
    muzzle_height = layout.muzzle_height
    animation = defender.visual_animation
    if layout.muzzle_cycle and animation is not None and animation.state == "shoot":
        index = min(animation.frame_index, len(layout.muzzle_cycle) - 1)
        muzzle_forward, muzzle_height = layout.muzzle_cycle[index]
    if animation is not None and animation.state == "shoot":
        muzzle_forward, muzzle_height = sprite_emitter_contact(
            animation.frame,
            muzzle_forward,
            muzzle_height,
            body_height=layout.body_height,
            source_body_height=layout.source_height,
            facing=1,
        )
    return (
        defender.render_x + muzzle_forward * depth,
        defender.y - muzzle_height * depth,
    )


def defender_animation_profile(defender: Defender) -> str:
    """Perfil corporal usado pelo shader sem alterar a ficha da carta."""
    return str(defender.stats.get("role", "humanoid"))


def enemy_animation_profile(enemy: Enemy) -> str:
    """Escolhe marcha, mordida e gesto de habilidade pela anatomia do ator."""
    boss_profiles = {
        "bruto_demolidor": "hammer_boss",
        "comandante": "commander_boss",
        "alfa": "toxic_boss",
        "mutante": "hammer_boss",
        "necromante": "necromancer_boss",
        "colosso": "colossus_boss",
        "tide": "sea_boss",
        "hunter": "sea_boss",
        "leviathan": "leviathan_boss",
    }
    if enemy.is_boss:
        return boss_profiles.get(str(enemy.data.get("type", "")), "heavy")
    if enemy.key == "rastejante" or enemy.key in CRAWLER_ENEMIES:
        return "crawler"
    if "jump" in enemy.tags:
        return "jumper"
    if "dig" in enemy.tags:
        return "digger"
    if "runner" in enemy.tags or "dash" in enemy.tags:
        return "runner"
    if "gun" in enemy.tags or "acid" in enemy.tags:
        return "shooter"
    if "heal" in enemy.tags or "steal" in enemy.tags:
        return "caster"
    if (
        "stomp" in enemy.tags
        or "parasite" in enemy.tags
        or "explode_death" in enemy.tags
    ):
        return "heavy"
    return "walker"


def actor_pose(
    motion: ActorMotion,
    *,
    enemy: bool,
    profile: str = "generic",
    progress: float = 0.0,
) -> tuple[float, float, float, float, float]:
    """Converte um estado semântico em pose, inclinação e escala.

    As quatro fases de cada ciclo são calculadas de forma determinística. Na
    prática isso funciona como uma pequena folha de sprites, só que não perde
    sincronia quando a máquina cai de 60 para 30 FPS.
    """
    direction = -1.0 if enemy else 1.0
    cycle = math.sin(motion.state_elapsed * math.tau * 1.75)
    pulse = math.sin(motion.state_elapsed * math.tau * 3.2)
    state = motion.state
    dx, dy, angle, scale_x, scale_y = 0.0, 0.0, 0.0, 1.0, 1.0
    if state == "spawn":
        p = clamp(motion.state_elapsed / 0.28, 0.0, 1.0)
        scale_x = scale_y = 0.72 + p * 0.28
        dy = (1.0 - p) * 18
    elif state == "walk":
        stride = 1.45 if profile == "runner" else 1.0
        dx = cycle * 2.2 * stride
        dy = -abs(cycle) * 3.2 * stride
        angle = cycle * 3.4 * direction * stride
        scale_x = 1.0 + abs(cycle) * 0.022
    elif state in {"brace", "idle", "armed"}:
        dy = -abs(cycle) * 1.1
        angle = cycle * 0.75 * direction
    elif state == "attack":
        p = progress or clamp(motion.state_elapsed / 0.28, 0.0, 1.0)
        thrust = math.sin(p * math.pi)
        dx = direction * thrust * (8.5 if enemy else 3.6)
        dy = thrust * (1.8 if enemy else -1.4)
        angle = direction * thrust * (11.0 if enemy else -4.0)
        scale_x = 1.0 + thrust * (0.065 if enemy else 0.025)
    elif state in {"support", "promote"}:
        dy = -abs(pulse) * 4.0
        angle = pulse * 3.0
        scale_x = scale_y = 1.0 + abs(pulse) * 0.045
    elif state == "reload":
        # O fallback mostra os mesmos quatro tempos do shader; a mão e o pente
        # são completados pelo deformador de braços e arma no apresentador.
        action = clamp(progress, 0.0, 1.0)
        reach = math.sin(clamp(action / 0.45, 0.0, 1.0) * math.pi)
        insert = math.sin(clamp((action - 0.38) / 0.58, 0.0, 1.0) * math.pi)
        dx = direction * (reach - insert) * 2.5
        dy = (reach + insert) * 1.7
        angle = direction * (reach * 5.5 - insert * 3.0)
        scale_y = 1.0 - reach * 0.018
    elif state == "hit":
        impact = math.sin(clamp(motion.state_elapsed / 0.16, 0.0, 1.0) * math.pi)
        dx = -direction * impact * 8.0
        dy = -impact * 2.5
        angle = -direction * impact * 10.0
    elif state == "stunned":
        dx = math.sin(motion.state_elapsed * 16.0) * 2.5
        angle = math.sin(motion.state_elapsed * 11.0) * 9.0
    elif state == "jump":
        angle = -direction * 10.0
        scale_x = 1.06
        scale_y = 0.96
    elif state.startswith("dig"):
        angle = direction * cycle * 2.0
        scale_x = 1.0 + abs(cycle) * 0.03
    elif state == "skill":
        action = progress or clamp(motion.state_elapsed / 0.46, 0.0, 1.0)
        power = math.sin(action * math.pi)
        if profile in {"hammer_boss", "colossus_boss"}:
            dy = power * 5.5
            angle = direction * (12.0 - action * 25.0) * power
            scale_x, scale_y = 1.0 + power * 0.07, 1.0 - power * 0.07
        elif profile in {"sea_boss", "leviathan_boss"}:
            dx = direction * power * 7.0
            dy = -power * 7.0
            angle = direction * power * 7.0
        else:
            dy = -power * 4.5
            angle = direction * math.sin(action * math.tau) * 7.0
            scale_x = scale_y = 1.0 + power * 0.06
    elif state == "roll":
        dx = cycle * 0.8
        dy = -abs(cycle) * 1.7
        angle = cycle * 1.4
    elif state == "dead":
        p = clamp(motion.state_elapsed / 0.48, 0.0, 1.0)
        dx = direction * p * 10.0
        angle = -direction * p * 28.0
        scale_x = 1.0 + p * 0.08
        scale_y = 1.0 - p * 0.22
    # Defensores mantêm o contato dos pés com o terreno em qualquer estado.
    # A sensação de vida vem dos braços, arma, inclinação e troca de quadros;
    # deslocar a silhueta inteira para cima fazia sobretudo o Marinheiro parecer
    # estar pulando. Saltos reais continuam exclusivos dos inimigos que possuem
    # a habilidade correspondente e usam ``enemy.jump_state``.
    if not enemy:
        dy = 0.0
    return dx, dy, angle, scale_x, scale_y


class Game:
    def __init__(self, *, integration_preview: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption(f"Soldados vs Zumbis — {VERSION}")
        self.presenter: OpenGLPresenter | None = None
        self.renderer_error = ""
        self.renderer_label = "SOFTWARE · CPU/RAM"
        self.actor_commands: list[ActorCommand] = []
        self.overlay_surface: pygame.Surface | None = None
        self.world_surface = self._create_display()
        self.screen = self.world_surface
        self.clock = pygame.time.Clock()
        self.fonts = FontBook()
        self.assets = Assets()
        self.scenario_runtime = ScenarioRuntime()
        self.audio = AudioSystem()
        # Mouse continua sendo o padrão solicitado. O modo Teclado habilita
        # um cursor de grade próprio sem alterar as regras de posicionamento.
        self.control_mode = "mouse"
        self.integration_preview = bool(integration_preview)
        self.gpu_preload_queue: list[pygame.Surface] = []
        self.gpu_preloaded = 0
        self.gpu_queue_ready = False
        self.running = True
        self.scene = "loading"
        self.scene_elapsed = 0.0
        self.save = load_save()
        self.region = "city"
        self.difficulty = "medium"
        self.selection: list[tuple[str, str]] = []
        self.battle: Battle | None = None
        self.dossier_kind = "units"
        self.dossier_page = 0
        self.character_region = "city"
        self.character_index = 0
        self.selection_carousel_index = 0
        self.selection_inspect_key: str | None = None
        self.story_page = 0
        self.hover_card: tuple[str, str] | None = None

    def _create_display(self) -> pygame.Surface:
        """Usa CPU/RAM por padrão; OpenGL só existe como opção explícita."""
        requested = os.environ.get("SVZ_RENDERER", "software").strip().lower()
        dummy_driver = os.environ.get("SDL_VIDEODRIVER", "").strip().lower() == "dummy"
        if requested in {"opengl", "gpu"} and not dummy_driver:
            try:
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
                pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
                pygame.display.set_mode(
                    (WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF
                )
                presenter = OpenGLPresenter(WIDTH, HEIGHT)
                self.presenter = presenter
                self.renderer_label = presenter.info.label
                self.overlay_surface = pygame.Surface(
                    (WIDTH, HEIGHT), pygame.SRCALPHA, 32
                )
                return pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA, 32)
            except Exception as exc:  # driver ausente ou OpenGL muito antigo
                self.renderer_error = f"{type(exc).__name__}: {exc}"
                if self.presenter is not None:
                    self.presenter.close()
                    self.presenter = None
                pygame.display.quit()
                pygame.display.init()
                pygame.display.set_caption(f"Soldados vs Zumbis — {VERSION}")
        display = pygame.display.set_mode((WIDTH, HEIGHT))
        self.renderer_label = "SOFTWARE · CPU/RAM"
        self.overlay_surface = None
        return display

    def present_frame(self) -> None:
        """Entrega o quadro ao compositor escolhido sem duplicar a lógica."""
        if self.presenter is None:
            pygame.display.flip()
            return
        tint = REGIONS.get(
            self.battle.region if self.battle else self.region, REGIONS["city"]
        )["accent"]
        self.presenter.present(
            self.world_surface,
            actors=self.actor_commands,
            overlay=self.overlay_surface,
            elapsed=self.scene_elapsed,
            tint=tint,
            strength=1.0 if self.scene == "battle" else 0.42,
        )

    def run(self) -> None:
        try:
            while self.running:
                dt = min(0.05, self.clock.tick(FPS) / 1000.0)
                self.scene_elapsed += dt
                self.handle_events()
                self.update(dt)
                self.draw()
                self.present_frame()
        finally:
            if self.presenter is not None:
                self.presenter.close()
            pygame.quit()

    def update(self, dt: float) -> None:
        self.audio.sync(
            self.scene,
            self.battle.region if self.scene == "battle" and self.battle else None,
        )
        self.scenario_runtime.update(
            dt, self.battle if self.scene == "battle" else None
        )
        if self.scene == "loading":
            if not self.assets.complete:
                self.assets.load_next()
            if self.assets.complete:
                self.assets.prepare_production_animations()
                if self.presenter is not None:
                    if not self.gpu_queue_ready:
                        self.gpu_preload_queue = self.assets.actor_sources()
                        self.gpu_queue_ready = True
                    batch_end = min(len(self.gpu_preload_queue), self.gpu_preloaded + 8)
                    if batch_end > self.gpu_preloaded:
                        self.presenter.preload_sprites(
                            self.gpu_preload_queue[self.gpu_preloaded : batch_end]
                        )
                        self.gpu_preloaded = batch_end
                    if self.gpu_preloaded < len(self.gpu_preload_queue):
                        return
                # Mesmo o executável de integração começa no menu INICIAR.
                # O sinalizador mantém as ondas reduzidas, mas nunca pula a
                # navegação escolhida pelo jogador nem abre o mapa sozinho.
                self.scene = "title"
                self.scene_elapsed = 0
        elif self.scene == "battle" and self.battle:
            self.battle.update(dt)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self.hover_card = None

    def handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.scene == "title":
                self.running = False
            elif self.scene == "battle":
                self.leave_battle_to_title()
            else:
                self.scene = "title"
            return
        if self.scene == "title" and key in (pygame.K_RETURN, pygame.K_SPACE):
            self.scene = "difficulty"
        elif self.scene == "difficulty" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.difficulty = ("easy", "medium", "hard")[key - pygame.K_1]
            self.scene = "campaign"
        elif self.scene == "campaign" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            target = ("city", "desert", "beach")[key - pygame.K_1]
            self.enter_selection(target)
        elif self.scene == "characters" and key in (pygame.K_LEFT, pygame.K_RIGHT):
            keys = self.character_keys()
            if keys:
                delta = -1 if key == pygame.K_LEFT else 1
                self.character_index = (self.character_index + delta) % len(keys)
        elif self.scene == "settings":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_c):
                self.control_mode = (
                    "keyboard" if self.control_mode == "mouse" else "mouse"
                )
                self.audio.play("ui")
            elif key == pygame.K_m:
                self.audio.set_enabled(not self.audio.enabled)
                self.audio.play("ui")
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.audio.set_volume(self.audio.volume - 0.10)
                self.audio.play("ui")
            elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.audio.set_volume(self.audio.volume + 0.10)
                self.audio.play("ui")
        elif self.scene == "battle" and self.battle:
            if pygame.K_1 <= key <= pygame.K_8:
                choice = key - pygame.K_1
                if choice < len(self.battle.selected):
                    self.battle.selected_card = choice
                    self.battle.remove_mode = False
                    self.audio.play("ui")
            elif self.control_mode == "keyboard" and key in (
                pygame.K_LEFT,
                pygame.K_a,
                pygame.K_RIGHT,
                pygame.K_d,
                pygame.K_UP,
                pygame.K_w,
                pygame.K_DOWN,
                pygame.K_s,
            ):
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.battle.keyboard_col = max(0, self.battle.keyboard_col - 1)
                elif key in (pygame.K_RIGHT, pygame.K_d):
                    self.battle.keyboard_col = min(
                        LAST_PLACEABLE_COLUMN,
                        self.battle.keyboard_col + 1,
                    )
                elif key in (pygame.K_UP, pygame.K_w):
                    self.battle.keyboard_row = max(0, self.battle.keyboard_row - 1)
                else:
                    self.battle.keyboard_row = min(
                        ROWS - 1, self.battle.keyboard_row + 1
                    )
                self.audio.play("ui", min_interval_ms=45)
            elif self.control_mode == "keyboard" and key in (pygame.K_q, pygame.K_e):
                direction = -1 if key == pygame.K_q else 1
                count = len(self.battle.selected)
                self.battle.selected_card = (
                    self.battle.selected_card + direction
                ) % count
                self.battle.remove_mode = False
                self.audio.play("ui")
            elif self.control_mode == "keyboard" and key in (
                pygame.K_RETURN,
                pygame.K_f,
                pygame.K_SPACE,
            ):
                if self.battle.remove_mode:
                    self.battle.remove_defender(
                        self.battle.keyboard_row, self.battle.keyboard_col
                    )
                elif self.battle.card_cooldowns[self.battle.selected_card] <= 0:
                    self.battle.place(
                        self.battle.keyboard_row, self.battle.keyboard_col
                    )
                else:
                    self.battle.announce(
                        "Esta carta ainda está recarregando.", 1.3, GRAY
                    )
            elif self.control_mode == "keyboard" and key in (pygame.K_n, pygame.K_TAB):
                if not self.battle.started_wave:
                    self.battle.intermission = 0
                    self.battle.start_next_wave()
                else:
                    self.battle.announce(
                        "A horda atual ainda está em andamento.", 1.3, GRAY
                    )
            elif key == pygame.K_r and self.battle.difficulty != "easy":
                self.battle.remove_mode = not self.battle.remove_mode
                self.battle.announce(
                    (
                        "Voltar à base: clique na tropa que deseja recolher."
                        if self.battle.remove_mode
                        else "Retorno à base desativado."
                    ),
                    1.4,
                    TEAL,
                )
            elif key == pygame.K_p:
                self.battle.paused = not self.battle.paused
                self.battle.announce(
                    "Partida pausada." if self.battle.paused else "Partida retomada.",
                    1.4,
                    GOLD,
                )
            elif (
                self.control_mode == "mouse"
                and key == pygame.K_SPACE
                and not self.battle.started_wave
            ):
                self.battle.intermission = 0
                self.battle.start_next_wave()
            elif self.battle.finished and key == pygame.K_RETURN:
                self.finish_battle()

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.scene == "loading":
            return
        if self.scene != "battle":
            self.audio.play("ui", min_interval_ms=55)
        if self.scene == "title":
            self.click_title(pos)
        elif self.scene == "difficulty":
            self.click_difficulty(pos)
        elif self.scene == "campaign":
            self.click_campaign(pos)
        elif self.scene == "characters":
            self.click_characters(pos)
        elif self.scene == "story":
            self.click_story(pos)
        elif self.scene == "settings":
            if self.settings_control_rect().collidepoint(pos):
                self.control_mode = (
                    "keyboard" if self.control_mode == "mouse" else "mouse"
                )
            elif self.settings_sound_rect().collidepoint(pos):
                self.audio.set_enabled(not self.audio.enabled)
            elif self.settings_volume_minus_rect().collidepoint(pos):
                self.audio.set_volume(self.audio.volume - 0.10)
            elif self.settings_volume_plus_rect().collidepoint(pos):
                self.audio.set_volume(self.audio.volume + 0.10)
            elif self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
        elif self.scene.startswith("dossier"):
            self.click_dossier(pos)
        elif self.scene == "howto":
            if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
        elif self.scene == "battle" and self.battle:
            if self.battle.finished:
                if pygame.Rect(
                    WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50
                ).collidepoint(pos):
                    self.finish_battle()
            else:
                self.battle.handle_click(pos)

    def title_buttons(self) -> list[tuple[str, pygame.Rect]]:
        return [
            ("INICIAR", pygame.Rect(62, 276, 274, 52)),
            ("PERSONAGENS", pygame.Rect(62, 338, 274, 48)),
            ("HISTÓRIA DO JOGO", pygame.Rect(62, 396, 274, 48)),
            ("CONFIGURAÇÕES", pygame.Rect(62, 454, 274, 48)),
            ("COMO JOGAR", pygame.Rect(62, 512, 274, 44)),
            ("SAIR", pygame.Rect(62, 566, 274, 40)),
        ]

    @staticmethod
    def settings_control_rect() -> pygame.Rect:
        return pygame.Rect(505, 245, 270, 48)

    @staticmethod
    def settings_sound_rect() -> pygame.Rect:
        return pygame.Rect(505, 326, 270, 48)

    @staticmethod
    def settings_volume_minus_rect() -> pygame.Rect:
        return pygame.Rect(505, 407, 64, 44)

    @staticmethod
    def settings_volume_plus_rect() -> pygame.Rect:
        return pygame.Rect(711, 407, 64, 44)

    def click_title(self, pos: tuple[int, int]) -> None:
        for label, rect in self.title_buttons():
            if not rect.collidepoint(pos):
                continue
            if label == "INICIAR":
                self.scene = "difficulty"
            elif label == "PERSONAGENS":
                self.scene, self.dossier_kind, self.character_region = (
                    "characters",
                    "units",
                    "city",
                )
            elif label == "HISTÓRIA DO JOGO":
                self.scene, self.story_page = "story", 0
            elif label == "CONFIGURAÇÕES":
                self.scene = "settings"
            elif label == "COMO JOGAR":
                self.scene = "howto"
            elif label == "SAIR":
                self.running = False

    def click_characters(self, pos: tuple[int, int]) -> None:
        for index, region in enumerate(("city", "desert", "beach")):
            if pygame.Rect(340 + index * 205, 82, 190, 42).collidepoint(pos):
                self.character_region = region
                self.character_index = 0
                return
        if pygame.Rect(424, 136, 205, 40).collidepoint(pos):
            self.dossier_kind = "units"
            self.character_index = 0
            return
        if pygame.Rect(650, 136, 205, 40).collidepoint(pos):
            self.dossier_kind = "zombies"
            self.character_index = 0
            return
        keys = self.character_keys()
        if keys and pygame.Rect(260, 184, 180, 40).collidepoint(pos):
            self.character_index = (self.character_index - 1) % len(keys)
            return
        if keys and pygame.Rect(WIDTH - 440, 184, 180, 40).collidepoint(pos):
            self.character_index = (self.character_index + 1) % len(keys)
            return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def character_keys(self) -> list[str]:
        if self.dossier_kind == "units":
            return [key for key, _display in REGION_ROSTERS[self.character_region]]
        # O dossiê mostra o elenco completo que realmente participa das 12
        # ondas: seis comuns, três subchefes e três chefes regionais.
        return list(
            REGION_ENEMIES[self.character_region]
            + REGION_SUBBOSSES[self.character_region]
            + REGION_BOSSES[self.character_region]
        )

    def click_story(self, pos: tuple[int, int]) -> None:
        if pygame.Rect(245, 646, 170, 44).collidepoint(pos):
            self.story_page = max(0, self.story_page - 1)
        elif pygame.Rect(WIDTH - 415, 646, 170, 44).collidepoint(pos):
            self.story_page = min(2, self.story_page + 1)
        elif self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def difficulty_buttons(self) -> list[tuple[str, pygame.Rect]]:
        return [
            ("easy", pygame.Rect(80, 500, 320, 48)),
            ("medium", pygame.Rect(480, 500, 320, 48)),
            ("hard", pygame.Rect(880, 500, 320, 48)),
        ]

    def click_difficulty(self, pos: tuple[int, int]) -> None:
        for key, rect in self.difficulty_buttons():
            if rect.collidepoint(pos):
                self.difficulty = key
                self.scene = "campaign"
                return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def click_campaign(self, pos: tuple[int, int]) -> None:
        for index, region in enumerate(("city", "desert", "beach")):
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            if rect.collidepoint(pos):
                self.enter_selection(region)
                return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def enter_selection(self, region: str) -> None:
        self.region = region
        # Não há mais uma etapa de seleção pré-partida. Cada mapa entrega sua
        # equipe regional completa de oito cartas e inicia imediatamente.
        available = self.available_selection_keys(region)
        self.selection = [
            (key, self.card_display_name(region, key)) for key in available[:8]
        ]
        self.selection_carousel_index = 0
        self.selection_inspect_key = None
        self.hover_card = None
        self.battle = Battle(self, region, self.selection[:])
        self.scene = "battle"

    @staticmethod
    def _unique_keys(keys: list[str]) -> list[str]:
        seen: set[str] = set()
        return [key for key in keys if not (key in seen or seen.add(key))]

    def regional_card_keys(self, region: str) -> list[str]:
        """A produção atual expõe somente o personagem já redesenhado."""
        return [key for key, _display in REGION_ROSTERS[region]]

    def available_selection_keys(self, region: str | None = None) -> list[str]:
        region = region or self.region
        return self.regional_card_keys(region)

    @staticmethod
    def card_display_name(region: str, key: str) -> str:
        for roster_key, display in REGION_ROSTERS[region]:
            if roster_key == key:
                return display
        return str(DEFENSES[key]["base"])

    def selection_cards(self) -> list[tuple[str, str, pygame.Rect]]:
        """Restaura a grade compacta usada antes de iniciar a partida."""
        keys = self.available_selection_keys()
        cards: list[tuple[str, str, pygame.Rect]] = []
        for index, key in enumerate(keys):
            row = index // 5
            column = index % 5
            row_count = min(5, len(keys) - row * 5)
            row_width = row_count * 238 + max(0, row_count - 1) * 12
            x = (WIDTH - row_width) // 2 + column * 250
            y = 96 + row * 230
            cards.append(
                (
                    key,
                    self.card_display_name(self.region, key),
                    pygame.Rect(x, y, 238, 215),
                )
            )
        return cards

    @staticmethod
    def selection_inspect_button(card_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            card_rect.x + 119, card_rect.bottom - 39, card_rect.width - 129, 27
        )

    @staticmethod
    def selection_inspection_close_rect() -> pygame.Rect:
        return pygame.Rect(WIDTH // 2 - 105, 552, 210, 42)

    def click_selection(self, pos: tuple[int, int]) -> None:
        if self.selection_inspect_key is not None:
            if self.selection_inspection_close_rect().collidepoint(pos):
                self.selection_inspect_key = None
            return
        for key, display, rect in self.selection_cards():
            if self.selection_inspect_button(rect).collidepoint(pos):
                self.selection_inspect_key = key
                return
            if not rect.collidepoint(pos):
                continue
            item = (key, display)
            if item in self.selection:
                self.selection.remove(item)
            elif len(self.selection) < 3:
                self.selection.append(item)
            return
        launch = pygame.Rect(WIDTH - 290, 650, 240, 46)
        if launch.collidepoint(pos):
            if 1 <= len(self.selection) <= 3:
                self.battle = Battle(self, self.region, self.selection[:])
                self.scene = "battle"
            else:
                return
        if self.button_rect("Voltar", 45, 650, 160, 46).collidepoint(pos):
            self.scene = "campaign"

    def dossier_items(self) -> list[dict]:
        if self.dossier_kind == "units":
            regional_keys = set(self.regional_card_keys(self.region))
            items = [
                {"kind": "evolution", "l1": l1, "l2": l2}
                for l1, l2 in PROMOTIONS.items()
                if l1 in regional_keys and l2 in regional_keys
            ]
            if "instrutor" in regional_keys and self.difficulty == "hard":
                items.append({"kind": "promoter", "key": "instrutor"})
            return items
        return [
            {
                "name": data["name"],
                "sub": "Chefe" if key in BOSSES else "Inimigo",
                "ability": data["ability"],
                "hp": int(data["hp"]),
                "key": key,
            }
            for key, data in {**ENEMIES, **BOSSES}.items()
        ]

    def click_dossier(self, pos: tuple[int, int]) -> None:
        if self.button_rect("Voltar", 40, 648, 160, 42).collidepoint(pos):
            self.scene = "title"
            return
        if pygame.Rect(WIDTH - 180, 648, 140, 42).collidepoint(pos):
            items = self.dossier_items()
            pages = max(1, math.ceil(len(items) / 6))
            self.dossier_page = (self.dossier_page + 1) % pages

    def finish_battle(self) -> None:
        if not self.battle:
            self.scene = "campaign"
            return
        if self.battle.victory:
            region = self.battle.region
            if region not in self.save["completed"]:
                self.save["completed"].append(region)
            self.save["unlocked"] = list(REGIONS)
            self.save["best_wave"][region] = max(
                self.save["best_wave"].get(region, 0), TOTAL_WAVES
            )
            save_campaign(self.save)
        self.battle = None
        self.scene = "campaign"

    def leave_battle_to_title(self) -> None:
        """Saída voluntária sem registrar vitória, derrota ou progresso falso."""
        self.battle = None
        self.scene = "title"
        self.scene_elapsed = 0.0


from src.game.entities import (
    Defender,
    Enemy,
    FloatingText,
    LaneBomb,
    Particle,
    Projectile,
    SpawnOrder,
)
from src.game.assets import Assets, FontBook
from src.game.battle import Battle
from src.game.presentation import attach_presentation_methods

attach_presentation_methods(Game)
del attach_presentation_methods

def main():
    """Ponto de entrada do jogo Soldados vs Zumbis."""
    if "--verificar-pacote" in sys.argv[1:]:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        os.environ.setdefault("SVZ_RENDERER", "software")
        game = Game()
        for _ in range(game.assets.total + 8):
            game.update(1 / FPS)
            game.draw()
            if game.scene == "title":
                break
        if game.scene != "title" or not game.assets.complete:
            raise RuntimeError(
                "O pacote nao conseguiu carregar as artes e o menu inicial"
            )
        pygame.quit()
        marker_path = os.environ.get("SVZ_PACKAGE_CHECK_FILE")
        if marker_path:
            Path(marker_path).write_text("PACOTE_OK", encoding="utf-8")
        if sys.stdout is not None:
            print("PACOTE_OK", flush=True)
    else:
        Game(integration_preview="--integracao-beta4" in sys.argv[1:]).run()


if __name__ == "__main__":
    main()
