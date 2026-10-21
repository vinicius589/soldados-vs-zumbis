"""Remove fundos suaves conectados às bordas de uma sprite sheet.

O recorte é feito célula por célula. Um flood-fill acompanha apenas variações
locais pequenas, por isso atravessa gradientes e halos de cenário, mas para no
contorno nítido do pixel art. O arquivo-fonte nunca é sobrescrito.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def clear_cell(image: Image.Image, box: tuple[int, int, int, int], tolerance: int) -> None:
    left, top, right, bottom = box
    pixels = image.load()
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(left, right):
        queue.append((x, top))
        queue.append((x, bottom - 1))
    for y in range(top + 1, bottom - 1):
        queue.append((left, y))
        queue.append((right - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        current = pixels[x, y][:3]
        pixels[x, y] = (*current, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (left <= nx < right and top <= ny < bottom) or (nx, ny) in seen:
                continue
            if color_distance(current, pixels[nx, ny][:3]) <= tolerance:
                queue.append((nx, ny))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--tolerance", type=int, default=14)
    parser.add_argument(
        "--restore-alpha",
        action="store_true",
        help="reconstrói a opacidade pelo RGB antes de remover o fundo",
    )
    args = parser.parse_args()

    image = Image.open(args.source).convert("RGBA")
    if args.restore_alpha:
        # Algumas folhas tiveram o uniforme preto/azul confundido com o fundo
        # durante uma remoção anterior. O RGB original continua intacto; esta
        # opção recompõe a máscara do zero antes do flood-fill por célula.
        image.putalpha(255)
    cell_width = image.width // args.columns
    cell_height = image.height // args.rows
    for row in range(args.rows):
        for column in range(args.columns):
            left = column * cell_width
            top = row * cell_height
            right = image.width if column == args.columns - 1 else (column + 1) * cell_width
            bottom = image.height if row == args.rows - 1 else (row + 1) * cell_height
            clear_cell(image, (left, top, right, bottom), args.tolerance)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.destination)


if __name__ == "__main__":
    main()
