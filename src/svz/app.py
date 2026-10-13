"""Inicialização, ciclo principal, navegação e entrada do jogador."""
from __future__ import annotations

from svz.scenarios import ScenarioRuntime
from svz.presenter import ActorCommand
from svz.presenter import OpenGLPresenter
import math
import logging
import random
import os
import pygame

from .assets import (
    Assets,
    FontBook,
)
from .audio import (
    AudioSystem,
)
from .battle import (
    Battle,
)
from .config import (
    FPS,
    GOLD,
    GRAY,
    HEIGHT,
    LAST_PLACEABLE_COLUMN,
    ROWS,
    TEAL,
    TOTAL_WAVES,
    VERSION,
    WIDTH,
)
from .content import (
    BOSSES,
    DEFENSES,
    ENEMIES,
    PROMOTIONS,
    REGIONS,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
)
from .entities import (
    Defender,
    Enemy,
    Projectile,
)
from .motion import (
    ActorMotion,
    VisualEffect,
)
from .persistence import (
    load_save,
    save_campaign,
)
from .rendering import (
    GameRenderer,
)


from .video import VideoDisplay
from .session_store import SessionStore
from .snapshot import capture, activate

logger = logging.getLogger(__name__)
AUTOSAVE_SECONDS = 10.0


class Game:
    def __init__(self, *, integration_preview: bool = False, save_path=None) -> None:
        self.renderer = GameRenderer(self)
        pygame.init()
        pygame.display.set_caption(f"Soldados vs Zumbis — {VERSION}")
        self.presenter: OpenGLPresenter | None = None
        self.renderer_error = ""
        self.renderer_label = "SOFTWARE · CPU/RAM"
        self.actor_commands: list[ActorCommand] = []
        self.overlay_surface: pygame.Surface | None = None
        self.video = VideoDisplay(save_path)
        self.video_notice = ""
        self.video_notice_left = 0.0
        try:
            self.world_surface = self._create_display()
        except pygame.error:
            if not self.video.fullscreen:
                raise
            logger.exception("Tela cheia indisponível; iniciando em janela.")
            self.video.fullscreen = False
            self.world_surface = self._create_display()
            self.video_notice = "Tela cheia indisponível. O jogo iniciou em janela; tente F11."
            self.video_notice_left = 8.0
        self.screen = self.world_surface
        self.clock = pygame.time.Clock()
        self.fonts = FontBook()
        self.assets = Assets()
        self.scenario_runtime = ScenarioRuntime()
        self.audio = AudioSystem()
        # Mouse continua sendo o padrão solicitado. O modo Teclado habilita
        # um cursor de grade próprio sem alterar as regras de posicionamento.
        self.control_mode = "mouse"
        self.integration_preview = bool(integration_preview)
        self.gpu_preload_queue: list[pygame.Surface] = []
        self.gpu_preloaded = 0
        self.gpu_queue_ready = False
        self.running = True
        self.scene = "loading"
        self.scene_elapsed = 0.0
        self.save_path = save_path
        self.save_error = False
        self.save = load_save(save_path)
        self.session_store = SessionStore(save_path)
        self.pending_snapshot = self.session_store.load()
        self.session_notice = self.session_store.error
        self.autosave_elapsed = 0.0
        self.suspended_random = None
        self.region = "city"
        self.difficulty = "medium"
        self.selection: list[tuple[str, str]] = []
        self.battle: Battle | None = None
        self.dossier_kind = "units"
        self.dossier_page = 0
        self.character_region = "city"
        self.character_index = 0
        self.selection_carousel_index = 0
        self.selection_inspect_key: str | None = None
        self.story_page = 0
        self.hover_card: tuple[str, str] | None = None

    def _create_display(self) -> pygame.Surface:
        """Usa CPU/RAM por padrão; OpenGL só existe como opção explícita."""
        requested = os.environ.get("SVZ_RENDERER", "software").strip().lower()
        dummy_driver = os.environ.get("SDL_VIDEODRIVER", "").strip().lower() == "dummy"
        if requested in {"opengl", "gpu"} and not dummy_driver:
            try:
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
                pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
                self.video.create_mode(pygame.OPENGL | pygame.DOUBLEBUF)
                presenter = OpenGLPresenter(WIDTH, HEIGHT)
                self.presenter = presenter
                self.renderer_label = presenter.info.label
                self.overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA, 32)
                return pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA, 32)
            except Exception as exc:  # driver ausente ou OpenGL muito antigo
                self.renderer_error = f"{type(exc).__name__}: {exc}"
                if self.presenter is not None:
                    self.presenter.close()
                    self.presenter = None
                pygame.display.quit()
                pygame.display.init()
                pygame.display.set_caption(f"Soldados vs Zumbis — {VERSION}")
        self.video.create_mode()
        self.renderer_label = "SOFTWARE · CPU/RAM"
        self.overlay_surface = None
        return pygame.Surface((WIDTH, HEIGHT)).convert()

    def present_frame(self) -> None:
        """Entrega o quadro ao compositor escolhido sem duplicar a lógica."""
        if self.presenter is None:
            self.video.present(self.world_surface)
            return
        tint = REGIONS.get(self.battle.region if self.battle else self.region, REGIONS["city"])["accent"]
        self.presenter.present(
            self.world_surface,
            actors=self.actor_commands,
            overlay=self.overlay_surface,
            elapsed=self.scene_elapsed,
            tint=tint,
            strength=1.0 if self.scene == "battle" else 0.42,
        )

    def toggle_fullscreen(self) -> bool:
        """Troca somente a apresentação; a partida e os recursos seguem vivos."""
        previous = self.video.fullscreen
        if self.presenter is not None:
            self.presenter.close()
            self.presenter = None
        self.video.fullscreen = not previous
        succeeded = True
        try:
            self.world_surface = self._create_display()
        except pygame.error:
            logger.exception("Não foi possível alternar a exibição.")
            self.video.fullscreen = previous
            try:
                self.world_surface = self._create_display()
            except pygame.error:
                self.video.fullscreen = False
                self.world_surface = self._create_display()
            self.video_notice = "Não foi possível trocar a exibição. Tente novamente com F11."
            self.video_notice_left = 8.0
            succeeded = False
        self.screen = self.world_surface
        self.gpu_preload_queue = []
        self.gpu_preloaded = 0
        self.gpu_queue_ready = False
        self.hover_card = None
        if succeeded:
            self.video_notice = ""
            if not self.video.save_preference():
                self.video_notice = "Exibição alterada, mas não foi possível guardar a preferência."
                self.video_notice_left = 8.0
        return succeeded

    def run(self) -> None:
        try:
            while self.running:
                dt = min(0.05, self.clock.tick(FPS) / 1000.0)
                self.scene_elapsed += dt
                self.handle_events()
                self.update(dt)
                self.draw()
                self.present_frame()
        finally:
            self.checkpoint()
            if self.presenter is not None:
                self.presenter.close()
            pygame.quit()

    def update(self, dt: float) -> None:
        self.video_notice_left = max(0.0, self.video_notice_left - dt)
        if not self.video_notice_left:
            self.video_notice = ""
        self.audio.sync(
            self.scene,
            self.battle.region if self.scene == "battle" and self.battle else None,
        )
        self.scenario_runtime.update(dt, self.battle if self.scene == "battle" else None)
        if self.scene == "loading":
            if not self.assets.complete:
                self.assets.load_next()
            if self.assets.complete:
                self.assets.prepare_production_animations()
                if self.presenter is not None:
                    if not self.gpu_queue_ready:
                        self.gpu_preload_queue = self.assets.actor_sources()
                        self.gpu_queue_ready = True
                    batch_end = min(len(self.gpu_preload_queue), self.gpu_preloaded + 8)
                    if batch_end > self.gpu_preloaded:
                        self.presenter.preload_sprites(self.gpu_preload_queue[self.gpu_preloaded:batch_end])
                        self.gpu_preloaded = batch_end
                    if self.gpu_preloaded < len(self.gpu_preload_queue):
                        return
                # Mesmo o executável de integração começa no menu INICIAR.
                # O sinalizador mantém as ondas reduzidas, mas nunca pula a
                # navegação escolhida pelo jogador nem abre o mapa sozinho.
                self.scene = "title"
                self.scene_elapsed = 0
        elif self.scene == "battle" and self.battle:
            was_finished = self.battle.finished
            previous_wave = self.battle.wave
            if not was_finished:
                self.battle.update(dt)
            if not self.battle.paused and not was_finished:
                self.autosave_elapsed += dt
            if (self.autosave_elapsed >= AUTOSAVE_SECONDS or
                    self.battle.wave != previous_wave or self.battle.finished != was_finished):
                self.checkpoint()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.request_quit()
            elif event.type == pygame.KEYDOWN:
                video_key = event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and getattr(event, "mod", 0) & pygame.KMOD_ALT)
                if video_key and getattr(event, "repeat", False):
                    continue
                self.handle_key(event.key, getattr(event, "mod", 0))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.video.mouse_position(event.pos)
                if pos != (-1, -1):
                    self.handle_click(pos)
            elif event.type == pygame.MOUSEMOTION:
                self.hover_card = None

    def handle_key(self, key: int, mod: int = 0) -> None:
        if key == pygame.K_F11 or (key == pygame.K_RETURN and mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return
        if key == pygame.K_ESCAPE:
            if self.scene == "title":
                self.request_quit()
            elif self.scene == "battle":
                self.leave_battle_to_title()
            else:
                self.scene = "title"
            return
        if self.scene in ("confirm_new", "confirm_exit"):
            # Só um clique explícito confirma uma ação que perde a partida atual.
            return
        if self.scene == "title" and key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.can_continue():
                self.resume_battle()
            else:
                self.request_new_game()
        elif self.scene == "difficulty" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.difficulty = ("easy", "medium", "hard")[key - pygame.K_1]
            self.scene = "campaign"
        elif self.scene == "campaign" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            target = ("city", "desert", "beach")[key - pygame.K_1]
            self.enter_selection(target)
        elif self.scene == "characters" and key in (pygame.K_LEFT, pygame.K_RIGHT):
            keys = self.character_keys()
            if keys:
                delta = -1 if key == pygame.K_LEFT else 1
                self.character_index = (self.character_index + delta) % len(keys)
        elif self.scene == "settings":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_c):
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
                self.audio.play("ui")
            elif key == pygame.K_m:
                self.audio.set_enabled(not self.audio.enabled)
                self.audio.play("ui")
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.audio.set_volume(self.audio.volume - 0.10)
                self.audio.play("ui")
            elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.audio.set_volume(self.audio.volume + 0.10)
                self.audio.play("ui")
        elif self.scene == "battle" and self.battle:
            if pygame.K_1 <= key <= pygame.K_8:
                choice = key - pygame.K_1
                if choice < len(self.battle.selected):
                    self.battle.selected_card = choice
                    self.battle.remove_mode = False
                    self.audio.play("ui")
            elif self.control_mode == "keyboard" and key in (
                pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
                pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s,
            ):
                if key in (pygame.K_LEFT, pygame.K_a):
                    self.battle.keyboard_col = max(0, self.battle.keyboard_col - 1)
                elif key in (pygame.K_RIGHT, pygame.K_d):
                    self.battle.keyboard_col = min(
                        LAST_PLACEABLE_COLUMN,
                        self.battle.keyboard_col + 1,
                    )
                elif key in (pygame.K_UP, pygame.K_w):
                    self.battle.keyboard_row = max(0, self.battle.keyboard_row - 1)
                else:
                    self.battle.keyboard_row = min(ROWS - 1, self.battle.keyboard_row + 1)
                self.audio.play("ui", min_interval_ms=45)
            elif self.control_mode == "keyboard" and key in (pygame.K_q, pygame.K_e):
                direction = -1 if key == pygame.K_q else 1
                count = len(self.battle.selected)
                self.battle.selected_card = (self.battle.selected_card + direction) % count
                self.battle.remove_mode = False
                self.audio.play("ui")
            elif self.control_mode == "keyboard" and key in (pygame.K_RETURN, pygame.K_f, pygame.K_SPACE):
                if self.battle.remove_mode:
                    self.battle.remove_defender(self.battle.keyboard_row, self.battle.keyboard_col)
                elif self.battle.card_cooldowns[self.battle.selected_card] <= 0:
                    self.battle.place(self.battle.keyboard_row, self.battle.keyboard_col)
                else:
                    self.battle.announce("Esta carta ainda está recarregando.", 1.3, GRAY)
            elif self.control_mode == "keyboard" and key in (pygame.K_n, pygame.K_TAB):
                if not self.battle.started_wave:
                    self.battle.intermission = 0
                    self.battle.start_next_wave()
                else:
                    self.battle.announce("A horda atual ainda está em andamento.", 1.3, GRAY)
            elif key == pygame.K_r:
                self.battle.remove_mode = not self.battle.remove_mode
                self.battle.announce("Ferramenta de remoção ativada." if self.battle.remove_mode else "Ferramenta de remoção desativada.", 1.4, TEAL)
            elif key == pygame.K_p:
                self.battle.paused = not self.battle.paused
                self.battle.announce("Partida pausada." if self.battle.paused else "Partida retomada.", 1.4, GOLD)
                self.checkpoint()
            elif self.control_mode == "mouse" and key == pygame.K_SPACE and not self.battle.started_wave:
                self.battle.intermission = 0
                self.battle.start_next_wave()
            elif self.battle.finished and key == pygame.K_RETURN:
                self.finish_battle()

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.scene == "loading":
            return
        if self.scene != "battle":
            self.audio.play("ui", min_interval_ms=55)
        if self.scene in ("confirm_new", "confirm_exit"):
            if self.confirm_cancel_rect().collidepoint(pos):
                self.scene = "title"
            elif self.confirm_accept_rect().collidepoint(pos):
                if self.scene == "confirm_exit":
                    self.running = False
                elif self.session_store.clear():
                    self.battle = None
                    self.pending_snapshot = None
                    self.session_notice = ""
                    self.scene = "difficulty"
                else:
                    self.session_notice = self.session_store.error
        elif self.scene == "title":
            self.click_title(pos)
        elif self.scene == "difficulty":
            self.click_difficulty(pos)
        elif self.scene == "campaign":
            self.click_campaign(pos)
        elif self.scene == "characters":
            self.click_characters(pos)
        elif self.scene == "story":
            self.click_story(pos)
        elif self.scene == "settings":
            if self.settings_control_rect().collidepoint(pos):
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
            elif self.settings_video_rect().collidepoint(pos):
                self.toggle_fullscreen()
            elif self.settings_sound_rect().collidepoint(pos):
                self.audio.set_enabled(not self.audio.enabled)
            elif self.settings_volume_minus_rect().collidepoint(pos):
                self.audio.set_volume(self.audio.volume - 0.10)
            elif self.settings_volume_plus_rect().collidepoint(pos):
                self.audio.set_volume(self.audio.volume + 0.10)
            elif self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
        elif self.scene.startswith("dossier"):
            self.click_dossier(pos)
        elif self.scene == "howto":
            if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
        elif self.scene == "battle" and self.battle:
            if self.battle.finished:
                if pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50).collidepoint(pos):
                    self.finish_battle()
            else:
                was_paused = self.battle.paused
                self.battle.handle_click(pos)
                if self.scene == "battle" and self.battle.paused != was_paused:
                    self.checkpoint()

    def title_buttons(self) -> list[tuple[str, pygame.Rect]]:
        if self.can_continue():
            labels = ("CONTINUAR", "NOVA PARTIDA", "PERSONAGENS", "HISTÓRIA DO JOGO",
                      "CONFIGURAÇÕES", "COMO JOGAR", "SAIR")
            return [(label, pygame.Rect(62, 264 + index * 49, 274, 40))
                    for index, label in enumerate(labels)]
        return [
            ("INICIAR", pygame.Rect(62, 276, 274, 52)),
            ("PERSONAGENS", pygame.Rect(62, 338, 274, 48)),
            ("HISTÓRIA DO JOGO", pygame.Rect(62, 396, 274, 48)),
            ("CONFIGURAÇÕES", pygame.Rect(62, 454, 274, 48)),
            ("COMO JOGAR", pygame.Rect(62, 512, 274, 44)),
            ("SAIR", pygame.Rect(62, 566, 274, 40)),
        ]

    @staticmethod
    def settings_control_rect() -> pygame.Rect:
        return pygame.Rect(505, 245, 270, 48)

    @staticmethod
    def settings_sound_rect() -> pygame.Rect:
        return pygame.Rect(505, 326, 270, 48)

    @staticmethod
    def settings_volume_minus_rect() -> pygame.Rect:
        return pygame.Rect(505, 407, 64, 44)

    @staticmethod
    def settings_volume_plus_rect() -> pygame.Rect:
        return pygame.Rect(711, 407, 64, 44)

    @staticmethod
    def settings_video_rect() -> pygame.Rect:
        return pygame.Rect(505, 458, 270, 42)

    def click_title(self, pos: tuple[int, int]) -> None:
        for label, rect in self.title_buttons():
            if not rect.collidepoint(pos):
                continue
            if label == "CONTINUAR":
                self.resume_battle()
            elif label in ("INICIAR", "NOVA PARTIDA"):
                self.request_new_game()
            elif label == "PERSONAGENS":
                self.scene, self.dossier_kind, self.character_region = "characters", "units", "city"
            elif label == "HISTÓRIA DO JOGO":
                self.scene, self.story_page = "story", 0
            elif label == "CONFIGURAÇÕES":
                self.scene = "settings"
            elif label == "COMO JOGAR":
                self.scene = "howto"
            elif label == "SAIR":
                self.request_quit()

    def click_characters(self, pos: tuple[int, int]) -> None:
        for index, region in enumerate(("city", "desert", "beach")):
            if pygame.Rect(340 + index * 205, 82, 190, 42).collidepoint(pos):
                self.character_region = region
                self.character_index = 0
                return
        if pygame.Rect(424, 136, 205, 40).collidepoint(pos):
            self.dossier_kind = "units"
            self.character_index = 0
            return
        if pygame.Rect(650, 136, 205, 40).collidepoint(pos):
            self.dossier_kind = "zombies"
            self.character_index = 0
            return
        keys = self.character_keys()
        if keys and pygame.Rect(260, 184, 180, 40).collidepoint(pos):
            self.character_index = (self.character_index - 1) % len(keys)
            return
        if keys and pygame.Rect(WIDTH - 440, 184, 180, 40).collidepoint(pos):
            self.character_index = (self.character_index + 1) % len(keys)
            return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def character_keys(self) -> list[str]:
        if self.dossier_kind == "units":
            return [key for key, _display in REGION_ROSTERS[self.character_region]]
        # O dossiê mostra o elenco completo que realmente participa das 12
        # ondas: seis comuns, três subchefes e três chefes regionais.
        return list(
            REGION_ENEMIES[self.character_region]
            + REGION_SUBBOSSES[self.character_region]
            + REGION_BOSSES[self.character_region]
        )


    def click_story(self, pos: tuple[int, int]) -> None:
        if pygame.Rect(245, 646, 170, 44).collidepoint(pos):
            self.story_page = max(0, self.story_page - 1)
        elif pygame.Rect(WIDTH - 415, 646, 170, 44).collidepoint(pos):
            self.story_page = min(2, self.story_page + 1)
        elif self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def difficulty_buttons(self) -> list[tuple[str, pygame.Rect]]:
        return [
            ("easy", pygame.Rect(80, 500, 320, 48)),
            ("medium", pygame.Rect(480, 500, 320, 48)),
            ("hard", pygame.Rect(880, 500, 320, 48)),
        ]

    def click_difficulty(self, pos: tuple[int, int]) -> None:
        for key, rect in self.difficulty_buttons():
            if rect.collidepoint(pos):
                self.difficulty = key
                self.scene = "campaign"
                return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def click_campaign(self, pos: tuple[int, int]) -> None:
        for index, region in enumerate(("city", "desert", "beach")):
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            if rect.collidepoint(pos):
                self.enter_selection(region)
                return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def enter_selection(self, region: str) -> None:
        self.region = region
        # Não há mais uma etapa de seleção pré-partida. Cada mapa entrega sua
        # equipe regional completa de oito cartas e inicia imediatamente.
        available = self.available_selection_keys(region)
        self.selection = [(key, self.card_display_name(region, key)) for key in available[:8]]
        self.selection_carousel_index = 0
        self.selection_inspect_key = None
        self.hover_card = None
        self.battle = Battle(self, region, self.selection[:])
        self.scene = "battle"
        self.checkpoint()

    @staticmethod
    def _unique_keys(keys: list[str]) -> list[str]:
        seen: set[str] = set()
        return [key for key in keys if not (key in seen or seen.add(key))]

    def regional_card_keys(self, region: str) -> list[str]:
        """A produção atual expõe somente o personagem já redesenhado."""
        return [key for key, _display in REGION_ROSTERS[region]]

    def available_selection_keys(self, region: str | None = None) -> list[str]:
        region = region or self.region
        return self.regional_card_keys(region)

    @staticmethod
    def card_display_name(region: str, key: str) -> str:
        for roster_key, display in REGION_ROSTERS[region]:
            if roster_key == key:
                return display
        return str(DEFENSES[key]["base"])

    def selection_cards(self) -> list[tuple[str, str, pygame.Rect]]:
        """Restaura a grade compacta usada antes de iniciar a partida."""
        keys = self.available_selection_keys()
        cards: list[tuple[str, str, pygame.Rect]] = []
        for index, key in enumerate(keys):
            row = index // 5
            column = index % 5
            row_count = min(5, len(keys) - row * 5)
            row_width = row_count * 238 + max(0, row_count - 1) * 12
            x = (WIDTH - row_width) // 2 + column * 250
            y = 96 + row * 230
            cards.append(
                (key, self.card_display_name(self.region, key), pygame.Rect(x, y, 238, 215))
            )
        return cards

    @staticmethod
    def selection_inspect_button(card_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(card_rect.x + 119, card_rect.bottom - 39, card_rect.width - 129, 27)

    @staticmethod
    def selection_inspection_close_rect() -> pygame.Rect:
        return pygame.Rect(WIDTH // 2 - 105, 552, 210, 42)

    def click_selection(self, pos: tuple[int, int]) -> None:
        if self.selection_inspect_key is not None:
            if self.selection_inspection_close_rect().collidepoint(pos):
                self.selection_inspect_key = None
            return
        for key, display, rect in self.selection_cards():
            if self.selection_inspect_button(rect).collidepoint(pos):
                self.selection_inspect_key = key
                return
            if not rect.collidepoint(pos):
                continue
            item = (key, display)
            if item in self.selection:
                self.selection.remove(item)
            elif len(self.selection) < 3:
                self.selection.append(item)
            return
        launch = pygame.Rect(WIDTH - 290, 650, 240, 46)
        if launch.collidepoint(pos):
            if 1 <= len(self.selection) <= 3:
                self.battle = Battle(self, self.region, self.selection[:])
                self.scene = "battle"
                self.checkpoint()
            else:
                return
        if self.button_rect("Voltar", 45, 650, 160, 46).collidepoint(pos):
            self.scene = "campaign"

    def dossier_items(self) -> list[dict]:
        if self.dossier_kind == "units":
            regional_keys = set(self.regional_card_keys(self.region))
            items = [
                {"kind": "evolution", "l1": l1, "l2": l2}
                for l1, l2 in PROMOTIONS.items()
                if l1 in regional_keys and l2 in regional_keys
            ]
            if "instrutor" in regional_keys and self.difficulty == "hard":
                items.append({"kind": "promoter", "key": "instrutor"})
            return items
        return [
            {"name": data["name"], "sub": "Chefe" if key in BOSSES else "Inimigo", "ability": data["ability"], "hp": int(data["hp"]), "key": key}
            for key, data in {**ENEMIES, **BOSSES}.items()
        ]

    def click_dossier(self, pos: tuple[int, int]) -> None:
        if self.button_rect("Voltar", 40, 648, 160, 42).collidepoint(pos):
            self.scene = "title"
            return
        if pygame.Rect(WIDTH - 180, 648, 140, 42).collidepoint(pos):
            items = self.dossier_items()
            pages = max(1, math.ceil(len(items) / 6))
            self.dossier_page = (self.dossier_page + 1) % pages

    def finish_battle(self) -> None:
        if not self.battle:
            self.scene = "campaign"
            return
        if self.battle.victory:
            region = self.battle.region
            if region not in self.save["completed"]:
                self.save["completed"].append(region)
            self.save["unlocked"] = list(REGIONS)
            self.save["best_wave"][region] = max(self.save["best_wave"].get(region, 0), TOTAL_WAVES)
            self.save_error = not save_campaign(self.save, self.save_path)
        if (self.battle.victory and self.save_error) or not self.session_store.clear():
            self.session_notice = "Não foi possível gravar o resultado. Tente voltar ao mapa novamente."
            return
        self.battle = None
        self.pending_snapshot = None
        self.session_notice = ""
        self.scene = "campaign"

    def can_continue(self) -> bool:
        return self.battle is not None or self.pending_snapshot is not None

    def checkpoint(self) -> bool:
        if self.battle is None:
            return True
        try:
            self.pending_snapshot = capture(self.battle)
            ok = self.session_store.save(self.pending_snapshot)
            self.session_notice = self.session_store.error
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            logger.exception("Não foi possível preparar a partida para salvamento.")
            self.session_notice = "Não foi possível salvar. A partida continua disponível nesta janela."
            ok = False
        self.autosave_elapsed = 0.0
        return ok

    def leave_battle_to_title(self) -> None:
        """Suspende a partida sem registrar vitória ou apagar o estado em memória."""
        if self.battle is not None and self.battle.finished:
            self.finish_battle()
            return
        self.checkpoint()
        self.suspended_random = random.getstate()
        self.scene = "title"

    def resume_battle(self) -> bool:
        if not self.can_continue():
            return False
        if self.battle is None:
            try:
                self.battle = activate(self.pending_snapshot, self)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError):
                logger.exception("Partida salva inválida; arquivo preservado.")
                self.pending_snapshot = None
                self.session_notice = "Não foi possível retomar este arquivo. Você pode iniciar uma nova partida."
                return False
        elif self.suspended_random is not None:
            random.setstate(self.suspended_random)
        self.region, self.difficulty = self.battle.region, self.battle.difficulty
        self.selection = self.battle.selected[:]
        self.battle.paused = not self.battle.finished
        self.scene = "battle"
        self.autosave_elapsed = 0.0
        self.suspended_random = None
        return True

    def request_new_game(self) -> None:
        self.scene = "confirm_new" if self.can_continue() else "difficulty"

    def request_quit(self) -> None:
        if self.checkpoint():
            self.running = False
        else:
            self.scene = "confirm_exit"

    @staticmethod
    def confirm_accept_rect() -> pygame.Rect:
        return pygame.Rect(325, 420, 300, 50)

    @staticmethod
    def confirm_cancel_rect() -> pygame.Rect:
        return pygame.Rect(655, 420, 300, 50)

    def button_rect(self, label: str, x: int, y: int, w: int, h: int) -> pygame.Rect:
        return self.renderer.button_rect(label, x, y, w, h)

    def draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[float, float], anchor: str='topleft', shadow: bool=False) -> pygame.Rect:
        return self.renderer.draw_text(text, font, color, pos, anchor, shadow)

    def panel(self, rect: pygame.Rect, alpha: int=210, border: tuple[int, int, int]=(91, 106, 112), radius: int=10) -> None:
        return self.renderer.panel(rect, alpha, border, radius)

    def button(self, label: str, rect: pygame.Rect, accent: tuple[int, int, int], enabled: bool=True) -> None:
        return self.renderer.button(label, rect, accent, enabled)

    def draw_loading(self) -> None:
        return self.renderer.draw_loading()

    def draw_title(self) -> None:
        return self.renderer.draw_title()

    def draw_difficulty(self) -> None:
        return self.renderer.draw_difficulty()

    def draw_campaign(self) -> None:
        return self.renderer.draw_campaign()

    def draw_selection(self) -> None:
        return self.renderer.draw_selection()

    def draw_selection_inspection(self, key: str) -> None:
        return self.renderer.draw_selection_inspection(key)

    def draw_characters(self) -> None:
        return self.renderer.draw_characters()

    def draw_comic_bubble(self, rect: pygame.Rect, text: str, tail: tuple[int, int]) -> None:
        return self.renderer.draw_comic_bubble(rect, text, tail)

    def draw_comic_actor(self, actor: str, state: str, frame_index: int, point: tuple[int, int], body_height: int, *, flip: bool=False) -> pygame.Rect:
        return self.renderer.draw_comic_actor(actor, state, frame_index, point, body_height, flip=flip)

    def draw_story(self) -> None:
        return self.renderer.draw_story()

    def draw_settings(self) -> None:
        return self.renderer.draw_settings()

    def draw_howto(self) -> None:
        return self.renderer.draw_howto()

    def draw_unit_evolution_dossier(self) -> None:
        return self.renderer.draw_unit_evolution_dossier()

    def draw_dossier(self) -> None:
        return self.renderer.draw_dossier()

    def draw_battle(self) -> None:
        return self.renderer.draw_battle()

    def draw_lane_guides(self, battle: Battle) -> None:
        return self.renderer.draw_lane_guides(battle)

    def draw_lane_bombs(self, battle: Battle) -> None:
        return self.renderer.draw_lane_bombs(battle)

    def draw_battle_top(self) -> None:
        return self.renderer.draw_battle_top()

    def defender_sprite(self, battle: Battle, defender: Defender) -> pygame.Surface:
        return self.renderer.defender_sprite(battle, defender)

    def enemy_sprite(self, battle: Battle, enemy: Enemy) -> pygame.Surface:
        return self.renderer.enemy_sprite(battle, enemy)

    def draw_actor_sprite(self, sprite: pygame.Surface, x: float, ground_y: float, width: float, height: float, motion: ActorMotion, *, enemy: bool, vertical_offset: float=0.0, alpha: int=255, progress: float=0.0, state_override: str | None=None, profile: str='generic', frame_animated: bool=False) -> pygame.Rect:
        return self.renderer.draw_actor_sprite(sprite, x, ground_y, width, height, motion, enemy=enemy, vertical_offset=vertical_offset, alpha=alpha, progress=progress, state_override=state_override, profile=profile, frame_animated=frame_animated)

    def draw_fallen(self, battle: Battle) -> None:
        return self.renderer.draw_fallen(battle)

    def draw_linked_skill_effect(self, effect: VisualEffect, x: float, y: float, progress: float) -> bool:
        return self.renderer.draw_linked_skill_effect(effect, x, y, progress)

    def draw_gas_cloud(self, x: float, y: float, progress: float, scale: float) -> None:
        return self.renderer.draw_gas_cloud(x, y, progress, scale)

    def draw_visual_effects(self, battle: Battle) -> None:
        return self.renderer.draw_visual_effects(battle)

    def blit_effect_frame(self, sheet: str, row: int, stage: int, x: float, y: float, width: float, height: float, *, alpha: int=255, angle: float=0.0, midbottom: bool=False, flip_x: bool=False) -> pygame.Rect | None:
        return self.renderer.blit_effect_frame(sheet, row, stage, x, y, width, height, alpha=alpha, angle=angle, midbottom=midbottom, flip_x=flip_x)

    def blit_muzzle_cycle(self, stage: int, x: float, y: float, *, width: float, height: float) -> pygame.Rect | None:
        return self.renderer.blit_muzzle_cycle(stage, x, y, width=width, height=height)

    @staticmethod
    def frame_has_muzzle_flash(sprite: pygame.Surface, defender: Defender) -> bool:
        return GameRenderer.frame_has_muzzle_flash(sprite, defender)

    @staticmethod
    def eased(value: float) -> float:
        return GameRenderer.eased(value)

    def draw_reload_action(self, defender: Defender, rect: pygame.Rect, scale: tuple[float, float], depth: float, progress: float) -> None:
        return self.renderer.draw_reload_action(defender, rect, scale, depth, progress)

    def draw_weapon_action(self, defender: Defender, rect: pygame.Rect, scale: tuple[float, float], depth: float) -> None:
        return self.renderer.draw_weapon_action(defender, rect, scale, depth)

    def draw_defender(self, defender: Defender) -> None:
        return self.renderer.draw_defender(defender)

    def draw_enemy(self, enemy: Enemy) -> None:
        return self.renderer.draw_enemy(enemy)

    @staticmethod
    def flow_points(start: tuple[float, float], end: tuple[float, float], elapsed: float, amplitude: float, count: int=18) -> list[tuple[int, int]]:
        return GameRenderer.flow_points(start, end, elapsed, amplitude, count)

    @staticmethod
    def ribbon_polygon(points: list[tuple[int, int]], start_width: float, end_width: float, *, taper_tip: bool=False) -> list[tuple[int, int]]:
        return GameRenderer.ribbon_polygon(points, start_width, end_width, taper_tip=taper_tip)

    @staticmethod
    def water_ribbon_polygon(points: list[tuple[int, int]], start_width: float, end_width: float, elapsed: float, phase: float=0.0) -> list[tuple[int, int]]:
        return GameRenderer.water_ribbon_polygon(points, start_width, end_width, elapsed, phase)

    def draw_pressurized_water(self, start: tuple[float, float], end: tuple[float, float], elapsed: float, depth: float, palette: tuple[tuple[int, int, int, int], ...]) -> None:
        return self.renderer.draw_pressurized_water(start, end, elapsed, depth, palette)

    def draw_combustion_flame(self, start: tuple[float, float], end: tuple[float, float], elapsed: float, travel: float, depth: float) -> None:
        return self.renderer.draw_combustion_flame(start, end, elapsed, travel, depth)

    def draw_elemental_stream(self, projectile: Projectile, x: float, y: float) -> None:
        return self.renderer.draw_elemental_stream(projectile, x, y)

    def draw_gas_grenade_projectile(self, x: float, y: float, angle: float, depth: float, progress: float, previous: tuple[float, float]) -> None:
        return self.renderer.draw_gas_grenade_projectile(x, y, angle, depth, progress, previous)

    def draw_projectiles(self, battle: Battle) -> None:
        return self.renderer.draw_projectiles(battle)

    def draw_particles(self, battle: Battle) -> None:
        return self.renderer.draw_particles(battle)

    def draw_battle_status(self) -> None:
        return self.renderer.draw_battle_status()

    def draw_result_overlay(self) -> None:
        return self.renderer.draw_result_overlay()

    def health_bar(self, x: float, y: float, width: float, ratio: float, color: tuple[int, int, int]) -> None:
        return self.renderer.health_bar(x, y, width, ratio, color)

    def ammo_bar(self, x: float, y: float, width: float, ratio: float) -> None:
        return self.renderer.ammo_bar(x, y, width, ratio)

    def blit_sprite(self, sprite: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
        return self.renderer.blit_sprite(sprite, x, y, width, height)

    def blit_actor_in_rect(self, sprite: pygame.Surface, rect: pygame.Rect, body_height: int, *, source_body_height: float=130.0, outline: tuple[int, int, int] | None=None) -> pygame.Rect:
        return self.renderer.blit_actor_in_rect(sprite, rect, body_height, source_body_height=source_body_height, outline=outline)

    def draw_portrait_backdrop(self, rect: pygame.Rect, accent: tuple[int, int, int]) -> None:
        return self.renderer.draw_portrait_backdrop(rect, accent)

    def card_sprite(self, region: str, key: str, index: int) -> pygame.Surface:
        return self.renderer.card_sprite(region, key, index)

    @staticmethod
    def card_metrics(data: dict) -> tuple[str, str]:
        return GameRenderer.card_metrics(data)

    def draw_wrapped(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect, lines: int, center: bool=False) -> None:
        return self.renderer.draw_wrapped(text, font, color, rect, lines, center)

    def draw(self) -> None:
        return self.renderer.draw()
