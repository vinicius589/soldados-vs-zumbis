"""Estado da partida e regras de combate."""
from __future__ import annotations

from svz.animation import AnimationManager
from typing import Callable
import math
import pygame
import random

from .balance import (
    boss_damage_scale,
    enemy_damage_scale,
)
from .board import (
    cell_center,
    cell_rect,
    lane_bomb_ground_y,
    lane_bomb_home_x,
    lane_bounds,
)
from .config import (
    BEACH_WATER_DEFENDERS,
    BEACH_WATER_ROWS,
    BOARD,
    CARD_RECHARGE_SECONDS,
    CELL_H,
    CELL_W,
    COLS,
    GOLD,
    GRAY,
    LANE_BOMB_HOME_X,
    LANE_PROTECTION_COLUMN,
    LANE_PROTECTION_END_X,
    LAST_PLACEABLE_COLUMN,
    RED,
    ROWS,
    TEAL,
    TOTAL_WAVES,
    WHITE,
)
from .content import (
    CRAWLER_ENEMIES,
    DEFENDER_ACTOR_BY_KEY,
    DEFENSES,
    ENEMIES,
    REGIONS,
    regional_sprite_index,
    REGION_ROSTERS,
    difficulty_profile,
)
from .combat_actions import CombatActionsMixin
from .enemy_abilities import EnemyAbilityMixin
from .enemy_motion import EnemyMotionMixin
from .entities import (
    Defender,
    Enemy,
    FloatingText,
    LaneBomb,
    Particle,
    Projectile,
    SpawnOrder,
)
from .math_utils import (
    clamp,
)
from .motion import (
    DefeatAnimation,
    VisualEffect,
)
from .projectile_combat import resolve_impact, update_aim
from . import hud_layout
from .waves import (
    WaveDirector,
)


from uuid import uuid4


class Battle(EnemyMotionMixin, CombatActionsMixin, EnemyAbilityMixin):
    def __init__(self, app: "Game", region: str, selected: list[tuple[str, str]]) -> None:
        self.wave_director = WaveDirector(self)
        self.app = app
        self.region = region
        self.score = 0
        self.match_id = uuid4().hex
        self.player_name = getattr(app, "player_name", "") or "Jogador"
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

    @property
    def accepts_actions(self) -> bool:
        return not self.paused and not self.finished

    def place(self, row: int, col: int) -> bool:
        if not self.accepts_actions:
            return False
        if self.card_cooldowns[self.selected_card] > 0:
            self.announce("Esta carta ainda está recarregando.", 1.3, GRAY)
            return False
        key, display = self.card()
        allowed, reason = self.can_place(key, row, col)
        if not allowed:
            self.announce(reason, 1.7, RED)
            return False
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
        return True

    def remove_defender(self, row: int, col: int) -> None:
        """Retira uma defesa por escolha do jogador e devolve parte do custo."""
        if not self.accepts_actions:
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
            self.announce("Nenhuma tropa para recolher nesta posição.", 1.4, GRAY)
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
        return hud_layout.menu_rect()

    @staticmethod
    def pause_rect() -> pygame.Rect:
        return hud_layout.pause_rect()

    @staticmethod
    def remove_rect() -> pygame.Rect:
        return hud_layout.remove_rect()

    @staticmethod
    def next_wave_rect() -> pygame.Rect:
        return hud_layout.next_wave_rect()

    def start_next_wave(self) -> bool:
        if not self.accepts_actions or self.started_wave or self.wave >= TOTAL_WAVES:
            return False
        self.wave_director.start_next_wave()
        return True

    def build_wave(self, wave: int) -> list[SpawnOrder]:
        return self.wave_director.build_wave(wave)

    def spawn_row_for(self, enemy_key: str, boss: bool=False) -> int:
        return self.wave_director.spawn_row_for(enemy_key, boss)

    def spawn_enemy(self, order: SpawnOrder) -> None:
        return self.wave_director.spawn_enemy(order)

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
            defender.tactical_ammo_timer = max(0.0, defender.tactical_ammo_timer - dt)
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
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("O tempo dos projéteis deve ser finito e não negativo.")
        for projectile in self.projectiles[:]:
            projectile.elapsed += dt
            if projectile.elapsed < 0:
                continue
            update_aim(self, projectile)
            if projectile.elapsed < projectile.travel:
                continue
            self.projectiles.remove(projectile)
            resolve_impact(self, projectile)

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
        return self.wave_director.update_wave(dt)

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
        if getattr(self.app, "pending_powerup", None):
            self.app.try_use_powerup(pos)
            return
        if self.remove_rect().collidepoint(pos):
            self.remove_mode = not self.remove_mode
            self.announce("Voltar à base: clique na tropa que deseja recolher." if self.remove_mode else "Retorno à base desativado.", 1.8, TEAL)
            return
        if self.next_wave_rect().collidepoint(pos):
            if not self.started_wave:
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
        return hud_layout.card_rects(len(self.selected))
