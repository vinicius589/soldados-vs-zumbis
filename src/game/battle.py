"""Estado e regras de uma batalha em andamento."""
from __future__ import annotations

from src.game.runtime import *  # noqa: F403

class Battle:
    def __init__(self, app: Game, region: str, selected: list[tuple[str, str]]) -> None:
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

    def announce(
        self, message: str, seconds: float = 2.5, color: tuple[int, int, int] = WHITE
    ) -> None:
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
            return (
                False,
                f"Esta Unidade ocupa {footprint} casas e não cabe nesse ponto.",
            )
        if any(
            d.row == row
            and requested.intersection(
                range(d.col, d.col + max(1, int(d.stats.get("footprint", 1))))
            )
            for d in self.defenders
        ):
            return False, "Este ponto já está ocupado."
        if (
            LANE_PROTECTION_COLUMN in requested
            and self.lane_bombs[row].state != "spent"
        ):
            return False, "Casa reservada à contenção inicial desta faixa."
        water = self.cell_is_water(row, col)
        if data.get("water_only") and key not in BEACH_WATER_DEFENDERS:
            return (
                False,
                "Esta unidade aquática pertence ao catálogo antigo e não entra na Beta 4.",
            )
        if key in BEACH_WATER_DEFENDERS and not water:
            return (
                False,
                "Unidade aquática: só pode ser instalada nas faixas de água da Praia.",
            )
        if water and key not in BEACH_WATER_DEFENDERS:
            return (
                False,
                "Canal exclusivo: posicione o Barco de Patrulha ou o Submarino Tático.",
            )
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
        defender = Defender(
            key, display, row, col, data, sprite_index, region=self.region
        )
        actor_key = DEFENDER_ACTOR_BY_KEY.get(key)
        if actor_key:
            defender.visual_animation = self.app.assets.new_production_animation(
                actor_key
            )
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
            self.announce(
                "No Fácil, as tropas posicionadas não podem ser removidas.", 1.8, GRAY
            )
            return
        defender = next(
            (
                d
                for d in self.defenders
                if d.row == row
                and d.col <= col < d.col + max(1, int(d.stats.get("footprint", 1)))
            ),
            None,
        )
        if defender is None:
            self.announce("Nenhuma tropa nesta faixa para recolher.", 1.4, GRAY)
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
                self.explosion(
                    LANE_PROTECTION_END_X[self.region], y, explosion_color, 22
                )

    @staticmethod
    def menu_rect() -> pygame.Rect:
        return pygame.Rect(16, 126, 90, 34)

    @staticmethod
    def pause_rect() -> pygame.Rect:
        return pygame.Rect(112, 126, 92, 34)

    @staticmethod
    def remove_rect() -> pygame.Rect:
        return pygame.Rect(210, 126, 156, 34)

    @staticmethod
    def next_wave_rect() -> pygame.Rect:
        return pygame.Rect(372, 126, 124, 34)

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
            self.announce(
                f"Onda {self.wave}: a escolta do chefe está a caminho.", 2.6, RED
            )
        elif slot == 3:
            subboss_key = REGION_SUBBOSSES[self.region][chapter]
            self.announce(
                f"Onda {self.wave}: SUB-BOSS {ENEMIES[subboss_key]['name']}.", 2.4, GOLD
            )
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
        count = max(
            2, int(round(base_count * float(self.difficulty_data["spawn_count"])))
        )
        wave_progress = wave / TOTAL_WAVES
        for index in range(count):
            if index < 3:
                key = pool[min(index, len(pool) - 1)]
            else:
                weighted = pool.copy()
                if wave_progress > 0.35:
                    weighted.extend(pool[-min(3, len(pool)) :])
                if wave_progress > 0.70:
                    weighted.extend(pool[-min(5, len(pool)) :])
                key = random.choice(weighted)
            wait = (1.28 - 0.07 * (wave - 1) + random.random() * 0.16) * float(
                self.difficulty_data["spawn_wait"]
            )
            orders.append(SpawnOrder(wait, key, self.spawn_row_for(key)))
        if slot == 3:
            subboss_key = REGION_SUBBOSSES[self.region][chapter]
            orders.append(
                SpawnOrder(0.85, subboss_key, self.spawn_row_for(subboss_key))
            )
        elif slot == 4:
            boss_key = REGION_BOSSES[self.region][chapter]
            escort_count = max(
                1,
                int(round((1 + chapter) * float(self.difficulty_data["escort_count"]))),
            )
            for _ in range(escort_count):
                escort_key = random.choice(pool[-min(4, len(pool)) :])
                orders.insert(
                    random.randrange(len(orders) + 1),
                    SpawnOrder(0.32, escort_key, self.spawn_row_for(escort_key)),
                )
            orders.append(
                SpawnOrder(
                    1.15, boss_key, self.spawn_row_for(boss_key, boss=True), True
                )
            )
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
        if (
            boss
            or enemy_key in BEACH_WATER_ENEMIES
            or ENEMIES.get(enemy_key, {}).get("amphibious")
        ):
            return random.choice(tuple(self.water_rows))
        land_rows = tuple(row for row in range(ROWS) if row not in self.water_rows)
        return random.choice(land_rows)

    def spawn_enemy(self, order: SpawnOrder) -> None:
        data = BOSSES.get(order.key) or ENEMIES[order.key]
        enemy = Enemy(
            order.key,
            order.row,
            data,
            self.region,
            self.wave,
            difficulty=self.difficulty,
        )
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

    def target_in_range(
        self, defender: Defender, min_distance: float = 0
    ) -> Enemy | None:
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
            "xerife_rua": lambda enemy: enemy.key
            in {"infectado_urbano", "tecnico_subestacao"},
            "atirador_precisao_swat": lambda enemy: bool(enemy.data.get("immunities"))
            or enemy.data.get("subboss", False),
            "agente_entrada": lambda enemy: enemy.key in {"bruto", "bruto_demolidor"},
            "especialista_antipraga": lambda enemy: enemy.key
            in {"policial", "divisor", "cuspidor_alfa"},
            "lancador_foguetes": lambda enemy: "shield" in enemy.tags
            or enemy.data.get("subboss", False),
            "escudeiro_tropa_choque": lambda enemy: enemy.key
            in {"bruto", "bruto_demolidor"},
            "atirador_horizonte": lambda enemy: enemy.key
            in {"curandeiro", "necromante"},
            "tenente_artilheiro": lambda enemy: enemy.key
            in {"mutante", "mutante_ruinas"},
            "incinerador_deserto": lambda enemy: enemy.key
            in {"curandeiro", "necromante"},
            "guardiao_laminas": lambda enemy: enemy.key == "parasita",
            "atirador_precisao_marinha": lambda enemy: enemy.key
            in {"mergulhador", "cacador"},
            "bombeiro_hidraulico": lambda enemy: enemy.key == "salva_vidas"
            or "shield" in enemy.tags,
            "submarino_tatico": lambda enemy: enemy.is_boss
            or enemy.key in {"mergulhador", "cacador"},
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
        self.announce(
            "Escavador: começou a cavar sob a primeira defesa.", 1.55, (232, 198, 112)
        )

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
            progress = clamp(
                1.0 - enemy.jump_timer / max(0.01, enemy.jump_duration), 0.0, 1.0
            )
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
            progress = clamp(
                1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0
            )
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

    def take_enemy_damage(
        self,
        enemy: Enemy,
        amount: float,
        effect: str = "",
        source: Defender | None = None,
    ) -> None:
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
                self.texts.append(
                    FloatingText("DEFESA ROMPIDA", enemy.x, enemy.y - 65, TEAL, 0.9)
                )
                self.announce(f"{source.display_name} rompeu {label}.", 1.5, TEAL)

        # Contenções de início de pista continuam absolutas. A imunidade vale
        # para tropas e projéteis, não para o dispositivo único da própria fase.
        containment_hit = source is None and amount >= 9000
        if not containment_hit and enemy.defense_broken <= 0:
            if channel in tuple(enemy.data.get("immunities", ())) and not counter_hit:
                self.texts.append(
                    FloatingText("IMUNE", enemy.x, enemy.y - 54, RED, 0.65)
                )
                return
            resistance = float(enemy.data.get("resistances", {}).get(channel, 0.0))
            amount *= max(0.0, 1.0 - clamp(resistance, 0.0, 0.95))
        weakness = float(enemy.data.get("weaknesses", {}).get(channel, 1.0))
        amount *= max(0.0, weakness)
        armor = float(enemy.data.get("armor", 0))
        if "shield" in enemy.tags and effect not in {
            "flame",
            "poison",
            "explosion",
            "mortar",
        }:
            armor = max(armor, 0.52)
        if source and source.ascended > 0:
            amount *= 1.55
        applied = amount * (1 - armor)
        enemy.hp -= applied
        if effect not in {"status_tick", "acid"}:
            self.app.audio.play("zombie_hit", min_interval_ms=70)
        if effect not in {"status_tick", "acid"}:
            enemy.motion.flash()
            # Uma rajada não pode manter a animação não repetitiva no último
            # quadro. Cada reação termina e reserva um intervalo de corrida.
            # O Corredor reage visualmente, mas nunca perde velocidade por
            # stagger; os demais pausam somente em impactos registrados.
            if not enemy.jump_state and not enemy.dig_state:
                runner = "runner" in enemy.tags
                reacted = enemy.motion.react_to_hit(
                    RUNNER_HIT_SECONDS if runner else ZOMBIE_HIT_SECONDS,
                    recovery=0.42 if runner else 0.26,
                )
                if reacted and "unstaggerable" not in enemy.tags:
                    enemy.stun = max(
                        enemy.stun, float(enemy.data.get("damage_stagger", 0.14))
                    )
        if effect == "flame":
            was_burning = enemy.burn > 0
            enemy.burn = max(enemy.burn, 3.3)
            if not was_burning:
                self.pulse(enemy.x, enemy.y - 20, (246, 142, 45), 6)
            self.effects.append(
                VisualEffect(
                    "flame_impact",
                    enemy.x,
                    enemy.y - 24,
                    (246, 142, 45),
                    0.26,
                    scale=0.72,
                )
            )
        elif effect == "poison":
            was_poisoned = enemy.poisoned > 0
            enemy.poisoned = max(enemy.poisoned, 4.2)
            if not was_poisoned:
                self.pulse(enemy.x, enemy.y - 20, (132, 239, 80), 7)
            self.effects.append(
                VisualEffect(
                    "toxic_impact",
                    enemy.x,
                    enemy.y - 24,
                    (132, 239, 80),
                    0.34,
                    scale=0.82,
                )
            )
        elif effect == "water":
            # Água não substitui o dano de fogo em força bruta: ela extingue
            # a queima e segura o avanço do alvo por uma janela curta.
            enemy.burn = 0.0
            soak_time = 3.6 if source and source.ascended > 0 else 2.4
            enemy.soaked = max(enemy.soaked, soak_time)
            self.effects.append(
                VisualEffect(
                    "water_impact",
                    enemy.x,
                    enemy.y - 20,
                    (102, 224, 244),
                    0.30,
                    scale=0.78,
                )
            )
        if effect == "acid":
            enemy.corrosion = max(enemy.corrosion, 2.5)
        self.texts.append(
            FloatingText(
                str(max(0, int(round(applied)))),
                enemy.x,
                enemy.y - 52,
                GOLD if source and source.ascended else WHITE,
                0.55,
            )
        )
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def damage_defender(
        self, defender: Defender, amount: float, effect: str = ""
    ) -> None:
        if defender.hp <= 0:
            return
        defender.hp -= amount
        self.app.audio.play("soldier_hit", min_interval_ms=95)
        defender.motion.flash()
        defender.motion.react_to_hit(SOLDIER_HIT_SECONDS, recovery=0.22)
        if effect == "stun":
            defender.stun = max(defender.stun, 2.2)
        elif effect == "acid":
            defender.corrosion = max(defender.corrosion, 4.0)
        elif effect == "acid_brief":
            defender.corrosion = max(defender.corrosion, 1.8)
        if effect in {"acid", "acid_brief"}:
            self.effects.append(
                VisualEffect(
                    "toxic_impact",
                    defender.x,
                    defender.y - 28,
                    (132, 239, 80),
                    0.28,
                    scale=0.58,
                )
            )
        self.texts.append(
            FloatingText(str(int(amount)), defender.x, defender.y - 48, RED, 0.6)
        )
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
                if (
                    enemy.row == defender.row
                    and abs(enemy.x - defender.x) < CELL_W * 1.35
                ):
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
                if (
                    defender.row == enemy.row
                    and abs(defender.x - enemy.x) < CELL_W * 1.15
                ):
                    self.damage_defender(
                        defender,
                        self.scaled_enemy_damage(enemy, 52 + self.wave * 2),
                        "acid",
                    )
            self.explosion(enemy.x, enemy.y, (114, 212, 99), 25)
        if enemy.is_boss:
            bonus = int(
                round((46 + self.wave * 2) * float(self.difficulty_data["supply_gain"]))
            )
            self.supplies = min(
                int(self.difficulty_data["supply_cap"]), self.supplies + bonus
            )
            self.boss_seen.add(self.wave)
            self.announce(f"Chefe neutralizado: +{bonus} suprimentos.", 3.4, GOLD)
            self.pulse(WIDTH / 2, HEIGHT / 2, GOLD, 75)
        elif enemy.data.get("subboss"):
            bonus = int(round(18 * float(self.difficulty_data["supply_gain"])))
            self.supplies = min(
                int(self.difficulty_data["supply_cap"]), self.supplies + bonus
            )
            self.announce(f"Sub-boss neutralizado: +{bonus} suprimentos.", 2.4, GOLD)
        else:
            self.supplies = min(
                int(self.difficulty_data["supply_cap"]), self.supplies + 1
            )

    def pulse(
        self, x: float, y: float, color: tuple[int, int, int], amount: int
    ) -> None:
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
        self.effects.append(
            VisualEffect("explosion", x, y - 18, color, 0.46, scale=scale)
        )
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
        defender.attack_timer = float(defender.stats["cooldown"]) * (
            0.68 if ascending else 1.0
        )
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
        if (
            defender.visual_animation is not None
            and "shoot" in defender.visual_animation.animations
        ):
            # O projétil é criado neste mesmo método. Colocar a sprite em
            # disparo agora impede que sua origem seja medida na pose parada.
            defender.visual_animation.play("shoot", restart=True)
        heavy_roles = {
            "heavy",
            "shotgun",
            "sniper",
            "grenade",
            "gas_grenade",
            "mortar",
            "rocket",
            "sub",
        }
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
            self.projectiles.append(
                Projectile(
                    miss_x,
                    miss_y,
                    None,
                    target.x,
                    target.y - 18,
                    0,
                    "tracer",
                    defender,
                    travel=0.22,
                )
            )
            return
        damage = float(defender.stats["damage"]) * float(
            self.difficulty_data["defender_damage"]
        )
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
            kind, radius = profiled_kind or "shotgun", CELL_W * (
                0.45 if ascending else 0.25
            )
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
                        if enemy is not target
                        and enemy.row == target.row
                        and enemy.hp > 0
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
        elif kind in {
            "grenade",
            "grenade_40mm",
            "gas_grenade",
            "bazooka",
            "rpg7_rocket",
        }:
            projectile.elapsed = -0.12
        self.projectiles.append(projectile)

    def closest_enemy_at(self, row: int, x: float) -> Enemy | None:
        candidates = [
            enemy for enemy in self.enemies if enemy.row == row and enemy.hp > 0
        ]
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
        old_ammo_ratio = (
            target.ammo / max(1, target.max_ammo) if target.max_ammo else 1.0
        )
        target.key = target_key
        target.stats = upgraded
        target.sprite_index = regional_sprite_index(self.region, target_key)
        target.hp = max(1.0, float(upgraded["hp"]) * max(0.55, old_hp_ratio))
        target.ammo = (
            int(round(int(upgraded["ammo"]) * old_ammo_ratio))
            if int(upgraded["ammo"])
            else 0
        )
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
        self.announce(
            f"PROMOÇÃO CONCLUÍDA: {target.display_name} agora é N2!", 2.5, GOLD
        )
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
            self.texts.append(
                FloatingText(f"+{gain} SUP", defender.x, defender.y - 55, GOLD, 1.0)
            )
            self.pulse(defender.x, defender.y - 18, GOLD, 8)
        elif role == "promoter" and defender.utility_timer <= 0:
            self.promote_defender(defender)
        elif role == "sonar" and defender.utility_timer <= 0:
            revealed = [
                enemy
                for enemy in self.enemies
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
                self.announce(
                    f"Sonar: {len(revealed)} ameaça(s) revelada(s).", 1.3, TEAL
                )

    def update_self_reload(self, defender: Defender, dt: float) -> bool:
        """Executa a recarga da própria arma e bloqueia o tiro nesse estado."""
        if defender.max_ammo <= 0 or defender.ammo > 0:
            defender.reload_timer = 0.0
            defender.reload_total = 0.0
            return False
        # A última rajada continua visualmente completa antes de a arma baixar.
        if (
            defender.reload_timer <= 0
            and defender.motion.state == "attack"
            and defender.motion.event_left > 0
        ):
            return True
        if defender.reload_timer <= 0:
            defender.reload_total = weapon_reload_seconds(
                defender.stats, defender.ascended > 0
            )
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
                reload_seconds = max(
                    0.01, defender.reload_total or defender.reload_timer
                )
                state, rate = "reload", clip.duration / reload_seconds
            elif (
                defender.motion.state == "support" and "support" in animation.animations
            ):
                state, rate = "support", 1.0
            elif defender.motion.state == "hit":
                state = "hit"
                rate = animation.animations["hit"].duration / SOLDIER_HIT_SECONDS
            elif defender.motion.state == "stunned":
                # Atordoamento longo não pode segurar o último quadro do
                # clipe de dano, que é uma ação única.
                state, rate = "idle", 1.0
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
            elif enemy.motion.state == "hit":
                state = "hit"
                window = (
                    RUNNER_HIT_SECONDS if "runner" in enemy.tags else ZOMBIE_HIT_SECONDS
                )
                rate = animation.animations["hit"].duration / window
            elif enemy.motion.state == "stunned":
                state = "idle"
            elif enemy.motion.state in {"walk", "spawn"} or (
                "runner" in enemy.tags
                and enemy.stun <= 0
                and self.blocker_for(enemy) is None
            ):
                state = "move"
                # Cada ciclo cobre um comprimento de passada coerente com a
                # silhueta. Corredores alternam os pés mais depressa;
                # rastejadores apoiam braços e tronco com cadência lenta.
                speed = float(enemy.data["speed"]) * (1.55 if enemy.rage > 0 else 1.0)
                if enemy.soaked > 0:
                    speed *= 0.68
                if enemy.poisoned > 0:
                    speed *= 0.88
                stride = (
                    22.0
                    if "runner" in enemy.tags
                    else (12.0 if enemy.key in CRAWLER_ENEMIES else 18.0)
                )
                rate = clamp(
                    animation.animations["move"].duration * speed / stride, 0.48, 2.4
                )
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
                target = next(
                    (
                        enemy
                        for enemy in self.enemies
                        if enemy.row == defender.row and abs(enemy.x - defender.x) < 49
                    ),
                    None,
                )
                if target:
                    is_safe = defender.stats["level"] >= 2
                    if is_safe or random.random() < 0.72:
                        if defender.ascended:
                            for enemy in self.enemies[:]:
                                if enemy.row == defender.row:
                                    self.take_enemy_damage(
                                        enemy, 9999, "explosion", defender
                                    )
                            self.announce(
                                "Mina ascensionada: linha inteira limpa!", 1.7, GOLD
                            )
                        else:
                            radius = CELL_W * (
                                0.82 if defender.key == "bomba_agua" else 0.35
                            )
                            for enemy in self.enemies[:]:
                                if (
                                    enemy.row == defender.row
                                    and abs(enemy.x - defender.x) < radius
                                ):
                                    self.take_enemy_damage(
                                        enemy,
                                        defender.stats["damage"],
                                        "explosion",
                                        defender,
                                    )
                        self.effects.append(
                            VisualEffect(
                                "explosion",
                                defender.x,
                                defender.y - 13,
                                GOLD,
                                0.32,
                                scale=0.95,
                            )
                        )
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
                        if (
                            enemy.row == defender.row
                            and abs(enemy.x - defender.x) <= radius
                        ):
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
        visual_kind, visual_color = entrance_visuals.get(
            str(boss_type), ("ground_slam", RED)
        )
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
            self.announce(
                "BRUTO DEMOLIDOR: tropas militares paralisadas por 3 s!", 2.8, RED
            )
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
            self.announce(
                "Cuspidor Alfa: névoa ácida global por um instante!",
                2.4,
                (150, 232, 112),
            )
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if (
                    abs(defender.row - enemy.row) <= 1
                    and abs(defender.x - enemy.x) < CELL_W * 2.25
                ):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 8))
                    defender.stun = max(defender.stun, 1.15)
            enemy.skill_timer = 14.0
            self.announce(
                "Mutante das Ruínas: o abalo atingiu apenas a vanguarda próxima.",
                2.2,
                RED,
            )
        elif boss_type == "necromante":
            self.enemies.append(
                Enemy(
                    "necromante_minion",
                    enemy.row,
                    ENEMIES["necromante_minion"],
                    self.region,
                    self.wave,
                    difficulty=self.difficulty,
                    x=enemy.x + 48,
                )
            )
            enemy.skill_timer = 15.0
            self.announce(
                "Necromante: uma múmia foi invocada na chegada.", 2.3, (197, 128, 238)
            )
        elif boss_type == "colosso":
            for defender in self.defenders:
                if self.is_military_defender(defender):
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce(
                "Colosso Mutante: tremor inicial interrompeu os tiros por 1,2 s.",
                2.4,
                RED,
            )
        elif boss_type == "tide":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 8))
                    defender.stun = max(defender.stun, 0.9)
            enemy.skill_timer = 14.0
            self.announce(
                "Bruto da Maré: a primeira onda abalou o canal.", 2.1, (95, 195, 239)
            )
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 4.8, enemy.x - CELL_W * 0.7)
            enemy.skill_timer = 13.0
            self.announce(
                "Caçador Abissal: mergulhou e surgiu mais perto no canal.",
                2.1,
                (95, 195, 239),
            )
        elif boss_type == "leviathan":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 14))
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce(
                "LEVIATÃ: uma onda de entrada atingiu a faixa de água.",
                2.4,
                (95, 195, 239),
            )
        else:
            enemy.skill_timer = 12.0

    @staticmethod
    def enemy_projectile_origin(enemy: Enemy, kind: str) -> tuple[float, float]:
        """Ponto anatômico/equipamento de onde cada ataque realmente parte."""
        category = (
            "boss"
            if enemy.is_boss
            else ("subboss" if enemy.data.get("subboss") else "common")
        )
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
        category = (
            "boss"
            if enemy.is_boss
            else ("subboss" if enemy.data.get("subboss") else "common")
        )
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
        if (
            kind
            in {
                "arcane_cast",
                "electric_arc",
                "signal_pulse",
                "heal_pulse",
                "heal_receive",
                "command_aura",
                "parasite_burst",
            }
            and animation is not None
        ):
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
        if kind in {
            "arcane_cast",
            "electric_arc",
            "signal_pulse",
            "heal_pulse",
            "heal_receive",
            "supply_snatch",
            "command_aura",
            "parasite_burst",
        }:
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
        enemy.skill_timer = cooldowns.get(boss_type, 12.0) * float(
            self.difficulty_data["skill_cooldown"]
        )
        skill_duration = self.enemy_skill_duration(enemy)
        enemy.motion.trigger("skill", skill_duration)
        if (
            enemy.visual_animation is not None
            and "skill" in enemy.visual_animation.animations
        ):
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
        visual_kind, visual_color = skill_visuals.get(
            str(boss_type), ("ground_slam", RED)
        )
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
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and self.is_military_defender(d)
            ]
            for defender in targets:
                defender.stun = max(defender.stun, 1.2)
                self.pulse(defender.x, defender.y - 22, RED, 7)
            self.announce(
                f"Martelo do Bruto: faixa {enemy.row + 1} interrompida por 1,2 s.",
                2.0,
                RED,
            )
        elif boss_type == "comandante":
            escorts = [
                other
                for other in self.enemies
                if other is not enemy
                and abs(other.row - enemy.row) <= 1
                and abs(other.x - enemy.x) < CELL_W * 2.8
            ]
            for other in escorts:
                other.rage = max(other.rage, 2.2)
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.5
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                for vertical in (-11, 9):
                    damage = self.scaled_enemy_damage(enemy, 10 + self.wave)
                    origin_x, origin_y = self.enemy_projectile_origin(
                        enemy, "enemy_bullet"
                    )
                    self.projectiles.append(
                        Projectile(
                            origin_x,
                            origin_y + vertical,
                            victim,
                            victim.x,
                            victim.y - 24,
                            damage,
                            "enemy_bullet",
                            enemy,
                            0,
                            False,
                            0.32,
                        )
                    )
            self.announce(
                "Comandante: escolta próxima acelerada e rajada dupla disparada.",
                1.9,
                RED,
            )
        elif boss_type == "alfa":
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0
            ]
            for victim in sorted(
                targets, key=lambda defender: defender.x, reverse=True
            )[:1]:
                damage = self.scaled_enemy_damage(enemy, 10 + self.wave)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "acid")
                self.projectiles.append(
                    Projectile(
                        origin_x,
                        origin_y,
                        victim,
                        victim.x,
                        victim.y - 18,
                        damage,
                        "acid",
                        enemy,
                        0,
                        False,
                        0.45,
                        effect="acid_brief",
                    )
                )
            self.announce(
                f"Cuspidor Alfa: saliva corrosiva na faixa {enemy.row + 1}.",
                1.8,
                (150, 232, 112),
            )
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if (
                    defender.row == enemy.row
                    and abs(defender.x - enemy.x) < CELL_W * 2.15
                ):
                    self.damage_defender(defender, self.scaled_enemy_damage(enemy, 12))
                    defender.stun = max(defender.stun, 1.0)
            self.announce(
                f"Mutante: punho de ruína na faixa {enemy.row + 1}.", 1.8, RED
            )
        elif boss_type == "necromante":
            self.enemies.append(
                Enemy(
                    "necromante_minion",
                    enemy.row,
                    ENEMIES["necromante_minion"],
                    self.region,
                    self.wave,
                    difficulty=self.difficulty,
                    x=enemy.x + 42,
                )
            )
            for other in self.enemies:
                if other is not enemy and abs(other.x - enemy.x) < CELL_W * 1.65:
                    other.hp = min(other.max_hp, other.hp + 28)
            self.announce(
                "Necromante: novas múmias e cura localizada da escolta.",
                2.0,
                (197, 128, 238),
            )
        elif boss_type == "colosso":
            targets = [
                d
                for d in self.defenders
                if d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                damage = self.scaled_enemy_damage(enemy, 18)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "mortar")
                self.projectiles.append(
                    Projectile(
                        origin_x,
                        origin_y,
                        victim,
                        victim.x,
                        victim.y - 24,
                        damage,
                        "mortar",
                        enemy,
                        0,
                        False,
                        0.52,
                    )
                )
            self.announce("Colosso: rocha arremessada contra uma faixa-alvo.", 1.9, RED)
        elif boss_type == "tide":
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, self.scaled_enemy_damage(enemy, 12))
                victim.stun = max(victim.stun, 0.8)
            self.announce(
                "Bruto da Maré: golpe concentrado no canal.", 1.8, (95, 195, 239)
            )
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 3.4, enemy.x - CELL_W * 0.85)
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, self.scaled_enemy_damage(enemy, 10))
                victim.stun = max(victim.stun, 0.7)
            self.announce(
                "Caçador Abissal: mergulho ofensivo no canal.", 1.8, (95, 195, 239)
            )
        elif boss_type == "leviathan":
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                damage = self.scaled_enemy_damage(enemy, 24)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "torpedo")
                self.projectiles.append(
                    Projectile(
                        origin_x,
                        origin_y,
                        victim,
                        victim.x,
                        victim.y - 12,
                        damage,
                        "torpedo",
                        enemy,
                        0,
                        False,
                        0.42,
                    )
                )
            self.announce(
                "LEVIATÃ: jato de pressão concentrado na faixa de água.",
                2.0,
                (95, 195, 239),
            )

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
        if (
            enemy.visual_animation is not None
            and "skill" in enemy.visual_animation.animations
        ):
            # Bala, ácido, rede e demais efeitos consultam exatamente o quadro
            # de habilidade que começou agora, nunca a pose de caminhada.
            enemy.visual_animation.play("skill", restart=True)
        self.app.audio.play("ability", min_interval_ms=140)
        # No Difícil os poderes inimigos retornam um pouco antes. No Fácil o
        # multiplicador é 1, portanto o equilíbrio aprovado não se altera.
        enemy.skill_timer = random.uniform(3.4, 5.8) * float(
            self.difficulty_data["skill_cooldown"]
        )
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
                if (
                    defender.row == enemy.row
                    and 0 < enemy.x - defender.x < CELL_W * 2.7
                ):
                    defender.attack_timer = max(defender.attack_timer, 0.72)
        if "dash" in enemy.tags:
            # O Surfista acelera por uma janela visível; a posição continua
            # avançando quadro a quadro e passa pela colisão varrida normal.
            enemy.rage = max(enemy.rage, 1.15)
            effect_x, effect_y = self.enemy_effect_origin(enemy, "water_splash")
            self.effects.append(
                VisualEffect(
                    "water_splash",
                    effect_x,
                    effect_y,
                    (84, 196, 203),
                    skill_duration,
                    scale=0.62,
                    owner=enemy,
                    anchor_kind="water_splash",
                )
            )
        if "naval_hunter" in enemy.tags:
            enemy.rage = max(enemy.rage, 0.86)
            effect_x, effect_y = self.enemy_effect_origin(enemy, "water_splash")
            self.effects.append(
                VisualEffect(
                    "water_splash",
                    effect_x,
                    effect_y,
                    (84, 196, 203),
                    skill_duration,
                    scale=0.55,
                    owner=enemy,
                    anchor_kind="water_splash",
                )
            )
        if "gun" in enemy.tags:
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4
            ]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                damage = self.scaled_enemy_damage(enemy, 20 + self.wave * 1.3)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "enemy_bullet")
                self.projectiles.append(
                    Projectile(
                        origin_x,
                        origin_y,
                        victim,
                        victim.x,
                        victim.y - 20,
                        damage,
                        "enemy_bullet",
                        enemy,
                        0,
                        False,
                        0.30,
                    )
                )
        if "acid" in enemy.tags:
            targets = [
                d
                for d in self.defenders
                if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 3.2
            ]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                damage = self.scaled_enemy_damage(enemy, 16 + self.wave)
                origin_x, origin_y = self.enemy_projectile_origin(enemy, "acid")
                self.projectiles.append(
                    Projectile(
                        origin_x,
                        origin_y,
                        victim,
                        victim.x,
                        victim.y - 18,
                        damage,
                        "acid",
                        enemy,
                        CELL_W * 0.34,
                        False,
                        0.48,
                        effect="acid",
                    )
                )
        if "shock" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "signal_pulse")
            self.effects.append(
                VisualEffect(
                    "signal_pulse",
                    effect_x,
                    effect_y,
                    TEAL,
                    skill_duration,
                    scale=0.76,
                    owner=enemy,
                    anchor_kind="signal_pulse",
                )
            )
            targets = [
                defender
                for defender in self.defenders
                if defender.row == enemy.row
                and defender.x < enemy.x
                and enemy.x - defender.x < CELL_W * 2.4
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                victim.stun = max(victim.stun, 0.72)
                victim.attack_timer = max(victim.attack_timer, 0.72)
                self.effects.append(
                    VisualEffect(
                        "electric_arc", victim.x, victim.y, TEAL, 0.42, scale=0.62
                    )
                )
                self.announce("Pulso da subestação: recarga atrasada.", 1.2, TEAL)
        if "net" in enemy.tags:
            targets = [
                defender
                for defender in self.defenders
                if defender.row == enemy.row
                and defender.x < enemy.x
                and enemy.x - defender.x < CELL_W * 3.0
            ]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                victim.stun = max(victim.stun, 0.58)
                victim.attack_timer = max(victim.attack_timer, 1.05)
                self.effects.append(
                    VisualEffect(
                        "net_cast",
                        victim.x,
                        victim.y - 30,
                        (84, 196, 203),
                        min(skill_duration, 0.72),
                        scale=0.70,
                    )
                )
                self.announce(
                    "Rede contaminada: cadência reduzida.", 1.2, (84, 196, 203)
                )
        if "scream" in enemy.tags:
            self.effects.append(
                VisualEffect(
                    "command_aura",
                    enemy.x,
                    enemy.y,
                    RED,
                    skill_duration,
                    scale=0.72,
                    owner=enemy,
                    anchor_kind="command_aura",
                )
            )
            for other in self.enemies:
                if other.row == enemy.row and abs(other.x - enemy.x) < CELL_W * 2.6:
                    other.rage = max(other.rage, 3.5)
            if random.random() < 0.36:
                self.enemies.append(
                    Enemy(
                        "caminhante" if self.region != "beach" else "boia",
                        enemy.row,
                        ENEMIES["caminhante" if self.region != "beach" else "boia"],
                        self.region,
                        self.wave,
                        difficulty=self.difficulty,
                        x=BOARD.right + 20,
                    )
                )
            self.announce("Grito: a horda ganhou velocidade.", 1.2, RED)
        if "heal" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "heal_pulse")
            self.effects.append(
                VisualEffect(
                    "heal_pulse",
                    effect_x,
                    effect_y,
                    (154, 239, 134),
                    skill_duration,
                    scale=0.76,
                    owner=enemy,
                    anchor_kind="heal_pulse",
                )
            )
            nearby = [
                other
                for other in self.enemies
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
                    revived = Enemy(
                        key,
                        row,
                        ENEMIES[key],
                        self.region,
                        self.wave,
                        difficulty=self.difficulty,
                        x=x + 42,
                    )
                    revived.hp = revived.max_hp * 0.40
                    self.enemies.append(revived)
                    enemy.revived = True
        if "parasite" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "parasite_burst")
            self.effects.append(
                VisualEffect(
                    "parasite_burst",
                    effect_x,
                    effect_y,
                    (218, 106, 76),
                    skill_duration,
                    scale=0.70,
                    owner=enemy,
                    anchor_kind="parasite_burst",
                )
            )
            for defender in self.defenders:
                if (
                    defender.row == enemy.row
                    and defender.x < enemy.x
                    and enemy.x - defender.x < CELL_W * 2.1
                ):
                    defender.stun = max(defender.stun, 2.6)
            self.announce("Parasita: tiro das tropas foi desabilitado.", 1.4, RED)
        if "stomp" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "ground_slam")
            self.effects.append(
                VisualEffect(
                    "ground_slam",
                    effect_x,
                    effect_y,
                    (223, 132, 73),
                    skill_duration,
                    scale=0.84,
                    owner=enemy,
                    anchor_kind="ground_slam",
                )
            )
            for defender in self.defenders:
                if (
                    defender.row == enemy.row
                    and abs(defender.x - enemy.x) < CELL_W * 1.8
                ):
                    self.damage_defender(
                        defender, self.scaled_enemy_damage(enemy, 24), "stun"
                    )
        if "steal" in enemy.tags:
            effect_x, effect_y = self.enemy_effect_origin(enemy, "supply_snatch")
            self.effects.append(
                VisualEffect(
                    "supply_snatch",
                    effect_x,
                    effect_y,
                    GOLD,
                    skill_duration,
                    scale=0.68,
                    owner=enemy,
                    anchor_kind="supply_snatch",
                )
            )
            stolen = min(18, self.supplies)
            self.supplies -= stolen
            enemy.stolen += stolen
            self.announce(
                "Ladrão de Suprimentos roubou carga — clique nele!", 2.0, GOLD
            )

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
                    if (
                        victim in self.defenders
                        and victim.hp > 0
                        and abs(victim.row - enemy.row) == 0
                    ):
                        # O dano coincide com o contato da mordida/martelo, não
                        # com o primeiro quadro da preparação do ataque.
                        self.app.audio.play("bite", min_interval_ms=110)
                        self.damage_defender(victim, enemy.attack_damage)
                    enemy.attack_damage = 0.0
            # Queimadura e Envenenado causam pulsos legíveis de dano. O dano
            # periódico não renova o próprio estado, portanto ambos acabam no
            # tempo previsto em vez de permanecerem ativos para sempre.
            if enemy.dot_timer <= 0 and (enemy.burn > 0 or enemy.poisoned > 0):
                dot_damage = (3.2 if enemy.burn > 0 else 0.0) + (
                    2.25 if enemy.poisoned > 0 else 0.0
                )
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
                if enemy.motion.state != "hit":
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
                    scale = (
                        boss_damage_scale(self.wave)
                        if enemy.is_boss
                        else enemy_damage_scale(self.wave)
                    )
                    damage = self.scaled_enemy_damage(
                        enemy, float(enemy.data["damage"]) * scale
                    )
                    if not enemy.first_attack_done:
                        damage *= float(enemy.data.get("first_attack_multiplier", 1.0))
                        enemy.first_attack_done = True
                    if "naval_hunter" in enemy.tags and blocker.stats.get("water_only"):
                        # O traje do mergulhador foi criado para enfrentar as
                        # embarcações: a habilidade não afeta tropas em terra.
                        damage *= 1.55
                    if int(blocker.stats.get("combat_class", 0)) in tuple(
                        enemy.data.get("devour_classes", ())
                    ):
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
                    enemy.motion.trigger(
                        "brace", min(0.28, max(0.08, enemy.attack_timer))
                    )
                continue
            next_x = enemy.x - speed * dt
            crossed_blocker = self.swept_blocker_for(enemy, next_x)
            if crossed_blocker is not None:
                enemy.x = (
                    crossed_blocker.x
                    + float(enemy.data.get("contact_distance", 58.0))
                    - 0.25
                )
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
                    self.take_enemy_damage(
                        target,
                        projectile.damage,
                        projectile.effect,
                        (
                            projectile.owner
                            if isinstance(projectile.owner, Defender)
                            else None
                        ),
                    )
                    if projectile.radius > 0:
                        for other in self.enemies[:]:
                            if other is target:
                                continue
                            if (
                                other.row == target.row
                                and abs(other.x - target.x) < projectile.radius
                            ):
                                self.take_enemy_damage(
                                    other,
                                    projectile.damage * 0.72,
                                    projectile.effect,
                                    (
                                        projectile.owner
                                        if isinstance(projectile.owner, Defender)
                                        else None
                                    ),
                                )
                    explosive_kinds = {
                        "grenade",
                        "grenade_40mm",
                        "mortar",
                        "mortar_shell",
                        "bazooka",
                        "rpg7_rocket",
                        "torpedo",
                        "compact_torpedo",
                    }
                    if projectile.kind == "gas_grenade":
                        # A munição não vira um jato. Ela chega em arco, abre
                        # no chão e deixa uma nuvem baixa dentro da própria
                        # faixa, coerente com o equipamento anticontaminação.
                        self.effects.append(
                            VisualEffect(
                                "toxic_wave",
                                projectile.target_x,
                                projectile.target_y - 10,
                                (132, 239, 80),
                                1.05,
                                scale=1.08,
                            )
                        )
                    elif projectile.kind in explosive_kinds:
                        scale = (
                            1.35
                            if projectile.kind in {"bazooka", "rpg7_rocket"}
                            else (
                                1.12
                                if projectile.kind in {"mortar", "mortar_shell"}
                                else 0.96
                            )
                        )
                        self.explosion(
                            projectile.target_x,
                            projectile.target_y,
                            GOLD,
                            16,
                            scale=scale,
                        )
            else:
                target = projectile.target
                if isinstance(target, Defender) and target in self.defenders:
                    self.damage_defender(target, projectile.damage, projectile.effect)
                    if projectile.radius:
                        cross_lanes = (
                            isinstance(projectile.owner, Enemy)
                            and projectile.owner.is_boss
                        )
                        for other in self.defenders[:]:
                            if other is target:
                                continue
                            same_lane = other.row == target.row
                            boss_reach = (
                                cross_lanes and abs(other.y - target.y) < CELL_H * 0.75
                            )
                            if (same_lane or boss_reach) and abs(
                                other.x - target.x
                            ) < projectile.radius:
                                self.damage_defender(
                                    other, projectile.damage * 0.5, projectile.effect
                                )
                    if projectile.kind == "acid":
                        self.effects.append(
                            VisualEffect(
                                "toxic_impact",
                                projectile.target_x,
                                projectile.target_y,
                                (132, 239, 80),
                                0.30,
                                scale=0.78,
                            )
                        )
                    elif projectile.kind == "torpedo":
                        self.effects.append(
                            VisualEffect(
                                "water_impact",
                                projectile.target_x,
                                projectile.target_y,
                                (102, 224, 244),
                                0.32,
                                scale=0.92,
                            )
                        )
                    else:
                        # Tiros inimigos recebem um impacto curto de munição;
                        # não fabricam uma explosão de granada a cada acerto.
                        self.effects.append(
                            VisualEffect(
                                "ballistic_impact",
                                projectile.target_x,
                                projectile.target_y,
                                (241, 198, 122),
                                0.18,
                                scale=0.30,
                            )
                        )

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
                        self.announce(
                            f"ALERTA: {self.boss_banner_name} chegando!", 3.0, RED
                        )
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
            reward = int(
                round(reward_base * float(self.difficulty_data["supply_gain"]))
            )
            if self.wave % 4 == 0:
                reward += int(round(14 * float(self.difficulty_data["supply_gain"])))
            self.supplies = min(
                int(self.difficulty_data["supply_cap"]), self.supplies + reward
            )
            self.announce(
                f"Onda {self.wave} concluída: +{reward} suprimentos.", 2.4, GOLD
            )

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
            self.announce(
                "Partida pausada." if self.paused else "Partida retomada.", 1.5, GOLD
            )
            return
        if self.paused:
            return
        if self.difficulty != "easy" and self.remove_rect().collidepoint(pos):
            self.remove_mode = not self.remove_mode
            self.announce(
                (
                    "Voltar à base: clique na tropa que deseja recolher."
                    if self.remove_mode
                    else "Retorno à base desativado."
                ),
                1.8,
                TEAL,
            )
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
        return [
            pygame.Rect(10 + index * width, 8, width - 5, 102) for index in range(count)
        ]
