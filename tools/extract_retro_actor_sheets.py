"""Extrai atores 16-bit de fundos suaves sem apagar roupa ou equipamento.

O fundo é estimado pelas bordas de cada célula. Pixels que se afastam dessa
paleta formam sementes de primeiro plano; a máscara cresce apenas por pixels
vizinhos ainda diferentes do fundo. Assim um uniforme escuro não é confundido
com sombra e o gradiente do cenário não invade a sprite.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "beta4_producao"

SHEETS = (
    ("city_enemies_retro_8x12_v2.png", "city_enemies_retro_8x12_v2_alpha.png"),
    ("desert_enemies_retro_8x12_v3.png", "desert_enemies_retro_8x12_v3_alpha.png"),
    ("beach_enemies_retro_8x12_v4.png", "beach_enemies_retro_8x12_v4_alpha.png"),
)


def _background_palette(rgb: np.ndarray) -> np.ndarray:
    top = rgb[:5:2, ::3].reshape(-1, 3)
    bottom = rgb[-5::2, ::3].reshape(-1, 3)
    left = rgb[::3, :5:2].reshape(-1, 3)
    right = rgb[::3, -5::2].reshape(-1, 3)
    samples = np.concatenate((top, bottom, left, right), axis=0)
    # Quantização curta reduz custo sem transformar tons de pele/roupa em fundo.
    return np.unique((samples // 8) * 8, axis=0).astype(np.int16)


def _connected_foreground(candidate: np.ndarray, seed: np.ndarray) -> np.ndarray:
    height, width = candidate.shape
    keep = np.zeros_like(candidate, dtype=bool)
    queue: deque[tuple[int, int]] = deque(
        (int(y), int(x)) for y, x in np.argwhere(seed)
    )
    while queue:
        y, x = queue.popleft()
        if keep[y, x] or not candidate[y, x]:
            continue
        keep[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and not keep[ny, nx] and candidate[ny, nx]:
                queue.append((ny, nx))
    return keep


def extract_cell(cell: Image.Image) -> Image.Image:
    rgba = np.array(cell.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[:, :, :3].astype(np.int16)
    palette = _background_palette(rgb)
    # Distância Chebyshev funciona melhor em pixel art: basta um canal divergir.
    distance = np.full(rgb.shape[:2], 255, dtype=np.int16)
    for color in palette:
        distance = np.minimum(distance, np.max(np.abs(rgb - color), axis=2))
    candidate = distance >= 13
    seed = distance >= 38
    keep = _connected_foreground(candidate, seed)
    alpha = np.zeros(distance.shape, dtype=np.uint8)
    ramp = np.clip((distance.astype(np.float32) - 11.0) / 22.0, 0.0, 1.0)
    alpha[keep] = np.maximum(96, np.rint(ramp[keep] * 255.0)).astype(np.uint8)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def extract_sheet(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    columns, rows = 8, 12
    output = Image.new("RGBA", image.size, (0, 0, 0, 0))
    for row in range(rows):
        for column in range(columns):
            box = (
                round(column * image.width / columns),
                round(row * image.height / rows),
                round((column + 1) * image.width / columns),
                round((row + 1) * image.height / rows),
            )
            output.alpha_composite(extract_cell(image.crop(box)), (box[0], box[1]))
    output.save(destination)


def main() -> None:
    for source_name, destination_name in SHEETS:
        extract_sheet(ASSETS / source_name, ASSETS / destination_name)
    print("FOLHAS_RETRO_16BIT_EXTRAIDAS")


if __name__ == "__main__":
    main()
