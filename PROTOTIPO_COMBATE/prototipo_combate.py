"""Ensaio isolado das ações de combate aprovadas para tropas comuns.

Inclui disparo, recarga, dano no zumbi, mordida e dano no soldado. Não inclui
morte de unidades comuns; esse custo visual fica reservado a chefes e
subchefes, conforme a decisão atual do projeto.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pygame


WIDTH, HEIGHT = 1280, 720
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
CARD_ROOT = PROJECT_ROOT / "PROTOTIPO_CARTA_CAMPO"
CARD_ASSETS = CARD_ROOT / "assets"
SCENARIO = (
    PROJECT_ROOT
    / "CENARIOS_BETA4_CONCEITOS"
    / "prontos_1280x720"
    / "01_nova_york_terminal_helix_entrada_unica_v4.png"
)

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(CARD_ROOT))
from animation2d import AnimationClip, Entity, SpriteSheet  # noqa: E402
from prototipo_carta_campo import (  # noqa: E402
    load_two_row_sheet,
    normalize_cells,
    pad_animation_groups,
)


GROUND_Y = 406
GUARD_X = 500.0
ATTACK_RANGE = 338.0
BITE_DISTANCE = 116.0
MAGAZINE_SIZE = 4

BUTTON_FIRE = pygame.Rect(20, 18, 230, 48)
BUTTON_BITE = pygame.Rect(264, 18, 230, 48)
BUTTON_RESET = pygame.Rect(1086, 18, 174, 48)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=600)
    parser.add_argument("--mode", choices=("fire", "bite"), default="fire")
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def load_rows(path: Path, columns: int, rows: int, target_height: int) -> list[list[pygame.Surface]]:
    sheet = SpriteSheet.from_file(path)
    cells = sheet.slice_equal(columns, rows)
    return [
        normalize_cells(cells[row * columns : (row + 1) * columns], target_height)
        for row in range(rows)
    ]


def main_figure_rect(frame: pygame.Surface) -> pygame.Rect:
    """Retorna a silhueta principal, ignorando cápsulas e carregadores."""
    components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
    if not components:
        raise ValueError("a animação contém um quadro completamente transparente")
    return max(components, key=lambda rect: rect.width * rect.height)


def normalize_actor_height(
    frames: list[pygame.Surface], target_actor_height: int
) -> list[pygame.Surface]:
    """Iguala a altura do corpo sem usar VFX solto como parte da escala.

    Uma cápsula acima da cabeça ou um carregador caindo não pode encolher o
    Guarda. Cada pose é dimensionada pela silhueta corporal e depois o
    ``pad_animation_groups`` fixa o mesmo centro e a mesma base dos pés.
    """
    normalized: list[pygame.Surface] = []
    for frame in frames:
        actor = main_figure_rect(frame)
        content = frame.get_bounding_rect(min_alpha=8)
        factor = target_actor_height / actor.height
        crop = frame.subsurface(content).copy()
        size = (
            max(1, round(crop.get_width() * factor)),
            max(1, round(crop.get_height() * factor)),
        )
        normalized.append(pygame.transform.scale(crop, size))
    return normalized


def keep_main_figure(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    """Remove resíduos de outra fileira sem tocar no personagem principal."""
    cleaned: list[pygame.Surface] = []
    for frame in frames:
        source_mask = pygame.mask.from_surface(frame, threshold=8)
        components = source_mask.get_bounding_rects()
        if not components:
            cleaned.append(frame)
            continue
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


def keep_reload_props(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    """Mantém carregadores próximos às mãos, removendo invasões superiores."""
    cleaned: list[pygame.Surface] = []
    for frame in frames:
        components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
        if not components:
            cleaned.append(frame)
            continue
        main = max(components, key=lambda rect: rect.width * rect.height)
        result = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        result.blit(frame, main, main)
        minimum_prop_y = main.top + round(main.height * 0.34)
        action_zone = main.inflate(90, 24)
        for component in components:
            if component == main:
                continue
            if component.centery >= minimum_prop_y and action_zone.colliderect(component):
                result.blit(frame, component, component)
        cleaned.append(result)
    return cleaned


class CombatPrototype:
    def __init__(self, *, headless: bool = False, mode: str = "fire") -> None:
        pygame.init()
        self.headless = headless
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Soldados vs Zumbis — ensaio de combate")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16)
        self.tiny = pygame.font.SysFont("arial", 14, bold=True)
        self.background = pygame.image.load(str(SCENARIO)).convert()

        _, guard_idle = load_two_row_sheet(
            CARD_ASSETS / "guarda_rua_implantacao_idle_8x2_v1.png", 130
        )
        action_sheet = SpriteSheet.from_file(
            CARD_ASSETS / "guarda_rua_tiro_recarga_8x2_v2_pronto.png"
        )
        action_cells = action_sheet.slice_equal(8, 2)
        approved_actor_height = round(
            sum(main_figure_rect(frame).height for frame in guard_idle) / len(guard_idle)
        )
        guard_shoot = normalize_actor_height(action_cells[:8], approved_actor_height)
        guard_reload = normalize_actor_height(action_cells[8:], approved_actor_height)
        guard_hit = keep_main_figure(
            load_rows(CARD_ASSETS / "guarda_rua_dano_8x1_v2_limpo.png", 8, 1, 130)[0]
        )
        guard_groups = pad_animation_groups(
            {
                "idle": guard_idle,
                "shoot": guard_shoot,
                "reload": guard_reload,
                "hit": guard_hit,
            }
        )
        zombie_walk, zombie_idle = load_two_row_sheet(
            CARD_ASSETS / "caminhante_urbano_andando_idle_8x2_v1.png", 136
        )
        bite_sheet = SpriteSheet.from_file(
            CARD_ASSETS / "caminhante_urbano_mordida_4x2_v4_pronto.png"
        )
        approved_zombie_height = round(
            sum(main_figure_rect(frame).height for frame in zombie_idle)
            / len(zombie_idle)
        )
        zombie_bite = normalize_actor_height(
            bite_sheet.slice_equal(4, 2), approved_zombie_height
        )
        zombie_damage = load_rows(
            CARD_ASSETS / "caminhante_urbano_mordida_dano_8x2_v2_limpo.png",
            8,
            2,
            136,
        )[1]
        # A mordida foi reempacotada em 4x2 para que os braços não atravessem
        # células estreitas. O dano aprovado continua vindo da folha anterior.
        zombie_damage = keep_main_figure(zombie_damage)
        zombie_groups = pad_animation_groups(
            {
                "move": zombie_walk,
                "idle": zombie_idle,
                "bite": zombie_bite,
                "hit": zombie_damage,
            }
        )

        # A última fileira de queda da folha do Guarda não é registrada.
        self.guard_clips = {
            "idle": AnimationClip.uniform(guard_groups["idle"], fps=5.0, name="pronto"),
            "shoot": AnimationClip.uniform(
                guard_groups["shoot"], fps=10.0, loop=False, name="disparo"
            ),
            "reload": AnimationClip.timed(
                guard_groups["reload"],
                (0.20, 0.24, 0.28, 0.30, 0.28, 0.24, 0.20, 0.18),
                loop=False,
                name="recarga",
            ),
            "hit": AnimationClip.timed(
                guard_groups["hit"],
                (0.07, 0.07, 0.09, 0.11, 0.10, 0.09, 0.08, 0.10),
                loop=False,
                name="dano",
            ),
        }

        # Mordida e dano agora têm folhas próprias. Nenhuma das duas reutiliza
        # a caminhada ou tenta representar a ação apenas com flash de cor.
        self.zombie_clips = {
            "move": AnimationClip.uniform(zombie_groups["move"], fps=7.0, name="caminhada"),
            "idle": AnimationClip.uniform(zombie_groups["idle"], fps=4.5, name="ameaça"),
            "bite": AnimationClip.timed(
                zombie_groups["bite"],
                (0.11, 0.09, 0.09, 0.08, 0.11, 0.13, 0.11, 0.10),
                loop=False,
                name="mordida",
            ),
            "hit": AnimationClip.timed(
                zombie_groups["hit"],
                (0.06, 0.07, 0.08, 0.10, 0.10, 0.10, 0.09, 0.12),
                loop=False,
                name="dano",
            ),
        }

        self.mode = mode
        self.paused = False
        self.guard: Entity
        self.zombie: Entity
        self.ammo = MAGAZINE_SIZE
        self.shot_cooldown = 0.0
        self.shot_elapsed = 0.0
        self.shot_hit_applied = False
        self.bite_elapsed = 0.0
        self.bite_hit_applied = False
        self.bite_cooldown = 0.0
        self.bite_origin_x = 0.0
        self.zombie_hit_origin_x = 0.0
        self.guard_damage = 0
        self.zombie_damage = 0
        self.event_text = ""
        self.reset(mode)

    def reset(self, mode: str | None = None) -> None:
        if mode is not None:
            self.mode = mode
        self.guard = Entity(
            self.guard_clips,
            initial_state="idle",
            position=(GUARD_X, GROUND_Y),
            anchor="midbottom",
            auto_kill_state=None,
        )
        self.zombie = Entity(
            self.zombie_clips,
            initial_state="move",
            # A chegada completa já foi aprovada no ensaio anterior; aqui o
            # inimigo começa perto para o usuário chegar logo às ações.
            position=(900.0 if self.mode == "fire" else 800.0, GROUND_Y),
            anchor="midbottom",
            auto_kill_state=None,
        )
        self.zombie.velocity.x = -60.0 if self.mode == "fire" else -76.0
        self.ammo = MAGAZINE_SIZE
        self.shot_cooldown = 0.0
        self.shot_elapsed = 0.0
        self.shot_hit_applied = False
        self.bite_elapsed = 0.0
        self.bite_hit_applied = False
        self.bite_cooldown = 0.0
        self.bite_origin_x = 0.0
        self.zombie_hit_origin_x = 0.0
        self.guard_damage = 0
        self.zombie_damage = 0
        self.event_text = (
            "O Guarda só dispara quando o zumbi entra no alcance."
            if self.mode == "fire"
            else "O Caminhante avançará até a distância real de mordida."
        )

    @property
    def distance(self) -> float:
        return self.zombie.position.x - self.guard.position.x

    def start_shot(self) -> None:
        self.guard.set_state("shoot", restart=True)
        self.ammo -= 1
        self.shot_elapsed = 0.0
        self.shot_hit_applied = False
        self.event_text = f"Disparo alternado — {self.ammo} bala(s) restantes."

    def start_reload(self) -> None:
        self.guard.set_state("reload", restart=True)
        self.event_text = "Recarga completa: retirar, descartar e inserir os carregadores."

    def update_fire_mode(self, dt: float) -> None:
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        if self.distance > ATTACK_RANGE and self.zombie.state == "move":
            return

        self.zombie.velocity.x = 0.0
        if self.zombie.state == "move":
            self.zombie.set_state("idle")

        if self.guard.state == "shoot":
            self.shot_elapsed += dt
            if self.shot_elapsed >= 0.28 and not self.shot_hit_applied:
                self.shot_hit_applied = True
                self.zombie_damage += 12
                self.zombie_hit_origin_x = self.zombie.position.x
                self.zombie.set_state("hit", restart=True)
                self.event_text = f"Caminhante recebeu dano. Total do ensaio: {self.zombie_damage}."
            if self.guard.animation.finished:
                self.guard.set_state("idle")
                self.shot_cooldown = 0.34
        elif self.guard.state == "reload":
            if self.guard.animation.finished:
                self.ammo = MAGAZINE_SIZE
                self.guard.set_state("idle")
                self.shot_cooldown = 0.25
                self.event_text = "Recarga concluída; as duas pistolas voltaram à mira."
        elif self.guard.state == "idle" and self.shot_cooldown <= 0.0:
            if self.ammo <= 0:
                self.start_reload()
            elif self.zombie.state != "hit":
                self.start_shot()

        if self.zombie.state == "hit":
            recoil = (0, 3, 7, 10, 8, 5, 2, 0)[self.zombie.animation.frame_index]
            self.zombie.position.x = self.zombie_hit_origin_x + recoil
            if self.zombie.animation.finished:
                self.zombie.position.x = self.zombie_hit_origin_x
                self.zombie.set_state("idle")

    def start_bite(self) -> None:
        self.zombie.set_state("bite", restart=True)
        self.bite_origin_x = self.zombie.position.x
        self.bite_elapsed = 0.0
        self.bite_hit_applied = False
        self.event_text = "Mordida iniciada: apoio dos pés, avanço e contato."

    def update_bite_mode(self, dt: float) -> None:
        self.bite_cooldown = max(0.0, self.bite_cooldown - dt)
        if self.distance > BITE_DISTANCE and self.zombie.state == "move":
            return

        self.zombie.velocity.x = 0.0
        if self.zombie.state == "move":
            self.zombie.set_state("idle")
            self.bite_cooldown = 0.25

        if self.zombie.state == "bite":
            self.bite_elapsed += dt
            lunge = (0, 2, 7, 14, 23, 21, 11, 0)[self.zombie.animation.frame_index]
            self.zombie.position.x = self.bite_origin_x - lunge
            if self.zombie.animation.frame_index >= 4 and not self.bite_hit_applied:
                self.bite_hit_applied = True
                self.guard_damage += 18
                self.guard.set_state("hit", restart=True)
                self.event_text = f"Guarda recebeu dano. Total do ensaio: {self.guard_damage}."
            if self.zombie.animation.finished:
                self.zombie.position.x = self.bite_origin_x
                self.zombie.set_state("idle")
                self.bite_cooldown = 0.75
        elif self.zombie.state == "idle" and self.bite_cooldown <= 0.0:
            self.start_bite()

        if self.guard.state == "hit" and self.guard.animation.finished:
            self.guard.set_state("idle")

    def update(self, dt: float) -> None:
        if self.paused:
            return
        self.guard.update(dt)
        self.zombie.update(dt)
        if self.mode == "fire":
            self.update_fire_mode(dt)
        else:
            self.update_bite_mode(dt)

    def draw_button(self, rect: pygame.Rect, label: str, active: bool) -> None:
        pygame.draw.rect(self.screen, (36, 76, 67) if active else (36, 53, 65), rect, border_radius=8)
        pygame.draw.rect(self.screen, (247, 183, 57) if active else (101, 223, 202), rect, 2, border_radius=8)
        text = self.small.render(label, True, (249, 245, 222))
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_status(self) -> None:
        panel = pygame.Surface((WIDTH, 126), pygame.SRCALPHA)
        panel.fill((4, 9, 15, 232))
        self.screen.blit(panel, (0, 0))
        self.draw_button(BUTTON_FIRE, "1  TIRO + RECARGA", self.mode == "fire")
        self.draw_button(BUTTON_BITE, "2  MORDIDA + DANO", self.mode == "bite")
        self.draw_button(BUTTON_RESET, "R  RECOMEÇAR", False)

        title = "TESTE DE COMBATE ANIMADO"
        self.screen.blit(self.font.render(title, True, (244, 247, 236)), (518, 20))
        self.screen.blit(self.small.render(self.event_text, True, (139, 229, 210)), (518, 53))
        values = (
            f"Munição: {self.ammo}/{MAGAZINE_SIZE}     "
            f"Dano no zumbi: {self.zombie_damage}     Dano no soldado: {self.guard_damage}"
        )
        self.screen.blit(self.small.render(values, True, (247, 190, 72)), (518, 78))
        hint = "1/2: trocar ensaio   |   P: pausar   |   R: reiniciar   |   ESC: sair"
        self.screen.blit(self.tiny.render(hint, True, (190, 199, 201)), (518, 101))

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.guard.draw(self.screen)
        self.zombie.draw(self.screen)
        self.draw_status()
        pygame.display.flip()

    def run(self, *, max_frames: int | None = None, screenshot: Path | None = None) -> int:
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
                    elif event.key == pygame.K_1:
                        self.reset("fire")
                    elif event.key == pygame.K_2:
                        self.reset("bite")
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if BUTTON_FIRE.collidepoint(event.pos):
                        self.reset("fire")
                    elif BUTTON_BITE.collidepoint(event.pos):
                        self.reset("bite")
                    elif BUTTON_RESET.collidepoint(event.pos):
                        self.reset()
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
    prototype = CombatPrototype(headless=args.headless, mode=args.mode)
    return prototype.run(
        max_frames=args.frames if args.headless else None,
        screenshot=args.screenshot,
    )


if __name__ == "__main__":
    raise SystemExit(main())
