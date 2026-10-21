"""Galeria executável dos cenários animados da Beta 4.

O arquivo é também um ensaio isolado: nenhuma dessas mudanças entra no jogo
principal antes da aprovação visual do usuário.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pygame


WIDTH, HEIGHT = 1280, 720
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "prontos_1280x720"
AMBIENT_ASSETS = ROOT / "animacao_ambiental"
PIXEL_ROOT = ROOT.parent / "PIXEL_ART_SPRITES_BETA4" / "frames_sem_chroma"
SCENES = [
    ("NOVA YORK — TERMINAL FÉLIX-13", "01_nova_york_terminal_helix_entrada_unica_v4.png", "cidade"),
    ("EGITO — ESCAVAÇÃO FÉLIX DE KHEPRA", "02_egito_escavacao_helix_piras_apagadas_v5.png", "egito"),
    ("MINAS GERAIS — CACHOEIRA FÉLIX", "03_minas_cachoeira_helix_entrada_unica_v4.png", "minas"),
]

LANE_CENTERS = {
    # Centro geométrico entre as divisórias; na cidade coincide com o tracejado.
    "cidade": (280, 368, 458, 553),
    "egito": (270, 366, 462, 558),
    "minas": (239, 327, 427, 529),
}

AMBIENT_ANCHORS = {
    # Espaços vazios no piso das bases: nunca sobre torre, teto ou equipamento.
    # Nova York: corredor superior marcado entre a barraca e a mureta. O ponto
    # é o chão sob os pés, antes das caixas da borda direita.
    "cidade": (35, 455),
    "egito": (80, 400),
    "minas": (80, 312),
}

CITY_WHISTLE_TIMELINE = (0, 0, 0, 1, 2, 3, 4, 5, 5, 6, 7, 7, 0, 0, 0, 0)
REGIONAL_SALUTE_TIMELINE = (0, 0, 1, 2, 3, 4, 4, 4, 5, 6, 7, 7, 0, 0)
DESERT_BRAZIER_ANCHORS = ((997, 208), (1239, 354))

DEFENSE_START_X = {
    # Recuados para o início real de cada faixa; o Y permanece no eixo central.
    "cidade": (215, 215, 215, 215),
    "egito": (215, 215, 215, 215),
    "minas": (215, 215, 215, 215),
}

# Último ponto ainda pertencente à faixa jogável. As defesas atravessam apenas
# o terreno, desaparecendo antes da entrada/cachoeira em vez de invadir o
# cenário decorativo do lado inimigo.
DEFENSE_END_X = {
    "cidade": (1082, 1082, 1082, 1082),
    "egito": (1040, 1040, 1040, 1040),
    "minas": (1088, 1088, 1088, 1088),
}

# Ponto de surgimento lógico. O fundo V4 terá uma entrada física ao redor
# desses pontos; os zumbis nunca nascerão fora da própria faixa.
ZOMBIE_ENTRY_X = {
    "cidade": 1210,
    "egito": 1200,
    "minas": 1195,
}


@dataclass
class AmbientPixel:
    x: float
    y: float
    speed: float
    phase: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--scene", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--trigger-defense", action="store_true")
    parser.add_argument("--trigger-horde", action="store_true")
    parser.add_argument("--trigger-boss", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def remove_green_chroma(surface: pygame.Surface, *, black_limit: int = 24) -> pygame.Surface:
    """Remove apenas o fundo uniforme conectado às bordas.

    Além do chroma verde, algumas folhas geradas vieram com preto puro. O
    componente conectado à borda é removido sem apagar contornos pretos nem
    detalhes verdes protegidos dentro da silhueta.
    """
    clean = surface.convert_alpha()
    rgb = pygame.surfarray.array3d(clean)
    red = rgb[:, :, 0].astype(np.float32)
    green_channel = rgb[:, :, 1].astype(np.float32)
    blue = rgb[:, :, 2].astype(np.float32)
    green_candidate = (
        (green_channel > 55)
        & (green_channel > red * 1.05 + 8)
        & (green_channel > blue * 1.03 + 6)
    )
    black_candidate = (
        (red < black_limit)
        & (green_channel < black_limit)
        & (blue < black_limit)
    )
    candidate = green_candidate | black_candidate
    candidate_surface = pygame.Surface(clean.get_size(), pygame.SRCALPHA)
    candidate_alpha = pygame.surfarray.pixels_alpha(candidate_surface)
    candidate_alpha[:, :] = candidate.astype(np.uint8) * 255
    del candidate_alpha
    candidate_mask = pygame.mask.from_surface(candidate_surface, threshold=1)
    border = pygame.mask.Mask(clean.get_size())
    border.draw(pygame.mask.Mask((clean.get_width(), 2), fill=True), (0, 0))
    border.draw(pygame.mask.Mask((clean.get_width(), 2), fill=True), (0, clean.get_height() - 2))
    border.draw(pygame.mask.Mask((2, clean.get_height()), fill=True), (0, 0))
    border.draw(pygame.mask.Mask((2, clean.get_height()), fill=True), (clean.get_width() - 2, 0))
    background = pygame.mask.Mask(clean.get_size())
    for component in candidate_mask.connected_components(minimum=8):
        if component.overlap(border, (0, 0)) is not None:
            background.draw(component, (0, 0))
    background_surface = background.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(0, 0, 0, 0),
    )
    remove = pygame.surfarray.array_alpha(background_surface) > 0
    alpha = pygame.surfarray.pixels_alpha(clean)
    alpha[remove] = 0
    del alpha
    return clean


def split_sheet(
    path: Path,
    columns: int,
    rows: int,
    *,
    black_limit: int = 24,
    clean_background: bool = True,
) -> list[list[pygame.Surface]]:
    loaded = pygame.image.load(str(path))
    if clean_background:
        sheet = remove_green_chroma(loaded, black_limit=black_limit)
    else:
        # Assets RGBA já transparentes não passam pelo chroma. Isso preserva
        # uniformes verdes e chamas verdes que poderiam ser confundidos com o
        # fundo durante a limpeza.
        sheet = loaded.convert_alpha()
    cell_w = sheet.get_width() // columns
    cell_h = sheet.get_height() // rows
    result: list[list[pygame.Surface]] = []
    for row in range(rows):
        row_frames = []
        for column in range(columns):
            rect = pygame.Rect(column * cell_w, row * cell_h, cell_w, cell_h)
            row_frames.append(sheet.subsurface(rect).copy())
        result.append(row_frames)
    return result


def load_frames(folder: Path) -> list[pygame.Surface]:
    return [pygame.image.load(str(path)).convert_alpha() for path in sorted(folder.glob("frame_*.png"))]


def fit(surface: pygame.Surface, width: int, height: int) -> pygame.Surface:
    factor = min(width / surface.get_width(), height / surface.get_height())
    size = (max(1, round(surface.get_width() * factor)), max(1, round(surface.get_height() * factor)))
    return pygame.transform.smoothscale(surface, size)


def fit_actor(surface: pygame.Surface, body_height: int) -> pygame.Surface:
    """Iguala a altura do corpo sem deformar a largura do uniforme."""
    components = pygame.mask.from_surface(surface, threshold=8).get_bounding_rects()
    if not components:
        return surface
    body = max(components, key=lambda rect: rect.width * rect.height)
    factor = body_height / max(1, body.height)
    return pygame.transform.scale(
        surface,
        (
            max(1, round(surface.get_width() * factor)),
            max(1, round(surface.get_height() * factor)),
        ),
    )


def trim(surface: pygame.Surface, padding: int = 2) -> pygame.Surface:
    rect = surface.get_bounding_rect(min_alpha=10)
    rect.inflate_ip(padding * 2, padding * 2)
    rect = rect.clip(surface.get_rect())
    return surface.subsurface(rect).copy()


def alpha_base_point(surface: pygame.Surface, min_alpha: int = 10) -> tuple[int, int]:
    """Retorna o centro do ponto onde um sprite opaco toca a superfície.

    Usar ``rect.midbottom`` funciona apenas quando o desenho é simétrico dentro
    do quadro. As chamas balançam e têm fagulhas laterais; por isso, o centro do
    retângulo muda visualmente. O pequeno trecho inferior opaco é estável e
    representa o pé real da chama que precisa permanecer preso à taça.
    """
    bounds = surface.get_bounding_rect(min_alpha=min_alpha)
    if bounds.width <= 0 or bounds.height <= 0:
        return surface.get_width() // 2, surface.get_height()

    alpha = pygame.surfarray.array_alpha(surface)
    band_height = max(3, round(bounds.height * 0.08))
    band_top = max(bounds.top, bounds.bottom - band_height)
    band = alpha[bounds.left : bounds.right, band_top : bounds.bottom]
    opaque_x, opaque_y = np.nonzero(band >= min_alpha)
    if opaque_x.size == 0:
        return bounds.centerx, bounds.bottom

    # A mediana não é puxada por uma fagulha isolada. Dar mais peso às linhas
    # baixas mantém o encaixe firme mesmo quando a língua de fogo se inclina.
    absolute_y = opaque_y + band_top
    weights = 1.0 + (absolute_y - band_top)
    base_x = bounds.left + round(float(np.average(opaque_x, weights=weights)))
    return base_x, bounds.bottom


def normalize_sequence(frames: list[pygame.Surface], padding: int = 3) -> list[pygame.Surface]:
    """Usa o mesmo recorte em toda a sequência para impedir saltos do pivô."""
    bounds = [frame.get_bounding_rect(min_alpha=10) for frame in frames]
    union = bounds[0].unionall(bounds[1:])
    union.inflate_ip(padding * 2, padding * 2)
    union = union.clip(frames[0].get_rect())
    return [frame.subsurface(union).copy() for frame in frames]


def boost_alpha(surface: pygame.Surface, factor: float) -> pygame.Surface:
    """Reforça a densidade de uma textura sem criar contorno geométrico."""
    result = surface.copy()
    alpha = pygame.surfarray.pixels_alpha(result)
    amplified = np.minimum(255, alpha.astype(np.float32) * factor).astype(np.uint8)
    alpha[:, :] = amplified
    del alpha
    return result


def make_fog_texture(seed: int, width: int = 180, height: int = 120) -> pygame.Surface:
    """Cria um volume orgânico; não deixa círculos ou formas geométricas visíveis."""
    rng = random.Random(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    density = np.zeros((height, width), dtype=np.float32)
    for _ in range(13):
        cx = rng.uniform(18, width - 18)
        cy = rng.uniform(18, height - 18)
        sx = rng.uniform(20, 48)
        sy = rng.uniform(13, 34)
        density += np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) * 1.7)
    density /= max(0.001, float(density.max()))
    density = np.clip((density - 0.12) * 74, 0, 58).astype(np.uint8)
    texture = pygame.Surface((width, height), pygame.SRCALPHA)
    texture.fill((68, 238, 126, 0))
    alpha = pygame.surfarray.pixels_alpha(texture)
    alpha[:, :] = density.T
    del alpha
    return texture


def make_dust_texture(seed: int, width: int = 280, height: int = 138) -> pygame.Surface:
    """Cria massas orgânicas de areia, sem círculos ou riscos geométricos."""
    rng = random.Random(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    density = np.zeros((height, width), dtype=np.float32)
    for _ in range(18):
        cx = rng.uniform(20, width - 20)
        cy = rng.uniform(16, height - 16)
        sx = rng.uniform(24, 70)
        sy = rng.uniform(12, 34)
        density += np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) * 1.8)
    density /= max(0.001, float(density.max()))
    # A textura já carrega sua própria transparência. Valores muito baixos
    # desapareciam sobre a paleta ocre do fundo e faziam a animação existir
    # apenas matematicamente, sem leitura visual.
    density = np.clip((density - 0.08) * 142, 0, 118).astype(np.uint8)
    texture = pygame.Surface((width, height), pygame.SRCALPHA)
    texture.fill((218, 151, 62, 0))
    alpha = pygame.surfarray.pixels_alpha(texture)
    alpha[:, :] = density.T
    del alpha
    return texture


class ScenarioGallery:
    def __init__(self, headless: bool = False, scene: int = 1) -> None:
        pygame.init()
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Soldados vs Zumbis — Cenários animados Beta 4")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 15)
        self.index = scene - 1
        self.elapsed = 0.0
        self.boss_timer = 0.0
        self.boss_active = False
        self.horde_active = False
        self.horde_flame = 0.0
        self.defense_timer = -1.0
        self.defense_duration = 4.4
        self.selected_lane = 0
        self.notice = ""
        self.notice_timer = 0.0
        self.images = [pygame.image.load(str(ASSETS / file)).convert() for _, file, _ in SCENES]
        general_sheet = split_sheet(
            AMBIENT_ASSETS / "general_saudacao_3x8_v1.png",
            8,
            3,
            clean_background=False,
        )
        self.general = [normalize_sequence(row) for row in general_sheet]
        lieutenant_sheet = split_sheet(
            AMBIENT_ASSETS / "tenente_policia_apito_1x8_v1.png",
            8,
            1,
            clean_background=False,
        )[0]
        self.city_lieutenant = normalize_sequence(lieutenant_sheet)
        beach_officer_sheet = split_sheet(
            AMBIENT_ASSETS / "oficial_marinha_brasil_saudacao_1x8_v2.png",
            8,
            1,
            clean_background=False,
        )[0]
        self.beach_officer = normalize_sequence(beach_officer_sheet)
        self.whistle_font = pygame.font.Font(None, 28)
        mine_sheet = split_sheet(AMBIENT_ASSETS / "mina_aquatica_v2_1x8.png", 8, 1)[0]
        self.aquatic_mine = normalize_sequence(mine_sheet)
        land_charge_sheet = split_sheet(
            AMBIENT_ASSETS / "carga_terrestre_minas_v2_1x8.png",
            8,
            1,
        )[0]
        self.land_charge = normalize_sequence(land_charge_sheet)
        # A folha da cachoeira tem fundo preto comprimido; somente ela precisa
        # do limite mais amplo. Os uniformes escuros mantêm todos os pixels.
        brazier_sheet = split_sheet(
            AMBIENT_ASSETS / "pira_toxica_verde_1x8_v1.png",
            8,
            1,
            clean_background=False,
        )[0]
        self.egypt_brazier_flame = normalize_sequence(brazier_sheet)
        self.tractor = load_frames(PIXEL_ROOT / "veiculos" / "trator_esteiras")
        self.drone = load_frames(PIXEL_ROOT / "veiculos" / "drone_helices")
        self.muzzle = load_frames(PIXEL_ROOT / "vfx" / "muzzle_flash")
        self.explosion = load_frames(PIXEL_ROOT / "vfx" / "explosao")
        self.splash = load_frames(PIXEL_ROOT / "vfx" / "respingo_agua")
        self.flames = load_frames(PIXEL_ROOT / "vfx" / "chamas")
        self.fog_textures = [make_fog_texture(900 + index) for index in range(4)]
        self.dust_textures = [make_dust_texture(1200 + index) for index in range(5)]
        rng = random.Random(731)
        self.pixels = [
            AmbientPixel(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(22, 70), rng.random() * math.tau)
            for _ in range(90)
        ]

    @property
    def kind(self) -> str:
        return SCENES[self.index][2]

    def change(self, direction: int) -> None:
        self.index = (self.index + direction) % len(SCENES)
        self.elapsed = 0.0
        self.boss_timer = 0.0
        self.boss_active = False
        self.horde_active = False
        self.horde_flame = 0.0
        self.defense_timer = -1.0
        self.selected_lane = 0
        self.notice = ""

    def trigger_defense(self) -> None:
        self.defense_timer = 0.0
        self.notice_timer = 0.0

    def toggle_horde(self) -> None:
        """Simula o começo/fim de uma horda no testador de cenários."""
        self.horde_active = not self.horde_active
        self.notice = "HORDA INICIADA" if self.horde_active else "HORDA ENCERRADA"
        self.notice_timer = 1.4

    def toggle_boss(self) -> None:
        """No testador, a segunda chamada representa a derrota do chefe."""
        if self.boss_active:
            self.boss_active = False
            self.boss_timer = 0.0
        else:
            self.boss_active = True
            self.boss_timer = 3.2
            # Todo chefe chega escoltado; portanto, sua entrada também inicia
            # uma horda e acende as piras caso ainda estivessem em repouso.
            self.horde_active = True

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.boss_timer = max(0.0, self.boss_timer - dt)
        self.notice_timer = max(0.0, self.notice_timer - dt)
        flame_target = 1.0 if self.horde_active else 0.0
        flame_rate = 1.15 if flame_target > self.horde_flame else 0.8
        step = flame_rate * dt
        if self.horde_flame < flame_target:
            self.horde_flame = min(flame_target, self.horde_flame + step)
        elif self.horde_flame > flame_target:
            self.horde_flame = max(flame_target, self.horde_flame - step)
        if self.defense_timer >= 0.0:
            self.defense_timer += dt
            if self.defense_timer > self.defense_duration:
                self.defense_timer = -1.0
        for pixel in self.pixels:
            pixel.x -= pixel.speed * dt
            if pixel.x < -20:
                pixel.x = WIDTH + 20

    def draw_whistle_sfx(self, officer_rect: pygame.Rect) -> None:
        """Escreve o som somente enquanto o tenente está soprando o apito."""
        pulse = 1.0 + 0.05 * math.sin(self.elapsed * 18.0)
        fill = self.whistle_font.render("FIIIU!", True, (255, 222, 82))
        outline = self.whistle_font.render("FIIIU!", True, (16, 23, 30))
        size = (round(fill.get_width() * pulse), round(fill.get_height() * pulse))
        fill = pygame.transform.scale(fill, size)
        outline = pygame.transform.scale(outline, size)
        center = (officer_rect.right + 22, officer_rect.top + 18)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)):
            self.screen.blit(outline, outline.get_rect(center=(center[0] + dx, center[1] + dy)))
        self.screen.blit(fill, fill.get_rect(center=center))

    def draw_commander(self) -> None:
        """Anima o comando regional sem transformar o policial em general."""
        if self.kind == "cidade":
            frame_index = CITY_WHISTLE_TIMELINE[
                int(self.elapsed * 3.6) % len(CITY_WHISTLE_TIMELINE)
            ]
            source = self.city_lieutenant[frame_index]
        elif self.kind == "egito":
            frame_index = REGIONAL_SALUTE_TIMELINE[
                int(self.elapsed * 3.0) % len(REGIONAL_SALUTE_TIMELINE)
            ]
            source = self.general[1][frame_index]
        else:
            frame_index = REGIONAL_SALUTE_TIMELINE[
                int(self.elapsed * 3.0) % len(REGIONAL_SALUTE_TIMELINE)
            ]
            source = self.beach_officer[frame_index]
        frame = fit_actor(source, 96)
        x, baseline = AMBIENT_ANCHORS[self.kind]
        # O contato é sempre calculado pelos pés, nunca pelo centro da imagem.
        rect = frame.get_rect(bottomleft=(x, baseline))
        self.screen.blit(frame, rect)
        if self.kind == "cidade" and frame_index in (3, 4, 5):
            self.draw_whistle_sfx(rect)

    def draw_city_rain(self, overlay: pygame.Surface) -> None:
        """Chuva tóxica ativa apenas enquanto o chefe da cidade está vivo."""
        if not self.boss_active:
            return
        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        wash.fill((20, 42, 50, 34))
        overlay.blit(wash, (0, 0))
        for i, pixel in enumerate(self.pixels):
            x = int((pixel.x * 1.9 - self.elapsed * (230 + i % 7 * 13)) % (WIDTH + 80)) - 40
            y = int((pixel.y * 2.3 + self.elapsed * (410 + i % 9 * 17)) % (HEIGHT + 70)) - 35
            length = 9 + i % 8
            pygame.draw.line(overlay, (168, 222, 221, 95 + i % 3 * 25), (x, y), (x - 4, y + length), 1)
        splash_frame = self.splash[int(self.elapsed * 8) % len(self.splash)]
        for i, lane_y in enumerate(LANE_CENTERS["cidade"]):
            x = 260 + int((self.elapsed * (95 + i * 17) + i * 211) % 820)
            splash = fit(splash_frame, 22, 14)
            splash.set_alpha(115)
            overlay.blit(splash, (x, lane_y + 15))

    def draw_egypt_light(self, overlay: pygame.Surface) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 0.45)
        overlay.fill((255, 154, 48, int(5 + pulse * 11)))

    def draw_egypt_entry_mist(self, overlay: pygame.Surface) -> None:
        """Névoa exclusiva do chefe, contida dentro da entrada egípcia."""
        if not self.boss_active:
            return
        for index in range(3):
            fog = boost_alpha(self.fog_textures[index], 1.8)
            fog = pygame.transform.smoothscale(fog, (108 - index * 12, 58 - index * 6))
            fog.fill((128, 255, 116, 205), special_flags=pygame.BLEND_RGBA_MULT)
            fog.set_alpha(38 + index * 8)
            x = 1160 + index * 38 + int(9 * math.sin(self.elapsed * 0.62 + index))
            y = 430 - index * 58 - int(8 * math.sin(self.elapsed * 0.78 + index))
            overlay.blit(fog, (x, y))

        # Durante o aviso, a névoa engrossa dentro da entrada única. Ela não
        # atravessa as pistas nem vira um desenho solto no chão.
        if self.boss_timer > 0.0:
            arrival = 1.0 - self.boss_timer / 3.2
            pulse = 0.5 + 0.5 * math.sin(arrival * math.pi * 8.0)
            for index in range(4):
                fog = boost_alpha(self.fog_textures[(index + 1) % len(self.fog_textures)], 2.6)
                fog = pygame.transform.smoothscale(fog, (132 - index * 10, 72 - index * 5))
                fog.fill((127, 255, 112, 220), special_flags=pygame.BLEND_RGBA_MULT)
                fog.set_alpha(64 + int(pulse * 42) - index * 6)
                x = 1128 + index * 30 + int(8 * math.sin(self.elapsed * 1.1 + index))
                y = 374 - index * 54 - int(9 * math.sin(self.elapsed * 0.9 + index))
                overlay.blit(fog, (x, y))

    def draw_egypt_braziers(self, overlay: pygame.Surface) -> None:
        """Anima as duas piras da fachada sem acrescentar sarcófagos."""
        # A chama reage à horda, não apenas ao chefe. O valor é atualizado por
        # delta time para crescer suavemente e continuar independente do FPS.
        growth = max(0.0, min(1.0, self.horde_flame))
        growth = growth * growth * (3.0 - 2.0 * growth)
        flame_fps = 6.5 + growth * 3.5
        base_index = int(self.elapsed * flame_fps) % len(self.egypt_brazier_flame)
        # Estes pontos são a boca das duas piras pintadas no fundo. Não usar
        # coordenadas das pistas: isso criava uma chama flutuando nas pedras.
        # Cinco pixels acima fazem o pé do fogo entrar na concavidade da taça,
        # sem cobrir a borda frontal ou parecer apoiado fora dela.
        # Centros medidos nos dois pontos azuis marcados pelo usuário.
        # As duas piras agora têm chamas com a mesma largura e altura.
        perspective = (1.0, 1.0)
        width = round(54 + (84 - 54) * growth)
        height = round(84 + (132 - 84) * growth)
        alpha = round(220 + (244 - 220) * growth)
        for offset, (anchor, depth_scale) in enumerate(zip(DESERT_BRAZIER_ANCHORS, perspective)):
            source = self.egypt_brazier_flame[(base_index + offset * 3) % 8]
            # Ambas crescem a partir da taça durante a chegada do chefe.
            flame = fit(source, round(width * depth_scale), round(height * depth_scale))
            flame.set_alpha(alpha)
            base_x, base_y = alpha_base_point(flame)
            overlay.blit(flame, (anchor[0] - base_x, anchor[1] - base_y))

    def draw_minas_boss_storm(self, overlay: pygame.Surface) -> None:
        """Clima do chefe sem redesenhar ou sobrepor a água do cenário."""
        if not self.boss_active:
            return
        storm = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        storm.fill((4, 17, 25, 42))
        overlay.blit(storm, (0, 0))

        # Relâmpago distante representado pela iluminação integral do ambiente,
        # sem riscos, círculos ou símbolos desenhados sobre as pistas.
        cycle = self.elapsed % 3.8
        if cycle < 0.16:
            strength = 1.0 - cycle / 0.16
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((164, 236, 224, int(76 * strength)))
            overlay.blit(flash, (0, 0))

    def draw_ambient(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))
        if self.kind == "cidade":
            # A fumaça verde animada foi retirada de Nova York. A cidade usa
            # apenas a chuva durante o chefe.
            self.draw_city_rain(overlay)
        elif self.kind == "egito":
            self.draw_egypt_light(overlay)
            self.draw_egypt_entry_mist(overlay)
            self.draw_egypt_braziers(overlay)
        else:
            # Minas usa somente a água pintada no fundo aprovado. As antigas
            # camadas de correnteza, respingo e cachoeira foram removidas.
            self.draw_minas_boss_storm(overlay)
        self.screen.blit(overlay, (0, 0))
        self.draw_commander()

    def draw_defense(self) -> None:
        if self.defense_timer < 0.0:
            return
        t = self.defense_timer
        progress = min(1.0, t / self.defense_duration)
        lane_y = LANE_CENTERS[self.kind][self.selected_lane]
        start_x = DEFENSE_START_X[self.kind][self.selected_lane]
        end_x = DEFENSE_END_X[self.kind][self.selected_lane]
        if self.kind == "cidade":
            frame = fit(self.tractor[int(t * 10) % len(self.tractor)], 116, 92)
            x = round(start_x + progress * (end_x - start_x))
            rect = frame.get_rect(center=(x, lane_y))
            if rect.right < end_x:
                self.screen.blit(frame, rect)
        elif self.kind == "egito":
            frame = fit(self.drone[int(t * 12) % len(self.drone)], 104, 78)
            x = round(start_x + progress * (end_x - start_x))
            drone_rect = frame.get_rect(center=(x, lane_y + int(4 * math.sin(t * 7))))
            if drone_rect.right < end_x:
                self.screen.blit(frame, drone_rect)
            if drone_rect.right < end_x and int(t * 12) % 3 == 1:
                flash = fit(self.muzzle[int(t * 18) % len(self.muzzle)], 46, 34)
                flash_rect = flash.get_rect(midleft=(drone_rect.right - 8, drone_rect.centery))
                if flash_rect.right <= end_x:
                    self.screen.blit(flash, flash_rect)
        else:
            is_water_lane = self.selected_lane in (1, 2)
            mine_fps = 16.0
            mine_duration = 8.0 / mine_fps
            if t < mine_duration:
                stage = min(7, int(t * mine_fps))
                if is_water_lane:
                    defense = fit(self.aquatic_mine[stage], 74, 48)
                else:
                    defense = fit(self.land_charge[stage], 66, 44)
                self.screen.blit(defense, defense.get_rect(center=(start_x, lane_y)))
            # O contato dispara a carga quase imediatamente. A pequena margem
            # de 0,12 s existe apenas para o jogador perceber o acionamento.
            if t >= 0.12:
                effect_duration = len(self.explosion) / 7.5
                for column in range(6):
                    local = t - 0.12 - column * 0.07
                    blast_x = start_x + column * 180
                    if local < 0 or local >= effect_duration or blast_x > end_x:
                        continue
                    explosion_index = int(local * 7.5)
                    blast = fit(self.explosion[explosion_index], 116, 100)
                    blast_center = (blast_x, lane_y)
                    self.screen.blit(blast, blast.get_rect(center=blast_center))

    def draw_defense_stations(self) -> None:
        """Mostra cada defesa dentro do começo real de sua própria linha."""
        lanes = LANE_CENTERS[self.kind]
        if self.kind == "cidade":
            station = fit(self.tractor[int(self.elapsed * 6) % len(self.tractor)], 67, 52)
            for lane, lane_y in enumerate(lanes):
                if self.defense_timer >= 0.0 and lane == self.selected_lane:
                    continue
                start_x = DEFENSE_START_X[self.kind][lane]
                self.screen.blit(station, station.get_rect(center=(start_x, lane_y)))
        elif self.kind == "egito":
            station = fit(self.drone[int(self.elapsed * 8) % len(self.drone)], 62, 46)
            for lane, lane_y in enumerate(lanes):
                if self.defense_timer >= 0.0 and lane == self.selected_lane:
                    continue
                start_x = DEFENSE_START_X[self.kind][lane]
                self.screen.blit(station, station.get_rect(center=(start_x, lane_y)))
        else:
            for lane in range(4):
                if self.defense_timer >= 0.0 and lane == self.selected_lane:
                    continue
                lane_y = lanes[lane]
                if lane in (1, 2):
                    station = fit(self.aquatic_mine[int(self.elapsed * 3) % 4], 74, 48)
                else:
                    station = fit(self.land_charge[int(self.elapsed * 3) % 4], 66, 44)
                start_x = DEFENSE_START_X[self.kind][lane]
                self.screen.blit(station, station.get_rect(center=(start_x, lane_y)))

    def draw_boss_arrival(self) -> None:
        if self.boss_timer <= 0:
            return
        progress = 1.0 - self.boss_timer / 3.2
        pulse = (math.sin(progress * math.pi * 7) + 1.0) * 0.5
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((12, 0, 0, 80 + int(70 * pulse)))
        self.screen.blit(shade, (0, 0))
        border = 5 + int(7 * pulse)
        pygame.draw.rect(self.screen, (185, 32, 26), self.screen.get_rect(), border)
        label = self.font.render("CHEFE SE APROXIMA", True, (255, 224, 190))
        panel = pygame.Rect(0, 0, label.get_width() + 70, 62)
        panel.center = (WIDTH // 2, 92)
        pygame.draw.rect(self.screen, (36, 7, 7), panel, border_radius=8)
        pygame.draw.rect(self.screen, (216, 55, 38), panel, 2, border_radius=8)
        self.screen.blit(label, label.get_rect(center=panel.center))

    def draw_hud(self) -> None:
        title = SCENES[self.index][0]
        top = pygame.Surface((WIDTH, 68), pygame.SRCALPHA)
        top.fill((5, 10, 16, 218))
        self.screen.blit(top, (0, 0))
        self.screen.blit(self.font.render(title, True, (245, 247, 235)), (22, 8))
        action = {"cidade": "TRATOR", "egito": "DRONE DE ATAQUE", "minas": "DEFESA DA LINHA"}[self.kind]
        hint = (
            f"← → cenário   |   1–4 linha ({self.selected_lane + 1})   |   "
            f"C {action}   |   H horda   |   B chefe/derrotar   |   ESC sair"
        )
        self.screen.blit(self.small.render(hint, True, (141, 226, 215)), (24, 41))
        if self.notice_timer > 0.0:
            label = self.small.render(self.notice, True, (255, 236, 154))
            panel = label.get_rect(center=(WIDTH // 2, 94)).inflate(24, 14)
            pygame.draw.rect(self.screen, (32, 22, 6), panel, border_radius=6)
            pygame.draw.rect(self.screen, (245, 184, 54), panel, 2, border_radius=6)
            self.screen.blit(label, label.get_rect(center=panel.center))

    def draw(self) -> None:
        shake = int(5 * math.sin(self.elapsed * 42)) if self.boss_timer > 2.1 else 0
        if self.kind == "minas" and self.elapsed % 7.2 < 0.34:
            shake += int(2 * math.sin(self.elapsed * 68))
        self.screen.fill((5, 7, 10))
        self.screen.blit(self.images[self.index], (shake, 0))
        self.draw_ambient()
        self.draw_defense_stations()
        self.draw_defense()
        self.draw_boss_arrival()
        self.draw_hud()
        pygame.display.flip()

    def run(
        self,
        *,
        max_frames: int | None = None,
        screenshot: Path | None = None,
        trigger_defense: bool = False,
        trigger_horde: bool = False,
        trigger_boss: bool = False,
    ) -> int:
        running = True
        rendered = 0
        if trigger_defense:
            if self.kind == "minas":
                self.selected_lane = 1
            self.trigger_defense()
        if trigger_horde:
            self.toggle_horde()
        if trigger_boss:
            self.toggle_boss()
        while running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                        self.change(1)
                    elif event.key in {pygame.K_LEFT, pygame.K_a}:
                        self.change(-1)
                    elif pygame.K_1 <= event.key <= pygame.K_4:
                        self.selected_lane = event.key - pygame.K_1
                    elif event.key == pygame.K_b:
                        self.toggle_boss()
                    elif event.key == pygame.K_c:
                        self.trigger_defense()
                    elif event.key == pygame.K_h:
                        self.toggle_horde()
            self.update(dt)
            self.draw()
            rendered += 1
            if max_frames is not None and rendered >= max_frames:
                if screenshot:
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(screenshot))
                running = False
        pygame.quit()
        return 0


def main() -> int:
    args = parse_args()
    gallery = ScenarioGallery(args.headless, args.scene)
    return gallery.run(
        max_frames=args.frames if args.headless else None,
        screenshot=args.screenshot,
        trigger_defense=args.trigger_defense,
        trigger_horde=args.trigger_horde,
        trigger_boss=args.trigger_boss,
    )


if __name__ == "__main__":
    raise SystemExit(main())
