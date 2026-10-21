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
from .rendering_geometry import (
    flow_points as geometry_flow_points,
    ribbon_polygon as geometry_ribbon_polygon,
    water_ribbon_polygon as geometry_water_ribbon_polygon,
)
from .persistence import (
    load_save,
    save_campaign,
)
from .rendering import (
    GameRenderer,
)


from .settings import Settings, ACTION_LABELS, DEFAULT_BINDINGS
from .navigation import MenuNavigation
from .timing import FixedStepper
from .video import VideoDisplay
from .session_store import SessionStore
from .snapshot import capture, activate
from .scoring import normalize_player_name, SHOP_ITEMS

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
        self.settings = Settings(save_path)
        self.fonts = FontBook(self.settings.large_text)
        self.navigation = MenuNavigation(self)
        self.binding_action = None
        self.show_card_info = False
        self.stepper = FixedStepper()
        self.assets = Assets()
        self.scenario_runtime = ScenarioRuntime()
        self.audio = AudioSystem()
        # Mouse continua sendo o padrão solicitado. O modo Teclado habilita
        # um cursor de grade próprio sem alterar as regras de posicionamento.
        self.control_mode = self.settings.control_mode
        self.audio.set_volume(self.settings.volume)
        self.audio.set_levels(self.settings.music, self.settings.ambience, self.settings.effects)
        self.audio.set_enabled(self.settings.sound)
        self.integration_preview = bool(integration_preview)
        self.gpu_preload_queue: list[pygame.Surface] = []
        self.gpu_preloaded = 0
        self.gpu_queue_ready = False
        self.running = True
        self.scene = "loading"
        self.scene_elapsed = 0.0
        from .scoring import ScoreStore
        self.score_store = ScoreStore(save_path)
        self.score_page = 0
        self.score_view = "ranking"
        self.score_rows, self.score_total = [], 0
        self.profile_data = {"player_name": "", "credits": 0, "medkits": 0, "tactical_ammo": 0}
        self.player_name = self.settings.player_name
        self.profile_name_draft = self.player_name
        self.profile_return_scene = "title"
        self.profile_error = ""
        self.pending_powerup: str | None = None
        self.save_path = save_path
        self.save_error = False
        campaign_notices = []
        self.save = load_save(save_path, campaign_notices)
        self.session_store = SessionStore(save_path)
        self.pending_snapshot = self.session_store.load()
        self.session_notice = self.session_store.error or ' '.join(campaign_notices)
        self.autosave_elapsed = 0.0
        self.suspended_random = None
        self.region = "city"
        self.difficulty = "medium"
        self.selection: list[tuple[str, str]] = []
        self.battle: Battle | None = None
        self.dossier_kind = "units"
        self.character_region = "city"
        self.character_index = 0
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
                dt = self.clock.tick(FPS) / 1000.0
                self.handle_events()
                self.stepper.advance(dt, self.simulation_step)
                self.draw()
                self.present_frame()
        finally:
            self.checkpoint()
            if self.presenter is not None:
                self.presenter.close()
            pygame.quit()

    def simulation_step(self, dt: float) -> None:
        self.scene_elapsed += dt
        self.update(dt)

    def update(self, dt: float) -> None:
        self.video_notice_left = max(0.0, self.video_notice_left - dt)
        if not self.video_notice_left:
            self.video_notice = ""
        self.audio.sync(
            self.scene,
            self.battle.region if self.scene == "battle" and self.battle else None,
        )
        if not (self.scene == "battle" and self.battle and (self.battle.paused or self.battle.finished)):
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
                if self.battle.finished:
                    self.score_store.record(self.battle)
            if not self.battle.paused and not was_finished:
                self.autosave_elapsed += dt
            if (self.autosave_elapsed >= AUTOSAVE_SECONDS or
                    self.battle.wave != previous_wave or self.battle.finished != was_finished):
                self.checkpoint()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.request_quit()
            elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
                if self.settings.auto_pause and self.scene == "battle" and self.battle and self.battle.accepts_actions:
                    self.battle.paused = True
                    self.checkpoint()
            elif event.type == pygame.TEXTINPUT and self.scene == "profile":
                addition = "".join(character for character in event.text if character.isprintable())
                self.profile_name_draft = (self.profile_name_draft + addition)[:20]
            elif event.type == pygame.KEYDOWN:
                video_key = event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and getattr(event, "mod", 0) & pygame.KMOD_ALT)
                if video_key and getattr(event, "repeat", False):
                    continue
                self.handle_key(event.key, getattr(event, "mod", 0))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.navigation.visible = False
                pos = self.video.mouse_position(event.pos)
                if pos != (-1, -1):
                    self.handle_click(pos)
            elif event.type == pygame.MOUSEMOTION:
                self.navigation.visible = False
                self.hover_card = None

    def handle_key(self, key: int, mod: int = 0) -> None:
        if self.binding_action is not None:
            if key == pygame.K_ESCAPE:
                self.binding_action = None
            elif self.settings.assign(self.binding_action, key):
                self.binding_action = None
                self.save_settings()
            else:
                self.video_notice = "Tecla reservada ou já usada. Escolha outra; Esc cancela."
                self.video_notice_left = 4
            return
        if key == pygame.K_F11 or (key == pygame.K_RETURN and mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return
        if key == pygame.K_ESCAPE:
            if self.scene == "profile":
                self.cancel_profile()
            elif self.scene == "battle" and self.pending_powerup:
                self.pending_powerup = None
                if self.battle:
                    self.battle.announce("Uso do consumível cancelado.", 1.3, GOLD)
            elif self.scene == "title":
                self.request_quit()
            elif self.scene == "battle":
                self.leave_battle_to_title()
            else:
                self.scene = "settings" if self.scene == "bindings" else "title"
            return
        if self.scene == "profile":
            if key == pygame.K_BACKSPACE:
                self.profile_name_draft = self.profile_name_draft[:-1]
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.save_profile()
            elif key == pygame.K_a and mod & pygame.KMOD_CTRL:
                self.profile_name_draft = ""
            return
        if key == pygame.K_F1 and self.scene == "battle":
            self.show_card_info = not self.show_card_info
            return
        if key == pygame.K_F5 and self.can_continue():
            if self.checkpoint():
                self.video_notice, self.video_notice_left = "Partida salva.", 2.5
            return
        if self.scene != "battle" and self.navigation.handle(key, mod):
            return
        if self.scene == "difficulty" and pygame.K_1 <= key <= pygame.K_3:
            self.difficulty = ("easy", "medium", "hard")[key - pygame.K_1]
            self.scene = "campaign"
        elif self.scene == "campaign" and pygame.K_1 <= key <= pygame.K_3:
            self.enter_selection(("city", "desert", "beach")[key - pygame.K_1])
        elif self.scene == "settings":
            if key == pygame.K_c:
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
            elif key == pygame.K_m:
                self.audio.set_enabled(not self.audio.enabled)
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.audio.set_volume(self.audio.volume - .1)
            elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.audio.set_volume(self.audio.volume + .1)
            self.save_settings()
        elif self.scene == "battle" and self.battle:
            b = self.battle
            if b.finished:
                if key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.finish_battle()
                return
            action = self.settings.action(key)
            if action == "pause":
                b.paused = not b.paused
                b.announce("Partida pausada." if b.paused else "Partida retomada.", 1.4, GOLD)
                self.checkpoint()
                return
            if b.paused:
                return
            if key in (pygame.K_h, pygame.K_t):
                self.pending_powerup = "medkit" if key == pygame.K_h else "tactical_ammo"
                item = SHOP_ITEMS[self.pending_powerup]["label"].upper()
                b.announce(f"{item}: clique no soldado que receberá o item. Esc cancela.", 3.0, GOLD)
                return
            if pygame.K_1 <= key <= pygame.K_8:
                choice = key - pygame.K_1
                if choice < len(b.selected):
                    b.selected_card, b.remove_mode = choice, False
            elif action == "remove":
                b.remove_mode = not b.remove_mode
            elif self.control_mode == "mouse" and key == pygame.K_SPACE:
                b.start_next_wave()
            elif self.control_mode == "keyboard":
                if action in ("up", "down", "left", "right"):
                    b.keyboard_col = min(LAST_PLACEABLE_COLUMN, max(0, b.keyboard_col + (action == "right") - (action == "left")))
                    b.keyboard_row = min(ROWS - 1, max(0, b.keyboard_row + (action == "down") - (action == "up")))
                elif action in ("previous", "next"):
                    b.selected_card = (b.selected_card + (1 if action == "next" else -1)) % len(b.selected)
                    b.remove_mode = False
                elif action == "place":
                    if b.remove_mode:
                        b.remove_defender(b.keyboard_row, b.keyboard_col)
                    else:
                        b.place(b.keyboard_row, b.keyboard_col)
                elif action == "wave":
                    b.start_next_wave()

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
        elif self.scene == "profile":
            self.click_profile(pos)
        elif self.scene == "scores":
            if pygame.Rect(50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
            elif pygame.Rect(430, 645, 260, 46).collidepoint(pos):
                self.score_view = "history" if self.score_view == "ranking" else "ranking"
                self.score_page = 0
                self.refresh_scores()
            elif pygame.Rect(735, 645, 150, 46).collidepoint(pos) and self.score_page > 0:
                self.score_page -= 1
                self.refresh_scores()
            elif pygame.Rect(910, 645, 280, 46).collidepoint(pos) and (self.score_page + 1) * 10 < self.score_total:
                self.score_page += 1
                self.refresh_scores()
        elif self.scene == "difficulty":
            self.click_difficulty(pos)
        elif self.scene == "campaign":
            self.click_campaign(pos)
        elif self.scene == "characters":
            self.click_characters(pos)
        elif self.scene == "story":
            self.click_story(pos)
        elif self.scene == "settings":
            self.click_settings(pos)
        elif self.scene == "bindings":
            if pygame.Rect(50,645,170,46).collidepoint(pos):
                self.scene = "settings"
            elif pygame.Rect(485,574,310,42).collidepoint(pos):
                self.settings.bindings = DEFAULT_BINDINGS.copy()
                self.save_settings()
            else:
                for i, action in enumerate(self.settings.bindings):
                    if self.binding_rect(i).collidepoint(pos):
                        self.binding_action = action
                        break
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
            labels = (
                "CONTINUAR", "NOVA PARTIDA", "PERFIL / LOJA", "PERSONAGENS",
                "HISTÓRIA DO JOGO", "CONFIGURAÇÕES", "COMO JOGAR", "RANKING", "SAIR",
            )
            return [
                (label, pygame.Rect(62, 250 + index * 44, 274, 37))
                for index, label in enumerate(labels)
            ]
        labels = (
            "INICIAR", "PERFIL / LOJA", "PERSONAGENS", "HISTÓRIA DO JOGO",
            "CONFIGURAÇÕES", "COMO JOGAR", "RANKING", "SAIR",
        )
        return [
            (label, pygame.Rect(62, 276 + index * 47, 274, 39))
            for index, label in enumerate(labels)
        ]

    @staticmethod
    def settings_control_rect():
        return pygame.Rect(280,172,300,42)

    @staticmethod
    def settings_sound_rect():
        return pygame.Rect(280,226,300,42)

    @staticmethod
    def settings_video_rect():
        return pygame.Rect(280,280,300,42)

    @staticmethod
    def settings_volume_minus_rect():
        return pygame.Rect(650,342,58,36)

    @staticmethod
    def settings_volume_plus_rect():
        return pygame.Rect(790,342,58,36)

    def settings_items(self):
        items = {"control": self.settings_control_rect(), "sound": self.settings_sound_rect(),
                 "video": self.settings_video_rect(), "large_text": pygame.Rect(835,172,300,42),
                 "auto_pause": pygame.Rect(835,226,300,42), "reduced_motion": pygame.Rect(835,280,300,42)}
        for i,name in enumerate(("volume","music","ambience","effects")):
            items[name+"_minus"] = pygame.Rect(650,342+i*48,58,36)
            items[name+"_plus"] = pygame.Rect(790,342+i*48,58,36)
        items["bindings"] = pygame.Rect(440,553,400,42)
        return items

    @staticmethod
    def binding_rect(index):
        return pygame.Rect(110+(index//5)*550,154+(index%5)*76,510,56)

    def click_settings(self, pos):
        if pygame.Rect(50,645,170,46).collidepoint(pos):
            self.scene = "title"
            return
        for name,rect in self.settings_items().items():
            if not rect.collidepoint(pos):
                continue
            if name == "control":
                self.control_mode = "keyboard" if self.control_mode == "mouse" else "mouse"
            elif name == "sound":
                self.audio.set_enabled(not self.audio.enabled)
            elif name == "video":
                self.toggle_fullscreen()
            elif name == "bindings":
                self.scene = "bindings"
            elif name in ("large_text","auto_pause","reduced_motion"):
                setattr(self.settings,name,not getattr(self.settings,name))
                self.fonts = FontBook(self.settings.large_text)
            else:
                group, direction = name.rsplit("_",1)
                delta = .1 if direction == "plus" else -.1
                if group == "volume":
                    self.audio.set_volume(self.audio.volume + delta)
                else:
                    setattr(self.settings,group,min(1.,max(0.,getattr(self.settings,group)+delta)))
                    self.audio.set_levels(self.settings.music,self.settings.ambience,self.settings.effects)
            self.save_settings()
            return

    def save_settings(self):
        self.settings.control_mode = self.control_mode
        self.settings.sound = self.audio.enabled
        self.settings.volume = self.audio.volume
        if not self.settings.save():
            self.video_notice, self.video_notice_left = "Não foi possível guardar as preferências.", 4

    def click_title(self, pos: tuple[int, int]) -> None:
        for label, rect in self.title_buttons():
            if not rect.collidepoint(pos):
                continue
            if label == "CONTINUAR":
                if self.player_name:
                    self.resume_battle()
                else:
                    self.open_profile("resume")
            elif label in ("INICIAR", "NOVA PARTIDA"):
                self.request_new_game()
            elif label == "PERFIL / LOJA":
                self.open_profile("title")
            elif label == "PERSONAGENS":
                self.scene, self.dossier_kind, self.character_region = "characters", "units", "city"
            elif label == "HISTÓRIA DO JOGO":
                self.scene, self.story_page = "story", 0
            elif label == "CONFIGURAÇÕES":
                self.scene = "settings"
            elif label == "COMO JOGAR":
                self.scene = "howto"
            elif label == "RANKING":
                self.score_view = "ranking"
                self.score_page = 0
                self.refresh_scores()
                self.scene = "scores"
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
        self.hover_card = None
        self.battle = Battle(self, region, self.selection[:])
        self.battle.player_name = self.player_name or "Jogador"
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

    def finish_battle(self) -> None:
        if not self.battle:
            self.scene = "campaign"
            return
        b = self.battle
        if not b.finished:
            return
        if not self.score_store.record(b):
            self.session_notice = self.score_store.error
            return
        region, reached = b.region, min(TOTAL_WAVES, b.wave)
        self.save["best_wave"][region] = max(self.save["best_wave"].get(region, 0), reached)
        results = self.save.setdefault("by_difficulty", {}).setdefault(b.difficulty, {})
        record = results.setdefault(region, {"best_wave": 0, "victory": False})
        record["best_wave"] = max(record["best_wave"], reached)
        record["victory"] = record["victory"] or b.victory
        if b.victory and region not in self.save["completed"]:
            self.save["completed"].append(region)
        self.save_error = not save_campaign(self.save, self.save_path)
        if self.save_error or not self.session_store.clear():
            self.session_notice = "Não foi possível gravar o resultado. Tente voltar ao mapa novamente."
            return
        self.battle = None
        self.pending_snapshot = None
        self.session_notice = ""
        self.scene = "campaign"

    def continue_info(self):
        from datetime import datetime
        state = vars(self.battle) if self.battle else (self.pending_snapshot or {}).get("battle", {})
        region = REGIONS.get(state.get("region"), {}).get("short", "?")
        difficulty = {"easy":"Fácil","medium":"Médio","hard":"Difícil"}.get(state.get("difficulty"), "?")
        try:
            stamp = datetime.fromtimestamp(self.session_store.path.stat().st_mtime).strftime("%d/%m %H:%M")
        except OSError:
            stamp = "nesta sessão"
        return f"{region} • {difficulty} • onda {state.get('wave',0)}/{TOTAL_WAVES} • {stamp}"

    def can_continue(self) -> bool:
        return self.battle is not None or self.pending_snapshot is not None

    def checkpoint(self) -> bool:
        if self.battle is None:
            return True
        if self.battle.finished:
            self.score_store.record(self.battle)
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
                backup = self.session_store.load_backup()
                try:
                    if backup is None:
                        raise ValueError("Cópia anterior indisponível.")
                    self.battle = activate(backup, self)
                    self.pending_snapshot = backup
                    self.session_notice = self.session_store.error
                except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError):
                    self.pending_snapshot = None
                    self.session_notice = "Não foi possível retomar este arquivo. Você pode iniciar uma nova partida."
                    return False
        elif self.suspended_random is not None:
            random.setstate(self.suspended_random)
        # Se uma partida antiga for retomada depois de cadastrar um perfil,
        # os novos pontos pertencem ao jogador atualmente ativo, não ao nome
        # genérico que possa ter sido gravado por uma versão anterior.
        if self.player_name:
            self.battle.player_name = self.player_name
        self.region, self.difficulty = self.battle.region, self.battle.difficulty
        self.selection = self.battle.selected[:]
        self.battle.paused = not self.battle.finished
        self.scene = "battle"
        self.autosave_elapsed = 0.0
        self.suspended_random = None
        return True

    def refresh_scores(self) -> None:
        if self.score_view == "history":
            self.score_rows, self.score_total = self.score_store.page(self.score_page)
        else:
            self.score_rows, self.score_total = self.score_store.leaderboard(self.score_page)

    @staticmethod
    def profile_name_rect() -> pygame.Rect:
        return pygame.Rect(320, 215, 640, 54)

    @staticmethod
    def profile_save_rect() -> pygame.Rect:
        return pygame.Rect(485, 292, 310, 48)

    @staticmethod
    def profile_medkit_rect() -> pygame.Rect:
        return pygame.Rect(220, 390, 400, 135)

    @staticmethod
    def profile_ammo_rect() -> pygame.Rect:
        return pygame.Rect(660, 390, 400, 135)

    @staticmethod
    def profile_medkit_buy_rect() -> pygame.Rect:
        return pygame.Rect(242, 499, 356, 23)

    @staticmethod
    def profile_ammo_buy_rect() -> pygame.Rect:
        return pygame.Rect(682, 499, 356, 23)

    def open_profile(self, return_scene: str = "title") -> None:
        self.profile_return_scene = return_scene
        self.profile_name_draft = self.player_name
        self.profile_error = ""
        # A leitura SQLite ocorre ao entrar na tela, não em cada quadro de desenho.
        self.profile_data = (
            self.score_store.profile(self.player_name)
            if self.player_name
            else {"player_name": "", "credits": 0, "medkits": 0, "tactical_ammo": 0}
        )
        if self.player_name and self.score_store.error:
            self.profile_error = self.score_store.error
        self.scene = "profile"
        self.navigation.scene = None
        try:
            pygame.key.start_text_input()
        except pygame.error:
            pass

    def cancel_profile(self) -> None:
        try:
            pygame.key.stop_text_input()
        except pygame.error:
            pass
        self.profile_error = ""
        self.scene = "title"

    def save_profile(self) -> bool:
        try:
            name = normalize_player_name(self.profile_name_draft)
        except ValueError as exc:
            self.profile_error = str(exc)
            return False
        if not self.score_store.ensure_profile(name):
            self.profile_error = self.score_store.error
            return False
        profile = self.score_store.profile(name)
        if self.score_store.error:
            self.profile_error = self.score_store.error
            return False
        self.player_name = name
        self.settings.player_name = name
        self.profile_data = profile
        settings_saved = self.settings.save()
        warning = ""
        if not settings_saved:
            warning = "Perfil criado, mas não foi possível salvar o nome nas configurações. Ele vale nesta sessão."
        self.profile_error = ""
        try:
            pygame.key.stop_text_input()
        except pygame.error:
            pass
        destination = self.profile_return_scene
        self.scene = "title"
        if destination == "difficulty":
            self.scene = "difficulty"
        elif destination == "resume":
            resumed = self.resume_battle()
            if not resumed:
                self.scene = "title"
        elif destination == "title":
            self.video_notice = f"Perfil ativo: {self.player_name}."
            self.video_notice_left = 2.5
        if warning:
            self.video_notice = warning
            self.video_notice_left = 5.0
        return True

    def click_profile(self, pos: tuple[int, int]) -> None:
        if self.profile_name_rect().collidepoint(pos):
            self.profile_error = ""
            try:
                pygame.key.start_text_input()
            except pygame.error:
                pass
            return
        if self.profile_save_rect().collidepoint(pos):
            self.save_profile()
            return
        if self.profile_medkit_buy_rect().collidepoint(pos):
            self.buy_shop_item("medkit")
            return
        if self.profile_ammo_buy_rect().collidepoint(pos):
            self.buy_shop_item("tactical_ammo")
            return
        if pygame.Rect(50, 645, 170, 46).collidepoint(pos):
            self.cancel_profile()

    def buy_shop_item(self, item: str) -> bool:
        if not self.player_name:
            self.profile_error = "Salve um nome de jogador antes de comprar itens."
            return False
        if self.score_store.buy(self.player_name, item):
            self.profile_data = self.score_store.profile(self.player_name)
            label = SHOP_ITEMS[item]["label"]
            self.profile_error = f"{label} comprado. O item fica no inventário deste perfil."
            return True
        self.profile_error = self.score_store.error
        return False

    def try_use_powerup(self, pos: tuple[int, int]) -> bool:
        """Aplica o consumível na tropa clicada e mantém a partida pausável/salvável."""
        battle = self.battle
        item = self.pending_powerup
        if battle is None or item not in SHOP_ITEMS:
            self.pending_powerup = None
            return False
        target = next(
            (defender for defender in reversed(battle.defenders)
             if defender.hp > 0 and defender.hitbox().inflate(18, 18).collidepoint(pos)),
            None,
        )
        if target is None:
            battle.announce("Clique diretamente na tropa que receberá o consumível. Esc cancela.", 2.2, GOLD)
            return False
        if item == "medkit":
            if target.hp >= target.max_hp:
                battle.announce("Essa tropa não está ferida. Escolha uma tropa com vida perdida.", 2.0, GOLD)
                return False
            healed = min(target.max_hp - target.hp, max(25.0, target.max_hp * 0.45))
            if not self.score_store.consume(battle.player_name, item):
                self.pending_powerup = None
                battle.announce(self.score_store.error, 2.0, RED)
                return False
            target.hp = min(target.max_hp, target.hp + healed)
            target.motion.trigger("support", 0.9)
            battle.texts.append(__import__("svz.entities", fromlist=["FloatingText"]).FloatingText(
                f"+{int(round(healed))} VIDA", target.x, target.y - 50, TEAL, 1.2
            ))
            message = f"Kit médico usado em {target.display_name}: +{int(round(healed))} de vida."
        else:
            if target.max_ammo <= 0:
                battle.announce("Essa tropa não usa munição recarregável. Escolha outra.", 2.0, GOLD)
                return False
            if target.tactical_ammo_timer > 0:
                battle.announce("Essa tropa já está com munição tática ativa.", 2.0, GOLD)
                return False
            if not self.score_store.consume(battle.player_name, item):
                self.pending_powerup = None
                battle.announce(self.score_store.error, 2.0, RED)
                return False
            target.ammo = target.max_ammo
            target.reload_timer = 0.0
            target.reload_total = 0.0
            target.tactical_ammo_timer = 30.0
            target.motion.loop("idle")
            message = f"Munição tática em {target.display_name}: sem gastar munição por 30 segundos."
        self.pending_powerup = None
        if battle.player_name:
            self.profile_data = self.score_store.profile(battle.player_name)
        battle.announce(message, 3.0, TEAL)
        self.checkpoint()
        return True

    def request_new_game(self) -> None:
        self.navigation.scene = None
        if not self.player_name:
            self.open_profile("difficulty")
            return
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

    def draw_characters(self) -> None:
        return self.renderer.draw_characters()

    def draw_comic_bubble(self, rect: pygame.Rect, text: str, tail: tuple[int, int]) -> None:
        return self.renderer.draw_comic_bubble(rect, text, tail)

    def draw_comic_actor(self, actor: str, state: str, frame_index: int, point: tuple[int, int], body_height: int, *, flip: bool=False) -> pygame.Rect:
        return self.renderer.draw_comic_actor(actor, state, frame_index, point, body_height, flip=flip)

    def draw_story(self) -> None:
        return self.renderer.draw_story()

    def draw_profile(self) -> None:
        return self.renderer.draw_profile()

    def draw_settings(self) -> None:
        return self.renderer.draw_settings()

    def draw_howto(self) -> None:
        return self.renderer.draw_howto()

    def draw_battle(self) -> None:
        return self.renderer.draw_battle()

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

    def draw_defender(self, defender: Defender) -> None:
        return self.renderer.draw_defender(defender)

    def draw_enemy(self, enemy: Enemy) -> None:
        return self.renderer.draw_enemy(enemy)

    @staticmethod
    def flow_points(start: tuple[float, float], end: tuple[float, float], elapsed: float, amplitude: float, count: int=18) -> list[tuple[int, int]]:
        return geometry_flow_points(start, end, elapsed, amplitude, count)

    @staticmethod
    def ribbon_polygon(points: list[tuple[int, int]], start_width: float, end_width: float, *, taper_tip: bool=False) -> list[tuple[int, int]]:
        return geometry_ribbon_polygon(points, start_width, end_width, taper_tip=taper_tip)

    @staticmethod
    def water_ribbon_polygon(points: list[tuple[int, int]], start_width: float, end_width: float, elapsed: float, phase: float=0.0) -> list[tuple[int, int]]:
        return geometry_water_ribbon_polygon(points, start_width, end_width, elapsed, phase)

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
