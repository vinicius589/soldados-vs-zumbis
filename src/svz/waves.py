"""Composição e progressão das ondas."""
from __future__ import annotations

import random

from .config import (
    BOARD,
    ENEMY_ENTRY_REVEAL_SECONDS,
    ENEMY_ENTRY_X,
    GOLD,
    RED,
    ROWS,
    TOTAL_WAVES,
    WHITE,
)
from .content import (
    BEACH_WATER_ENEMIES,
    BOSSES,
    ENEMIES,
    ENEMY_ACTOR_BY_KEY,
    REGION_BOSSES,
    REGION_SUBBOSSES,
    wave_enemy_pool,
)
from .entities import (
    Enemy,
    SpawnOrder,
)


class WaveDirector:
    """Diretor de ondas composto pela partida, com estado explícito no proprietário."""

    def __init__(self, owner: "Battle") -> None:
        self.owner = owner

    def start_next_wave(self) -> None:
        if self.owner.wave >= TOTAL_WAVES:
            return
        self.owner.wave += 1
        self.owner.app.audio.play("wave", min_interval_ms=500)
        self.owner.started_wave = True
        self.owner.wave_banner = 3.0
        self.owner.orders = self.build_wave(self.owner.wave)
        self.owner.spawn_timer = 0.35
        self.owner.intermission = 0.0
        slot = (self.owner.wave - 1) % 4 + 1
        chapter = (self.owner.wave - 1) // 4
        if slot == 4:
            boss_key = REGION_BOSSES[self.owner.region][chapter]
            self.owner.boss_banner_name = BOSSES[boss_key]["name"]
            self.owner.boss_banner_subtitle = "A ESCOLTA ABRE CAMINHO"
            self.owner.announce(f"Onda {self.owner.wave}: a escolta do chefe está a caminho.", 2.6, RED)
        elif slot == 3:
            subboss_key = REGION_SUBBOSSES[self.owner.region][chapter]
            self.owner.announce(f"Onda {self.owner.wave}: SUB-BOSS {ENEMIES[subboss_key]['name']}.", 2.4, GOLD)
        else:
            self.owner.announce(f"ONDA COMUM {self.owner.wave}/{TOTAL_WAVES}", 2.0, WHITE)

    def build_wave(self, wave: int) -> list[SpawnOrder]:
        if getattr(self.owner.app, "integration_preview", False):
            # O ensaio usa a mesma liberação progressiva da campanha. Assim a
            # revisão visual da onda 1 não apresenta antes da hora um inimigo
            # que o jogador só conhecerá nos atos seguintes.
            count = min(8, 2 + wave)
            enemy_keys = wave_enemy_pool(self.owner.region, wave)
            return [
                SpawnOrder(
                    0.78 if index else 0.35,
                    enemy_keys[index % len(enemy_keys)],
                    self.spawn_row_for(enemy_keys[index % len(enemy_keys)]),
                )
                for index in range(count)
            ]
        pool = list(wave_enemy_pool(self.owner.region, wave))
        orders: list[SpawnOrder] = []
        slot = (wave - 1) % 4 + 1
        chapter = (wave - 1) // 4
        # A curva começa com espaço para aprender e termina em pressão real.
        # Subchefes e chefes ocupam o lugar de parte da massa, em vez de serem
        # simplesmente empilhados sobre uma horda já cheia.
        base_count_by_wave = (2, 3, 2, 2, 4, 5, 4, 4, 7, 8, 7, 8)
        base_count = base_count_by_wave[max(0, min(TOTAL_WAVES - 1, wave - 1))]
        count = max(2, int(round(base_count * float(self.owner.difficulty_data["spawn_count"]))))
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
            ) * float(self.owner.difficulty_data["spawn_wait"])
            orders.append(SpawnOrder(wait, key, self.spawn_row_for(key)))
        if slot == 3:
            subboss_key = REGION_SUBBOSSES[self.owner.region][chapter]
            orders.append(SpawnOrder(0.85, subboss_key, self.spawn_row_for(subboss_key)))
        elif slot == 4:
            boss_key = REGION_BOSSES[self.owner.region][chapter]
            escort_count = max(1, int(round((1 + chapter) * float(self.owner.difficulty_data["escort_count"]))))
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
        if self.owner.region != "beach":
            return random.randrange(ROWS)
        if boss or enemy_key in BEACH_WATER_ENEMIES or ENEMIES.get(enemy_key, {}).get("amphibious"):
            return random.choice(tuple(self.owner.water_rows))
        land_rows = tuple(row for row in range(ROWS) if row not in self.owner.water_rows)
        return random.choice(land_rows)

    def spawn_enemy(self, order: SpawnOrder) -> None:
        data = BOSSES.get(order.key) or ENEMIES[order.key]
        enemy = Enemy(order.key, order.row, data, self.owner.region, self.owner.wave, difficulty=self.owner.difficulty)
        actor_key = ENEMY_ACTOR_BY_KEY.get(order.key)
        if actor_key:
            enemy.visual_animation = self.owner.app.assets.new_production_animation(actor_key)
        enemy.x = ENEMY_ENTRY_X[self.owner.region]
        enemy.entry_reveal = ENEMY_ENTRY_REVEAL_SECONDS
        if order.boss:
            self.owner.app.audio.play("boss", min_interval_ms=1200)
            enemy.x = BOARD.right + 110
            enemy.boss_announced = True
            self.owner.shake = 0.38
        self.owner.enemies.append(enemy)
        if not order.boss:
            self.owner.app.audio.play("zombie_groan", min_interval_ms=1750)
        if order.boss:
            self.owner.boss_banner_name = str(data["name"])
            self.owner.boss_banner_subtitle = "ENTRADA ESPECIAL ATIVADA"
            self.owner.boss_entrance(enemy)

    def update_wave(self, dt: float) -> None:
        if self.owner.finished:
            return
        if not self.owner.started_wave:
            self.owner.intermission -= dt
            if self.owner.intermission <= 0:
                self.start_next_wave()
            return
        if self.owner.orders:
            self.owner.spawn_timer -= dt
            if self.owner.spawn_timer <= 0:
                # O alerta grande pertence à chegada do chefe, e não ao início
                # genérico da onda. Enquanto ele está visível, a ordem fica
                # segurada; terminado o aviso, o chefe entra de fato.
                next_order = self.owner.orders[0]
                if next_order.boss:
                    if not self.owner.boss_alert_pending:
                        boss_data = BOSSES[next_order.key]
                        self.owner.boss_alert_pending = True
                        self.owner.boss_warning = 3.0
                        self.owner.boss_banner_name = str(boss_data["name"])
                        self.owner.boss_banner_subtitle = "CHEFE E ESCOLTA EM APROXIMAÇÃO"
                        self.owner.announce(f"ALERTA: {self.owner.boss_banner_name} chegando!", 3.0, RED)
                        return
                    if self.owner.boss_warning > 0:
                        return
                    self.owner.boss_alert_pending = False
                order = self.owner.orders.pop(0)
                self.spawn_enemy(order)
                self.owner.spawn_timer = order.wait
        elif not self.owner.enemies:
            if self.owner.wave >= TOTAL_WAVES:
                self.owner.finished = True
                self.owner.victory = True
                self.owner.announce("REGIÃO PROTEGIDA!", 10, GOLD)
                return
            self.owner.started_wave = False
            self.owner.intermission = 5.0
            # Mais ajuda nas primeiras ondas e recompensa praticamente plana
            # no final: o jogo deixa de ser cruel no começo e deixa de inundar
            # o jogador de recursos quando a composição já está pronta.
            reward_base = max(16, 27 - self.owner.wave)
            reward = int(round(reward_base * float(self.owner.difficulty_data["supply_gain"])))
            if self.owner.wave % 4 == 0:
                reward += int(round(14 * float(self.owner.difficulty_data["supply_gain"])))
            self.owner.supplies = min(int(self.owner.difficulty_data["supply_cap"]), self.owner.supplies + reward)
            self.owner.announce(f"Onda {self.owner.wave} concluída: +{reward} suprimentos.", 2.4, GOLD)
