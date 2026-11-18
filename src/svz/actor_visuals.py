"""Poses, escala e origem visual dos ataques."""
from __future__ import annotations
from .cache import SurfaceCache

from svz.visual_layout import defender_layout
import math
import pygame

from .board import (
    lane_depth,
)
from .config import (
    BEACH_WATER_ROWS,
)
from .content import (
    CRAWLER_ENEMIES,
    DEFENDER_ACTOR_BY_KEY,
)
from .math_utils import (
    clamp,
)
from .motion import (
    ActorMotion,
)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import Defender, Enemy

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


_EMITTER_CONTACT_CACHE = SurfaceCache(max_bytes=16 * 1024 * 1024, max_entries=2048)


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
        sprite,
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
