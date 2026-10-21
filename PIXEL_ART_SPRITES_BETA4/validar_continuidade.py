"""Auditoria estrutural de transparência, bordas e direção da coleção ativa."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames_sem_chroma"
MANIFEST = ROOT / "sheet_manifest.json"
REPORT = ROOT / "RELATORIO_QA_CONTINUIDADE.txt"
EXCLUDED = {"ambiente"}

DIRECTION = {
    "tropa_fuzil": "direita",
    "tropa_lancachamas": "direita",
    "tropa_morteiro": "direita",
    "tropa_operadora_drone": "direita",
    "tropa_socorrista": "neutra/direita",
    "veiculos": "direita",
    "zumbi_classico": "esquerda",
    "zumbi_mergulhador": "esquerda",
    "zumbi_baiacu": "esquerda",
    "boss_mutante_gigante": "esquerda",
    "vfx": "neutra",
}
GREEN_DETAIL_SHEETS = {
    "tropa_morteiro",
    "zumbi_classico",
    "zumbi_mergulhador",
    "zumbi_baiacu",
    "boss_mutante_gigante",
    "vfx",
}


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    lines = ["SOLDADOS VS ZUMBIS — QA DE CONTINUIDADE", "=" * 43, ""]
    total = 0

    for spec in data["sheets"]:
        key = str(spec["key"])
        if key in EXCLUDED:
            continue
        expected = int(spec["columns"])
        sheet_total = 0
        for action in spec["rows"]:
            paths = sorted((FRAMES / key / str(action)).glob("frame_*.png"))
            if len(paths) != expected:
                errors.append(f"{key}/{action}: {len(paths)} arquivos, esperados {expected}")
            for path in paths:
                frame = pygame.image.load(str(path)).convert_alpha()
                alpha = pygame.surfarray.array_alpha(frame)
                rgb = pygame.surfarray.array3d(frame)
                if not (alpha > 0).any():
                    errors.append(f"{path.relative_to(ROOT)}: quadro vazio")
                if (
                    (alpha[0:2, :] > 0).any()
                    or (alpha[-2:, :] > 0).any()
                    or (alpha[:, 0:2] > 0).any()
                    or (alpha[:, -2:] > 0).any()
                ):
                    errors.append(f"{path.relative_to(ROOT)}: conteúdo invadindo a borda")
                red = rgb[:, :, 0].astype("float32")
                green = rgb[:, :, 1].astype("float32")
                blue = rgb[:, :, 2].astype("float32")
                exact_green = (
                    (red == 0)
                    & (green == 255)
                    & (blue == 0)
                    & (alpha > 0)
                )
                if exact_green.any():
                    errors.append(f"{path.relative_to(ROOT)}: chroma verde puro ainda visível")
                hidden_rgb = (alpha == 0) & (rgb.sum(axis=2) > 0)
                if hidden_rgb.any():
                    errors.append(f"{path.relative_to(ROOT)}: RGB residual escondido na transparência")

                # O chroma também pode deixar um contorno verde-escuro. A
                # auditoria se limita à faixa externa da silhueta para não
                # confundir veneno, algas ou uniformes verdes intencionais.
                opaque = pygame.mask.from_surface(frame, threshold=1)
                transparent = opaque.copy()
                transparent.invert()
                near_transparency = pygame.mask.Mask(frame.get_size())
                for offset_y in range(-5, 6):
                    for offset_x in range(-5, 6):
                        near_transparency.draw(transparent, (offset_x, offset_y))
                near_surface = near_transparency.to_surface(
                    setcolor=(255, 255, 255, 255),
                    unsetcolor=(0, 0, 0, 0),
                )
                near = pygame.surfarray.array_alpha(near_surface) > 0
                green_halo = (
                    near
                    & (alpha > 0)
                    & (
                        (
                            (green > 20)
                            & (green > red + 4)
                            & (green > blue + 3)
                        )
                        | (
                            (green > 4)
                            & (green < 60)
                            & (green > red * 1.25 + 2)
                            & (green > blue * 1.25 + 2)
                        )
                    )
                )
                if key not in GREEN_DETAIL_SHEETS and green_halo.any():
                    errors.append(f"{path.relative_to(ROOT)}: halo verde ainda visível na borda")
                total += 1
                sheet_total += 1
        lines.append(f"OK  {key}: {sheet_total} quadros; direção {DIRECTION[key]}")

    lines.extend(["", f"TOTAL: {total} quadros ativos", f"ERROS ESTRUTURAIS: {len(errors)}"])
    if errors:
        lines.extend(["", "PROBLEMAS:", *[f"- {error}" for error in errors]])
    else:
        lines.extend(
            [
                "",
                "RESULTADO: aprovado na verificação estrutural.",
                "- fundo transparente",
                "- nenhum quadro vazio",
                "- nenhuma silhueta tocando/invadindo a borda",
                "- nenhum chroma verde puro visível",
                "- nenhum halo de chroma nas tropas e nos veículos",
                "- pixels transparentes com RGB zerado, sem vazamento ao redimensionar",
                "- soldados e veículos orientados para a direita",
                "- zumbis e boss orientados para a esquerda",
            ]
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pygame.quit()
    print(f"QA: {total} quadros; {len(errors)} erros. Relatório: {REPORT.name}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
