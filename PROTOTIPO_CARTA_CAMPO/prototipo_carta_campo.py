"""Ensaio isolado: carta, implantação da tropa e chegada do primeiro zumbi.

Este arquivo não altera o jogo principal. Ele existe para validar, nesta ordem:

1. leitura e seleção da carta;
2. escala e contato dos pés com uma pista real do cenário;
3. caminhada do Guarda de Rua da base até o quadrado escolhido;
4. entrada do Caminhante Urbano pela direita, sem trocar de linha;
5. continuidade visual das novas folhas de sprites.

Todo movimento e toda troca de quadro são governados por ``dt``.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame


WIDTH, HEIGHT = 1280, 720
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
ASSETS = ROOT / "assets"
SCENARIO = (
    PROJECT_ROOT
    / "CENARIOS_BETA4_CONCEITOS"
    / "prontos_1280x720"
    / "01_nova_york_terminal_helix_entrada_unica_v4.png"
)

sys.path.insert(0, str(PROJECT_ROOT))
from animation2d import AnimationClip, Entity, SpriteSheet  # noqa: E402


LANE_CENTERS = (280, 368, 458, 553)
GROUND_OFFSETS = (36, 38, 39, 39)
GRID_X = (300, 410, 520, 630, 740, 850, 960)
CARD_RECT = pygame.Rect(22, 14, 184, 98)
RESET_RECT = pygame.Rect(1090, 24, 166, 48)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=420)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def scale_pixel_art(surface: pygame.Surface, target_height: int) -> pygame.Surface:
    factor = target_height / surface.get_height()
    target_width = max(1, round(surface.get_width() * factor))
    return pygame.transform.scale(surface, (target_width, target_height))


def normalize_cells(frames: list[pygame.Surface], target_height: int) -> list[pygame.Surface]:
    """Recorta cada pose e recompõe uma sequência com pés e pivô estáveis."""
    bounds = [frame.get_bounding_rect(min_alpha=8) for frame in frames]
    if any(rect.width <= 0 or rect.height <= 0 for rect in bounds):
        raise ValueError("a folha contém um quadro completamente transparente")

    width = max(rect.width for rect in bounds) + 8
    height = max(rect.height for rect in bounds) + 6
    normalized: list[pygame.Surface] = []
    for frame, rect in zip(frames, bounds):
        crop = frame.subsurface(rect).copy()
        canvas = pygame.Surface((width, height), pygame.SRCALPHA)
        # Todos os pés encostam na mesma base. A oscilação horizontal vem do
        # desenho do corpo, não de um retângulo transparente irregular.
        canvas.blit(crop, ((width - crop.get_width()) // 2, height - crop.get_height() - 3))
        normalized.append(scale_pixel_art(canvas, target_height))
    return normalized


def keep_main_figure(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    """Remove ruído e invasão da célula vizinha, preservando o ator inteiro."""
    cleaned: list[pygame.Surface] = []
    for frame in frames:
        source_mask = pygame.mask.from_surface(frame, threshold=8)
        components = source_mask.get_bounding_rects()
        if not components:
            raise ValueError("a animação contém um quadro completamente transparente")
        # ``connected_component()`` sem semente devolve o maior componente.
        # Aplicar a máscara pixel a pixel é importante: um recorte retangular
        # ainda poderia conter pedaços pequenos da pose vizinha.
        main_mask = source_mask.connected_component()
        keep_surface = main_mask.to_surface(
            setcolor=(255, 255, 255, 255),
            unsetcolor=(255, 255, 255, 0),
        )
        keep_alpha = pygame.surfarray.array_alpha(keep_surface)
        result = frame.copy()
        alpha = pygame.surfarray.pixels_alpha(result)
        alpha[keep_alpha <= 8] = 0
        del alpha
        cleaned.append(result)
    return cleaned


def pad_animation_groups(
    groups: dict[str, list[pygame.Surface]],
    *,
    horizontal_padding: int = 6,
    top_padding: int = 4,
) -> dict[str, list[pygame.Surface]]:
    """Coloca todos os estados de um ator na mesma caixa, sem reescalar.

    ``Entity`` ancora a superfície inteira. Se cada estado tiver uma largura ou
    altura diferente, a troca de animação parece aumentar o personagem e pode
    deslocar o pé, mesmo com ``midbottom``. Esta etapa cria uma única caixa para
    todos os estados e preserva o conteúdo na mesma base.
    """
    frames = [frame for group in groups.values() for frame in group]
    if not frames:
        raise ValueError("é necessário informar pelo menos um quadro")
    geometry: list[tuple[pygame.Surface, pygame.Rect]] = []
    for frame in frames:
        components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
        if not components:
            raise ValueError("a animação contém um quadro completamente transparente")
        main = max(components, key=lambda rect: rect.width * rect.height)
        geometry.append((frame, main))

    # Mede as sobras em torno do corpo principal. Clarões e carregadores podem
    # ampliar a caixa, mas nunca mudam o centro do ator nem a linha dos pés.
    min_x = min(-main.centerx for frame, main in geometry)
    max_x = max(frame.get_width() - main.centerx for frame, main in geometry)
    min_y = min(-main.bottom for frame, main in geometry)
    max_y = max(frame.get_height() - main.bottom for frame, main in geometry)
    # A margem lateral impede que arma, braço ou casaco encostem na borda da
    # textura. A margem é acrescentada à caixa, não ao desenho: o ator não é
    # ampliado. Não adicionamos margem inferior para não levantar os pés.
    width = max_x - min_x + horizontal_padding * 2
    height = max_y - min_y + top_padding
    actor_x = -min_x + horizontal_padding
    foot_y = -min_y + top_padding

    padded: dict[str, list[pygame.Surface]] = {}
    geometry_index = 0
    for state, state_frames in groups.items():
        padded[state] = []
        for frame in state_frames:
            _, main = geometry[geometry_index]
            geometry_index += 1
            canvas = pygame.Surface((width, height), pygame.SRCALPHA)
            canvas.blit(frame, (actor_x - main.centerx, foot_y - main.bottom))
            padded[state].append(canvas)
    return padded


def load_two_row_sheet(path: Path, target_height: int) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
    sheet = SpriteSheet.from_file(path)
    frames = keep_main_figure(sheet.slice_equal(8, 2))
    # As duas fileiras são normalizadas juntas. Assim, a transição de andar
    # para esperar nunca recalcula o tamanho nem move a base dos pés.
    normalized = normalize_cells(frames, target_height)
    return normalized[:8], normalized[8:]


@dataclass(slots=True)
class Deployment:
    target_x: float
    lane: int
    arrived: bool = False
    arrival_elapsed: float = 0.0


class Prototype:
    def __init__(self, *, headless: bool = False) -> None:
        pygame.init()
        self.headless = headless
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Soldados vs Zumbis — ensaio de carta e campo")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 23, bold=True)
        self.small = pygame.font.SysFont("arial", 16)
        self.tiny = pygame.font.SysFont("arial", 13, bold=True)
        self.background = pygame.image.load(str(SCENARIO)).convert()

        guard_walk, guard_idle = load_two_row_sheet(
            ASSETS / "guarda_rua_implantacao_idle_8x2_v1.png", 130
        )
        zombie_walk, zombie_idle = load_two_row_sheet(
            ASSETS / "caminhante_urbano_andando_idle_8x2_v1.png", 136
        )
        guard_groups = pad_animation_groups({"move": guard_walk, "idle": guard_idle})
        zombie_groups = pad_animation_groups({"move": zombie_walk, "idle": zombie_idle})
        self.guard_clips = {
            "move": AnimationClip.uniform(guard_groups["move"], fps=8.0, name="implantação"),
            "idle": AnimationClip.uniform(guard_groups["idle"], fps=5.0, name="pronto"),
        }
        self.zombie_clips = {
            "move": AnimationClip.uniform(zombie_groups["move"], fps=7.0, name="caminhada"),
            "idle": AnimationClip.uniform(zombie_groups["idle"], fps=4.5, name="ameaça"),
        }
        self.card_portrait = guard_groups["idle"][1]
        self.guard: Entity | None = None
        self.zombie: Entity | None = None
        self.deployment: Deployment | None = None
        self.selected = False
        self.hover_cell: tuple[int, int] | None = None
        self.demo_elapsed = 0.0
        self.demo_started = False
        self.notice = "Clique na carta e depois em um quadrado da pista."

    @staticmethod
    def ground_y(lane: int) -> int:
        return LANE_CENTERS[lane] + GROUND_OFFSETS[lane]

    @staticmethod
    def cell_rect(column: int, lane: int) -> pygame.Rect:
        return pygame.Rect(GRID_X[column] - 47, LANE_CENTERS[lane] - 38, 94, 76)

    def cell_at(self, position: tuple[int, int]) -> tuple[int, int] | None:
        for lane in range(4):
            for column in range(len(GRID_X)):
                if self.cell_rect(column, lane).collidepoint(position):
                    return column, lane
        return None

    def reset(self) -> None:
        self.guard = None
        self.zombie = None
        self.deployment = None
        self.selected = False
        self.demo_elapsed = 0.0
        self.demo_started = False
        self.notice = "Clique na carta e depois em um quadrado da pista."

    def deploy(self, column: int, lane: int) -> None:
        if self.guard is not None:
            self.notice = "Use RECOMEÇAR para testar outro quadrado."
            return
        ground = self.ground_y(lane)
        self.guard = Entity(
            self.guard_clips,
            initial_state="move",
            position=(174, ground),
            anchor="midbottom",
            auto_kill_state=None,
        )
        self.guard.velocity.x = 132.0
        self.deployment = Deployment(float(GRID_X[column]), lane)
        self.selected = False
        self.notice = "Guarda de Rua entrando no campo pela própria linha."

    def spawn_zombie(self) -> None:
        assert self.deployment is not None
        ground = self.ground_y(self.deployment.lane)
        self.zombie = Entity(
            self.zombie_clips,
            initial_state="move",
            position=(1188, ground),
            anchor="midbottom",
            auto_kill_state=None,
        )
        self.zombie.velocity.x = -58.0
        self.notice = "Caminhante Urbano chegando pela mesma pista."

    def update(self, dt: float) -> None:
        if self.guard is not None:
            self.guard.update(dt)
        if self.zombie is not None:
            self.zombie.update(dt)

        if self.guard is not None and self.deployment is not None:
            if not self.deployment.arrived and self.guard.position.x >= self.deployment.target_x:
                self.guard.position.x = self.deployment.target_x
                self.guard.velocity.x = 0.0
                self.guard.set_state("idle")
                self.deployment.arrived = True
                self.notice = "Implantação concluída. A horda está começando."
            if self.deployment.arrived:
                self.deployment.arrival_elapsed += dt
                if self.zombie is None and self.deployment.arrival_elapsed >= 0.65:
                    self.spawn_zombie()

        if self.zombie is not None and self.guard is not None:
            stop_x = self.guard.position.x + 150.0
            if self.zombie.position.x <= stop_x:
                self.zombie.position.x = stop_x
                self.zombie.velocity.x = 0.0
                self.zombie.set_state("idle")
                self.notice = "Escala e alinhamento prontos para sua avaliação."

    def update_demo(self, dt: float) -> None:
        self.demo_elapsed += dt
        if not self.demo_started and self.demo_elapsed >= 0.45:
            self.selected = True
            self.deploy(3, 1)
            self.demo_started = True

    def draw_cell_feedback(self) -> None:
        if not self.selected:
            return
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for lane in range(4):
            for column in range(len(GRID_X)):
                rect = self.cell_rect(column, lane)
                color = (55, 215, 188, 66)
                if self.hover_cell == (column, lane):
                    color = (255, 190, 63, 112)
                pygame.draw.rect(layer, color, rect, border_radius=7)
                pygame.draw.rect(layer, (127, 255, 225, 128), rect, 2, border_radius=7)
        self.screen.blit(layer, (0, 0))

    def draw_card(self) -> None:
        mouse = pygame.mouse.get_pos()
        hovered = CARD_RECT.collidepoint(mouse)
        fill = (25, 49, 62) if not self.selected else (35, 76, 68)
        if hovered:
            fill = (45, 76, 86)
        pygame.draw.rect(self.screen, fill, CARD_RECT, border_radius=9)
        pygame.draw.rect(
            self.screen,
            (246, 180, 55) if self.selected else (96, 225, 202),
            CARD_RECT,
            3,
            border_radius=9,
        )
        portrait_box = pygame.Rect(CARD_RECT.x + 6, CARD_RECT.y + 6, 66, 86)
        portrait = self.card_portrait
        if portrait.get_height() > 82:
            portrait = scale_pixel_art(portrait, 82)
        self.screen.blit(portrait, portrait.get_rect(midbottom=(portrait_box.centerx, portrait_box.bottom)))
        self.screen.blit(self.tiny.render("GUARDA DE RUA", True, (245, 248, 237)), (98, 23))
        self.screen.blit(self.tiny.render("CUSTO 90", True, (255, 201, 76)), (98, 44))
        self.screen.blit(self.tiny.render("VIDA 160", True, (142, 236, 215)), (98, 63))
        self.screen.blit(self.tiny.render("24 BALAS", True, (142, 236, 215)), (98, 82))

        if hovered:
            panel = pygame.Rect(218, 14, 405, 98)
            pygame.draw.rect(self.screen, (7, 15, 23), panel, border_radius=8)
            pygame.draw.rect(self.screen, (96, 225, 202), panel, 2, border_radius=8)
            lines = (
                "Duas pistolas • alcance de 3 quadrados",
                "Dano-base: 12 por disparo • rajada alternada",
                "Protótipo atual: implantação e postura de espera",
            )
            for index, line in enumerate(lines):
                self.screen.blit(self.small.render(line, True, (222, 235, 229)), (232, 27 + index * 24))

    def draw_ui(self) -> None:
        top = pygame.Surface((WIDTH, 126), pygame.SRCALPHA)
        top.fill((4, 9, 15, 229))
        self.screen.blit(top, (0, 0))
        self.draw_card()

        pygame.draw.rect(self.screen, (46, 64, 76), RESET_RECT, border_radius=8)
        pygame.draw.rect(self.screen, (246, 180, 55), RESET_RECT, 2, border_radius=8)
        label = self.small.render("RECOMEÇAR  [R]", True, (250, 241, 210))
        self.screen.blit(label, label.get_rect(center=RESET_RECT.center))

        title = self.font.render("ENSAIO 1 — CARTA, TROPA E ZUMBI", True, (245, 248, 237))
        self.screen.blit(title, (642, 18))
        self.screen.blit(self.small.render(self.notice, True, (143, 229, 211)), (642, 55))
        hint = "Clique: selecionar/posicionar   |   R: recomeçar   |   ESC: sair"
        self.screen.blit(self.small.render(hint, True, (190, 196, 199)), (642, 82))

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.draw_cell_feedback()
        if self.guard is not None:
            self.guard.draw(self.screen)
        if self.zombie is not None:
            self.zombie.draw(self.screen)
        self.draw_ui()
        pygame.display.flip()

    def run(
        self,
        *,
        max_frames: int | None = None,
        demo: bool = False,
        screenshot: Path | None = None,
    ) -> int:
        running = True
        rendered = 0
        while running:
            dt = 1.0 / 60.0 if self.headless else min(0.05, self.clock.tick(60) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.reset()
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_cell = self.cell_at(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if RESET_RECT.collidepoint(event.pos):
                        self.reset()
                    elif CARD_RECT.collidepoint(event.pos) and self.guard is None:
                        self.selected = not self.selected
                        self.notice = "Agora escolha um quadrado iluminado." if self.selected else "Seleção cancelada."
                    elif self.selected:
                        cell = self.cell_at(event.pos)
                        if cell is not None:
                            self.deploy(*cell)

            if demo:
                self.update_demo(dt)
            self.update(dt)
            self.draw()
            rendered += 1
            if max_frames is not None and rendered >= max_frames:
                if screenshot is not None:
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(screenshot))
                running = False
        pygame.quit()
        return 0


def main() -> int:
    args = parse_args()
    app = Prototype(headless=args.headless)
    return app.run(
        max_frames=args.frames if args.headless else None,
        demo=args.demo,
        screenshot=args.screenshot,
    )


if __name__ == "__main__":
    raise SystemExit(main())
