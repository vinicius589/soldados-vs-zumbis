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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pygame

from animation2d import AnimationManager
from beta4_expansion_roster import EXPANSION_DEFENDERS
from beta4_production_animations import build_production_clips, new_production_animation
from beta4_scenario_runtime import ScenarioRuntime
from opengl_presenter import ActorCommand, OpenGLPresenter
from visual_layout import (
    DEFENDER_WEAPON_PROFILES,
    ENEMY_ATTACK_ORIGINS,
    ENEMY_BODY_LAYOUTS,
    PROJECTILE_LAUNCH_GAPS,
    PROJECTILE_LAYOUTS,
    defender_layout,
)


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "v7"
PRODUCTION_ASSET_DIR = ROOT / "assets" / "beta4_producao"
AUDIO_DIR = ROOT / "assets" / "audio_beta4"
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
BEACH_WATER_DEFENDERS = frozenset({"lancha", "submarino", "barco_patrulha", "submarino_tatico"})
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


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


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


def enemy_wave_scale(wave: int) -> float:
    """Mantém as primeiras ondas acolhedoras e endurece a reta final.

    A versão anterior começava com vida cheia e liberava ameaças depressa;
    assim, o primeiro contato parecia mais duro que a metade da campanha.
    """
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.66 + 1.50 * progress ** 1.55


def enemy_damage_scale(wave: int) -> float:
    """Escala separada para que o fim não seja só uma esponja de vida."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.62 + 1.10 * progress ** 1.50


def boss_wave_scale(wave: int) -> float:
    """Chefes escalam com a campanha sem virar paredes de vida.

    Um chefe deve mudar a montagem da linha, não exigir uma composição
    perfeita ou prender o jogador numa sequência infinita de atordoamentos.
    Por isso sua vida cresce mais devagar que a de uma horda comum.
    """
    # Chefes mantêm sua identidade, mas precisam cair com uma montagem boa
    # antes que a contenção de última linha vire o único plano viável.
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.78 + 1.25 * progress ** 1.40


def boss_damage_scale(wave: int) -> float:
    """Contém o dano físico dos chefes nas ondas altas."""
    progress = clamp((wave - 1) / max(1, TOTAL_WAVES - 1), 0.0, 1.0)
    return 0.70 + 0.95 * progress ** 1.45


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
            _data["role"] not in {"shotgun", "flame", "waterjet", "suicide_bomber", "shield", "blade"},
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
    "xerife_rua": ("Patrulha Básica", 1, "Tiro forte e recarga curta por baixo custo.", "Alcance curto e não atravessa aliados."),
    "agente_swat": ("SWAT de Supressão", 1, "Rajada atravessa a formação aliada.", "Dano por projétil baixo e recarga longa."),
    "operador_radio_policial": ("Comando e Logística", 1, "Gera suprimentos durante a onda sem exigir outra carta.", "Não ataca e precisa ser protegido."),
    "atirador_precisao_swat": ("SWAT de Observação", 1, "Prioriza alvos de maior vida.", "Cadência baixa e fraco contra enxames."),
    "agente_entrada": ("Tropa de Choque", 1, "Leque devastador à queima-roupa.", "Só cobre a casa imediatamente à frente."),
    "especialista_antipraga": ("Unidade Antipraga", 2, "A nuvem química corrói blindagem biológica e contamina grupos.", "Ocupa duas casas, usa tambor de seis granadas e recarrega lentamente."),
    "lancador_foguetes": ("Resposta Pesada", 2, "Explosão quebra grupos e blindados.", "Ocupa duas casas, um disparo e recarga longa."),
    "escudeiro_tropa_choque": ("Tropa de Choque", 1, "Interrompe a primeira investida recebida.", "Corpo a corpo e sem resposta a atacantes distantes."),
}
for _key, (_unit, _space, _advantage, _disadvantage) in CITY_TACTICAL_UNITS.items():
    DEFENSES[_key]["tactical_unit"] = _unit
    DEFENSES[_key]["footprint"] = _space
    DEFENSES[_key]["situational_advantage"] = _advantage
    DEFENSES[_key]["situational_disadvantage"] = _disadvantage
    DEFENSES[_key]["ability"] = f"{DEFENSES[_key]['ability']} Unidade {_unit}: {_advantage} Limite: {_disadvantage}"


# Índices de atlas por carta, região e nível. Eles não podem ser inferidos
# apenas pelo "papel" da unidade: as três folhas de arte têm ordens próprias
# e uma célula N1 não representa automaticamente sua evolução N2. Esta é a
# única fonte usada pela seleção, pelo HUD, pelo dossiê e pela tropa em campo.
CARD_ATLAS_INDEX = {
    "city": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "bombardeiro": 5, "granadeiro": 5,
        "morteiro_basico": 5, "morteiro": 5,
        "radio": 7, "torre_radio": 7,
        "lanca_chamas_bolso": 9, "lanca_chamas": 9,
        "lancador_veneno": 9, "canhao_veneno": 9,
        "barreira": 10, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
    },
    "desert": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "morteiro_basico": 5, "morteiro": 5,
        "bombardeiro": 6, "granadeiro": 5,
        "radio": 8, "torre_radio": 7,
        "lanca_chamas_bolso": 10, "lanca_chamas": 9,
        "barreira": 11, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
    },
    "beach": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "morteiro_basico": 5, "morteiro": 5,
        "bombardeiro": 7, "granadeiro": 5,
        "radio": 9, "torre_radio": 7,
        "lancador_agua": 9, "canhao_mare": 9,
        "barreira": 11, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
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
ENEMIES.update({
    "policial_helix": {
        "name": "Policial Infectado da Félix",
        "hp": 218, "speed": 9.2, "damage": 18, "attack": 1.05, "sprite": 3,
        "armor": 0.34, "tags": ("shield",),
        "ability": "Colete e capacete absorvem os primeiros tiros; corrosão e precisão quebram a proteção.",
    },
    "cientista_helix": {
        "name": "Cientista da Félix",
        "hp": 164, "speed": 9.5, "damage": 15, "attack": 1.15, "sprite": 6,
        "tags": ("acid",),
        "ability": "O cilindro rompido lança composto corrosivo a até três blocos, sem qualquer poder sobrenatural.",
    },
    "tecnico_subestacao": {
        "name": "Técnico da Subestação",
        "hp": 176, "speed": 11.0, "damage": 16, "attack": 1.05, "sprite": 8,
        "tags": ("shock",),
        "ability": "Baterias presas ao corpo descarregam um pulso curto que atrasa a tropa mais próxima.",
    },
    "arqueiro_necropole": {
        "name": "Arqueiro da Necrópole",
        "hp": 152, "speed": 10.8, "damage": 17, "attack": 1.08, "sprite": 3,
        "tags": ("gun",),
        "ability": "Ataca à distância com um arco físico preservado; é perigoso, mas possui pouca vida.",
    },
    "hospedeiro_escaravelhos": {
        "name": "Hospedeiro de Escaravelhos",
        "hp": 238, "speed": 8.2, "damage": 21, "attack": 1.12, "sprite": 7,
        "armor": 0.16, "tags": ("explode_death",),
        "ability": "A colônia alterada no torso se espalha no impacto final e pune tropas amontoadas.",
    },
    "saqueador_canopico": {
        "name": "Saqueador Canópico",
        "hp": 146, "speed": 13.0, "damage": 12, "attack": 1.18, "sprite": 3,
        "tags": ("steal",),
        "ability": "Prioriza a retaguarda e rouba uma pequena carga de suprimentos usando recipientes da escavação.",
    },
    "pescador_praga": {
        "name": "Pescador da Praga",
        "hp": 186, "speed": 10.4, "damage": 18, "attack": 1.10, "sprite": 6,
        "tags": ("net",), "amphibious": True,
        "ability": "Lança uma rede contaminada que reduz por instantes a cadência da defesa mais próxima.",
    },
    "baiacu_mutante": {
        "name": "Baiacu Mutante",
        "hp": 520, "speed": 6.8, "damage": 36, "attack": 1.12, "sprite": 9,
        "armor": 0.28, "tags": ("explode_death", "stomp"),
        "ability": "Subchefe aquático: infla sob fogo e espalha espinhos somente na própria faixa ao ser abatido.",
    },
})

ENEMIES["bruto"].update({
    "name": "Demolidor do Metrô",
    "ability": "Subchefe industrial: marreta duas casas próximas e exige contenção antes do contato.",
})
ENEMIES["divisor"].update({
    "name": "Bruto da Quarentena",
    "ability": "Subchefe dentro de um traje Félix rompido; as placas reduzem explosões frontais.",
})
ENEMIES["policial"].update({
    "name": "Comandante Infectado",
    "ability": "Subchefe policial mutado: coordena a faixa e dispara rajadas curtas contra a retaguarda.",
})
ENEMIES["parasita"].update({
    "name": "Guardião do Sarcófago",
    "ability": "Escudo funerário contaminado desvia fogo frontal até o Guardião de Lâminas abrir sua postura.",
})
ENEMIES["curandeiro"].update({
    "name": "Sacerdote da Praga",
    "ability": "Incensário químico restaura tecido infectado próximo; o Incinerador interrompe a regeneração.",
})
ENEMIES["mutante"].update({
    "name": "Executor da Escavação",
    "ability": "Subchefe pesado fundido a ferramentas do sítio; golpeia o chão e quebra formações compactas.",
})
ENEMIES["salva_vidas"].update({
    "name": "Salva-Vidas Colossal",
    "ability": "Subchefe anfíbio: investida de resgate mutada derruba a cadência das tropas na própria faixa.",
})
ENEMIES["cacador"].update({
    "name": "Caçador das Profundidades",
    "ability": "Subchefe de mergulho blindado que avança com arpão; sonar e precisão naval expõem suas placas.",
})


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

BOSSES["bruto_demolidor"].update({
    "counter_keys": ("agente_entrada", "escudeiro_tropa_choque"),
    "counter_label": "Tropa de Choque",
})
BOSSES["necromante"].update({
    "weaknesses": {"thermal": 1.45},
    "counter_label": "Incinerador do Deserto",
})
BOSSES["leviata"].update({
    "weaknesses": {"piercing": 1.55},
    "counter_label": "Submarino Tático",
})


REGION_ENEMIES = {
    "city": (
        "infectado_urbano", "corredor_cidade", "rastejador_cidade",
        "policial_helix", "cientista_helix", "tecnico_subestacao",
    ),
    "desert": (
        "desperto_khepra", "corredor_deserto", "rastejador_deserto",
        "arqueiro_necropole", "hospedeiro_escaravelhos", "saqueador_canopico",
    ),
    "beach": (
        "afogado_cachoeira", "corredor_cachoeira", "rastejador_cachoeira",
        "surfista", "mergulhador", "pescador_praga",
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
        SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


class FontBook:
    def __init__(self) -> None:
        self.title = pygame.font.SysFont("arial", 45, bold=True)
        self.h1 = pygame.font.SysFont("arial", 28, bold=True)
        self.h2 = pygame.font.SysFont("arial", 20, bold=True)
        self.body = pygame.font.SysFont("arial", 16)
        self.small = pygame.font.SysFont("arial", 13)
        self.tiny = pygame.font.SysFont("arial", 11)


class Assets:
    """Carrega uma única fonte por quadro para manter a abertura leve."""

    def __init__(self) -> None:
        self.images: dict[str, pygame.Surface] = {}
        self.unit_sprites: dict[str, list[pygame.Surface]] = {}
        self.unit_l2_sprites: dict[str, list[pygame.Surface]] = {}
        self.zombie_sprites: dict[str, list[pygame.Surface]] = {}
        self.animation_frames: dict[str, list[pygame.Surface]] = {}
        self.effect_frames: dict[str, list[pygame.Surface]] = {}
        self.boss_portraits: dict[str, list[pygame.Surface]] = {}
        self.scale_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self.trim_cache: dict[int, pygame.Surface] = {}
        self.production_clips: dict[str, dict] | None = None
        # Somente telas, cenários já aprovados e VFX genéricos são carregados
        # aqui. Todo atlas antigo de soldado, zumbi ou chefe foi retirado da
        # produção; os atores ativos vêm exclusivamente de
        # ``assets/beta4_producao`` (elenco regional completo e doze ameaças por
        # região na integração jogável atual).
        self.jobs: list[tuple[str, Path, str]] = [
            ("loading_beta3", ASSET_DIR / "loading_beta3_reference.png", "image"),
            ("menu", ASSET_DIR / "menu.png", "image"),
            *[
                (f"{region}_bg", ASSET_DIR / info["bg"], "image")
                for region, info in REGIONS.items()
            ],
            ("elemental_effects", ASSET_DIR / "elemental_effects_sheet_beta4_v2.png", "effects_4x3"),
            ("combat_effects", ASSET_DIR / "combat_effects_sheet_beta4.png", "effects_4x3"),
            ("ability_effects", ASSET_DIR / "ability_effects_sheet_beta4.png", "effects_4x3"),
            ("projectile_sprites", ASSET_DIR / "projectile_sprites_sheet_beta4.png", "effects_4x3"),
            ("city_boss_portraits", PRODUCTION_ASSET_DIR / "city_boss_portraits_3x1_v1.png", "portraits_3x1"),
            ("desert_boss_portraits", PRODUCTION_ASSET_DIR / "desert_boss_portraits_3x1_v1.png", "portraits_3x1"),
            ("beach_boss_portraits", PRODUCTION_ASSET_DIR / "beach_boss_portraits_3x1_v1.png", "portraits_3x1"),
            ("muzzle_cycle", PRODUCTION_ASSET_DIR / "muzzle_cycle_source_v1.png", "animation_8x1"),
        ]
        self.loaded = 0
        self.error: str | None = None

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def complete(self) -> bool:
        return self.loaded >= self.total

    def load_next(self) -> None:
        if self.complete:
            return
        key, path, kind = self.jobs[self.loaded]
        try:
            source = pygame.image.load(str(path)).convert_alpha()
            if kind == "image":
                if key.endswith("_bg"):
                    self.images[key] = self.fit_four_lane_background(source, key.split("_")[0])
                else:
                    self.images[key] = pygame.transform.smoothscale(source, (WIDTH, HEIGHT))
            elif kind == "sprite":
                self.images[key] = source
            elif kind == "animation":
                self.animation_frames[key] = self.slice_grid(source, 4, 2)
            elif kind == "animation_4x3":
                self.animation_frames[key] = self.slice_grid(source, 4, 3)
            elif kind == "animation_8x1":
                self.animation_frames[key] = [
                    self.trim_alpha(frame) for frame in self.slice_grid(source, 8, 1)
                ]
            elif kind == "portraits_3x1":
                region = key.split("_")[0]
                self.boss_portraits[region] = [
                    self.portrait_actor(frame) for frame in self.slice_grid(source, 3, 1)
                ]
            elif kind == "effects_4x3":
                self.effect_frames[key] = [self.trim_alpha(frame) for frame in self.slice_grid(source, 4, 3)]
            else:
                sprites = self.slice_atlas(source)
                if kind == "units":
                    self.unit_sprites[key.split("_")[0]] = sprites
                elif kind == "units_l2":
                    self.unit_l2_sprites[key.split("_")[0]] = sprites
                else:
                    self.zombie_sprites[key.split("_")[0]] = sprites
        except pygame.error as exc:
            self.error = f"Falha ao carregar {path.name}: {exc}"
            # Um arquivo ausente gera mensagem explícita na tela de carga. O
            # fallback fica transparente para nunca fingir uma animação com
            # círculo, bloco colorido ou outro símbolo provisório.
            placeholder = pygame.Surface((1, 1), pygame.SRCALPHA)
            if kind == "image":
                self.images[key] = pygame.transform.smoothscale(placeholder, (WIDTH, HEIGHT))
            elif kind == "sprite":
                self.images[key] = placeholder
            elif kind == "animation":
                self.animation_frames[key] = [placeholder] * 8
            elif kind == "animation_4x3":
                self.animation_frames[key] = [placeholder] * 12
            elif kind == "animation_8x1":
                self.animation_frames[key] = [placeholder] * 8
            elif kind == "portraits_3x1":
                self.boss_portraits[key.split("_")[0]] = [placeholder] * 3
            elif kind == "effects_4x3":
                self.effect_frames[key] = [placeholder] * 12
            elif kind == "units":
                self.unit_sprites[key.split("_")[0]] = [placeholder] * 12
            elif kind == "units_l2":
                self.unit_l2_sprites[key.split("_")[0]] = [placeholder] * 12
            else:
                self.zombie_sprites[key.split("_")[0]] = [placeholder] * 12
        self.loaded += 1

    @staticmethod
    def fit_four_lane_background(source: pygame.Surface, region: str) -> pygame.Surface:
        """Preserva a continuidade da pintura final sem remontar faixas.

        Os novos cenários já foram produzidos em 1280x720 e seus limites estão
        descritos em ``LANE_BOUNDS``. Recortar e esticar bandas individualmente
        quebrava calçadas, pedras, água e a entrada dos zumbis.
        """
        if source.get_size() == (WIDTH, HEIGHT):
            return source.copy()
        return pygame.transform.smoothscale(source, (WIDTH, HEIGHT))

    @staticmethod
    def slice_atlas(source: pygame.Surface) -> list[pygame.Surface]:
        width, height = source.get_size()
        tiles: list[pygame.Surface] = []
        for row in range(3):
            for col in range(4):
                rect = pygame.Rect(col * width // 4, row * height // 3, width // 4, height // 3)
                tile = source.subsurface(rect).copy()
                if tile.get_flags() & pygame.SRCALPHA == 0:
                    tile.set_colorkey((0, 0, 0))
                tiles.append(tile)
        return tiles

    @staticmethod
    def slice_grid(source: pygame.Surface, columns: int, rows: int) -> list[pygame.Surface]:
        """Recorta uma folha regular preservando seu canal alfa original."""
        width, height = source.get_size()
        frames: list[pygame.Surface] = []
        for row in range(rows):
            for column in range(columns):
                rect = pygame.Rect(
                    column * width // columns,
                    row * height // rows,
                    width // columns,
                    height // rows,
                )
                frames.append(source.subsurface(rect).copy())
        return frames

    @staticmethod
    def trim_alpha(source: pygame.Surface) -> pygame.Surface:
        """Remove apenas a margem transparente de um VFX ou projétil."""
        bounds = source.get_bounding_rect(min_alpha=8)
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return source.subsurface(bounds).copy()

    @staticmethod
    def portrait_actor(source: pygame.Surface) -> pygame.Surface:
        """Mantém o chefe inteiro e descarta fragmentos soltos entre células."""
        mask = pygame.mask.from_surface(source, threshold=8)
        components = mask.connected_components(minimum=6)
        if not components:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        main = max(components, key=lambda component: component.count())
        main_rect = main.get_bounding_rects()[0]
        kept = pygame.Surface(source.get_size(), pygame.SRCALPHA)
        for component in components:
            rects = component.get_bounding_rects()
            if not rects:
                continue
            rect = rects[0]
            # Braços, armas e tubos podem ser componentes separados, porém
            # continuam próximos do corpo. Pedaços vindos do retrato vizinho
            # ficam colados à borda e longe da figura principal.
            gap_x = max(0, max(main_rect.left, rect.left) - min(main_rect.right, rect.right))
            gap_y = max(0, max(main_rect.top, rect.top) - min(main_rect.bottom, rect.bottom))
            touches_side = rect.left <= 1 or rect.right >= source.get_width() - 1
            if component is not main and (touches_side or gap_x > 18 or gap_y > 18):
                continue
            alpha = component.to_surface(
                setcolor=(255, 255, 255, 255),
                unsetcolor=(255, 255, 255, 0),
            )
            fragment = source.copy()
            fragment.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            kept.blit(fragment, (0, 0))
        bounds = kept.get_bounding_rect(min_alpha=8)
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return kept.subsurface(bounds).copy()

    def base_unit(self, region: str, index: int) -> pygame.Surface:
        sprites = self.unit_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def unit(self, region: str, index: int, level: int = 1) -> pygame.Surface:
        """N1 usa o atlas base; N2 recebe silhueta e uniforme próprios."""
        if level >= 2:
            sprites = self.unit_l2_sprites.get(region, [])
            if sprites:
                return sprites[index % len(sprites)]
        return self.base_unit(region, index)

    def zombie(self, region: str, index: int) -> pygame.Surface:
        sprites = self.zombie_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def scaled(self, sprite: pygame.Surface, width: float, height: float) -> pygame.Surface:
        """Evita redimensionar os mesmos retratos gigantes a cada quadro."""
        size = (max(1, int(width)), max(1, int(height)))
        key = (id(sprite), *size)
        cached = self.scale_cache.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(sprite, size)
            self.scale_cache[key] = cached
        return cached

    def trimmed(self, sprite: pygame.Surface) -> pygame.Surface:
        """Remove só a margem transparente do recorte usado no campo.

        Cartas continuam usando o enquadramento integral do atlas. Em batalha,
        o recorte justo garante que a última linha opaca da bota, roda ou casco
        coincida de verdade com a âncora do terreno.
        """
        key = id(sprite)
        cached = self.trim_cache.get(key)
        if cached is not None:
            return cached
        bounds = sprite.get_bounding_rect(min_alpha=8)
        if bounds.width <= 1 or bounds.height <= 1:
            self.trim_cache[key] = sprite
            return sprite
        bounds = bounds.inflate(4, 4).clip(sprite.get_rect())
        trimmed = sprite.subsurface(bounds).copy()
        self.trim_cache[key] = trimmed
        return trimmed

    def actor_sources(self) -> list[pygame.Surface]:
        """Lista exatamente os recortes que poderão virar atores OpenGL."""
        self.prepare_production_animations()
        candidates: list[pygame.Surface] = []
        for store in (self.unit_sprites, self.unit_l2_sprites, self.zombie_sprites, self.animation_frames):
            for sprites in store.values():
                candidates.extend(sprites)
        for key, _path, kind in self.jobs:
            if kind == "sprite" and key != "beta4_toxic_impact" and key in self.images:
                candidates.append(self.images[key])
        if self.production_clips:
            for actor_clips in self.production_clips.values():
                for clip in actor_clips.values():
                    candidates.extend(clip.frames)
        unique: list[pygame.Surface] = []
        seen: set[int] = set()
        for sprite in candidates:
            trimmed = self.trimmed(sprite)
            if id(trimmed) not in seen:
                seen.add(id(trimmed))
                unique.append(trimmed)
        return unique

    def prepare_production_animations(self) -> None:
        """Pré-carrega somente as folhas novas do elenco jogável atual."""
        if self.production_clips is None:
            self.production_clips = build_production_clips()

    def new_production_animation(self, actor: str) -> AnimationManager:
        self.prepare_production_animations()
        assert self.production_clips is not None
        return new_production_animation(self.production_clips, actor)


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
        return pygame.Rect(int(self.x - width / 2), int(self.y - height), int(width), int(height + 12))

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
        scale = boss_wave_scale(self.wave) if self.key in BOSSES else enemy_wave_scale(self.wave)
        scale *= float(profile["boss_hp" if self.key in BOSSES else "enemy_hp"])
        self.hp = float(self.data["hp"]) * scale

    @property
    def y(self) -> float:
        return terrain_y(self.region, self.row, self.x)

    @property
    def max_hp(self) -> float:
        profile = difficulty_profile(self.difficulty)
        scale = boss_wave_scale(self.wave) if self.is_boss else enemy_wave_scale(self.wave)
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
        return pygame.Rect(int(self.x - width / 2), int(self.y - height), int(width), int(height + 10))


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


_EMITTER_CONTACT_CACHE: dict[tuple[int, float, float, float, float, int], tuple[float, float]] = {}


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
    if (
        layout.muzzle_cycle
        and animation is not None
        and animation.state == "shoot"
    ):
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
    if "stomp" in enemy.tags or "parasite" in enemy.tags or "explode_death" in enemy.tags:
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


class Battle:
    def __init__(self, app: "Game", region: str, selected: list[tuple[str, str]]) -> None:
        self.app = app
        self.region = region
        self.difficulty = getattr(app, "difficulty", "medium")
        self.difficulty_data = difficulty_profile(self.difficulty)
        valid_keys = {key for key, _display in REGION_ROSTERS.get(region, ())}
        self.selected = [item for item in selected if item[0] in valid_keys][:8]
        if not self.selected:
            fallback_key, fallback_display = REGION_ROSTERS[region][0]
            self.selected = [(fallback_key, fallback_display)]
        self.defenders: list[Defender] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.effects: list[VisualEffect] = []
        self.fallen: list[DefeatAnimation] = []
        # O suficiente para experimentar a primeira formação, mas sem tornar
        # a economia da campanha irrelevante.
        self.supplies = int(self.difficulty_data["initial_supplies"])
        self.wave = 0
        self.wave_banner = 0.0
        self.intermission = 2.5
        self.orders: list[SpawnOrder] = []
        self.spawn_timer = 0.0
        self.started_wave = False
        self.finished = False
        self.lost = False
        self.victory = False
        self.message = f"Modo {self.difficulty_data['label']}: posicione a equipe."
        self.message_timer = 4.0
        self.selected_card = 0
        self.remove_mode = False
        self.keyboard_row = 0
        self.keyboard_col = 1
        self.boss_seen: set[int] = set()
        self.ambient_phase = 0.0
        self.shake = 0.0
        self.global_toxic = 0.0
        self.boss_warning = 0.0
        self.boss_banner_name = ""
        self.boss_banner_subtitle = ""
        self.boss_alert_pending = False
        self.paused = False
        self.dead_history: list[tuple[str, int, float]] = []
        # Quatro faixas: AREIA, ÁGUA, ÁGUA, AREIA. As duas faixas centrais
        # dividem o canal contínuo pintado na nova Praia.
        self.water_rows = set(BEACH_WATER_ROWS) if region == "beach" else set()
        self.lane_bombs = [
            LaneBomb(row, x=lane_bomb_home_x(region, row)) for row in range(ROWS)
        ]
        self.card_cooldowns = [0.0 for _ in self.selected]

    def announce(self, message: str, seconds: float = 2.5, color: tuple[int, int, int] = WHITE) -> None:
        self.message = message
        self.message_timer = seconds
        # Alertas de interface são exibidos na aba superior. Assim eles não
        # atravessam as cartas nem reintroduzem uma faixa de texto na partida.

    def cell_is_water(self, row: int, col: int) -> bool:
        if self.region != "beach":
            return False
        # As duas linhas centrais pertencem ao canal da Praia.
        return row in self.water_rows

    def ground_cell_rect(self, row: int, col: int) -> pygame.Rect:
        return cell_rect(row, col, self.region).inflate(-14, -10)

    def board_cell_at(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """Traduz um clique somente quando ele está dentro da faixa pintada."""
        if not BOARD.left <= pos[0] <= BOARD.right:
            return None
        col = int(clamp((pos[0] - BOARD.left) / CELL_W, 0, COLS - 1))
        if col > LAST_PLACEABLE_COLUMN:
            return None
        for row in range(ROWS):
            top, bottom = lane_bounds(self.region, row)
            if top <= pos[1] < bottom or (row == ROWS - 1 and pos[1] == bottom):
                return row, col
        return None

    def card(self) -> tuple[str, str]:
        return self.selected[self.selected_card]

    def can_place(self, key: str, row: int, col: int) -> tuple[bool, str]:
        if not (0 <= row < ROWS and 0 <= col <= LAST_PLACEABLE_COLUMN):
            return False, "Fora da área de combate."
        data = DEFENSES[key]
        footprint = max(1, int(data.get("footprint", 1)))
        requested = set(range(col, col + footprint))
        if col + footprint > LAST_PLACEABLE_COLUMN + 1:
            return False, f"Esta Unidade ocupa {footprint} casas e não cabe nesse ponto."
        if any(
            d.row == row
            and requested.intersection(range(d.col, d.col + max(1, int(d.stats.get("footprint", 1)))))
            for d in self.defenders
        ):
            return False, "Este ponto já está ocupado."
        if LANE_PROTECTION_COLUMN in requested and self.lane_bombs[row].state != "spent":
            return False, "Casa reservada à contenção inicial desta faixa."
        water = self.cell_is_water(row, col)
        if data.get("water_only") and key not in BEACH_WATER_DEFENDERS:
            return False, "Esta unidade aquática pertence ao catálogo antigo e não entra na Beta 4."
        if key in BEACH_WATER_DEFENDERS and not water:
            return False, "Unidade aquática: só pode ser instalada nas faixas de água da Praia."
        if water and key not in BEACH_WATER_DEFENDERS:
            return False, "Canal exclusivo: posicione o Barco de Patrulha ou o Submarino Tático."
        if self.supplies < data["cost"]:
            return False, "Suprimentos insuficientes."
        return True, ""

    def place(self, row: int, col: int) -> None:
        key, display = self.card()
        allowed, reason = self.can_place(key, row, col)
        if not allowed:
            self.announce(reason, 1.7, RED)
            return
        data = DEFENSES[key]
        self.supplies -= data["cost"]
        sprite_index = regional_sprite_index(self.region, key)
        defender = Defender(key, display, row, col, data, sprite_index, region=self.region)
        actor_key = DEFENDER_ACTOR_BY_KEY.get(key)
        if actor_key:
            defender.visual_animation = self.app.assets.new_production_animation(actor_key)
            if data["role"] == "suicide_bomber":
                # Esta carta já nasce fixada na casa escolhida. Ela nunca corre,
                # salta ou desliza pelo mapa procurando um alvo.
                defender.visual_animation.play("idle", restart=True)
                defender.deployment_x = None
                defender.deployment_target_x = None
                defender.motion.loop("idle")
            else:
                defender.visual_animation.play("move", restart=True)
                defender.deployment_x = float(BOARD.left + 18)
                defender.deployment_target_x = defender.x
                defender.motion.loop("walk")
        self.defenders.append(defender)
        self.app.audio.play("place")
        # Toda carta retorna após o mesmo intervalo legível: não há exceção
        # por mapa, nível ou função, e a barra conta os 10 segundos completos.
        self.card_cooldowns[self.selected_card] = CARD_RECHARGE_SECONDS
        self.pulse(defender.x, defender.y, self.region_color(), 20)
        self.announce(f"{display} em posição.", 1.2, self.region_color())

    def remove_defender(self, row: int, col: int) -> None:
        """Retira uma defesa por escolha do jogador e devolve parte do custo."""
        if self.difficulty == "easy":
            self.announce("No Fácil, as tropas posicionadas não podem ser removidas.", 1.8, GRAY)
            return
        defender = next(
            (
                d for d in self.defenders
                if d.row == row
                and d.col <= col < d.col + max(1, int(d.stats.get("footprint", 1)))
            ),
            None,
        )
        if defender is None:
            self.announce("Nenhuma tropa nesta faixa para remover.", 1.4, GRAY)
            return
        self.defenders.remove(defender)
        refund = max(1, math.ceil(float(defender.stats["cost"]) * 0.35))
        self.supplies += refund
        self.pulse(defender.x, defender.y, (188, 206, 214), 12)
        self.announce(f"{defender.display_name} recolhido: +{refund} SUP.", 1.8, TEAL)

    def trigger_lane_bomb(self, row: int) -> bool:
        cart = self.lane_bombs[row]
        if cart.state != "armed":
            return False
        cart.x = lane_bomb_home_x(self.region, row)
        self.shake = max(self.shake, 0.16)
        label, color = self.lane_bomb_info(row)
        self.announce(f"{label} — faixa {row + 1} ativada!", 1.8, color)
        effect_y = lane_bomb_ground_y(self.region, row)
        self.pulse(cart.x + 24, effect_y, color, 16)
        if self.region == "beach":
            # Em Minas a proteção não percorre a pista: o primeiro contato
            # detona imediatamente uma cadeia que limpa a faixa inteira.
            cart.state = "spent"
            victims = [enemy for enemy in self.enemies[:] if enemy.row == row]
            for enemy in victims:
                if enemy in self.enemies:
                    self.take_enemy_damage(enemy, 99999, "explosion")
                    cart.kills += 1
            y = effect_y
            for x in range(LANE_BOMB_HOME_X + 35, LANE_PROTECTION_END_X["beach"], 112):
                self.explosion(float(x), y, color, 18, scale=0.84)
            return True
        cart.state = "rolling"
        cart.motion.loop("roll")
        return True

    def lane_bomb_info(self, row: int) -> tuple[str, tuple[int, int, int]]:
        """Retorna a contenção própria de cada terreno/faixa."""
        if self.region == "city":
            return "TRATOR DE CONTENÇÃO", GOLD
        if self.region == "desert":
            return "DRONE DE ATAQUE", (235, 181, 88)
        if row in self.water_rows:
            return "MINA AQUÁTICA", (95, 209, 236)
        return "CARGA TERRESTRE", (104, 201, 207)

    def lane_bomb_asset_key(self, row: int) -> str:
        if self.region == "city":
            return "lane_bomb_cart"
        if self.region == "desert":
            return "desert_lane_bomb_cart"
        return "beach_water_bomb" if row in self.water_rows else "beach_land_bomb_cart"

    def update_lane_bombs(self, dt: float) -> None:
        """Move o carrinho-bomba e limpa somente a faixa invadida uma vez."""
        for cart in self.lane_bombs:
            cart.motion.advance(dt, "roll" if cart.state == "rolling" else "armed")
            if cart.state != "rolling":
                continue
            previous_x = cart.x
            cart.x += 720 * dt
            y = cell_center(cart.row, 0, self.region)[1]
            for enemy in self.enemies[:]:
                swept_left = min(previous_x, cart.x) - 52
                swept_right = max(previous_x, cart.x) + 52
                if enemy.row == cart.row and swept_left <= enemy.x <= swept_right:
                    self.take_enemy_damage(enemy, 99999, "explosion")
                    cart.kills += 1
            if cart.x > LANE_PROTECTION_END_X[self.region]:
                cart.state = "spent"
                _, explosion_color = self.lane_bomb_info(cart.row)
                self.explosion(LANE_PROTECTION_END_X[self.region], y, explosion_color, 22)

    @staticmethod
    def menu_rect() -> pygame.Rect:
        return pygame.Rect(16, 126, 90, 34)

    @staticmethod
    def pause_rect() -> pygame.Rect:
        return pygame.Rect(112, 126, 92, 34)

    @staticmethod
    def remove_rect() -> pygame.Rect:
        return pygame.Rect(210, 126, 112, 34)

    @staticmethod
    def next_wave_rect() -> pygame.Rect:
        return pygame.Rect(328, 126, 168, 34)

    def start_next_wave(self) -> None:
        if self.wave >= TOTAL_WAVES:
            return
        self.wave += 1
        self.app.audio.play("wave", min_interval_ms=500)
        self.started_wave = True
        self.wave_banner = 3.0
        self.orders = self.build_wave(self.wave)
        self.spawn_timer = 0.35
        self.intermission = 0.0
        slot = (self.wave - 1) % 4 + 1
        chapter = (self.wave - 1) // 4
        if slot == 4:
            boss_key = REGION_BOSSES[self.region][chapter]
            self.boss_banner_name = BOSSES[boss_key]["name"]
            self.boss_banner_subtitle = "A ESCOLTA ABRE CAMINHO"
            self.announce(f"Onda {self.wave}: a escolta do chefe está a caminho.", 2.6, RED)
        elif slot == 3:
            subboss_key = REGION_SUBBOSSES[self.region][chapter]
            self.announce(f"Onda {self.wave}: SUB-BOSS {ENEMIES[subboss_key]['name']}.", 2.4, GOLD)
        else:
            self.announce(f"ONDA COMUM {self.wave}/{TOTAL_WAVES}", 2.0, WHITE)

    def build_wave(self, wave: int) -> list[SpawnOrder]:
        if getattr(self.app, "integration_preview", False):
            # O ensaio usa a mesma liberação progressiva da campanha. Assim a
            # revisão visual da onda 1 não apresenta antes da hora um inimigo
            # que o jogador só conhecerá nos atos seguintes.
            count = min(8, 2 + wave)
            enemy_keys = wave_enemy_pool(self.region, wave)
            return [
                SpawnOrder(
                    0.78 if index else 0.35,
                    enemy_keys[index % len(enemy_keys)],
                    self.spawn_row_for(enemy_keys[index % len(enemy_keys)]),
                )
                for index in range(count)
            ]
        pool = list(wave_enemy_pool(self.region, wave))
        orders: list[SpawnOrder] = []
        slot = (wave - 1) % 4 + 1
        chapter = (wave - 1) // 4
        # A curva começa com espaço para aprender e termina em pressão real.
        # Subchefes e chefes ocupam o lugar de parte da massa, em vez de serem
        # simplesmente empilhados sobre uma horda já cheia.
        base_count_by_wave = (2, 3, 2, 2, 4, 5, 4, 4, 7, 8, 7, 8)
        base_count = base_count_by_wave[max(0, min(TOTAL_WAVES - 1, wave - 1))]
        count = max(2, int(round(base_count * float(self.difficulty_data["spawn_count"]))))
        wave_progress = wave / TOTAL_WAVES
        for index in range(count):
            if index < 3:
                key = pool[min(index, len(pool) - 1)]
            else:
                weighted = pool.copy()
                if wave_progress > 0.35:
                    weighted.extend(pool[-min(3, len(pool)):])
                if wave_progress > 0.70:
                    weighted.extend(pool[-min(5, len(pool)):])
                key = random.choice(weighted)
            wait = (
                1.28 - 0.07 * (wave - 1) + random.random() * 0.16
            ) * float(self.difficulty_data["spawn_wait"])
            orders.append(SpawnOrder(wait, key, self.spawn_row_for(key)))
        if slot == 3:
            subboss_key = REGION_SUBBOSSES[self.region][chapter]
            orders.append(SpawnOrder(0.85, subboss_key, self.spawn_row_for(subboss_key)))
        elif slot == 4:
            boss_key = REGION_BOSSES[self.region][chapter]
            escort_count = max(1, int(round((1 + chapter) * float(self.difficulty_data["escort_count"]))))
            for _ in range(escort_count):
                escort_key = random.choice(pool[-min(4, len(pool)):])
                orders.insert(random.randrange(len(orders) + 1), SpawnOrder(0.32, escort_key, self.spawn_row_for(escort_key)))
            orders.append(SpawnOrder(1.15, boss_key, self.spawn_row_for(boss_key, boss=True), True))
        return orders

    def spawn_row_for(self, enemy_key: str, boss: bool = False) -> int:
        """Escolhe uma faixa compatível com a natureza do invasor.

        Na Praia, chefes da maré e inimigos aquáticos entram nas duas rotas do
        canal central; ameaças costeiras terrestres usam as duas faixas secas.
        Desse modo, a posição de nascimento respeita tanto a mecânica quanto
        a perspectiva desenhada do mapa.
        """
        if self.region != "beach":
            return random.randrange(ROWS)
        if boss or enemy_key in BEACH_WATER_ENEMIES or ENEMIES.get(enemy_key, {}).get("amphibious"):
            return random.choice(tuple(self.water_rows))
        land_rows = tuple(row for row in range(ROWS) if row not in self.water_rows)
        return random.choice(land_rows)

    def spawn_enemy(self, order: SpawnOrder) -> None:
        data = BOSSES.get(order.key) or ENEMIES[order.key]
        enemy = Enemy(order.key, order.row, data, self.region, self.wave, difficulty=self.difficulty)
        actor_key = ENEMY_ACTOR_BY_KEY.get(order.key)
        if actor_key:
            enemy.visual_animation = self.app.assets.new_production_animation(actor_key)
        enemy.x = ENEMY_ENTRY_X[self.region]
        enemy.entry_reveal = ENEMY_ENTRY_REVEAL_SECONDS
        if order.boss:
            self.app.audio.play("boss", min_interval_ms=1200)
            enemy.x = BOARD.right + 110
            enemy.boss_announced = True
            self.shake = 0.38
        self.enemies.append(enemy)
        if not order.boss:
            self.app.audio.play("zombie_groan", min_interval_ms=1750)
        if order.boss:
            self.boss_banner_name = str(data["name"])
            self.boss_banner_subtitle = "ENTRADA ESPECIAL ATIVADA"
            self.boss_entrance(enemy)

    def region_color(self) -> tuple[int, int, int]:
        return REGIONS[self.region]["accent"]

    def scaled_enemy_damage(self, enemy: Enemy, amount: float) -> float:
        """Aplica o modo ao dano de mordidas, projéteis e habilidades inimigas."""
        key = "boss_damage" if enemy.is_boss else "enemy_damage"
        return float(amount) * float(self.difficulty_data[key])

    def target_in_range(self, defender: Defender, min_distance: float = 0) -> Enemy | None:
        """Detecta apenas infectados à frente e dentro da linha da carta."""
        maximum = float(defender.stats["range"]) * CELL_W
        lower_bound = defender.x + max(0.0, min_distance)
        choices = [
            enemy
            for enemy in self.enemies
            if enemy.row == defender.row
            and enemy.x >= lower_bound
            and enemy.x - defender.x <= maximum
            and enemy.hp > 0
        ]
        if not defender.stats.get("shoot_through_allies", False):
            choices = [
                enemy
                for enemy in choices
                if not any(
                    ally is not defender
                    and ally.row == defender.row
                    and ally.hp > 0
                    and ally.deployed
                    and defender.x < ally.x < enemy.x
                    for ally in self.defenders
                )
            ]
        if not choices:
            return None
        # Cada especialidade procura primeiro a ameaça que justifica sua vaga
        # na equipe. Se ela não existir na faixa, a carta volta ao alvo mais
        # próximo e nunca fica artificialmente parada.
        priorities: dict[str, Callable[[Enemy], bool]] = {
            "xerife_rua": lambda enemy: enemy.key in {"infectado_urbano", "tecnico_subestacao"},
            "atirador_precisao_swat": lambda enemy: bool(enemy.data.get("immunities")) or enemy.data.get("subboss", False),
            "agente_entrada": lambda enemy: enemy.key in {"bruto", "bruto_demolidor"},
            "especialista_antipraga": lambda enemy: enemy.key in {"policial", "divisor", "cuspidor_alfa"},
            "lancador_foguetes": lambda enemy: "shield" in enemy.tags or enemy.data.get("subboss", False),
            "escudeiro_tropa_choque": lambda enemy: enemy.key in {"bruto", "bruto_demolidor"},
            "atirador_horizonte": lambda enemy: enemy.key in {"curandeiro", "necromante"},
            "tenente_artilheiro": lambda enemy: enemy.key in {"mutante", "mutante_ruinas"},
            "incinerador_deserto": lambda enemy: enemy.key in {"curandeiro", "necromante"},
            "guardiao_laminas": lambda enemy: enemy.key == "parasita",
            "atirador_precisao_marinha": lambda enemy: enemy.key in {"mergulhador", "cacador"},
            "bombeiro_hidraulico": lambda enemy: enemy.key == "salva_vidas" or "shield" in enemy.tags,
            "submarino_tatico": lambda enemy: enemy.is_boss or enemy.key in {"mergulhador", "cacador"},
        }
        predicate = priorities.get(defender.key)
        preferred = [enemy for enemy in choices if predicate and predicate(enemy)]
        if preferred:
            if defender.stats.get("role") == "sniper":
                return max(preferred, key=lambda enemy: (enemy.max_hp, -enemy.x))
            return min(preferred, key=lambda enemy: enemy.x)
        return min(choices, key=lambda enemy: enemy.x)

    def blocker_for(self, enemy: Enemy) -> Defender | None:
        contact_distance = float(enemy.data.get("contact_distance", 58.0))
        choices = [
            defender
            for defender in self.defenders
            if defender.row == enemy.row
            and defender.hp > 0
            and defender.deployed
            and defender.x <= enemy.x
        ]
        if not choices:
            return None
        nearest = max(choices, key=lambda d: d.x)
        if enemy.x - nearest.x <= contact_distance + 0.5:
            return nearest
        return None

    def swept_blocker_for(self, enemy: Enemy, next_x: float) -> Defender | None:
        """Impede que um passo rápido atravesse a hitbox de uma defesa.

        A verificação considera o segmento percorrido no quadro, portanto
        continua correta mesmo com ``dt`` alto ou com o Corredor mais veloz.
        """
        contact_distance = float(enemy.data.get("contact_distance", 58.0))
        crossed = [
            defender
            for defender in self.defenders
            if defender.row == enemy.row
            and defender.hp > 0
            and defender.deployed
            and defender.x <= enemy.x
            and next_x <= defender.x + contact_distance
        ]
        return max(crossed, key=lambda defender: defender.x) if crossed else None

    def begin_jump(self, enemy: Enemy, blocker: Defender) -> None:
        """Inicia um único salto contínuo sobre a primeira defesa bloqueadora."""
        enemy.jump_used = True
        enemy.jump_state = "vault"
        enemy.jump_duration = 0.52
        enemy.jump_timer = enemy.jump_duration
        enemy.jump_start_x = enemy.x
        enemy.jump_end_x = max(BOARD.left + 8, blocker.x - 60)
        enemy.motion.trigger("jump", enemy.jump_duration)
        self.pulse(enemy.x, enemy.y + 16, GOLD, 9)
        self.announce(f"{enemy.data['name']}: ultrapassou uma única defesa.", 1.35, RED)

    def begin_dig(self, enemy: Enemy, blocker: Defender) -> None:
        """Inicia a escavação mostrada em três etapas, sem teleporte ou dano grátis."""
        enemy.dig_used = True
        enemy.burrowed = True
        enemy.dig_state = "enter"
        enemy.dig_duration = 0.34
        enemy.dig_timer = enemy.dig_duration
        enemy.dig_start_x = enemy.x
        # A saída fica logo depois da primeira defesa encontrada. O Escavador
        # não pode saltar uma fileira inteira nem escolher um alvo distante.
        enemy.dig_end_x = max(BOARD.left + 8, blocker.x - 60)
        enemy.motion.trigger("dig_enter", enemy.dig_duration)
        self.pulse(enemy.x, enemy.y + 17, (194, 160, 77), 12)
        self.announce("Escavador: começou a cavar sob a primeira defesa.", 1.55, (232, 198, 112))

    def update_enemy_motion(self, enemy: Enemy, dt: float) -> bool:
        """Atualiza movimentos especiais que devem ser vistos antes da próxima ação.

        Retorna ``True`` enquanto o inimigo estiver saltando ou escavando.
        Isso impede que o movimento normal transforme a animação num
        teleporte e também impede mordidas durante a travessia.
        """
        if enemy.jump_state:
            if enemy.motion.state != "jump":
                enemy.motion.trigger("jump", enemy.jump_timer)
            enemy.jump_timer = max(0.0, enemy.jump_timer - dt)
            progress = clamp(1.0 - enemy.jump_timer / max(0.01, enemy.jump_duration), 0.0, 1.0)
            enemy.x = lerp(enemy.jump_start_x, enemy.jump_end_x, progress)
            if enemy.jump_timer <= 0:
                enemy.x = enemy.jump_end_x
                enemy.jump_state = ""
                self.pulse(enemy.x, enemy.y + 17, GOLD, 10)
            return True

        if not enemy.dig_state:
            return False

        enemy.dig_timer = max(0.0, enemy.dig_timer - dt)
        if enemy.dig_state == "enter":
            if enemy.motion.state != "dig_enter":
                enemy.motion.trigger("dig_enter", enemy.dig_timer)
            if enemy.dig_timer <= 0:
                enemy.dig_state = "tunnel"
                enemy.dig_duration = 0.58
                enemy.dig_timer = enemy.dig_duration
                enemy.motion.trigger("dig_tunnel", enemy.dig_duration)
            return True

        if enemy.dig_state == "tunnel":
            if enemy.motion.state != "dig_tunnel":
                enemy.motion.trigger("dig_tunnel", enemy.dig_timer)
            progress = clamp(1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0)
            enemy.x = lerp(enemy.dig_start_x, enemy.dig_end_x, progress)
            if enemy.dig_timer <= 0:
                enemy.x = enemy.dig_end_x
                enemy.dig_state = "emerge"
                enemy.dig_duration = 0.34
                enemy.dig_timer = enemy.dig_duration
                enemy.motion.trigger("dig_emerge", enemy.dig_duration)
                self.pulse(enemy.x, enemy.y + 17, (218, 185, 103), 11)
            return True

        # Etapa final: a silhueta cresce do chão no renderizador e só então
        # o Escavador volta a poder se mover ou atacar.
        if enemy.motion.state != "dig_emerge":
            enemy.motion.trigger("dig_emerge", enemy.dig_timer)
        if enemy.dig_timer <= 0:
            enemy.dig_state = ""
            enemy.burrowed = False
            self.pulse(enemy.x, enemy.y + 17, (226, 192, 112), 8)
        return True

    @staticmethod
    def damage_channel(effect: str, source: Defender | None) -> str:
        """Classifica o dano sem depender do nome visual do projétil."""
        if effect in {"explosion", "mortar"}:
            return "explosive"
        if effect in {"poison", "acid", "acid_brief"}:
            return "chemical"
        if effect in {"flame", "status_tick"}:
            return "thermal"
        if effect == "water":
            return "hydraulic"
        if source is None:
            return "environment"
        role = str(source.stats.get("role", ""))
        if role == "sniper":
            return "precision"
        if role == "sub":
            return "piercing"
        if role in {"shield", "blade"}:
            return "melee"
        if role in {"grenade", "mortar", "rocket", "suicide_bomber", "mine"}:
            return "explosive"
        if role in {"poison", "gas_grenade"}:
            return "chemical"
        if role == "flame":
            return "thermal"
        if role == "waterjet":
            return "hydraulic"
        return "ballistic"

    def take_enemy_damage(self, enemy: Enemy, amount: float, effect: str = "", source: Defender | None = None) -> None:
        if enemy.hp <= 0:
            return
        channel = self.damage_channel(effect, source)
        counter_keys = tuple(enemy.data.get("counter_keys", ()))
        counter_hit = source is not None and source.key in counter_keys
        if counter_hit:
            was_closed = enemy.defense_broken <= 0
            enemy.defense_broken = max(enemy.defense_broken, 5.0)
            if was_closed:
                label = str(enemy.data.get("defense_name", "defesa especial"))
                self.texts.append(FloatingText("DEFESA ROMPIDA", enemy.x, enemy.y - 65, TEAL, 0.9))
                self.announce(f"{source.display_name} rompeu {label}.", 1.5, TEAL)

        # Contenções de início de pista continuam absolutas. A imunidade vale
        # para tropas e projéteis, não para o dispositivo único da própria fase.
        containment_hit = source is None and amount >= 9000
        if not containment_hit and enemy.defense_broken <= 0:
            if channel in tuple(enemy.data.get("immunities", ())) and not counter_hit:
                self.texts.append(FloatingText("IMUNE", enemy.x, enemy.y - 54, RED, 0.65))
                return
            resistance = float(enemy.data.get("resistances", {}).get(channel, 0.0))
            amount *= max(0.0, 1.0 - clamp(resistance, 0.0, 0.95))
        weakness = float(enemy.data.get("weaknesses", {}).get(channel, 1.0))
        amount *= max(0.0, weakness)
        armor = float(enemy.data.get("armor", 0))
        if "shield" in enemy.tags and effect not in {"flame", "poison", "explosion", "mortar"}:
            armor = max(armor, 0.52)
        if source and source.ascended > 0:
            amount *= 1.55
        applied = amount * (1 - armor)
        enemy.hp -= applied
        if effect not in {"status_tick", "acid"}:
            self.app.audio.play("zombie_hit", min_interval_ms=70)
        if effect not in {"status_tick", "acid"}:
            enemy.motion.flash()
            # Todo infectado acusa o impacto e interrompe brevemente o avanço.
            # Corredores são a exceção declarada: ainda piscam/animam o golpe,
            # mas sua corrida lógica nunca é paralisada pelo stagger.
            if "unstaggerable" not in enemy.tags:
                enemy.stun = max(enemy.stun, float(enemy.data.get("damage_stagger", 0.14)))
            if not enemy.jump_state and not enemy.dig_state:
                hit_duration = (
                    enemy.visual_animation.animations["hit"].duration
                    if enemy.visual_animation is not None
                    else 0.12
                )
                enemy.motion.trigger("hit", hit_duration)
        if effect == "flame":
            was_burning = enemy.burn > 0
            enemy.burn = max(enemy.burn, 3.3)
            if not was_burning:
                self.pulse(enemy.x, enemy.y - 20, (246, 142, 45), 6)
            self.effects.append(VisualEffect("flame_impact", enemy.x, enemy.y - 24, (246, 142, 45), 0.26, scale=0.72))
        elif effect == "poison":
            was_poisoned = enemy.poisoned > 0
            enemy.poisoned = max(enemy.poisoned, 4.2)
            if not was_poisoned:
                self.pulse(enemy.x, enemy.y - 20, (132, 239, 80), 7)
            self.effects.append(VisualEffect("toxic_impact", enemy.x, enemy.y - 24, (132, 239, 80), 0.34, scale=0.82))
        elif effect == "water":
            # Água não substitui o dano de fogo em força bruta: ela extingue
            # a queima e segura o avanço do alvo por uma janela curta.
            enemy.burn = 0.0
            soak_time = 3.6 if source and source.ascended > 0 else 2.4
            enemy.soaked = max(enemy.soaked, soak_time)
            self.effects.append(VisualEffect("water_impact", enemy.x, enemy.y - 20, (102, 224, 244), 0.30, scale=0.78))
        if effect == "acid":
            enemy.corrosion = max(enemy.corrosion, 2.5)
        self.texts.append(FloatingText(str(max(0, int(round(applied)))), enemy.x, enemy.y - 52, GOLD if source and source.ascended else WHITE, 0.55))
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def damage_defender(self, defender: Defender, amount: float, effect: str = "") -> None:
        if defender.hp <= 0:
            return
        defender.hp -= amount
        self.app.audio.play("soldier_hit", min_interval_ms=95)
        defender.motion.flash()
        hit_duration = (
            defender.visual_animation.animations["hit"].duration
            if defender.visual_animation is not None
            else 0.12
        )
        defender.motion.trigger("hit", hit_duration)
        if effect == "stun":
            defender.stun = max(defender.stun, 2.2)
        elif effect == "acid":
            defender.corrosion = max(defender.corrosion, 4.0)
        elif effect == "acid_brief":
            defender.corrosion = max(defender.corrosion, 1.8)
        if effect in {"acid", "acid_brief"}:
            self.effects.append(VisualEffect("toxic_impact", defender.x, defender.y - 28, (132, 239, 80), 0.28, scale=0.58))
        self.texts.append(FloatingText(str(int(amount)), defender.x, defender.y - 48, RED, 0.6))
        if defender.hp <= 0:
            self.kill_defender(defender)

    def kill_defender(self, defender: Defender) -> None:
        if defender not in self.defenders:
            return
        # Tropas comuns não recebem uma falsa queda procedural. Ao zerar a
        # vida, saem imediatamente do campo, conforme a regra desta etapa.
        self.defenders.remove(defender)
        if defender.stats["role"] == "barrier" and defender.stats["level"] >= 2:
            for enemy in self.enemies[:]:
                if enemy.row == defender.row and abs(enemy.x - defender.x) < CELL_W * 1.35:
                    self.take_enemy_damage(enemy, defender.stats["damage"], "explosion")
            self.explosion(defender.x, defender.y, RED, 28)
        self.announce(f"{defender.display_name} foi perdido.", 1.5, RED)

    def kill_enemy(self, enemy: Enemy) -> None:
        if enemy not in self.enemies:
            return
        # Apenas chefes/subchefes manterão animação de morte dedicada. O
        # Caminhante e os demais inimigos comuns desaparecem ao chegar a zero.
        if enemy.is_boss or enemy.data.get("subboss"):
            sprite = self.app.enemy_sprite(self, enemy)
            width, height = enemy_render_scale(enemy, self.region)
            self.fallen.append(
                DefeatAnimation(
                    sprite,
                    enemy.x,
                    enemy.y,
                    width,
                    height,
                    self.region == "beach" and enemy.row in self.water_rows,
                    0.58,
                    enemy=True,
                )
            )
        self.enemies.remove(enemy)
        self.dead_history.append((enemy.key, enemy.row, enemy.x))
        if len(self.dead_history) > 12:
            self.dead_history.pop(0)
        if enemy.is_boss or enemy.data.get("subboss"):
            self.explosion(enemy.x, enemy.y, GOLD, 26)
        if "explode_death" in enemy.tags:
            for defender in self.defenders[:]:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 1.15:
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 52 + self.wave * 2), "acid")
            self.explosion(enemy.x, enemy.y, (114, 212, 99), 25)
        if enemy.is_boss:
            bonus = int(round((46 + self.wave * 2) * float(self.difficulty_data["supply_gain"])))
            self.supplies = min(int(self.difficulty_data["supply_cap"]), self.supplies + bonus)
            self.boss_seen.add(self.wave)
            self.announce(f"Chefe neutralizado: +{bonus} suprimentos.", 3.4, GOLD)
            self.pulse(WIDTH / 2, HEIGHT / 2, GOLD, 75)
        elif enemy.data.get("subboss"):
            bonus = int(round(18 * float(self.difficulty_data["supply_gain"])))
            self.supplies = min(int(self.difficulty_data["supply_cap"]), self.supplies + bonus)
            self.announce(f"Sub-boss neutralizado: +{bonus} suprimentos.", 2.4, GOLD)
        else:
            self.supplies = min(int(self.difficulty_data["supply_cap"]), self.supplies + 1)

    def pulse(self, x: float, y: float, color: tuple[int, int, int], amount: int) -> None:
        # Mantido como gancho de compatibilidade. A versão antiga espalhava
        # círculos; a Beta 4 reserva o desenho para sprites de VFX completos.
        return

    def explosion(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        amount: int,
        *,
        scale: float | None = None,
    ) -> None:
        if scale is None:
            scale = clamp(0.62 + amount / 44.0, 0.72, 1.58)
        self.effects.append(VisualEffect("explosion", x, y - 18, color, 0.46, scale=scale))
        self.shake = max(self.shake, 0.16)
        self.app.audio.play("explosion", min_interval_ms=120)

    def fire_defender(self, defender: Defender, target: Enemy) -> None:
        role = defender.stats["role"]
        level = defender.stats["level"]
        ascending = defender.ascended > 0
        if role in {"radio", "promoter", "barrier", "mine", "suicide_bomber", "sonar"}:
            return
        if defender.max_ammo > 0:
            defender.ammo -= 1
        defender.attack_timer = float(defender.stats["cooldown"]) * (0.68 if ascending else 1.0)
        approved_shot_duration = (
            defender.visual_animation.animations["shoot"].duration
            if defender.visual_animation is not None
            else 0.0
        )
        defender.motion.trigger(
            "attack",
            approved_shot_duration
            or (0.48 if role == "mortar" else (0.36 if role == "grenade" else 0.24)),
        )
        if defender.visual_animation is not None and "shoot" in defender.visual_animation.animations:
            # O projétil é criado neste mesmo método. Colocar a sprite em
            # disparo agora impede que sua origem seja medida na pose parada.
            defender.visual_animation.play("shoot", restart=True)
        heavy_roles = {"heavy", "shotgun", "sniper", "grenade", "gas_grenade", "mortar", "rocket", "sub"}
        rifle_roles = {"rifle", "flame", "waterjet", "poison", "boat"}
        shot_sound = (
            "shot_heavy"
            if role in heavy_roles
            else ("shot_rifle" if role in rifle_roles else "shot_pistol")
        )
        self.app.audio.play(shot_sound, min_interval_ms=55)
        if role == "sniper" and level == 1 and not ascending and random.random() < 0.28:
            self.texts.append(FloatingText("ERROU", target.x, target.y - 42, GRAY, 0.7))
            miss_x, miss_y = defender_weapon_origin(defender)
            self.projectiles.append(Projectile(miss_x, miss_y, None, target.x, target.y - 18, 0, "tracer", defender, travel=0.22))
            return
        damage = float(defender.stats["damage"]) * float(self.difficulty_data["defender_damage"])
        kind = "bullet"
        radius = 0.0
        effect = ""
        weapon_profile = DEFENDER_WEAPON_PROFILES.get(defender.key)
        profiled_kind = weapon_profile.projectile_kind if weapon_profile else ""
        if role in {"rifle", "heavy"}:
            kind = profiled_kind or "rifle"
            if role == "heavy":
                damage *= 1.06
            if ascending:
                kind, radius = "fuzileiro", CELL_W * 0.72
                damage *= 1.25
        elif role == "shotgun":
            kind, radius = profiled_kind or "shotgun", CELL_W * (0.45 if ascending else 0.25)
            distance = max(1, (target.x - defender.x) / CELL_W)
            damage *= 1.45 if distance < 1.2 else 0.9
            if ascending:
                damage *= 1.4
        elif role == "sniper":
            kind = profiled_kind or "sniper"
            if ascending:
                damage *= 2.55
        elif role in {"grenade", "mortar"}:
            kind = profiled_kind or ("mortar" if role == "mortar" else "grenade")
            radius = CELL_W * (1.05 if ascending else 0.78)
            effect = "mortar"
            if ascending and role == "mortar":
                same_lane = sorted(
                    (
                        enemy
                        for enemy in self.enemies
                        if enemy is not target and enemy.row == target.row and enemy.hp > 0
                    ),
                    key=lambda enemy: abs(enemy.x - target.x),
                )[:2]
                origin_x, origin_y = defender_weapon_origin(defender)
                for clone in same_lane:
                    self.projectiles.append(
                        Projectile(
                            origin_x,
                            origin_y,
                            clone,
                            clone.x,
                            clone.y - 15,
                            damage * 0.72,
                            kind,
                            defender,
                            radius,
                            True,
                            0.45,
                            elapsed=-0.30,
                            effect=effect,
                        )
                    )
            if ascending and role == "grenade":
                kind, radius, damage = "bazooka", BOARD.width, damage * 1.45
        elif role == "rocket":
            kind, radius, effect = profiled_kind or "bazooka", CELL_W * 1.05, "mortar"
        elif role == "flame":
            kind, radius, effect = "flame", CELL_W * 0.55, "flame"
            damage *= 0.70
        elif role == "gas_grenade":
            kind = profiled_kind or "gas_grenade"
            radius = CELL_W * 0.82
            effect = "poison"
        elif role == "poison":
            kind = "poison"
            radius = CELL_W * (0.48 if level == 1 else 0.62)
            effect = "poison"
            damage *= 0.62
        elif role == "waterjet":
            kind = "waterjet"
            radius = CELL_W * (0.38 if level == 1 else 0.50)
            effect = "water"
            damage *= 0.62
        elif role == "boat":
            kind = profiled_kind or "boat"
        elif role == "sub":
            kind, radius = profiled_kind or "torpedo", CELL_W * 0.42
        elif role in {"shield", "blade"}:
            kind = "melee"
            radius = CELL_W * 0.12
        travel = {
            "shotgun": 0.18,
            "buckshot_12g": 0.18,
            "sniper": 0.20,
            "sniper_awm": 0.22,
            "sniper_762": 0.22,
            "sniper_338": 0.24,
            "rifle": 0.24,
            "fuzileiro": 0.24,
            "pistol_9mm": 0.20,
            "pistol_50ae": 0.22,
            "revolver_357": 0.22,
            "smg_9mm": 0.20,
            "rifle_556_scar": 0.24,
            "rifle_556_m16": 0.24,
            "mg_762": 0.23,
            "naval_round": 0.25,
            "grenade_40mm": 0.46,
            "gas_grenade": 0.48,
            "mortar_shell": 0.56,
            "rpg7_rocket": 0.45,
            "flame": 0.38,
            "poison": 0.38,
            "waterjet": 0.38,
            "torpedo": 0.62,
            "compact_torpedo": 0.62,
        }.get(kind, 0.42)
        # A mesma âncora alimenta lógica e desenho. O projétil não muda de
        # posição quando a perspectiva ou o quadro da animação muda.
        muzzle_x, muzzle_y = defender_weapon_origin(defender)
        projectile = Projectile(
            muzzle_x,
            muzzle_y,
            target,
            target.x,
            target.y - 16,
            damage,
            kind,
            defender,
            radius,
            True,
            travel,
            effect=effect,
        )
        if kind in {"mortar", "mortar_shell"}:
            projectile.elapsed = -0.34
        elif kind in {"grenade", "grenade_40mm", "gas_grenade", "bazooka", "rpg7_rocket"}:
            projectile.elapsed = -0.12
        self.projectiles.append(projectile)

    def closest_enemy_at(self, row: int, x: float) -> Enemy | None:
        candidates = [enemy for enemy in self.enemies if enemy.row == row and enemy.hp > 0]
        return min(candidates, key=lambda e: abs(e.x - x)) if candidates else None

    def promote_defender(self, instructor: Defender) -> bool:
        """Converte uma tropa N1 real em sua carta N2 correspondente.

        A promoção obedece à mesma regra de isolamento do combate: o instrutor
        só alcança uma tropa da própria faixa.
        """
        radius = float(instructor.stats["range"]) * CELL_W
        candidates = [
            defender
            for defender in self.defenders
            if defender is not instructor
            and defender.key in PROMOTIONS
            and int(defender.stats["level"]) == 1
            and defender.ascended <= 0
            and abs(defender.x - instructor.x) <= radius
            and defender.row == instructor.row
        ]
        if not candidates:
            # Não reinicia o minuto inteiro se ainda não houver uma tropa N1
            # válida por perto: o jogador ganha uma pequena janela para criar
            # ou reposicionar a candidata.
            instructor.utility_timer = 8.0
            return False

        target = min(candidates, key=lambda defender: abs(defender.x - instructor.x))
        target_key = PROMOTIONS[target.key]
        upgraded = DEFENSES[target_key]
        old_hp_ratio = target.hp / max(1.0, target.max_hp)
        old_ammo_ratio = target.ammo / max(1, target.max_ammo) if target.max_ammo else 1.0
        target.key = target_key
        target.stats = upgraded
        target.sprite_index = regional_sprite_index(self.region, target_key)
        target.hp = max(1.0, float(upgraded["hp"]) * max(0.55, old_hp_ratio))
        target.ammo = int(round(int(upgraded["ammo"]) * old_ammo_ratio)) if int(upgraded["ammo"]) else 0
        target.reload_timer = 0.0
        target.reload_total = 0.0
        target.attack_timer = 0.0
        target.utility_timer = 0.0
        target.stun = 0.0
        target.corrosion = 0.0
        target.display_name = self.display_name_for(target_key)
        instructor.utility_timer = float(instructor.stats["cooldown"])
        instructor.motion.trigger("support", 0.46)
        target.motion.trigger("promote", 0.60)
        self.announce(f"PROMOÇÃO CONCLUÍDA: {target.display_name} agora é N2!", 2.5, GOLD)
        self.pulse(target.x, target.y - 12, GOLD, 28)
        return True

    def display_name_for(self, key: str) -> str:
        """Mantém a nomenclatura regional quando uma carta muda de nível."""
        for roster_key, display in REGION_ROSTERS[self.region]:
            if roster_key == key:
                return display
        return str(DEFENSES[key]["base"])

    def utility_defender(self, defender: Defender, dt: float) -> None:
        role = defender.stats["role"]
        if role == "radio" and defender.utility_timer <= 0:
            # Contrato único da economia: qualquer gerador regional entrega
            # exatamente doze suprimentos a cada doze segundos. A dificuldade
            # ainda regula custos, inimigos e recompensas, mas nunca altera o
            # relógio do gerador, que precisa ser previsível desde o começo.
            gain = 12
            room = int(self.difficulty_data["supply_cap"]) - self.supplies
            gain = max(0, min(gain, room))
            self.supplies += gain
            defender.utility_timer = 12.0
            self.app.audio.play("supply", min_interval_ms=240)
            defender.motion.trigger("support", 1.60)
            self.texts.append(FloatingText(f"+{gain} SUP", defender.x, defender.y - 55, GOLD, 1.0))
            self.pulse(defender.x, defender.y - 18, GOLD, 8)
        elif role == "promoter" and defender.utility_timer <= 0:
            self.promote_defender(defender)
        elif role == "sonar" and defender.utility_timer <= 0:
            revealed = [
                enemy for enemy in self.enemies
                if enemy.row == defender.row and enemy.x >= defender.x
            ]
            for enemy in revealed:
                enemy.soaked = max(enemy.soaked, 2.2)
                enemy.quarantine_mark = max(enemy.quarantine_mark, 2.2)
                if defender.key in tuple(enemy.data.get("counter_keys", ())):
                    enemy.defense_broken = max(enemy.defense_broken, 5.0)
            defender.utility_timer = float(defender.stats["cooldown"])
            defender.motion.trigger("support", 0.9)
            if revealed:
                self.announce(f"Sonar: {len(revealed)} ameaça(s) revelada(s).", 1.3, TEAL)

    def update_self_reload(self, defender: Defender, dt: float) -> bool:
        """Executa a recarga da própria arma e bloqueia o tiro nesse estado."""
        if defender.max_ammo <= 0 or defender.ammo > 0:
            defender.reload_timer = 0.0
            defender.reload_total = 0.0
            return False
        # A última rajada continua visualmente completa antes de a arma baixar.
        if defender.reload_timer <= 0 and defender.motion.state == "attack" and defender.motion.event_left > 0:
            return True
        if defender.reload_timer <= 0:
            defender.reload_total = weapon_reload_seconds(defender.stats, defender.ascended > 0)
            defender.reload_timer = defender.reload_total
            defender.motion.trigger("reload", defender.reload_total)
            self.app.audio.play("reload", min_interval_ms=160)
        defender.reload_timer = max(0.0, defender.reload_timer - dt)
        if defender.reload_timer <= 0:
            defender.ammo = defender.max_ammo
            defender.attack_timer = max(defender.attack_timer, 0.16)
            defender.motion.loop("idle")
            defender.reload_total = 0.0
            return True
        if defender.motion.state != "reload":
            defender.motion.trigger("reload", defender.reload_timer)
        return True

    def update_deployments(self, dt: float) -> None:
        """Faz a carta virar um soldado que caminha da base até a célula."""
        for defender in self.defenders:
            if defender.deployment_x is None or defender.deployment_target_x is None:
                continue
            defender.motion.loop("walk")
            defender.deployment_x += defender.deployment_speed * dt
            if defender.deployment_x >= defender.deployment_target_x:
                defender.deployment_x = None
                defender.deployment_target_x = None
                defender.motion.loop("idle")
                self.pulse(defender.x, defender.y, self.region_color(), 12)

    @staticmethod
    def _play_visual_state(
        animation: AnimationManager,
        state: str,
        *,
        playback_rate: float = 1.0,
    ) -> None:
        changed = animation.play(state)
        if changed:
            animation.playback_rate = max(0.05, float(playback_rate))

    def update_production_animations(self, dt: float) -> None:
        """Sincroniza a lógica real com as novas sprites, sempre por ``dt``."""
        for defender in self.defenders:
            animation = defender.visual_animation
            if animation is None:
                continue
            if not defender.deployed or defender.motion.state == "walk":
                state = "move"
                # A passada acompanha os pixels realmente percorridos. O ator
                # não é simplesmente transladado sobre uma pose lenta.
                move_clip = animation.animations["move"]
                stride = 62.0
                rate = clamp(
                    move_clip.duration * defender.deployment_speed / stride,
                    0.85,
                    3.8,
                )
            elif defender.motion.state == "attack":
                state, rate = "shoot", 1.0
            elif defender.motion.state == "reload":
                clip = animation.animations["reload"]
                reload_seconds = max(0.01, defender.reload_total or defender.reload_timer)
                state, rate = "reload", clip.duration / reload_seconds
            elif defender.motion.state == "support" and "support" in animation.animations:
                state, rate = "support", 1.0
            elif defender.motion.state in {"hit", "stunned"}:
                state, rate = "hit", 1.0
            else:
                state, rate = "idle", 1.0
            self._play_visual_state(animation, state, playback_rate=rate)
            animation.playback_rate = max(0.05, float(rate))
            animation.update(dt)

        for enemy in self.enemies:
            animation = enemy.visual_animation
            if animation is None:
                continue
            rate = 1.0
            if enemy.motion.state == "attack":
                state = "bite"
            elif (
                enemy.motion.state
                in {"skill", "jump", "dig_enter", "dig_tunnel", "dig_emerge"}
                and "skill" in animation.animations
            ):
                state = "skill"
            elif enemy.motion.state in {"hit", "stunned"}:
                state = "hit"
            elif enemy.motion.state in {"walk", "spawn"}:
                state = "move"
                # Cada ciclo cobre um comprimento de passada coerente com a
                # silhueta. Corredores alternam os pés mais depressa;
                # rastejadores apoiam braços e tronco com cadência lenta.
                speed = float(enemy.data["speed"]) * (1.55 if enemy.rage > 0 else 1.0)
                if enemy.soaked > 0:
                    speed *= 0.68
                if enemy.poisoned > 0:
                    speed *= 0.88
                stride = 22.0 if "runner" in enemy.tags else (12.0 if enemy.key in CRAWLER_ENEMIES else 18.0)
                rate = clamp(animation.animations["move"].duration * speed / stride, 0.48, 2.4)
            else:
                state = "idle"
            self._play_visual_state(animation, state, playback_rate=rate)
            animation.playback_rate = rate
            animation.update(dt)

    def update_defenders(self, dt: float) -> None:
        for defender in self.defenders[:]:
            role = defender.stats["role"]
            defender.motion.advance(dt, "armed" if role == "mine" else "idle")
            defender.attack_timer -= dt
            defender.utility_timer -= dt
            defender.stun = max(0.0, defender.stun - dt)
            defender.corrosion = max(0.0, defender.corrosion - dt)
            defender.ascended = max(0.0, defender.ascended - dt)
            defender.pulse += dt
            if not defender.deployed:
                continue
            if defender.corrosion > 0 and random.random() < dt * 1.6:
                self.damage_defender(defender, 1.6)
            if role == "mine":
                target = next((enemy for enemy in self.enemies if enemy.row == defender.row and abs(enemy.x - defender.x) < 49), None)
                if target:
                    is_safe = defender.stats["level"] >= 2
                    if is_safe or random.random() < 0.72:
                        if defender.ascended:
                            for enemy in self.enemies[:]:
                                if enemy.row == defender.row:
                                    self.take_enemy_damage(enemy, 9999, "explosion", defender)
                            self.announce("Mina ascensionada: linha inteira limpa!", 1.7, GOLD)
                        else:
                            radius = CELL_W * (0.82 if defender.key == "bomba_agua" else 0.35)
                            for enemy in self.enemies[:]:
                                if enemy.row == defender.row and abs(enemy.x - defender.x) < radius:
                                    self.take_enemy_damage(enemy, defender.stats["damage"], "explosion", defender)
                        self.effects.append(VisualEffect("explosion", defender.x, defender.y - 13, GOLD, 0.32, scale=0.95))
                        self.explosion(defender.x, defender.y, GOLD, 18)
                    else:
                        self.announce("A mina falhou!", 1.2, RED)
                    self.defenders.remove(defender)
                continue
            if role == "suicide_bomber":
                contact = next(
                    (
                        enemy
                        for enemy in self.enemies
                        if enemy.row == defender.row
                        and abs(enemy.x - defender.x) <= 54.0
                    ),
                    None,
                )
                if contact is not None:
                    damage = float(defender.stats["damage"]) * float(
                        self.difficulty_data["defender_damage"]
                    )
                    radius = CELL_W * 0.82
                    for enemy in self.enemies[:]:
                        if enemy.row == defender.row and abs(enemy.x - defender.x) <= radius:
                            self.take_enemy_damage(enemy, damage, "explosion", defender)
                    self.explosion(defender.x, defender.y, GOLD, 22, scale=1.08)
                    self.defenders.remove(defender)
                    self.announce("Homem-Bomba detonou no contato!", 1.3, GOLD)
                continue
            if defender.stun > 0:
                defender.motion.trigger("stunned", defender.stun)
                continue
            if self.update_self_reload(defender, dt):
                continue
            self.utility_defender(defender, dt)
            minimum = CELL_W * 1.05 if role == "mortar" else 0
            target = self.target_in_range(defender, minimum)
            if target and defender.attack_timer <= 0 and defender.has_ammo():
                self.fire_defender(defender, target)

    @staticmethod
    def is_military_defender(defender: Defender) -> bool:
        """Tropas humanas recebem os efeitos globais de entrada dos chefes.

        Minas e barreiras são equipamentos fixos; elas continuam como opção de
        contenção quando uma chegada especial fecha temporariamente os tiros.
        """
        return defender.stats["role"] not in {"barrier", "mine", "suicide_bomber"}

    def boss_entrance(self, enemy: Enemy) -> None:
        """Executa uma única ação de entrada. Ela nunca é reutilizada no ciclo.

        Cada chefe ganha um impacto memorável ao aparecer, mas a ação recorrente
        que vem depois é menor, localizada e possui um intervalo legível.
        """
        boss_type = enemy.data.get("type", "")
        skill_duration = self.enemy_skill_duration(enemy, 0.72)
        enemy.motion.trigger("skill", skill_duration)
        self.shake = max(self.shake, 0.42)
        entrance_visuals = {
            "bruto_demolidor": ("ground_slam", (230, 91, 61)),
            "comandante": ("command_aura", (232, 77, 62)),
            "alfa": ("toxic_wave", (132, 239, 80)),
            "mutante": ("ground_slam", (225, 152, 70)),
            "necromante": ("arcane_cast", (197, 128, 238)),
            "colosso": ("ground_slam", (227, 163, 81)),
            "tide": ("tidal_surge", (95, 195, 239)),
            "hunter": ("tidal_surge", (95, 195, 239)),
            "leviathan": ("tidal_surge", (95, 195, 239)),
        }
        visual_kind, visual_color = entrance_visuals.get(str(boss_type), ("ground_slam", RED))
        effect_x, effect_y = self.enemy_effect_origin(enemy, visual_kind)
        self.effects.append(
            VisualEffect(
                visual_kind,
                effect_x,
                effect_y,
                visual_color,
                skill_duration,
                scale=1.45,
                owner=enemy,
                anchor_kind=visual_kind,
            )
        )
        if boss_type == "bruto_demolidor":
            for defender in self.defenders:
                if self.is_military_defender(defender):
                    defender.stun = max(defender.stun, 3.0)
            enemy.skill_timer = 18.0
            self.announce("BRUTO DEMOLIDOR: tropas militares paralisadas por 3 s!", 2.8, RED)
        elif boss_type == "comandante":
            for other in self.enemies:
                if other is not enemy and abs(other.x - enemy.x) < CELL_W * 4.2:
                    other.rage = max(other.rage, 2.4)
            enemy.skill_timer = 14.0
            self.announce("Comandante dos Mortos: a escolta recebeu fúria!", 2.4, RED)
        elif boss_type == "alfa":
            self.global_toxic = 1.2
            for defender in self.defenders:
                defender.corrosion = max(defender.corrosion, 1.0)
            enemy.skill_timer = 14.0
            self.announce("Cuspidor Alfa: névoa ácida global por um instante!", 2.4, (150, 232, 112))
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if abs(defender.row - enemy.row) <= 1 and abs(defender.x - enemy.x) < CELL_W * 2.25:
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 8))
                    defender.stun = max(defender.stun, 1.15)
            enemy.skill_timer = 14.0
            self.announce("Mutante das Ruínas: o abalo atingiu apenas a vanguarda próxima.", 2.2, RED)
        elif boss_type == "necromante":
            self.enemies.append(Enemy("necromante_minion", enemy.row, ENEMIES["necromante_minion"], self.region, self.wave, difficulty=self.difficulty, x=enemy.x + 48))
            enemy.skill_timer = 15.0
            self.announce("Necromante: uma múmia foi invocada na chegada.", 2.3, (197, 128, 238))
        elif boss_type == "colosso":
            for defender in self.defenders:
                if self.is_military_defender(defender):
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce("Colosso Mutante: tremor inicial interrompeu os tiros por 1,2 s.", 2.4, RED)
        elif boss_type == "tide":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 8))
                    defender.stun = max(defender.stun, 0.9)
            enemy.skill_timer = 14.0
            self.announce("Bruto da Maré: a primeira onda abalou o canal.", 2.1, (95, 195, 239))
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 4.8, enemy.x - CELL_W * 0.7)
            enemy.skill_timer = 13.0
            self.announce("Caçador Abissal: mergulhou e surgiu mais perto no canal.", 2.1, (95, 195, 239))
        elif boss_type == "leviathan":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 14))
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce("LEVIATÃ: uma onda de entrada atingiu a faixa de água.", 2.4, (95, 195, 239))
        else:
            enemy.skill_timer = 12.0

    @staticmethod
    def enemy_projectile_origin(enemy: Enemy, kind: str) -> tuple[float, float]:
        """Ponto anatômico/equipamento de onde cada ataque realmente parte."""
        category = "boss" if enemy.is_boss else ("subboss" if enemy.data.get("subboss") else "common")
        body_height, source_height = ENEMY_BODY_LAYOUTS[category]
        depth = lane_depth(enemy.region, enemy.row)
        dx, height_ratio = ENEMY_ATTACK_ORIGINS.get(kind, (-16.0, 0.55))
        emitter_height = body_height * height_ratio
        animation = enemy.visual_animation
        if animation is not None and animation.state == "skill":
            dx, emitter_height = sprite_emitter_contact(
                animation.frame,
                dx,
                emitter_height,
                body_height=body_height,
                source_body_height=source_height,
                facing=-1,
            )
        return enemy.x + dx * depth, enemy.y - emitter_height * depth

    @staticmethod
    def enemy_effect_origin(enemy: Enemy, kind: str) -> tuple[float, float]:
        """Ancora efeitos no chão, na água ou no corpo conforme a habilidade."""
        if kind in {"ground_slam", "tidal_surge", "water_splash"}:
            return enemy.x, enemy.y - 12 * lane_depth(enemy.region, enemy.row)
        if kind == "toxic_wave":
            return Battle.enemy_projectile_origin(enemy, "acid")
        category = "boss" if enemy.is_boss else ("subboss" if enemy.data.get("subboss") else "common")
        body_height, source_height = ENEMY_BODY_LAYOUTS[category]
        depth = lane_depth(enemy.region, enemy.row)
        animation = enemy.visual_animation
        if kind == "supply_snatch" and animation is not None:
            forward, height = sprite_emitter_contact(
                animation.frame,
                -14.0,
                body_height * 0.52,
                body_height=body_height,
                source_body_height=source_height,
                facing=-1,
            )
            return enemy.x + forward * depth, enemy.y - height * depth
        if kind in {
            "arcane_cast", "electric_arc", "signal_pulse", "heal_pulse",
            "heal_receive", "command_aura", "parasite_burst",
        } and animation is not None:
            # A aura acompanha o torso visível da pose atual. O sistema antigo
            # usava sempre x-8/y-48 e deixava cruz, parasita ou pulso flutuando
            # quando o zumbi inclinava o corpo durante a habilidade.
            frame = animation.frame
            bounds = frame.get_bounding_rect(min_alpha=8)
            if bounds.width > 0 and bounds.height > 0:
                source_x = bounds.centerx
                vertical_ratio = 0.58 if kind == "parasite_burst" else 0.44
                source_y = bounds.top + bounds.height * vertical_ratio
                ratio = body_height / max(1.0, source_height)
                forward = (source_x - frame.get_width() / 2) * ratio
                height = (frame.get_height() - source_y) * ratio
                return enemy.x + forward * depth, enemy.y - height * depth
        if kind in {"arcane_cast", "electric_arc", "signal_pulse", "heal_pulse", "heal_receive", "supply_snatch", "command_aura", "parasite_burst"}:
            return enemy.x - 8 * depth, enemy.y - (64 if enemy.is_boss else 48) * depth
        return enemy.x, enemy.y - 30 * lane_depth(enemy.region, enemy.row)

    @staticmethod
    def enemy_skill_duration(enemy: Enemy, fallback: float = 0.62) -> float:
        """Usa exatamente o relógio da sprite para corpo e efeito terminarem juntos."""
        if enemy.visual_animation is not None:
            clip = enemy.visual_animation.animations.get("skill")
            if clip is not None:
                return max(0.01, clip.duration)
        return fallback

    def boss_skill(self, enemy: Enemy) -> None:
        """Habilidade recorrente, sempre mais justa que a entrada do chefe."""
        boss_type = enemy.data.get("type", "")
        cooldowns = {
            "bruto_demolidor": 18.0,
            "comandante": 14.0,
            "alfa": 14.0,
            "mutante": 14.0,
            "necromante": 15.0,
            "colosso": 18.0,
            "tide": 14.0,
            "hunter": 13.0,
            "leviathan": 18.0,
        }
        enemy.skill_timer = cooldowns.get(boss_type, 12.0) * float(self.difficulty_data["skill_cooldown"])
        skill_duration = self.enemy_skill_duration(enemy)
        enemy.motion.trigger("skill", skill_duration)
        if enemy.visual_animation is not None and "skill" in enemy.visual_animation.animations:
            enemy.visual_animation.play("skill", restart=True)
        self.shake = max(self.shake, 0.24)
        skill_visuals = {
            "bruto_demolidor": ("ground_slam", (230, 91, 61)),
            "comandante": ("command_aura", (232, 77, 62)),
            "alfa": ("toxic_wave", (132, 239, 80)),
            "mutante": ("ground_slam", (225, 152, 70)),
            "necromante": ("arcane_cast", (197, 128, 238)),
            "colosso": ("ground_slam", (227, 163, 81)),
            "tide": ("tidal_surge", (95, 195, 239)),
            "hunter": ("tidal_surge", (95, 195, 239)),
            "leviathan": ("tidal_surge", (95, 195, 239)),
        }
        visual_kind, visual_color = skill_visuals.get(str(boss_type), ("ground_slam", RED))
        effect_x, effect_y = self.enemy_effect_origin(enemy, visual_kind)
        self.effects.append(
            VisualEffect(
                visual_kind,
                effect_x,
                effect_y,
                visual_color,
                skill_duration,
                scale=1.0,
                owner=enemy,
                anchor_kind=visual_kind,
            )
        )

        if boss_type == "bruto_demolidor":
            # Regra central do primeiro chefe: sem stun global repetido. O
            # martelo fecha somente a faixa na qual o chefe está por 1,2 s.
            targets = [d for d in self.defenders if d.row == enemy.row and self.is_military_defender(d)]
            for defender in targets:
                defender.stun = max(defender.stun, 1.2)
                self.pulse(defender.x, defender.y - 22, RED, 7)
            self.announce(f"Martelo do Bruto: faixa {enemy.row + 1} interrompida por 1,2 s.", 2.0, RED)
        elif boss_type == "comandante":
            escorts = [
                other for other in self.enemies
                if other is not enemy and abs(other.row - enemy.row) <= 1 and abs(other.x - enemy.x) < CELL_W * 2.8
            ]
            for other in escorts:
                other.rage = max(other.rage, 2.2)
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.5]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                for vertical in (-11, 9):
                    damage = self.scaled_enemy_damage(enemy, 10 + self.wave)
                    origin_x, origin_y = self.enemy_projectile_origin(enemy, "enemy_bullet")
                    self.projectiles.append(Projectile(origin_x, origin_y + vertical, victim, victim.x, victim.y - 24, damage, "enemy_bullet", enemy, 0, False, 0.32))
            self.announce("Comandante: escolta próxima acelerada e rajada dupla disparada.", 1.9, RED)
        elif boss_type == "alfa":
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0]
            for victim in sorted(targets, key=lambda defender: defender.x, reverse=True)[:1]:
                damage = self.scaled_enemy_damage(enemy, 10 + self.wave)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "acid")
                self.projectiles.append(Projectile(origin_x, origin_y, victim, victim.x, victim.y - 18, damage, "acid", enemy, 0, False, 0.45, effect="acid_brief"))
            self.announce(f"Cuspidor Alfa: saliva corrosiva na faixa {enemy.row + 1}.", 1.8, (150, 232, 112))
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 2.15:
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 12))
                    defender.stun = max(defender.stun, 1.0)
            self.announce(f"Mutante: punho de ruína na faixa {enemy.row + 1}.", 1.8, RED)
        elif boss_type == "necromante":
            self.enemies.append(Enemy("necromante_minion", enemy.row, ENEMIES["necromante_minion"], self.region, self.wave, difficulty=self.difficulty, x=enemy.x + 42))
            for other in self.enemies:
                if other is not enemy and abs(other.x - enemy.x) < CELL_W * 1.65:
                    other.hp = min(other.max_hp, other.hp + 28)
            self.announce("Necromante: novas múmias e cura localizada da escolta.", 2.0, (197, 128, 238))
        elif boss_type == "colosso":
            targets = [d for d in self.defenders if d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                damage = self.scaled_enemy_damage(enemy, 18)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "mortar")
                self.projectiles.append(Projectile(origin_x, origin_y, victim, victim.x, victim.y - 24, damage, "mortar", enemy, 0, False, 0.52))
            self.announce("Colosso: rocha arremessada contra uma faixa-alvo.", 1.9, RED)
        elif boss_type == "tide":
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, self.scaled_enemy_damage(enemy, 12))
                victim.stun = max(victim.stun, 0.8)
            self.announce("Bruto da Maré: golpe concentrado no canal.", 1.8, (95, 195, 239))
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 3.4, enemy.x - CELL_W * 0.85)
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, self.scaled_enemy_damage(enemy, 10))
                victim.stun = max(victim.stun, 0.7)
            self.announce("Caçador Abissal: mergulho ofensivo no canal.", 1.8, (95, 195, 239))
        elif boss_type == "leviathan":
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                damage = self.scaled_enemy_damage(enemy, 24)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "torpedo")
                self.projectiles.append(Projectile(origin_x, origin_y, victim, victim.x, victim.y - 12, damage, "torpedo", enemy, 0, False, 0.42))
            self.announce("LEVIATÃ: jato de pressão concentrado na faixa de água.", 2.0, (95, 195, 239))

    def enemy_special(self, enemy: Enemy) -> None:
        if enemy.is_boss:
            self.boss_skill(enemy)
            return
        # Inimigos básicos e rastejadores não fingem possuir um poder. A ação
        # especial só toca quando existe uma regra real associada à ficha.
        # Mordida e devorar continuam usando o estado físico de ataque.
        active_tags = ACTIVE_ENEMY_SKILL_TAGS.intersection(enemy.tags)
        if not active_tags:
            enemy.skill_timer = 9999.0
            return
        skill_duration = (
            enemy.visual_animation.animations["skill"].duration
            if enemy.visual_animation is not None
            and "skill" in enemy.visual_animation.animations
            else 0.61
        )
        enemy.motion.trigger("skill", skill_duration)
        if enemy.visual_animation is not None and "skill" in enemy.visual_animation.animations:
            # Bala, ácido, rede e demais efeitos consultam exatamente o quadro
            # de habilidade que começou agora, nunca a pose de caminhada.
            enemy.visual_animation.play("skill", restart=True)
        self.app.audio.play("ability", min_interval_ms=140)
        # No Difícil os poderes inimigos retornam um pouco antes. No Fácil o
        # multiplicador é 1, portanto o equilíbrio aprovado não se altera.
        enemy.skill_timer = random.uniform(3.4, 5.8) * float(self.difficulty_data["skill_cooldown"])
        if "runner" in enemy.tags:
            # O Corredor não teleporta nem dá dash: a folha mostra a passada
            # sustentada, enquanto a regra mantém velocidade constante e o
            # primeiro ataque dobrado definidos na própria ficha.
            enemy.rage = 0.0
        if "signal_jammer" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "signal_pulse")
            self.effects.append(
                VisualEffect(
                    "signal_pulse",
                    effect_x,
                    effect_y,
                    TEAL,
                    skill_duration,
                    scale=0.72,
                    owner=enemy,
                    anchor_kind="signal_pulse",
                )
            )
            for defender in self.defenders:
                if defender.row == enemy.row and 0 < enemy.x - defender.x < CELL_W * 2.7:
                    defender.attack_timer = max(defender.attack_timer, 0.72)
        if "dash" in enemy.tags:
            # O Surfista acelera por uma janela visível; a posição continua
            # avançando quadro a quadro e passa pela colisão varrida normal.
            enemy.rage = max(enemy.rage, 1.15)
            effect_x, effect_y = self.enemy_effect_origin(enemy, "water_splash")
            self.effects.append(VisualEffect("water_splash", effect_x, effect_y, (84, 196, 203), skill_duration, scale=0.62, owner=enemy, anchor_kind="water_splash"))
        if "naval_hunter" in enemy.tags:
            enemy.rage = max(enemy.rage, 0.86)
            effect_x, effect_y = self.enemy_effect_origin(enemy, "water_splash")
            self.effects.append(VisualEffect("water_splash", effect_x, effect_y, (84, 196, 203), skill_duration, scale=0.55, owner=enemy, anchor_kind="water_splash"))
        if "gun" in enemy.tags:
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                damage = self.scaled_enemy_damage(enemy, 20 + self.wave * 1.3)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "enemy_bullet")
                self.projectiles.append(Projectile(origin_x, origin_y, victim, victim.x, victim.y - 20, damage, "enemy_bullet", enemy, 0, False, 0.30))
        if "acid" in enemy.tags:
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 3.2]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                damage = self.scaled_enemy_damage(enemy, 16 + self.wave)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "acid")
                self.projectiles.append(Projectile(origin_x, origin_y, victim, victim.x, victim.y - 18, damage, "acid", enemy, CELL_W * 0.34, False, 0.48, effect="acid"))
        if "shock" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "signal_pulse")
            self.effects.append(VisualEffect("signal_pulse", effect_x, effect_y, TEAL, skill_duration, scale=0.76, owner=enemy, anchor_kind="signal_pulse"))
            targets = [
                defender for defender in self.defenders
                if defender.row == enemy.row and defender.x < enemy.x
                and enemy.x - defender.x < CELL_W * 2.4
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                victim.stun = max(victim.stun, 0.72)
                victim.attack_timer = max(victim.attack_timer, 0.72)
                self.effects.append(VisualEffect("electric_arc", victim.x, victim.y, TEAL, 0.42, scale=0.62))
                self.announce("Pulso da subestação: recarga atrasada.", 1.2, TEAL)
        if "net" in enemy.tags:
            targets = [
                defender for defender in self.defenders
                if defender.row == enemy.row and defender.x < enemy.x
                and enemy.x - defender.x < CELL_W * 3.0
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                victim.stun = max(victim.stun, 0.58)
                victim.attack_timer = max(victim.attack_timer, 1.05)
                self.effects.append(VisualEffect("net_cast", victim.x, victim.y - 30, (84, 196, 203), min(skill_duration, 0.72), scale=0.70))
                self.announce("Rede contaminada: cadência reduzida.", 1.2, (84, 196, 203))
        if "scream" in enemy.tags:
            self.effects.append(VisualEffect("command_aura", enemy.x, enemy.y, RED, skill_duration, scale=0.72, owner=enemy, anchor_kind="command_aura"))
            for other in self.enemies:
                if other.row == enemy.row and abs(other.x - enemy.x) < CELL_W * 2.6:
                    other.rage = max(other.rage, 3.5)
            if random.random() < 0.36:
                self.enemies.append(Enemy("caminhante" if self.region != "beach" else "boia", enemy.row, ENEMIES["caminhante" if self.region != "beach" else "boia"], self.region, self.wave, difficulty=self.difficulty, x=BOARD.right + 20))
            self.announce("Grito: a horda ganhou velocidade.", 1.2, RED)
        if "heal" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "heal_pulse")
            self.effects.append(VisualEffect("heal_pulse", effect_x, effect_y, (154, 239, 134), skill_duration, scale=0.76, owner=enemy, anchor_kind="heal_pulse"))
            nearby = [
                other for other in self.enemies
                if other is not enemy
                and other.row == enemy.row
                and abs(other.x - enemy.x) < CELL_W * 1.8
            ]
            for other in nearby:
                other.hp = min(other.max_hp, other.hp + 42)
                self.effects.append(
                    VisualEffect(
                        "heal_receive",
                        other.x,
                        other.y - 34,
                        (154, 239, 134),
                        skill_duration,
                        scale=0.52,
                        owner=other,
                        anchor_kind="heal_receive",
                    )
                )
            if self.dead_history and not enemy.revived and random.random() < 0.4:
                same_lane_dead = next(
                    (
                        (key, row, x)
                        for key, row, x in reversed(self.dead_history)
                        if row == enemy.row
                    ),
                    None,
                )
                if same_lane_dead is not None:
                    key, row, x = same_lane_dead
                else:
                    key = ""
                    row = enemy.row
                    x = enemy.x
                if key in ENEMIES:
                    revived = Enemy(key, row, ENEMIES[key], self.region, self.wave, difficulty=self.difficulty, x=x + 42)
                    revived.hp = revived.max_hp * 0.40
                    self.enemies.append(revived)
                    enemy.revived = True
        if "parasite" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "parasite_burst")
            self.effects.append(VisualEffect("parasite_burst", effect_x, effect_y, (218, 106, 76), skill_duration, scale=0.70, owner=enemy, anchor_kind="parasite_burst"))
            for defender in self.defenders:
                if defender.row == enemy.row and defender.x < enemy.x and enemy.x - defender.x < CELL_W * 2.1:
                    defender.stun = max(defender.stun, 2.6)
            self.announce("Parasita: tiro das tropas foi desabilitado.", 1.4, RED)
        if "stomp" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "ground_slam")
            self.effects.append(VisualEffect("ground_slam", effect_x, effect_y, (223, 132, 73), skill_duration, scale=0.84, owner=enemy, anchor_kind="ground_slam"))
            for defender in self.defenders:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 1.8:
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 24), "stun")
        if "steal" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "supply_snatch")
            self.effects.append(VisualEffect("supply_snatch", effect_x, effect_y, GOLD, skill_duration, scale=0.68, owner=enemy, anchor_kind="supply_snatch"))
            stolen = min(18, self.supplies)
            self.supplies -= stolen
            enemy.stolen += stolen
            self.announce("Ladrão de Suprimentos roubou carga — clique nele!", 2.0, GOLD)

    def update_enemies(self, dt: float) -> None:
        for enemy in self.enemies[:]:
            enemy.age += dt
            enemy.motion.advance(dt, "walk")
            enemy.attack_timer -= dt
            enemy.skill_timer -= dt
            enemy.stun = max(0.0, enemy.stun - dt)
            enemy.burn = max(0.0, enemy.burn - dt)
            enemy.poisoned = max(0.0, enemy.poisoned - dt)
            enemy.soaked = max(0.0, enemy.soaked - dt)
            enemy.corrosion = max(0.0, enemy.corrosion - dt)
            enemy.quarantine_mark = max(0.0, enemy.quarantine_mark - dt)
            enemy.defense_broken = max(0.0, enemy.defense_broken - dt)
            enemy.rage = max(0.0, enemy.rage - dt)
            enemy.step_timer -= dt
            enemy.dot_timer -= dt
            if enemy.attack_windup > 0:
                enemy.attack_windup = max(0.0, enemy.attack_windup - dt)
                if enemy.attack_windup <= 0:
                    victim = enemy.attack_target
                    enemy.attack_target = None
                    if victim in self.defenders and victim.hp > 0 and abs(victim.row - enemy.row) == 0:
                        # O dano coincide com o contato da mordida/martelo, não
                        # com o primeiro quadro da preparação do ataque.
                        self.app.audio.play("bite", min_interval_ms=110)
                        self.damage_defender(victim, enemy.attack_damage)
                    enemy.attack_damage = 0.0
            # Queimadura e Envenenado causam pulsos legíveis de dano. O dano
            # periódico não renova o próprio estado, portanto ambos acabam no
            # tempo previsto em vez de permanecerem ativos para sempre.
            if enemy.dot_timer <= 0 and (enemy.burn > 0 or enemy.poisoned > 0):
                dot_damage = (3.2 if enemy.burn > 0 else 0.0) + (2.25 if enemy.poisoned > 0 else 0.0)
                self.take_enemy_damage(enemy, dot_damage, "status_tick")
                enemy.dot_timer = 0.5
                if enemy not in self.enemies:
                    continue
            if enemy.corrosion > 0:
                self.take_enemy_damage(enemy, 2.0 * dt, "acid")
                if enemy not in self.enemies:
                    continue
            if enemy.skill_timer <= 0:
                self.enemy_special(enemy)
                if enemy not in self.enemies:
                    continue
            if self.update_enemy_motion(enemy, dt):
                continue
            if enemy.stun > 0:
                enemy.motion.trigger("stunned", enemy.stun)
                continue
            speed = float(enemy.data["speed"]) * (1.55 if enemy.rage > 0 else 1.0)
            if (
                enemy.age < float(getattr(enemy, "entry_reveal", 0.0))
                and "constant_speed" not in enemy.tags
            ):
                # A passagem não vira uma espera escondida: enquanto o corpo
                # é revelado, ele atravessa a boca do portão com um passo de
                # entrada mais decidido e então retoma sua velocidade normal.
                speed *= 5.0
            if enemy.soaked > 0:
                speed *= 0.68
            if enemy.poisoned > 0:
                speed *= 0.88
            blocker = self.blocker_for(enemy)
            if blocker:
                if "dig" in enemy.tags and not enemy.dig_used:
                    self.begin_dig(enemy, blocker)
                    continue
                if "jump" in enemy.tags and not enemy.jump_used:
                    self.begin_jump(enemy, blocker)
                    continue
                if enemy.attack_timer <= 0 and enemy.attack_windup <= 0:
                    scale = boss_damage_scale(self.wave) if enemy.is_boss else enemy_damage_scale(self.wave)
                    damage = self.scaled_enemy_damage(enemy, float(enemy.data["damage"]) * scale)
                    if not enemy.first_attack_done:
                        damage *= float(enemy.data.get("first_attack_multiplier", 1.0))
                        enemy.first_attack_done = True
                    if "naval_hunter" in enemy.tags and blocker.stats.get("water_only"):
                        # O traje do mergulhador foi criado para enfrentar as
                        # embarcações: a habilidade não afeta tropas em terra.
                        damage *= 1.55
                    if int(blocker.stats.get("combat_class", 0)) in tuple(enemy.data.get("devour_classes", ())):
                        # O Rastejador é lento e pode ser abatido no trajeto;
                        # se alcançar uma tropa básica/avançada, a mordida é
                        # fatal como contrapartida explícita à baixa velocidade.
                        damage = max(damage, blocker.hp + 1.0)
                    attack_duration = (
                        enemy.visual_animation.animations["bite"].duration
                        if enemy.visual_animation is not None
                        else (0.44 if enemy.is_boss else 0.34)
                    )
                    enemy.attack_target = blocker
                    enemy.attack_damage = damage
                    # A animação agora é deliberadamente mais lenta para que
                    # cada pose possa ser lida. O momento lógico do contato
                    # não pode ficar preso à duração total do clipe: a mordida
                    # acerta no avanço do corpo e a recuperação visual termina
                    # depois, sem enfraquecer o zumbi por causa da apresentação.
                    contact_cap = 0.46 if enemy.is_boss else 0.38
                    enemy.attack_windup = min(contact_cap, attack_duration * 0.42)
                    enemy.motion.trigger("attack", attack_duration)
                    enemy.attack_timer = float(enemy.data["attack"])
                elif enemy.motion.event_left <= 0:
                    enemy.motion.trigger("brace", min(0.28, max(0.08, enemy.attack_timer)))
                continue
            next_x = enemy.x - speed * dt
            crossed_blocker = self.swept_blocker_for(enemy, next_x)
            if crossed_blocker is not None:
                enemy.x = crossed_blocker.x + float(enemy.data.get("contact_distance", 58.0)) - 0.25
                # O ataque começa no quadro seguinte pela mesma rotina usada
                # para qualquer contato, mas o corpo nunca invade a hitbox.
                continue
            cart = self.lane_bombs[enemy.row]
            # O gatilho coincide com a frente visível da contenção; o invasor
            # não atravessa o trator, drone ou bomba antes de ativá-lo.
            if cart.state == "armed" and next_x <= cart.x + 28:
                enemy.x = cart.x + 28
                self.trigger_lane_bomb(enemy.row)
                continue
            enemy.x = next_x
            if enemy.x <= BOARD.left + 8:
                if cart.state == "rolling":
                    # O zumbi é segurado por um instante na saída, dando ao
                    # carrinho tempo para alcançá-lo visualmente na faixa.
                    enemy.x = max(enemy.x, BOARD.left - 2)
                    continue
            if enemy.x < BOARD.left - 42:
                self.lost = True
                self.finished = True
                self.announce("BASE INVADIDA", 10, RED)

    def update_projectiles(self, dt: float) -> None:
        for projectile in self.projectiles[:]:
            projectile.elapsed += dt
            if projectile.elapsed < 0:
                continue
            t = clamp(projectile.elapsed / projectile.travel, 0, 1)
            if t < 1:
                continue
            self.projectiles.remove(projectile)
            if projectile.friendly:
                target = projectile.target
                if isinstance(target, Enemy) and target in self.enemies:
                    self.take_enemy_damage(target, projectile.damage, projectile.effect, projectile.owner if isinstance(projectile.owner, Defender) else None)
                    if projectile.radius > 0:
                        for other in self.enemies[:]:
                            if other is target:
                                continue
                            if other.row == target.row and abs(other.x - target.x) < projectile.radius:
                                self.take_enemy_damage(other, projectile.damage * 0.72, projectile.effect, projectile.owner if isinstance(projectile.owner, Defender) else None)
                    explosive_kinds = {
                        "grenade", "grenade_40mm", "mortar", "mortar_shell",
                        "bazooka", "rpg7_rocket", "torpedo", "compact_torpedo",
                    }
                    if projectile.kind == "gas_grenade":
                        # A munição não vira um jato. Ela chega em arco, abre
                        # no chão e deixa uma nuvem baixa dentro da própria
                        # faixa, coerente com o equipamento anticontaminação.
                        self.effects.append(
                            VisualEffect(
                                "toxic_wave", projectile.target_x,
                                projectile.target_y - 10, (132, 239, 80),
                                1.05, scale=1.08,
                            )
                        )
                    elif projectile.kind in explosive_kinds:
                        scale = (
                            1.35
                            if projectile.kind in {"bazooka", "rpg7_rocket"}
                            else (1.12 if projectile.kind in {"mortar", "mortar_shell"} else 0.96)
                        )
                        self.explosion(projectile.target_x, projectile.target_y, GOLD, 16, scale=scale)
            else:
                target = projectile.target
                if isinstance(target, Defender) and target in self.defenders:
                    self.damage_defender(target, projectile.damage, projectile.effect)
                    if projectile.radius:
                        cross_lanes = isinstance(projectile.owner, Enemy) and projectile.owner.is_boss
                        for other in self.defenders[:]:
                            if other is target:
                                continue
                            same_lane = other.row == target.row
                            boss_reach = cross_lanes and abs(other.y - target.y) < CELL_H * 0.75
                            if (same_lane or boss_reach) and abs(other.x - target.x) < projectile.radius:
                                self.damage_defender(other, projectile.damage * 0.5, projectile.effect)
                    if projectile.kind == "acid":
                        self.effects.append(VisualEffect("toxic_impact", projectile.target_x, projectile.target_y, (132, 239, 80), 0.30, scale=0.78))
                    elif projectile.kind == "torpedo":
                        self.effects.append(VisualEffect("water_impact", projectile.target_x, projectile.target_y, (102, 224, 244), 0.32, scale=0.92))
                    else:
                        # Tiros inimigos recebem um impacto curto de munição;
                        # não fabricam uma explosão de granada a cada acerto.
                        self.effects.append(VisualEffect("ballistic_impact", projectile.target_x, projectile.target_y, (241, 198, 122), 0.18, scale=0.30))

    def update_particles(self, dt: float) -> None:
        for particle in self.particles[:]:
            particle.ttl -= dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += particle.gravity * dt
            if particle.ttl <= 0:
                self.particles.remove(particle)
        for text in self.texts[:]:
            text.ttl -= dt
            text.y -= 20 * dt
            if text.ttl <= 0:
                self.texts.remove(text)
        for effect in self.effects[:]:
            effect.elapsed += dt
            if effect.elapsed >= effect.duration:
                self.effects.remove(effect)
        for fallen in self.fallen[:]:
            fallen.elapsed += dt
            if fallen.elapsed >= fallen.duration:
                self.fallen.remove(fallen)

    def update_wave(self, dt: float) -> None:
        if self.finished:
            return
        if not self.started_wave:
            self.intermission -= dt
            if self.intermission <= 0:
                self.start_next_wave()
            return
        if self.orders:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                # O alerta grande pertence à chegada do chefe, e não ao início
                # genérico da onda. Enquanto ele está visível, a ordem fica
                # segurada; terminado o aviso, o chefe entra de fato.
                next_order = self.orders[0]
                if next_order.boss:
                    if not self.boss_alert_pending:
                        boss_data = BOSSES[next_order.key]
                        self.boss_alert_pending = True
                        self.boss_warning = 3.0
                        self.boss_banner_name = str(boss_data["name"])
                        self.boss_banner_subtitle = "CHEFE E ESCOLTA EM APROXIMAÇÃO"
                        self.announce(f"ALERTA: {self.boss_banner_name} chegando!", 3.0, RED)
                        return
                    if self.boss_warning > 0:
                        return
                    self.boss_alert_pending = False
                order = self.orders.pop(0)
                self.spawn_enemy(order)
                self.spawn_timer = order.wait
        elif not self.enemies:
            if self.wave >= TOTAL_WAVES:
                self.finished = True
                self.victory = True
                self.announce("REGIÃO PROTEGIDA!", 10, GOLD)
                return
            self.started_wave = False
            self.intermission = 5.0
            # Mais ajuda nas primeiras ondas e recompensa praticamente plana
            # no final: o jogo deixa de ser cruel no começo e deixa de inundar
            # o jogador de recursos quando a composição já está pronta.
            reward_base = max(16, 27 - self.wave)
            reward = int(round(reward_base * float(self.difficulty_data["supply_gain"])))
            if self.wave % 4 == 0:
                reward += int(round(14 * float(self.difficulty_data["supply_gain"])))
            self.supplies = min(int(self.difficulty_data["supply_cap"]), self.supplies + reward)
            self.announce(f"Onda {self.wave} concluída: +{reward} suprimentos.", 2.4, GOLD)

    def update(self, dt: float) -> None:
        # Pausa congela relógios, recargas, projéteis, inimigos e contagens. A
        # interface continua recebendo clique para MENU ou para retomar.
        if self.paused:
            return
        self.ambient_phase += dt
        self.shake = max(0, self.shake - dt)
        self.global_toxic = max(0, self.global_toxic - dt)
        self.boss_warning = max(0, self.boss_warning - dt)
        self.message_timer = max(0, self.message_timer - dt)
        for index, value in enumerate(self.card_cooldowns):
            self.card_cooldowns[index] = max(0, value - dt)
        self.update_wave(dt)
        self.update_deployments(dt)
        self.update_defenders(dt)
        self.update_enemies(dt)
        self.update_lane_bombs(dt)
        self.update_projectiles(dt)
        self.update_particles(dt)
        self.update_production_animations(dt)

    def enemy_at(self, pos: tuple[int, int]) -> Enemy | None:
        for enemy in reversed(self.enemies):
            if enemy.hitbox().inflate(16, 16).collidepoint(pos):
                return enemy
        return None

    def click_enemy(self, enemy: Enemy) -> bool:
        if "steal" not in enemy.tags:
            return False
        returned = int(enemy.stolen) + 28
        self.supplies += returned
        self.announce(f"Carga recuperada: +{returned} suprimentos!", 2.0, GOLD)
        self.kill_enemy(enemy)
        return True

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.finished:
            return
        if self.menu_rect().collidepoint(pos):
            self.app.leave_battle_to_title()
            return
        if self.pause_rect().collidepoint(pos):
            self.paused = not self.paused
            self.announce("Partida pausada." if self.paused else "Partida retomada.", 1.5, GOLD)
            return
        if self.paused:
            return
        if self.difficulty != "easy" and self.remove_rect().collidepoint(pos):
            self.remove_mode = not self.remove_mode
            self.announce("Ferramenta de remoção ativada: clique em uma defesa." if self.remove_mode else "Ferramenta de remoção desativada.", 1.8, TEAL)
            return
        if self.next_wave_rect().collidepoint(pos):
            if not self.started_wave:
                self.intermission = 0
                self.start_next_wave()
            else:
                self.announce("A horda atual ainda está em andamento.", 1.3, GRAY)
            return
        thief = self.enemy_at(pos)
        if thief and self.click_enemy(thief):
            return
        for index, rect in enumerate(self.card_rects()):
            if rect.collidepoint(pos):
                if self.card_cooldowns[index] <= 0:
                    self.selected_card = index
                    self.remove_mode = False
                    key, display = self.selected[index]
                    # Confirmação breve, sem devolver a antiga barra fixa de
                    # descrição: a moldura dourada, a arte e o nome seguem a
                    # mesma chave que será usada por place().
                    self.announce(f"Selecionado: {display}.", 1.15, self.region_color())
                return
        cell = self.board_cell_at(pos)
        if cell:
            row, col = cell
            if self.remove_mode:
                self.remove_defender(row, col)
            else:
                self.place(row, col)

    def card_rects(self) -> list[pygame.Rect]:
        count = len(self.selected)
        width = min(138, (WIDTH - 185) // max(1, count))
        return [pygame.Rect(10 + index * width, 8, width - 5, 102) for index in range(count)]


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
                pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
                presenter = OpenGLPresenter(WIDTH, HEIGHT)
                self.presenter = presenter
                self.renderer_label = presenter.info.label
                self.overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA, 32)
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
        tint = REGIONS.get(self.battle.region if self.battle else self.region, REGIONS["city"])["accent"]
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
        self.scenario_runtime.update(dt, self.battle if self.scene == "battle" else None)
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
                        self.presenter.preload_sprites(self.gpu_preload_queue[self.gpu_preloaded:batch_end])
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
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
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
                pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
                pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s,
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
                    self.battle.keyboard_row = min(ROWS - 1, self.battle.keyboard_row + 1)
                self.audio.play("ui", min_interval_ms=45)
            elif self.control_mode == "keyboard" and key in (pygame.K_q, pygame.K_e):
                direction = -1 if key == pygame.K_q else 1
                count = len(self.battle.selected)
                self.battle.selected_card = (self.battle.selected_card + direction) % count
                self.battle.remove_mode = False
                self.audio.play("ui")
            elif self.control_mode == "keyboard" and key in (pygame.K_RETURN, pygame.K_f, pygame.K_SPACE):
                if self.battle.remove_mode:
                    self.battle.remove_defender(self.battle.keyboard_row, self.battle.keyboard_col)
                elif self.battle.card_cooldowns[self.battle.selected_card] <= 0:
                    self.battle.place(self.battle.keyboard_row, self.battle.keyboard_col)
                else:
                    self.battle.announce("Esta carta ainda está recarregando.", 1.3, GRAY)
            elif self.control_mode == "keyboard" and key in (pygame.K_n, pygame.K_TAB):
                if not self.battle.started_wave:
                    self.battle.intermission = 0
                    self.battle.start_next_wave()
                else:
                    self.battle.announce("A horda atual ainda está em andamento.", 1.3, GRAY)
            elif key == pygame.K_r and self.battle.difficulty != "easy":
                self.battle.remove_mode = not self.battle.remove_mode
                self.battle.announce("Ferramenta de remoção ativada." if self.battle.remove_mode else "Ferramenta de remoção desativada.", 1.4, TEAL)
            elif key == pygame.K_p:
                self.battle.paused = not self.battle.paused
                self.battle.announce("Partida pausada." if self.battle.paused else "Partida retomada.", 1.4, GOLD)
            elif self.control_mode == "mouse" and key == pygame.K_SPACE and not self.battle.started_wave:
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
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
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
                if pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50).collidepoint(pos):
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
                self.scene, self.dossier_kind, self.character_region = "characters", "units", "city"
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
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"
        elif pygame.Rect(245, 646, 170, 44).collidepoint(pos) and self.story_page > 0:
            self.story_page -= 1
        elif pygame.Rect(WIDTH - 415, 646, 170, 44).collidepoint(pos) and self.story_page < 2:
            self.story_page += 1

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
        self.selection = [(key, self.card_display_name(region, key)) for key in available[:8]]
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
                (key, self.card_display_name(self.region, key), pygame.Rect(x, y, 238, 215))
            )
        return cards

    @staticmethod
    def selection_inspect_button(card_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(card_rect.x + 119, card_rect.bottom - 39, card_rect.width - 129, 27)

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
            {"name": data["name"], "sub": "Chefe" if key in BOSSES else "Inimigo", "ability": data["ability"], "hp": int(data["hp"]), "key": key}
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
            self.save["best_wave"][region] = max(self.save["best_wave"].get(region, 0), TOTAL_WAVES)
            save_campaign(self.save)
        self.battle = None
        self.scene = "campaign"

    def leave_battle_to_title(self) -> None:
        """Saída voluntária sem registrar vitória, derrota ou progresso falso."""
        self.battle = None
        self.scene = "title"
        self.scene_elapsed = 0.0

    def button_rect(self, label: str, x: int, y: int, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(x, y, w, h)

    def draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[float, float], anchor: str = "topleft", shadow: bool = False) -> pygame.Rect:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        if shadow:
            shadow_surface = font.render(text, True, (0, 0, 0))
            shadow_rect = shadow_surface.get_rect()
            setattr(shadow_rect, anchor, (int(pos[0] + 2), int(pos[1] + 2)))
            self.screen.blit(shadow_surface, shadow_rect)
        self.screen.blit(surface, rect)
        return rect

    def panel(self, rect: pygame.Rect, alpha: int = 210, border: tuple[int, int, int] = (91, 106, 112), radius: int = 10) -> None:
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (12, 20, 25, alpha), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, (*border, min(255, alpha + 25)), surface.get_rect(), width=2, border_radius=radius)
        self.screen.blit(surface, rect)

    def button(self, label: str, rect: pygame.Rect, accent: tuple[int, int, int], enabled: bool = True) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
        outer = tuple(min(255, c + 25) for c in accent) if hover else accent
        color = outer if enabled else (67, 73, 76)
        pygame.draw.rect(self.screen, (8, 13, 17), rect.inflate(4, 4), border_radius=8)
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.screen, (228, 235, 228), rect, width=1, border_radius=7)
        self.draw_text(label, self.fonts.h2, INK if enabled else GRAY, rect.center, "center")

    def draw_loading(self) -> None:
        loading_art = self.assets.images.get("loading_beta3")
        if loading_art is not None:
            self.screen.blit(loading_art, (0, 0))
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((3, 8, 12, 54))
            self.screen.blit(veil, (0, 0))
        else:
            self.screen.fill((8, 13, 18))
        asset_progress = self.assets.loaded / max(1, self.assets.total)
        if self.presenter is not None:
            gpu_total = len(self.gpu_preload_queue)
            gpu_progress = (self.gpu_preloaded / gpu_total) if gpu_total else (1.0 if self.assets.complete else 0.0)
            progress = asset_progress * 0.74 + gpu_progress * 0.26
        else:
            progress = asset_progress
        # A arte entregue pelo usuário já contém o título. O painel discreto
        # abaixo não a redesenha nem esconde o logotipo central.
        panel = pygame.Rect(WIDTH // 2 - 282, HEIGHT - 150, 564, 108)
        self.panel(panel, 204, (166, 130, 62), 12)
        self.draw_text(f"{VERSION} — CARREGANDO", self.fonts.h2, WHITE, (panel.centerx, panel.y + 17), "center", True)
        bar = pygame.Rect(panel.x + 42, panel.y + 51, panel.width - 84, 18)
        pygame.draw.rect(self.screen, (31, 42, 47), bar, border_radius=9)
        pygame.draw.rect(self.screen, TEAL, (bar.x, bar.y, int(bar.width * progress), bar.height), border_radius=9)
        if self.presenter is not None and self.assets.complete:
            status = f"Enviando atores para a GPU  {self.gpu_preloaded}/{len(self.gpu_preload_queue)}"
        else:
            status = f"Preparando artes e animações  {self.assets.loaded}/{self.assets.total}"
        self.draw_text(status, self.fonts.small, WHITE, (panel.centerx, panel.y + 79), "center")
        if self.assets.error:
            self.draw_text(self.assets.error, self.fonts.small, RED, (panel.centerx, panel.y - 18), "center")

    def draw_title(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((3, 8, 12, 92))
        self.screen.blit(tint, (0, 0))
        self.panel(pygame.Rect(36, 80, 336, 548), 210, (166, 130, 62), 14)
        self.draw_text("SOLDADOS", self.fonts.title, (242, 239, 218), (62, 108), shadow=True)
        self.draw_text("VS", self.fonts.small, GOLD, (338, 153), "topright", True)
        self.draw_text("ZUMBIS", self.fonts.title, (154, 206, 127), (62, 166), shadow=True)
        self.draw_text("DEFENDA. RECARREGUE. RESISTA.", self.fonts.small, GRAY, (64, 224))
        for label, rect in self.title_buttons():
            accent = GOLD if label == "INICIAR" else (81, 145, 137)
            self.button(label, rect, accent)
        self.draw_text(f"{VERSION} • Cidade • Deserto • Cachoeira", self.fonts.small, WHITE, (40, HEIGHT - 28))
        self.draw_text("Artes originais • campanha de 12 ondas", self.fonts.small, WHITE, (WIDTH - 36, HEIGHT - 28), "topright")

    def draw_difficulty(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 178))
        self.screen.blit(veil, (0, 0))
        self.draw_text("ESCOLHA A DIFICULDADE", self.fonts.title, WHITE, (WIDTH / 2, 42), "center", True)
        self.draw_text("O modo altera recursos, força dos inimigos e ritmo das hordas.", self.fonts.body, GOLD, (WIDTH / 2, 91), "center")
        descriptions = {
            "easy": (
                "COMEÇAR TRANQUILO",
                ("175 suprimentos iniciais", "Limite de reserva: 420", "Inimigos mais frágeis para aprender"),
            ),
            "medium": (
                "CAMPANHA EQUILIBRADA",
                ("135 suprimentos iniciais", "Pressão progressiva e equilibrada", "12 ondas em três atos táticos"),
            ),
            "hard": (
                "SOBREVIVÊNCIA VETERANA",
                ("105 suprimentos iniciais", "Limite de reserva: 240", "Hordas mais rápidas e resistentes"),
            ),
        }
        for index, (key, button_rect) in enumerate(self.difficulty_buttons()):
            profile = difficulty_profile(key)
            card = pygame.Rect(button_rect.x - 25, 150, button_rect.width + 50, 370)
            self.panel(card, 235, profile["accent"], 14)
            subtitle, lines = descriptions[key]
            self.draw_text(profile["label"], self.fonts.title, profile["accent"], (card.centerx, card.y + 32), "center", True)
            self.draw_text(subtitle, self.fonts.small, WHITE, (card.centerx, card.y + 92), "center")
            for line_index, line in enumerate(lines):
                y = card.y + 148 + line_index * 53
                pygame.draw.circle(self.screen, profile["accent"], (card.x + 31, y + 8), 5)
                self.draw_wrapped(line, self.fonts.small, WHITE, pygame.Rect(card.x + 46, y - 7, card.width - 64, 31), 2)
            self.draw_wrapped(profile["summary"], self.fonts.tiny, GRAY, pygame.Rect(card.x + 23, card.bottom - 71, card.width - 46, 38), 2, center=True)
            self.button(f"ESCOLHER {profile['label']}", button_rect, profile["accent"])
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_campaign(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 11, 16, 170))
        self.screen.blit(veil, (0, 0))
        self.draw_text("MAPA DA CAMPANHA", self.fonts.title, WHITE, (WIDTH / 2, 38), "center", True)
        profile = difficulty_profile(self.difficulty)
        self.draw_text(f"Modo {profile['label']} — {profile['summary']}", self.fonts.body, profile["accent"], (WIDTH / 2, 84), "center")
        self.draw_text("Escolha Cidade, Deserto ou Cachoeira. São 12 ondas: duas comuns, um sub-boss e um boss por ato.", self.fonts.small, GOLD, (WIDTH / 2, 111), "center")
        for index, region in enumerate(("city", "desert", "beach")):
            info = REGIONS[region]
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            unlocked = True
            background = self.assets.images[f"{region}_bg"]
            crop = pygame.Rect(index * 160, 150, 360, 208)
            image = pygame.Surface((360, 210))
            image.blit(background, (0, 0), crop)
            self.screen.blit(image, rect)
            self.panel(rect, 105 if unlocked else 215, info["accent"] if unlocked else (75, 75, 75), 14)
            if not unlocked:
                lock = pygame.Rect(rect.centerx - 28, rect.y + 104, 56, 66)
                pygame.draw.rect(self.screen, (49, 54, 60), lock, border_radius=9)
                pygame.draw.arc(self.screen, GRAY, (lock.x + 9, lock.y - 27, 38, 40), 0, math.pi, 5)
                self.draw_text("BLOQUEADA", self.fonts.h2, GRAY, (rect.centerx, rect.y + 184), "center")
            else:
                self.draw_text(info["short"], self.fonts.h1, WHITE, (rect.centerx, rect.y + 222), "center", True)
                self.draw_text(info["tag"], self.fonts.small, info["accent"], (rect.centerx, rect.y + 252), "center")
                best = self.save["best_wave"].get(region, 0)
                status = "REGIÃO PROTEGIDA" if region in self.save["completed"] else f"Melhor: onda {best}/{TOTAL_WAVES}"
                self.draw_text(status, self.fonts.small, GOLD if region in self.save["completed"] else WHITE, (rect.centerx, rect.y + 286), "center")
                self.button("PREPARAR DEFESA", pygame.Rect(rect.x + 55, rect.y + 304, 250, 34), info["accent"])
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_selection(self) -> None:
        region = REGIONS[self.region]
        self.screen.blit(self.assets.images[f"{self.region}_bg"], (0, 0))
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 11, 14, 157))
        self.screen.blit(shade, (0, 0))
        profile = difficulty_profile(self.difficulty)
        self.draw_text(f"SELEÇÃO DE CARTAS — {region['name'].upper()} — {profile['label']}", self.fonts.h1, WHITE, (WIDTH / 2, 20), "center", True)
        self.draw_text("Escolha até três cartas • clique em DETALHES para inspecionar", self.fonts.small, profile["accent"], (WIDTH / 2, 56), "center")
        self.draw_text(f"{len(self.selection)}/3 selecionadas", self.fonts.h2, region["accent"], (WIDTH - 40, 66), "topright")
        for key, display, rect in self.selection_cards():
            data = DEFENSES[key]
            chosen = (key, display) in self.selection
            self.panel(rect, 232, GOLD if chosen else (91, 105, 107), 10)
            portrait = pygame.Rect(rect.x + 8, rect.y + 38, 104, 158)
            self.draw_portrait_backdrop(portrait, region["accent"])
            sprite = self.card_sprite(self.region, key, int(data["sprite"]))
            self.blit_actor_in_rect(sprite, portrait, 146, outline=region["accent"])
            self.draw_wrapped(display.upper(), self.fonts.tiny, WHITE, pygame.Rect(rect.x + 12, rect.y + 11, rect.width - 45, 24), 1)
            stat_x = rect.x + 120
            reload_seconds = weapon_reload_seconds(data)
            reload_text = f"{reload_seconds:.1f}s" if reload_seconds > 0 else "—"
            self.draw_text(f"VIDA  {int(data['hp'])}", self.fonts.small, WHITE, (stat_x, rect.y + 55))
            self.draw_text(f"DANO  {int(data['damage'])}", self.fonts.small, GOLD, (stat_x, rect.y + 88))
            self.draw_text(f"RECARGA  {reload_text}", self.fonts.tiny, TEAL, (stat_x, rect.y + 123))
            inspect_rect = self.selection_inspect_button(rect)
            self.button("DETALHES", inspect_rect, (78, 112, 121))
            if chosen:
                check_x, check_y = rect.right - 24, rect.y + 22
                pygame.draw.line(self.screen, GOLD, (check_x - 8, check_y), (check_x - 2, check_y + 7), 4)
                pygame.draw.line(self.screen, GOLD, (check_x - 2, check_y + 7), (check_x + 9, check_y - 8), 4)
        selected_names = " • ".join(display for _key, display in self.selection) or "nenhuma carta"
        self.draw_text(f"EQUIPE: {selected_names}", self.fonts.tiny, WHITE, (WIDTH / 2, 620), "center", True)
        self.button("VOLTAR", self.button_rect("Voltar", 45, 650, 160, 46), (98, 126, 137))
        self.button("INICIAR MISSÃO", pygame.Rect(WIDTH - 290, 650, 240, 46), region["accent"], 1 <= len(self.selection) <= 3)
        if self.selection_inspect_key is not None:
            self.draw_selection_inspection(self.selection_inspect_key)

    def draw_selection_inspection(self, key: str) -> None:
        """Abre os dados completos somente após o clique em DETALHES."""
        if key not in DEFENSES or key not in self.available_selection_keys():
            self.selection_inspect_key = None
            return
        data = DEFENSES[key]
        display = self.card_display_name(self.region, key)
        accent = REGIONS[self.region]["accent"]
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((2, 5, 8, 214))
        self.screen.blit(veil, (0, 0))
        modal = pygame.Rect(160, 74, 960, 536)
        self.panel(modal, 248, accent, 16)
        portrait = pygame.Rect(modal.x + 28, modal.y + 55, 300, 390)
        self.draw_portrait_backdrop(portrait, accent)
        sprite = self.card_sprite(self.region, key, int(data["sprite"]))
        self.blit_actor_in_rect(sprite, portrait, 332, outline=accent)
        text_x = modal.x + 360
        text_w = modal.width - 392
        self.draw_text(display.upper(), self.fonts.h1, WHITE, (text_x, modal.y + 38), shadow=True)
        self.draw_text(str(data.get("tactical_unit", "Unidade regional")), self.fonts.small, accent, (text_x, modal.y + 78))
        reload_seconds = weapon_reload_seconds(data)
        stats = f"VIDA {int(data['hp'])}  •  DANO {int(data['damage'])}  •  RECARGA {reload_seconds:.1f}s  •  CUSTO {int(data['cost'])}"
        self.draw_wrapped(stats, self.fonts.tiny, GOLD, pygame.Rect(text_x, modal.y + 108, text_w, 36), 2)
        self.draw_text("HISTÓRIA", self.fonts.tiny, GRAY, (text_x, modal.y + 158))
        self.draw_wrapped(str(data["lore"]), self.fonts.small, WHITE, pygame.Rect(text_x, modal.y + 179, text_w, 65), 3)
        self.draw_text("FUNÇÃO NO CAMPO", self.fonts.tiny, GRAY, (text_x, modal.y + 260))
        self.draw_wrapped(str(data["tactical_function"]), self.fonts.small, TEAL, pygame.Rect(text_x, modal.y + 281, text_w, 48), 2)
        self.draw_text("POR QUE ESSA CARTA É NECESSÁRIA", self.fonts.tiny, GRAY, (text_x, modal.y + 348))
        self.draw_wrapped(str(data["mechanical_need"]), self.fonts.small, WHITE, pygame.Rect(text_x, modal.y + 369, text_w, 65), 3)
        self.button("FECHAR DETALHES", self.selection_inspection_close_rect(), accent)

    def draw_characters(self) -> None:
        """Exibe todos os defensores e os infectados ativos da região."""
        region = self.character_region
        info = REGIONS[region]
        self.screen.blit(self.assets.images[f"{region}_bg"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 184))
        self.screen.blit(veil, (0, 0))
        self.draw_text("PERSONAGENS DO JOGO", self.fonts.title, WHITE, (WIDTH / 2, 24), "center", True)
        for index, key in enumerate(("city", "desert", "beach")):
            rect = pygame.Rect(340 + index * 205, 82, 190, 42)
            self.button(REGIONS[key]["short"], rect, REGIONS[key]["accent"] if key == region else (76, 92, 98))
        self.button("SOLDADO", pygame.Rect(424, 136, 205, 40), info["accent"] if self.dossier_kind == "units" else (70, 80, 85))
        self.button("ZUMBI", pygame.Rect(650, 136, 205, 40), (126, 196, 91) if self.dossier_kind == "zombies" else (70, 80, 85))
        is_unit = self.dossier_kind == "units"
        keys = self.character_keys()
        if not keys:
            self.draw_text("Nenhum personagem disponível.", self.fonts.h1, RED, (WIDTH / 2, 330), "center")
            self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
            return
        self.character_index = int(clamp(self.character_index, 0, len(keys) - 1))
        self.button("ANTERIOR", pygame.Rect(260, 184, 180, 40), (70, 88, 96))
        self.draw_text(f"{self.character_index + 1}/{len(keys)}", self.fonts.h2, WHITE, (WIDTH / 2, 204), "center")
        self.button("PRÓXIMO", pygame.Rect(WIDTH - 440, 184, 180, 40), (70, 88, 96))

        key = keys[self.character_index]
        data = DEFENSES[key] if is_unit else ({**ENEMIES, **BOSSES})[key]
        actor = (DEFENDER_ACTOR_BY_KEY if is_unit else ENEMY_ACTOR_BY_KEY)[key]
        if self.assets.production_clips is None:
            self.assets.prepare_production_animations()
        clip_bank = self.assets.production_clips or {}
        if actor not in clip_bank:
            self.draw_text("Arte do personagem ainda não foi carregada.", self.fonts.h1, RED, (WIDTH / 2, 330), "center")
            self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
            return
        sprite = clip_bank[actor]["idle" if is_unit else "move"].frames[1]
        # Chefes largos não podem usar um quadro estreito da folha de combate
        # como retrato. Serra, tubos, braços e pernas atravessavam a fronteira
        # matemática da célula e apareciam cortados no dossiê. Os três retratos
        # completos de cada região têm fundo transparente e enquadramento
        # próprio, sem alterar as animações usadas no campo.
        boss_keys = REGION_BOSSES.get(region, ())
        if not is_unit and key in boss_keys:
            portraits = self.assets.boss_portraits.get(region, [])
            portrait_index = boss_keys.index(key)
            if portrait_index < len(portraits):
                sprite = portraits[portrait_index]

        card = pygame.Rect(210, 232, 860, 358)
        accent = info["accent"] if is_unit else (132, 207, 93)
        self.panel(card, 240, accent, 16)
        portrait = pygame.Rect(card.x + 28, card.y + 34, 245, 278)
        self.draw_portrait_backdrop(portrait, accent)
        crawler = key in CRAWLER_ENEMIES
        dedicated_boss_portrait = not is_unit and key in boss_keys
        self.blit_actor_in_rect(
            sprite,
            portrait,
            254 if dedicated_boss_portrait else (238 if not crawler else 164),
            source_body_height=(
                None
                if dedicated_boss_portrait
                else (130.0 if is_unit else (92.0 if crawler else 136.0))
            ),
            outline=accent,
        )
        text_x = card.x + 306
        self.draw_text(str(data.get("base", data.get("name"))), self.fonts.h1, WHITE, (text_x, card.y + 32), shadow=True)
        faction = {
            "city": "Polícia dos Estados Unidos • Terminal Félix-13",
            "desert": "Forças Armadas do Egito • Escavação Khepra",
            "beach": "Marinha do Brasil • Cachoeira Contaminada",
        }[region]
        self.draw_text(faction if is_unit else info["tag"], self.fonts.small, accent, (text_x, card.y + 72))
        if is_unit:
            if data["role"] == "radio":
                stats = (
                    f"VIDA {int(data['hp'])}     SUPRIMENTOS +{int(data['supply_gain'])}",
                    f"CICLO {float(data['cooldown']):.1f}s     NÃO ATACA     CARTA 10s",
                )
            else:
                stats = (
                    f"VIDA {int(data['hp'])}     DANO {int(data['damage'])}     ALCANCE {int(data['range'])}",
                    f"MUNIÇÃO {int(data['ammo'])}     RECARGA {weapon_reload_seconds(data):.1f}s     CARTA 10s",
                )
        else:
            action = "rastejar • morder" if crawler else ("correr • avançar" if "dash" in data.get("tags", ()) else "caminhar • morder")
            stats = (
                f"VIDA {int(data['hp'])}     DANO {int(data['damage'])}     VELOCIDADE {int(data['speed'])}",
                f"AÇÃO: {action} • receber dano • desaparecer",
            )
        for index, line in enumerate(stats):
            box = pygame.Rect(text_x, card.y + 105 + index * 49, 522, 37)
            pygame.draw.rect(self.screen, (20, 31, 36), box, border_radius=8)
            self.draw_text(line, self.fonts.small, GOLD if index == 0 else TEAL, (box.x + 14, box.y + 10))
        if is_unit:
            self.draw_wrapped(str(data["lore"]), self.fonts.small, WHITE, pygame.Rect(text_x, card.y + 205, 522, 48), 2)
            self.draw_wrapped("FUNÇÃO: " + str(data["tactical_function"]), self.fonts.tiny, TEAL, pygame.Rect(text_x, card.y + 261, 522, 30), 2)
            self.draw_wrapped("NECESSÁRIA: " + str(data["mechanical_need"]), self.fonts.tiny, GOLD, pygame.Rect(text_x, card.y + 296, 522, 35), 2)
        else:
            counter = str(data.get("counter_label", "Dano concentrado"))
            defense = str(data.get("defense_name", "sem defesa especial"))
            self.draw_wrapped(str(data["ability"]), self.fonts.body, WHITE, pygame.Rect(text_x, card.y + 205, 522, 62), 3)
            self.draw_wrapped(f"DEFESA: {defense} • COUNTER: {counter}", self.fonts.tiny, GOLD, pygame.Rect(text_x, card.y + 282, 522, 38), 2)
        self.draw_text("INTEGRADO • arte, animação e ficha próprias desta região", self.fonts.tiny, GRAY, (text_x, card.bottom - 22))
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_comic_bubble(
        self,
        rect: pygame.Rect,
        text: str,
        tail: tuple[int, int],
    ) -> None:
        """Balão de fala verdadeiro, com cauda apontando para o personagem."""
        fill = (255, 250, 224)
        border = (22, 24, 25)
        attach_x = int(clamp(tail[0], rect.left + 24, rect.right - 24))
        attach_y = rect.bottom - 3 if tail[1] >= rect.centery else rect.top + 3
        pygame.draw.polygon(
            self.screen,
            fill,
            ((attach_x - 12, attach_y), (attach_x + 12, attach_y), tail),
        )
        pygame.draw.lines(
            self.screen,
            border,
            False,
            ((attach_x - 12, attach_y), tail, (attach_x + 12, attach_y)),
            3,
        )
        pygame.draw.rect(self.screen, fill, rect, border_radius=18)
        pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
        self.draw_wrapped(text, self.fonts.small, INK, rect.inflate(-18, -13), 3, center=True)

    def draw_comic_actor(
        self,
        actor: str,
        state: str,
        frame_index: int,
        point: tuple[int, int],
        body_height: int,
        *,
        flip: bool = False,
    ) -> pygame.Rect:
        assert self.assets.production_clips is not None
        frames = self.assets.production_clips[actor][state].frames
        sprite = frames[frame_index % len(frames)]
        content = sprite.get_bounding_rect(min_alpha=8)
        sprite = sprite.subsurface(content).copy()
        source_height = 130.0 if actor.endswith("guard") else 136.0
        width, height = animated_actor_render_scale(
            sprite,
            1.0,
            body_height=body_height,
            source_body_height=source_height,
        )
        rendered = pygame.transform.smoothscale(sprite, (max(1, round(width)), max(1, round(height))))
        if flip:
            rendered = pygame.transform.flip(rendered, True, False)
        rect = rendered.get_rect(midbottom=point)
        self.screen.blit(rendered, rect)
        return rect

    def draw_story(self) -> None:
        """Prólogo em quadrinhos: personagens, ação, falas e continuidade."""
        pages = (
            {
                "region": "city",
                "title": "1 • O ACIDENTE FÉLIX",
                "captions": (
                    "NOVA YORK — 23h47. O reator experimental perde contenção.",
                    "A descarga mistura radiação, fármacos e material biológico.",
                    "A polícia fecha o Terminal Félix-13 — tarde demais.",
                ),
                "dialogue": (
                    "Central, o reator da Félix explodiu!",
                    "Eles eram funcionários... agora estão vindo para a rua.",
                    "Fechem o Terminal! Ninguém passa!",
                ),
                "sfx": ("WAA-OOO!", "KRA-KOOM!", "CLAC!"),
            },
            {
                "region": "desert",
                "title": "2 • OS MORTOS DE KHEPRA",
                "captions": (
                    "EGITO. O vento leva partículas da Félix até a escavação.",
                    "Sob a areia, corpos preservados despertam contaminados.",
                    "O Sa'ka forma quatro linhas diante da necrópole.",
                ),
                "dialogue": (
                    "Comando, a areia ao redor da tumba está brilhando!",
                    "Isso não é magia. É a mesma praga de Nova York.",
                    "Sa'ka, armas prontas! Eles estão saindo!",
                ),
                "sfx": ("WHOOOSH", "KRRRAA...", "CHK-CHK!"),
            },
            {
                "region": "beach",
                "title": "3 • A CACHOEIRA CONTAMINADA",
                "captions": (
                    "MINAS GERAIS. Resíduos alcançam o rio acima da cachoeira.",
                    "A correnteza transforma banhistas e equipes de resgate.",
                    "A Marinha fecha as margens enquanto prepara embarcações para os canais.",
                ),
                "dialogue": (
                    "A água ficou verde. Retirem todos da correnteza!",
                    "Há infectados nas margens e movimento dentro dos canais!",
                    "Marinheiros na terra; barcos e submarinos nos canais!",
                ),
                "sfx": ("SPLASH!", "GHHH...", "TAC!"),
            },
        )
        page = pages[self.story_page]
        region = page["region"]
        accent = REGIONS[region]["accent"]
        bg = self.assets.images[f"{region}_bg"]
        defender_actor = DEFENDER_ACTOR_BY_KEY[BASIC_DEFENDER_BY_REGION[region]]
        enemy_actor = ENEMY_ACTOR_BY_KEY[BASIC_ENEMY_BY_REGION[region]]

        self.screen.fill((12, 11, 10))
        self.draw_text("HISTÓRIA DO JOGO", self.fonts.title, WHITE, (WIDTH / 2, 18), "center", True)
        self.draw_text(page["title"], self.fonts.h2, accent, (WIDTH / 2, 66), "center")
        panels = (
            (pygame.Rect(55, 103, 1170, 235), pygame.Rect(0, 70, 1280, 420)),
            (pygame.Rect(55, 356, 565, 246), pygame.Rect(0, 140, 690, 480)),
            (pygame.Rect(660, 356, 565, 246), pygame.Rect(590, 120, 690, 500)),
        )
        for index, (dest, source) in enumerate(panels):
            image = pygame.transform.smoothscale(bg.subsurface(source), dest.size)
            self.screen.blit(image, dest)
            # Retícula e borda grossa deixam o quadro com leitura impressa,
            # sem transformar o cenário numa simples miniatura do mapa.
            shade = pygame.Surface(dest.size, pygame.SRCALPHA)
            shade.fill((15, 15, 18, 34 if index == 0 else 50))
            self.screen.blit(shade, dest)
            for x in range(dest.left + 3, dest.right, 7):
                for y in range(dest.top + 3, dest.bottom, 7):
                    pygame.draw.circle(self.screen, (0, 0, 0, 36), (x, y), 1)
            pygame.draw.rect(self.screen, (246, 239, 205), dest, 6)

            narration = pygame.Rect(dest.x + 12, dest.y + 10, min(dest.width - 24, 430), 38)
            pygame.draw.rect(self.screen, (246, 214, 113), narration, border_radius=3)
            pygame.draw.rect(self.screen, INK, narration, 2, border_radius=3)
            self.draw_wrapped(page["captions"][index], self.fonts.tiny, INK, narration.inflate(-12, -8), 2)

            floor = dest.bottom - 10
            if index == 0:
                guard = self.draw_comic_actor(defender_actor, "idle", 2, (dest.x + 250, floor), 132)
                self.draw_comic_actor(enemy_actor, "move", 4, (dest.right - 230, floor), 137)
                bubble = pygame.Rect(dest.x + 405, dest.y + 57, 355, 70)
                tail = (guard.centerx + 20, guard.top + 22)
            elif index == 1:
                guard = self.draw_comic_actor(defender_actor, "idle", 1, (dest.x + 92, floor), 112)
                self.draw_comic_actor(enemy_actor, "move", 1, (dest.centerx + 70, floor + 3), 112)
                self.draw_comic_actor(enemy_actor, "bite", 4, (dest.right - 58, floor), 120)
                bubble = pygame.Rect(dest.x + 148, dest.y + 54, 365, 66)
                tail = (guard.centerx + 8, guard.top + 18)
            else:
                guard = self.draw_comic_actor(defender_actor, "shoot", 3, (dest.centerx - 65, floor), 120)
                self.draw_comic_actor(enemy_actor, "hit", 3, (dest.right - 72, floor), 112)
                bubble = pygame.Rect(dest.x + 24, dest.y + 52, 310, 66)
                tail = (guard.centerx + 16, guard.top + 26)
            self.draw_comic_bubble(bubble, page["dialogue"][index], tail)
            self.draw_text(
                page["sfx"][index],
                self.fonts.h2,
                (255, 234, 91),
                (dest.right - 22, dest.y + 18),
                "topright",
                True,
            )

        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
        self.button("ANTERIOR", pygame.Rect(245, 646, 170, 44), accent, self.story_page > 0)
        self.draw_text(f"PÁGINA {self.story_page + 1}/3", self.fonts.small, WHITE, (WIDTH / 2, 661), "center")
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 415, 646, 170, 44), accent, self.story_page < 2)

    def draw_settings(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 190))
        self.screen.blit(veil, (0, 0))
        card = pygame.Rect(285, 112, 710, 478)
        self.panel(card, 244, TEAL, 16)
        self.draw_text("CONFIGURAÇÕES", self.fonts.title, WHITE, (card.centerx, card.y + 54), "center", True)
        self.draw_text("CONTROLE", self.fonts.h2, GOLD, (card.x + 95, 218))
        control_label = "MOUSE (PADRÃO)" if self.control_mode == "mouse" else "TECLADO"
        self.button(control_label, self.settings_control_rect(), TEAL)
        self.draw_text("SOM", self.fonts.h2, GOLD, (card.x + 95, 299))
        sound_label = "LIGADO" if self.audio.enabled and self.audio.ready else ("INDISPONÍVEL" if not self.audio.ready else "DESLIGADO")
        self.button(sound_label, self.settings_sound_rect(), TEAL if self.audio.enabled and self.audio.ready else (92, 108, 116), self.audio.ready)
        self.draw_text("VOLUME", self.fonts.h2, GOLD, (card.x + 95, 380))
        self.button("−", self.settings_volume_minus_rect(), (92, 126, 137), self.audio.ready)
        self.button("+", self.settings_volume_plus_rect(), (92, 126, 137), self.audio.ready)
        volume_bar = pygame.Rect(581, 417, 118, 18)
        pygame.draw.rect(self.screen, (29, 42, 49), volume_bar, border_radius=8)
        pygame.draw.rect(self.screen, TEAL, (volume_bar.x, volume_bar.y, int(volume_bar.width * self.audio.volume), volume_bar.height), border_radius=8)
        self.draw_text(f"{int(round(self.audio.volume * 100))}%", self.fonts.tiny, WHITE, (volume_bar.centerx, volume_bar.y - 23), "center")
        self.draw_text("VÍDEO", self.fonts.h2, GOLD, (card.x + 95, 463))
        video_rect = pygame.Rect(505, 458, 270, 42)
        pygame.draw.rect(self.screen, (20, 72, 68), video_rect, border_radius=7)
        pygame.draw.rect(self.screen, (228, 235, 228), video_rect, width=1, border_radius=7)
        self.draw_text("SOFTWARE · CPU/RAM", self.fonts.small, WHITE, video_rect.center, "center", True)
        if self.control_mode == "keyboard":
            help_text = "WASD/setas: mover cursor • Q/E: trocar carta • Enter/F/Espaço: posicionar • R: remover • N/Tab: próxima onda • P: pausar"
        else:
            help_text = "Mouse: escolher carta, apontar para uma casa e clicar. Teclas 1–8 continuam selecionando cartas e P pausa a partida."
        self.draw_wrapped(help_text, self.fonts.tiny, WHITE, pygame.Rect(card.x + 70, 518, card.width - 140, 52), 3, center=True)
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_howto(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 10, 14, 186))
        self.screen.blit(veil, (0, 0))
        card = pygame.Rect(116, 72, WIDTH - 232, 560)
        self.panel(card, 238, GOLD, 16)
        self.draw_text("COMO JOGAR", self.fonts.title, WHITE, (card.centerx, card.y + 30), "center")
        lines = [
            ("1. Monte a equipe", "No carrossel, veja uma carta ampliada por vez e escolha até três tropas próprias daquele cenário."),
            ("2. Posicione na faixa", "A tropa fica centralizada no terreno escolhido e ataca somente o zumbi que avança naquela mesma linha."),
            ("3. Leia os counters", "Imunidades exigem a carta indicada na ficha. Rompa a defesa e aproveite a janela antes que ela se feche."),
            ("4. Proteção de emergência", "Tratores, drones e cargas ficam no centro do começo da faixa. O primeiro invasor que chega até eles ativa a contenção."),
            ("5. Ondas e dificuldade", "Sobreviva a 12 ondas em três atos: duas comuns, uma de sub-boss e uma de boss. Cada ato aumenta vida, dano e densidade."),
            ("6. Comandos", "Mouse é o padrão. Em Configurações, Teclado ativa WASD/setas, Q/E para cartas, Enter/F/Espaço para posicionar, R para remover, N/Tab para a onda e P para pausar."),
        ]
        y = card.y + 102
        for head, body in lines:
            self.draw_text(head, self.fonts.h2, GOLD, (card.x + 48, y))
            self.draw_wrapped(body, self.fonts.body, WHITE, pygame.Rect(card.x + 48, y + 27, card.width - 96, 46), 2)
            y += 76
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_unit_evolution_dossier(self) -> None:
        """Mostra a progressão literalmente em duas faixas: N1 sobre N2."""
        self.screen.blit(self.assets.images["menu"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 14, 190))
        self.screen.blit(overlay, (0, 0))
        accent = REGIONS[self.region]["accent"]
        self.draw_text("EVOLUÇÃO DOS SOLDADOS", self.fonts.title, WHITE, (WIDTH / 2, 20), "center", True)
        self.draw_text("TELA LEGADA DESATIVADA • use PERSONAGENS no menu principal", self.fonts.small, accent, (WIDTH / 2, 70), "center")
        items = self.dossier_items()
        start = self.dossier_page * 6
        for index, item in enumerate(items[start:start + 6]):
            row, col = divmod(index, 3)
            rect = pygame.Rect(52 + col * 404, 110 + row * 247, 372, 226)
            self.panel(rect, 238, accent, 12)
            if item["kind"] == "promoter":
                data = DEFENSES["instrutor"]
                sprite = self.card_sprite(self.region, "instrutor", int(data["sprite"]))
                self.blit_sprite(sprite, rect.x + 18, rect.y + 48, 106, 126)
                self.draw_text("CARTA DE PROMOÇÃO", self.fonts.tiny, GOLD, (rect.x + 140, rect.y + 25))
                self.draw_text(data["base"], self.fonts.h2, WHITE, (rect.x + 140, rect.y + 48))
                self.draw_text(f"Custo {data['cost']} SUP • HP {data['hp']}", self.fonts.tiny, GOLD, (rect.x + 140, rect.y + 78))
                self.draw_wrapped(data["ability"], self.fonts.small, (219, 229, 225), pygame.Rect(rect.x + 140, rect.y + 104, 210, 74), 4)
                continue
            for tier_index, key in enumerate((item["l1"], item["l2"])):
                data = DEFENSES[key]
                tier = pygame.Rect(rect.x + 10, rect.y + 27 + tier_index * 96, rect.width - 20, 88)
                tier_color = (102, 128, 135) if tier_index == 0 else GOLD
                self.panel(tier, 205, tier_color, 8)
                sprite = self.card_sprite(self.region, key, int(data["sprite"]))
                self.blit_sprite(sprite, tier.x + 5, tier.y + 8, 60, 72)
                self.draw_text(f"N{data['level']}", self.fonts.tiny, tier_color, (tier.x + 74, tier.y + 9), shadow=True)
                self.draw_text(str(data["base"]), self.fonts.small, WHITE, (tier.x + 103, tier.y + 7))
                self.draw_text(f"HP {int(data['hp'])} • DANO {int(data['damage'])} • ALC {int(data['range'])}", self.fonts.tiny, GOLD, (tier.x + 74, tier.y + 29))
                self.draw_wrapped(str(data["ability"]), self.fonts.tiny, (219, 229, 225), pygame.Rect(tier.x + 74, tier.y + 45, tier.width - 84, 34), 2)
        pages = max(1, math.ceil(len(items) / 6))
        self.draw_text(f"Página {self.dossier_page + 1}/{pages} • uniforme atual: {REGIONS[self.region]['short'].title()}", self.fonts.small, WHITE, (WIDTH / 2, 664), "center")
        self.button("VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137))
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

    def draw_dossier(self) -> None:
        is_units = self.dossier_kind == "units"
        if is_units:
            self.draw_unit_evolution_dossier()
            return
        self.screen.blit(self.assets.images["menu"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 14, 190))
        self.screen.blit(overlay, (0, 0))
        heading = "INFORMAÇÕES DOS SOLDADOS" if is_units else "INFORMAÇÕES DOS ZUMBIS"
        accent = TEAL if is_units else (139, 222, 106)
        self.draw_text(heading, self.fonts.title, WHITE, (WIDTH / 2, 24), "center", True)
        self.draw_text("As fichas abaixo mostram função, poder e contraponto tático.", self.fonts.body, accent, (WIDTH / 2, 70), "center")
        items = self.dossier_items()
        start = self.dossier_page * 6
        page_items = items[start:start + 6]
        for index, item in enumerate(page_items):
            row, col = divmod(index, 3)
            rect = pygame.Rect(52 + col * 404, 123 + row * 235, 372, 208)
            self.panel(rect, 236, accent, 12)
            icon_index = DEFENSES[item["key"]]["sprite"] if is_units else ({**ENEMIES, **BOSSES}[item["key"]]["sprite"])
            sprite_region = "city" if is_units else ("city" if item["key"] in {"caminhante", "corredor", "rastejante", "conehead", "policial", "militar", "escudo", "cuspidor", "divisor", "gritador", "saltador", "bruto", "bruto_demolidor", "comandante_mortos", "cuspidor_alfa"} else ("desert" if item["key"] in {"digger", "ladrao", "curandeiro", "parasita", "mutante", "necromante_minion", "mutante_ruinas", "necromante", "colosso_mutante"} else "beach"))
            # A ficha de zumbis deve usar exatamente o mesmo retrato que a
            # batalha. Antes esta tela ainda puxava o quadro antigo do atlas
            # urbano para o Saltador, que incluía uma pilastra de cenário.
            # O retrato exclusivo da Beta 3 não traz obstáculo algum.
            dossier_sheet = {
                ("city", "caminhante"): "city_walker_walk",
                ("desert", "digger"): "desert_digger_states",
                ("beach", "nadador"): "beach_swimmer_walk",
            }.get((sprite_region, item["key"])) if not is_units else None
            if not is_units and item["key"] in BOSSES:
                boss_frames = self.assets.animation_frames.get(f"{sprite_region}_boss_actions", [])
                boss_row = REGIONS[sprite_region]["bosses"].index(item["key"])
                sprite = boss_frames[boss_row * 4] if len(boss_frames) >= 12 else self.assets.zombie(sprite_region, int(icon_index))
            elif dossier_sheet and self.assets.animation_frames.get(dossier_sheet):
                sprite = self.assets.animation_frames[dossier_sheet][0]
            elif not is_units and item["key"] == "saltador" and "zombie_jumper_beta3" in self.assets.images:
                sprite = self.assets.images["zombie_jumper_beta3"]
            elif not is_units and item["key"] == "rastejante" and "zombie_crawler_beta3" in self.assets.images:
                sprite = self.assets.images["zombie_crawler_beta3"]
            else:
                sprite = self.card_sprite(sprite_region, item["key"], int(icon_index)) if is_units else self.assets.zombie(sprite_region, int(icon_index))
            self.blit_sprite(sprite, rect.x + 14, rect.y + 44, 105, 118)
            self.draw_text(item["name"], self.fonts.h2, WHITE, (rect.x + 132, rect.y + 22))
            self.draw_text(item["sub"], self.fonts.small, accent, (rect.x + 132, rect.y + 51))
            stat = f"Custo: {item['cost']} SUP • Nível {item['level']}" if is_units else f"Vida base: {item['hp']}"
            self.draw_text(stat, self.fonts.tiny, GOLD, (rect.x + 132, rect.y + 76))
            self.draw_wrapped(item["ability"], self.fonts.small, (219, 229, 225), pygame.Rect(rect.x + 132, rect.y + 100, 220, 83), 4)
        pages = max(1, math.ceil(len(items) / 6))
        self.draw_text(f"Página {self.dossier_page + 1}/{pages}", self.fonts.small, WHITE, (WIDTH / 2, 664), "center")
        self.button("VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137))
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

    def draw_battle(self) -> None:
        assert self.battle is not None
        battle = self.battle
        background = self.assets.images[f"{battle.region}_bg"]
        shake_x = int(math.sin(self.scene_elapsed * 55) * 4 * battle.shake)
        shake_y = int(math.cos(self.scene_elapsed * 37) * 3 * battle.shake)
        self.screen.blit(background, (shake_x, shake_y))
        # Generais, piras, efeitos de horda e clima de chefe são exatamente
        # as animações aprovadas no visualizador de cenários.
        self.scenario_runtime.draw(self.screen, battle)
        # As quatro pistas já estão pintadas no próprio cenário. Nenhuma faixa
        # sintética é sobreposta à arte: pés, água, asfalto e areia coincidem.
        ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if battle.global_toxic > 0:
            ambient.fill((92, 202, 86, int(30 + battle.global_toxic * 8)))
        self.screen.blit(ambient, (0, 0))
        self.draw_lane_bombs(battle)
        mouse = pygame.mouse.get_pos()
        hovered_cell = (
            (battle.keyboard_row, battle.keyboard_col)
            if self.control_mode == "keyboard"
            else battle.board_cell_at(mouse)
        )
        if hovered_cell and not battle.finished:
            row, col = hovered_cell
            outline = battle.ground_cell_rect(row, col)
            color = RED if battle.remove_mode else battle.region_color()
            pygame.draw.rect(self.screen, color, outline, 2, border_radius=12)
            if self.control_mode == "keyboard":
                pygame.draw.rect(self.screen, WHITE, outline.inflate(-6, -6), 1, border_radius=10)
            if battle.cell_is_water(row, col):
                pygame.draw.arc(self.screen, (110, 213, 250), outline.inflate(-22, -28), 0, math.pi, 2)
        for defender in battle.defenders:
            self.draw_defender(defender)
        for enemy in battle.enemies:
            self.draw_enemy(enemy)
        self.draw_fallen(battle)
        if self.overlay_surface is not None:
            self.screen = self.overlay_surface
        self.draw_projectiles(battle)
        self.draw_visual_effects(battle)
        self.draw_particles(battle)
        self.draw_battle_top()
        self.draw_battle_status()
        if battle.finished:
            self.draw_result_overlay()

    def draw_lane_guides(self, battle: Battle) -> None:
        """Compatibilidade: os limites agora pertencem à própria pintura."""
        return

    def draw_lane_bombs(self, battle: Battle) -> None:
        """Mostra a contenção visual própria de cada terreno antes da invasão."""
        for cart in battle.lane_bombs:
            if cart.state == "spent":
                continue
            y = lane_bomb_ground_y(battle.region, cart.row)
            x = cart.x if cart.state == "rolling" else lane_bomb_home_x(battle.region, cart.row)
            is_water_buoy = battle.region == "beach" and cart.row in battle.water_rows
            depth = lane_depth(battle.region, cart.row)
            # As bombas de Minas ficam plantadas no contato e somem no mesmo
            # instante em que disparam a cadeia de explosões. Trator e drone
            # percorrem a faixa e desaparecem antes da entrada inimiga.
            if battle.region == "beach" and cart.state == "rolling":
                continue
            sprite, base_size = self.scenario_runtime.lane_defense_frame(
                battle.region,
                cart.row,
                moving=cart.state == "rolling",
                water=is_water_buoy,
            )
            width, height = base_size[0] * depth, base_size[1] * depth
            self.draw_actor_sprite(sprite, x, y, width, height, cart.motion, enemy=False)

    def draw_battle_top(self) -> None:
        assert self.battle is not None
        battle = self.battle
        rects = battle.card_rects()
        for index, ((key, display), rect) in enumerate(zip(battle.selected, rects)):
            data = DEFENSES[key]
            active = index == battle.selected_card
            self.panel(rect, 238, GOLD if active else battle.region_color(), 7)
            if battle.card_cooldowns[index] > 0:
                dark = pygame.Surface(rect.size, pygame.SRCALPHA)
                dark.fill((0, 0, 0, 125))
                self.screen.blit(dark, rect)
                self.draw_text(f"{math.ceil(battle.card_cooldowns[index])}s", self.fonts.small, WHITE, rect.center, "center", True)
            self.blit_sprite(self.card_sprite(battle.region, key, int(data["sprite"])), rect.x + 5, rect.y + 25, 44, 56)
            self.draw_text(str(index + 1), self.fonts.tiny, GOLD, (rect.x + 7, rect.y + 6))
            metric_a, metric_b = self.card_metrics(data)
            self.draw_text(f"{data['cost']} SUP", self.fonts.tiny, GOLD, (rect.x + 51, rect.y + 15))
            self.draw_text(metric_a, self.fonts.tiny, WHITE, (rect.x + 51, rect.y + 35))
            self.draw_text(metric_b, self.fonts.tiny, TEAL if data["ammo"] or data["role"] in {"radio", "promoter"} else GRAY, (rect.x + 51, rect.y + 54))
            if data.get("water_only"):
                self.draw_text("ÁGUA", self.fonts.tiny, TEAL, (rect.centerx, rect.bottom - 15), "center")
        self.panel(pygame.Rect(WIDTH - 176, 8, 166, 104), 230, battle.region_color(), 8)
        self.draw_text(f"{battle.supplies}/{int(battle.difficulty_data['supply_cap'])} SUP", self.fonts.h2, GOLD, (WIDTH - 93, 18), "center")
        self.draw_text(f"ONDA {battle.wave}/{TOTAL_WAVES}", self.fonts.small, WHITE, (WIDTH - 93, 48), "center")
        self.draw_text(f"{len(battle.enemies) + len(battle.orders)} INVASORES", self.fonts.tiny, GRAY, (WIDTH - 93, 78), "center")

        # Comandos de missão em uma única aba, sempre acima do terreno.
        shelf = pygame.Rect(10, 118, WIDTH - 20, 50)
        self.panel(shelf, 221, battle.region_color(), 8)
        self.button("MENU", battle.menu_rect(), battle.region_color())
        self.button("PAUSA", battle.pause_rect(), GOLD)
        if battle.difficulty != "easy":
            self.button("REMOVER", battle.remove_rect(), RED if battle.remove_mode else (88, 125, 132))
        self.button("PRÓXIMA", battle.next_wave_rect(), battle.region_color(), not battle.started_wave)
        if battle.started_wave:
            tactical_status = f"HORDA ATIVA • {len(battle.enemies) + len(battle.orders)} invasores"
        else:
            tactical_status = f"INTERVALO TÁTICO • {max(0, math.ceil(battle.intermission))} s"
        ticker = battle.message if battle.message_timer > 0 else "Equipe em posição."
        if len(ticker) > 62:
            ticker = ticker[:59] + "..."
        self.draw_text(tactical_status, self.fonts.tiny, WHITE, (520, 127))
        self.draw_text(ticker, self.fonts.tiny, GOLD if battle.message_timer > 0 else GRAY, (520, 147))
        control_hint = "WASD • Q/E • ENTER • N • P" if self.control_mode == "keyboard" else "MOUSE • 1–8 • P"
        self.draw_text(control_hint, self.fonts.tiny, GRAY, (WIDTH - 26, 136), "topright")

        # Ficha completa apenas por hover: remove a redundância sem esconder a
        # informação tática para quem quer comparar as cartas.
        mouse = pygame.mouse.get_pos()
        hovered = next(((key, display, rect) for (key, display), rect in zip(battle.selected, rects) if rect.collidepoint(mouse)), None)
        if hovered:
            key, display, rect = hovered
            data = DEFENSES[key]
            tooltip_x = int(clamp(rect.centerx - 170, 154, WIDTH - 350))
            tooltip = pygame.Rect(tooltip_x, 178, 340, 72)
            self.panel(tooltip, 239, battle.region_color(), 8)
            self.draw_text(display, self.fonts.small, GOLD, (tooltip.x + 13, tooltip.y + 9))
            self.draw_wrapped(data["ability"], self.fonts.tiny, WHITE, pygame.Rect(tooltip.x + 13, tooltip.y + 29, tooltip.width - 26, 35), 2)

    def defender_sprite(self, battle: Battle, defender: Defender) -> pygame.Surface:
        """Fonte visual da defesa ativa e da animação de derrota."""
        if defender.visual_animation is not None:
            return defender.visual_animation.frame
        return self.card_sprite(battle.region, defender.key, defender.sprite_index)

    def enemy_sprite(self, battle: Battle, enemy: Enemy) -> pygame.Surface:
        """Fonte visual do inimigo, centralizando os retratos especiais."""
        if enemy.visual_animation is not None:
            return enemy.visual_animation.frame
        if enemy.is_boss:
            frames = self.assets.animation_frames.get(f"{battle.region}_boss_actions", [])
            if len(frames) >= 12:
                boss_row = REGIONS[battle.region]["bosses"].index(enemy.key)
                row_frames = frames[boss_row * 4:boss_row * 4 + 4]
                if enemy.motion.state == "skill":
                    return row_frames[3]
                if enemy.motion.state == "attack":
                    return row_frames[2]
                if enemy.motion.state in {"hit", "stunned"}:
                    return row_frames[1]
                return row_frames[enemy.motion.phase(fps=4.6, frames=2)]
        sheet_key = {
            ("city", "caminhante"): "city_walker_walk",
            ("desert", "digger"): "desert_digger_states",
            ("beach", "nadador"): "beach_swimmer_walk",
        }.get((battle.region, enemy.key))
        if sheet_key:
            frames = self.assets.animation_frames.get(sheet_key, [])
            if frames:
                if enemy.key == "digger" and enemy.motion.state == "walk":
                    frame_index = enemy.motion.phase(fps=5.5, frames=2)
                elif enemy.key == "digger" and enemy.motion.state == "dig_enter":
                    frame_index = min(4, 2 + int(enemy.motion.state_elapsed / 0.16))
                elif enemy.key == "digger" and enemy.motion.state == "dig_tunnel":
                    frame_index = 4
                elif enemy.key == "digger" and enemy.motion.state == "dig_emerge":
                    frame_index = 5
                elif enemy.key == "digger" and enemy.motion.state == "attack":
                    frame_index = 6
                elif enemy.motion.state == "walk":
                    frame_index = enemy.motion.phase(fps=10.0, frames=len(frames))
                elif enemy.motion.state == "attack":
                    frame_index = 2
                elif enemy.motion.state in {"hit", "stunned"}:
                    frame_index = 4
                else:
                    frame_index = 0
                return frames[frame_index % len(frames)]
        if enemy.key == "saltador" and "zombie_jumper_beta3" in self.assets.images:
            return self.assets.images["zombie_jumper_beta3"]
        if enemy.key == "rastejante" and battle.region == "city" and "zombie_crawler_beta3" in self.assets.images:
            return self.assets.images["zombie_crawler_beta3"]
        return self.assets.zombie(battle.region, int(enemy.data["sprite"]))

    def draw_actor_sprite(
        self,
        sprite: pygame.Surface,
        x: float,
        ground_y: float,
        width: float,
        height: float,
        motion: ActorMotion,
        *,
        enemy: bool,
        vertical_offset: float = 0.0,
        alpha: int = 255,
        progress: float = 0.0,
        state_override: str | None = None,
        profile: str = "generic",
        frame_animated: bool = False,
    ) -> pygame.Rect:
        """Desenha uma pose articulada preservando os pés no terreno real."""
        if sprite.get_width() <= 1:
            return pygame.Rect(int(x), int(ground_y), 1, 1)
        # Animações de produção já compartilham uma caixa e um pivô fixos. O
        # trim por quadro recentralizava cada pose e fazia corpo, mangueira e
        # efeitos saltarem alguns pixels. Artes estáticas antigas ainda usam o
        # recorte tradicional.
        if not frame_animated:
            sprite = self.assets.trimmed(sprite)
        action_progress = clamp(float(progress), 0.0, 1.0)
        if action_progress <= 0.0 and motion.event_left > 0:
            action_progress = clamp(
                motion.state_elapsed / max(0.001, motion.state_elapsed + motion.event_left),
                0.0,
                1.0,
            )
        if self.presenter is not None:
            self.actor_commands.append(
                ActorCommand(
                    sprite=sprite,
                    x=float(x),
                    ground_y=float(ground_y),
                    width=max(1.0, float(width)),
                    height=max(1.0, float(height)),
                    state="sprite_sequence" if frame_animated else (state_override or motion.state),
                    elapsed=motion.state_elapsed,
                    enemy=enemy,
                    vertical_offset=vertical_offset,
                    alpha=max(0, min(255, int(alpha))),
                    hit_flash=0.0 if frame_animated else motion.hit_flash,
                    progress=action_progress,
                    profile="sprite_sequence" if frame_animated else profile,
                )
            )
            return pygame.Rect(
                int(x - width / 2),
                int(ground_y + vertical_offset - height),
                max(1, int(width)),
                max(1, int(height)),
            )
        if frame_animated:
            dx, dy, angle, scale_x, scale_y = 0.0, 0.0, 0.0, 1.0, 1.0
        else:
            dx, dy, angle, scale_x, scale_y = actor_pose(
                motion,
                enemy=enemy,
                profile=profile,
                progress=action_progress,
            )
        size = (max(1, int(width * scale_x)), max(1, int(height * scale_y)))
        rendered = pygame.transform.rotate(self.assets.scaled(sprite, *size), angle)
        if alpha < 255:
            rendered.set_alpha(max(0, alpha))
        if motion.hit_flash > 0 and not frame_animated:
            flash_alpha = int(105 * clamp(motion.hit_flash / 0.13, 0.0, 1.0))
            flash = pygame.Surface(rendered.get_size(), pygame.SRCALPHA)
            flash.fill((255, 238, 210, flash_alpha))
            rendered.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        rect = rendered.get_rect(midbottom=(int(x + dx), int(ground_y + dy + vertical_offset)))
        self.screen.blit(rendered, rect)
        return rect

    def draw_fallen(self, battle: Battle) -> None:
        """Mostra uma queda curta antes de a silhueta sumir em partículas."""
        for fallen in battle.fallen:
            progress = clamp(fallen.elapsed / max(0.01, fallen.duration), 0.0, 1.0)
            alpha = int(255 * (1.0 - progress))
            motion = ActorMotion(state="dead", state_elapsed=fallen.elapsed, event_left=fallen.duration)
            self.draw_actor_sprite(
                fallen.sprite,
                fallen.x,
                fallen.y,
                fallen.width,
                fallen.height,
                motion,
                enemy=fallen.enemy,
                alpha=alpha,
                progress=progress,
            )

    def draw_linked_skill_effect(
        self,
        effect: VisualEffect,
        x: float,
        y: float,
        progress: float,
    ) -> bool:
        """Desenha sinais próprios que permanecem presos ao personagem.

        Estes gestos não reaproveitam fogo, água ou uma explosão genérica. A
        geometria é pequena e funcional: pulso, rede, cura, roubo ou parasita
        comunicam exatamente a regra executada pelo inimigo.
        """
        supported = {
            "command_aura",
            "signal_pulse",
            "heal_pulse",
            "heal_receive",
            "supply_snatch",
            "net_cast",
            "parasite_burst",
        }
        if effect.kind not in supported:
            return False
        size = max(84, round(180 * effect.scale))
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        center = pygame.Vector2(size / 2, size / 2)
        fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
        alpha = max(0, min(255, round(225 * fade)))
        color = (*effect.color, alpha)
        pale = tuple(min(255, channel + 70) for channel in effect.color) + (alpha,)
        radius = max(12, round((20 + progress * 46) * effect.scale))

        if effect.kind in {"command_aura", "signal_pulse", "heal_pulse"}:
            pygame.draw.circle(layer, color, center, radius, max(2, round(4 * effect.scale)))
            pygame.draw.circle(layer, pale, center, max(5, round(radius * 0.62)), max(1, round(2 * effect.scale)))
        if effect.kind == "command_aura":
            for angle in (-0.72, 0.0, 0.72):
                end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
                pygame.draw.line(layer, pale, center, end, max(2, round(3 * effect.scale)))
        elif effect.kind == "signal_pulse":
            pygame.draw.line(layer, pale, center + (-5, 9), center + (0, -radius * 0.72), max(2, round(3 * effect.scale)))
            for side in (-1, 1):
                arc = pygame.Rect(0, 0, radius * 1.18, radius * 1.18)
                arc.center = center + (side * radius * 0.26, -radius * 0.34)
                pygame.draw.arc(layer, pale, arc, -1.0, 1.0, max(2, round(2 * effect.scale)))
        elif effect.kind == "heal_pulse":
            arm = max(6, round(radius * 0.36))
            thickness = max(3, round(radius * 0.18))
            pygame.draw.rect(layer, pale, (center.x - thickness / 2, center.y - arm, thickness, arm * 2))
            pygame.draw.rect(layer, pale, (center.x - arm, center.y - thickness / 2, arm * 2, thickness))
            # Partículas orbitam o gesto de cura; a cruz deixa de ser a única
            # mudança entre os quadros.
            for index in range(6):
                angle = progress * math.tau * 1.5 + index * math.tau / 6
                orbit = radius * (0.58 + 0.10 * (index % 2))
                point = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit
                pygame.draw.circle(layer, pale, point, max(2, round(2.8 * effect.scale)))
        elif effect.kind == "heal_receive":
            # O aliado curado responde à habilidade: energia sobe do chão ao
            # tronco em tempos diferentes, sempre na mesma pista do emissor.
            for index in range(7):
                phase = (progress + index / 7.0) % 1.0
                px = center.x + math.sin(index * 2.1 + progress * 5.0) * radius * 0.46
                py = center.y + radius * 0.55 - phase * radius * 1.25
                pygame.draw.circle(layer, pale, (round(px), round(py)), max(2, round(3.0 * effect.scale)))
            cross_y = center.y - radius * 0.15
            arm = max(4, round(radius * 0.22))
            thickness = max(2, round(radius * 0.10))
            pygame.draw.rect(layer, color, (center.x - thickness / 2, cross_y - arm, thickness, arm * 2))
            pygame.draw.rect(layer, color, (center.x - arm, cross_y - thickness / 2, arm * 2, thickness))
        elif effect.kind == "supply_snatch":
            for index in range(6):
                angle = index * math.tau / 6 + progress * 0.5
                start = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
                end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * 0.30
                pygame.draw.line(layer, color, start, end, max(2, round(3 * effect.scale)))
                pygame.draw.circle(layer, pale, end, max(2, round(4 * effect.scale)))
        elif effect.kind == "net_cast":
            net_radius = max(16, round(radius * 0.90))
            rect = pygame.Rect(0, 0, net_radius * 2, net_radius * 1.45)
            rect.center = center
            for step in range(-net_radius, net_radius + 1, max(7, net_radius // 4)):
                pygame.draw.line(layer, color, (rect.left, center.y + step * 0.55), (rect.right, center.y - step * 0.55), 2)
                pygame.draw.line(layer, color, (rect.left, center.y - step * 0.55), (rect.right, center.y + step * 0.55), 2)
            pygame.draw.ellipse(layer, pale, rect, 2)
        elif effect.kind == "parasite_burst":
            ground = center + (0, radius * 0.45)
            for index in range(7):
                angle = -2.85 + index * 0.42
                length = radius * (0.60 + (index % 2) * 0.24)
                tip = ground + pygame.Vector2(math.cos(angle), math.sin(angle)) * length
                pygame.draw.line(layer, color, ground, tip, max(2, round(4 * effect.scale)))
                pygame.draw.circle(layer, pale, tip, max(2, round(3 * effect.scale)))

        self.screen.blit(layer, layer.get_rect(center=(round(x), round(y))))
        return True

    def draw_gas_cloud(
        self,
        x: float,
        y: float,
        progress: float,
        scale: float,
    ) -> None:
        """Nuvem baixa de gás anticorrosivo, com expansão e dissipação."""
        # A altura cabe dentro de uma única pista. Assim o recorte de faixa
        # protege as linhas vizinhas sem amputar a parte principal da nuvem.
        width = max(108, round(174 * scale))
        height = max(58, round(70 * scale))
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        center_x = width / 2
        ground_y = height * 0.78
        growth = 0.34 + 0.66 * (1.0 - (1.0 - progress) ** 2)
        fade = 1.0 - clamp((progress - 0.66) / 0.34, 0.0, 1.0)

        ring = pygame.Rect(0, 0, width * 0.72 * growth, height * 0.24 * growth)
        ring.center = (center_x, ground_y)
        pygame.draw.ellipse(
            layer, (146, 231, 77, round(185 * fade)), ring,
            max(1, round(2 * scale)),
        )

        for index in range(11):
            phase = index * 1.73
            horizontal = math.sin(phase) * width * (0.12 + 0.018 * index) * growth
            rise = (5 + (index % 4) * 5 + progress * (10 + index * 0.72)) * scale
            drift = math.sin(progress * 4.2 + phase) * 7 * scale
            blob_x = center_x + horizontal + drift
            blob_y = ground_y - rise
            radius_x = (12 + (index % 4) * 4) * scale * growth
            radius_y = (8 + ((index + 2) % 4) * 2.7) * scale * growth
            outer = pygame.Rect(0, 0, radius_x * 2.0, radius_y * 2.0)
            outer.center = (blob_x, blob_y)
            inner = outer.inflate(-radius_x * 0.62, -radius_y * 0.62)
            pygame.draw.ellipse(
                layer, (50, 112, 35, round((135 + index * 4) * fade)), outer,
            )
            pygame.draw.ellipse(
                layer, (146, 222, 70, round((145 + index * 5) * fade)), inner,
            )

        for index in range(7):
            q = (progress * 0.82 + index / 7.0) % 1.0
            speck_x = center_x + math.sin(index * 2.4) * width * 0.25 * growth
            speck_y = ground_y - (10 + q * 34) * scale
            pygame.draw.circle(
                layer,
                (190, 242, 112, round(170 * fade * (1.0 - q * 0.45))),
                (round(speck_x), round(speck_y)),
                max(1, round(2.1 * scale)),
            )
        self.screen.blit(
            layer, layer.get_rect(midbottom=(round(x), round(y + 18 * scale))),
        )

    def draw_visual_effects(self, battle: Battle) -> None:
        """Exibe somente quadros rasterizados de matéria e impacto reais."""
        styles = {
            "flame_impact": ("elemental_effects", 0, 118, 92),
            "water_impact": ("elemental_effects", 1, 132, 88),
            "toxic_impact": ("elemental_effects", 2, 126, 96),
            "toxic_wave": ("elemental_effects", 2, 212, 136),
            "ground_slam": ("ability_effects", 0, 236, 126),
            "arcane_cast": ("ability_effects", 1, 164, 174),
            "tidal_surge": ("ability_effects", 2, 260, 142),
            "water_splash": ("ability_effects", 2, 138, 82),
            "electric_arc": ("combat_effects", 0, 78, 54),
            "explosion": ("combat_effects", 2, 184, 146),
            "ballistic_impact": ("combat_effects", 0, 92, 66),
        }
        for effect in battle.effects:
            progress = clamp(effect.elapsed / max(0.01, effect.duration), 0.0, 1.0)
            effect_x, effect_y = effect.x, effect.y
            if isinstance(effect.owner, Enemy):
                effect_x, effect_y = battle.enemy_effect_origin(
                    effect.owner,
                    effect.anchor_kind or effect.kind,
                )
            previous_clip = self.screen.get_clip()
            boss_can_cross = isinstance(effect.owner, Enemy) and effect.owner.is_boss
            if not boss_can_cross:
                if isinstance(effect.owner, (Enemy, Defender)):
                    effect_row = effect.owner.row
                else:
                    effect_row = min(
                        range(ROWS),
                        key=lambda row: abs(terrain_y(battle.region, row, effect_x) - effect_y),
                    )
                top, bottom = lane_bounds(battle.region, effect_row)
                self.screen.set_clip(pygame.Rect(0, int(top), WIDTH, max(1, math.ceil(bottom - top))))
            if self.draw_linked_skill_effect(effect, effect_x, effect_y, progress):
                self.screen.set_clip(previous_clip)
                continue
            if effect.kind == "toxic_wave":
                self.draw_gas_cloud(effect_x, effect_y, progress, effect.scale)
                self.screen.set_clip(previous_clip)
                continue
            stage = min(3, int(progress * 4.0))
            sheet, row, base_width, base_height = styles.get(
                effect.kind,
                ("combat_effects", 2, 184, 146),
            )
            growth = 0.80 + progress * 0.36
            fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
            self.blit_effect_frame(
                sheet,
                row,
                stage,
                effect_x,
                effect_y,
                base_width * effect.scale * growth,
                base_height * effect.scale * growth,
                alpha=int(255 * fade),
            )
            self.screen.set_clip(previous_clip)

    def blit_effect_frame(
        self,
        sheet: str,
        row: int,
        stage: int,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        alpha: int = 255,
        angle: float = 0.0,
        midbottom: bool = False,
        flip_x: bool = False,
    ) -> pygame.Rect | None:
        """Desenha um quadro pré-pintado; jamais fabrica um símbolo geométrico."""
        frames = self.assets.effect_frames.get(sheet, [])
        index = row * 4 + max(0, min(3, int(stage)))
        if index >= len(frames) or frames[index].get_width() <= 1:
            return None
        rendered = self.assets.scaled(frames[index], width, height)
        if flip_x:
            rendered = pygame.transform.flip(rendered, True, False)
        if angle:
            rendered = pygame.transform.rotate(rendered, angle)
        elif alpha < 255:
            rendered = rendered.copy()
        if alpha < 255:
            rendered.set_alpha(max(0, min(255, int(alpha))))
        if midbottom:
            rect = rendered.get_rect(midbottom=(int(x), int(y)))
        else:
            rect = rendered.get_rect(center=(int(x), int(y)))
        self.screen.blit(rendered, rect)
        return rect

    def blit_muzzle_cycle(
        self,
        stage: int,
        x: float,
        y: float,
        *,
        width: float,
        height: float,
    ) -> pygame.Rect | None:
        """Desenha somente a ignição e o clarão na boca da arma.

        A folha também possui fumaça e estojos em posições próprias, mas ao
        escalar a célula inteira esses elementos pareciam um segundo projétil
        embaixo do soldado. O recuo da sprite continua visível e a sequência
        usa apenas os três clarões centrados no cano.
        """
        frames = self.assets.animation_frames.get("muzzle_cycle", [])
        if not frames:
            return None
        flash_cycle = (0, 1, 2, 3, 2, 1, 0, 0)
        frame_index = flash_cycle[max(0, min(len(flash_cycle) - 1, int(stage)))]
        frame = frames[min(len(frames) - 1, frame_index)]
        if frame.get_width() <= 1 or frame.get_height() <= 1:
            return None
        rendered = self.assets.scaled(frame, width, height)
        rect = rendered.get_rect(midleft=(int(x), int(y)))
        self.screen.blit(rendered, rect)
        return rect

    @staticmethod
    def frame_has_muzzle_flash(
        sprite: pygame.Surface,
        defender: Defender,
    ) -> bool:
        """Evita duplicar um clarão que já foi pintado junto da arma."""
        layout = defender_visual_layout(defender)
        depth = lane_depth(defender.region, defender.row)
        muzzle_x, muzzle_y = defender_weapon_origin(defender)
        ratio = layout.source_height / max(1.0, layout.body_height)
        source_x = round(
            sprite.get_width() / 2
            + ((muzzle_x - defender.render_x) / max(0.01, depth)) * ratio
        )
        source_y = round(
            sprite.get_height()
            - ((defender.y - muzzle_y) / max(0.01, depth)) * ratio
        )
        area = pygame.Rect(source_x - 18, source_y - 12, 21, 25).clip(sprite.get_rect())
        if area.width <= 0 or area.height <= 0:
            return False
        for x in range(area.left, area.right):
            for y in range(area.top, area.bottom):
                red, green, blue, alpha = sprite.get_at((x, y))
                if alpha > 24 and red >= 190 and green >= 82 and blue <= 125 and red >= blue + 70:
                    return True
        return False

    @staticmethod
    def eased(value: float) -> float:
        """Curva suave usada por mãos, carregadores e munição visível."""
        value = clamp(value, 0.0, 1.0)
        return value * value * (3.0 - 2.0 * value)

    def draw_reload_action(
        self,
        defender: Defender,
        rect: pygame.Rect,
        scale: tuple[float, float],
        depth: float,
        progress: float,
    ) -> None:
        """Mostra a troca física de munição sem palavra, relógio ou ícone.

        A mão sai da arma, alcança o cinto, carrega um pente/cartucho/cilindro
        e o encaixa no equipamento. A barra de munição existente é o único
        indicador abstrato; todo o restante é movimento corporal.
        """
        # A Beta 4 executa esse gesto na malha corporal OpenGL. O antigo braço
        # de linhas e o carregador geométrico não devem voltar a ser exibidos.
        return
        role = str(defender.stats.get("role", ""))
        if role in {"radio", "promoter", "barrier", "mine"}:
            return
        p = clamp(progress, 0.0, 1.0)
        x, y = defender.x, defender.y
        shoulder = (x + 2 * depth, y - scale[1] * 0.61)
        receiver = (x + 22 * depth, y - scale[1] * 0.50)
        pocket = (x - 7 * depth, y - scale[1] * 0.29)

        if p < 0.22:
            q = self.eased(p / 0.22)
            hand = (lerp(receiver[0], pocket[0], q), lerp(receiver[1], pocket[1], q))
        elif p < 0.44:
            q = self.eased((p - 0.22) / 0.22)
            hand = (pocket[0] - 2 * depth, pocket[1] + math.sin(q * math.pi) * 3 * depth)
        elif p < 0.78:
            q = self.eased((p - 0.44) / 0.34)
            hand = (lerp(pocket[0], receiver[0], q), lerp(pocket[1], receiver[1], q))
        else:
            q = self.eased((p - 0.78) / 0.22)
            rest = (x + 10 * depth, y - scale[1] * 0.52)
            hand = (lerp(receiver[0], rest[0], q), lerp(receiver[1], rest[1], q))

        elbow = (
            lerp(shoulder[0], hand[0], 0.52) - 4 * depth,
            lerp(shoulder[1], hand[1], 0.52) + 7 * depth,
        )
        sleeve = {
            "city": (46, 69, 67),
            "desert": (135, 105, 65),
            "beach": (32, 72, 92),
        }[defender.region]
        pygame.draw.line(self.screen, sleeve, shoulder, elbow, max(2, int(6 * depth)))
        pygame.draw.line(self.screen, sleeve, elbow, hand, max(2, int(5 * depth)))
        pygame.draw.circle(self.screen, (198, 152, 111), (int(hand[0]), int(hand[1])), max(2, int(4 * depth)))

        # O objeto aparece apenas depois de ser retirado do cinto e desaparece
        # dentro da arma na fase de encaixe.
        if 0.30 <= p <= 0.84:
            alpha = int(255 * min(1.0, (p - 0.30) / 0.08, (0.84 - p) / 0.08))
            item = pygame.Surface((max(8, int(15 * depth)), max(10, int(24 * depth))), pygame.SRCALPHA)
            if role == "shotgun":
                for offset in (3, 8):
                    pygame.draw.rect(item, (172, 42, 38, alpha), (offset, 2, 4, item.get_height() - 4), border_radius=2)
                    pygame.draw.line(item, (238, 187, 72, alpha), (offset, 2), (offset + 3, 2), 2)
            elif role in {"mortar", "grenade", "gas_grenade"}:
                pygame.draw.ellipse(item, (91, 104, 69, alpha), (2, 1, item.get_width() - 4, item.get_height() - 2))
                pygame.draw.line(item, (231, 184, 78, alpha), (2, item.get_height() // 2), (item.get_width() - 2, item.get_height() // 2), 2)
            elif role in {"flame", "poison", "waterjet"}:
                canister = {
                    "flame": (207, 93, 43, alpha),
                    "poison": (91, 175, 74, alpha),
                    "waterjet": (67, 177, 220, alpha),
                }[role]
                pygame.draw.rect(item, canister, (2, 2, item.get_width() - 4, item.get_height() - 4), border_radius=4)
                pygame.draw.line(item, (225, 236, 228, alpha), (3, 6), (item.get_width() - 3, 6), 2)
            else:
                pygame.draw.rect(item, (48, 55, 55, alpha), (2, 1, item.get_width() - 4, item.get_height() - 2), border_radius=2)
                pygame.draw.line(item, (151, 165, 160, alpha), (4, 5), (item.get_width() - 4, 5), 2)
            rotated = pygame.transform.rotate(item, -18 + p * 26)
            self.screen.blit(rotated, rotated.get_rect(center=(int(hand[0] + 3 * depth), int(hand[1] + 5 * depth))))

    def draw_weapon_action(
        self,
        defender: Defender,
        rect: pygame.Rect,
        scale: tuple[float, float],
        depth: float,
    ) -> None:
        """Detalhe mecânico do disparo que não existe no retrato estático."""
        # O lançamento está no estado de ataque e o obus real aparece na folha
        # de projéteis. Não desenhar braços ou munição com primitivas.
        return
        if defender.stats.get("role") != "mortar":
            return
        total = max(0.001, defender.motion.state_elapsed + defender.motion.event_left)
        p = clamp(defender.motion.state_elapsed / total, 0.0, 1.0)
        q = self.eased(clamp(p / 0.72, 0.0, 1.0))
        start = (defender.x - 10 * depth, defender.y - scale[1] * 0.45)
        tube = (defender.x + 18 * depth, defender.y - scale[1] * 0.30)
        shell_x = lerp(start[0], tube[0], q)
        shell_y = lerp(start[1], tube[1], q) - math.sin(q * math.pi) * 13 * depth
        shoulder = (defender.x, defender.y - scale[1] * 0.60)
        hand = (shell_x - 2 * depth, shell_y)
        pygame.draw.line(self.screen, (87, 89, 69), shoulder, hand, max(2, int(5 * depth)))
        shell = pygame.Surface((max(7, int(11 * depth)), max(12, int(23 * depth))), pygame.SRCALPHA)
        pygame.draw.ellipse(shell, (101, 116, 73, 255), shell.get_rect())
        pygame.draw.line(shell, GOLD, (2, shell.get_height() // 2), (shell.get_width() - 2, shell.get_height() // 2), 2)
        self.screen.blit(shell, shell.get_rect(center=(int(shell_x), int(shell_y))))

    def draw_defender(self, defender: Defender) -> None:
        assert self.battle is not None
        battle = self.battle
        x, y = defender.render_x, defender.y
        role = defender.stats["role"]
        depth = lane_depth(battle.region, defender.row)
        sprite = self.defender_sprite(battle, defender)
        frame_animated = defender.visual_animation is not None
        if frame_animated:
            layout = defender_visual_layout(defender)
            scale = animated_actor_render_scale(
                sprite,
                depth,
                body_height=layout.body_height,
                source_body_height=layout.source_height,
            )
        else:
            scale = defender_render_scale(defender)
        shadow_width = max(28, int(scale[0] * (0.82 if role in {"barrier", "boat", "sub"} else 0.68)))
        shadow_height = max(6, int(13 * depth))
        shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        if battle.cell_is_water(defender.row, defender.col):
            pygame.draw.ellipse(shadow, (90, 220, 235, 105), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (7, 36, 52, 85), shadow.get_rect().inflate(-10, -4))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        self.screen.blit(shadow, shadow.get_rect(midbottom=(int(x), int(y + 3))))
        # A mesma fonte de arte atende carta, campo e queda. A pose em si
        # muda conforme o estado emitido pela lógica de combate.
        reload_progress = (
            1.0 - defender.reload_timer / max(0.01, defender.reload_total)
            if defender.reloading
            else 0.0
        )
        rect = self.draw_actor_sprite(
            sprite,
            x,
            y,
            *scale,
            defender.motion,
            enemy=False,
            progress=reload_progress,
            profile=defender_animation_profile(defender),
            frame_animated=frame_animated,
        )
        world_target = self.screen
        if self.overlay_surface is not None:
            self.screen = self.overlay_surface
        if defender.motion.state == "attack":
            if frame_animated and defender.visual_animation is not None:
                attack_progress = defender.visual_animation.normalized_progress
            else:
                total = max(0.001, defender.motion.state_elapsed + defender.motion.event_left)
                attack_progress = clamp(defender.motion.state_elapsed / total, 0.0, 1.0)
            stage = min(7, int(attack_progress * 8.0))
            # O cano está à frente do peito, nunca no centro/perna do ator.
            # Água, fogo e veneno não ganham uma segunda figura colada na
            # arma. O fluxo real é desenhado pelo projétil contínuo, usando a
            # mesma origem física do cano durante toda a ação.
            # Se a folha já contém um clarão conectado, ele é preservado. Se
            # não contém, desenhamos um único clarão no mesmo ponto usado pelo
            # projétil. O tamanho vem da arma real da carta, nunca da SWAT como
            # molde universal; água e fogo não passam por esta camada.
            weapon_profile = DEFENDER_WEAPON_PROFILES.get(defender.key)
            if (
                weapon_profile is not None
                and weapon_profile.flash_size[0] > 0
                and not self.frame_has_muzzle_flash(sprite, defender)
            ):
                muzzle_x, muzzle_y = defender_weapon_origin(defender)
                flash_width, flash_height = weapon_profile.flash_size
                self.blit_muzzle_cycle(
                    stage,
                    muzzle_x,
                    muzzle_y,
                    width=flash_width * depth,
                    height=flash_height * depth,
                )
        if defender.corrosion > 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(defender.corrosion * 5.0) % 4,
                x, y - scale[1] * 0.38, scale[0] * 0.72, scale[1] * 0.62,
                alpha=168,
            )
        bar_width = max(32, int(44 * depth))
        self.health_bar(x - bar_width / 2, y + 5, bar_width, defender.hp / defender.max_hp, (89, 214, 144))
        if defender.max_ammo:
            ammo_width = max(28, int(38 * depth))
            ammo_ratio = (
                1.0 - defender.reload_timer / max(0.01, defender.reload_total)
                if defender.reloading
                else defender.ammo / max(1, defender.max_ammo)
            )
            self.ammo_bar(x - ammo_width / 2, y + 11, ammo_width, ammo_ratio)
        self.screen = world_target

    def draw_enemy(self, enemy: Enemy) -> None:
        assert self.battle is not None
        battle = self.battle
        water_enemy = battle.region == "beach" and enemy.row in battle.water_rows
        depth = lane_depth(battle.region, enemy.row)
        sprite = self.enemy_sprite(battle, enemy)
        frame_animated = enemy.visual_animation is not None
        render_x = enemy.x
        if frame_animated:
            animation = enemy.visual_animation
            assert animation is not None
            if animation.state == "bite":
                offsets = (
                    (0, 1, 2, 4, 7, 6, 3, 0)
                    if "runner" in enemy.tags
                    else (0, 2, 7, 14, 23, 21, 11, 0)
                )
                render_x -= offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            elif animation.state == "hit":
                offsets = (0, 3, 7, 10, 8, 5, 2, 0)
                render_x += offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            crawler = enemy.key in CRAWLER_ENEMIES
            if crawler:
                category = "crawler"
            elif enemy.is_boss:
                # O chefe é reconhecivelmente maior, mas não cresce a ponto de
                # invadir a pista vizinha ou ter cabeça/pés cortados.
                category = "boss"
            elif enemy.data.get("subboss"):
                category = "subboss"
            else:
                # Humanoides comuns compartilham a mesma altura corporal dos
                # soldados. A ameaça vem da animação e dos atributos, não de
                # um zumbi comum artificialmente gigante.
                category = "common"
            body_height, source_height = ENEMY_BODY_LAYOUTS[category]
            scale = animated_actor_render_scale(
                sprite,
                depth,
                body_height=body_height,
                source_body_height=source_height,
            )
        else:
            scale = enemy_render_scale(enemy, battle.region)
        shadow_width = max(28, int(scale[0] * (0.86 if enemy.is_boss else 0.68)))
        shadow_height = max(6, int(13 * depth))
        shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        if water_enemy:
            pygame.draw.ellipse(shadow, (91, 221, 238, 112), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (8, 37, 50, 88), shadow.get_rect().inflate(-10, -4))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 115), shadow.get_rect())
        self.screen.blit(shadow, shadow.get_rect(midbottom=(int(render_x), int(enemy.y + 3))))

        vertical_offset = 0.0
        alpha = 255
        top, bottom = lane_bounds(battle.region, enemy.row)
        lane_height = bottom - top
        if enemy.jump_state:
            progress = clamp(1.0 - enemy.jump_timer / max(0.01, enemy.jump_duration), 0.0, 1.0)
            vertical_offset = -math.sin(progress * math.pi) * lane_height * 0.78
        elif enemy.dig_state == "enter":
            progress = clamp(1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0)
            vertical_offset = lane_height * 0.42 * progress
            alpha = int(255 * (1.0 - progress * 0.42))
        elif enemy.dig_state == "emerge":
            progress = clamp(1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0)
            vertical_offset = lane_height * 0.42 * (1.0 - progress)
            alpha = int(146 + 109 * progress)
        entry_reveal = float(getattr(enemy, "entry_reveal", 0.0))
        if entry_reveal > 0 and enemy.age < entry_reveal:
            reveal = clamp(enemy.age / entry_reveal, 0.0, 1.0)
            reveal = reveal * reveal * (3.0 - 2.0 * reveal)
            alpha = min(alpha, max(0, int(255 * reveal)))
        state_override = (
            "swim"
            if water_enemy and enemy.motion.state == "walk"
            else None
        )
        rect = self.draw_actor_sprite(
            sprite,
            render_x,
            enemy.y,
            *scale,
            enemy.motion,
            enemy=True,
            vertical_offset=vertical_offset,
            alpha=alpha,
            state_override=state_override,
            profile=enemy_animation_profile(enemy),
            frame_animated=frame_animated,
        )
        world_target = self.screen
        if self.overlay_surface is not None:
            self.screen = self.overlay_surface
        if enemy.burn > 0:
            self.blit_effect_frame(
                "elemental_effects", 0, int(enemy.age * 11.0) % 4,
                render_x, enemy.y + 1, scale[0] * 0.94, scale[1] * 0.78,
                alpha=205, midbottom=True,
            )
        if enemy.poisoned > 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(enemy.age * 8.0) % 4,
                render_x, enemy.y - scale[1] * 0.42,
                scale[0] * 1.04, scale[1] * 0.72, alpha=176,
            )
        if enemy.soaked > 0:
            self.blit_effect_frame(
                "elemental_effects", 1, int(enemy.age * 9.0) % 4,
                render_x, enemy.y + 2, scale[0] * 1.15, scale[1] * 0.58,
                alpha=182, midbottom=True,
            )
        if enemy.corrosion > 0 and enemy.poisoned <= 0:
            self.blit_effect_frame(
                "elemental_effects", 2, int(enemy.age * 7.0) % 4,
                render_x, enemy.y - scale[1] * 0.46,
                scale[0] * 0.76, scale[1] * 0.54, alpha=154,
            )
        # Roubo, cura e demais habilidades só exibem efeito durante o gesto
        # correspondente. Uma aura permanente aqui parecia veneno aleatório.
        width = (74 if enemy.is_boss else 44) * depth
        self.health_bar(render_x - width / 2, enemy.y + 5, width, enemy.hp / enemy.max_hp, RED)
        self.screen = world_target

    @staticmethod
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
        for index in range(max(3, count)):
            q = index / max(1, count - 1)
            envelope = math.sin(q * math.pi)
            wave = math.sin(q * math.tau * 2.1 - elapsed * 31.0) * amplitude * envelope
            points.append(
                (
                    int(lerp(start[0], end[0], q) + normal_x * wave),
                    int(lerp(start[1], end[1], q) + normal_y * wave),
                )
            )
        return points

    @staticmethod
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

    @staticmethod
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

    def draw_pressurized_water(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        elapsed: float,
        depth: float,
        palette: tuple[tuple[int, int, int, int], ...],
    ) -> None:
        """Água sob pressão com massa, transparência e atomização na ponta."""
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = max(1.0, math.hypot(dx, dy))
        direction = pygame.Vector2(dx / distance, dy / distance)
        normal = pygame.Vector2(-direction.y, direction.x)
        count = max(14, min(30, int(distance / 5.5)))
        points: list[pygame.Vector2] = []
        for index in range(count):
            q = index / max(1, count - 1)
            wave = (
                math.sin(q * math.pi * 1.35 - elapsed * 9.0) * 0.72
                + math.sin(q * math.pi * 4.7 + elapsed * 7.0) * 0.20
            ) * depth
            fall = q * q * 5.2 * depth
            base = pygame.Vector2(lerp(start[0], end[0], q), lerp(start[1], end[1], q))
            points.append(base + normal * wave + pygame.Vector2(0, fall))

        tuples = [(round(point.x), round(point.y)) for point in points]
        outer = self.water_ribbon_polygon(
            tuples, 5.7 * depth, 3.3 * depth, elapsed, phase=0.0,
        )
        body = self.water_ribbon_polygon(
            tuples, 3.9 * depth, 2.0 * depth, elapsed, phase=1.4,
        )
        core = self.water_ribbon_polygon(
            tuples[: max(4, round(len(tuples) * 0.82))],
            1.65 * depth, 0.55 * depth, elapsed, phase=2.2,
        )
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if len(outer) >= 3:
            pygame.draw.polygon(layer, (19, 91, 145, 192), outer)
            pygame.draw.aalines(layer, (78, 181, 224, 205), True, outer)
        if len(body) >= 3:
            pygame.draw.polygon(layer, (48, 158, 210, 220), body)
        if len(core) >= 3:
            pygame.draw.polygon(layer, (183, 232, 244, 225), core)

        # Reflexos curtos percorrem a água em velocidades diferentes. Eles
        # comunicam vazão sem transformar o jato numa linha branca contínua.
        for index in range(4):
            q0 = (elapsed * (1.65 + index * 0.11) + index * 0.23) % 0.72
            q1 = min(0.84, q0 + 0.09 + index * 0.012)
            p0 = points[min(len(points) - 1, round(q0 * (len(points) - 1)))]
            p1 = points[min(len(points) - 1, round(q1 * (len(points) - 1)))]
            pygame.draw.aaline(
                layer, (224, 249, 252, 210),
                (round(p0.x), round(p0.y - depth)),
                (round(p1.x), round(p1.y - depth)),
            )
        pygame.draw.ellipse(
            layer, (102, 205, 235, 235),
            pygame.Rect(0, 0, max(4, round(8 * depth)), max(3, round(6 * depth))).move(
                round(start[0] - 4 * depth), round(start[1] - 3 * depth)
            ),
        )

        # A ponta atomiza em gotas de tamanhos diferentes. Todas continuam na
        # direção do mesmo alvo e no mesmo relógio, sem camada desencontrada.
        for index in range(14):
            q = 0.70 + index * 0.021
            base_index = min(len(points) - 1, round(q * (len(points) - 1)))
            base = points[base_index]
            side = math.sin(index * 2.31 + elapsed * 15.0) * (2.0 + index * 0.31) * depth
            forward = (2.0 + (index % 5) * 2.4) * depth
            drop = base + normal * side + direction * forward + pygame.Vector2(0, index * 0.34 * depth)
            radius = max(1, round((2.2 - index * 0.075) * depth))
            pygame.draw.circle(
                layer,
                (212, 245, 250, 220) if index % 3 == 0 else (66, 174, 219, 205),
                (round(drop.x), round(drop.y)),
                radius,
            )
        self.screen.blit(layer, (0, 0))

    def draw_combustion_flame(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        elapsed: float,
        travel: float,
        depth: float,
    ) -> None:
        """Chama cônica em ignição curta, abertura média e combustão plena.

        Cada quadro é redesenhado do zero. A fase anterior, portanto, some
        enquanto a próxima ocupa mais comprimento e volume. Isso evita tanto
        o acúmulo de quadros quanto o aspecto de uma fita líquida vermelha.
        """
        vector = pygame.Vector2(end[0] - start[0], end[1] - start[1])
        distance = vector.length()
        if distance < 2.0:
            return
        direction = vector.normalize()
        normal = pygame.Vector2(-direction.y, direction.x)
        phase = clamp(elapsed / max(0.01, travel), 0.0, 1.0)
        # Três poses materiais com transição suave: a anterior apaga enquanto
        # a seguinte assume o volume. Não há uma fita que cresce como água.
        stage = min(2, int(phase * 3.0))
        local = phase * 3.0 - stage
        stage_widths = (9.0, 20.0, 34.0)
        previous_width = stage_widths[max(0, stage - 1)]
        width = lerp(previous_width, stage_widths[stage], local) * depth
        flicker = math.sin(elapsed * 31.0) * 1.1 * depth
        tip = pygame.Vector2(end) + normal * flicker
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        def flame_polygon(length_ratio: float, width_ratio: float, wobble: float) -> list[pygame.Vector2]:
            """Pluma orgânica: volume contínuo com bordas vivas e assimétricas."""
            sample_count = 20
            upper: list[pygame.Vector2] = []
            lower: list[pygame.Vector2] = []
            for index in range(sample_count):
                q = index / (sample_count - 1)
                center = pygame.Vector2(start) + direction * distance * length_ratio * q
                envelope = math.sin(math.pi * q) ** 0.70
                # A pluma abre mais na metade final e fecha numa ponta fina.
                envelope *= 0.62 + 0.48 * q
                upper_noise = (
                    math.sin(index * 1.73 + elapsed * 24.0) * wobble
                    + math.sin(index * 0.61 - elapsed * 17.0) * wobble * 0.55
                )
                lower_noise = (
                    math.sin(index * 1.29 - elapsed * 21.0 + 1.4) * wobble
                    + math.sin(index * 0.47 + elapsed * 13.0) * wobble * 0.48
                )
                upper_half = width * width_ratio * envelope * (1.0 + upper_noise)
                lower_half = width * width_ratio * envelope * (0.82 + lower_noise)
                upper.append(center - normal * max(0.0, upper_half))
                lower.append(center + normal * max(0.0, lower_half))
            return upper + list(reversed(lower))

        outer = flame_polygon(1.0, 1.0, 0.12)
        middle = flame_polygon(0.90, 0.67, 0.10)
        hot = flame_polygon(0.64, 0.34, 0.07)
        pygame.draw.polygon(layer, (177, 43, 12, 188), outer)
        pygame.draw.aalines(layer, (233, 71, 15, 218), True, outer)
        pygame.draw.polygon(layer, (244, 89, 13, 232), middle)
        pygame.draw.polygon(layer, (255, 178, 36, 246), hot)

        # Línguas independentes quebram a borda do cone e dão combustão, não
        # líquido tingido. A ponta de cada língua pulsa, mas nunca volta.
        for index in range(6):
            q0 = 0.08 + index * 0.13
            q1 = min(0.94, q0 + 0.24 + (index % 3) * 0.09)
            center = pygame.Vector2(start) + direction * distance * q0
            tongue_tip = pygame.Vector2(start) + direction * distance * q1
            side = math.sin(elapsed * (21.0 + index) + index * 1.8) * width * 0.42
            tongue_tip += normal * side
            half = max(1.8, width * max(0.10, 0.27 - index * 0.025))
            color = (
                (255, 190, 43, 240)
                if index < 4
                else (244, 92, 20, 230)
            )
            pygame.draw.polygon(
                layer,
                color,
                [center - normal * half, tongue_tip, center + normal * half],
            )

        inner_tip = pygame.Vector2(start) + direction * distance * (0.32 + 0.07 * local)
        inner_half = max(1.8, width * 0.22)
        pygame.draw.polygon(
            layer,
            (255, 221, 92, 248),
            [pygame.Vector2(start) - normal * 1.5, inner_tip,
             pygame.Vector2(start) + normal * 1.5,
             pygame.Vector2(start) + direction * distance * 0.22 + normal * inner_half],
        )
        hot_tip = pygame.Vector2(start) + direction * distance * 0.30
        pygame.draw.line(
            layer, (255, 247, 198, 248), start,
            (round(hot_tip.x), round(hot_tip.y)), max(2, round(3.2 * depth)),
        )

        if stage == 2:
            for index in range(7):
                ember = tip - direction * (5 + index * 7) * depth
                ember += normal * math.sin(elapsed * 17.0 + index * 2.0) * (4 + index * 0.7) * depth
                pygame.draw.circle(
                    layer, (255, 131, 35, 170),
                    (round(ember.x), round(ember.y - index * 0.7 * depth)),
                    max(1, round(1.5 * depth)),
                )
            # Fumaça somente na combustão plena, deslocada para cima e já
            # perdendo opacidade; ela não nasce no bocal nem cobre o soldado.
            for index in range(3):
                smoke = tip - direction * (3 + index * 10) * depth
                smoke += normal * math.sin(elapsed * 8.0 + index) * 4.0 * depth
                smoke.y -= (5 + index * 3) * depth
                pygame.draw.circle(
                    layer, (54, 47, 42, 72 - index * 14),
                    (round(smoke.x), round(smoke.y)),
                    max(2, round((4.5 - index * 0.6) * depth)),
                )
        self.screen.blit(layer, (0, 0))

    def draw_elemental_stream(self, projectile: Projectile, x: float, y: float) -> None:
        """Desenha um fluxo contínuo preso ao emissor, sem sprite duplicada.

        A origem é recalculada no equipamento a cada quadro. Duas fitas
        suaves formam matéria e brilho; assim o jato cresce do bocal até o
        alvo sem virar uma mancha separada na frente do personagem.
        """
        if isinstance(projectile.owner, Defender):
            start_x, start_y = defender_weapon_origin(projectile.owner)
        elif isinstance(projectile.owner, Enemy):
            start_x, start_y = Battle.enemy_projectile_origin(
                projectile.owner,
                "acid" if projectile.kind == "poison" else "torpedo",
            )
        else:
            start_x, start_y = float(projectile.x), float(projectile.y)
        dx, dy = float(x) - start_x, float(y) - start_y
        distance = math.hypot(dx, dy)
        if distance < 3.0:
            return
        source_row = int(getattr(projectile.owner, "row", 0))
        depth = lane_depth(self.battle.region if self.battle else "city", source_row)
        palette = {
            "flame": ((125, 43, 24, 225), (239, 91, 31, 245), (255, 213, 72, 255)),
            "waterjet": ((24, 91, 142, 218), (57, 157, 202, 242), (178, 224, 234, 238)),
            "poison": ((38, 89, 42, 225), (83, 174, 50, 245), (180, 226, 81, 255)),
        }[projectile.kind]
        is_water = projectile.kind == "waterjet"
        if is_water:
            self.draw_pressurized_water(
                (start_x, start_y),
                (x, y),
                projectile.elapsed,
                depth,
                palette,
            )
            return
        if projectile.kind == "flame":
            self.draw_combustion_flame(
                (start_x, start_y), (x, y), projectile.elapsed,
                projectile.travel, depth,
            )
            return
        points = self.flow_points(
            (start_x, start_y),
            (x, y),
            projectile.elapsed,
            # Alta pressão oscila pouco. O desenho anterior ondulava como um
            # cabo elétrico e deixava três linhas separadas em vez de água.
            amplitude={"flame": 3.0, "poison": 3.5}[projectile.kind] * depth,
            count=max(9, min(24, int(distance / 7))),
        )
        outer = self.ribbon_polygon(points, 8.0 * depth, 5.0 * depth, taper_tip=True)
        middle = self.ribbon_polygon(points, 5.2 * depth, 2.8 * depth, taper_tip=True)
        core = self.ribbon_polygon(points, 2.1 * depth, 0.8 * depth, taper_tip=True)
        if len(outer) >= 3:
            pygame.draw.polygon(self.screen, palette[0], outer)
            pygame.draw.polygon(self.screen, palette[1], middle)
            pygame.draw.polygon(self.screen, palette[2], core)
        # Uma única gota/faísca de contato acompanha a ponta; não há clarão
        # adicional no bocal nem segunda animação concorrendo com o corpo.
        tip_radius = max(2, round(3.0 * depth))
        pygame.draw.circle(self.screen, palette[2], (round(x), round(y)), tip_radius)

    def draw_gas_grenade_projectile(
        self,
        x: float,
        y: float,
        angle: float,
        depth: float,
        progress: float,
        previous: tuple[float, float],
    ) -> None:
        """Cápsula química legível, pequena e distinta de uma bala comum."""
        width = max(12, round(15 * depth))
        height = max(8, round(9 * depth))
        capsule = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
        body = pygame.Rect(4, 4, width, height)
        pygame.draw.ellipse(capsule, (31, 42, 31, 235), body)
        pygame.draw.ellipse(capsule, (112, 131, 72, 255), body, max(1, round(depth)))
        band = pygame.Rect(
            body.centerx - max(1, round(2 * depth)), body.y + 1,
            max(2, round(4 * depth)), body.height - 2,
        )
        pygame.draw.rect(
            capsule, (148, 221, 78, 255), band,
            border_radius=max(1, round(depth)),
        )
        pygame.draw.circle(
            capsule, (213, 245, 139, 245),
            (body.right - max(2, round(3 * depth)), body.centery),
            max(1, round(1.4 * depth)),
        )
        rotated = pygame.transform.rotate(capsule, angle + progress * 720.0)

        # Uma esteira curta ajuda a leitura do arco, mas termina antes da
        # cápsula e jamais nasce como um segundo projétil.
        trail_alpha = round(135 * (1.0 - clamp((progress - 0.62) / 0.38, 0.0, 1.0)))
        trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.aaline(
            trail, (155, 215, 108, trail_alpha), previous,
            (lerp(previous[0], x, 0.58), lerp(previous[1], y, 0.58)),
        )
        self.screen.blit(trail, (0, 0))
        self.screen.blit(rotated, rotated.get_rect(center=(round(x), round(y))))

    def draw_projectiles(self, battle: Battle) -> None:
        arcing_kinds = {
            "grenade", "grenade_40mm", "gas_grenade", "mortar",
            "mortar_shell", "bazooka", "rpg7_rocket",
        }
        for projectile in battle.projectiles:
            if projectile.elapsed < 0:
                continue
            t = clamp(projectile.elapsed / projectile.travel, 0, 1)
            x = lerp(projectile.x, projectile.target_x, t)
            y = lerp(projectile.y, projectile.target_y, t) - (
                math.sin(t * math.pi) * 46 if projectile.kind in arcing_kinds else 0
            )
            if projectile.kind in {"flame", "poison", "waterjet"}:
                self.draw_elemental_stream(projectile, x, y)
                continue
            art = PROJECTILE_LAYOUTS.get(projectile.kind)
            if not art:
                continue
            row, column, width, height = art
            next_t = min(1.0, t + 0.025)
            next_x = lerp(projectile.x, projectile.target_x, next_t)
            next_y = lerp(projectile.y, projectile.target_y, next_t) - (
                math.sin(next_t * math.pi) * 46
                if projectile.kind in arcing_kinds
                else 0
            )
            angle = -math.degrees(math.atan2(next_y - y, next_x - x))
            source_row = int(getattr(projectile.owner, "row", 0))
            depth = lane_depth(battle.region, source_row)
            if projectile.kind == "gas_grenade":
                previous_t = max(0.0, t - 0.045)
                previous_x = lerp(projectile.x, projectile.target_x, previous_t)
                previous_y = lerp(projectile.y, projectile.target_y, previous_t) - (
                    math.sin(previous_t * math.pi) * 46
                )
                self.draw_gas_grenade_projectile(
                    x, y, angle, depth, t, (previous_x, previous_y),
                )
                continue
            self.blit_effect_frame(
                "projectile_sprites",
                row,
                column,
                x,
                y,
                width * depth,
                height * depth,
                alpha=176 if projectile.kind == "tracer" else 255,
                angle=angle,
            )

    def draw_particles(self, battle: Battle) -> None:
        # Partículas circulares foram retiradas. Impactos e matéria usam folhas
        # rasterizadas; textos de dano continuam sendo informação de HUD.
        for text in battle.texts:
            self.draw_text(text.text, self.fonts.tiny, text.color, (text.x, text.y), "center", True)

    def draw_battle_status(self) -> None:
        assert self.battle is not None
        battle = self.battle
        if battle.boss_warning > 0:
            banner = pygame.Rect(WIDTH // 2 - 330, 238, 660, 124)
            self.panel(banner, 244, RED, 12)
            self.draw_text("ALERTA: CHEFE CHEGANDO", self.fonts.h1, RED, (banner.centerx, banner.y + 16), "center", True)
            self.draw_text(battle.boss_banner_name, self.fonts.h2, WHITE, (banner.centerx, banner.y + 54), "center", True)
            self.draw_text(battle.boss_banner_subtitle, self.fonts.small, GOLD, (banner.centerx, banner.y + 85), "center")
        if battle.paused:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((3, 8, 12, 132))
            self.screen.blit(veil, (0, 0))
            pause_card = pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 74, 410, 148)
            self.panel(pause_card, 246, GOLD, 12)
            self.draw_text("PAUSADO", self.fonts.title, GOLD, (pause_card.centerx, pause_card.y + 23), "center", True)
            self.draw_text("Clique em PAUSA ou pressione P para continuar.", self.fonts.small, WHITE, (pause_card.centerx, pause_card.y + 86), "center")

    def draw_result_overlay(self) -> None:
        assert self.battle is not None
        battle = self.battle
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 6, 9, 188))
        self.screen.blit(overlay, (0, 0))
        heading = "REGIÃO PROTEGIDA" if battle.victory else "BASE INVADIDA"
        color = GOLD if battle.victory else RED
        self.panel(pygame.Rect(WIDTH // 2 - 265, HEIGHT // 2 - 130, 530, 285), 242, color, 16)
        self.draw_text(heading, self.fonts.title, color, (WIDTH / 2, HEIGHT / 2 - 85), "center", True)
        body = "Você venceu as 12 ondas e os três chefes da região. Todos os territórios continuam disponíveis." if battle.victory else "Um infectado atravessou a linha final. Refaça a equipe e preserve munição para as ondas finais."
        self.draw_wrapped(body, self.fonts.body, WHITE, pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 30, 410, 55), 3, center=True)
        self.draw_text(f"Onda alcançada: {battle.wave}/{TOTAL_WAVES}", self.fonts.small, GRAY, (WIDTH / 2, HEIGHT // 2 + 46), "center")
        self.button("VOLTAR AO MAPA", pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50), color)

    def health_bar(self, x: float, y: float, width: float, ratio: float, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 4)
        pygame.draw.rect(self.screen, (18, 21, 23), rect, border_radius=2)
        fill_width = int(rect.width * clamp(ratio, 0, 1))
        if fill_width > 0:
            pygame.draw.rect(self.screen, color, (rect.x, rect.y, fill_width, rect.height), border_radius=2)

    def ammo_bar(self, x: float, y: float, width: float, ratio: float) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 3)
        pygame.draw.rect(self.screen, (19, 28, 33), rect, border_radius=2)
        pygame.draw.rect(self.screen, TEAL, (rect.x, rect.y, int(rect.width * clamp(ratio, 0, 1)), rect.height), border_radius=2)

    def blit_sprite(self, sprite: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
        if sprite.get_width() <= 1:
            return
        scaled = self.assets.scaled(sprite, width, height)
        self.screen.blit(scaled, (int(x), int(y)))

    def blit_actor_in_rect(
        self,
        sprite: pygame.Surface,
        rect: pygame.Rect,
        body_height: int,
        *,
        source_body_height: float = 130.0,
        outline: tuple[int, int, int] | None = None,
    ) -> pygame.Rect:
        """Enquadra um ator sem deformar corpo, arma ou chapéu."""
        content = sprite.get_bounding_rect(min_alpha=8)
        if content.width <= 0 or content.height <= 0:
            return pygame.Rect(rect.centerx, rect.bottom, 1, 1)
        sprite = sprite.subsurface(content).copy()
        # Retrato é uma moldura de inspeção, não o campo de batalha. Ajustar
        # pelo próprio conteúdo garante corpo inteiro e ocupa a área útil sem
        # herdar escalas físicas diferentes de soldado, rastejador e chefe.
        max_width = rect.width - 18
        max_height = rect.height - 18
        limiter = min(max_width / content.width, max_height / content.height)
        rendered = pygame.transform.smoothscale(
            sprite,
            (max(1, round(content.width * limiter)), max(1, round(content.height * limiter))),
        )
        target = rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 4))
        if outline is not None:
            mask = pygame.mask.from_surface(rendered, threshold=8)
            silhouette = mask.to_surface(
                setcolor=(*outline, 205),
                unsetcolor=(0, 0, 0, 0),
            ).convert_alpha()
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                self.screen.blit(silhouette, target.move(dx, dy))
        self.screen.blit(rendered, target)
        return target

    def draw_portrait_backdrop(
        self, rect: pygame.Rect, accent: tuple[int, int, int]
    ) -> None:
        """Contraste neutro para uniformes pretos sem fingir transparência."""
        pygame.draw.rect(self.screen, (24, 35, 43), rect, border_radius=12)
        glow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow,
            (*accent, 38),
            (rect.width // 10, rect.height // 8, rect.width * 4 // 5, rect.height * 3 // 4),
        )
        self.screen.blit(glow, rect.topleft)
        pygame.draw.rect(self.screen, (*accent,), rect, width=1, border_radius=12)

    def card_sprite(self, region: str, key: str, index: int) -> pygame.Surface:
        """Escolhe a silhueta da carta e do objeto já posicionado.

        Minas recebem sprites individuais onde a leitura do cenário importa:
        cidade usa duas cargas urbanas limpas, Praia usa duas minas de areia e
        a Bomba de Água é uma mina naval independente, sem plataforma.
        """
        actor_key = DEFENDER_ACTOR_BY_KEY.get(key)
        if actor_key and self.assets.production_clips is None:
            self.assets.prepare_production_animations()
        if actor_key and self.assets.production_clips:
            return self.assets.production_clips[actor_key]["idle"].frames[1]
        custom_asset = CARD_ART_ASSETS.get((region, key))
        if custom_asset:
            return self.assets.images[custom_asset]
        terrain_mine_assets = {
            "city": {"mina": "city_mine_n1", "mina_segura": "city_mine_n2"},
            "beach": {"mina": "beach_mine_land_n1", "mina_segura": "beach_mine_land_n2"},
        }
        if key == "atirador_lancha":
            return self.assets.images["beach_boat_shooter"]
        asset_key = terrain_mine_assets.get(region, {}).get(key)
        if asset_key:
            return self.assets.images[asset_key]
        if key == "bomba_agua":
            return self.assets.images["beach_mine_water"]
        if DEFENSES.get(key, {}).get("water_only"):
            water_index = {"lancha": 5, "submarino": 6}[key]
            return self.assets.base_unit("beach", water_index)
        level = int(DEFENSES.get(key, {}).get("level", 1))
        return self.assets.unit(region, regional_sprite_index(region, key), level)

    @staticmethod
    def card_metrics(data: dict) -> tuple[str, str]:
        """Converte a função em dois números úteis para a face da carta.

        A descrição continua no hover/dossiê. Aqui entram apenas estatísticas
        que o jogador usa para decidir rápido entre custo, alcance, munição,
        cura, recarga e contenção.
        """
        role = str(data["role"])
        level = int(data["level"])
        if role == "radio":
            gain = int(data.get("supply_gain", 14 if level == 1 else 28))
            return f"SUP +{gain}", f"CICLO {float(data['cooldown']):.1f}s"
        if role == "sonar":
            return "REVELA CANAL", f"PULSO {float(data['cooldown']):.1f}s"
        if role in {"shield", "blade"}:
            return f"DANO {int(data['damage'])}", f"SEM MUNIÇÃO • ALC {int(data['range'])}"
        if role == "waterjet":
            return f"DANO {int(data['damage'])}", f"LENTO 32% • ALC {int(data['range'])}"
        if role == "poison":
            return f"DANO {int(data['damage'])}", f"VENENO 4.2s • ALC {int(data['range'])}"
        if role == "gas_grenade":
            return f"DANO {int(data['damage'])}", f"GÁS EM ÁREA • ALC {int(data['range'])}"
        if role == "promoter":
            return "PROMOVE N1→N2", f"CICLO {int(data['cooldown'])}s"
        if role == "barrier":
            return f"HP {int(data['hp'])}", "EXPLODE" if level >= 2 else "BLOQUEIO"
        if role == "mine":
            area = "ÁREA" if data.get("water_only") else ("SEGURA" if level >= 2 else "1 ALVO")
            return f"DANO {int(data['damage'])}", area
        if role == "suicide_bomber":
            return f"DANO {int(data['damage'])}", "CONTATO • IMÓVEL"
        reload_time = weapon_reload_seconds(data)
        reload_label = f" • REC {reload_time:.1f}s" if reload_time else ""
        return f"DANO {int(data['damage'])}", f"MUN {int(data['ammo'])}{reload_label}"

    def draw_wrapped(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect, lines: int, center: bool = False) -> None:
        words = text.split()
        built: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                built.append(current)
                current = word
        if current:
            built.append(current)
        for index, line in enumerate(built[:lines]):
            y = rect.y + index * (font.get_height() + 2)
            anchor = "midtop" if center else "topleft"
            x = rect.centerx if center else rect.x
            self.draw_text(line, font, color, (x, y), anchor)

    def draw(self) -> None:
        # Atores OpenGL ficam entre o mundo e o HUD. A cada quadro as duas
        # superfícies são reconstruídas; nenhuma animação deixa rastros.
        self.screen = self.world_surface
        self.world_surface.fill((0, 0, 0, 255))
        self.actor_commands.clear()
        if self.overlay_surface is not None:
            self.overlay_surface.fill((0, 0, 0, 0))
        if self.scene == "loading":
            self.draw_loading()
        elif self.scene == "title":
            self.draw_title()
        elif self.scene == "difficulty":
            self.draw_difficulty()
        elif self.scene == "campaign":
            self.draw_campaign()
        elif self.scene == "characters":
            self.draw_characters()
        elif self.scene == "story":
            self.draw_story()
        elif self.scene == "settings":
            self.draw_settings()
        elif self.scene == "howto":
            self.draw_howto()
        elif self.scene.startswith("dossier"):
            self.draw_dossier()
        elif self.scene == "battle" and self.battle:
            self.draw_battle()


if __name__ == "__main__":
    Game(integration_preview="--integracao-beta4" in sys.argv[1:]).run()
