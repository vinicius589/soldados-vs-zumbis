"""Normaliza uma folha RGBA de atores numa grade sem invasão de quadros.

O gerador pode aproximar a grade visual sem respeitar matematicamente suas
divisões. Este utilitário identifica os maiores componentes (os corpos), liga
efeitos soltos ao corpo mais próximo e recompõe cada pose com um pivô comum nos
pés. Nenhum pixel do desenho é redesenhado.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import numpy as np


@dataclass(slots=True)
class Component:
    mask: pygame.Mask
    rect: pygame.Rect
    pixels: int


@dataclass(slots=True)
class Actor:
    body: Component
    parts: list[Component]

    @property
    def anchor(self) -> tuple[int, int]:
        return self.body.rect.centerx, self.body.rect.bottom


def _distance(component: Component, actor: Actor) -> float:
    anchor_x, anchor_y = actor.anchor
    return abs(component.rect.centerx - anchor_x) + abs(component.rect.centery - anchor_y) * 2.0


def _copy_component(
    source: pygame.Surface,
    destination: pygame.Surface,
    component: Component,
    offset: tuple[int, int],
) -> None:
    rect = component.rect
    component_surface = component.mask.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    crop = source.subsurface(rect).copy()
    crop.blit(component_surface.subsurface(rect), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    destination.blit(crop, (rect.x + offset[0], rect.y + offset[1]))


def repack(source_path: Path, destination_path: Path, columns: int, rows: int) -> tuple[int, int]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    source = pygame.image.load(str(source_path)).convert_alpha()
    source_rgb = pygame.surfarray.array3d(source)
    source_alpha = pygame.surfarray.array_alpha(source)
    mask = pygame.mask.from_surface(source, threshold=8)
    components: list[Component] = []
    for component_mask in mask.connected_components(minimum=5):
        rects = component_mask.get_bounding_rects()
        if rects:
            components.append(Component(component_mask, rects[0], component_mask.count()))

    expected = columns * rows
    if len(components) < expected:
        raise ValueError(f"esperados {expected} corpos, mas há somente {len(components)} componentes")

    bodies = sorted(components, key=lambda item: item.pixels, reverse=True)[:expected]
    # Corredores inclinados e, principalmente, rastejantes ocupam bem menos
    # altura que um caminhante em pé. A validação anterior (45% da fileira)
    # rejeitava justamente essas poses válidas nas folhas do Deserto e da
    # Cachoeira. Ainda mantemos um piso conservador para não aceitar faíscas,
    # gotas ou cartuchos como se fossem um ator.
    minimum_height = source.get_height() / rows * 0.20
    if any(body.rect.height < minimum_height for body in bodies):
        raise ValueError("um dos componentes principais é pequeno demais para ser um corpo")

    # A geração já organiza os centros aproximadamente por fileira. Ordenar
    # por Y, separar em grupos de oito e então ordenar por X recupera a grade
    # sem depender de linhas matemáticas que poderiam cortar braços ou armas.
    by_y = sorted(bodies, key=lambda item: item.rect.centery)
    ordered: list[Component] = []
    for row in range(rows):
        group = by_y[row * columns : (row + 1) * columns]
        if len(group) != columns:
            raise ValueError(f"fileira {row} não contém {columns} corpos")
        ordered.extend(sorted(group, key=lambda item: item.rect.centerx))

    actors = [Actor(body, [body]) for body in ordered]
    body_ids = {id(body) for body in bodies}
    for component in components:
        if id(component) in body_ids:
            continue
        rect = component.rect
        colors = source_rgb[rect.left : rect.right, rect.top : rect.bottom]
        visible = source_alpha[rect.left : rect.right, rect.top : rect.bottom] > 8
        values = colors[visible]
        red_fraction = 0.0
        if values.size:
            red_fraction = float(
                np.mean(
                    (values[:, 0] > 150)
                    & (values[:, 0] > values[:, 1].astype(np.float32) * 1.35)
                    & (values[:, 0] > values[:, 2].astype(np.float32) * 1.20)
                )
            )
        # Os respingos físicos da fileira de dano podem ser desenhados acima
        # do corpo e, geometricamente, ficar mais perto da fileira de recarga.
        # A cor identifica esse caso sem confundir carregadores escuros.
        candidates = actors[-columns:] if rows >= 2 and red_fraction >= 0.40 else actors
        nearest = min(candidates, key=lambda actor: _distance(component, actor))
        nearest.parts.append(component)

    left = right = top = bottom = 0
    for actor in actors:
        anchor_x, anchor_y = actor.anchor
        for part in actor.parts:
            left = max(left, anchor_x - part.rect.left)
            right = max(right, part.rect.right - anchor_x)
            top = max(top, anchor_y - part.rect.top)
            bottom = max(bottom, part.rect.bottom - anchor_y)

    padding_x, padding_top, padding_bottom = 12, 10, 5
    cell_width = left + right + padding_x * 2
    cell_height = top + bottom + padding_top + padding_bottom
    target_anchor = (left + padding_x, top + padding_top)
    output = pygame.Surface((cell_width * columns, cell_height * rows), pygame.SRCALPHA)

    for index, actor in enumerate(actors):
        frame = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
        anchor_x, anchor_y = actor.anchor
        offset = (target_anchor[0] - anchor_x, target_anchor[1] - anchor_y)
        for part in actor.parts:
            _copy_component(source, frame, part, offset)
        output.blit(frame, ((index % columns) * cell_width, (index // columns) * cell_height))

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(output, str(destination_path))
    pygame.quit()
    return cell_width, cell_height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--rows", type=int, default=1)
    args = parser.parse_args()
    width, height = repack(args.source, args.destination, args.columns, args.rows)
    print(f"OK: grade {args.columns}x{args.rows}, célula {width}x{height}, arquivo {args.destination}")


if __name__ == "__main__":
    main()
