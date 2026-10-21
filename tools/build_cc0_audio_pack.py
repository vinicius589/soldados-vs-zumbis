"""Monta o pacote sonoro a partir de gravações CC0 verificáveis.

Não sintetiza disparos ou vozes. O tratamento limita-se a recortar silêncio,
converter para o formato usado pelo Pygame, controlar pico e montar camadas
curtas (mordida = voz + crocância + impacto úmido).
"""

from __future__ import annotations

import os
from pathlib import Path
import wave

import numpy as np

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame


RATE = 44_100
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "audio_sources_cc0"
OUT = ROOT / "assets" / "audio_beta4"


def _decode_pcm(raw: bytes, width: int) -> np.ndarray:
    if width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if width == 3:
        triplets = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        values = (
            triplets[:, 0].astype(np.int32)
            | (triplets[:, 1].astype(np.int32) << 8)
            | (triplets[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values - 0x1000000, values)
        return values.astype(np.float32) / 8_388_608.0
    raise ValueError(f"largura PCM não suportada: {width}")


def _resample(samples: np.ndarray, source_rate: int) -> np.ndarray:
    if source_rate == RATE or samples.size == 0:
        return samples.astype(np.float32, copy=False)
    length = max(1, round(samples.size * RATE / source_rate))
    old = np.linspace(0.0, 1.0, samples.size, endpoint=False)
    new = np.linspace(0.0, 1.0, length, endpoint=False)
    return np.interp(new, old, samples).astype(np.float32)


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        width = source.getsampwidth()
        rate = source.getframerate()
        decoded = _decode_pcm(source.readframes(source.getnframes()), width)
    if channels > 1:
        decoded = decoded.reshape(-1, channels).mean(axis=1)
    return _resample(decoded, rate)


def load_compressed(path: Path) -> np.ndarray:
    sound = pygame.mixer.Sound(str(path))
    decoded = pygame.sndarray.array(sound).astype(np.float32)
    if decoded.ndim > 1:
        decoded = decoded.mean(axis=1)
    return decoded / 32768.0


def load(path: Path) -> np.ndarray:
    return load_wav(path) if path.suffix.lower() == ".wav" else load_compressed(path)


def normalize(samples: np.ndarray, peak: float = 0.9) -> np.ndarray:
    samples = samples.astype(np.float32, copy=True)
    maximum = float(np.max(np.abs(samples))) if samples.size else 0.0
    if maximum > 0:
        samples *= peak / maximum
    return np.clip(samples, -1.0, 1.0)


def trim(samples: np.ndarray, threshold: float = 0.006, margin: float = 0.025) -> np.ndarray:
    active = np.flatnonzero(np.abs(samples) >= threshold)
    if active.size == 0:
        return samples
    pad = round(margin * RATE)
    return samples[max(0, int(active[0]) - pad) : min(samples.size, int(active[-1]) + pad + 1)]


def fade(samples: np.ndarray, attack: float = 0.003, release: float = 0.08) -> np.ndarray:
    result = samples.astype(np.float32, copy=True)
    attack_n = min(result.size, round(attack * RATE))
    release_n = min(result.size, round(release * RATE))
    if attack_n:
        result[:attack_n] *= np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if release_n:
        result[-release_n:] *= np.linspace(1.0, 0.0, release_n, dtype=np.float32)
    return result


def around_loudest(samples: np.ndarray, before: float, after: float) -> np.ndarray:
    peak = int(np.argmax(np.abs(samples)))
    start = max(0, peak - round(before * RATE))
    end = min(samples.size, peak + round(after * RATE))
    return samples[start:end]


def segment(samples: np.ndarray, start: float, seconds: float) -> np.ndarray:
    left = max(0, round(start * RATE))
    right = min(samples.size, left + round(seconds * RATE))
    return samples[left:right]


def mix(length_seconds: float, layers: list[tuple[np.ndarray, float, float]]) -> np.ndarray:
    output = np.zeros(round(length_seconds * RATE), dtype=np.float32)
    for clip, start_seconds, gain in layers:
        start = round(start_seconds * RATE)
        available = min(clip.size, output.size - start)
        if available > 0:
            output[start : start + available] += clip[:available] * gain
    return output


def write(name: str, samples: np.ndarray, peak: float = 0.9) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pcm = (normalize(samples, peak) * 32767.0).astype("<i2")
    with wave.open(str(OUT / name), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(pcm.tobytes())


def main() -> None:
    pygame.mixer.pre_init(RATE, -16, 2, 512)
    pygame.mixer.init()

    guns = SOURCE / "gunshots_tabasco" / "sounds"
    pistol = fade(around_loudest(load_wav(guns / "cz.wav"), 0.018, 0.58), release=0.16)
    rifle = fade(around_loudest(load_wav(guns / "sks.wav"), 0.018, 0.72), release=0.20)
    heavy = fade(around_loudest(load_wav(guns / "shotty.wav"), 0.018, 0.68), release=0.22)
    write("shot_pistol.wav", pistol, 0.88)
    write("shot_rifle.wav", rifle, 0.94)
    write("shot_heavy.wav", heavy, 0.96)

    reload_clip = fade(
        trim(load_wav(SOURCE / "assaultriflereload1_springyspringo_cc0.wav"), 0.003),
        attack=0.002,
        release=0.035,
    )
    write("reload.wav", reload_clip, 0.82)
    switch_path = next((SOURCE / "sfx_100_v2_cc0").rglob("sfx100v2_switch_01.ogg"))
    ui_click = fade(trim(load_compressed(switch_path), 0.003), release=0.055)
    # Clique seco de chave mecânica: comunica confirmação sem lembrar moedas,
    # plataforma ou o antigo bipe de videogame.
    write("ui_click.wav", ui_click[: round(0.42 * RATE)], 0.68)
    equipment = trim(load_wav(SOURCE / "equipment_clicks_lfa_cc0.wav"), 0.004)
    write("place.wav", fade(segment(equipment, 0.0, 0.46), release=0.07), 0.72)

    zombies = SOURCE / "zombies_artisticdude" / "zombies"
    groan = fade(trim(load_wav(zombies / "zombie-17.wav"), 0.004), attack=0.01, release=0.10)
    hit = fade(trim(load_wav(zombies / "zombie-11.wav"), 0.004), attack=0.005, release=0.08)
    skill = fade(trim(load_wav(zombies / "zombie-16.wav"), 0.004), attack=0.01, release=0.12)
    bite_voice = fade(trim(load_wav(zombies / "zombie-24.wav"), 0.004), release=0.07)
    crunch = fade(trim(load_compressed(SOURCE / "crunchybite_fvcalderan_cc0.ogg"), 0.004), release=0.05)
    squish = fade(trim(load_compressed(SOURCE / "squishsplat_ezduzziteh_cc0.mp3"), 0.004), release=0.05)
    bite = mix(0.78, [(bite_voice, 0.0, 0.60), (crunch, 0.09, 0.92), (squish, 0.22, 0.58)])
    write("zombie_groan.wav", groan, 0.78)
    write("zombie_hit.wav", hit, 0.76)
    write("zombie_skill.wav", skill, 0.84)
    write("bite.wav", bite, 0.86)

    # Sinais de onda e chefe também partem de vozes reais do mesmo pacote,
    # evitando os bipes/sintetizadores que destoavam da cena.
    wave_voice_a = fade(trim(load_wav(zombies / "zombie-1.wav"), 0.004), release=0.16)
    wave_voice_b = fade(trim(load_wav(zombies / "zombie-7.wav"), 0.004), release=0.18)
    wave = mix(2.25, [(wave_voice_a, 0.0, 0.78), (wave_voice_b, 0.38, 0.62)])
    write("wave.wav", wave, 0.78)

    thunder_path = next((SOURCE / "sfx_100_v2_cc0").rglob("sfx100v2_thunder_01.ogg"))
    thunder = fade(trim(load_compressed(thunder_path), 0.002), attack=0.002, release=0.35)
    write("thunder.wav", thunder, 0.88)
    boss_voice = fade(trim(load_wav(zombies / "zombie-22.wav"), 0.004), release=0.24)
    boss = mix(2.85, [(boss_voice, 0.0, 0.86), (thunder, 0.24, 0.38)])
    write("boss.wav", boss, 0.90)

    soldier_hit = fade(trim(load_wav(SOURCE / "player_hit.wav"), 0.004), release=0.08)
    write("soldier_hit.wav", soldier_hit, 0.70)
    explosion_source = load_wav(SOURCE / "dull_explosion.wav")
    explosion = fade(around_loudest(explosion_source, 0.06, 1.45), release=0.30)
    write("explosion.wav", explosion, 0.94)

    radio = load_compressed(SOURCE / "radio_static_xhunterko_cc0.mp3")
    write("supply.wav", fade(segment(radio, 1.1, 0.68), release=0.10), 0.56)
    scream = fade(trim(load_compressed(SOURCE / "female_scream_aura_cc0.ogg"), 0.004), release=0.10)
    write("alarm_scream.wav", scream, 0.78)
    whistle = fade(trim(load_wav(SOURCE / "referee_whistle_sfxmint_cc0.wav"), 0.004), release=0.10)
    write("whistle.wav", whistle, 0.72)

    # Abertura mais marcada: trilha retro de ação feita para invasão
    # zumbi/alienígena. Mantém bateria e pulso de combate sem virar um jingle.
    menu = load_compressed(SOURCE / "biohazardsopening_centurion_cc0.ogg")
    write("music_menu.wav", fade(segment(menu, 0.0, 32.0), attack=0.12, release=0.75), 0.76)
    city = load_compressed(SOURCE / "city_ambience_tinyworlds_cc0.mp3")
    desert = load_compressed(SOURCE / "desert_wind_aquinn_cc0.mp3")
    river = load_compressed(SOURCE / "river_waves_randommind_cc0.mp3")
    write("ambience_city.wav", fade(segment(city, 1.0, 14.0), attack=0.2, release=0.4), 0.50)
    write("ambience_desert.wav", fade(segment(desert, 2.0, 14.0), attack=0.2, release=0.4), 0.48)
    write("ambience_beach.wav", fade(segment(river, 4.0, 14.0), attack=0.2, release=0.4), 0.54)

    pygame.mixer.quit()
    print("PACOTE_CC0_RECONSTRUIDO")


if __name__ == "__main__":
    main()
