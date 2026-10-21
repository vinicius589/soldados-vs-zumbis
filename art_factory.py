"""Creates the original PNG sprite set shipped with Soldados vs Zumbis.

Run once after installing pygame-ce.  The game already includes the resulting
PNGs; this script exists so that the illustrations remain reproducible.
"""
from __future__ import annotations

import math
import os
import random

import pygame


ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
UNITS = [
    "fuzileiro", "tenente", "general", "bombardeiro", "sniper", "morteiro",
    "rambo", "forcas_especiais", "engenheiro", "lanca_chamas", "escopeteiro",
    "operador_radio", "operador_drone", "buggy",
    "lancha_patrulha", "submarino", "bomba_agua", "mina", "ferramenta_medica",
]
ZOMBIES = [
    "caminhante", "corredor", "bruto", "rastejante", "toxico", "blindado",
    "divisor", "feral", "gritador", "cuspidor", "pulador", "necromante",
    "sandstalker", "nadador", "tide_brute", "conehead",
    "bandeireiro", "porta_escudo", "escavadeira", "doutor_zumbi",
    "general_morto", "mutante_titan",
]


def put_text(surface: pygame.Surface, text: str, pos: tuple[int, int], size: int, color=(245, 239, 212)):
    font = pygame.font.SysFont("arial", size, bold=True)
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=pos))


def poly(surface, color, points, outline=(18, 25, 25), width=2):
    pygame.draw.polygon(surface, outline, points)
    pygame.draw.polygon(surface, color, points)
    if width:
        pygame.draw.lines(surface, outline, True, points, width)


def shade_circle(surface, center, radius, color, edge=(18, 25, 25)):
    pygame.draw.circle(surface, edge, center, radius + 2)
    pygame.draw.circle(surface, color, center, radius)
    pygame.draw.circle(surface, tuple(min(255, c + 36) for c in color), (center[0] - radius // 3, center[1] - radius // 3), max(2, radius // 3))


def soldier_sprite(name: str, index: int) -> pygame.Surface:
    s = pygame.Surface((128, 144), pygame.SRCALPHA)
    rng = random.Random(700 + index)
    olive = [(62, 94, 55), (51, 77, 67), (91, 87, 49), (63, 79, 89)][index % 4]
    accent = [(212, 164, 52), (81, 164, 214), (226, 110, 49), (161, 83, 178)][index % 4]
    skin = (211, 150, 102)
    # soft cast shadow
    pygame.draw.ellipse(s, (0, 0, 0, 74), (18, 126, 88, 11))
    if name == "buggy":
        poly(s, olive, [(15, 101), (96, 101), (111, 121), (26, 124)])
        pygame.draw.rect(s, (31, 43, 42), (30, 85, 60, 22), border_radius=5)
        pygame.draw.rect(s, (85, 111, 90), (44, 73, 35, 16), border_radius=3)
        for x in (31, 92):
            shade_circle(s, (x, 123), 11, (36, 40, 41))
            pygame.draw.circle(s, (178, 139, 63), (x, 123), 4)
        pygame.draw.line(s, (24, 28, 28), (78, 78), (122, 59), 7)
        pygame.draw.circle(s, accent, (122, 59), 5)
        return s
    if name == "lancha_patrulha":
        poly(s, (49, 89, 102), [(8, 105), (118, 105), (101, 130), (25, 130)])
        pygame.draw.rect(s, olive, (36, 82, 48, 24), border_radius=6)
        pygame.draw.polygon(s, (168, 198, 203), [(52, 82), (70, 82), (75, 99), (48, 99)])
        pygame.draw.line(s, (21, 31, 34), (89, 81), (117, 61), 6)
        return s
    if name == "submarino":
        pygame.draw.ellipse(s, (23, 34, 39), (13, 73, 103, 46))
        pygame.draw.ellipse(s, (52, 93, 101), (16, 76, 97, 39))
        pygame.draw.rect(s, (52, 93, 101), (56, 58, 25, 21), border_radius=5)
        pygame.draw.line(s, (29, 46, 49), (68, 58), (68, 40), 5)
        pygame.draw.circle(s, (234, 187, 54), (100, 93), 5)
        return s
    if name == "bomba_agua":
        shade_circle(s, (62, 88), 37, (42, 89, 104))
        pygame.draw.rect(s, (57, 72, 73), (56, 38, 13, 20), border_radius=3)
        pygame.draw.circle(s, accent, (62, 37), 7)
        for a in range(0, 360, 45):
            x, y = 62 + int(math.cos(math.radians(a)) * 40), 88 + int(math.sin(math.radians(a)) * 40)
            pygame.draw.line(s, (128, 181, 190), (62, 88), (x, y), 3)
        return s
    if name == "mina":
        shade_circle(s, (63, 103), 27, (63, 80, 67))
        for a in range(0, 360, 45):
            x1, y1 = 63 + int(math.cos(math.radians(a)) * 27), 103 + int(math.sin(math.radians(a)) * 27)
            x2, y2 = 63 + int(math.cos(math.radians(a)) * 38), 103 + int(math.sin(math.radians(a)) * 38)
            pygame.draw.line(s, (33, 41, 36), (x1, y1), (x2, y2), 6)
        pygame.draw.circle(s, accent, (63, 103), 7)
        return s
    if name == "ferramenta_medica":
        pygame.draw.rect(s, (224, 225, 209), (27, 62, 72, 54), border_radius=9)
        pygame.draw.rect(s, (103, 45, 42), (54, 69, 18, 40), border_radius=2)
        pygame.draw.rect(s, (103, 45, 42), (43, 80, 40, 18), border_radius=2)
        pygame.draw.rect(s, (86, 66, 45), (45, 48, 36, 17), border_radius=4)
        return s
    # human figure
    pygame.draw.rect(s, (28, 37, 35), (46, 104, 15, 25), border_radius=4)
    pygame.draw.rect(s, (28, 37, 35), (70, 104, 15, 25), border_radius=4)
    pygame.draw.ellipse(s, (19, 27, 25), (38, 124, 31, 8))
    pygame.draw.ellipse(s, (19, 27, 25), (63, 124, 31, 8))
    pygame.draw.rect(s, olive, (38, 67, 51, 44), border_radius=10)
    pygame.draw.rect(s, (35, 49, 42), (44, 76, 39, 26), border_radius=5)
    pygame.draw.rect(s, accent, (46, 82, 35, 5), border_radius=2)
    shade_circle(s, (63, 53), 20, skin)
    pygame.draw.rect(s, (34, 54, 42), (39, 37, 48, 15), border_radius=7)
    pygame.draw.arc(s, (23, 33, 30), (37, 33, 53, 32), math.pi, math.tau, 3)
    pygame.draw.circle(s, (25, 31, 28), (55, 56), 3)
    pygame.draw.circle(s, (25, 31, 28), (72, 56), 3)
    # specialty devices and weapon, all original silhouettes
    weapon = (30, 38, 39)
    if name == "morteiro":
        pygame.draw.line(s, weapon, (91, 79), (106, 37), 10)
        pygame.draw.circle(s, (78, 79, 72), (106, 37), 7)
    elif name == "lanca_chamas":
        pygame.draw.rect(s, (117, 78, 44), (32, 77, 13, 24), border_radius=3)
        pygame.draw.line(s, weapon, (76, 80), (117, 70), 7)
        pygame.draw.circle(s, (242, 116, 46), (118, 70), 7)
    elif name == "operador_radio":
        pygame.draw.rect(s, (37, 49, 45), (31, 71, 16, 26), border_radius=3)
        pygame.draw.line(s, (36, 40, 42), (38, 72), (29, 46), 3)
        pygame.draw.circle(s, accent, (76, 78), 5)
    elif name == "operador_drone":
        pygame.draw.circle(s, (42, 57, 61), (101, 53), 10)
        pygame.draw.line(s, (42, 57, 61), (88, 40), (114, 66), 3)
        pygame.draw.line(s, (42, 57, 61), (114, 40), (88, 66), 3)
    elif name == "engenheiro":
        pygame.draw.rect(s, (202, 163, 54), (42, 34, 43, 13), border_radius=5)
        pygame.draw.line(s, (46, 42, 37), (80, 78), (111, 104), 6)
    else:
        length = 50 if name == "sniper" else 41
        pygame.draw.line(s, weapon, (76, 80), (76 + length, 69), 7)
        pygame.draw.line(s, (86, 94, 86), (93, 79), (106, 91), 2)
        if name == "bombardeiro":
            shade_circle(s, (108, 69), 11, (103, 49, 41))
        if name == "rambo":
            pygame.draw.rect(s, (116, 38, 34), (37, 48, 52, 5))
    for _ in range(4):
        x, y = rng.randint(43, 84), rng.randint(72, 102)
        pygame.draw.circle(s, tuple(max(0, c - 14) for c in olive), (x, y), 2)
    return s


def zombie_sprite(name: str, index: int) -> pygame.Surface:
    s = pygame.Surface((128, 144), pygame.SRCALPHA)
    rng = random.Random(1800 + index)
    skin = [(105, 155, 137), (106, 132, 112), (113, 151, 145), (127, 142, 106)][index % 4]
    cloth = [(57, 68, 67), (63, 58, 72), (77, 59, 53), (54, 74, 85)][index % 4]
    pygame.draw.ellipse(s, (0, 0, 0, 74), (14, 127, 94, 10))
    # bosses are visibly bigger
    giant = name in {"bruto", "tide_brute", "mutante_titan"}
    scale = 1.25 if giant else 1.0
    cx = 62
    torso = pygame.Rect(int(cx - 28 * scale), int(71 * scale), int(56 * scale), int(46 * scale))
    pygame.draw.rect(s, (22, 31, 29), torso.inflate(4, 4), border_radius=12)
    pygame.draw.rect(s, cloth, torso, border_radius=10)
    pygame.draw.line(s, (37, 52, 42), (torso.left + 9, torso.top + 10), (torso.right - 9, torso.bottom - 9), 3)
    head_r = int(23 * scale)
    hy = int(53 * scale)
    shade_circle(s, (cx, hy), head_r, skin)
    # torn hair / ear shapes
    pygame.draw.polygon(s, (33, 42, 36), [(cx - head_r, hy - 7), (cx - head_r + 8, hy - head_r - 6), (cx - 2, hy - head_r + 3)])
    pygame.draw.circle(s, skin, (cx - head_r, hy + 5), 6)
    pygame.draw.circle(s, skin, (cx + head_r, hy + 5), 6)
    for eye in (cx - 8, cx + 9):
        pygame.draw.circle(s, (34, 40, 37), (eye, hy), 6)
        pygame.draw.circle(s, (239, 223, 133), (eye, hy), 3)
    pygame.draw.arc(s, (47, 42, 36), (cx - 10, hy + 5, 23, 16), 0, math.pi, 2)
    # legs
    pygame.draw.line(s, (39, 48, 43), (cx - 14, torso.bottom - 5), (cx - 22, 132), 12)
    pygame.draw.line(s, (39, 48, 43), (cx + 13, torso.bottom - 5), (cx + 23, 132), 12)
    # hands / arms
    pygame.draw.line(s, skin, (torso.left + 5, torso.top + 15), (torso.left - 13, torso.top + 36), 12)
    pygame.draw.line(s, skin, (torso.right - 5, torso.top + 17), (torso.right + 18, torso.top + 27), 12)
    if name == "rastejante":
        s = pygame.transform.smoothscale(s, (128, 100))
        target = pygame.Surface((128, 144), pygame.SRCALPHA); target.blit(s, (0, 39)); return target
    if name == "corredor":
        pygame.draw.line(s, (33, 42, 37), (42, 118), (23, 130), 8)
    if name == "toxico":
        for p in [(32, 92), (50, 113), (89, 85), (99, 111)]:
            shade_circle(s, p, 5, (154, 210, 54))
    if name == "blindado":
        pygame.draw.rect(s, (67, 85, 89), (31, 70, 64, 29), border_radius=5)
        pygame.draw.line(s, (143, 160, 154), (38, 79), (85, 91), 3)
        pygame.draw.rect(s, (64, 76, 76), (38, 26, 48, 13), border_radius=5)
    if name == "divisor":
        pygame.draw.line(s, (183, 98, 65), (62, 26), (62, 77), 4)
    if name == "feral":
        for x in (39, 56, 73, 87): pygame.draw.line(s, (40, 36, 31), (x, 38), (x + 4, 26), 4)
    if name == "gritador":
        pygame.draw.ellipse(s, (46, 33, 31), (50, 61, 25, 20))
        for r in (10, 17): pygame.draw.arc(s, (211, 112, 74), (47-r, 64-r//2, 31+2*r, 18+r), -1, 1, 2)
    if name == "cuspidor":
        pygame.draw.circle(s, (178, 222, 63), (95, 65), 8)
        pygame.draw.line(s, (178, 222, 63), (102, 65), (122, 76), 4)
    if name == "pulador":
        pygame.draw.line(s, (124, 76, 38), (23, 112), (10, 72), 5)
        pygame.draw.line(s, (124, 76, 38), (99, 114), (117, 79), 5)
    if name == "necromante":
        pygame.draw.polygon(s, (68, 50, 87), [(39, 45), (61, 12), (88, 45)])
        pygame.draw.line(s, (77, 50, 46), (97, 84), (119, 43), 5)
    if name == "sandstalker":
        pygame.draw.rect(s, (181, 139, 72), (32, 64, 61, 49), border_radius=12)
        pygame.draw.circle(s, (222, 185, 98), (62, 44), 15)
    if name == "nadador":
        pygame.draw.ellipse(s, (51, 143, 183), (21, 112, 88, 18))
        pygame.draw.arc(s, (172, 232, 244), (20, 105, 90, 20), 0, math.pi, 2)
    if name == "conehead":
        pygame.draw.polygon(s, (226, 125, 46), [(42, 35), (62, 2), (82, 35)])
    if name == "bandeireiro":
        pygame.draw.line(s, (65, 42, 31), (103, 34), (103, 123), 4)
        pygame.draw.polygon(s, (137, 54, 49), [(102, 38), (75, 48), (102, 63)])
    if name == "porta_escudo":
        poly(s, (82, 99, 103), [(84, 68), (117, 80), (113, 125), (81, 119)])
    if name == "escavadeira":
        pygame.draw.line(s, (86, 61, 45), (94, 86), (124, 129), 7)
        pygame.draw.rect(s, (115, 109, 82), (108, 116, 20, 14), border_radius=3)
    if name == "doutor_zumbi":
        pygame.draw.rect(s, (199, 199, 178), (39, 72, 47, 44), border_radius=7)
        pygame.draw.line(s, (199, 199, 178), (37, 68), (90, 68), 4)
    if name == "general_morto":
        pygame.draw.rect(s, (37, 83, 74), (31, 68, 63, 48), border_radius=9)
        pygame.draw.rect(s, (34, 49, 43), (35, 29, 57, 13), border_radius=4)
        pygame.draw.circle(s, (216, 171, 56), (61, 84), 5)
    if name == "mutante_titan":
        for p in [(37, 84), (95, 88), (51, 107), (83, 115)]: shade_circle(s, p, 6, (153, 197, 68))
    for _ in range(3):
        x, y = rng.randint(35, 90), rng.randint(72, 110)
        pygame.draw.circle(s, tuple(max(0, c - 20) for c in cloth), (x, y), 2)
    return s


def terrain_tile(key: str) -> pygame.Surface:
    s = pygame.Surface((160, 104), pygame.SRCALPHA)
    palettes = {
        "city": ((62, 66, 67), (139, 145, 142), (34, 40, 41)),
        "desert": ((169, 117, 60), (220, 171, 86), (116, 77, 44)),
        "beach": ((46, 142, 166), (175, 227, 220), (125, 90, 54)),
    }
    base, light, dark = palettes[key]
    s.fill(base)
    rng = random.Random(key)
    for i in range(28):
        x, y = rng.randrange(160), rng.randrange(104)
        if key == "beach":
            pygame.draw.arc(s, light, (x, y, rng.randrange(12, 31), 7), 0, math.pi, 2)
        elif key == "desert":
            pygame.draw.line(s, dark, (x, y), (x + rng.randrange(-7, 8), y + rng.randrange(-3, 5)), 1)
        else:
            pygame.draw.line(s, light, (x, y), (x + rng.randrange(-3, 4), y - rng.randrange(2, 8)), 1)
    pygame.draw.rect(s, dark, s.get_rect(), 3)
    return s


def main():
    os.makedirs(os.path.join(ASSETS, "units"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS, "zombies"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS, "terrain"), exist_ok=True)
    pygame.init(); pygame.font.init()
    for i, name in enumerate(UNITS):
        pygame.image.save(soldier_sprite(name, i), os.path.join(ASSETS, "units", f"{name}.png"))
    for i, name in enumerate(ZOMBIES):
        pygame.image.save(zombie_sprite(name, i), os.path.join(ASSETS, "zombies", f"{name}.png"))
    for key in ("city", "desert", "beach"):
        pygame.image.save(terrain_tile(key), os.path.join(ASSETS, "terrain", f"{key}.png"))
    pygame.quit()
    print("Original PNG sprite set generated.")


if __name__ == "__main__":
    main()
