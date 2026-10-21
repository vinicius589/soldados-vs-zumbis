"""Laboratório de aprovação das animações pixel art da Beta 4.

Este programa é deliberadamente independente do jogo principal: ele carrega os
quadros em ``frames/``, reproduz cada sequência usando delta time e salva a
avaliação do usuário em ``REVISAO_DAS_ANIMACOES.json``.

Execute pelo arquivo ``TESTAR_TODAS_AS_ANIMACOES.bat``. Para uma verificação
automatizada sem abrir janela, use ``--headless``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
RAW_FRAMES_ROOT = ROOT / "frames"
CLEAN_FRAMES_ROOT = ROOT / "frames_sem_chroma"
GREEN_DETAIL_SHEETS = {
    "tropa_morteiro",
    "zumbi_classico",
    "zumbi_mergulhador",
    "zumbi_baiacu",
    "boss_mutante_gigante",
    "vfx",
}
FRAMES_ROOT = CLEAN_FRAMES_ROOT if CLEAN_FRAMES_ROOT.is_dir() else RAW_FRAMES_ROOT
MANIFEST_PATH = ROOT / "sheet_manifest.json"
REVIEW_PATH = ROOT / "REVISAO_DAS_ANIMACOES_V2.json"

WIDTH, HEIGHT = 1280, 720
SIDEBAR = pygame.Rect(18, 110, 320, 580)
STAGE = pygame.Rect(354, 110, 908, 430)
FILMSTRIP = pygame.Rect(354, 554, 908, 136)
VISIBLE_ROWS = 15

CHROMA = (0, 255, 0)
BG = (8, 12, 18)
PANEL = (17, 25, 34)
PANEL_2 = (24, 34, 44)
LINE = (56, 74, 86)
WHITE = (239, 244, 241)
MUTED = (155, 169, 176)
CYAN = (82, 224, 204)
GOLD = (244, 187, 65)
GREEN = (64, 204, 120)
RED = (232, 82, 77)


GROUP_LABELS = {
    "ambiente": "CENÁRIO",
    "tropa_fuzil": "TROPAS",
    "tropa_lancachamas": "TROPAS",
    "tropa_morteiro": "TROPAS",
    "tropa_operadora_drone": "TROPAS",
    "tropa_socorrista": "TROPAS",
    "veiculos": "VEÍCULOS",
    "zumbi_classico": "ZUMBIS",
    "zumbi_mergulhador": "ZUMBIS",
    "zumbi_baiacu": "ZUMBIS",
    "boss_mutante_gigante": "CHEFE",
    "vfx": "EFEITOS",
}

PRETTY_NAMES = {
    "ambiente": "Ambiente",
    "tropa_fuzil": "Soldado com fuzil",
    "tropa_lancachamas": "Soldado com lança-chamas",
    "tropa_morteiro": "Operador de morteiro",
    "tropa_operadora_drone": "Operadora de drone",
    "tropa_socorrista": "Socorrista",
    "veiculos": "Veículos e máquinas",
    "zumbi_classico": "Zumbi clássico",
    "zumbi_mergulhador": "Zumbi mergulhador",
    "zumbi_baiacu": "Zumbi baiacu",
    "boss_mutante_gigante": "Boss mutante gigante",
    "vfx": "Efeito visual",
}

ACTION_NAMES = {
    "ondas_mar": "Ondas do mar",
    "agua_trincheira": "Água fluindo",
    "luzes_pier": "Luzes do píer",
    "brilho_caverna": "Brilho da caverna",
    "nevoa": "Névoa dinâmica",
    "relampagos": "Relâmpagos",
    "idle": "Parado / respiração",
    "atirando": "Atirando",
    "disparando": "Disparando",
    "recarregando": "Recarregando",
    "acionando_drone": "Acionando o drone",
    "trocando_bateria": "Trocando a bateria",
    "prestando_socorro": "Prestando socorro",
    "repondo_maleta": "Repondo a maleta",
    "barco_flutuando": "Barco flutuando",
    "submarino_flutuando": "Submarino flutuando",
    "trator_esteiras": "Esteiras do trator",
    "drone_helices": "Hélices do drone",
    "andando": "Andando",
    "atacando": "Atacando",
    "atacando_arpao": "Atacando com arpão",
    "inflando_atacando": "Inflando e atacando",
    "ataque_pesado": "Ataque pesado",
    "morrendo": "Morrendo",
    "muzzle_flash": "Clarão do disparo",
    "chamas": "Chamas contínuas",
    "explosao": "Explosão",
    "respingo_agua": "Respingo de água",
}

ONE_SHOT_ACTIONS = {"morrendo", "explosao", "muzzle_flash", "respingo_agua", "ataque_pesado"}
TRAVEL_ACTIONS = {"andando", "trator_esteiras"}
EXCLUDED_SHEET_KEYS = {"ambiente"}
LEFTWARD_SHEETS = {
    "zumbi_classico",
    "zumbi_mergulhador",
    "zumbi_baiacu",
    "boss_mutante_gigante",
}


@dataclass(slots=True)
class AnimationItem:
    sheet_key: str
    action: str
    frames: list[pygame.Surface]
    source_paths: list[Path]
    group: str

    @property
    def key(self) -> str:
        return f"{self.sheet_key}:{self.action}"

    @property
    def title(self) -> str:
        return PRETTY_NAMES.get(self.sheet_key, self.sheet_key.replace("_", " ").title())

    @property
    def action_title(self) -> str:
        return ACTION_NAMES.get(self.action, self.action.replace("_", " ").title())

    @property
    def one_shot(self) -> bool:
        return self.action in ONE_SHOT_ACTIONS

    @property
    def travels(self) -> bool:
        return self.action in TRAVEL_ACTIONS

    @property
    def moves_left(self) -> bool:
        return self.sheet_key in LEFTWARD_SHEETS

    @property
    def default_fps(self) -> float:
        """Velocidade visual adequada para cada gesto, sem depender do monitor."""
        if self.action in {"recarregando", "trocando_bateria", "repondo_maleta"}:
            return 2.5
        if self.action in {"andando", "trator_esteiras"}:
            return 4.5
        if self.action in {"atacando", "atacando_arpao", "inflando_atacando"}:
            return 4.5
        if self.action in {"disparando", "acionando_drone", "ataque_pesado"}:
            return 4.0
        if self.action == "morrendo":
            return 4.0
        if self.action in {"muzzle_flash", "explosao", "respingo_agua", "chamas"}:
            return 7.0
        return 5.0


@dataclass(slots=True)
class Button:
    rect: pygame.Rect
    text: str
    action: str
    tone: str = "neutral"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Testa todas as animações pixel art da Beta 4.")
    parser.add_argument("--headless", action="store_true", help="Executa uma verificação automática sem janela.")
    parser.add_argument("--frames", type=int, default=45, help="Quantidade de quadros do teste headless.")
    parser.add_argument("--screenshot", type=Path, help="Salva uma captura durante o teste headless.")
    return parser.parse_args()


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifesto não encontrado: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_reviews() -> dict[str, str]:
    try:
        raw = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in raw.items()
        if value in {"aprovada", "ajustar"}
    }


def save_reviews(reviews: dict[str, str]) -> None:
    ordered = dict(sorted(reviews.items()))
    REVIEW_PATH.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_frame(path: Path) -> pygame.Surface:
    source = pygame.image.load(str(path)).convert_alpha()
    if CLEAN_FRAMES_ROOT in path.parents:
        return source
    cleaned = source.copy()
    sheet_key = path.parent.parent.name
    # O fundo não veio apenas em RGB(0, 255, 0): a geração criou dezenas de
    # tons verdes nas bordas e em pequenos bolsões internos. A tolerância é
    # aplicada a TODOS esses pixels, não só à maior região conectada. Assim os
    # riscos neon deixam de acompanhar braços, armas, pernas e silhuetas.
    pygame.transform.threshold(
        cleaned,
        source,
        (*CHROMA, 255),
        threshold=(112, 112, 112, 255),
        set_color=(0, 0, 0, 0),
        set_behavior=1,
        inverse_set=True,
    )
    # Segunda passada: elimina o halo verde escuro de antialias que encosta na
    # transparência. A operação alcança só cinco pixels para dentro da borda;
    # cores verdes internas do personagem (algas, veneno etc.) permanecem.
    opaque = pygame.mask.from_surface(cleaned, threshold=1)
    transparent = opaque.copy()
    transparent.invert()
    near_transparency = pygame.mask.Mask(cleaned.get_size())
    for offset_y in range(-5, 6):
        for offset_x in range(-5, 6):
            near_transparency.draw(transparent, (offset_x, offset_y))
    near_surface = near_transparency.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(0, 0, 0, 0),
    )
    try:
        # Critério relativo: também reconhece o verde escurecido pelo
        # antialias, sem confundir pixels azuis/cinzas apenas por serem escuros.
        rgb = pygame.surfarray.pixels3d(cleaned)
        alpha = pygame.surfarray.pixels_alpha(cleaned)
        red = rgb[:, :, 0].astype("int16")
        green = rgb[:, :, 1].astype("int16")
        blue = rgb[:, :, 2].astype("int16")
        near = pygame.surfarray.array_alpha(near_surface) > 0
        # A regra por proporção alcança também o halo verde quase preto que a
        # geração deixou em cabelos, antenas, hélices e armas. Tons neutros,
        # azuis/cianos e verdes internos fora da borda não são removidos.
        green_spill = (
            near
            & (alpha > 0)
            & (green > 20)
            & (green > red * 1.35 + 3)
            & (green > blue * 1.15 + 2)
        )
        if sheet_key in GREEN_DETAIL_SHEETS:
            green_spill[:] = False
        alpha[green_spill] = 0
        del alpha, rgb
    except (ImportError, ValueError):
        # Fallback sem NumPy: ainda remove a faixa verde mais evidente.
        broad_green = pygame.mask.from_threshold(
            source,
            (*CHROMA, 255),
            threshold=(155, 155, 155, 255),
        )
        edge_spill = broad_green.overlap_mask(near_transparency, (0, 0))
        edge_cutout = edge_spill.to_surface(
            setcolor=(255, 255, 255, 0),
            unsetcolor=(255, 255, 255, 255),
        )
        cleaned.blit(edge_cutout, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Remoção em camadas: ao apagar a primeira borda contaminada, outra faixa
    # verde que estava logo atrás passa a tocar a transparência. Três iterações
    # curtas alcançam esse resíduo sem varrer cores verdes no miolo do desenho.
    for _ in range(3):
        opaque = pygame.mask.from_surface(cleaned, threshold=1)
        transparent = opaque.copy()
        transparent.invert()
        near_transparency = pygame.mask.Mask(cleaned.get_size())
        for offset_y in range(-3, 4):
            for offset_x in range(-3, 4):
                near_transparency.draw(transparent, (offset_x, offset_y))
        near_surface = near_transparency.to_surface(
            setcolor=(255, 255, 255, 255),
            unsetcolor=(0, 0, 0, 0),
        )
        rgb = pygame.surfarray.pixels3d(cleaned)
        alpha = pygame.surfarray.pixels_alpha(cleaned)
        red = rgb[:, :, 0].astype("float32")
        green = rgb[:, :, 1].astype("float32")
        blue = rgb[:, :, 2].astype("float32")
        near = pygame.surfarray.array_alpha(near_surface) > 0
        layered_spill = (
            near
            & (alpha > 0)
            & (green > 20)
            & (green > red * 1.35 + 3)
            & (green > blue * 1.15 + 2)
        )
        if sheet_key in GREEN_DETAIL_SHEETS:
            layered_spill[:] = False
        removed = int(layered_spill.sum())
        alpha[layered_spill] = 0
        del alpha, rgb
        if removed == 0:
            break

    # Soldados e veículos desta coleção não possuem nenhuma peça verde. Neles,
    # qualquer pixel fortemente verde é sobra do chroma e pode ser eliminado
    # em toda a área, inclusive em antenas e frestas que não tocam o exterior.
    if sheet_key not in GREEN_DETAIL_SHEETS:
        rgb = pygame.surfarray.pixels3d(cleaned)
        alpha = pygame.surfarray.pixels_alpha(cleaned)
        red = rgb[:, :, 0].astype("float32")
        green = rgb[:, :, 1].astype("float32")
        blue = rgb[:, :, 2].astype("float32")
        chroma_residue = (
            (alpha > 0)
            & (green > 20)
            & (green > red + 4)
            & (green > blue + 3)
        )
        dark_chroma_residue = (
            (alpha > 0)
            & (green > 4)
            & (green < 60)
            & (green > red * 1.25 + 2)
            & (green > blue * 1.25 + 2)
        )
        alpha[chroma_residue | dark_chroma_residue] = 0
        del alpha, rgb
    # Remove linhas de grade e pequenos pedaços do quadro vizinho. Uma invasão
    # costuma formar um componente desconectado encostado na borda; componentes
    # intencionais no interior (cápsulas, drone, fumaça e detritos) são mantidos.
    alpha = pygame.surfarray.pixels_alpha(cleaned)
    alpha[:2, :] = 0
    alpha[-2:, :] = 0
    alpha[:, :2] = 0
    alpha[:, -2:] = 0
    del alpha
    if path.parent.parent.name != "vfx":
        silhouette = pygame.mask.from_surface(cleaned, threshold=1)
        parts = silhouette.connected_components(minimum=3)
        if parts:
            primary = max(parts, key=pygame.mask.Mask.count)
            primary_size = max(1, primary.count())
            width, height = cleaned.get_size()
            intrusions = pygame.mask.Mask((width, height))
            for part in parts:
                if part is primary:
                    continue
                boxes = part.get_bounding_rects()
                if not boxes:
                    continue
                box = boxes[0]
                touches_edge = (
                    box.left <= 3
                    or box.top <= 3
                    or box.right >= width - 3
                    or box.bottom >= height - 3
                )
                if touches_edge and part.count() < primary_size * 0.35:
                    intrusions.draw(part, (0, 0))
            if intrusions.count():
                intrusion_cutout = intrusions.to_surface(
                    setcolor=(255, 255, 255, 0),
                    unsetcolor=(255, 255, 255, 255),
                )
                cleaned.blit(intrusion_cutout, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Um pixel totalmente transparente ainda pode guardar RGB verde. Embora o
    # alfa o esconda, certos redimensionadores misturam esse RGB com a borda e
    # recriam um risco verde. Zerar os canais invisíveis impede esse vazamento.
    rgb = pygame.surfarray.pixels3d(cleaned)
    alpha_copy = pygame.surfarray.array_alpha(cleaned)
    rgb[alpha_copy == 0] = (0, 0, 0)
    del rgb
    return cleaned


def discover_items(manifest: dict) -> list[AnimationItem]:
    items: list[AnimationItem] = []
    for sheet in manifest.get("sheets", []):
        sheet_key = str(sheet["key"])
        if sheet_key in EXCLUDED_SHEET_KEYS:
            continue
        expected_count = int(sheet["columns"])
        group = GROUP_LABELS.get(sheet_key, "OUTROS")
        for action in sheet["rows"]:
            action_dir = FRAMES_ROOT / sheet_key / str(action)
            paths = sorted(action_dir.glob("frame_*.png"))
            if len(paths) != expected_count:
                raise RuntimeError(
                    f"{sheet_key}/{action}: esperados {expected_count} quadros, "
                    f"mas foram encontrados {len(paths)}."
                )
            items.append(
                AnimationItem(
                    sheet_key=sheet_key,
                    action=str(action),
                    frames=[load_frame(path) for path in paths],
                    source_paths=paths,
                    group=group,
                )
            )
    if not items:
        raise RuntimeError("Nenhuma animação foi encontrada no manifesto.")
    return items


def fit_nearest(surface: pygame.Surface, box: tuple[int, int], zoom: float = 1.0) -> pygame.Surface:
    """Ajusta sem suavização para preservar os pixels da arte 16-bit."""
    width, height = surface.get_size()
    factor = min(box[0] / max(1, width), box[1] / max(1, height)) * zoom
    target = (max(1, round(width * factor)), max(1, round(height * factor)))
    return pygame.transform.scale(surface, target)


def draw_text(
    target: pygame.Surface,
    font: pygame.font.Font,
    value: str,
    color: tuple[int, int, int],
    pos: tuple[int, int],
    *,
    center: bool = False,
) -> pygame.Rect:
    rendered = font.render(value, True, color)
    rect = rendered.get_rect(center=pos) if center else rendered.get_rect(topleft=pos)
    target.blit(rendered, rect)
    return rect


class AnimationLaboratory:
    def __init__(self, *, headless: bool = False) -> None:
        pygame.init()
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Soldados vs Zumbis — Validação das Animações Beta 4")
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("arial", 27, bold=True)
        self.font_h2 = pygame.font.SysFont("arial", 19, bold=True)
        self.font_body = pygame.font.SysFont("arial", 15)
        self.font_small = pygame.font.SysFont("consolas", 13)
        self.font_button = pygame.font.SysFont("arial", 14, bold=True)

        self.manifest = load_manifest()
        self.items = discover_items(self.manifest)
        self.reviews = load_reviews()
        self.selected = 0
        self.frame_index = 0
        self.elapsed = 0.0
        self.one_shot_wait = 0.0
        self.fps = self.items[0].default_fps
        self.zoom = 1.0
        self.paused = False
        self.show_chroma = False
        self.show_baseline = True
        self.travel_position = 0.0
        self.scroll = 0
        self.toast = ""
        self.toast_timer = 0.0
        self.buttons: list[Button] = []

    @property
    def item(self) -> AnimationItem:
        return self.items[self.selected]

    def select(self, index: int) -> None:
        self.selected = index % len(self.items)
        self.fps = self.item.default_fps
        self.frame_index = 0
        self.elapsed = 0.0
        self.one_shot_wait = 0.0
        self.travel_position = 0.0
        visible_rows = VISIBLE_ROWS
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + visible_rows:
            self.scroll = self.selected - visible_rows + 1

    def mark(self, status: str) -> None:
        self.reviews[self.item.key] = status
        save_reviews(self.reviews)
        self.toast = "APROVADA E SALVA" if status == "aprovada" else "MARCADA PARA AJUSTE"
        self.toast_timer = 1.8

    def update(self, dt: float) -> None:
        self.toast_timer = max(0.0, self.toast_timer - dt)
        if self.paused:
            return
        item = self.item
        self.elapsed += dt
        frame_duration = 1.0 / self.fps
        while self.elapsed >= frame_duration:
            self.elapsed -= frame_duration
            if self.frame_index < len(item.frames) - 1:
                self.frame_index += 1
            elif item.one_shot:
                self.one_shot_wait += frame_duration
                if self.one_shot_wait >= 0.65:
                    self.frame_index = 0
                    self.one_shot_wait = 0.0
                    self.travel_position = 0.0
            else:
                self.frame_index = 0
            if item.travels:
                self.travel_position = (self.travel_position + 0.018) % 1.0

    def step_frame(self, direction: int) -> None:
        self.paused = True
        self.frame_index = (self.frame_index + direction) % len(self.item.frames)
        self.elapsed = 0.0

    def act(self, action: str) -> None:
        if action == "previous":
            self.select(self.selected - 1)
        elif action == "next":
            self.select(self.selected + 1)
        elif action == "play":
            self.paused = not self.paused
        elif action == "slower":
            self.fps = max(2.0, self.fps - 1.0)
        elif action == "faster":
            self.fps = min(24.0, self.fps + 1.0)
        elif action == "zoom_out":
            self.zoom = max(0.6, self.zoom - 0.15)
        elif action == "zoom_in":
            self.zoom = min(3.5, self.zoom + 0.15)
        elif action == "step_back":
            self.step_frame(-1)
        elif action == "step_forward":
            self.step_frame(1)
        elif action == "approve":
            self.mark("aprovada")
        elif action == "adjust":
            self.mark("ajustar")
        elif action == "chroma":
            self.show_chroma = not self.show_chroma
        elif action == "baseline":
            self.show_baseline = not self.show_baseline

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max(0, len(self.items) - VISIBLE_ROWS), self.scroll - event.y * 3))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    self.act(button.action)
                    return True
            if SIDEBAR.collidepoint(event.pos):
                row = (event.pos[1] - (SIDEBAR.top + 42)) // 32
                index = self.scroll + row
                if 0 <= row < VISIBLE_ROWS and 0 <= index < len(self.items):
                    self.select(index)
            return True
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key in {pygame.K_RIGHT, pygame.K_PAGEDOWN, pygame.K_TAB}:
            self.select(self.selected + 1)
        elif event.key in {pygame.K_LEFT, pygame.K_PAGEUP}:
            self.select(self.selected - 1)
        elif event.key == pygame.K_UP:
            self.select(self.selected - 1)
        elif event.key == pygame.K_DOWN:
            self.select(self.selected + 1)
        elif event.key == pygame.K_SPACE:
            self.act("play")
        elif event.key in {pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS}:
            self.act("faster")
        elif event.key in {pygame.K_MINUS, pygame.K_KP_MINUS}:
            self.act("slower")
        elif event.key == pygame.K_LEFTBRACKET:
            self.act("step_back")
        elif event.key == pygame.K_RIGHTBRACKET:
            self.act("step_forward")
        elif event.key == pygame.K_a:
            self.act("approve")
        elif event.key == pygame.K_r:
            self.act("adjust")
        elif event.key == pygame.K_c:
            self.act("chroma")
        elif event.key == pygame.K_l:
            self.act("baseline")
        elif event.key == pygame.K_0:
            self.zoom = 1.0
            self.fps = self.item.default_fps
        return True

    def add_button(self, rect: pygame.Rect, text: str, action: str, tone: str = "neutral") -> None:
        self.buttons.append(Button(rect, text, action, tone))

    def draw_button(self, button: Button, mouse: tuple[int, int]) -> None:
        tones = {
            "neutral": (37, 51, 63),
            "cyan": (32, 103, 99),
            "green": (32, 116, 68),
            "red": (126, 48, 49),
            "gold": (132, 96, 31),
        }
        color = tones[button.tone]
        if button.rect.collidepoint(mouse):
            color = tuple(min(255, channel + 24) for channel in color)
        pygame.draw.rect(self.screen, color, button.rect, border_radius=7)
        pygame.draw.rect(self.screen, LINE, button.rect, 1, border_radius=7)
        draw_text(self.screen, self.font_button, button.text, WHITE, button.rect.center, center=True)

    def draw_header(self) -> None:
        draw_text(self.screen, self.font_title, "LABORATÓRIO DE ANIMAÇÕES — BETA 4", WHITE, (20, 17))
        draw_text(
            self.screen,
            self.font_body,
            f"{len(self.items)} animações • {sum(len(item.frames) for item in self.items)} quadros • nenhuma alteração no jogo principal",
            MUTED,
            (22, 53),
        )
        active_keys = {item.key for item in self.items}
        approved = sum(self.reviews.get(key) == "aprovada" for key in active_keys)
        adjust = sum(self.reviews.get(key) == "ajustar" for key in active_keys)
        pending = len(self.items) - approved - adjust
        summary = f"APROVADAS {approved:02d}   AJUSTAR {adjust:02d}   PENDENTES {pending:02d}"
        summary_image = self.font_small.render(summary, True, CYAN)
        self.screen.blit(summary_image, summary_image.get_rect(topright=(1260, 31)))

        x = 354
        controls = [
            ("<< ANTERIOR", "previous", "neutral", 104),
            ("PRÓXIMA >>", "next", "neutral", 104),
            ("PAUSAR" if not self.paused else "REPRODUZIR", "play", "gold", 112),
            ("– FPS", "slower", "neutral", 72),
            ("+ FPS", "faster", "neutral", 72),
            ("– ZOOM", "zoom_out", "neutral", 78),
            ("+ ZOOM", "zoom_in", "neutral", 78),
            ("APROVAR", "approve", "green", 98),
            ("AJUSTAR", "adjust", "red", 98),
        ]
        for text, action, tone, width in controls:
            self.add_button(pygame.Rect(x, 76, width, 31), text, action, tone)
            x += width + 7

    def draw_sidebar(self) -> None:
        pygame.draw.rect(self.screen, PANEL, SIDEBAR, border_radius=10)
        pygame.draw.rect(self.screen, LINE, SIDEBAR, 1, border_radius=10)
        draw_text(self.screen, self.font_h2, "TODAS AS ANIMAÇÕES", WHITE, (SIDEBAR.x + 14, SIDEBAR.y + 11))
        y = SIDEBAR.y + 42
        mouse = pygame.mouse.get_pos()
        for row, index in enumerate(range(self.scroll, min(len(self.items), self.scroll + VISIBLE_ROWS))):
            item = self.items[index]
            rect = pygame.Rect(SIDEBAR.x + 8, y + row * 32, SIDEBAR.width - 16, 29)
            selected = index == self.selected
            if selected:
                pygame.draw.rect(self.screen, (34, 80, 84), rect, border_radius=5)
            elif rect.collidepoint(mouse):
                pygame.draw.rect(self.screen, PANEL_2, rect, border_radius=5)
            status = self.reviews.get(item.key)
            icon = "✓" if status == "aprovada" else "!" if status == "ajustar" else "·"
            icon_color = GREEN if status == "aprovada" else RED if status == "ajustar" else MUTED
            draw_text(self.screen, self.font_body, icon, icon_color, (rect.x + 7, rect.y + 5))
            label = f"{index + 1:02d} {item.title} — {item.action_title}"
            if len(label) > 39:
                label = label[:38] + "…"
            draw_text(self.screen, self.font_small, label, WHITE if selected else MUTED, (rect.x + 27, rect.y + 7))

        footer_y = SIDEBAR.bottom - 35
        draw_text(
            self.screen,
            self.font_small,
            "Roda do mouse ou ↑ ↓ para navegar",
            MUTED,
            (SIDEBAR.x + 15, footer_y),
        )

    def draw_checker(self, rect: pygame.Rect) -> None:
        cell = 24
        for y in range(rect.top, rect.bottom, cell):
            for x in range(rect.left, rect.right, cell):
                parity = ((x - rect.left) // cell + (y - rect.top) // cell) % 2
                color = (26, 35, 43) if parity else (20, 29, 36)
                pygame.draw.rect(self.screen, color, (x, y, cell, cell))

    def draw_stage(self) -> None:
        pygame.draw.rect(self.screen, PANEL, STAGE, border_radius=10)
        if self.show_chroma:
            inner = STAGE.inflate(-4, -4)
            pygame.draw.rect(self.screen, CHROMA, inner, border_radius=8)
        else:
            self.draw_checker(STAGE.inflate(-4, -4))
        pygame.draw.rect(self.screen, LINE, STAGE, 1, border_radius=10)

        item = self.item
        draw_text(self.screen, self.font_h2, item.title, WHITE, (STAGE.x + 18, STAGE.y + 14))
        draw_text(self.screen, self.font_body, item.action_title, GOLD, (STAGE.x + 18, STAGE.y + 43))
        draw_text(
            self.screen,
            self.font_small,
            f"{item.group}  •  {len(item.frames)} quadros  •  {self.fps:.0f} FPS  •  zoom {self.zoom:.2f}x",
            MUTED,
            (STAGE.x + 18, STAGE.y + 68),
        )
        behavior = "UMA VEZ + REPETIÇÃO DE TESTE" if item.one_shot else "LOOP CONTÍNUO"
        draw_text(self.screen, self.font_small, behavior, CYAN, (STAGE.right - 253, STAGE.y + 18))

        frame = item.frames[self.frame_index]
        display = fit_nearest(frame, (STAGE.width - 120, STAGE.height - 150), self.zoom)
        floor_y = STAGE.bottom - 51
        if self.show_baseline:
            pygame.draw.line(self.screen, (75, 126, 124), (STAGE.x + 38, floor_y), (STAGE.right - 38, floor_y), 1)
            for x in range(STAGE.x + 38, STAGE.right - 38, 64):
                pygame.draw.line(self.screen, (46, 76, 77), (x, floor_y - 5), (x, floor_y + 5), 1)
            draw_text(self.screen, self.font_small, "LINHA DO CHÃO", (94, 150, 146), (STAGE.x + 42, floor_y + 9))

        if item.travels:
            left = STAGE.x + 90
            right = STAGE.right - 90
            progress = 1.0 - self.travel_position if item.moves_left else self.travel_position
            center_x = int(left + (right - left) * progress)
        else:
            center_x = STAGE.centerx
        sprite_rect = display.get_rect(midbottom=(center_x, floor_y))
        self.screen.blit(display, sprite_rect)

        status = self.reviews.get(item.key)
        if status:
            color = GREEN if status == "aprovada" else RED
            text = "APROVADA" if status == "aprovada" else "PRECISA AJUSTAR"
            badge = pygame.Rect(STAGE.right - 188, STAGE.bottom - 42, 160, 28)
            pygame.draw.rect(self.screen, color, badge, border_radius=14)
            draw_text(self.screen, self.font_button, text, BG, badge.center, center=True)

    def draw_filmstrip(self) -> None:
        pygame.draw.rect(self.screen, PANEL, FILMSTRIP, border_radius=10)
        pygame.draw.rect(self.screen, LINE, FILMSTRIP, 1, border_radius=10)
        draw_text(
            self.screen,
            self.font_small,
            f"QUADRO {self.frame_index + 1}/{len(self.item.frames)} — use [ e ] para conferir um por um",
            MUTED,
            (FILMSTRIP.x + 15, FILMSTRIP.y + 10),
        )

        count = len(self.item.frames)
        gap = 8
        available = FILMSTRIP.width - 30
        cell_width = min(104, (available - gap * (count - 1)) // count)
        start_x = FILMSTRIP.centerx - (cell_width * count + gap * (count - 1)) // 2
        y = FILMSTRIP.y + 35
        for index, frame in enumerate(self.item.frames):
            rect = pygame.Rect(start_x + index * (cell_width + gap), y, cell_width, 85)
            selected = index == self.frame_index
            pygame.draw.rect(self.screen, (28, 39, 48), rect, border_radius=5)
            pygame.draw.rect(self.screen, GOLD if selected else LINE, rect, 3 if selected else 1, border_radius=5)
            thumb = fit_nearest(frame, (rect.width - 8, rect.height - 22), 1.0)
            thumb_rect = thumb.get_rect(center=(rect.centerx, rect.centery - 5))
            self.screen.blit(thumb, thumb_rect)
            draw_text(self.screen, self.font_small, str(index + 1), WHITE, (rect.centerx, rect.bottom - 11), center=True)

    def draw_footer_controls(self) -> None:
        y = STAGE.bottom - 39
        x = STAGE.x + 18
        for text, action, width in [
            ("< QUADRO", "step_back", 92),
            ("QUADRO >", "step_forward", 92),
            ("CHROMA", "chroma", 86),
            ("LINHA DO CHÃO", "baseline", 132),
        ]:
            self.add_button(pygame.Rect(x, y, width, 28), text, action, "cyan" if action in {"chroma", "baseline"} else "neutral")
            x += width + 7

    def draw(self) -> None:
        self.buttons = []
        self.screen.fill(BG)
        self.draw_header()
        self.draw_sidebar()
        self.draw_stage()
        self.draw_footer_controls()
        self.draw_filmstrip()
        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            self.draw_button(button, mouse)
        if self.toast_timer > 0.0:
            toast = pygame.Rect(STAGE.centerx - 145, STAGE.y + 96, 290, 38)
            pygame.draw.rect(self.screen, (7, 18, 22), toast, border_radius=19)
            pygame.draw.rect(self.screen, CYAN, toast, 2, border_radius=19)
            draw_text(self.screen, self.font_button, self.toast, WHITE, toast.center, center=True)
        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.update(dt)
            self.draw()
        pygame.quit()

    def run_headless(self, frame_count: int, screenshot: Path | None) -> None:
        # Renderiza ao menos um quadro de cada item para detectar também erros
        # de escala/desenho que o simples carregamento de arquivo não revelaria.
        for index in range(len(self.items)):
            self.select(index)
            self.update(1.0 / 60.0)
            self.draw()
        self.select(0)
        for _ in range(max(1, frame_count)):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
            self.update(1.0 / 60.0)
            self.draw()
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.screen, str(screenshot))
        total_frames = sum(len(item.frames) for item in self.items)
        print(f"OK: {len(self.items)} animações e {total_frames} quadros carregados.")
        pygame.quit()


def main() -> int:
    args = parse_args()
    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    try:
        laboratory = AnimationLaboratory(headless=args.headless)
        if args.headless:
            laboratory.run_headless(args.frames, args.screenshot)
        else:
            laboratory.run()
    except Exception as exc:  # A mensagem amigável permanece visível no .bat.
        print(f"ERRO AO ABRIR O LABORATÓRIO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
