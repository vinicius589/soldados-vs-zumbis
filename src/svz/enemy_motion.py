"""Movimento especial e colisões das unidades inimigas.

As regras usam o estado e os serviços fornecidos pela partida, mas não dependem
da classe Battle. Isso mantém salto, escavação e colisão varrida isolados sem
duplicar relógios ou listas de entidades.
"""
from __future__ import annotations

from .config import BOARD, CELL_W, GOLD, RED
from .entities import Defender, Enemy
from .math_utils import clamp, lerp


class EnemyMotionMixin:
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

