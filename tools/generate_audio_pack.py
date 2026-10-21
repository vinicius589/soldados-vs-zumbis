"""Gera o pacote sonoro original da Beta 4 sem amostras de terceiros.

Os efeitos priorizam transientes, ruído filtrado e camadas graves. Isso evita
os bipes senoidais que soavam como um jogo de plataforma e produz sinais
físicos coerentes com armas, metal, água, vento e criaturas infectadas.
"""

from __future__ import annotations

import math
import random
import wave
from pathlib import Path


RATE = 44_100
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio_beta4"


def blank(seconds: float) -> list[float]:
    return [0.0] * max(1, round(seconds * RATE))


def envelope(length: int, attack: float = 0.005, release: float = 0.12) -> list[float]:
    attack_samples = max(1, round(attack * RATE))
    release_samples = max(1, round(release * RATE))
    values: list[float] = []
    for index in range(length):
        up = min(1.0, index / attack_samples)
        down = min(1.0, (length - 1 - index) / release_samples)
        values.append(max(0.0, min(up, down)) ** 1.35)
    return values


def tone(seconds: float, start_hz: float, end_hz: float | None = None, *,
         volume: float = 1.0, attack: float = 0.005, release: float = 0.12,
         harmonics: tuple[tuple[float, float], ...] = ()) -> list[float]:
    end_hz = start_hz if end_hz is None else end_hz
    result = blank(seconds)
    env = envelope(len(result), attack, release)
    phase = 0.0
    harmonic_phases = [0.0 for _ in harmonics]
    for index in range(len(result)):
        progress = index / max(1, len(result) - 1)
        frequency = start_hz + (end_hz - start_hz) * progress
        phase += math.tau * frequency / RATE
        value = math.sin(phase)
        for h_index, (ratio, strength) in enumerate(harmonics):
            harmonic_phases[h_index] += math.tau * frequency * ratio / RATE
            value += math.sin(harmonic_phases[h_index]) * strength
        result[index] = value * env[index] * volume
    return result


def noise(seconds: float, *, volume: float = 1.0, seed: int = 1,
          smoothing: float = 0.0, attack: float = 0.002,
          release: float = 0.16) -> list[float]:
    rng = random.Random(seed)
    result = blank(seconds)
    env = envelope(len(result), attack, release)
    previous = 0.0
    smoothing = max(0.0, min(0.9995, smoothing))
    for index in range(len(result)):
        current = rng.uniform(-1.0, 1.0)
        previous = previous * smoothing + current * (1.0 - smoothing)
        result[index] = previous * env[index] * volume
    return result


def pulse_train(seconds: float, period: float, width: float, *, seed: int,
                volume: float, smoothing: float = 0.72) -> list[float]:
    rng = random.Random(seed)
    result = blank(seconds)
    state = 0.0
    for index in range(len(result)):
        position = (index / RATE) % period
        if position < width:
            state = state * smoothing + rng.uniform(-1.0, 1.0) * (1.0 - smoothing)
            shape = math.sin(math.pi * position / max(width, 1e-4)) ** 2
            result[index] = state * shape * volume
    return result


def place(track: list[float], clip: list[float], start: float, gain: float = 1.0) -> None:
    offset = round(start * RATE)
    for index, value in enumerate(clip):
        target = offset + index
        if 0 <= target < len(track):
            track[target] += value * gain


def mix(seconds: float, layers: list[tuple[list[float], float, float]]) -> list[float]:
    result = blank(seconds)
    for clip, start, gain in layers:
        place(result, clip, start, gain)
    return result


def normalize(samples: list[float], peak: float = 0.92) -> list[float]:
    maximum = max(0.0001, max(abs(value) for value in samples))
    factor = min(1.0, peak / maximum)
    return [max(-1.0, min(1.0, value * factor)) for value in samples]


def write(name: str, samples: list[float], peak: float = 0.92) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pcm = bytearray()
    for value in normalize(samples, peak):
        integer = int(value * 32767)
        pcm.extend(integer.to_bytes(2, "little", signed=True))
    with wave.open(str(OUT / f"{name}.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(bytes(pcm))


def gunshot(kind: str) -> list[float]:
    if kind == "pistol":
        seconds, low, crack, tail = 0.34, 94, 0.24, 0.20
    elif kind == "rifle":
        seconds, low, crack, tail = 0.42, 72, 0.31, 0.27
    else:
        seconds, low, crack, tail = 0.62, 48, 0.43, 0.42
    return mix(seconds, [
        (noise(crack, volume=1.0, seed=31 + len(kind), smoothing=0.12, release=0.11), 0.0, 1.0),
        (tone(seconds, low, low * 0.42, volume=0.9, release=tail,
              harmonics=((0.51, 0.34), (2.03, 0.18))), 0.0, 1.0),
        (noise(seconds, volume=0.34, seed=71, smoothing=0.93, release=tail), 0.015, 1.0),
    ])


def looped_ambience(kind: str, seconds: float = 10.0) -> list[float]:
    result = blank(seconds)
    seed = {"city": 101, "desert": 202, "beach": 303}[kind]
    bed = noise(seconds, volume=0.30, seed=seed, smoothing=0.992,
                attack=0.8, release=0.8)
    place(result, bed, 0)
    if kind == "city":
        place(result, tone(seconds, 43, 47, volume=0.18, attack=1.2, release=1.2,
                           harmonics=((2.0, 0.22),)), 0)
        for time in (2.0, 6.6):
            place(result, mix(0.55, [
                (noise(0.24, volume=0.4, seed=seed + round(time * 10), smoothing=0.75), 0, 1),
                (tone(0.52, 360, 170, volume=0.14, release=0.34), 0.03, 1),
            ]), time)
    elif kind == "desert":
        place(result, noise(seconds, volume=0.34, seed=seed + 1, smoothing=0.965,
                            attack=0.8, release=0.8), 0)
        for time in (1.2, 3.8, 7.1):
            place(result, pulse_train(0.9, 0.13, 0.055, seed=seed + int(time * 10),
                                      volume=0.16, smoothing=0.55), time)
    else:
        place(result, noise(seconds, volume=0.48, seed=seed + 1, smoothing=0.72,
                            attack=0.8, release=0.8), 0)
        place(result, tone(seconds, 58, 55, volume=0.12, attack=1.2, release=1.2,
                           harmonics=((0.5, 0.30),)), 0)
    return result


def main() -> None:
    # Interface e ações mecânicas.
    write("ui_click", mix(0.11, [
        (noise(0.035, volume=0.62, seed=5, smoothing=0.45, release=0.025), 0, 1),
        (tone(0.09, 118, 82, volume=0.35, release=0.07), 0.008, 1),
    ]))
    write("place", mix(0.30, [
        (tone(0.26, 92, 48, volume=0.70, release=0.20), 0, 1),
        (noise(0.09, volume=0.55, seed=8, smoothing=0.50, release=0.07), 0, 1),
        (noise(0.06, volume=0.44, seed=9, smoothing=0.30), 0.12, 1),
    ]))
    write("shot_pistol", gunshot("pistol"))
    write("shot_rifle", gunshot("rifle"))
    write("shot_heavy", gunshot("heavy"))
    write("reload", mix(0.78, [
        (noise(0.055, volume=0.48, seed=11, smoothing=0.28, release=0.04), 0.00, 1),
        (tone(0.12, 310, 128, volume=0.20, release=0.08), 0.01, 1),
        (noise(0.080, volume=0.55, seed=12, smoothing=0.45, release=0.06), 0.34, 1),
        (tone(0.11, 180, 76, volume=0.30, release=0.08), 0.35, 1),
        (noise(0.065, volume=0.62, seed=13, smoothing=0.34, release=0.05), 0.65, 1),
    ]))
    write("explosion", mix(1.10, [
        (noise(0.28, volume=1.0, seed=14, smoothing=0.22, release=0.25), 0, 1),
        (tone(1.08, 63, 24, volume=0.92, release=0.82, harmonics=((0.5, 0.36),)), 0, 1),
        (noise(1.0, volume=0.48, seed=15, smoothing=0.96, release=0.82), 0.08, 1),
    ]))

    # Infectados e combate corporal.
    write("zombie_groan", mix(1.05, [
        (tone(0.98, 92, 61, volume=0.52, attack=0.06, release=0.28,
              harmonics=((0.5, 0.40), (1.52, 0.26), (2.37, 0.14))), 0, 1),
        (noise(0.92, volume=0.20, seed=21, smoothing=0.92, attack=0.05, release=0.3), 0.03, 1),
    ]))
    write("zombie_hit", mix(0.34, [
        (tone(0.31, 134, 72, volume=0.50, release=0.24, harmonics=((0.5, 0.38),)), 0, 1),
        (noise(0.16, volume=0.46, seed=22, smoothing=0.64, release=0.12), 0, 1),
    ]))
    write("soldier_hit", mix(0.30, [
        (tone(0.28, 174, 108, volume=0.40, release=0.18), 0, 1),
        (noise(0.13, volume=0.42, seed=23, smoothing=0.53, release=0.10), 0, 1),
    ]))
    write("bite", mix(0.43, [
        (noise(0.12, volume=0.72, seed=24, smoothing=0.68, release=0.10), 0, 1),
        (tone(0.36, 108, 49, volume=0.46, release=0.28), 0.035, 1),
        (noise(0.10, volume=0.54, seed=25, smoothing=0.42, release=0.08), 0.19, 1),
    ]))
    write("zombie_skill", mix(0.70, [
        (noise(0.62, volume=0.48, seed=26, smoothing=0.93, release=0.40), 0, 1),
        (tone(0.68, 120, 36, volume=0.58, release=0.50,
              harmonics=((0.5, 0.35), (1.7, 0.20))), 0, 1),
    ]))

    # Sinais táticos e cenário.
    write("supply", mix(0.62, [
        (noise(0.19, volume=0.35, seed=41, smoothing=0.18, release=0.14), 0, 1),
        (tone(0.16, 980, 840, volume=0.18, release=0.12), 0.18, 1),
        (noise(0.16, volume=0.32, seed=42, smoothing=0.2, release=0.12), 0.31, 1),
    ]))
    write("wave", mix(1.10, [
        (tone(0.48, 76, 54, volume=0.72, release=0.35, harmonics=((2.0, 0.18),)), 0, 1),
        (tone(0.60, 69, 45, volume=0.67, release=0.44), 0.46, 1),
    ]))
    write("boss", mix(1.85, [
        (tone(1.80, 57, 31, volume=0.78, attack=0.04, release=0.8,
              harmonics=((0.5, 0.46), (1.49, 0.25))), 0, 1),
        (noise(1.45, volume=0.31, seed=43, smoothing=0.985, release=0.8), 0.10, 1),
    ]))
    write("whistle", mix(0.72, [
        (tone(0.68, 2450, 2720, volume=0.32, attack=0.02, release=0.10,
              harmonics=((2.0, 0.20),)), 0, 1),
        (noise(0.68, volume=0.08, seed=44, smoothing=0.82, attack=0.02, release=0.1), 0, 1),
    ]))
    write("alarm_scream", mix(0.88, [
        (tone(0.82, 420, 315, volume=0.42, attack=0.04, release=0.18,
              harmonics=((2.02, 0.28), (3.05, 0.12))), 0, 1),
        (noise(0.70, volume=0.10, seed=45, smoothing=0.93, attack=0.04, release=0.18), 0.02, 1),
    ]))
    write("thunder", mix(1.65, [
        (noise(0.20, volume=0.68, seed=46, smoothing=0.32, release=0.16), 0, 1),
        (tone(1.62, 51, 25, volume=0.72, release=1.20,
              harmonics=((0.5, 0.40),)), 0.02, 1),
        (noise(1.55, volume=0.29, seed=47, smoothing=0.987, release=1.15), 0.04, 1),
    ]))

    # Trilha original sombria, baseada em pulso marcial grave e textura; não
    # usa melodias agudas nem arpejos de plataforma.
    music = blank(16.0)
    for start, root in ((0, 48), (4, 43), (8, 40), (12, 45)):
        place(music, tone(4.2, root, root, volume=0.18, attack=0.55, release=0.65,
                          harmonics=((1.5, 0.24), (2.0, 0.14))), start)
    for beat in [index * 0.8 for index in range(20)]:
        place(music, tone(0.26, 71, 38, volume=0.24, release=0.22), beat)
        if int(beat * 10) % 16 == 8:
            place(music, noise(0.10, volume=0.16, seed=100 + int(beat * 10),
                               smoothing=0.55, release=0.08), beat)
    place(music, noise(16.0, volume=0.08, seed=99, smoothing=0.996,
                       attack=0.8, release=0.8), 0)
    write("music_menu", music, peak=0.82)
    write("ambience_city", looped_ambience("city"), peak=0.72)
    write("ambience_desert", looped_ambience("desert"), peak=0.72)
    write("ambience_beach", looped_ambience("beach"), peak=0.72)


if __name__ == "__main__":
    main()
