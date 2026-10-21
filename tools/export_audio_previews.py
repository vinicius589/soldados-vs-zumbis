"""Monta prévias auditáveis do pacote sonoro sem alterar os sons do jogo."""

from __future__ import annotations

from array import array
from pathlib import Path
import wave


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "audio_beta4"
OUTPUT = ROOT / "visual_qa_beta4" / "audio"
RATE = 44_100


def read(name: str, seconds: float | None = None) -> array:
    with wave.open(str(SOURCE / name), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, RATE):
            raise ValueError(f"formato inesperado em {name}")
        count = source.getnframes()
        if seconds is not None:
            count = min(count, round(seconds * RATE))
        samples = array("h")
        samples.frombytes(source.readframes(count))
        return samples


def silence(seconds: float = 0.42) -> array:
    return array("h", [0]) * round(seconds * RATE)


def sequence(*parts: array) -> array:
    result = array("h")
    for part in parts:
        result.extend(part)
    return result


def write(name: str, samples: array) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT / name), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(samples.tobytes())


def main() -> None:
    gap = silence()
    write(
        "01_interface_e_musica.wav",
        sequence(
            read("music_menu.wav", 6.0), gap,
            read("ui_click.wav"), gap,
            read("place.wav"), gap,
            read("supply.wav"), gap,
            read("wave.wav"), gap,
            read("boss.wav"),
        ),
    )
    write(
        "02_armas_e_recarga.wav",
        sequence(
            read("shot_pistol.wav"), gap,
            read("shot_rifle.wav"), gap,
            read("shot_heavy.wav"), gap,
            read("reload.wav"), gap,
            read("soldier_hit.wav"), gap,
            read("explosion.wav"),
        ),
    )
    write(
        "03_zumbis.wav",
        sequence(
            read("zombie_groan.wav"), gap,
            read("bite.wav"), gap,
            read("zombie_hit.wav"), gap,
            read("zombie_skill.wav"),
        ),
    )
    write(
        "04_cenarios.wav",
        sequence(
            read("ambience_city.wav", 4.0), gap,
            read("whistle.wav"), gap,
            read("ambience_desert.wav", 4.0), gap,
            read("ambience_beach.wav", 4.0), gap,
            read("alarm_scream.wav"), gap,
            read("thunder.wav"),
        ),
    )
    print(f"PREVIAS_DE_AUDIO: {OUTPUT}")


if __name__ == "__main__":
    main()
