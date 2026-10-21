"""Dano, ataques, suporte e recarga das tropas.

O mixin executa ações de combate usando o estado da partida proprietária,
mantendo a lógica de dano e as regras de arma longe do ciclo de atualização.
"""
from __future__ import annotations

import random

from .actor_visuals import defender_weapon_origin, enemy_render_scale
from .config import BOARD, CELL_W, GOLD, GRAY, HEIGHT, RED, TEAL, WHITE, WIDTH
from .content import weapon_reload_seconds
from .entities import Defender, Enemy, FloatingText, Projectile
from .math_utils import clamp
from .motion import DefeatAnimation, VisualEffect
from .scoring import points_for
from .visual_layout import DEFENDER_WEAPON_PROFILES


class CombatActionsMixin:
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
        self.score += points_for(self.region, enemy.key)
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
        if defender.max_ammo > 0 and defender.tactical_ammo_timer <= 0:
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
