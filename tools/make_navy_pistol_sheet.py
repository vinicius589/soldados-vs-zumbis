"""Cria o marinheiro básico com pistola 9 mm a partir do atlas aprovado.

O atlas do xerife já possui todas as poses físicas de uma arma curta. Esta
ferramenta preserva cada silhueta e cada pivô, troca somente a leitura do
uniforme e acrescenta a identificação brasileira. Assim nenhuma linha volta
a usar a carabina longa que havia sido atribuída por engano ao marinheiro.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pygame


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "beta4_producao" / "guarda_rua_8x5_v1.png"
OUTPUT = ROOT / "assets" / "beta4_producao" / "marinheiro_pistola_9mm_8x5_v3.png"


def recolor_cell(cell: pygame.Surface) -> pygame.Surface:
    result = cell.copy()
    components = pygame.mask.from_surface(result, threshold=8).get_bounding_rects()
    if not components:
        return result
    body = max(components, key=lambda rect: rect.width * rect.height)

    rgb = pygame.surfarray.pixels3d(result)
    alpha = pygame.surfarray.pixels_alpha(result)
    xs = np.arange(result.get_width())[:, None]
    ys = np.arange(result.get_height())[None, :]
    opaque = alpha >= 8
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)

    # Bege da camisa/jaqueta -> azul-marinho de serviço. Tons alaranjados do
    # rosto ficam fora da maior parte da máscara; luvas podem permanecer
    # escuras, coerentes com a unidade armada.
    torso = (
        opaque
        & (ys >= body.top + round(body.height * 0.22))
        & (ys <= body.bottom - round(body.height * 0.16))
        & (r >= 64)
        & (g >= 45)
        & (r >= g)
        & (g >= b)
        & ((r - b) >= 18)
        & ((r - g) <= 72)
    )
    luminance = (r * 3 + g * 5 + b * 2) // 10
    rgb[:, :, 0][torso] = np.clip(10 + luminance[torso] * 0.10, 12, 38)
    rgb[:, :, 1][torso] = np.clip(25 + luminance[torso] * 0.16, 28, 66)
    rgb[:, :, 2][torso] = np.clip(52 + luminance[torso] * 0.30, 58, 118)

    # O topo da antiga cobertura policial vira o gorro branco do praça. O
    # corpo é usado como referência, então sangue/efeitos soltos não entram.
    cap = (
        opaque
        & (xs >= body.left)
        & (xs < body.right)
        & (ys >= body.top)
        & (ys <= body.top + round(body.height * 0.17))
        & ~((r > g + 22) & (g > b + 12))
    )
    cap_light = np.clip(178 + luminance * 0.34, 188, 250)
    rgb[:, :, 0][cap] = cap_light[cap]
    rgb[:, :, 1][cap] = cap_light[cap]
    rgb[:, :, 2][cap] = np.clip(cap_light[cap] + 5, 193, 255)
    del rgb, alpha

    # Patch do Brasil no ombro voltado à câmera.
    patch_w = max(6, round(body.width * 0.075))
    patch_h = max(4, round(body.height * 0.045))
    patch = pygame.Rect(
        body.left + round(body.width * 0.28),
        body.top + round(body.height * 0.31),
        patch_w,
        patch_h,
    )
    pygame.draw.rect(result, (24, 133, 68), patch)
    pygame.draw.polygon(
        result,
        (244, 208, 52),
        (patch.midtop, patch.midright, patch.midbottom, patch.midleft),
    )
    pygame.draw.circle(result, (35, 69, 139), patch.center, max(1, patch_h // 4))
    return result


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)
    sheet = pygame.image.load(str(SOURCE)).convert_alpha()
    columns, rows = 8, 5
    cell_w, cell_h = sheet.get_width() // columns, sheet.get_height() // rows
    output = pygame.Surface((cell_w * columns, cell_h * rows), pygame.SRCALPHA)
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(column * cell_w, row * cell_h, cell_w, cell_h)
            output.blit(recolor_cell(sheet.subsurface(rect).copy()), rect)
    pygame.image.save(output, str(OUTPUT))
    pygame.quit()
    print(OUTPUT)


if __name__ == "__main__":
    main()
