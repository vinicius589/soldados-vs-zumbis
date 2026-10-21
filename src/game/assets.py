"""Carregamento e preparação de recursos da campanha."""
from __future__ import annotations

from src.game.runtime import *  # noqa: F403

class FontBook:
    def __init__(self) -> None:
        self.title = pygame.font.SysFont("arial", 45, bold=True)
        self.h1 = pygame.font.SysFont("arial", 28, bold=True)
        self.h2 = pygame.font.SysFont("arial", 20, bold=True)
        self.body = pygame.font.SysFont("arial", 16)
        self.small = pygame.font.SysFont("arial", 13)
        self.tiny = pygame.font.SysFont("arial", 11)

class Assets:
    """Carrega uma única fonte por quadro para manter a abertura leve."""

    def __init__(self) -> None:
        self.images: dict[str, pygame.Surface] = {}
        self.unit_sprites: dict[str, list[pygame.Surface]] = {}
        self.unit_l2_sprites: dict[str, list[pygame.Surface]] = {}
        self.zombie_sprites: dict[str, list[pygame.Surface]] = {}
        self.animation_frames: dict[str, list[pygame.Surface]] = {}
        self.effect_frames: dict[str, list[pygame.Surface]] = {}
        self.boss_portraits: dict[str, list[pygame.Surface]] = {}
        self.scale_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self.trim_cache: dict[int, pygame.Surface] = {}
        self.production_clips: dict[str, dict] | None = None
        # Somente telas, cenários já aprovados e VFX genéricos são carregados
        # aqui. Todo atlas antigo de soldado, zumbi ou chefe foi retirado da
        # produção; os atores ativos vêm exclusivamente de
        # ``assets/beta4_producao`` (elenco regional completo e doze ameaças por
        # região na integração jogável atual).
        self.jobs: list[tuple[str, Path, str]] = [
            ("loading_beta3", ASSET_DIR / "loading_beta3_reference.png", "image"),
            ("menu", ASSET_DIR / "menu.png", "image"),
            *[
                (f"{region}_bg", ASSET_DIR / info["bg"], "image")
                for region, info in REGIONS.items()
            ],
            (
                "elemental_effects",
                ASSET_DIR / "elemental_effects_sheet_beta4_v2.png",
                "effects_4x3",
            ),
            (
                "combat_effects",
                ASSET_DIR / "combat_effects_sheet_beta4.png",
                "effects_4x3",
            ),
            (
                "ability_effects",
                ASSET_DIR / "ability_effects_sheet_beta4.png",
                "effects_4x3",
            ),
            (
                "projectile_sprites",
                ASSET_DIR / "projectile_sprites_sheet_beta4.png",
                "effects_4x3",
            ),
            (
                "city_boss_portraits",
                PRODUCTION_ASSET_DIR / "city_boss_portraits_3x1_v1.png",
                "portraits_3x1",
            ),
            (
                "desert_boss_portraits",
                PRODUCTION_ASSET_DIR / "desert_boss_portraits_3x1_v1.png",
                "portraits_3x1",
            ),
            (
                "beach_boss_portraits",
                PRODUCTION_ASSET_DIR / "beach_boss_portraits_3x1_v1.png",
                "portraits_3x1",
            ),
            (
                "muzzle_cycle",
                PRODUCTION_ASSET_DIR / "muzzle_cycle_source_v1.png",
                "animation_8x1",
            ),
        ]
        self.loaded = 0
        self.error: str | None = None

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def complete(self) -> bool:
        return self.loaded >= self.total

    def load_next(self) -> None:
        if self.complete:
            return
        key, path, kind = self.jobs[self.loaded]
        try:
            source = pygame.image.load(str(path)).convert_alpha()
            if kind == "image":
                if key.endswith("_bg"):
                    self.images[key] = self.fit_four_lane_background(
                        source, key.split("_")[0]
                    )
                else:
                    self.images[key] = pygame.transform.smoothscale(
                        source, (WIDTH, HEIGHT)
                    )
            elif kind == "sprite":
                self.images[key] = source
            elif kind == "animation":
                self.animation_frames[key] = self.slice_grid(source, 4, 2)
            elif kind == "animation_4x3":
                self.animation_frames[key] = self.slice_grid(source, 4, 3)
            elif kind == "animation_8x1":
                self.animation_frames[key] = [
                    self.trim_alpha(frame) for frame in self.slice_grid(source, 8, 1)
                ]
            elif kind == "portraits_3x1":
                region = key.split("_")[0]
                self.boss_portraits[region] = [
                    self.portrait_actor(frame)
                    for frame in self.slice_grid(source, 3, 1)
                ]
            elif kind == "effects_4x3":
                self.effect_frames[key] = [
                    self.trim_alpha(frame) for frame in self.slice_grid(source, 4, 3)
                ]
            else:
                sprites = self.slice_atlas(source)
                if kind == "units":
                    self.unit_sprites[key.split("_")[0]] = sprites
                elif kind == "units_l2":
                    self.unit_l2_sprites[key.split("_")[0]] = sprites
                else:
                    self.zombie_sprites[key.split("_")[0]] = sprites
        except pygame.error as exc:
            self.error = f"Falha ao carregar {path.name}: {exc}"
            # Um arquivo ausente gera mensagem explícita na tela de carga. O
            # fallback fica transparente para nunca fingir uma animação com
            # círculo, bloco colorido ou outro símbolo provisório.
            placeholder = pygame.Surface((1, 1), pygame.SRCALPHA)
            if kind == "image":
                self.images[key] = pygame.transform.smoothscale(
                    placeholder, (WIDTH, HEIGHT)
                )
            elif kind == "sprite":
                self.images[key] = placeholder
            elif kind == "animation":
                self.animation_frames[key] = [placeholder] * 8
            elif kind == "animation_4x3":
                self.animation_frames[key] = [placeholder] * 12
            elif kind == "animation_8x1":
                self.animation_frames[key] = [placeholder] * 8
            elif kind == "portraits_3x1":
                self.boss_portraits[key.split("_")[0]] = [placeholder] * 3
            elif kind == "effects_4x3":
                self.effect_frames[key] = [placeholder] * 12
            elif kind == "units":
                self.unit_sprites[key.split("_")[0]] = [placeholder] * 12
            elif kind == "units_l2":
                self.unit_l2_sprites[key.split("_")[0]] = [placeholder] * 12
            else:
                self.zombie_sprites[key.split("_")[0]] = [placeholder] * 12
        self.loaded += 1

    @staticmethod
    def fit_four_lane_background(source: pygame.Surface, region: str) -> pygame.Surface:
        """Preserva a continuidade da pintura final sem remontar faixas.

        Os novos cenários já foram produzidos em 1280x720 e seus limites estão
        descritos em ``LANE_BOUNDS``. Recortar e esticar bandas individualmente
        quebrava calçadas, pedras, água e a entrada dos zumbis.
        """
        if source.get_size() == (WIDTH, HEIGHT):
            return source.copy()
        return pygame.transform.smoothscale(source, (WIDTH, HEIGHT))

    @staticmethod
    def slice_atlas(source: pygame.Surface) -> list[pygame.Surface]:
        width, height = source.get_size()
        tiles: list[pygame.Surface] = []
        for row in range(3):
            for col in range(4):
                rect = pygame.Rect(
                    col * width // 4, row * height // 3, width // 4, height // 3
                )
                tile = source.subsurface(rect).copy()
                if tile.get_flags() & pygame.SRCALPHA == 0:
                    tile.set_colorkey((0, 0, 0))
                tiles.append(tile)
        return tiles

    @staticmethod
    def slice_grid(
        source: pygame.Surface, columns: int, rows: int
    ) -> list[pygame.Surface]:
        """Recorta uma folha regular preservando seu canal alfa original."""
        width, height = source.get_size()
        frames: list[pygame.Surface] = []
        for row in range(rows):
            for column in range(columns):
                rect = pygame.Rect(
                    column * width // columns,
                    row * height // rows,
                    width // columns,
                    height // rows,
                )
                frames.append(source.subsurface(rect).copy())
        return frames

    @staticmethod
    def trim_alpha(source: pygame.Surface) -> pygame.Surface:
        """Remove apenas a margem transparente de um VFX ou projétil."""
        bounds = source.get_bounding_rect(min_alpha=8)
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return source.subsurface(bounds).copy()

    @staticmethod
    def portrait_actor(source: pygame.Surface) -> pygame.Surface:
        """Mantém o chefe inteiro e descarta fragmentos soltos entre células."""
        mask = pygame.mask.from_surface(source, threshold=8)
        components = mask.connected_components(minimum=6)
        if not components:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        main = max(components, key=lambda component: component.count())
        main_rect = main.get_bounding_rects()[0]
        kept = pygame.Surface(source.get_size(), pygame.SRCALPHA)
        for component in components:
            rects = component.get_bounding_rects()
            if not rects:
                continue
            rect = rects[0]
            # Braços, armas e tubos podem ser componentes separados, porém
            # continuam próximos do corpo. Pedaços vindos do retrato vizinho
            # ficam colados à borda e longe da figura principal.
            gap_x = max(
                0, max(main_rect.left, rect.left) - min(main_rect.right, rect.right)
            )
            gap_y = max(
                0, max(main_rect.top, rect.top) - min(main_rect.bottom, rect.bottom)
            )
            touches_side = rect.left <= 1 or rect.right >= source.get_width() - 1
            if component is not main and (touches_side or gap_x > 18 or gap_y > 18):
                continue
            alpha = component.to_surface(
                setcolor=(255, 255, 255, 255),
                unsetcolor=(255, 255, 255, 0),
            )
            fragment = source.copy()
            fragment.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            kept.blit(fragment, (0, 0))
        bounds = kept.get_bounding_rect(min_alpha=8)
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return kept.subsurface(bounds).copy()

    def base_unit(self, region: str, index: int) -> pygame.Surface:
        sprites = self.unit_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def unit(self, region: str, index: int, level: int = 1) -> pygame.Surface:
        """N1 usa o atlas base; N2 recebe silhueta e uniforme próprios."""
        if level >= 2:
            sprites = self.unit_l2_sprites.get(region, [])
            if sprites:
                return sprites[index % len(sprites)]
        return self.base_unit(region, index)

    def zombie(self, region: str, index: int) -> pygame.Surface:
        sprites = self.zombie_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def scaled(
        self, sprite: pygame.Surface, width: float, height: float
    ) -> pygame.Surface:
        """Evita redimensionar os mesmos retratos gigantes a cada quadro."""
        size = (max(1, int(width)), max(1, int(height)))
        key = (id(sprite), *size)
        cached = self.scale_cache.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(sprite, size)
            self.scale_cache[key] = cached
        return cached

    def trimmed(self, sprite: pygame.Surface) -> pygame.Surface:
        """Remove só a margem transparente do recorte usado no campo.

        Cartas continuam usando o enquadramento integral do atlas. Em batalha,
        o recorte justo garante que a última linha opaca da bota, roda ou casco
        coincida de verdade com a âncora do terreno.
        """
        key = id(sprite)
        cached = self.trim_cache.get(key)
        if cached is not None:
            return cached
        bounds = sprite.get_bounding_rect(min_alpha=8)
        if bounds.width <= 1 or bounds.height <= 1:
            self.trim_cache[key] = sprite
            return sprite
        bounds = bounds.inflate(4, 4).clip(sprite.get_rect())
        trimmed = sprite.subsurface(bounds).copy()
        self.trim_cache[key] = trimmed
        return trimmed

    def actor_sources(self) -> list[pygame.Surface]:
        """Lista exatamente os recortes que poderão virar atores OpenGL."""
        self.prepare_production_animations()
        candidates: list[pygame.Surface] = []
        for store in (
            self.unit_sprites,
            self.unit_l2_sprites,
            self.zombie_sprites,
            self.animation_frames,
        ):
            for sprites in store.values():
                candidates.extend(sprites)
        for key, _path, kind in self.jobs:
            if kind == "sprite" and key != "beta4_toxic_impact" and key in self.images:
                candidates.append(self.images[key])
        if self.production_clips:
            for actor_clips in self.production_clips.values():
                for clip in actor_clips.values():
                    candidates.extend(clip.frames)
        unique: list[pygame.Surface] = []
        seen: set[int] = set()
        for sprite in candidates:
            trimmed = self.trimmed(sprite)
            if id(trimmed) not in seen:
                seen.add(id(trimmed))
                unique.append(trimmed)
        return unique

    def prepare_production_animations(self) -> None:
        """Pré-carrega somente as folhas novas do elenco jogável atual."""
        if self.production_clips is None:
            self.production_clips = build_production_clips()

    def new_production_animation(self, actor: str) -> AnimationManager:
        self.prepare_production_animations()
        assert self.production_clips is not None
        return new_production_animation(self.production_clips, actor)
