"""Gera provas visuais isoladas das animações realmente usadas na Beta 4."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from beta4_production_animations import build_production_clips


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "visual_qa_beta4" / "animacoes_corrigidas"
REGIONS = {
    "city": ("NOVA YORK", "city_guard", "city_auto", "city_zombie_v2", "city_runner_v2", "city_crawler_v2"),
    "desert": ("EGITO", "desert_guard", "desert_auto", "desert_zombie_v2", "desert_runner_v2", "desert_crawler_v2"),
    "beach": ("MINAS GERAIS", "beach_guard", "beach_auto", "beach_zombie_v2", "beach_runner_v2", "beach_crawler_v2"),
}


def _blit_grounded(canvas: pygame.Surface, sprite: pygame.Surface, center_x: int, ground_y: int) -> None:
    bounds = sprite.get_bounding_rect(min_alpha=8)
    if bounds.width <= 0:
        return
    cropped = sprite.subsurface(bounds).copy()
    factor = min(1.0, 142 / max(1, cropped.get_height()))
    scaled = pygame.transform.smoothscale(
        cropped,
        (max(1, round(cropped.get_width() * factor)), max(1, round(cropped.get_height() * factor))),
    )
    canvas.blit(scaled, scaled.get_rect(midbottom=(center_x, ground_y)))


def _save_gif(frames: list[pygame.Surface], path: Path) -> None:
    images = [
        Image.frombytes("RGB", frame.get_size(), pygame.image.tobytes(frame, "RGB"))
        for frame in frames
    ]
    # Cada quadro substitui integralmente o anterior. Sem ``disposal=2`` o
    # visualizador pode preservar pixels do quadro velho e fabricar o falso
    # "avanço de frame" que não existe na Surface usada pelo jogo.
    images[0].save(
        path,
        save_all=True,
        append_images=images[1:],
        duration=105,
        loop=0,
        optimize=False,
        disposal=2,
    )


def _panel(title: str) -> pygame.Surface:
    canvas = pygame.Surface((960, 720))
    canvas.fill((12, 18, 24))
    pygame.draw.rect(canvas, (27, 39, 48), (18, 18, 924, 684), border_radius=12)
    font = pygame.font.Font(None, 31)
    canvas.blit(font.render(title, True, (244, 207, 103)), (34, 29))
    return canvas


def _label(canvas: pygame.Surface, text: str, x: int, y: int) -> None:
    font = pygame.font.Font(None, 22)
    label = font.render(text, True, (224, 232, 235))
    canvas.blit(label, label.get_rect(center=(x, y)))


def _contact_sheet(
    clips: dict,
    title: str,
    actors: tuple[tuple[str, str], ...],
    states: tuple[tuple[str, str], ...],
) -> pygame.Surface:
    """Mostra cada quadro real; nenhum vazamento pode se esconder no GIF."""
    cell_w, row_h, label_w = 138, 112, 190
    rows = len(actors) * len(states)
    canvas = pygame.Surface((label_w + cell_w * 8 + 24, 64 + rows * row_h))
    canvas.fill((12, 18, 24))
    title_font = pygame.font.Font(None, 30)
    label_font = pygame.font.Font(None, 20)
    canvas.blit(title_font.render(title, True, (244, 207, 103)), (18, 18))
    row_index = 0
    for actor, actor_label in actors:
        for state, state_label in states:
            top = 58 + row_index * row_h
            ground = top + 82
            canvas.blit(
                label_font.render(f"{actor_label} • {state_label}", True, (224, 232, 235)),
                (12, top + 34),
            )
            sequence = clips[actor][state].frames
            for frame_index in range(8):
                x = label_w + frame_index * cell_w + cell_w // 2
                pygame.draw.line(
                    canvas,
                    (52, 78, 86),
                    (x - cell_w // 2 + 5, ground),
                    (x + cell_w // 2 - 5, ground),
                )
                _blit_grounded(canvas, sequence[frame_index % len(sequence)], x, ground)
                canvas.blit(
                    label_font.render(str(frame_index + 1), True, (104, 157, 166)),
                    (x - 4, ground + 8),
                )
            row_index += 1
    return canvas


def export() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    clips = build_production_clips()
    for region, (label, basic, advanced, normal, runner, crawler) in REGIONS.items():
        soldier_frames: list[pygame.Surface] = []
        soldier_columns = ((basic, "BÁSICO"), (advanced, "AVANÇADO"))
        soldier_states = (
            ("move", "ENTRADA A PÉ"),
            ("shoot", "DISPARO"),
            ("reload", "RECARGA"),
            ("hit", "DANO"),
        )
        for tick in range(24):
            canvas = _panel(f"{label} — SOLDADOS: PÉS FIXOS E EFEITOS NA ORIGEM")
            for column, (actor, actor_label) in enumerate(soldier_columns):
                for row, (state, state_label) in enumerate(soldier_states):
                    x = 268 + column * 430
                    ground = 190 + row * 155
                    pygame.draw.line(canvas, (74, 104, 112), (x - 125, ground), (x + 125, ground), 2)
                    sequence = clips[actor][state].frames
                    _blit_grounded(canvas, sequence[tick % len(sequence)], x, ground)
                    _label(canvas, f"{actor_label} • {state_label}", x, ground + 25)
            soldier_frames.append(canvas)
        _save_gif(soldier_frames, OUTPUT / f"soldados_{region}.gif")
        pygame.image.save(soldier_frames[0], OUTPUT / f"soldados_{region}_quadro.png")
        soldier_contact = _contact_sheet(
            clips,
            f"{label} — TODOS OS QUADROS DOS SOLDADOS",
            soldier_columns,
            soldier_states,
        )
        pygame.image.save(soldier_contact, OUTPUT / f"soldados_{region}_contato.png")

        zombie_frames: list[pygame.Surface] = []
        zombie_columns = ((normal, "PADRÃO"), (runner, "CORREDOR"), (crawler, "RASTEJADOR"))
        zombie_states = (
            ("move", "ANDAR"),
            ("bite", "MORDER"),
            ("hit", "DANO"),
            ("skill", "HABILIDADE"),
        )
        for tick in range(24):
            canvas = _panel(f"{label} — ZUMBIS: CONTINUIDADE E HITBOX VISUAL")
            for column, (actor, actor_label) in enumerate(zombie_columns):
                for row, (state, state_label) in enumerate(zombie_states):
                    x = 180 + column * 300
                    ground = 190 + row * 155
                    pygame.draw.line(canvas, (74, 104, 112), (x - 110, ground), (x + 110, ground), 2)
                    sequence = clips[actor][state].frames
                    _blit_grounded(canvas, sequence[tick % len(sequence)], x, ground)
                    _label(canvas, f"{actor_label} • {state_label}", x, ground + 25)
            zombie_frames.append(canvas)
        _save_gif(zombie_frames, OUTPUT / f"zumbis_{region}.gif")
        pygame.image.save(zombie_frames[0], OUTPUT / f"zumbis_{region}_quadro.png")
        contact = _contact_sheet(
            clips,
            f"{label} — TODOS OS QUADROS DA PRÉVIA",
            zombie_columns,
            zombie_states,
        )
        pygame.image.save(contact, OUTPUT / f"zumbis_{region}_contato.png")
    pygame.quit()
    print(f"QA_ANIMACOES_EXPORTADA: {OUTPUT}")


if __name__ == "__main__":
    export()
