"""Exporta uma revisão visual compacta de todos os atores ativos da Beta 4.

O painel usa fundo claro e escuro ao mesmo tempo. Assim ele denuncia tanto
alfa apagado (corpo invisível) quanto resíduos de fundo que poderiam passar
despercebidos dentro dos cards escuros do menu.
"""

from __future__ import annotations

import os
import argparse
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import beta4_production_animations as production
from beta4_production_animations import ACTOR_SHEETS, ENEMY_ROSTER_ROWS, build_production_clips


OUTPUT = ROOT / "visual_qa_beta4" / "atores_ativos"


def state_samples(states: dict) -> list[tuple[str, pygame.Surface]]:
    ordered = ("idle", "move", "shoot", "reload", "support", "bite", "hit", "skill")
    samples: list[tuple[str, pygame.Surface]] = []
    for state in ordered:
        clip = states.get(state)
        if clip is not None:
            samples.append((state, clip.frames[len(clip.frames) // 2]))
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="ATOR=ARQUIVO",
        help="troca temporariamente uma folha para comparar reparos de alfa",
    )
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    for override in args.override:
        actor, filename = override.split("=", 1)
        _old_filename, kind = ACTOR_SHEETS[actor]
        source = Path(filename)
        if source.is_absolute():
            target = production.ASSETS / source.name
            target.write_bytes(source.read_bytes())
            filename = source.name
        ACTOR_SHEETS[actor] = (filename, kind)
    pygame.init()
    pygame.display.set_mode((1, 1))
    clips = build_production_clips()
    font = pygame.font.SysFont("consolas", 17, bold=True)
    small = pygame.font.SysFont("consolas", 13)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    regions = {
        "cidade": ("city_",),
        "deserto": ("desert_",),
        "cachoeira": ("beach_",),
    }
    for region, prefixes in regions.items():
        actors = [actor for actor in ACTOR_SHEETS if actor.startswith(prefixes)]
        row_height = 176
        width = 1180
        sheet = pygame.Surface((width, 48 + row_height * len(actors)))
        sheet.fill((226, 221, 203))
        title = font.render(f"BETA 4 - REVISAO DE ALFA E ANIMACAO - {region.upper()}", True, (20, 28, 33))
        sheet.blit(title, (18, 14))

        for row, actor in enumerate(actors):
            y = 48 + row * row_height
            dark = pygame.Rect(0, y, width, row_height)
            pygame.draw.rect(sheet, (22, 31, 38) if row % 2 == 0 else (238, 233, 216), dark)
            color = (238, 238, 226) if row % 2 == 0 else (20, 29, 34)
            label = font.render(actor, True, color)
            filename = small.render(ACTOR_SHEETS[actor][0], True, (92, 205, 185) if row % 2 == 0 else (31, 111, 104))
            sheet.blit(label, (16, y + 18))
            sheet.blit(filename, (16, y + 47))

            for column, (state, frame) in enumerate(state_samples(clips[actor])):
                cell = pygame.Rect(285 + column * 125, y + 8, 112, 152)
                pygame.draw.rect(sheet, (56, 71, 80) if row % 2 == 0 else (198, 207, 199), cell, border_radius=8)
                content = frame.get_bounding_rect(min_alpha=8)
                if content.width and content.height:
                    cropped = frame.subsurface(content).copy()
                    scale = min((cell.width - 12) / cropped.get_width(), (cell.height - 32) / cropped.get_height())
                    rendered = pygame.transform.scale(
                        cropped,
                        (max(1, round(cropped.get_width() * scale)), max(1, round(cropped.get_height() * scale))),
                    )
                    target = rendered.get_rect(midbottom=(cell.centerx, cell.bottom - 7))
                    sheet.blit(rendered, target)
                state_label = small.render(state, True, color)
                sheet.blit(state_label, (cell.x + 5, cell.y + 4))

        pygame.image.save(sheet, str(OUTPUT / f"atores_{region}{args.suffix}.png"))

    for region, prefix in (("cidade", "city_"), ("deserto", "desert_"), ("cachoeira", "beach_")):
        actors = [actor for actor in ENEMY_ROSTER_ROWS if actor.startswith(prefix)]
        row_height = 176
        width = 1040
        sheet = pygame.Surface((width, 48 + row_height * len(actors)))
        sheet.fill((226, 221, 203))
        title = font.render(f"BETA 4 - NOVO ELENCO INIMIGO - {region.upper()}", True, (20, 28, 33))
        sheet.blit(title, (18, 14))
        for row, actor in enumerate(actors):
            y = 48 + row * row_height
            dark_row = row % 2 == 0
            pygame.draw.rect(sheet, (22, 31, 38) if dark_row else (238, 233, 216), (0, y, width, row_height))
            color = (238, 238, 226) if dark_row else (20, 29, 34)
            sheet.blit(font.render(actor, True, color), (16, y + 18))
            for column, (state, frame) in enumerate(state_samples(clips[actor])):
                cell = pygame.Rect(285 + column * 125, y + 8, 112, 152)
                pygame.draw.rect(sheet, (56, 71, 80) if dark_row else (198, 207, 199), cell, border_radius=8)
                content = frame.get_bounding_rect(min_alpha=8)
                if content.width and content.height:
                    cropped = frame.subsurface(content).copy()
                    scale = min((cell.width - 12) / cropped.get_width(), (cell.height - 32) / cropped.get_height())
                    rendered = pygame.transform.scale(
                        cropped,
                        (max(1, round(cropped.get_width() * scale)), max(1, round(cropped.get_height() * scale))),
                    )
                    sheet.blit(rendered, rendered.get_rect(midbottom=(cell.centerx, cell.bottom - 7)))
                sheet.blit(small.render(state, True, color), (cell.x + 5, cell.y + 4))
        pygame.image.save(sheet, str(OUTPUT / f"inimigos_{region}{args.suffix}.png"))

    pygame.quit()
    print(f"PAINEIS_EXPORTADOS: {OUTPUT}")


if __name__ == "__main__":
    main()
