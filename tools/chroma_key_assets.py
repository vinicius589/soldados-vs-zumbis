"""Converte folhas de arte com chroma magenta em PNG RGBA.

O arquivo-fonte gerado é preservado. A borda recebe alfa gradual e
descontaminação de cor para que não reste um halo rosa durante a animação.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
import pygame


KEY = np.array((255.0, 0.0, 255.0), dtype=np.float32)


def smoothstep(low: float, high: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - low) / max(0.001, high - low), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def connected_chroma_background(rgb: np.ndarray) -> np.ndarray:
    """Seleciona apenas o magenta ligado às bordas da folha.

    Tons roxos podem existir dentro de roupa/magia. A conectividade impede
    que esses detalhes internos sejam apagados só por terem matiz semelhante.
    """
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    candidate = (
        (np.minimum(red, blue) > green + 24.0)
        & (np.abs(red - blue) < 128.0)
        & ((red + blue) * 0.5 > 55.0)
    )
    width, height = candidate.shape
    background = np.zeros_like(candidate, dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in (0, height - 1):
            if candidate[x, y] and not background[x, y]:
                background[x, y] = True
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if candidate[x, y] and not background[x, y]:
                background[x, y] = True
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        if x > 0 and candidate[x - 1, y] and not background[x - 1, y]:
            background[x - 1, y] = True
            queue.append((x - 1, y))
        if x + 1 < width and candidate[x + 1, y] and not background[x + 1, y]:
            background[x + 1, y] = True
            queue.append((x + 1, y))
        if y > 0 and candidate[x, y - 1] and not background[x, y - 1]:
            background[x, y - 1] = True
            queue.append((x, y - 1))
        if y + 1 < height and candidate[x, y + 1] and not background[x, y + 1]:
            background[x, y + 1] = True
            queue.append((x, y + 1))
    return background


def convert(source_path: Path, target_path: Path) -> None:
    pygame.init()
    source = pygame.image.load(str(source_path))
    rgb = pygame.surfarray.array3d(source).astype(np.float32)
    width, height = source.get_size()
    border = max(6, min(width, height) // 80)
    border_pixels = np.concatenate(
        (
            rgb[:border].reshape(-1, 3),
            rgb[-border:].reshape(-1, 3),
            rgb[:, :border].reshape(-1, 3),
            rgb[:, -border:].reshape(-1, 3),
        )
    )
    # O gerador pode aproximar #FF00FF como um magenta levemente texturizado.
    # A mediana da moldura estima a cor efetiva sem depender desse desvio.
    effective_key = np.median(border_pixels, axis=0).astype(np.float32)
    distance = np.linalg.norm(rgb - effective_key, axis=2)

    # O miolo perfeitamente magenta some por completo. Pixels misturados pela
    # antisserrilha tornam-se semitransparentes em vez de formar uma borda dura.
    distance_alpha = np.clip((distance - 7.0) / 54.0, 0.0, 1.0)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    magenta_chroma = np.minimum(red, blue) - green
    magenta_brightness = (red + blue) * 0.5
    magenta_balance = np.abs(red - blue)
    background_confidence = (
        smoothstep(72.0, 155.0, magenta_chroma)
        * smoothstep(135.0, 205.0, magenta_brightness)
        * (1.0 - smoothstep(42.0, 112.0, magenta_balance))
    )
    hue_alpha = 1.0 - background_confidence
    alpha_f = np.minimum(distance_alpha, hue_alpha)
    connected_background = connected_chroma_background(rgb)
    alpha_f[connected_background] = 0.0

    # Suaviza somente o primeiro anel externo do recorte; o interior continua
    # opaco e o fundo conectado continua completamente transparente.
    near_background = np.zeros_like(connected_background)
    near_background[1:] |= connected_background[:-1]
    near_background[:-1] |= connected_background[1:]
    near_background[:, 1:] |= connected_background[:, :-1]
    near_background[:, :-1] |= connected_background[:, 1:]
    edge = near_background & ~connected_background
    alpha_f[edge] = np.minimum(alpha_f[edge], np.clip((distance[edge] - 5.0) / 46.0, 0.0, 1.0))
    safe_alpha = np.maximum(alpha_f[..., None], 1.0 / 255.0)
    foreground = (rgb - (1.0 - alpha_f[..., None]) * effective_key) / safe_alpha
    foreground = np.clip(foreground, 0.0, 255.0).astype(np.uint8)
    alpha = np.rint(alpha_f * 255.0).astype(np.uint8)

    output = pygame.Surface(source.get_size(), pygame.SRCALPHA, 32)
    pygame.surfarray.blit_array(output, foreground)
    alpha_view = pygame.surfarray.pixels_alpha(output)
    alpha_view[:] = alpha
    del alpha_view

    target_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(output, str(target_path))
    bounds = output.get_bounding_rect(min_alpha=8)
    print(
        f"CHROMA_OK source={source_path.name} target={target_path.name} "
        f"size={output.get_size()} alpha={int(alpha.min())}-{int(alpha.max())} "
        f"key={tuple(int(v) for v in effective_key)} "
        f"bounds={bounds.x},{bounds.y},{bounds.width},{bounds.height}"
    )
    pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    convert(args.source.resolve(), args.target.resolve())


if __name__ == "__main__":
    main()
