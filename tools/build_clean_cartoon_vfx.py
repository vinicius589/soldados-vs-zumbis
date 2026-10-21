"""Gera VFX 2D simples, lisos e transparentes para a Beta 4.

As folhas antigas tinham iluminação quase fotográfica e halos que invadiam a
célula vizinha. Aqui cada quadro é desenhado em resolução dupla e reduzido com
antialiasing: o resultado conserva o traço cartunesco sem ficar serrilhado ou
com aparência de pixel art grosseira.
"""

from __future__ import annotations

from pathlib import Path
from math import cos, pi, sin

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "v7"
SCALE = 3
CELL = 256
SHEET_SIZE = (CELL * 4, CELL * 3)


def point(value: tuple[float, float]) -> tuple[int, int]:
    return int(value[0] * SCALE), int(value[1] * SCALE)


def box(value: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(int(item * SCALE) for item in value)  # type: ignore[return-value]


def polygon(draw: ImageDraw.ImageDraw, points, *, fill, outline=(19, 25, 31, 255), width=5):
    scaled = [point(item) for item in points]
    draw.polygon(scaled, fill=fill)
    draw.line(scaled + [scaled[0]], fill=outline, width=width * SCALE, joint="curve")


def ellipse(draw: ImageDraw.ImageDraw, bounds, *, fill, outline=(19, 25, 31, 255), width=5):
    draw.ellipse(box(bounds), fill=fill, outline=outline, width=width * SCALE)


def line(draw: ImageDraw.ImageDraw, points, *, fill, width):
    draw.line([point(item) for item in points], fill=fill, width=width * SCALE, joint="curve")


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (SHEET_SIZE[0] * SCALE, SHEET_SIZE[1] * SCALE), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def cell_origin(column: int, row: int) -> tuple[int, int]:
    return column * CELL, row * CELL


def save(image: Image.Image, filename: str) -> None:
    image.resize(SHEET_SIZE, Image.Resampling.LANCZOS).save(OUTPUT / filename)


def bullet(draw, column, row, body, tip, *, length=148, height=44, band=None):
    ox, oy = cell_origin(column, row)
    left, cy = ox + (CELL - length) / 2, oy + CELL / 2
    right = left + length
    ellipse(draw, (left, cy - height / 2, right - height * .40, cy + height / 2), fill=body, width=5)
    polygon(draw, [(right - height * .65, cy - height / 2), (right, cy), (right - height * .65, cy + height / 2)], fill=tip, width=5)
    if band:
        line(draw, [(right - height * .82, cy - height * .42), (right - height * .82, cy + height * .42)], fill=band, width=7)
    line(draw, [(left + 16, cy - height * .20), (right - height * .88, cy - height * .20)], fill=(255, 232, 139, 255), width=4)


def build_projectiles() -> None:
    image, draw = canvas()
    bullet(draw, 0, 0, (218, 160, 48, 255), (230, 90, 55, 255), length=150, height=38)
    # Cartucho, usado apenas como referência visual no menu; o projétil da
    # espingarda em jogo continua sendo um agrupamento pequeno de chumbos.
    ox, oy = cell_origin(1, 0)
    ellipse(draw, (ox + 55, oy + 92, ox + 201, oy + 164), fill=(190, 49, 40, 255), width=6)
    line(draw, [(ox + 78, oy + 94), (ox + 78, oy + 162)], fill=(226, 170, 52, 255), width=14)
    line(draw, [(ox + 101, oy + 100), (ox + 181, oy + 100)], fill=(246, 98, 73, 255), width=5)
    bullet(draw, 2, 0, (208, 151, 43, 255), (218, 83, 48, 255), length=166, height=34)
    bullet(draw, 3, 0, (207, 151, 42, 255), (224, 88, 54, 255), length=166, height=42, band=(45, 55, 65, 255))

    # Granada
    ox, oy = cell_origin(0, 1)
    ellipse(draw, (ox + 78, oy + 79, ox + 178, oy + 181), fill=(83, 112, 55, 255), width=6)
    for x in (103, 128, 153):
        line(draw, [(ox + x, oy + 88), (ox + x, oy + 172)], fill=(42, 67, 43, 255), width=4)
    for y in (108, 136, 162):
        line(draw, [(ox + 87, oy + y), (ox + 169, oy + y)], fill=(42, 67, 43, 255), width=4)
    polygon(draw, [(ox + 118, oy + 81), (ox + 144, oy + 81), (ox + 150, oy + 58), (ox + 118, oy + 58)], fill=(74, 83, 76, 255), width=5)
    line(draw, [(ox + 139, oy + 60), (ox + 171, oy + 47)], fill=(180, 186, 184, 255), width=8)
    ellipse(draw, (ox + 158, oy + 37, ox + 181, oy + 60), fill=(0, 0, 0, 0), outline=(28, 33, 36, 255), width=5)

    # Morteiro, foguete e torpedo
    for column, body, accent, fins, propeller in (
        (1, (91, 112, 63, 255), (38, 53, 40, 255), True, False),
        (2, (82, 103, 60, 255), (239, 166, 35, 255), True, False),
        (3, (56, 81, 98, 255), (221, 225, 220, 255), True, True),
    ):
        ox, oy = cell_origin(column, 1)
        polygon(draw, [(ox + 58, oy + 109), (ox + 176, oy + 109), (ox + 207, oy + 128), (ox + 176, oy + 147), (ox + 58, oy + 147)], fill=body, width=6)
        polygon(draw, [(ox + 63, oy + 109), (ox + 43, oy + 86), (ox + 82, oy + 109)], fill=body, width=5)
        polygon(draw, [(ox + 63, oy + 147), (ox + 43, oy + 170), (ox + 82, oy + 147)], fill=body, width=5)
        line(draw, [(ox + 157, oy + 112), (ox + 157, oy + 144)], fill=accent, width=8)
        if propeller:
            ellipse(draw, (ox + 37, oy + 108, ox + 59, oy + 130), fill=(230, 161, 32, 255), width=4)
            line(draw, [(ox + 48, oy + 96), (ox + 48, oy + 159)], fill=(230, 161, 32, 255), width=7)

    # Ácido, projétil infectado, drone e arpão.
    ox, oy = cell_origin(0, 2)
    polygon(draw, [(ox + 52, oy + 132), (ox + 82, oy + 105), (ox + 131, oy + 94), (ox + 183, oy + 109), (ox + 207, oy + 132), (ox + 181, oy + 157), (ox + 126, oy + 164), (ox + 81, oy + 152)], fill=(102, 211, 45, 255), outline=(34, 89, 34, 255), width=6)
    for cx, cy, radius in ((77, 102, 9), (54, 151, 7), (198, 100, 6)):
        ellipse(draw, (ox + cx - radius, oy + cy - radius, ox + cx + radius, oy + cy + radius), fill=(148, 239, 65, 255), outline=(34, 89, 34, 255), width=3)
    bullet(draw, 1, 2, (211, 219, 204, 255), (181, 45, 43, 255), length=142, height=38, band=(91, 41, 42, 255))
    ox, oy = cell_origin(2, 2)
    polygon(draw, [(ox + 59, oy + 109), (ox + 176, oy + 109), (ox + 205, oy + 128), (ox + 176, oy + 147), (ox + 59, oy + 147)], fill=(57, 73, 85, 255), width=6)
    polygon(draw, [(ox + 83, oy + 109), (ox + 61, oy + 83), (ox + 112, oy + 109)], fill=(57, 73, 85, 255), width=5)
    line(draw, [(ox + 158, oy + 112), (ox + 158, oy + 144)], fill=(224, 59, 52, 255), width=8)
    ox, oy = cell_origin(3, 2)
    polygon(draw, [(ox + 52, oy + 119), (ox + 180, oy + 119), (ox + 211, oy + 93), (ox + 199, oy + 128), (ox + 211, oy + 163), (ox + 180, oy + 137), (ox + 52, oy + 137)], fill=(194, 205, 208, 255), width=6)
    line(draw, [(ox + 81, oy + 111), (ox + 81, oy + 145)], fill=(185, 126, 64, 255), width=13)
    save(image, "projectile_sprites_sheet_beta4_clean.png")


def burst_points(cx, cy, outer, inner, count=12):
    result = []
    for index in range(count * 2):
        angle = -pi / 2 + index * pi / count
        radius = outer if index % 2 == 0 else inner
        result.append((cx + cos(angle) * radius, cy + sin(angle) * radius))
    return result


def build_combat() -> None:
    image, draw = canvas()
    for row in range(3):
        for stage in range(4):
            ox, oy = cell_origin(stage, row)
            size = (32 + stage * 15) if row == 0 else (44 + stage * 18 if row == 1 else 58 + stage * 23)
            cx, cy = ox + 128, oy + 128
            if row == 0:
                polygon(draw, burst_points(cx, cy, size, size * .38, 9), fill=(255, 179, 36, 255), outline=(155, 66, 25, 255), width=4)
                polygon(draw, burst_points(cx, cy, size * .55, size * .20, 8), fill=(255, 241, 157, 255), outline=(255, 241, 157, 255), width=2)
            elif row == 1:
                for dx, dy, radius in ((-18, 5, .35), (8, -9, .44), (25, 8, .30)):
                    ellipse(draw, (cx + dx - size * radius, cy + dy - size * radius, cx + dx + size * radius, cy + dy + size * radius), fill=(122, 128, 130, 210), outline=(55, 62, 65, 255), width=4)
            else:
                polygon(draw, burst_points(cx, cy, size, size * .46, 10), fill=(238, 91, 35, 255), outline=(117, 48, 26, 255), width=5)
                ellipse(draw, (cx - size * .40, cy - size * .40, cx + size * .40, cy + size * .40), fill=(255, 207, 55, 255), outline=(255, 238, 132, 255), width=4)
    save(image, "combat_effects_sheet_beta4_clean.png")


def build_elemental() -> None:
    image, draw = canvas()
    palettes = (
        ((237, 78, 31, 255), (255, 205, 48, 255), (131, 47, 28, 255)),
        ((43, 140, 216, 255), (123, 220, 248, 255), (31, 82, 132, 255)),
        ((76, 177, 51, 255), (166, 228, 70, 255), (38, 91, 43, 255)),
    )
    for row, (outer, inner, outline) in enumerate(palettes):
        for stage in range(4):
            ox, oy = cell_origin(stage, row)
            length = 78 + stage * 25
            height = 28 + stage * 10
            cx, cy = ox + 128, oy + 128
            polygon(draw, [(cx - length / 2, cy), (cx - length * .18, cy - height / 2), (cx + length / 2, cy), (cx - length * .18, cy + height / 2)], fill=outer, outline=outline, width=5)
            polygon(draw, [(cx - length * .28, cy), (cx, cy - height * .24), (cx + length * .33, cy), (cx, cy + height * .24)], fill=inner, outline=inner, width=2)
            if row != 0:
                for index in range(2 + stage):
                    bx = cx - length * .16 + index * 16
                    by = cy - height * .62 - (index % 2) * 6
                    ellipse(draw, (bx - 5, by - 5, bx + 5, by + 5), fill=inner, outline=outline, width=2)
    save(image, "elemental_effects_sheet_beta4_clean.png")


def build_abilities() -> None:
    image, draw = canvas()
    for stage in range(4):
        ox, oy = cell_origin(stage, 0)
        width = 45 + stage * 27
        cx, cy = ox + 128, oy + 148
        polygon(draw, burst_points(cx, cy, width, width * .56, 9), fill=(160, 119, 69, 255), outline=(73, 57, 45, 255), width=5)
        line(draw, [(cx - width, cy + 23), (cx + width, cy + 23)], fill=(80, 64, 51, 230), width=7)
    for stage in range(4):
        ox, oy = cell_origin(stage, 1)
        cx, cy = ox + 128, oy + 128
        radius = 35 + stage * 18
        for ring in (1.0, .67):
            ellipse(draw, (cx - radius * ring, cy - radius * ring, cx + radius * ring, cy + radius * ring), fill=(0, 0, 0, 0), outline=(105, 196, 219, 235), width=5)
        line(draw, [(cx, cy + 17), (cx, cy - radius * .70)], fill=(228, 231, 213, 255), width=6)
        polygon(draw, [(cx, cy - radius), (cx - 8, cy - radius * .65), (cx + 8, cy - radius * .65)], fill=(228, 231, 213, 255), outline=(228, 231, 213, 255), width=2)
    for stage in range(4):
        ox, oy = cell_origin(stage, 2)
        cx, cy = ox + 128, oy + 145
        length = 55 + stage * 25
        points = []
        for index in range(9):
            x = cx - length + index * length / 4
            y = cy + sin(index * pi / 2) * (15 + stage * 4)
            points.append((x, y))
        line(draw, points, fill=(43, 139, 211, 255), width=16)
        line(draw, [(x, y - 5) for x, y in points], fill=(130, 224, 246, 255), width=5)
    save(image, "ability_effects_sheet_beta4_clean.png")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_projectiles()
    build_combat()
    build_elemental()
    build_abilities()
    print("Folhas 2D limpas geradas em", OUTPUT)


if __name__ == "__main__":
    main()
