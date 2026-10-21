"""Remove somente o fogo fixo das piras do Egito aprovado.

A versão limpa criada por edição de imagem é usada apenas como fonte local de
restauração. O mapa aprovado continua sendo a base; duas máscaras pequenas e
suavizadas substituem os pixels das chamas, sem trocar pistas ou arquitetura.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "prontos_1280x720" / "02_egito_escavacao_helix_entrada_unica_v4.png"
CLEAN_REFERENCE = ROOT / "variantes_imagegen" / "02_egito_piras_apagadas_imagegen_1280x720.png"
OUTPUT = ROOT / "prontos_1280x720" / "02_egito_escavacao_helix_piras_apagadas_v5.png"


def restore_region(
    base: Image.Image,
    clean: Image.Image,
    box: tuple[int, int, int, int],
    polygon: list[tuple[int, int]],
) -> None:
    left, top, right, bottom = box
    patch = clean.crop(box)
    mask = Image.new("L", patch.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(x - left, y - top) for x, y in polygon], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3.0))
    base.paste(patch, (left, top), mask)


def main() -> int:
    base = Image.open(SOURCE).convert("RGB")
    clean = Image.open(CLEAN_REFERENCE).convert("RGB")
    if base.size != (1280, 720) or clean.size != base.size:
        raise ValueError("As duas referências precisam estar em 1280x720.")

    restore_region(
        base,
        clean,
        (968, 136, 1038, 214),
        [(980, 147), (1022, 145), (1030, 188), (1024, 207), (980, 210), (972, 186)],
    )
    restore_region(
        base,
        clean,
        (1178, 262, 1260, 356),
        [(1190, 276), (1246, 274), (1255, 326), (1248, 350), (1189, 352), (1182, 316)],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    base.save(OUTPUT, optimize=True)
    print(f"OK: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
