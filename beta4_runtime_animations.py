"""Animações aprovadas da Beta 4 prontas para o combate real.

Este módulo é a ponte entre as folhas validadas nos protótipos e a lógica da
partida. Ele mantém todos os estados de um ator na mesma caixa, com o mesmo
pivô e a mesma linha dos pés. Assim trocar de andar para atirar, recarregar,
morder ou receber dano nunca aumenta o personagem nem corta seus membros.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from animation2d import AnimationClip, AnimationManager, SpriteSheet


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "PROTOTIPO_CARTA_CAMPO" / "assets"


def _main_figure(frame: pygame.Surface) -> pygame.Rect:
    components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
    if not components:
        raise ValueError("a animação contém um quadro completamente transparente")
    return max(components, key=lambda rect: rect.width * rect.height)


def _keep_main_figure(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    """Remove resíduos isolados sem recortar braços, pernas ou armas do ator."""
    cleaned: list[pygame.Surface] = []
    for frame in frames:
        source_mask = pygame.mask.from_surface(frame, threshold=8)
        if not source_mask.get_bounding_rects():
            raise ValueError("a animação contém um quadro completamente transparente")
        main_mask = source_mask.connected_component()
        mask_surface = main_mask.to_surface(
            setcolor=(255, 255, 255, 255),
            unsetcolor=(255, 255, 255, 0),
        )
        keep_alpha = pygame.surfarray.array_alpha(mask_surface)
        result = frame.copy()
        alpha = pygame.surfarray.pixels_alpha(result)
        alpha[keep_alpha <= 8] = 0
        del alpha
        cleaned.append(result)
    return cleaned


def _scale_to_height(surface: pygame.Surface, target_height: int) -> pygame.Surface:
    factor = target_height / max(1, surface.get_height())
    return pygame.transform.scale(
        surface,
        (max(1, round(surface.get_width() * factor)), target_height),
    )


def _normalize_cells(frames: list[pygame.Surface], target_height: int) -> list[pygame.Surface]:
    """Recorta poses e recompõe a sequência com pés e centro constantes."""
    bounds = [frame.get_bounding_rect(min_alpha=8) for frame in frames]
    if any(rect.width <= 0 or rect.height <= 0 for rect in bounds):
        raise ValueError("a folha contém um quadro completamente transparente")
    width = max(rect.width for rect in bounds) + 8
    height = max(rect.height for rect in bounds) + 6
    normalized: list[pygame.Surface] = []
    for frame, rect in zip(frames, bounds):
        crop = frame.subsurface(rect).copy()
        canvas = pygame.Surface((width, height), pygame.SRCALPHA)
        canvas.blit(crop, ((width - crop.get_width()) // 2, height - crop.get_height() - 3))
        normalized.append(_scale_to_height(canvas, target_height))
    return normalized


def _normalize_actor_height(
    frames: list[pygame.Surface], target_actor_height: int
) -> list[pygame.Surface]:
    """Dimensiona pelo corpo principal, não por cápsulas ou carregadores soltos."""
    normalized: list[pygame.Surface] = []
    for frame in frames:
        actor = _main_figure(frame)
        content = frame.get_bounding_rect(min_alpha=8)
        factor = target_actor_height / max(1, actor.height)
        crop = frame.subsurface(content).copy()
        normalized.append(
            pygame.transform.scale(
                crop,
                (
                    max(1, round(crop.get_width() * factor)),
                    max(1, round(crop.get_height() * factor)),
                ),
            )
        )
    return normalized


def _pad_groups(
    groups: dict[str, list[pygame.Surface]],
    *,
    horizontal_padding: int = 6,
    top_padding: int = 4,
) -> dict[str, list[pygame.Surface]]:
    """Coloca todos os estados numa caixa única sem reescalar o corpo."""
    frames = [frame for group in groups.values() for frame in group]
    geometry: list[tuple[pygame.Surface, pygame.Rect]] = [
        (frame, _main_figure(frame)) for frame in frames
    ]
    min_x = min(-main.centerx for frame, main in geometry)
    max_x = max(frame.get_width() - main.centerx for frame, main in geometry)
    min_y = min(-main.bottom for frame, main in geometry)
    max_y = max(frame.get_height() - main.bottom for frame, main in geometry)
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


def _two_rows(path: Path, target_height: int) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
    frames = _keep_main_figure(SpriteSheet.from_file(path).slice_equal(8, 2))
    normalized = _normalize_cells(frames, target_height)
    return normalized[:8], normalized[8:]


def build_approved_clips() -> dict[str, dict[str, AnimationClip]]:
    """Carrega uma vez as folhas aprovadas e devolve clipes compartilháveis."""
    guard_move, guard_idle = _two_rows(
        ASSETS / "guarda_rua_implantacao_idle_8x2_v1.png", 130
    )
    action_cells = SpriteSheet.from_file(
        ASSETS / "guarda_rua_tiro_recarga_8x2_v2_pronto.png"
    ).slice_equal(8, 2)
    approved_guard_height = round(
        sum(_main_figure(frame).height for frame in guard_idle) / len(guard_idle)
    )
    guard_shoot = _normalize_actor_height(action_cells[:8], approved_guard_height)
    guard_reload = _normalize_actor_height(action_cells[8:], approved_guard_height)
    guard_hit = _keep_main_figure(
        _normalize_cells(
            SpriteSheet.from_file(
                ASSETS / "guarda_rua_dano_8x1_v2_limpo.png"
            ).slice_equal(8, 1),
            130,
        )
    )
    guard = _pad_groups(
        {
            "move": guard_move,
            "idle": guard_idle,
            "shoot": guard_shoot,
            "reload": guard_reload,
            "hit": guard_hit,
        }
    )

    walker_move, walker_idle = _two_rows(
        ASSETS / "caminhante_urbano_andando_idle_8x2_v1.png", 136
    )
    approved_walker_height = round(
        sum(_main_figure(frame).height for frame in walker_idle) / len(walker_idle)
    )
    walker_bite = _normalize_actor_height(
        SpriteSheet.from_file(
            ASSETS / "caminhante_urbano_mordida_4x2_v4_pronto.png"
        ).slice_equal(4, 2),
        approved_walker_height,
    )
    damage_cells = SpriteSheet.from_file(
        ASSETS / "caminhante_urbano_mordida_dano_8x2_v2_limpo.png"
    ).slice_equal(8, 2)[8:]
    walker_hit = _keep_main_figure(_normalize_cells(damage_cells, 136))
    walker = _pad_groups(
        {
            "move": walker_move,
            "idle": walker_idle,
            "bite": walker_bite,
            "hit": walker_hit,
        }
    )

    return {
        "guard": {
            "move": AnimationClip.uniform(guard["move"], fps=8.0, name="implantação"),
            "idle": AnimationClip.uniform(guard["idle"], fps=5.0, name="pronto"),
            "shoot": AnimationClip.uniform(
                guard["shoot"], fps=10.0, loop=False, name="disparo"
            ),
            "reload": AnimationClip.timed(
                guard["reload"],
                (0.20, 0.24, 0.28, 0.30, 0.28, 0.24, 0.20, 0.18),
                loop=False,
                name="recarga",
            ),
            "hit": AnimationClip.timed(
                guard["hit"],
                (0.07, 0.07, 0.09, 0.11, 0.10, 0.09, 0.08, 0.10),
                loop=False,
                name="dano",
            ),
        },
        "walker": {
            "move": AnimationClip.uniform(walker["move"], fps=7.0, name="caminhada"),
            "idle": AnimationClip.uniform(walker["idle"], fps=4.5, name="ameaça"),
            "bite": AnimationClip.timed(
                walker["bite"],
                (0.11, 0.09, 0.09, 0.08, 0.11, 0.13, 0.11, 0.10),
                loop=False,
                name="mordida",
            ),
            "hit": AnimationClip.timed(
                walker["hit"],
                (0.06, 0.07, 0.08, 0.10, 0.10, 0.10, 0.09, 0.12),
                loop=False,
                name="dano",
            ),
        },
    }


def new_animation(
    clips: dict[str, dict[str, AnimationClip]], actor: str
) -> AnimationManager:
    """Cria um reprodutor independente usando as superfícies pré-carregadas."""
    initial = "idle" if actor == "guard" else "move"
    return AnimationManager(clips[actor], initial_state=initial)

