"""Reempacota uma folha gerada em uma grade segura para recorte.

Geradores de imagem podem desenhar alguns pixels de uma pose além da divisão
matemática da célula. Este utilitário encontra os 16 corpos principais, associa
clarões, cápsulas e carregadores ao corpo mais próximo e cria uma nova grade
8x2 com margem transparente real. Nenhum pixel do personagem é redesenhado.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


@dataclass(slots=True)
class Component:
    mask: pygame.Mask
    rect: pygame.Rect


@dataclass(slots=True)
class ActorParts:
    main: Component
    parts: list[Component]

    @property
    def anchor(self) -> tuple[int, int]:
        return self.main.rect.centerx, self.main.rect.bottom


def _distance(component: Component, actor: ActorParts) -> float:
    """Distância ponderada que favorece a pose da mesma fileira."""
    actor_x, actor_y = actor.anchor
    rect = component.rect
    return abs(rect.centerx - actor_x) + abs(rect.centery - actor_y) * 1.8


def _blit_component(
    source: pygame.Surface,
    destination: pygame.Surface,
    component: Component,
    offset: tuple[int, int],
) -> None:
    """Copia apenas o componente, não outros resíduos dentro do retângulo."""
    rect = component.rect
    component_surface = component.mask.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    crop = source.subsurface(rect).copy()
    crop.blit(
        component_surface.subsurface(rect),
        (0, 0),
        special_flags=pygame.BLEND_RGBA_MULT,
    )
    destination.blit(crop, (rect.x + offset[0], rect.y + offset[1]))


def repack(
    source_path: Path,
    destination_path: Path,
    *,
    columns: int = 8,
    rows: int = 2,
) -> tuple[int, int]:
    pygame.init()
    pygame.display.set_mode((1, 1))
    source = pygame.image.load(str(source_path)).convert_alpha()
    mask = pygame.mask.from_surface(source, threshold=8)
    components = [
        Component(component_mask, component_mask.get_bounding_rects()[0])
        for component_mask in mask.connected_components()
        if component_mask.get_bounding_rects()
        and component_mask.get_bounding_rects()[0].width
        * component_mask.get_bounding_rects()[0].height
        >= 6
    ]

    # Os corpos completos são muito maiores que clarões, cápsulas e pentes.
    body_components = [
        component
        for component in components
        if component.rect.width >= 150 and component.rect.height >= 230
    ]
    expected_bodies = columns * rows
    if len(body_components) != expected_bodies:
        raise ValueError(
            f"esperados {expected_bodies} corpos principais, "
            f"encontrados {len(body_components)}"
        )

    if rows == 1:
        ordered = sorted(body_components, key=lambda component: component.rect.centerx)
    elif rows == 2:
        split_y = source.get_height() // 2
        top = sorted(
            (
                component
                for component in body_components
                if component.rect.centery < split_y
            ),
            key=lambda component: component.rect.centerx,
        )
        bottom = sorted(
            (
                component
                for component in body_components
                if component.rect.centery >= split_y
            ),
            key=lambda component: component.rect.centerx,
        )
        if len(top) != columns or len(bottom) != columns:
            raise ValueError(
                f"grade inválida: fileira superior={len(top)}, "
                f"inferior={len(bottom)}"
            )
        ordered = top + bottom
    else:
        raise ValueError("este utilitário aceita uma ou duas fileiras")

    actors = [ActorParts(component, [component]) for component in ordered]
    body_ids = {id(component) for component in body_components}
    for component in components:
        if id(component) in body_ids:
            continue
        nearest = min(actors, key=lambda actor: _distance(component, actor))
        nearest.parts.append(component)

    # Restos minúsculos do quadro vizinho não são efeitos. No tiro, os únicos
    # elementos soltos válidos são cápsulas acima das armas; na recarga, são os
    # dois carregadores abaixo das mãos. O clarão está conectado às pistolas.
    for index, actor in enumerate(actors):
        meaningful = [actor.main]
        for part in actor.parts[1:]:
            part_rect = part.rect
            area = part_rect.width * part_rect.height
            if index < 8:
                if (
                    area >= 30
                    and part_rect.centerx >= actor.main.rect.centerx
                    and part_rect.centery
                    <= actor.main.rect.top + actor.main.rect.height * 0.38
                ):
                    meaningful.append(part)
            elif (
                area >= 80
                and part_rect.centery
                >= actor.main.rect.top + actor.main.rect.height * 0.25
            ):
                meaningful.append(part)
        actor.parts = meaningful

    left = right = top_extent = bottom_extent = 0
    for actor in actors:
        anchor_x, anchor_y = actor.anchor
        for part in actor.parts:
            rect = part.rect
            left = max(left, anchor_x - rect.left)
            right = max(right, rect.right - anchor_x)
            top_extent = max(top_extent, anchor_y - rect.top)
            bottom_extent = max(bottom_extent, rect.bottom - anchor_y)

    padding_x, padding_top, padding_bottom = 14, 12, 4
    cell_width = left + right + padding_x * 2
    cell_height = top_extent + bottom_extent + padding_top + padding_bottom
    actor_x = left + padding_x
    actor_y = top_extent + padding_top
    sheet = pygame.Surface((cell_width * columns, cell_height * rows), pygame.SRCALPHA)

    for index, actor in enumerate(actors):
        frame = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
        anchor_x, anchor_y = actor.anchor
        offset_x = actor_x - anchor_x
        offset_y = actor_y - anchor_y
        for part in actor.parts:
            _blit_component(
                source,
                frame,
                part,
                (offset_x, offset_y),
            )
        column = index % columns
        row = index // columns
        sheet.blit(frame, (column * cell_width, row * cell_height))

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(destination_path))
    pygame.quit()
    return cell_width, cell_height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--rows", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    cell_width, cell_height = repack(
        args.source,
        args.destination,
        columns=args.columns,
        rows=args.rows,
    )
    print(
        f"OK: grade {args.columns}x{args.rows}, célula {cell_width}x{cell_height}, "
        f"arquivo {args.destination}"
    )


if __name__ == "__main__":
    main()
