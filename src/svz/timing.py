"""Passos fixos com recuperação limitada para não bloquear a interface."""
import math


class FixedStepper:
    def __init__(self, step=1 / 60, max_steps=15):
        if not math.isfinite(step) or step <= 0:
            raise ValueError("O passo deve ser finito e positivo.")
        if type(max_steps) is not int or max_steps <= 0:
            raise ValueError("O limite de passos deve ser inteiro e positivo.")
        if not math.isfinite(step * max_steps):
            raise ValueError("A janela de recuperação deve ser finita.")
        self.step = step
        self.max_steps = max_steps
        self.remainder = 0.0
        self.dropped_seconds = 0.0

    def advance(self, seconds, update):
        if not math.isfinite(seconds):
            raise ValueError("O tempo decorrido deve ser finito.")
        accepted = min(max(0.0, seconds), self.step * self.max_steps)
        self.dropped_seconds += max(0., seconds - accepted)
        self.remainder += accepted
        count = 0
        while self.remainder + 1e-10 >= self.step and count < self.max_steps:
            update(self.step)
            self.remainder = max(0., self.remainder - self.step)
            count += 1
        return count

