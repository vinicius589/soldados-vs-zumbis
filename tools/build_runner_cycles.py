"""Converte as reconstruções 4x2 em ciclos 8x1 seguros para o jogo.

O gerador deixou um halo de alfa quase invisível ao redor das figuras. A
limpeza abaixo conserva apenas pixels visíveis do ator e recompõe cada pose
numa célula com margem real, evitando que sapatos ou mãos invadam o quadro
seguinte.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
import pygame


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "beta4_producao"
SOURCES = ASSETS / "generated_runner_sources"
# Células mais largas acomodam a passada completa sem obrigar um quadro
# estendido a encolher. A altura corporal continua idêntica nos oito quadros.
CELL = (256, 256)
ACTOR_HEIGHT = 220


def _cell(sheet: Image.Image, column: int, row: int) -> Image.Image:
    width, height = sheet.size
    left = round(column * width / 4)
    right = round((column + 1) * width / 4)
    top = round(row * height / 2)
    bottom = round((row + 1) * height / 2)
    return sheet.crop((left, top, right, bottom))


def _clean_actor(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    red, green, blue, alpha = image.split()
    # O halo decorativo fica abaixo desse limiar. O contorno do pixel art é
    # opaco, portanto a silhueta não perde botas, dedos nem faixas.
    alpha = alpha.point(lambda value: value if value >= 88 else 0)
    cleaned = Image.merge("RGBA", (red, green, blue, alpha))
    # Se uma pose da linha anterior encostar matematicamente na célula atual,
    # ela ainda aparece como um componente separado. Conservamos somente a
    # silhueta corporal dominante da célula; pés e mãos legítimos permanecem
    # ligados ao ator nas reconstruções novas.
    surface = pygame.image.frombytes(cleaned.tobytes(), cleaned.size, "RGBA")
    components = pygame.mask.from_surface(surface, threshold=88).connected_components(minimum=3)
    if not components:
        raise ValueError("quadro de corredor vazio")
    main = max(components, key=lambda component: component.count())
    mask_surface = main.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    keep_alpha = Image.frombytes(
        "RGBA", cleaned.size, pygame.image.tobytes(mask_surface, "RGBA")
    ).getchannel("A")
    cleaned.putalpha(keep_alpha)
    bounds = cleaned.getbbox()
    if bounds is None:
        raise ValueError("quadro de corredor vazio")
    return cleaned.crop(bounds)


def _fit(image: Image.Image) -> Image.Image:
    actor = _clean_actor(image)
    factor = ACTOR_HEIGHT / actor.height
    size = (max(1, round(actor.width * factor)), max(1, round(actor.height * factor)))
    if size[0] > CELL[0] - 12:
        raise ValueError(
            f"passada larga demais para a célula sem alterar escala: {size[0]} px"
        )
    actor = actor.resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", CELL, (0, 0, 0, 0))
    x = (CELL[0] - actor.width) // 2
    y = CELL[1] - 13 - actor.height
    canvas.alpha_composite(actor, (x, y))
    return canvas


def _build(source_name: str, output_name: str, replacement_last: str | None = None) -> None:
    source = Image.open(SOURCES / source_name).convert("RGBA")
    poses = [_cell(source, column, row) for row in range(2) for column in range(4)]
    if replacement_last is not None:
        poses[-1] = Image.open(SOURCES / replacement_last).convert("RGBA")
    strip = Image.new("RGBA", (CELL[0] * 8, CELL[1]), (0, 0, 0, 0))
    for index, pose in enumerate(poses):
        strip.alpha_composite(_fit(pose), (index * CELL[0], 0))
    strip.save(ASSETS / output_name)


def main() -> None:
    _build(
        "city_runner_4x2_source.png",
        "corredor_cidade_corrida_8x1_v2.png",
        replacement_last="city_runner_frame8_source.png",
    )
    _build("desert_runner_4x2_source.png", "corredor_deserto_corrida_8x1_v2.png")
    _build("beach_runner_4x2_source.png", "corredor_cachoeira_corrida_8x1_v2.png")
    print("CICLOS_CORREDORES_RECONSTRUIDOS")


if __name__ == "__main__":
    main()
