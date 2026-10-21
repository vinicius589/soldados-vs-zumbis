"""Laboratório visual para aprovar animações antes de levá-las ao jogo.

O laboratório usa :mod:`animation2d`, mas não importa ``main.py`` e não altera
save, campanha, balanceamento, carregamento ou menu do jogo principal.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pygame

from animation2d import AnimationClip, AnimationManager, SpriteSheet


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "v7"
REVIEW_PATH = ROOT / "animation_review.json"
WIDTH, HEIGHT = 1280, 720
STAGE = pygame.Rect(18, 112, 922, 588)
PANEL = pygame.Rect(958, 112, 304, 588)

INK = (9, 14, 18)
PANEL_COLOR = (15, 24, 29)
WHITE = (239, 243, 240)
GRAY = (157, 171, 176)
GOLD = (239, 184, 70)
TEAL = (76, 204, 190)
RED = (224, 80, 67)


@dataclass(frozen=True, slots=True)
class PreviewSpec:
    key: str
    name: str
    chapter: str
    background: str
    actions: tuple[tuple[str, str], ...]
    baseline_ratio: float
    target_box: tuple[int, int]
    canvas_size: tuple[int, int]
    travel: bool = True


PREVIEWS = (
    PreviewSpec(
        "city_walker",
        "Irradiado Civil",
        "NOVA MANHATTAN — ZONA ZERO",
        "city_beta4_four_lanes.png",
        (
            ("andar", "city_radioactive_walker_walk_story.png"),
            ("morder", "city_radioactive_walker_bite_story_alpha.png"),
        ),
        0.69,
        (205, 255),
        (250, 285),
    ),
    PreviewSpec(
        "desert_mummy",
        "Múmia Operária",
        "EGITO — NECRÓPOLE DE KHEPRA",
        "desert_beta4_four_lanes.png",
        (("andar", "desert_mummy_walk_story.png"),),
        0.69,
        (205, 255),
        (250, 285),
    ),
    PreviewSpec(
        "beach_drowned",
        "Afogado Costeiro",
        "COSTA ATLÂNTICA — MARÉ MORTA",
        "beach_beta4_four_lanes.png",
        (("andar", "beach_drowned_walker_walk_story_alpha.png"),),
        0.78,
        (205, 255),
        (250, 285),
    ),
    PreviewSpec(
        "beach_swimmer",
        "Nadador Mutante",
        "COSTA ATLÂNTICA — CANAL",
        "beach_beta4_four_lanes.png",
        (("nadar", "beach_mutant_swimmer_swim_story_alpha.png"),),
        0.55,
        (280, 130),
        (320, 165),
    ),
)


def normalized_frame(
    frame: pygame.Surface,
    *,
    target_box: tuple[int, int],
    canvas_size: tuple[int, int],
) -> pygame.Surface:
    """Remove margem por quadro e realinha todos pela mesma linha-base.

    A posição dos pés não depende do tamanho da margem transparente gerada no
    arquivo. Para nadadores, a parte inferior do corpo usa a mesma âncora; a
    silhueta continua horizontal porque ``target_box`` é largo e baixo.

    Antes do recorte, somente a maior silhueta conectada é mantida. Isso evita
    que um braço ou pé da pose vizinha, desenhado além da divisória da folha de
    sprites, apareça solto no quadro atual.
    """
    alpha_mask = pygame.mask.from_surface(frame, threshold=8)
    components = alpha_mask.connected_components(minimum=6)
    if not components:
        return pygame.Surface(canvas_size, pygame.SRCALPHA)
    silhouette = max(components, key=pygame.mask.Mask.count)
    silhouette_surface = silhouette.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    isolated = frame.copy()
    isolated.blit(silhouette_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    bounds = isolated.get_bounding_rect(min_alpha=8)
    if bounds.width <= 1 or bounds.height <= 1:
        return pygame.Surface(canvas_size, pygame.SRCALPHA)
    cropped = isolated.subsurface(bounds).copy()
    factor = min(target_box[0] / cropped.get_width(), target_box[1] / cropped.get_height())
    size = (
        max(1, round(cropped.get_width() * factor)),
        max(1, round(cropped.get_height() * factor)),
    )
    scaled = pygame.transform.smoothscale(cropped, size)
    canvas = pygame.Surface(canvas_size, pygame.SRCALPHA)
    rect = scaled.get_rect(midbottom=(canvas_size[0] // 2, canvas_size[1] - 4))
    canvas.blit(scaled, rect)
    return canvas


def load_strip(spec: PreviewSpec, path: Path) -> list[pygame.Surface]:
    source = pygame.image.load(str(path)).convert_alpha()
    cells = SpriteSheet(source).slice_equal(8, 1)
    return [
        normalized_frame(frame, target_box=spec.target_box, canvas_size=spec.canvas_size)
        for frame in cells
    ]


def cover(source: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    """Escala e recorta uma imagem para preencher a área sem deformá-la."""
    factor = max(size[0] / source.get_width(), size[1] / source.get_height())
    scaled = pygame.transform.smoothscale(
        source,
        (round(source.get_width() * factor), round(source.get_height() * factor)),
    )
    result = pygame.Surface(size).convert()
    rect = scaled.get_rect(center=(size[0] // 2, size[1] // 2))
    result.blit(scaled, rect)
    return result


def load_reviews() -> dict[str, str]:
    try:
        raw = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        return {str(key): str(value) for key, value in raw.items() if value in {"aprovado", "ajustar"}}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def save_reviews(reviews: dict[str, str]) -> None:
    REVIEW_PATH.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")


class AnimationLab:
    def __init__(self, *, headless: bool = False) -> None:
        pygame.init()
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Soldados vs Zumbis — Laboratório de Animação")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("arial", 27, bold=True)
        self.font_h2 = pygame.font.SysFont("arial", 19, bold=True)
        self.font_body = pygame.font.SysFont("arial", 15)
        self.font_small = pygame.font.SysFont("consolas", 13)

        self.backgrounds: dict[str, pygame.Surface] = {}
        self.clips: dict[str, dict[str, AnimationClip]] = {}
        self.thumbnails: dict[str, pygame.Surface] = {}
        for spec in PREVIEWS:
            background = pygame.image.load(str(ASSETS / spec.background)).convert()
            self.backgrounds[spec.key] = cover(background, STAGE.size)
            action_clips: dict[str, AnimationClip] = {}
            for action, filename in spec.actions:
                frames = load_strip(spec, ASSETS / filename)
                action_clips[action] = AnimationClip.uniform(frames, fps=10.0, loop=True, name=f"{spec.key}:{action}")
                self.thumbnails.setdefault(spec.key, frames[0])
            self.clips[spec.key] = action_clips

        self.selected = 0
        self.action_index = 0
        self.manager = AnimationManager(self.clips[PREVIEWS[0].key], initial_state=PREVIEWS[0].actions[0][0])
        self.fps = 10.0
        self.paused = False
        self.calibration_line = False
        self.show_background = True
        self.actor_x = float(STAGE.right - 120)
        self.reviews = load_reviews()
        self.toast = ""
        self.toast_time = 0.0
        self.frame_time_average = 0.0

    @property
    def spec(self) -> PreviewSpec:
        return PREVIEWS[self.selected]

    @property
    def action(self) -> str:
        return self.spec.actions[self.action_index][0]

    def select(self, index: int) -> None:
        self.selected = index % len(PREVIEWS)
        self.action_index = 0
        actions = self.clips[self.spec.key]
        self.manager = AnimationManager(actions, initial_state=self.spec.actions[0][0])
        self.manager.playback_rate = self.fps / 10.0
        self.actor_x = float(STAGE.right - 120)
        self.toast = f"Carregado: {self.spec.name}"
        self.toast_time = 1.4

    def cycle_action(self) -> None:
        if len(self.spec.actions) <= 1:
            self.toast = "Este protótipo possui somente uma ação nesta rodada."
            self.toast_time = 1.8
            return
        self.action_index = (self.action_index + 1) % len(self.spec.actions)
        self.manager.play(self.action, restart=True)
        self.actor_x = float(STAGE.centerx + 120)

    def mark(self, status: str) -> None:
        review_key = f"{self.spec.key}:{self.action}"
        self.reviews[review_key] = status
        save_reviews(self.reviews)
        self.toast = "ANIMAÇÃO APROVADA" if status == "aprovado" else "MARCADA PARA AJUSTE"
        self.toast_time = 2.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        if pygame.K_1 <= event.key <= pygame.K_4:
            self.select(event.key - pygame.K_1)
        elif event.key == pygame.K_TAB:
            self.select(self.selected + 1)
        elif event.key == pygame.K_q:
            self.cycle_action()
        elif event.key == pygame.K_SPACE:
            self.paused = not self.paused
            self.manager.paused = self.paused
        elif event.key == pygame.K_LEFT and self.paused:
            self.manager.step(-1)
        elif event.key == pygame.K_RIGHT and self.paused:
            self.manager.step(1)
        elif event.key in {pygame.K_LEFTBRACKET, pygame.K_MINUS}:
            self.fps = max(2.0, self.fps - 1.0)
            self.manager.playback_rate = self.fps / 10.0
        elif event.key in {pygame.K_RIGHTBRACKET, pygame.K_EQUALS, pygame.K_PLUS}:
            self.fps = min(24.0, self.fps + 1.0)
            self.manager.playback_rate = self.fps / 10.0
        elif event.key == pygame.K_r:
            self.manager.restart()
            self.actor_x = float(STAGE.right - 120)
        elif event.key == pygame.K_f:
            self.calibration_line = not self.calibration_line
        elif event.key == pygame.K_b:
            self.show_background = not self.show_background
        elif event.key == pygame.K_a:
            self.mark("aprovado")
        elif event.key == pygame.K_x:
            self.mark("ajustar")
        elif event.key == pygame.K_c:
            self.reviews.pop(f"{self.spec.key}:{self.action}", None)
            save_reviews(self.reviews)
        elif event.key == pygame.K_s:
            path = ROOT / "animation_review_capture.png"
            pygame.image.save(self.screen, str(path))
            self.toast = f"Captura salva: {path.name}"
            self.toast_time = 2.0
        return True

    def update(self, dt: float) -> None:
        self.toast_time = max(0.0, self.toast_time - dt)
        self.frame_time_average = self.frame_time_average * 0.92 + dt * 0.08
        if self.paused:
            return
        self.manager.update(dt)
        if self.spec.travel and self.action in {"andar", "nadar"}:
            speed = 78.0 if self.action == "andar" else 92.0
            self.actor_x -= speed * dt
            if self.actor_x < STAGE.left + 95:
                self.actor_x = float(STAGE.right - 95)

    def text(
        self,
        value: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: tuple[int, int],
        *,
        center: bool = False,
    ) -> None:
        rendered = font.render(value, True, color)
        rect = rendered.get_rect(center=position) if center else rendered.get_rect(topleft=position)
        self.screen.blit(rendered, rect)

    def panel(self, rect: pygame.Rect, color: tuple[int, int, int] = PANEL_COLOR, border: tuple[int, int, int] = TEAL) -> None:
        pygame.draw.rect(self.screen, color, rect, border_radius=9)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=9)

    def draw_stage(self) -> None:
        self.panel(STAGE, (8, 13, 16), TEAL)
        if self.show_background:
            self.screen.blit(self.backgrounds[self.spec.key], STAGE)
        else:
            tile = 32
            for y in range(STAGE.top, STAGE.bottom, tile):
                for x in range(STAGE.left, STAGE.right, tile):
                    shade = (38, 43, 46) if ((x - STAGE.left) // tile + (y - STAGE.top) // tile) % 2 else (56, 62, 65)
                    pygame.draw.rect(self.screen, shade, (x, y, tile, tile))
        pygame.draw.rect(self.screen, TEAL, STAGE, width=2, border_radius=9)

        baseline = STAGE.top + round(STAGE.height * self.spec.baseline_ratio)
        if self.calibration_line:
            pygame.draw.line(self.screen, GOLD, (STAGE.left + 12, baseline), (STAGE.right - 12, baseline), 1)
            self.text("LINHA-BASE DE TESTE (não aparece no jogo)", self.font_small, GOLD, (STAGE.left + 22, baseline + 8))

        frame = self.manager.frame
        rect = frame.get_rect(midbottom=(round(self.actor_x), baseline))
        self.screen.blit(frame, rect)

        overlay = pygame.Surface((STAGE.width, 52), pygame.SRCALPHA)
        overlay.fill((3, 8, 10, 204))
        self.screen.blit(overlay, (STAGE.left, STAGE.top))
        self.text(self.spec.chapter, self.font_h2, GOLD, (STAGE.left + 18, STAGE.top + 8))
        self.text(
            f"{self.spec.name} • AÇÃO: {self.action.upper()}",
            self.font_body,
            WHITE,
            (STAGE.left + 18, STAGE.top + 31),
        )

    def draw_panel(self) -> None:
        self.panel(PANEL)
        self.text("PROTÓTIPOS", self.font_h2, GOLD, (PANEL.x + 16, PANEL.y + 14))
        for index, spec in enumerate(PREVIEWS):
            rect = pygame.Rect(PANEL.x + 12, PANEL.y + 45 + index * 83, PANEL.width - 24, 72)
            color = GOLD if index == self.selected else (68, 91, 98)
            pygame.draw.rect(self.screen, (20, 31, 36), rect, border_radius=7)
            pygame.draw.rect(self.screen, color, rect, width=2, border_radius=7)
            thumb = self.thumbnails[spec.key]
            max_size = (58, 60)
            factor = min(max_size[0] / thumb.get_width(), max_size[1] / thumb.get_height())
            scaled = pygame.transform.smoothscale(thumb, (max(1, round(thumb.get_width() * factor)), max(1, round(thumb.get_height() * factor))))
            self.screen.blit(scaled, scaled.get_rect(midbottom=(rect.x + 42, rect.bottom - 5)))
            self.text(f"{index + 1}. {spec.name}", self.font_body, WHITE, (rect.x + 79, rect.y + 12))
            action = self.action if index == self.selected else spec.actions[0][0]
            status = self.reviews.get(f"{spec.key}:{action}", "pendente")
            status_color = TEAL if status == "aprovado" else (RED if status == "ajustar" else GRAY)
            self.text(status.upper(), self.font_small, status_color, (rect.x + 79, rect.y + 39))

        info_y = PANEL.y + 384
        self.text("CONTROLE DE QUADROS", self.font_h2, GOLD, (PANEL.x + 16, info_y))
        self.text(f"Frame: {self.manager.frame_index + 1}/8", self.font_small, WHITE, (PANEL.x + 16, info_y + 31))
        self.text(f"Velocidade: {self.fps:.0f} fps  [- / +]", self.font_small, WHITE, (PANEL.x + 16, info_y + 51))
        actual_fps = 1.0 / self.frame_time_average if self.frame_time_average > 0 else 0.0
        self.text(f"Loop real: {actual_fps:5.1f} FPS • dt {self.frame_time_average * 1000:4.1f} ms", self.font_small, GRAY, (PANEL.x + 16, info_y + 71))
        self.text("ESPAÇO pausa • ←/→ quadro", self.font_small, GRAY, (PANEL.x + 16, info_y + 99))
        self.text("Q ação • R reinicia • B fundo", self.font_small, GRAY, (PANEL.x + 16, info_y + 119))
        self.text("F linha-base • S captura", self.font_small, GRAY, (PANEL.x + 16, info_y + 139))
        self.text("A APROVAR", self.font_h2, TEAL, (PANEL.x + 16, info_y + 171))
        self.text("X AJUSTAR", self.font_h2, RED, (PANEL.x + 156, info_y + 171))

    def draw(self) -> None:
        self.screen.fill(INK)
        self.text("LABORATÓRIO DE ANIMAÇÃO — APROVAÇÃO ANTES DO JOGO", self.font_title, WHITE, (WIDTH // 2, 24), center=True)
        self.text(
            "Quadros reais governados por delta time • menu e jogo principal não são alterados",
            self.font_body,
            GRAY,
            (WIDTH // 2, 61),
            center=True,
        )
        self.draw_stage()
        self.draw_panel()
        if self.toast_time > 0:
            toast = pygame.Rect(WIDTH // 2 - 220, 78, 440, 32)
            pygame.draw.rect(self.screen, (8, 15, 18), toast, border_radius=7)
            pygame.draw.rect(self.screen, GOLD, toast, width=2, border_radius=7)
            self.text(self.toast, self.font_body, WHITE, toast.center, center=True)
        pygame.display.flip()

    def run(self, *, frame_limit: int | None = None, capture: Path | None = None) -> None:
        running = True
        rendered = 0
        try:
            while running:
                dt = min(self.clock.tick(60) / 1000.0, 0.1)
                for event in pygame.event.get():
                    running = self.handle_event(event)
                    if not running:
                        break
                self.update(dt)
                self.draw()
                rendered += 1
                if frame_limit is not None and rendered >= frame_limit:
                    if capture is not None:
                        pygame.image.save(self.screen, str(capture))
                    break
        finally:
            pygame.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualizador de aprovação de animações do projeto")
    parser.add_argument("--headless", action="store_true", help="usa SDL dummy para teste automatizado")
    parser.add_argument("--frames", type=int, default=None, help="encerra após esta quantidade de quadros")
    parser.add_argument("--capture", type=Path, default=None, help="salva o último quadro renderizado")
    parser.add_argument(
        "--prototype",
        type=int,
        choices=range(1, len(PREVIEWS) + 1),
        default=1,
        metavar="N",
        help=f"abre diretamente um protótipo de 1 a {len(PREVIEWS)}",
    )
    parser.add_argument(
        "--action",
        type=str,
        default=None,
        help="ação inicial do protótipo, por exemplo: andar, morder ou nadar",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    lab = AnimationLab(headless=args.headless)
    lab.select(args.prototype - 1)
    if args.action is not None:
        available = {name for name, _ in lab.spec.actions}
        if args.action not in available:
            choices = ", ".join(sorted(available))
            raise SystemExit(
                f"A ação '{args.action}' não existe no protótipo {args.prototype}. "
                f"Ações disponíveis: {choices}."
            )
        lab.action_index = [name for name, _ in lab.spec.actions].index(args.action)
        lab.manager.play(args.action, restart=True)
    lab.run(frame_limit=args.frames, capture=args.capture)


if __name__ == "__main__":
    main()
