"""Métodos de interface e desenho, separados do fluxo principal do jogo."""
from __future__ import annotations

from src.game.runtime import *  # noqa: F403

def button_rect(self, label: str, x: int, y: int, w: int, h: int) -> pygame.Rect:
    return pygame.Rect(x, y, w, h)

def draw_text(
    self,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    pos: tuple[float, float],
    anchor: str = "topleft",
    shadow: bool = False,
) -> pygame.Rect:
    surface = font.render(text, True, color)
    rect = surface.get_rect()
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    if shadow:
        shadow_surface = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_surface.get_rect()
        setattr(shadow_rect, anchor, (int(pos[0] + 2), int(pos[1] + 2)))
        self.screen.blit(shadow_surface, shadow_rect)
    self.screen.blit(surface, rect)
    return rect

def panel(
    self,
    rect: pygame.Rect,
    alpha: int = 210,
    border: tuple[int, int, int] = (91, 106, 112),
    radius: int = 10,
) -> None:
    surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        surface, (12, 20, 25, alpha), surface.get_rect(), border_radius=radius
    )
    pygame.draw.rect(
        surface,
        (*border, min(255, alpha + 25)),
        surface.get_rect(),
        width=2,
        border_radius=radius,
    )
    self.screen.blit(surface, rect)

def button(
    self,
    label: str,
    rect: pygame.Rect,
    accent: tuple[int, int, int],
    enabled: bool = True,
) -> None:
    hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
    outer = tuple(min(255, c + 25) for c in accent) if hover else accent
    color = outer if enabled else (67, 73, 76)
    pygame.draw.rect(self.screen, (8, 13, 17), rect.inflate(4, 4), border_radius=8)
    pygame.draw.rect(self.screen, color, rect, border_radius=7)
    pygame.draw.rect(self.screen, (228, 235, 228), rect, width=1, border_radius=7)
    self.draw_text(
        label, self.fonts.h2, INK if enabled else GRAY, rect.center, "center"
    )

def draw_loading(self) -> None:
    loading_art = self.assets.images.get("loading_beta3")
    if loading_art is not None:
        self.screen.blit(loading_art, (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 54))
        self.screen.blit(veil, (0, 0))
    else:
        self.screen.fill((8, 13, 18))
    asset_progress = self.assets.loaded / max(1, self.assets.total)
    if self.presenter is not None:
        gpu_total = len(self.gpu_preload_queue)
        gpu_progress = (
            (self.gpu_preloaded / gpu_total)
            if gpu_total
            else (1.0 if self.assets.complete else 0.0)
        )
        progress = asset_progress * 0.74 + gpu_progress * 0.26
    else:
        progress = asset_progress
    # A arte entregue pelo usuário já contém o título. O painel discreto
    # abaixo não a redesenha nem esconde o logotipo central.
    panel = pygame.Rect(WIDTH // 2 - 282, HEIGHT - 150, 564, 108)
    self.panel(panel, 204, (166, 130, 62), 12)
    self.draw_text(
        f"{VERSION} — CARREGANDO",
        self.fonts.h2,
        WHITE,
        (panel.centerx, panel.y + 17),
        "center",
        True,
    )
    bar = pygame.Rect(panel.x + 42, panel.y + 51, panel.width - 84, 18)
    pygame.draw.rect(self.screen, (31, 42, 47), bar, border_radius=9)
    pygame.draw.rect(
        self.screen,
        TEAL,
        (bar.x, bar.y, int(bar.width * progress), bar.height),
        border_radius=9,
    )
    if self.presenter is not None and self.assets.complete:
        status = f"Enviando atores para a GPU  {self.gpu_preloaded}/{len(self.gpu_preload_queue)}"
    else:
        status = f"Preparando artes e animações  {self.assets.loaded}/{self.assets.total}"
    self.draw_text(
        status, self.fonts.small, WHITE, (panel.centerx, panel.y + 79), "center"
    )
    if self.assets.error:
        self.draw_text(
            self.assets.error,
            self.fonts.small,
            RED,
            (panel.centerx, panel.y - 18),
            "center",
        )

def draw_title(self) -> None:
    self.screen.blit(self.assets.images["menu"], (0, 0))
    tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    tint.fill((3, 8, 12, 92))
    self.screen.blit(tint, (0, 0))
    self.panel(pygame.Rect(36, 80, 336, 548), 210, (166, 130, 62), 14)
    self.draw_text(
        "SOLDADOS", self.fonts.title, (242, 239, 218), (62, 108), shadow=True
    )
    self.draw_text("VS", self.fonts.small, GOLD, (338, 153), "topright", True)
    self.draw_text(
        "ZUMBIS", self.fonts.title, (154, 206, 127), (62, 166), shadow=True
    )
    self.draw_text(
        "DEFENDA. RECARREGUE. RESISTA.", self.fonts.small, GRAY, (64, 224)
    )
    for label, rect in self.title_buttons():
        accent = GOLD if label == "INICIAR" else (81, 145, 137)
        self.button(label, rect, accent)
    self.draw_text(
        f"{VERSION} • Cidade • Deserto • Cachoeira",
        self.fonts.small,
        WHITE,
        (40, HEIGHT - 28),
    )
    self.draw_text(
        "Artes originais • campanha de 12 ondas",
        self.fonts.small,
        WHITE,
        (WIDTH - 36, HEIGHT - 28),
        "topright",
    )

def draw_difficulty(self) -> None:
    self.screen.blit(self.assets.images["menu"], (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((3, 8, 12, 178))
    self.screen.blit(veil, (0, 0))
    self.draw_text(
        "ESCOLHA A DIFICULDADE",
        self.fonts.title,
        WHITE,
        (WIDTH / 2, 42),
        "center",
        True,
    )
    self.draw_text(
        "O modo altera recursos, força dos inimigos e ritmo das hordas.",
        self.fonts.body,
        GOLD,
        (WIDTH / 2, 91),
        "center",
    )
    descriptions = {
        "easy": (
            "COMEÇAR TRANQUILO",
            (
                "175 suprimentos iniciais",
                "Limite de reserva: 420",
                "Inimigos mais frágeis para aprender",
            ),
        ),
        "medium": (
            "CAMPANHA EQUILIBRADA",
            (
                "135 suprimentos iniciais",
                "Pressão progressiva e equilibrada",
                "12 ondas em três atos táticos",
            ),
        ),
        "hard": (
            "SOBREVIVÊNCIA VETERANA",
            (
                "105 suprimentos iniciais",
                "Limite de reserva: 240",
                "Hordas mais rápidas e resistentes",
            ),
        ),
    }
    for index, (key, button_rect) in enumerate(self.difficulty_buttons()):
        profile = difficulty_profile(key)
        card = pygame.Rect(button_rect.x - 25, 150, button_rect.width + 50, 370)
        self.panel(card, 235, profile["accent"], 14)
        subtitle, lines = descriptions[key]
        self.draw_text(
            profile["label"],
            self.fonts.title,
            profile["accent"],
            (card.centerx, card.y + 32),
            "center",
            True,
        )
        self.draw_text(
            subtitle, self.fonts.small, WHITE, (card.centerx, card.y + 92), "center"
        )
        for line_index, line in enumerate(lines):
            y = card.y + 148 + line_index * 53
            pygame.draw.circle(
                self.screen, profile["accent"], (card.x + 31, y + 8), 5
            )
            self.draw_wrapped(
                line,
                self.fonts.small,
                WHITE,
                pygame.Rect(card.x + 46, y - 7, card.width - 64, 31),
                2,
            )
        self.draw_wrapped(
            profile["summary"],
            self.fonts.tiny,
            GRAY,
            pygame.Rect(card.x + 23, card.bottom - 71, card.width - 46, 38),
            2,
            center=True,
        )
        self.button(f"ESCOLHER {profile['label']}", button_rect, profile["accent"])
    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )

def draw_campaign(self) -> None:
    self.screen.blit(self.assets.images["menu"], (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 11, 16, 170))
    self.screen.blit(veil, (0, 0))
    self.draw_text(
        "MAPA DA CAMPANHA", self.fonts.title, WHITE, (WIDTH / 2, 38), "center", True
    )
    profile = difficulty_profile(self.difficulty)
    self.draw_text(
        f"Modo {profile['label']} — {profile['summary']}",
        self.fonts.body,
        profile["accent"],
        (WIDTH / 2, 84),
        "center",
    )
    self.draw_text(
        "Escolha Cidade, Deserto ou Cachoeira. São 12 ondas: duas comuns, um sub-boss e um boss por ato.",
        self.fonts.small,
        GOLD,
        (WIDTH / 2, 111),
        "center",
    )
    for index, region in enumerate(("city", "desert", "beach")):
        info = REGIONS[region]
        rect = pygame.Rect(72 + index * 402, 182, 360, 350)
        unlocked = True
        background = self.assets.images[f"{region}_bg"]
        crop = pygame.Rect(index * 160, 150, 360, 208)
        image = pygame.Surface((360, 210))
        image.blit(background, (0, 0), crop)
        self.screen.blit(image, rect)
        self.panel(
            rect,
            105 if unlocked else 215,
            info["accent"] if unlocked else (75, 75, 75),
            14,
        )
        if not unlocked:
            lock = pygame.Rect(rect.centerx - 28, rect.y + 104, 56, 66)
            pygame.draw.rect(self.screen, (49, 54, 60), lock, border_radius=9)
            pygame.draw.arc(
                self.screen, GRAY, (lock.x + 9, lock.y - 27, 38, 40), 0, math.pi, 5
            )
            self.draw_text(
                "BLOQUEADA",
                self.fonts.h2,
                GRAY,
                (rect.centerx, rect.y + 184),
                "center",
            )
        else:
            self.draw_text(
                info["short"],
                self.fonts.h1,
                WHITE,
                (rect.centerx, rect.y + 222),
                "center",
                True,
            )
            self.draw_text(
                info["tag"],
                self.fonts.small,
                info["accent"],
                (rect.centerx, rect.y + 252),
                "center",
            )
            best = self.save["best_wave"].get(region, 0)
            status = (
                "REGIÃO PROTEGIDA"
                if region in self.save["completed"]
                else f"Melhor: onda {best}/{TOTAL_WAVES}"
            )
            self.draw_text(
                status,
                self.fonts.small,
                GOLD if region in self.save["completed"] else WHITE,
                (rect.centerx, rect.y + 286),
                "center",
            )
            self.button(
                "PREPARAR DEFESA",
                pygame.Rect(rect.x + 55, rect.y + 304, 250, 34),
                info["accent"],
            )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )

def draw_selection(self) -> None:
    region = REGIONS[self.region]
    self.screen.blit(self.assets.images[f"{self.region}_bg"], (0, 0))
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((6, 11, 14, 157))
    self.screen.blit(shade, (0, 0))
    profile = difficulty_profile(self.difficulty)
    self.draw_text(
        f"SELEÇÃO DE CARTAS — {region['name'].upper()} — {profile['label']}",
        self.fonts.h1,
        WHITE,
        (WIDTH / 2, 20),
        "center",
        True,
    )
    self.draw_text(
        "Escolha até três cartas • clique em DETALHES para inspecionar",
        self.fonts.small,
        profile["accent"],
        (WIDTH / 2, 56),
        "center",
    )
    self.draw_text(
        f"{len(self.selection)}/3 selecionadas",
        self.fonts.h2,
        region["accent"],
        (WIDTH - 40, 66),
        "topright",
    )
    for key, display, rect in self.selection_cards():
        data = DEFENSES[key]
        chosen = (key, display) in self.selection
        self.panel(rect, 232, GOLD if chosen else (91, 105, 107), 10)
        portrait = pygame.Rect(rect.x + 8, rect.y + 38, 104, 158)
        self.draw_portrait_backdrop(portrait, region["accent"])
        sprite = self.card_sprite(self.region, key, int(data["sprite"]))
        self.blit_actor_in_rect(sprite, portrait, 146, outline=region["accent"])
        self.draw_wrapped(
            display.upper(),
            self.fonts.tiny,
            WHITE,
            pygame.Rect(rect.x + 12, rect.y + 11, rect.width - 45, 24),
            1,
        )
        stat_x = rect.x + 120
        reload_seconds = weapon_reload_seconds(data)
        reload_text = f"{reload_seconds:.1f}s" if reload_seconds > 0 else "—"
        self.draw_text(
            f"VIDA  {int(data['hp'])}",
            self.fonts.small,
            WHITE,
            (stat_x, rect.y + 55),
        )
        self.draw_text(
            f"DANO  {int(data['damage'])}",
            self.fonts.small,
            GOLD,
            (stat_x, rect.y + 88),
        )
        self.draw_text(
            f"RECARGA  {reload_text}", self.fonts.tiny, TEAL, (stat_x, rect.y + 123)
        )
        inspect_rect = self.selection_inspect_button(rect)
        self.button("DETALHES", inspect_rect, (78, 112, 121))
        if chosen:
            check_x, check_y = rect.right - 24, rect.y + 22
            pygame.draw.line(
                self.screen,
                GOLD,
                (check_x - 8, check_y),
                (check_x - 2, check_y + 7),
                4,
            )
            pygame.draw.line(
                self.screen,
                GOLD,
                (check_x - 2, check_y + 7),
                (check_x + 9, check_y - 8),
                4,
            )
    selected_names = (
        " • ".join(display for _key, display in self.selection) or "nenhuma carta"
    )
    self.draw_text(
        f"EQUIPE: {selected_names}",
        self.fonts.tiny,
        WHITE,
        (WIDTH / 2, 620),
        "center",
        True,
    )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 45, 650, 160, 46), (98, 126, 137)
    )
    self.button(
        "INICIAR MISSÃO",
        pygame.Rect(WIDTH - 290, 650, 240, 46),
        region["accent"],
        1 <= len(self.selection) <= 3,
    )
    if self.selection_inspect_key is not None:
        self.draw_selection_inspection(self.selection_inspect_key)

def draw_selection_inspection(self, key: str) -> None:
    """Abre os dados completos somente após o clique em DETALHES."""
    if key not in DEFENSES or key not in self.available_selection_keys():
        self.selection_inspect_key = None
        return
    data = DEFENSES[key]
    display = self.card_display_name(self.region, key)
    accent = REGIONS[self.region]["accent"]
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((2, 5, 8, 214))
    self.screen.blit(veil, (0, 0))
    modal = pygame.Rect(160, 74, 960, 536)
    self.panel(modal, 248, accent, 16)
    portrait = pygame.Rect(modal.x + 28, modal.y + 55, 300, 390)
    self.draw_portrait_backdrop(portrait, accent)
    sprite = self.card_sprite(self.region, key, int(data["sprite"]))
    self.blit_actor_in_rect(sprite, portrait, 332, outline=accent)
    text_x = modal.x + 360
    text_w = modal.width - 392
    self.draw_text(
        display.upper(), self.fonts.h1, WHITE, (text_x, modal.y + 38), shadow=True
    )
    self.draw_text(
        str(data.get("tactical_unit", "Unidade regional")),
        self.fonts.small,
        accent,
        (text_x, modal.y + 78),
    )
    reload_seconds = weapon_reload_seconds(data)
    stats = f"VIDA {int(data['hp'])}  •  DANO {int(data['damage'])}  •  RECARGA {reload_seconds:.1f}s  •  CUSTO {int(data['cost'])}"
    self.draw_wrapped(
        stats,
        self.fonts.tiny,
        GOLD,
        pygame.Rect(text_x, modal.y + 108, text_w, 36),
        2,
    )
    self.draw_text("HISTÓRIA", self.fonts.tiny, GRAY, (text_x, modal.y + 158))
    self.draw_wrapped(
        str(data["lore"]),
        self.fonts.small,
        WHITE,
        pygame.Rect(text_x, modal.y + 179, text_w, 65),
        3,
    )
    self.draw_text(
        "FUNÇÃO NO CAMPO", self.fonts.tiny, GRAY, (text_x, modal.y + 260)
    )
    self.draw_wrapped(
        str(data["tactical_function"]),
        self.fonts.small,
        TEAL,
        pygame.Rect(text_x, modal.y + 281, text_w, 48),
        2,
    )
    self.draw_text(
        "POR QUE ESSA CARTA É NECESSÁRIA",
        self.fonts.tiny,
        GRAY,
        (text_x, modal.y + 348),
    )
    self.draw_wrapped(
        str(data["mechanical_need"]),
        self.fonts.small,
        WHITE,
        pygame.Rect(text_x, modal.y + 369, text_w, 65),
        3,
    )
    self.button("FECHAR DETALHES", self.selection_inspection_close_rect(), accent)

def draw_characters(self) -> None:
    """Exibe todos os defensores e os infectados ativos da região."""
    region = self.character_region
    info = REGIONS[region]
    self.screen.blit(self.assets.images[f"{region}_bg"], (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((3, 8, 12, 184))
    self.screen.blit(veil, (0, 0))
    self.draw_text(
        "PERSONAGENS DO JOGO",
        self.fonts.title,
        WHITE,
        (WIDTH / 2, 24),
        "center",
        True,
    )
    for index, key in enumerate(("city", "desert", "beach")):
        rect = pygame.Rect(340 + index * 205, 82, 190, 42)
        self.button(
            REGIONS[key]["short"],
            rect,
            REGIONS[key]["accent"] if key == region else (76, 92, 98),
        )
    self.button(
        "SOLDADO",
        pygame.Rect(424, 136, 205, 40),
        info["accent"] if self.dossier_kind == "units" else (70, 80, 85),
    )
    self.button(
        "ZUMBI",
        pygame.Rect(650, 136, 205, 40),
        (126, 196, 91) if self.dossier_kind == "zombies" else (70, 80, 85),
    )
    is_unit = self.dossier_kind == "units"
    keys = self.character_keys()
    if not keys:
        self.draw_text(
            "Nenhum personagem disponível.",
            self.fonts.h1,
            RED,
            (WIDTH / 2, 330),
            "center",
        )
        self.button(
            "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
        )
        return
    self.character_index = int(clamp(self.character_index, 0, len(keys) - 1))
    self.button("ANTERIOR", pygame.Rect(260, 184, 180, 40), (70, 88, 96))
    self.draw_text(
        f"{self.character_index + 1}/{len(keys)}",
        self.fonts.h2,
        WHITE,
        (WIDTH / 2, 204),
        "center",
    )
    self.button("PRÓXIMO", pygame.Rect(WIDTH - 440, 184, 180, 40), (70, 88, 96))

    key = keys[self.character_index]
    data = DEFENSES[key] if is_unit else ({**ENEMIES, **BOSSES})[key]
    actor = (DEFENDER_ACTOR_BY_KEY if is_unit else ENEMY_ACTOR_BY_KEY)[key]
    if self.assets.production_clips is None:
        self.assets.prepare_production_animations()
    clip_bank = self.assets.production_clips or {}
    if actor not in clip_bank:
        self.draw_text(
            "Arte do personagem ainda não foi carregada.",
            self.fonts.h1,
            RED,
            (WIDTH / 2, 330),
            "center",
        )
        self.button(
            "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
        )
        return
    sprite = clip_bank[actor]["idle" if is_unit else "move"].frames[1]
    # Chefes largos não podem usar um quadro estreito da folha de combate
    # como retrato. Serra, tubos, braços e pernas atravessavam a fronteira
    # matemática da célula e apareciam cortados no dossiê. Os três retratos
    # completos de cada região têm fundo transparente e enquadramento
    # próprio, sem alterar as animações usadas no campo.
    boss_keys = REGION_BOSSES.get(region, ())
    if not is_unit and key in boss_keys:
        portraits = self.assets.boss_portraits.get(region, [])
        portrait_index = boss_keys.index(key)
        if portrait_index < len(portraits):
            sprite = portraits[portrait_index]

    card = pygame.Rect(210, 232, 860, 358)
    accent = info["accent"] if is_unit else (132, 207, 93)
    self.panel(card, 240, accent, 16)
    portrait = pygame.Rect(card.x + 28, card.y + 34, 245, 278)
    self.draw_portrait_backdrop(portrait, accent)
    crawler = key in CRAWLER_ENEMIES
    dedicated_boss_portrait = not is_unit and key in boss_keys
    self.blit_actor_in_rect(
        sprite,
        portrait,
        254 if dedicated_boss_portrait else (238 if not crawler else 164),
        source_body_height=(
            None
            if dedicated_boss_portrait
            else (130.0 if is_unit else (92.0 if crawler else 136.0))
        ),
        outline=accent,
    )
    text_x = card.x + 306
    self.draw_text(
        str(data.get("base", data.get("name"))),
        self.fonts.h1,
        WHITE,
        (text_x, card.y + 32),
        shadow=True,
    )
    faction = {
        "city": "Polícia dos Estados Unidos • Terminal Félix-13",
        "desert": "Forças Armadas do Egito • Escavação Khepra",
        "beach": "Marinha do Brasil • Cachoeira Contaminada",
    }[region]
    self.draw_text(
        faction if is_unit else info["tag"],
        self.fonts.small,
        accent,
        (text_x, card.y + 72),
    )
    if is_unit:
        if data["role"] == "radio":
            stats = (
                f"VIDA {int(data['hp'])}     SUPRIMENTOS +{int(data['supply_gain'])}",
                f"CICLO {float(data['cooldown']):.1f}s     NÃO ATACA     CARTA 10s",
            )
        else:
            stats = (
                f"VIDA {int(data['hp'])}     DANO {int(data['damage'])}     ALCANCE {int(data['range'])}",
                f"MUNIÇÃO {int(data['ammo'])}     RECARGA {weapon_reload_seconds(data):.1f}s     CARTA 10s",
            )
    else:
        action = (
            "rastejar • morder"
            if crawler
            else (
                "correr • avançar"
                if "dash" in data.get("tags", ())
                else "caminhar • morder"
            )
        )
        stats = (
            f"VIDA {int(data['hp'])}     DANO {int(data['damage'])}     VELOCIDADE {int(data['speed'])}",
            f"AÇÃO: {action} • receber dano • desaparecer",
        )
    for index, line in enumerate(stats):
        box = pygame.Rect(text_x, card.y + 105 + index * 49, 522, 37)
        pygame.draw.rect(self.screen, (20, 31, 36), box, border_radius=8)
        self.draw_text(
            line,
            self.fonts.small,
            GOLD if index == 0 else TEAL,
            (box.x + 14, box.y + 10),
        )
    if is_unit:
        self.draw_wrapped(
            str(data["lore"]),
            self.fonts.small,
            WHITE,
            pygame.Rect(text_x, card.y + 205, 522, 48),
            2,
        )
        self.draw_wrapped(
            "FUNÇÃO: " + str(data["tactical_function"]),
            self.fonts.tiny,
            TEAL,
            pygame.Rect(text_x, card.y + 261, 522, 30),
            2,
        )
        self.draw_wrapped(
            "NECESSÁRIA: " + str(data["mechanical_need"]),
            self.fonts.tiny,
            GOLD,
            pygame.Rect(text_x, card.y + 296, 522, 35),
            2,
        )
    else:
        counter = str(data.get("counter_label", "Dano concentrado"))
        defense = str(data.get("defense_name", "sem defesa especial"))
        self.draw_wrapped(
            str(data["ability"]),
            self.fonts.body,
            WHITE,
            pygame.Rect(text_x, card.y + 205, 522, 62),
            3,
        )
        self.draw_wrapped(
            f"DEFESA: {defense} • COUNTER: {counter}",
            self.fonts.tiny,
            GOLD,
            pygame.Rect(text_x, card.y + 282, 522, 38),
            2,
        )
    self.draw_text(
        "INTEGRADO • arte, animação e ficha próprias desta região",
        self.fonts.tiny,
        GRAY,
        (text_x, card.bottom - 22),
    )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )

def draw_comic_bubble(
    self,
    rect: pygame.Rect,
    text: str,
    tail: tuple[int, int],
) -> None:
    """Balão de fala verdadeiro, com cauda apontando para o personagem."""
    fill = (255, 250, 224)
    border = (22, 24, 25)
    attach_x = int(clamp(tail[0], rect.left + 24, rect.right - 24))
    attach_y = rect.bottom - 3 if tail[1] >= rect.centery else rect.top + 3
    pygame.draw.polygon(
        self.screen,
        fill,
        ((attach_x - 12, attach_y), (attach_x + 12, attach_y), tail),
    )
    pygame.draw.lines(
        self.screen,
        border,
        False,
        ((attach_x - 12, attach_y), tail, (attach_x + 12, attach_y)),
        3,
    )
    pygame.draw.rect(self.screen, fill, rect, border_radius=18)
    pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
    self.draw_wrapped(
        text, self.fonts.small, INK, rect.inflate(-18, -13), 3, center=True
    )

def draw_comic_actor(
    self,
    actor: str,
    state: str,
    frame_index: int,
    point: tuple[int, int],
    body_height: int,
    *,
    flip: bool = False,
) -> pygame.Rect:
    assert self.assets.production_clips is not None
    frames = self.assets.production_clips[actor][state].frames
    sprite = frames[frame_index % len(frames)]
    content = sprite.get_bounding_rect(min_alpha=8)
    sprite = sprite.subsurface(content).copy()
    source_height = 130.0 if actor.endswith("guard") else 136.0
    width, height = animated_actor_render_scale(
        sprite,
        1.0,
        body_height=body_height,
        source_body_height=source_height,
    )
    rendered = pygame.transform.smoothscale(
        sprite, (max(1, round(width)), max(1, round(height)))
    )
    if flip:
        rendered = pygame.transform.flip(rendered, True, False)
    rect = rendered.get_rect(midbottom=point)
    self.screen.blit(rendered, rect)
    return rect

def draw_story(self) -> None:
    """Prólogo em quadrinhos: personagens, ação, falas e continuidade."""
    pages = (
        {
            "region": "city",
            "title": "1 • O ACIDENTE FÉLIX",
            "captions": (
                "NOVA YORK — 23h47. O reator experimental perde contenção.",
                "A descarga mistura radiação, fármacos e material biológico.",
                "A polícia fecha o Terminal Félix-13 — tarde demais.",
            ),
            "dialogue": (
                "Central, o reator da Félix explodiu!",
                "Eles eram funcionários... agora estão vindo para a rua.",
                "Fechem o Terminal! Ninguém passa!",
            ),
            "sfx": ("WAA-OOO!", "KRA-KOOM!", "CLAC!"),
        },
        {
            "region": "desert",
            "title": "2 • OS MORTOS DE KHEPRA",
            "captions": (
                "EGITO. O vento leva partículas da Félix até a escavação.",
                "Sob a areia, corpos preservados despertam contaminados.",
                "O Sa'ka forma quatro linhas diante da necrópole.",
            ),
            "dialogue": (
                "Comando, a areia ao redor da tumba está brilhando!",
                "Isso não é magia. É a mesma praga de Nova York.",
                "Sa'ka, armas prontas! Eles estão saindo!",
            ),
            "sfx": ("WHOOOSH", "KRRRAA...", "CHK-CHK!"),
        },
        {
            "region": "beach",
            "title": "3 • A CACHOEIRA CONTAMINADA",
            "captions": (
                "MINAS GERAIS. Resíduos alcançam o rio acima da cachoeira.",
                "A correnteza transforma banhistas e equipes de resgate.",
                "A Marinha fecha as margens enquanto prepara embarcações para os canais.",
            ),
            "dialogue": (
                "A água ficou verde. Retirem todos da correnteza!",
                "Há infectados nas margens e movimento dentro dos canais!",
                "Marinheiros na terra; barcos e submarinos nos canais!",
            ),
            "sfx": ("SPLASH!", "GHHH...", "TAC!"),
        },
    )
    page = pages[self.story_page]
    region = page["region"]
    accent = REGIONS[region]["accent"]
    bg = self.assets.images[f"{region}_bg"]
    defender_actor = DEFENDER_ACTOR_BY_KEY[BASIC_DEFENDER_BY_REGION[region]]
    enemy_actor = ENEMY_ACTOR_BY_KEY[BASIC_ENEMY_BY_REGION[region]]

    self.screen.fill((12, 11, 10))
    self.draw_text(
        "HISTÓRIA DO JOGO", self.fonts.title, WHITE, (WIDTH / 2, 18), "center", True
    )
    self.draw_text(page["title"], self.fonts.h2, accent, (WIDTH / 2, 66), "center")
    panels = (
        (pygame.Rect(55, 103, 1170, 235), pygame.Rect(0, 70, 1280, 420)),
        (pygame.Rect(55, 356, 565, 246), pygame.Rect(0, 140, 690, 480)),
        (pygame.Rect(660, 356, 565, 246), pygame.Rect(590, 120, 690, 500)),
    )
    for index, (dest, source) in enumerate(panels):
        image = pygame.transform.smoothscale(bg.subsurface(source), dest.size)
        self.screen.blit(image, dest)
        # Retícula e borda grossa deixam o quadro com leitura impressa,
        # sem transformar o cenário numa simples miniatura do mapa.
        shade = pygame.Surface(dest.size, pygame.SRCALPHA)
        shade.fill((15, 15, 18, 34 if index == 0 else 50))
        self.screen.blit(shade, dest)
        for x in range(dest.left + 3, dest.right, 7):
            for y in range(dest.top + 3, dest.bottom, 7):
                pygame.draw.circle(self.screen, (0, 0, 0, 36), (x, y), 1)
        pygame.draw.rect(self.screen, (246, 239, 205), dest, 6)

        narration = pygame.Rect(
            dest.x + 12, dest.y + 10, min(dest.width - 24, 430), 38
        )
        pygame.draw.rect(self.screen, (246, 214, 113), narration, border_radius=3)
        pygame.draw.rect(self.screen, INK, narration, 2, border_radius=3)
        self.draw_wrapped(
            page["captions"][index],
            self.fonts.tiny,
            INK,
            narration.inflate(-12, -8),
            2,
        )

        floor = dest.bottom - 10
        if index == 0:
            guard = self.draw_comic_actor(
                defender_actor, "idle", 2, (dest.x + 250, floor), 132
            )
            self.draw_comic_actor(
                enemy_actor, "move", 4, (dest.right - 230, floor), 137
            )
            bubble = pygame.Rect(dest.x + 405, dest.y + 57, 355, 70)
            tail = (guard.centerx + 20, guard.top + 22)
        elif index == 1:
            guard = self.draw_comic_actor(
                defender_actor, "idle", 1, (dest.x + 92, floor), 112
            )
            self.draw_comic_actor(
                enemy_actor, "move", 1, (dest.centerx + 70, floor + 3), 112
            )
            self.draw_comic_actor(
                enemy_actor, "bite", 4, (dest.right - 58, floor), 120
            )
            bubble = pygame.Rect(dest.x + 148, dest.y + 54, 365, 66)
            tail = (guard.centerx + 8, guard.top + 18)
        else:
            guard = self.draw_comic_actor(
                defender_actor, "shoot", 3, (dest.centerx - 65, floor), 120
            )
            self.draw_comic_actor(
                enemy_actor, "hit", 3, (dest.right - 72, floor), 112
            )
            bubble = pygame.Rect(dest.x + 24, dest.y + 52, 310, 66)
            tail = (guard.centerx + 16, guard.top + 26)
        self.draw_comic_bubble(bubble, page["dialogue"][index], tail)
        self.draw_text(
            page["sfx"][index],
            self.fonts.h2,
            (255, 234, 91),
            (dest.right - 22, dest.y + 18),
            "topright",
            True,
        )

    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )
    self.button(
        "ANTERIOR", pygame.Rect(245, 646, 170, 44), accent, self.story_page > 0
    )
    self.draw_text(
        f"PÁGINA {self.story_page + 1}/3",
        self.fonts.small,
        WHITE,
        (WIDTH / 2, 661),
        "center",
    )
    self.button(
        "PRÓXIMA",
        pygame.Rect(WIDTH - 415, 646, 170, 44),
        accent,
        self.story_page < 2,
    )

def draw_settings(self) -> None:
    self.screen.blit(self.assets.images["menu"], (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((3, 8, 12, 190))
    self.screen.blit(veil, (0, 0))
    card = pygame.Rect(285, 112, 710, 478)
    self.panel(card, 244, TEAL, 16)
    self.draw_text(
        "CONFIGURAÇÕES",
        self.fonts.title,
        WHITE,
        (card.centerx, card.y + 54),
        "center",
        True,
    )
    self.draw_text("CONTROLE", self.fonts.h2, GOLD, (card.x + 95, 218))
    control_label = "MOUSE (PADRÃO)" if self.control_mode == "mouse" else "TECLADO"
    self.button(control_label, self.settings_control_rect(), TEAL)
    self.draw_text("SOM", self.fonts.h2, GOLD, (card.x + 95, 299))
    sound_label = (
        "LIGADO"
        if self.audio.enabled and self.audio.ready
        else ("INDISPONÍVEL" if not self.audio.ready else "DESLIGADO")
    )
    self.button(
        sound_label,
        self.settings_sound_rect(),
        TEAL if self.audio.enabled and self.audio.ready else (92, 108, 116),
        self.audio.ready,
    )
    self.draw_text("VOLUME", self.fonts.h2, GOLD, (card.x + 95, 380))
    self.button(
        "−", self.settings_volume_minus_rect(), (92, 126, 137), self.audio.ready
    )
    self.button(
        "+", self.settings_volume_plus_rect(), (92, 126, 137), self.audio.ready
    )
    volume_bar = pygame.Rect(581, 417, 118, 18)
    pygame.draw.rect(self.screen, (29, 42, 49), volume_bar, border_radius=8)
    pygame.draw.rect(
        self.screen,
        TEAL,
        (
            volume_bar.x,
            volume_bar.y,
            int(volume_bar.width * self.audio.volume),
            volume_bar.height,
        ),
        border_radius=8,
    )
    self.draw_text(
        f"{int(round(self.audio.volume * 100))}%",
        self.fonts.tiny,
        WHITE,
        (volume_bar.centerx, volume_bar.y - 23),
        "center",
    )
    self.draw_text("VÍDEO", self.fonts.h2, GOLD, (card.x + 95, 463))
    video_rect = pygame.Rect(505, 458, 270, 42)
    pygame.draw.rect(self.screen, (20, 72, 68), video_rect, border_radius=7)
    pygame.draw.rect(
        self.screen, (228, 235, 228), video_rect, width=1, border_radius=7
    )
    self.draw_text(
        "SOFTWARE · CPU/RAM",
        self.fonts.small,
        WHITE,
        video_rect.center,
        "center",
        True,
    )
    if self.control_mode == "keyboard":
        help_text = "WASD/setas: mover cursor • Q/E: trocar carta • Enter/F/Espaço: posicionar • R: remover • N/Tab: próxima onda • P: pausar"
    else:
        help_text = "Mouse: escolher carta, apontar para uma casa e clicar. Teclas 1–8 continuam selecionando cartas e P pausa a partida."
    self.draw_wrapped(
        help_text,
        self.fonts.tiny,
        WHITE,
        pygame.Rect(card.x + 70, 518, card.width - 140, 52),
        3,
        center=True,
    )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )

def draw_howto(self) -> None:
    self.screen.blit(self.assets.images["menu"], (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 10, 14, 186))
    self.screen.blit(veil, (0, 0))
    card = pygame.Rect(116, 72, WIDTH - 232, 560)
    self.panel(card, 238, GOLD, 16)
    self.draw_text(
        "COMO JOGAR", self.fonts.title, WHITE, (card.centerx, card.y + 30), "center"
    )
    lines = [
        (
            "1. Monte a equipe",
            "No carrossel, veja uma carta ampliada por vez e escolha até três tropas próprias daquele cenário.",
        ),
        (
            "2. Posicione na faixa",
            "A tropa fica centralizada no terreno escolhido e ataca somente o zumbi que avança naquela mesma linha.",
        ),
        (
            "3. Leia os counters",
            "Imunidades exigem a carta indicada na ficha. Rompa a defesa e aproveite a janela antes que ela se feche.",
        ),
        (
            "4. Proteção de emergência",
            "Tratores, drones e cargas ficam no centro do começo da faixa. O primeiro invasor que chega até eles ativa a contenção.",
        ),
        (
            "5. Ondas e dificuldade",
            "Sobreviva a 12 ondas em três atos: duas comuns, uma de sub-boss e uma de boss. Cada ato aumenta vida, dano e densidade.",
        ),
        (
            "6. Comandos",
            "Mouse é o padrão. Em Configurações, Teclado ativa WASD/setas, Q/E para cartas, Enter/F/Espaço para posicionar, R para remover, N/Tab para a onda e P para pausar.",
        ),
    ]
    y = card.y + 102
    for head, body in lines:
        self.draw_text(head, self.fonts.h2, GOLD, (card.x + 48, y))
        self.draw_wrapped(
            body,
            self.fonts.body,
            WHITE,
            pygame.Rect(card.x + 48, y + 27, card.width - 96, 46),
            2,
        )
        y += 76
    self.button(
        "VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137)
    )

def draw_unit_evolution_dossier(self) -> None:
    """Mostra a progressão literalmente em duas faixas: N1 sobre N2."""
    self.screen.blit(self.assets.images["menu"], (0, 0))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 10, 14, 190))
    self.screen.blit(overlay, (0, 0))
    accent = REGIONS[self.region]["accent"]
    self.draw_text(
        "EVOLUÇÃO DOS SOLDADOS",
        self.fonts.title,
        WHITE,
        (WIDTH / 2, 20),
        "center",
        True,
    )
    self.draw_text(
        "TELA LEGADA DESATIVADA • use PERSONAGENS no menu principal",
        self.fonts.small,
        accent,
        (WIDTH / 2, 70),
        "center",
    )
    items = self.dossier_items()
    start = self.dossier_page * 6
    for index, item in enumerate(items[start : start + 6]):
        row, col = divmod(index, 3)
        rect = pygame.Rect(52 + col * 404, 110 + row * 247, 372, 226)
        self.panel(rect, 238, accent, 12)
        if item["kind"] == "promoter":
            data = DEFENSES["instrutor"]
            sprite = self.card_sprite(self.region, "instrutor", int(data["sprite"]))
            self.blit_sprite(sprite, rect.x + 18, rect.y + 48, 106, 126)
            self.draw_text(
                "CARTA DE PROMOÇÃO",
                self.fonts.tiny,
                GOLD,
                (rect.x + 140, rect.y + 25),
            )
            self.draw_text(
                data["base"], self.fonts.h2, WHITE, (rect.x + 140, rect.y + 48)
            )
            self.draw_text(
                f"Custo {data['cost']} SUP • HP {data['hp']}",
                self.fonts.tiny,
                GOLD,
                (rect.x + 140, rect.y + 78),
            )
            self.draw_wrapped(
                data["ability"],
                self.fonts.small,
                (219, 229, 225),
                pygame.Rect(rect.x + 140, rect.y + 104, 210, 74),
                4,
            )
            continue
        for tier_index, key in enumerate((item["l1"], item["l2"])):
            data = DEFENSES[key]
            tier = pygame.Rect(
                rect.x + 10, rect.y + 27 + tier_index * 96, rect.width - 20, 88
            )
            tier_color = (102, 128, 135) if tier_index == 0 else GOLD
            self.panel(tier, 205, tier_color, 8)
            sprite = self.card_sprite(self.region, key, int(data["sprite"]))
            self.blit_sprite(sprite, tier.x + 5, tier.y + 8, 60, 72)
            self.draw_text(
                f"N{data['level']}",
                self.fonts.tiny,
                tier_color,
                (tier.x + 74, tier.y + 9),
                shadow=True,
            )
            self.draw_text(
                str(data["base"]),
                self.fonts.small,
                WHITE,
                (tier.x + 103, tier.y + 7),
            )
            self.draw_text(
                f"HP {int(data['hp'])} • DANO {int(data['damage'])} • ALC {int(data['range'])}",
                self.fonts.tiny,
                GOLD,
                (tier.x + 74, tier.y + 29),
            )
            self.draw_wrapped(
                str(data["ability"]),
                self.fonts.tiny,
                (219, 229, 225),
                pygame.Rect(tier.x + 74, tier.y + 45, tier.width - 84, 34),
                2,
            )
    pages = max(1, math.ceil(len(items) / 6))
    self.draw_text(
        f"Página {self.dossier_page + 1}/{pages} • uniforme atual: {REGIONS[self.region]['short'].title()}",
        self.fonts.small,
        WHITE,
        (WIDTH / 2, 664),
        "center",
    )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137)
    )
    self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

def draw_dossier(self) -> None:
    is_units = self.dossier_kind == "units"
    if is_units:
        self.draw_unit_evolution_dossier()
        return
    self.screen.blit(self.assets.images["menu"], (0, 0))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 10, 14, 190))
    self.screen.blit(overlay, (0, 0))
    heading = "INFORMAÇÕES DOS SOLDADOS" if is_units else "INFORMAÇÕES DOS ZUMBIS"
    accent = TEAL if is_units else (139, 222, 106)
    self.draw_text(
        heading, self.fonts.title, WHITE, (WIDTH / 2, 24), "center", True
    )
    self.draw_text(
        "As fichas abaixo mostram função, poder e contraponto tático.",
        self.fonts.body,
        accent,
        (WIDTH / 2, 70),
        "center",
    )
    items = self.dossier_items()
    start = self.dossier_page * 6
    page_items = items[start : start + 6]
    for index, item in enumerate(page_items):
        row, col = divmod(index, 3)
        rect = pygame.Rect(52 + col * 404, 123 + row * 235, 372, 208)
        self.panel(rect, 236, accent, 12)
        icon_index = (
            DEFENSES[item["key"]]["sprite"]
            if is_units
            else ({**ENEMIES, **BOSSES}[item["key"]]["sprite"])
        )
        sprite_region = (
            "city"
            if is_units
            else (
                "city"
                if item["key"]
                in {
                    "caminhante",
                    "corredor",
                    "rastejante",
                    "conehead",
                    "policial",
                    "militar",
                    "escudo",
                    "cuspidor",
                    "divisor",
                    "gritador",
                    "saltador",
                    "bruto",
                    "bruto_demolidor",
                    "comandante_mortos",
                    "cuspidor_alfa",
                }
                else (
                    "desert"
                    if item["key"]
                    in {
                        "digger",
                        "ladrao",
                        "curandeiro",
                        "parasita",
                        "mutante",
                        "necromante_minion",
                        "mutante_ruinas",
                        "necromante",
                        "colosso_mutante",
                    }
                    else "beach"
                )
            )
        )
        # A ficha de zumbis deve usar exatamente o mesmo retrato que a
        # batalha. Antes esta tela ainda puxava o quadro antigo do atlas
        # urbano para o Saltador, que incluía uma pilastra de cenário.
        # O retrato exclusivo da Beta 3 não traz obstáculo algum.
        dossier_sheet = (
            {
                ("city", "caminhante"): "city_walker_walk",
                ("desert", "digger"): "desert_digger_states",
                ("beach", "nadador"): "beach_swimmer_walk",
            }.get((sprite_region, item["key"]))
            if not is_units
            else None
        )
        if not is_units and item["key"] in BOSSES:
            boss_frames = self.assets.animation_frames.get(
                f"{sprite_region}_boss_actions", []
            )
            boss_row = REGIONS[sprite_region]["bosses"].index(item["key"])
            sprite = (
                boss_frames[boss_row * 4]
                if len(boss_frames) >= 12
                else self.assets.zombie(sprite_region, int(icon_index))
            )
        elif dossier_sheet and self.assets.animation_frames.get(dossier_sheet):
            sprite = self.assets.animation_frames[dossier_sheet][0]
        elif (
            not is_units
            and item["key"] == "saltador"
            and "zombie_jumper_beta3" in self.assets.images
        ):
            sprite = self.assets.images["zombie_jumper_beta3"]
        elif (
            not is_units
            and item["key"] == "rastejante"
            and "zombie_crawler_beta3" in self.assets.images
        ):
            sprite = self.assets.images["zombie_crawler_beta3"]
        else:
            sprite = (
                self.card_sprite(sprite_region, item["key"], int(icon_index))
                if is_units
                else self.assets.zombie(sprite_region, int(icon_index))
            )
        self.blit_sprite(sprite, rect.x + 14, rect.y + 44, 105, 118)
        self.draw_text(
            item["name"], self.fonts.h2, WHITE, (rect.x + 132, rect.y + 22)
        )
        self.draw_text(
            item["sub"], self.fonts.small, accent, (rect.x + 132, rect.y + 51)
        )
        stat = (
            f"Custo: {item['cost']} SUP • Nível {item['level']}"
            if is_units
            else f"Vida base: {item['hp']}"
        )
        self.draw_text(stat, self.fonts.tiny, GOLD, (rect.x + 132, rect.y + 76))
        self.draw_wrapped(
            item["ability"],
            self.fonts.small,
            (219, 229, 225),
            pygame.Rect(rect.x + 132, rect.y + 100, 220, 83),
            4,
        )
    pages = max(1, math.ceil(len(items) / 6))
    self.draw_text(
        f"Página {self.dossier_page + 1}/{pages}",
        self.fonts.small,
        WHITE,
        (WIDTH / 2, 664),
        "center",
    )
    self.button(
        "VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137)
    )
    self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

def draw_battle(self) -> None:
    assert self.battle is not None
    battle = self.battle
    background = self.assets.images[f"{battle.region}_bg"]
    shake_x = int(math.sin(self.scene_elapsed * 55) * 4 * battle.shake)
    shake_y = int(math.cos(self.scene_elapsed * 37) * 3 * battle.shake)
    self.screen.blit(background, (shake_x, shake_y))
    # Generais, piras, efeitos de horda e clima de chefe são exatamente
    # as animações aprovadas no visualizador de cenários.
    self.scenario_runtime.draw(self.screen, battle)
    # As quatro pistas já estão pintadas no próprio cenário. Nenhuma faixa
    # sintética é sobreposta à arte: pés, água, asfalto e areia coincidem.
    ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    if battle.global_toxic > 0:
        ambient.fill((92, 202, 86, int(30 + battle.global_toxic * 8)))
    self.screen.blit(ambient, (0, 0))
    self.draw_lane_bombs(battle)
    mouse = pygame.mouse.get_pos()
    hovered_cell = (
        (battle.keyboard_row, battle.keyboard_col)
        if self.control_mode == "keyboard"
        else battle.board_cell_at(mouse)
    )
    if hovered_cell and not battle.finished:
        row, col = hovered_cell
        outline = battle.ground_cell_rect(row, col)
        color = RED if battle.remove_mode else battle.region_color()
        pygame.draw.rect(self.screen, color, outline, 2, border_radius=12)
        if self.control_mode == "keyboard":
            pygame.draw.rect(
                self.screen, WHITE, outline.inflate(-6, -6), 1, border_radius=10
            )
        if battle.cell_is_water(row, col):
            pygame.draw.arc(
                self.screen,
                (110, 213, 250),
                outline.inflate(-22, -28),
                0,
                math.pi,
                2,
            )
    for defender in battle.defenders:
        self.draw_defender(defender)
    for enemy in battle.enemies:
        self.draw_enemy(enemy)
    self.draw_fallen(battle)
    if self.overlay_surface is not None:
        self.screen = self.overlay_surface
    self.draw_projectiles(battle)
    self.draw_visual_effects(battle)
    self.draw_particles(battle)
    self.draw_battle_top()
    self.draw_battle_status()
    if battle.finished:
        self.draw_result_overlay()

def draw_lane_guides(self, battle: Battle) -> None:
    """Compatibilidade: os limites agora pertencem à própria pintura."""
    return

def draw_lane_bombs(self, battle: Battle) -> None:
    """Mostra a contenção visual própria de cada terreno antes da invasão."""
    for cart in battle.lane_bombs:
        if cart.state == "spent":
            continue
        y = lane_bomb_ground_y(battle.region, cart.row)
        x = (
            cart.x
            if cart.state == "rolling"
            else lane_bomb_home_x(battle.region, cart.row)
        )
        is_water_buoy = battle.region == "beach" and cart.row in battle.water_rows
        depth = lane_depth(battle.region, cart.row)
        # As bombas de Minas ficam plantadas no contato e somem no mesmo
        # instante em que disparam a cadeia de explosões. Trator e drone
        # percorrem a faixa e desaparecem antes da entrada inimiga.
        if battle.region == "beach" and cart.state == "rolling":
            continue
        sprite, base_size = self.scenario_runtime.lane_defense_frame(
            battle.region,
            cart.row,
            moving=cart.state == "rolling",
            water=is_water_buoy,
        )
        width, height = base_size[0] * depth, base_size[1] * depth
        self.draw_actor_sprite(
            sprite, x, y, width, height, cart.motion, enemy=False
        )

def draw_battle_top(self) -> None:
    assert self.battle is not None
    battle = self.battle
    rects = battle.card_rects()
    for index, ((key, display), rect) in enumerate(zip(battle.selected, rects)):
        data = DEFENSES[key]
        active = index == battle.selected_card
        self.panel(rect, 238, GOLD if active else battle.region_color(), 7)
        if battle.card_cooldowns[index] > 0:
            dark = pygame.Surface(rect.size, pygame.SRCALPHA)
            dark.fill((0, 0, 0, 125))
            self.screen.blit(dark, rect)
            self.draw_text(
                f"{math.ceil(battle.card_cooldowns[index])}s",
                self.fonts.small,
                WHITE,
                rect.center,
                "center",
                True,
            )
        self.blit_sprite(
            self.card_sprite(battle.region, key, int(data["sprite"])),
            rect.x + 5,
            rect.y + 25,
            44,
            56,
        )
        self.draw_text(
            str(index + 1), self.fonts.tiny, GOLD, (rect.x + 7, rect.y + 6)
        )
        metric_a, metric_b = self.card_metrics(data)
        self.draw_text(
            f"{data['cost']} SUP", self.fonts.tiny, GOLD, (rect.x + 51, rect.y + 15)
        )
        self.draw_text(metric_a, self.fonts.tiny, WHITE, (rect.x + 51, rect.y + 35))
        self.draw_text(
            metric_b,
            self.fonts.tiny,
            TEAL if data["ammo"] or data["role"] in {"radio", "promoter"} else GRAY,
            (rect.x + 51, rect.y + 54),
        )
        if data.get("water_only"):
            self.draw_text(
                "ÁGUA",
                self.fonts.tiny,
                TEAL,
                (rect.centerx, rect.bottom - 15),
                "center",
            )
    self.panel(pygame.Rect(WIDTH - 176, 8, 166, 104), 230, battle.region_color(), 8)
    self.draw_text(
        f"{battle.supplies}/{int(battle.difficulty_data['supply_cap'])} SUP",
        self.fonts.h2,
        GOLD,
        (WIDTH - 93, 18),
        "center",
    )
    self.draw_text(
        f"ONDA {battle.wave}/{TOTAL_WAVES}",
        self.fonts.small,
        WHITE,
        (WIDTH - 93, 48),
        "center",
    )
    self.draw_text(
        f"{len(battle.enemies) + len(battle.orders)} INVASORES",
        self.fonts.tiny,
        GRAY,
        (WIDTH - 93, 78),
        "center",
    )

    # Comandos de missão em uma única aba, sempre acima do terreno.
    shelf = pygame.Rect(10, 118, WIDTH - 20, 50)
    self.panel(shelf, 221, battle.region_color(), 8)
    self.button("MENU", battle.menu_rect(), battle.region_color())
    self.button("PAUSA", battle.pause_rect(), GOLD)
    if battle.difficulty != "easy":
        self.button(
            "VOLTAR À BASE",
            battle.remove_rect(),
            (231, 133, 79) if battle.remove_mode else (47, 91, 105),
        )
    self.button(
        "PRÓXIMA",
        battle.next_wave_rect(),
        battle.region_color(),
        not battle.started_wave,
    )
    if battle.started_wave:
        tactical_status = (
            f"HORDA ATIVA • {len(battle.enemies) + len(battle.orders)} invasores"
        )
    else:
        tactical_status = (
            f"INTERVALO TÁTICO • {max(0, math.ceil(battle.intermission))} s"
        )
    ticker = battle.message if battle.message_timer > 0 else "Equipe em posição."
    if len(ticker) > 62:
        ticker = ticker[:59] + "..."
    self.draw_text(tactical_status, self.fonts.tiny, WHITE, (520, 127))
    self.draw_text(
        ticker,
        self.fonts.tiny,
        GOLD if battle.message_timer > 0 else GRAY,
        (520, 147),
    )
    control_hint = (
        "WASD • Q/E • ENTER • N • P"
        if self.control_mode == "keyboard"
        else "MOUSE • 1–8 • P"
    )
    self.draw_text(
        control_hint, self.fonts.tiny, GRAY, (WIDTH - 26, 136), "topright"
    )

    # Ficha completa apenas por hover: remove a redundância sem esconder a
    # informação tática para quem quer comparar as cartas.
    mouse = pygame.mouse.get_pos()
    hovered = next(
        (
            (key, display, rect)
            for (key, display), rect in zip(battle.selected, rects)
            if rect.collidepoint(mouse)
        ),
        None,
    )
    if hovered:
        key, display, rect = hovered
        data = DEFENSES[key]
        tooltip_x = int(clamp(rect.centerx - 170, 154, WIDTH - 350))
        tooltip = pygame.Rect(tooltip_x, 178, 340, 72)
        self.panel(tooltip, 239, battle.region_color(), 8)
        self.draw_text(
            display, self.fonts.small, GOLD, (tooltip.x + 13, tooltip.y + 9)
        )
        self.draw_wrapped(
            data["ability"],
            self.fonts.tiny,
            WHITE,
            pygame.Rect(tooltip.x + 13, tooltip.y + 29, tooltip.width - 26, 35),
            2,
        )

def defender_sprite(self, battle: Battle, defender: Defender) -> pygame.Surface:
    """Fonte visual da defesa ativa e da animação de derrota."""
    if defender.visual_animation is not None:
        return defender.visual_animation.frame
    return self.card_sprite(battle.region, defender.key, defender.sprite_index)

def enemy_sprite(self, battle: Battle, enemy: Enemy) -> pygame.Surface:
    """Fonte visual do inimigo, centralizando os retratos especiais."""
    if enemy.visual_animation is not None:
        return enemy.visual_animation.frame
    if enemy.is_boss:
        frames = self.assets.animation_frames.get(
            f"{battle.region}_boss_actions", []
        )
        if len(frames) >= 12:
            boss_row = REGIONS[battle.region]["bosses"].index(enemy.key)
            row_frames = frames[boss_row * 4 : boss_row * 4 + 4]
            if enemy.motion.state == "skill":
                return row_frames[3]
            if enemy.motion.state == "attack":
                return row_frames[2]
            if enemy.motion.state in {"hit", "stunned"}:
                return row_frames[1]
            return row_frames[enemy.motion.phase(fps=4.6, frames=2)]
    sheet_key = {
        ("city", "caminhante"): "city_walker_walk",
        ("desert", "digger"): "desert_digger_states",
        ("beach", "nadador"): "beach_swimmer_walk",
    }.get((battle.region, enemy.key))
    if sheet_key:
        frames = self.assets.animation_frames.get(sheet_key, [])
        if frames:
            if enemy.key == "digger" and enemy.motion.state == "walk":
                frame_index = enemy.motion.phase(fps=5.5, frames=2)
            elif enemy.key == "digger" and enemy.motion.state == "dig_enter":
                frame_index = min(4, 2 + int(enemy.motion.state_elapsed / 0.16))
            elif enemy.key == "digger" and enemy.motion.state == "dig_tunnel":
                frame_index = 4
            elif enemy.key == "digger" and enemy.motion.state == "dig_emerge":
                frame_index = 5
            elif enemy.key == "digger" and enemy.motion.state == "attack":
                frame_index = 6
            elif enemy.motion.state == "walk":
                frame_index = enemy.motion.phase(fps=10.0, frames=len(frames))
            elif enemy.motion.state == "attack":
                frame_index = 2
            elif enemy.motion.state in {"hit", "stunned"}:
                frame_index = 4
            else:
                frame_index = 0
            return frames[frame_index % len(frames)]
    if enemy.key == "saltador" and "zombie_jumper_beta3" in self.assets.images:
        return self.assets.images["zombie_jumper_beta3"]
    if (
        enemy.key == "rastejante"
        and battle.region == "city"
        and "zombie_crawler_beta3" in self.assets.images
    ):
        return self.assets.images["zombie_crawler_beta3"]
    return self.assets.zombie(battle.region, int(enemy.data["sprite"]))

def draw_actor_sprite(
    self,
    sprite: pygame.Surface,
    x: float,
    ground_y: float,
    width: float,
    height: float,
    motion: ActorMotion,
    *,
    enemy: bool,
    vertical_offset: float = 0.0,
    alpha: int = 255,
    progress: float = 0.0,
    state_override: str | None = None,
    profile: str = "generic",
    frame_animated: bool = False,
) -> pygame.Rect:
    """Desenha uma pose articulada preservando os pés no terreno real."""
    if sprite.get_width() <= 1:
        return pygame.Rect(int(x), int(ground_y), 1, 1)
    # Animações de produção já compartilham uma caixa e um pivô fixos. O
    # trim por quadro recentralizava cada pose e fazia corpo, mangueira e
    # efeitos saltarem alguns pixels. Artes estáticas antigas ainda usam o
    # recorte tradicional.
    if not frame_animated:
        sprite = self.assets.trimmed(sprite)
    action_progress = clamp(float(progress), 0.0, 1.0)
    if action_progress <= 0.0 and motion.event_left > 0:
        action_progress = clamp(
            motion.state_elapsed
            / max(0.001, motion.state_elapsed + motion.event_left),
            0.0,
            1.0,
        )
    if self.presenter is not None:
        self.actor_commands.append(
            ActorCommand(
                sprite=sprite,
                x=float(x),
                ground_y=float(ground_y),
                width=max(1.0, float(width)),
                height=max(1.0, float(height)),
                state=(
                    "sprite_sequence"
                    if frame_animated
                    else (state_override or motion.state)
                ),
                elapsed=motion.state_elapsed,
                enemy=enemy,
                vertical_offset=vertical_offset,
                alpha=max(0, min(255, int(alpha))),
                hit_flash=0.0 if frame_animated else motion.hit_flash,
                progress=action_progress,
                profile="sprite_sequence" if frame_animated else profile,
            )
        )
        return pygame.Rect(
            int(x - width / 2),
            int(ground_y + vertical_offset - height),
            max(1, int(width)),
            max(1, int(height)),
        )
    if frame_animated:
        dx, dy, angle, scale_x, scale_y = 0.0, 0.0, 0.0, 1.0, 1.0
    else:
        dx, dy, angle, scale_x, scale_y = actor_pose(
            motion,
            enemy=enemy,
            profile=profile,
            progress=action_progress,
        )
    size = (max(1, int(width * scale_x)), max(1, int(height * scale_y)))
    rendered = pygame.transform.rotate(self.assets.scaled(sprite, *size), angle)
    if alpha < 255:
        rendered.set_alpha(max(0, alpha))
    if motion.hit_flash > 0 and not frame_animated:
        flash_alpha = int(105 * clamp(motion.hit_flash / 0.13, 0.0, 1.0))
        flash = pygame.Surface(rendered.get_size(), pygame.SRCALPHA)
        flash.fill((255, 238, 210, flash_alpha))
        rendered.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    rect = rendered.get_rect(
        midbottom=(int(x + dx), int(ground_y + dy + vertical_offset))
    )
    self.screen.blit(rendered, rect)
    return rect

def draw_fallen(self, battle: Battle) -> None:
    """Mostra uma queda curta antes de a silhueta sumir em partículas."""
    for fallen in battle.fallen:
        progress = clamp(fallen.elapsed / max(0.01, fallen.duration), 0.0, 1.0)
        alpha = int(255 * (1.0 - progress))
        motion = ActorMotion(
            state="dead", state_elapsed=fallen.elapsed, event_left=fallen.duration
        )
        self.draw_actor_sprite(
            fallen.sprite,
            fallen.x,
            fallen.y,
            fallen.width,
            fallen.height,
            motion,
            enemy=fallen.enemy,
            alpha=alpha,
            progress=progress,
        )

def draw_linked_skill_effect(
    self,
    effect: VisualEffect,
    x: float,
    y: float,
    progress: float,
) -> bool:
    """Desenha sinais próprios que permanecem presos ao personagem.

    Estes gestos não reaproveitam fogo, água ou uma explosão genérica. A
    geometria é pequena e funcional: pulso, rede, cura, roubo ou parasita
    comunicam exatamente a regra executada pelo inimigo.
    """
    supported = {
        "command_aura",
        "signal_pulse",
        "heal_pulse",
        "heal_receive",
        "supply_snatch",
        "net_cast",
        "parasite_burst",
    }
    if effect.kind not in supported:
        return False
    size = max(84, round(180 * effect.scale))
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    center = pygame.Vector2(size / 2, size / 2)
    fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
    alpha = max(0, min(255, round(225 * fade)))
    color = (*effect.color, alpha)
    pale = tuple(min(255, channel + 70) for channel in effect.color) + (alpha,)
    radius = max(12, round((20 + progress * 46) * effect.scale))

    if effect.kind in {"command_aura", "signal_pulse", "heal_pulse"}:
        pygame.draw.circle(
            layer, color, center, radius, max(2, round(4 * effect.scale))
        )
        pygame.draw.circle(
            layer,
            pale,
            center,
            max(5, round(radius * 0.62)),
            max(1, round(2 * effect.scale)),
        )
    if effect.kind == "command_aura":
        for angle in (-0.72, 0.0, 0.72):
            end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
            pygame.draw.line(
                layer, pale, center, end, max(2, round(3 * effect.scale))
            )
    elif effect.kind == "signal_pulse":
        pygame.draw.line(
            layer,
            pale,
            center + (-5, 9),
            center + (0, -radius * 0.72),
            max(2, round(3 * effect.scale)),
        )
        for side in (-1, 1):
            arc = pygame.Rect(0, 0, radius * 1.18, radius * 1.18)
            arc.center = center + (side * radius * 0.26, -radius * 0.34)
            pygame.draw.arc(
                layer, pale, arc, -1.0, 1.0, max(2, round(2 * effect.scale))
            )
    elif effect.kind == "heal_pulse":
        arm = max(6, round(radius * 0.36))
        thickness = max(3, round(radius * 0.18))
        pygame.draw.rect(
            layer,
            pale,
            (center.x - thickness / 2, center.y - arm, thickness, arm * 2),
        )
        pygame.draw.rect(
            layer,
            pale,
            (center.x - arm, center.y - thickness / 2, arm * 2, thickness),
        )
        # Partículas orbitam o gesto de cura; a cruz deixa de ser a única
        # mudança entre os quadros.
        for index in range(6):
            angle = progress * math.tau * 1.5 + index * math.tau / 6
            orbit = radius * (0.58 + 0.10 * (index % 2))
            point = (
                center + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit
            )
            pygame.draw.circle(
                layer, pale, point, max(2, round(2.8 * effect.scale))
            )
    elif effect.kind == "heal_receive":
        # O aliado curado responde à habilidade: energia sobe do chão ao
        # tronco em tempos diferentes, sempre na mesma pista do emissor.
        for index in range(7):
            phase = (progress + index / 7.0) % 1.0
            px = center.x + math.sin(index * 2.1 + progress * 5.0) * radius * 0.46
            py = center.y + radius * 0.55 - phase * radius * 1.25
            pygame.draw.circle(
                layer,
                pale,
                (round(px), round(py)),
                max(2, round(3.0 * effect.scale)),
            )
        cross_y = center.y - radius * 0.15
        arm = max(4, round(radius * 0.22))
        thickness = max(2, round(radius * 0.10))
        pygame.draw.rect(
            layer,
            color,
            (center.x - thickness / 2, cross_y - arm, thickness, arm * 2),
        )
        pygame.draw.rect(
            layer,
            color,
            (center.x - arm, cross_y - thickness / 2, arm * 2, thickness),
        )
    elif effect.kind == "supply_snatch":
        for index in range(6):
            angle = index * math.tau / 6 + progress * 0.5
            start = (
                center + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius
            )
            end = (
                center
                + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * 0.30
            )
            pygame.draw.line(
                layer, color, start, end, max(2, round(3 * effect.scale))
            )
            pygame.draw.circle(layer, pale, end, max(2, round(4 * effect.scale)))
    elif effect.kind == "net_cast":
        net_radius = max(16, round(radius * 0.90))
        rect = pygame.Rect(0, 0, net_radius * 2, net_radius * 1.45)
        rect.center = center
        for step in range(-net_radius, net_radius + 1, max(7, net_radius // 4)):
            pygame.draw.line(
                layer,
                color,
                (rect.left, center.y + step * 0.55),
                (rect.right, center.y - step * 0.55),
                2,
            )
            pygame.draw.line(
                layer,
                color,
                (rect.left, center.y - step * 0.55),
                (rect.right, center.y + step * 0.55),
                2,
            )
        pygame.draw.ellipse(layer, pale, rect, 2)
    elif effect.kind == "parasite_burst":
        ground = center + (0, radius * 0.45)
        for index in range(7):
            angle = -2.85 + index * 0.42
            length = radius * (0.60 + (index % 2) * 0.24)
            tip = ground + pygame.Vector2(math.cos(angle), math.sin(angle)) * length
            pygame.draw.line(
                layer, color, ground, tip, max(2, round(4 * effect.scale))
            )
            pygame.draw.circle(layer, pale, tip, max(2, round(3 * effect.scale)))

    self.screen.blit(layer, layer.get_rect(center=(round(x), round(y))))
    return True

def draw_gas_cloud(
    self,
    x: float,
    y: float,
    progress: float,
    scale: float,
) -> None:
    """Nuvem baixa de gás anticorrosivo, com expansão e dissipação."""
    # A altura cabe dentro de uma única pista. Assim o recorte de faixa
    # protege as linhas vizinhas sem amputar a parte principal da nuvem.
    width = max(108, round(174 * scale))
    height = max(58, round(70 * scale))
    layer = pygame.Surface((width, height), pygame.SRCALPHA)
    center_x = width / 2
    ground_y = height * 0.78
    growth = 0.34 + 0.66 * (1.0 - (1.0 - progress) ** 2)
    fade = 1.0 - clamp((progress - 0.66) / 0.34, 0.0, 1.0)

    ring = pygame.Rect(0, 0, width * 0.72 * growth, height * 0.24 * growth)
    ring.center = (center_x, ground_y)
    pygame.draw.ellipse(
        layer,
        (146, 231, 77, round(185 * fade)),
        ring,
        max(1, round(2 * scale)),
    )

    for index in range(11):
        phase = index * 1.73
        horizontal = math.sin(phase) * width * (0.12 + 0.018 * index) * growth
        rise = (5 + (index % 4) * 5 + progress * (10 + index * 0.72)) * scale
        drift = math.sin(progress * 4.2 + phase) * 7 * scale
        blob_x = center_x + horizontal + drift
        blob_y = ground_y - rise
        radius_x = (12 + (index % 4) * 4) * scale * growth
        radius_y = (8 + ((index + 2) % 4) * 2.7) * scale * growth
        outer = pygame.Rect(0, 0, radius_x * 2.0, radius_y * 2.0)
        outer.center = (blob_x, blob_y)
        inner = outer.inflate(-radius_x * 0.62, -radius_y * 0.62)
        pygame.draw.ellipse(
            layer,
            (50, 112, 35, round((135 + index * 4) * fade)),
            outer,
        )
        pygame.draw.ellipse(
            layer,
            (146, 222, 70, round((145 + index * 5) * fade)),
            inner,
        )

    for index in range(7):
        q = (progress * 0.82 + index / 7.0) % 1.0
        speck_x = center_x + math.sin(index * 2.4) * width * 0.25 * growth
        speck_y = ground_y - (10 + q * 34) * scale
        pygame.draw.circle(
            layer,
            (190, 242, 112, round(170 * fade * (1.0 - q * 0.45))),
            (round(speck_x), round(speck_y)),
            max(1, round(2.1 * scale)),
        )
    self.screen.blit(
        layer,
        layer.get_rect(midbottom=(round(x), round(y + 18 * scale))),
    )

def draw_visual_effects(self, battle: Battle) -> None:
    """Exibe somente quadros rasterizados de matéria e impacto reais."""
    styles = {
        "flame_impact": ("elemental_effects", 0, 118, 92),
        "water_impact": ("elemental_effects", 1, 132, 88),
        "toxic_impact": ("elemental_effects", 2, 126, 96),
        "toxic_wave": ("elemental_effects", 2, 212, 136),
        "ground_slam": ("ability_effects", 0, 236, 126),
        "arcane_cast": ("ability_effects", 1, 164, 174),
        "tidal_surge": ("ability_effects", 2, 260, 142),
        "water_splash": ("ability_effects", 2, 138, 82),
        "electric_arc": ("combat_effects", 0, 78, 54),
        "explosion": ("combat_effects", 2, 184, 146),
        "ballistic_impact": ("combat_effects", 0, 92, 66),
    }
    for effect in battle.effects:
        progress = clamp(effect.elapsed / max(0.01, effect.duration), 0.0, 1.0)
        effect_x, effect_y = effect.x, effect.y
        if isinstance(effect.owner, Enemy):
            effect_x, effect_y = battle.enemy_effect_origin(
                effect.owner,
                effect.anchor_kind or effect.kind,
            )
        previous_clip = self.screen.get_clip()
        boss_can_cross = isinstance(effect.owner, Enemy) and effect.owner.is_boss
        if not boss_can_cross:
            if isinstance(effect.owner, (Enemy, Defender)):
                effect_row = effect.owner.row
            else:
                effect_row = min(
                    range(ROWS),
                    key=lambda row: abs(
                        terrain_y(battle.region, row, effect_x) - effect_y
                    ),
                )
            top, bottom = lane_bounds(battle.region, effect_row)
            self.screen.set_clip(
                pygame.Rect(0, int(top), WIDTH, max(1, math.ceil(bottom - top)))
            )
        if self.draw_linked_skill_effect(effect, effect_x, effect_y, progress):
            self.screen.set_clip(previous_clip)
            continue
        if effect.kind == "toxic_wave":
            self.draw_gas_cloud(effect_x, effect_y, progress, effect.scale)
            self.screen.set_clip(previous_clip)
            continue
        stage = min(3, int(progress * 4.0))
        sheet, row, base_width, base_height = styles.get(
            effect.kind,
            ("combat_effects", 2, 184, 146),
        )
        growth = 0.80 + progress * 0.36
        fade = 1.0 - clamp((progress - 0.72) / 0.28, 0.0, 1.0)
        self.blit_effect_frame(
            sheet,
            row,
            stage,
            effect_x,
            effect_y,
            base_width * effect.scale * growth,
            base_height * effect.scale * growth,
            alpha=int(255 * fade),
        )
        self.screen.set_clip(previous_clip)

def blit_effect_frame(
    self,
    sheet: str,
    row: int,
    stage: int,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    alpha: int = 255,
    angle: float = 0.0,
    midbottom: bool = False,
    flip_x: bool = False,
) -> pygame.Rect | None:
    """Desenha um quadro pré-pintado; jamais fabrica um símbolo geométrico."""
    frames = self.assets.effect_frames.get(sheet, [])
    index = row * 4 + max(0, min(3, int(stage)))
    if index >= len(frames) or frames[index].get_width() <= 1:
        return None
    rendered = self.assets.scaled(frames[index], width, height)
    if flip_x:
        rendered = pygame.transform.flip(rendered, True, False)
    if angle:
        rendered = pygame.transform.rotate(rendered, angle)
    elif alpha < 255:
        rendered = rendered.copy()
    if alpha < 255:
        rendered.set_alpha(max(0, min(255, int(alpha))))
    if midbottom:
        rect = rendered.get_rect(midbottom=(int(x), int(y)))
    else:
        rect = rendered.get_rect(center=(int(x), int(y)))
    self.screen.blit(rendered, rect)
    return rect

def blit_muzzle_cycle(
    self,
    stage: int,
    x: float,
    y: float,
    *,
    width: float,
    height: float,
) -> pygame.Rect | None:
    """Desenha somente a ignição e o clarão na boca da arma.

    A folha também possui fumaça e estojos em posições próprias, mas ao
    escalar a célula inteira esses elementos pareciam um segundo projétil
    embaixo do soldado. O recuo da sprite continua visível e a sequência
    usa apenas os três clarões centrados no cano.
    """
    frames = self.assets.animation_frames.get("muzzle_cycle", [])
    if not frames:
        return None
    flash_cycle = (0, 1, 2, 3, 2, 1, 0, 0)
    frame_index = flash_cycle[max(0, min(len(flash_cycle) - 1, int(stage)))]
    frame = frames[min(len(frames) - 1, frame_index)]
    if frame.get_width() <= 1 or frame.get_height() <= 1:
        return None
    rendered = self.assets.scaled(frame, width, height)
    rect = rendered.get_rect(midleft=(int(x), int(y)))
    self.screen.blit(rendered, rect)
    return rect

@staticmethod
def frame_has_muzzle_flash(
    sprite: pygame.Surface,
    defender: Defender,
) -> bool:
    """Evita duplicar um clarão que já foi pintado junto da arma."""
    layout = defender_visual_layout(defender)
    depth = lane_depth(defender.region, defender.row)
    muzzle_x, muzzle_y = defender_weapon_origin(defender)
    ratio = layout.source_height / max(1.0, layout.body_height)
    source_x = round(
        sprite.get_width() / 2
        + ((muzzle_x - defender.render_x) / max(0.01, depth)) * ratio
    )
    source_y = round(
        sprite.get_height() - ((defender.y - muzzle_y) / max(0.01, depth)) * ratio
    )
    area = pygame.Rect(source_x - 18, source_y - 12, 21, 25).clip(sprite.get_rect())
    if area.width <= 0 or area.height <= 0:
        return False
    for x in range(area.left, area.right):
        for y in range(area.top, area.bottom):
            red, green, blue, alpha = sprite.get_at((x, y))
            if (
                alpha > 24
                and red >= 190
                and green >= 82
                and blue <= 125
                and red >= blue + 70
            ):
                return True
    return False

@staticmethod
def eased(value: float) -> float:
    """Curva suave usada por mãos, carregadores e munição visível."""
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)

def draw_reload_action(
    self,
    defender: Defender,
    rect: pygame.Rect,
    scale: tuple[float, float],
    depth: float,
    progress: float,
) -> None:
    """Mostra a troca física de munição sem palavra, relógio ou ícone.

    A mão sai da arma, alcança o cinto, carrega um pente/cartucho/cilindro
    e o encaixa no equipamento. A barra de munição existente é o único
    indicador abstrato; todo o restante é movimento corporal.
    """
    # A Beta 4 executa esse gesto na malha corporal OpenGL. O antigo braço
    # de linhas e o carregador geométrico não devem voltar a ser exibidos.
    return
    role = str(defender.stats.get("role", ""))
    if role in {"radio", "promoter", "barrier", "mine"}:
        return
    p = clamp(progress, 0.0, 1.0)
    x, y = defender.x, defender.y
    shoulder = (x + 2 * depth, y - scale[1] * 0.61)
    receiver = (x + 22 * depth, y - scale[1] * 0.50)
    pocket = (x - 7 * depth, y - scale[1] * 0.29)

    if p < 0.22:
        q = self.eased(p / 0.22)
        hand = (lerp(receiver[0], pocket[0], q), lerp(receiver[1], pocket[1], q))
    elif p < 0.44:
        q = self.eased((p - 0.22) / 0.22)
        hand = (
            pocket[0] - 2 * depth,
            pocket[1] + math.sin(q * math.pi) * 3 * depth,
        )
    elif p < 0.78:
        q = self.eased((p - 0.44) / 0.34)
        hand = (lerp(pocket[0], receiver[0], q), lerp(pocket[1], receiver[1], q))
    else:
        q = self.eased((p - 0.78) / 0.22)
        rest = (x + 10 * depth, y - scale[1] * 0.52)
        hand = (lerp(receiver[0], rest[0], q), lerp(receiver[1], rest[1], q))

    elbow = (
        lerp(shoulder[0], hand[0], 0.52) - 4 * depth,
        lerp(shoulder[1], hand[1], 0.52) + 7 * depth,
    )
    sleeve = {
        "city": (46, 69, 67),
        "desert": (135, 105, 65),
        "beach": (32, 72, 92),
    }[defender.region]
    pygame.draw.line(self.screen, sleeve, shoulder, elbow, max(2, int(6 * depth)))
    pygame.draw.line(self.screen, sleeve, elbow, hand, max(2, int(5 * depth)))
    pygame.draw.circle(
        self.screen,
        (198, 152, 111),
        (int(hand[0]), int(hand[1])),
        max(2, int(4 * depth)),
    )

    # O objeto aparece apenas depois de ser retirado do cinto e desaparece
    # dentro da arma na fase de encaixe.
    if 0.30 <= p <= 0.84:
        alpha = int(255 * min(1.0, (p - 0.30) / 0.08, (0.84 - p) / 0.08))
        item = pygame.Surface(
            (max(8, int(15 * depth)), max(10, int(24 * depth))), pygame.SRCALPHA
        )
        if role == "shotgun":
            for offset in (3, 8):
                pygame.draw.rect(
                    item,
                    (172, 42, 38, alpha),
                    (offset, 2, 4, item.get_height() - 4),
                    border_radius=2,
                )
                pygame.draw.line(
                    item, (238, 187, 72, alpha), (offset, 2), (offset + 3, 2), 2
                )
        elif role in {"mortar", "grenade", "gas_grenade"}:
            pygame.draw.ellipse(
                item,
                (91, 104, 69, alpha),
                (2, 1, item.get_width() - 4, item.get_height() - 2),
            )
            pygame.draw.line(
                item,
                (231, 184, 78, alpha),
                (2, item.get_height() // 2),
                (item.get_width() - 2, item.get_height() // 2),
                2,
            )
        elif role in {"flame", "poison", "waterjet"}:
            canister = {
                "flame": (207, 93, 43, alpha),
                "poison": (91, 175, 74, alpha),
                "waterjet": (67, 177, 220, alpha),
            }[role]
            pygame.draw.rect(
                item,
                canister,
                (2, 2, item.get_width() - 4, item.get_height() - 4),
                border_radius=4,
            )
            pygame.draw.line(
                item, (225, 236, 228, alpha), (3, 6), (item.get_width() - 3, 6), 2
            )
        else:
            pygame.draw.rect(
                item,
                (48, 55, 55, alpha),
                (2, 1, item.get_width() - 4, item.get_height() - 2),
                border_radius=2,
            )
            pygame.draw.line(
                item, (151, 165, 160, alpha), (4, 5), (item.get_width() - 4, 5), 2
            )
        rotated = pygame.transform.rotate(item, -18 + p * 26)
        self.screen.blit(
            rotated,
            rotated.get_rect(
                center=(int(hand[0] + 3 * depth), int(hand[1] + 5 * depth))
            ),
        )

def draw_weapon_action(
    self,
    defender: Defender,
    rect: pygame.Rect,
    scale: tuple[float, float],
    depth: float,
) -> None:
    """Detalhe mecânico do disparo que não existe no retrato estático."""
    # O lançamento está no estado de ataque e o obus real aparece na folha
    # de projéteis. Não desenhar braços ou munição com primitivas.
    return
    if defender.stats.get("role") != "mortar":
        return
    total = max(0.001, defender.motion.state_elapsed + defender.motion.event_left)
    p = clamp(defender.motion.state_elapsed / total, 0.0, 1.0)
    q = self.eased(clamp(p / 0.72, 0.0, 1.0))
    start = (defender.x - 10 * depth, defender.y - scale[1] * 0.45)
    tube = (defender.x + 18 * depth, defender.y - scale[1] * 0.30)
    shell_x = lerp(start[0], tube[0], q)
    shell_y = lerp(start[1], tube[1], q) - math.sin(q * math.pi) * 13 * depth
    shoulder = (defender.x, defender.y - scale[1] * 0.60)
    hand = (shell_x - 2 * depth, shell_y)
    pygame.draw.line(
        self.screen, (87, 89, 69), shoulder, hand, max(2, int(5 * depth))
    )
    shell = pygame.Surface(
        (max(7, int(11 * depth)), max(12, int(23 * depth))), pygame.SRCALPHA
    )
    pygame.draw.ellipse(shell, (101, 116, 73, 255), shell.get_rect())
    pygame.draw.line(
        shell,
        GOLD,
        (2, shell.get_height() // 2),
        (shell.get_width() - 2, shell.get_height() // 2),
        2,
    )
    self.screen.blit(shell, shell.get_rect(center=(int(shell_x), int(shell_y))))

def draw_defender(self, defender: Defender) -> None:
    assert self.battle is not None
    battle = self.battle
    x, y = defender.render_x, defender.y
    role = defender.stats["role"]
    depth = lane_depth(battle.region, defender.row)
    sprite = self.defender_sprite(battle, defender)
    frame_animated = defender.visual_animation is not None
    if frame_animated:
        layout = defender_visual_layout(defender)
        scale = animated_actor_render_scale(
            sprite,
            depth,
            body_height=layout.body_height,
            source_body_height=layout.source_height,
        )
    else:
        scale = defender_render_scale(defender)
    shadow_width = max(
        28, int(scale[0] * (0.82 if role in {"barrier", "boat", "sub"} else 0.68))
    )
    shadow_height = max(6, int(13 * depth))
    shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
    if battle.cell_is_water(defender.row, defender.col):
        pygame.draw.ellipse(shadow, (90, 220, 235, 105), shadow.get_rect(), width=2)
        pygame.draw.ellipse(
            shadow, (7, 36, 52, 85), shadow.get_rect().inflate(-10, -4)
        )
    else:
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
    self.screen.blit(shadow, shadow.get_rect(midbottom=(int(x), int(y + 3))))
    # A mesma fonte de arte atende carta, campo e queda. A pose em si
    # muda conforme o estado emitido pela lógica de combate.
    reload_progress = (
        1.0 - defender.reload_timer / max(0.01, defender.reload_total)
        if defender.reloading
        else 0.0
    )
    rect = self.draw_actor_sprite(
        sprite,
        x,
        y,
        *scale,
        defender.motion,
        enemy=False,
        progress=reload_progress,
        profile=defender_animation_profile(defender),
        frame_animated=frame_animated,
    )
    world_target = self.screen
    if self.overlay_surface is not None:
        self.screen = self.overlay_surface
    if defender.motion.state == "attack":
        if frame_animated and defender.visual_animation is not None:
            attack_progress = defender.visual_animation.normalized_progress
        else:
            total = max(
                0.001, defender.motion.state_elapsed + defender.motion.event_left
            )
            attack_progress = clamp(defender.motion.state_elapsed / total, 0.0, 1.0)
        stage = min(7, int(attack_progress * 8.0))
        # O cano está à frente do peito, nunca no centro/perna do ator.
        # Água, fogo e veneno não ganham uma segunda figura colada na
        # arma. O fluxo real é desenhado pelo projétil contínuo, usando a
        # mesma origem física do cano durante toda a ação.
        # Se a folha já contém um clarão conectado, ele é preservado. Se
        # não contém, desenhamos um único clarão no mesmo ponto usado pelo
        # projétil. O tamanho vem da arma real da carta, nunca da SWAT como
        # molde universal; água e fogo não passam por esta camada.
        weapon_profile = DEFENDER_WEAPON_PROFILES.get(defender.key)
        if (
            weapon_profile is not None
            and weapon_profile.flash_size[0] > 0
            and not self.frame_has_muzzle_flash(sprite, defender)
        ):
            muzzle_x, muzzle_y = defender_weapon_origin(defender)
            flash_width, flash_height = weapon_profile.flash_size
            self.blit_muzzle_cycle(
                stage,
                muzzle_x,
                muzzle_y,
                width=flash_width * depth,
                height=flash_height * depth,
            )
    if defender.corrosion > 0:
        self.blit_effect_frame(
            "elemental_effects",
            2,
            int(defender.corrosion * 5.0) % 4,
            x,
            y - scale[1] * 0.38,
            scale[0] * 0.72,
            scale[1] * 0.62,
            alpha=168,
        )
    bar_width = max(32, int(44 * depth))
    self.health_bar(
        x - bar_width / 2,
        y + 5,
        bar_width,
        defender.hp / defender.max_hp,
        (89, 214, 144),
    )
    if defender.max_ammo:
        ammo_width = max(28, int(38 * depth))
        ammo_ratio = (
            1.0 - defender.reload_timer / max(0.01, defender.reload_total)
            if defender.reloading
            else defender.ammo / max(1, defender.max_ammo)
        )
        self.ammo_bar(x - ammo_width / 2, y + 11, ammo_width, ammo_ratio)
    self.screen = world_target

def draw_enemy(self, enemy: Enemy) -> None:
    assert self.battle is not None
    battle = self.battle
    water_enemy = battle.region == "beach" and enemy.row in battle.water_rows
    depth = lane_depth(battle.region, enemy.row)
    sprite = self.enemy_sprite(battle, enemy)
    frame_animated = enemy.visual_animation is not None
    render_x = enemy.x
    if frame_animated:
        animation = enemy.visual_animation
        assert animation is not None
        if animation.state == "bite":
            offsets = (
                (0, 1, 2, 4, 7, 6, 3, 0)
                if "runner" in enemy.tags
                else (0, 2, 7, 14, 23, 21, 11, 0)
            )
            render_x -= (
                offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            )
        elif animation.state == "hit":
            offsets = (0, 3, 7, 10, 8, 5, 2, 0)
            render_x += (
                offsets[min(animation.frame_index, len(offsets) - 1)] * depth
            )
        crawler = enemy.key in CRAWLER_ENEMIES
        if crawler:
            category = "crawler"
        elif enemy.is_boss:
            # O chefe é reconhecivelmente maior, mas não cresce a ponto de
            # invadir a pista vizinha ou ter cabeça/pés cortados.
            category = "boss"
        elif enemy.data.get("subboss"):
            category = "subboss"
        else:
            # Humanoides comuns compartilham a mesma altura corporal dos
            # soldados. A ameaça vem da animação e dos atributos, não de
            # um zumbi comum artificialmente gigante.
            category = "common"
        body_height, source_height = ENEMY_BODY_LAYOUTS[category]
        scale = animated_actor_render_scale(
            sprite,
            depth,
            body_height=body_height,
            source_body_height=source_height,
        )
    else:
        scale = enemy_render_scale(enemy, battle.region)
    shadow_width = max(28, int(scale[0] * (0.86 if enemy.is_boss else 0.68)))
    shadow_height = max(6, int(13 * depth))
    shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
    if water_enemy:
        pygame.draw.ellipse(shadow, (91, 221, 238, 112), shadow.get_rect(), width=2)
        pygame.draw.ellipse(
            shadow, (8, 37, 50, 88), shadow.get_rect().inflate(-10, -4)
        )
    else:
        pygame.draw.ellipse(shadow, (0, 0, 0, 115), shadow.get_rect())
    self.screen.blit(
        shadow, shadow.get_rect(midbottom=(int(render_x), int(enemy.y + 3)))
    )

    vertical_offset = 0.0
    alpha = 255
    top, bottom = lane_bounds(battle.region, enemy.row)
    lane_height = bottom - top
    if enemy.jump_state:
        progress = clamp(
            1.0 - enemy.jump_timer / max(0.01, enemy.jump_duration), 0.0, 1.0
        )
        vertical_offset = -math.sin(progress * math.pi) * lane_height * 0.78
    elif enemy.dig_state == "enter":
        progress = clamp(
            1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0
        )
        vertical_offset = lane_height * 0.42 * progress
        alpha = int(255 * (1.0 - progress * 0.42))
    elif enemy.dig_state == "emerge":
        progress = clamp(
            1.0 - enemy.dig_timer / max(0.01, enemy.dig_duration), 0.0, 1.0
        )
        vertical_offset = lane_height * 0.42 * (1.0 - progress)
        alpha = int(146 + 109 * progress)
    entry_reveal = float(getattr(enemy, "entry_reveal", 0.0))
    if entry_reveal > 0 and enemy.age < entry_reveal:
        reveal = clamp(enemy.age / entry_reveal, 0.0, 1.0)
        reveal = reveal * reveal * (3.0 - 2.0 * reveal)
        alpha = min(alpha, max(0, int(255 * reveal)))
    state_override = (
        "swim" if water_enemy and enemy.motion.state == "walk" else None
    )
    rect = self.draw_actor_sprite(
        sprite,
        render_x,
        enemy.y,
        *scale,
        enemy.motion,
        enemy=True,
        vertical_offset=vertical_offset,
        alpha=alpha,
        state_override=state_override,
        profile=enemy_animation_profile(enemy),
        frame_animated=frame_animated,
    )
    world_target = self.screen
    if self.overlay_surface is not None:
        self.screen = self.overlay_surface
    if enemy.burn > 0:
        self.blit_effect_frame(
            "elemental_effects",
            0,
            int(enemy.age * 11.0) % 4,
            render_x,
            enemy.y + 1,
            scale[0] * 0.94,
            scale[1] * 0.78,
            alpha=205,
            midbottom=True,
        )
    if enemy.poisoned > 0:
        self.blit_effect_frame(
            "elemental_effects",
            2,
            int(enemy.age * 8.0) % 4,
            render_x,
            enemy.y - scale[1] * 0.42,
            scale[0] * 1.04,
            scale[1] * 0.72,
            alpha=176,
        )
    if enemy.soaked > 0:
        self.blit_effect_frame(
            "elemental_effects",
            1,
            int(enemy.age * 9.0) % 4,
            render_x,
            enemy.y + 2,
            scale[0] * 1.15,
            scale[1] * 0.58,
            alpha=182,
            midbottom=True,
        )
    if enemy.corrosion > 0 and enemy.poisoned <= 0:
        self.blit_effect_frame(
            "elemental_effects",
            2,
            int(enemy.age * 7.0) % 4,
            render_x,
            enemy.y - scale[1] * 0.46,
            scale[0] * 0.76,
            scale[1] * 0.54,
            alpha=154,
        )
    # Roubo, cura e demais habilidades só exibem efeito durante o gesto
    # correspondente. Uma aura permanente aqui parecia veneno aleatório.
    width = (74 if enemy.is_boss else 44) * depth
    self.health_bar(
        render_x - width / 2, enemy.y + 5, width, enemy.hp / enemy.max_hp, RED
    )
    self.screen = world_target

@staticmethod
def flow_points(
    start: tuple[float, float],
    end: tuple[float, float],
    elapsed: float,
    amplitude: float,
    count: int = 18,
) -> list[tuple[int, int]]:
    """Constrói um jato contínuo ondulado entre bocal e frente do fluxo."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1.0, math.hypot(dx, dy))
    normal_x, normal_y = -dy / length, dx / length
    points: list[tuple[int, int]] = []
    for index in range(max(3, count)):
        q = index / max(1, count - 1)
        envelope = math.sin(q * math.pi)
        wave = math.sin(q * math.tau * 2.1 - elapsed * 31.0) * amplitude * envelope
        points.append(
            (
                int(lerp(start[0], end[0], q) + normal_x * wave),
                int(lerp(start[1], end[1], q) + normal_y * wave),
            )
        )
    return points

@staticmethod
def ribbon_polygon(
    points: list[tuple[int, int]],
    start_width: float,
    end_width: float,
    *,
    taper_tip: bool = False,
) -> list[tuple[int, int]]:
    """Cria as duas bordas de um fluxo para evitar o efeito de bolinhas."""
    if len(points) < 2:
        return points
    upper: list[tuple[int, int]] = []
    lower: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        before = points[max(0, index - 1)]
        after = points[min(len(points) - 1, index + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = max(1.0, math.hypot(dx, dy))
        normal_x, normal_y = -dy / length, dx / length
        q = index / max(1, len(points) - 1)
        width = lerp(start_width, end_width, q)
        if taper_tip:
            tip = clamp((q - 0.68) / 0.32, 0.0, 1.0)
            smooth_tip = tip * tip * (3.0 - 2.0 * tip)
            width *= lerp(1.0, 0.08, smooth_tip)
        upper.append(
            (int(point[0] + normal_x * width), int(point[1] + normal_y * width))
        )
        lower.append(
            (int(point[0] - normal_x * width), int(point[1] - normal_y * width))
        )
    return upper + list(reversed(lower))

@staticmethod
def water_ribbon_polygon(
    points: list[tuple[int, int]],
    start_width: float,
    end_width: float,
    elapsed: float,
    phase: float = 0.0,
) -> list[tuple[int, int]]:
    """Bordas irregulares de uma coluna de água sob pressão."""
    if len(points) < 2:
        return points
    upper: list[tuple[int, int]] = []
    lower: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        before = points[max(0, index - 1)]
        after = points[min(len(points) - 1, index + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = max(1.0, math.hypot(dx, dy))
        normal_x, normal_y = -dy / length, dx / length
        q = index / max(1, len(points) - 1)
        pressure_loss = q * q
        ripple = math.sin(q * math.tau * 3.2 - elapsed * 22.0 + phase)
        width = lerp(start_width, end_width, pressure_loss) * (1.0 + ripple * 0.12)
        upper.append(
            (int(point[0] + normal_x * width), int(point[1] + normal_y * width))
        )
        lower.append(
            (int(point[0] - normal_x * width), int(point[1] - normal_y * width))
        )
    return upper + list(reversed(lower))

def draw_pressurized_water(
    self,
    start: tuple[float, float],
    end: tuple[float, float],
    elapsed: float,
    depth: float,
    palette: tuple[tuple[int, int, int, int], ...],
) -> None:
    """Água sob pressão com massa, transparência e atomização na ponta."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    distance = max(1.0, math.hypot(dx, dy))
    direction = pygame.Vector2(dx / distance, dy / distance)
    normal = pygame.Vector2(-direction.y, direction.x)
    count = max(14, min(30, int(distance / 5.5)))
    points: list[pygame.Vector2] = []
    for index in range(count):
        q = index / max(1, count - 1)
        wave = (
            math.sin(q * math.pi * 1.35 - elapsed * 9.0) * 0.72
            + math.sin(q * math.pi * 4.7 + elapsed * 7.0) * 0.20
        ) * depth
        fall = q * q * 5.2 * depth
        base = pygame.Vector2(lerp(start[0], end[0], q), lerp(start[1], end[1], q))
        points.append(base + normal * wave + pygame.Vector2(0, fall))

    tuples = [(round(point.x), round(point.y)) for point in points]
    outer = self.water_ribbon_polygon(
        tuples,
        5.7 * depth,
        3.3 * depth,
        elapsed,
        phase=0.0,
    )
    body = self.water_ribbon_polygon(
        tuples,
        3.9 * depth,
        2.0 * depth,
        elapsed,
        phase=1.4,
    )
    core = self.water_ribbon_polygon(
        tuples[: max(4, round(len(tuples) * 0.82))],
        1.65 * depth,
        0.55 * depth,
        elapsed,
        phase=2.2,
    )
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    if len(outer) >= 3:
        pygame.draw.polygon(layer, (19, 91, 145, 192), outer)
        pygame.draw.aalines(layer, (78, 181, 224, 205), True, outer)
    if len(body) >= 3:
        pygame.draw.polygon(layer, (48, 158, 210, 220), body)
    if len(core) >= 3:
        pygame.draw.polygon(layer, (183, 232, 244, 225), core)

    # Reflexos curtos percorrem a água em velocidades diferentes. Eles
    # comunicam vazão sem transformar o jato numa linha branca contínua.
    for index in range(4):
        q0 = (elapsed * (1.65 + index * 0.11) + index * 0.23) % 0.72
        q1 = min(0.84, q0 + 0.09 + index * 0.012)
        p0 = points[min(len(points) - 1, round(q0 * (len(points) - 1)))]
        p1 = points[min(len(points) - 1, round(q1 * (len(points) - 1)))]
        pygame.draw.aaline(
            layer,
            (224, 249, 252, 210),
            (round(p0.x), round(p0.y - depth)),
            (round(p1.x), round(p1.y - depth)),
        )
    pygame.draw.ellipse(
        layer,
        (102, 205, 235, 235),
        pygame.Rect(0, 0, max(4, round(8 * depth)), max(3, round(6 * depth))).move(
            round(start[0] - 4 * depth), round(start[1] - 3 * depth)
        ),
    )

    # A ponta atomiza em gotas de tamanhos diferentes. Todas continuam na
    # direção do mesmo alvo e no mesmo relógio, sem camada desencontrada.
    for index in range(14):
        q = 0.70 + index * 0.021
        base_index = min(len(points) - 1, round(q * (len(points) - 1)))
        base = points[base_index]
        side = (
            math.sin(index * 2.31 + elapsed * 15.0) * (2.0 + index * 0.31) * depth
        )
        forward = (2.0 + (index % 5) * 2.4) * depth
        drop = (
            base
            + normal * side
            + direction * forward
            + pygame.Vector2(0, index * 0.34 * depth)
        )
        radius = max(1, round((2.2 - index * 0.075) * depth))
        pygame.draw.circle(
            layer,
            (212, 245, 250, 220) if index % 3 == 0 else (66, 174, 219, 205),
            (round(drop.x), round(drop.y)),
            radius,
        )
    self.screen.blit(layer, (0, 0))

def draw_combustion_flame(
    self,
    start: tuple[float, float],
    end: tuple[float, float],
    elapsed: float,
    travel: float,
    depth: float,
) -> None:
    """Chama cônica em ignição curta, abertura média e combustão plena.

    Cada quadro é redesenhado do zero. A fase anterior, portanto, some
    enquanto a próxima ocupa mais comprimento e volume. Isso evita tanto
    o acúmulo de quadros quanto o aspecto de uma fita líquida vermelha.
    """
    vector = pygame.Vector2(end[0] - start[0], end[1] - start[1])
    distance = vector.length()
    if distance < 2.0:
        return
    direction = vector.normalize()
    normal = pygame.Vector2(-direction.y, direction.x)
    phase = clamp(elapsed / max(0.01, travel), 0.0, 1.0)
    # Três poses materiais com transição suave: a anterior apaga enquanto
    # a seguinte assume o volume. Não há uma fita que cresce como água.
    stage = min(2, int(phase * 3.0))
    local = phase * 3.0 - stage
    stage_widths = (9.0, 20.0, 34.0)
    previous_width = stage_widths[max(0, stage - 1)]
    width = lerp(previous_width, stage_widths[stage], local) * depth
    flicker = math.sin(elapsed * 31.0) * 1.1 * depth
    tip = pygame.Vector2(end) + normal * flicker
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def flame_polygon(
        length_ratio: float, width_ratio: float, wobble: float
    ) -> list[pygame.Vector2]:
        """Pluma orgânica: volume contínuo com bordas vivas e assimétricas."""
        sample_count = 20
        upper: list[pygame.Vector2] = []
        lower: list[pygame.Vector2] = []
        for index in range(sample_count):
            q = index / (sample_count - 1)
            center = pygame.Vector2(start) + direction * distance * length_ratio * q
            envelope = math.sin(math.pi * q) ** 0.70
            # A pluma abre mais na metade final e fecha numa ponta fina.
            envelope *= 0.62 + 0.48 * q
            upper_noise = (
                math.sin(index * 1.73 + elapsed * 24.0) * wobble
                + math.sin(index * 0.61 - elapsed * 17.0) * wobble * 0.55
            )
            lower_noise = (
                math.sin(index * 1.29 - elapsed * 21.0 + 1.4) * wobble
                + math.sin(index * 0.47 + elapsed * 13.0) * wobble * 0.48
            )
            upper_half = width * width_ratio * envelope * (1.0 + upper_noise)
            lower_half = width * width_ratio * envelope * (0.82 + lower_noise)
            upper.append(center - normal * max(0.0, upper_half))
            lower.append(center + normal * max(0.0, lower_half))
        return upper + list(reversed(lower))

    outer = flame_polygon(1.0, 1.0, 0.12)
    middle = flame_polygon(0.90, 0.67, 0.10)
    hot = flame_polygon(0.64, 0.34, 0.07)
    pygame.draw.polygon(layer, (177, 43, 12, 188), outer)
    pygame.draw.aalines(layer, (233, 71, 15, 218), True, outer)
    pygame.draw.polygon(layer, (244, 89, 13, 232), middle)
    pygame.draw.polygon(layer, (255, 178, 36, 246), hot)

    # Línguas independentes quebram a borda do cone e dão combustão, não
    # líquido tingido. A ponta de cada língua pulsa, mas nunca volta.
    for index in range(6):
        q0 = 0.08 + index * 0.13
        q1 = min(0.94, q0 + 0.24 + (index % 3) * 0.09)
        center = pygame.Vector2(start) + direction * distance * q0
        tongue_tip = pygame.Vector2(start) + direction * distance * q1
        side = math.sin(elapsed * (21.0 + index) + index * 1.8) * width * 0.42
        tongue_tip += normal * side
        half = max(1.8, width * max(0.10, 0.27 - index * 0.025))
        color = (255, 190, 43, 240) if index < 4 else (244, 92, 20, 230)
        pygame.draw.polygon(
            layer,
            color,
            [center - normal * half, tongue_tip, center + normal * half],
        )

    inner_tip = pygame.Vector2(start) + direction * distance * (0.32 + 0.07 * local)
    inner_half = max(1.8, width * 0.22)
    pygame.draw.polygon(
        layer,
        (255, 221, 92, 248),
        [
            pygame.Vector2(start) - normal * 1.5,
            inner_tip,
            pygame.Vector2(start) + normal * 1.5,
            pygame.Vector2(start)
            + direction * distance * 0.22
            + normal * inner_half,
        ],
    )
    hot_tip = pygame.Vector2(start) + direction * distance * 0.30
    pygame.draw.line(
        layer,
        (255, 247, 198, 248),
        start,
        (round(hot_tip.x), round(hot_tip.y)),
        max(2, round(3.2 * depth)),
    )

    if stage == 2:
        for index in range(7):
            ember = tip - direction * (5 + index * 7) * depth
            ember += (
                normal
                * math.sin(elapsed * 17.0 + index * 2.0)
                * (4 + index * 0.7)
                * depth
            )
            pygame.draw.circle(
                layer,
                (255, 131, 35, 170),
                (round(ember.x), round(ember.y - index * 0.7 * depth)),
                max(1, round(1.5 * depth)),
            )
        # Fumaça somente na combustão plena, deslocada para cima e já
        # perdendo opacidade; ela não nasce no bocal nem cobre o soldado.
        for index in range(3):
            smoke = tip - direction * (3 + index * 10) * depth
            smoke += normal * math.sin(elapsed * 8.0 + index) * 4.0 * depth
            smoke.y -= (5 + index * 3) * depth
            pygame.draw.circle(
                layer,
                (54, 47, 42, 72 - index * 14),
                (round(smoke.x), round(smoke.y)),
                max(2, round((4.5 - index * 0.6) * depth)),
            )
    self.screen.blit(layer, (0, 0))

def draw_elemental_stream(self, projectile: Projectile, x: float, y: float) -> None:
    """Desenha um fluxo contínuo preso ao emissor, sem sprite duplicada.

    A origem é recalculada no equipamento a cada quadro. Duas fitas
    suaves formam matéria e brilho; assim o jato cresce do bocal até o
    alvo sem virar uma mancha separada na frente do personagem.
    """
    if isinstance(projectile.owner, Defender):
        start_x, start_y = defender_weapon_origin(projectile.owner)
    elif isinstance(projectile.owner, Enemy):
        start_x, start_y = Battle.enemy_projectile_origin(
            projectile.owner,
            "acid" if projectile.kind == "poison" else "torpedo",
        )
    else:
        start_x, start_y = float(projectile.x), float(projectile.y)
    dx, dy = float(x) - start_x, float(y) - start_y
    distance = math.hypot(dx, dy)
    if distance < 3.0:
        return
    source_row = int(getattr(projectile.owner, "row", 0))
    depth = lane_depth(self.battle.region if self.battle else "city", source_row)
    palette = {
        "flame": ((125, 43, 24, 225), (239, 91, 31, 245), (255, 213, 72, 255)),
        "waterjet": ((24, 91, 142, 218), (57, 157, 202, 242), (178, 224, 234, 238)),
        "poison": ((38, 89, 42, 225), (83, 174, 50, 245), (180, 226, 81, 255)),
    }[projectile.kind]
    is_water = projectile.kind == "waterjet"
    if is_water:
        self.draw_pressurized_water(
            (start_x, start_y),
            (x, y),
            projectile.elapsed,
            depth,
            palette,
        )
        return
    if projectile.kind == "flame":
        self.draw_combustion_flame(
            (start_x, start_y),
            (x, y),
            projectile.elapsed,
            projectile.travel,
            depth,
        )
        return
    points = self.flow_points(
        (start_x, start_y),
        (x, y),
        projectile.elapsed,
        # Alta pressão oscila pouco. O desenho anterior ondulava como um
        # cabo elétrico e deixava três linhas separadas em vez de água.
        amplitude={"flame": 3.0, "poison": 3.5}[projectile.kind] * depth,
        count=max(9, min(24, int(distance / 7))),
    )
    outer = self.ribbon_polygon(points, 8.0 * depth, 5.0 * depth, taper_tip=True)
    middle = self.ribbon_polygon(points, 5.2 * depth, 2.8 * depth, taper_tip=True)
    core = self.ribbon_polygon(points, 2.1 * depth, 0.8 * depth, taper_tip=True)
    if len(outer) >= 3:
        pygame.draw.polygon(self.screen, palette[0], outer)
        pygame.draw.polygon(self.screen, palette[1], middle)
        pygame.draw.polygon(self.screen, palette[2], core)
    # Uma única gota/faísca de contato acompanha a ponta; não há clarão
    # adicional no bocal nem segunda animação concorrendo com o corpo.
    tip_radius = max(2, round(3.0 * depth))
    pygame.draw.circle(self.screen, palette[2], (round(x), round(y)), tip_radius)

def draw_gas_grenade_projectile(
    self,
    x: float,
    y: float,
    angle: float,
    depth: float,
    progress: float,
    previous: tuple[float, float],
) -> None:
    """Cápsula química legível, pequena e distinta de uma bala comum."""
    width = max(12, round(15 * depth))
    height = max(8, round(9 * depth))
    capsule = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    body = pygame.Rect(4, 4, width, height)
    pygame.draw.ellipse(capsule, (31, 42, 31, 235), body)
    pygame.draw.ellipse(capsule, (112, 131, 72, 255), body, max(1, round(depth)))
    band = pygame.Rect(
        body.centerx - max(1, round(2 * depth)),
        body.y + 1,
        max(2, round(4 * depth)),
        body.height - 2,
    )
    pygame.draw.rect(
        capsule,
        (148, 221, 78, 255),
        band,
        border_radius=max(1, round(depth)),
    )
    pygame.draw.circle(
        capsule,
        (213, 245, 139, 245),
        (body.right - max(2, round(3 * depth)), body.centery),
        max(1, round(1.4 * depth)),
    )
    rotated = pygame.transform.rotate(capsule, angle + progress * 720.0)

    # Uma esteira curta ajuda a leitura do arco, mas termina antes da
    # cápsula e jamais nasce como um segundo projétil.
    trail_alpha = round(135 * (1.0 - clamp((progress - 0.62) / 0.38, 0.0, 1.0)))
    trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.aaline(
        trail,
        (155, 215, 108, trail_alpha),
        previous,
        (lerp(previous[0], x, 0.58), lerp(previous[1], y, 0.58)),
    )
    self.screen.blit(trail, (0, 0))
    self.screen.blit(rotated, rotated.get_rect(center=(round(x), round(y))))

def draw_projectiles(self, battle: Battle) -> None:
    arcing_kinds = {
        "grenade",
        "grenade_40mm",
        "gas_grenade",
        "mortar",
        "mortar_shell",
        "bazooka",
        "rpg7_rocket",
    }
    for projectile in battle.projectiles:
        if projectile.elapsed < 0:
            continue
        t = clamp(projectile.elapsed / projectile.travel, 0, 1)
        x = lerp(projectile.x, projectile.target_x, t)
        y = lerp(projectile.y, projectile.target_y, t) - (
            math.sin(t * math.pi) * 46 if projectile.kind in arcing_kinds else 0
        )
        if projectile.kind in {"flame", "poison", "waterjet"}:
            self.draw_elemental_stream(projectile, x, y)
            continue
        art = PROJECTILE_LAYOUTS.get(projectile.kind)
        if not art:
            continue
        row, column, width, height = art
        next_t = min(1.0, t + 0.025)
        next_x = lerp(projectile.x, projectile.target_x, next_t)
        next_y = lerp(projectile.y, projectile.target_y, next_t) - (
            math.sin(next_t * math.pi) * 46
            if projectile.kind in arcing_kinds
            else 0
        )
        angle = -math.degrees(math.atan2(next_y - y, next_x - x))
        source_row = int(getattr(projectile.owner, "row", 0))
        depth = lane_depth(battle.region, source_row)
        if projectile.kind == "gas_grenade":
            previous_t = max(0.0, t - 0.045)
            previous_x = lerp(projectile.x, projectile.target_x, previous_t)
            previous_y = lerp(projectile.y, projectile.target_y, previous_t) - (
                math.sin(previous_t * math.pi) * 46
            )
            self.draw_gas_grenade_projectile(
                x,
                y,
                angle,
                depth,
                t,
                (previous_x, previous_y),
            )
            continue
        self.blit_effect_frame(
            "projectile_sprites",
            row,
            column,
            x,
            y,
            width * depth,
            height * depth,
            alpha=176 if projectile.kind == "tracer" else 255,
            angle=angle,
        )

def draw_particles(self, battle: Battle) -> None:
    # Partículas circulares foram retiradas. Impactos e matéria usam folhas
    # rasterizadas; textos de dano continuam sendo informação de HUD.
    for text in battle.texts:
        self.draw_text(
            text.text, self.fonts.tiny, text.color, (text.x, text.y), "center", True
        )

def draw_battle_status(self) -> None:
    assert self.battle is not None
    battle = self.battle
    if battle.boss_warning > 0:
        banner = pygame.Rect(WIDTH // 2 - 330, 238, 660, 124)
        self.panel(banner, 244, RED, 12)
        self.draw_text(
            "ALERTA: CHEFE CHEGANDO",
            self.fonts.h1,
            RED,
            (banner.centerx, banner.y + 16),
            "center",
            True,
        )
        self.draw_text(
            battle.boss_banner_name,
            self.fonts.h2,
            WHITE,
            (banner.centerx, banner.y + 54),
            "center",
            True,
        )
        self.draw_text(
            battle.boss_banner_subtitle,
            self.fonts.small,
            GOLD,
            (banner.centerx, banner.y + 85),
            "center",
        )
    if battle.paused:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 132))
        self.screen.blit(veil, (0, 0))
        pause_card = pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 74, 410, 148)
        self.panel(pause_card, 246, GOLD, 12)
        self.draw_text(
            "PAUSADO",
            self.fonts.title,
            GOLD,
            (pause_card.centerx, pause_card.y + 23),
            "center",
            True,
        )
        self.draw_text(
            "Clique em PAUSA ou pressione P para continuar.",
            self.fonts.small,
            WHITE,
            (pause_card.centerx, pause_card.y + 86),
            "center",
        )

def draw_result_overlay(self) -> None:
    assert self.battle is not None
    battle = self.battle
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((3, 6, 9, 188))
    self.screen.blit(overlay, (0, 0))
    heading = "REGIÃO PROTEGIDA" if battle.victory else "BASE INVADIDA"
    color = GOLD if battle.victory else RED
    self.panel(
        pygame.Rect(WIDTH // 2 - 265, HEIGHT // 2 - 130, 530, 285), 242, color, 16
    )
    self.draw_text(
        heading,
        self.fonts.title,
        color,
        (WIDTH / 2, HEIGHT / 2 - 85),
        "center",
        True,
    )
    body = (
        "Você venceu as 12 ondas e os três chefes da região. Todos os territórios continuam disponíveis."
        if battle.victory
        else "Um infectado atravessou a linha final. Refaça a equipe e preserve munição para as ondas finais."
    )
    self.draw_wrapped(
        body,
        self.fonts.body,
        WHITE,
        pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 30, 410, 55),
        3,
        center=True,
    )
    self.draw_text(
        f"Onda alcançada: {battle.wave}/{TOTAL_WAVES}",
        self.fonts.small,
        GRAY,
        (WIDTH / 2, HEIGHT // 2 + 46),
        "center",
    )
    self.button(
        "VOLTAR AO MAPA",
        pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50),
        color,
    )

def health_bar(
    self,
    x: float,
    y: float,
    width: float,
    ratio: float,
    color: tuple[int, int, int],
) -> None:
    rect = pygame.Rect(int(x), int(y), int(width), 4)
    pygame.draw.rect(self.screen, (18, 21, 23), rect, border_radius=2)
    fill_width = int(rect.width * clamp(ratio, 0, 1))
    if fill_width > 0:
        pygame.draw.rect(
            self.screen,
            color,
            (rect.x, rect.y, fill_width, rect.height),
            border_radius=2,
        )

def ammo_bar(self, x: float, y: float, width: float, ratio: float) -> None:
    rect = pygame.Rect(int(x), int(y), int(width), 3)
    pygame.draw.rect(self.screen, (19, 28, 33), rect, border_radius=2)
    pygame.draw.rect(
        self.screen,
        TEAL,
        (rect.x, rect.y, int(rect.width * clamp(ratio, 0, 1)), rect.height),
        border_radius=2,
    )

def blit_sprite(
    self, sprite: pygame.Surface, x: float, y: float, width: float, height: float
) -> None:
    if sprite.get_width() <= 1:
        return
    scaled = self.assets.scaled(sprite, width, height)
    self.screen.blit(scaled, (int(x), int(y)))

def blit_actor_in_rect(
    self,
    sprite: pygame.Surface,
    rect: pygame.Rect,
    body_height: int,
    *,
    source_body_height: float = 130.0,
    outline: tuple[int, int, int] | None = None,
) -> pygame.Rect:
    """Enquadra um ator sem deformar corpo, arma ou chapéu."""
    content = sprite.get_bounding_rect(min_alpha=8)
    if content.width <= 0 or content.height <= 0:
        return pygame.Rect(rect.centerx, rect.bottom, 1, 1)
    sprite = sprite.subsurface(content).copy()
    # Retrato é uma moldura de inspeção, não o campo de batalha. Ajustar
    # pelo próprio conteúdo garante corpo inteiro e ocupa a área útil sem
    # herdar escalas físicas diferentes de soldado, rastejador e chefe.
    max_width = rect.width - 18
    max_height = rect.height - 18
    limiter = min(max_width / content.width, max_height / content.height)
    rendered = pygame.transform.smoothscale(
        sprite,
        (
            max(1, round(content.width * limiter)),
            max(1, round(content.height * limiter)),
        ),
    )
    target = rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 4))
    if outline is not None:
        mask = pygame.mask.from_surface(rendered, threshold=8)
        silhouette = mask.to_surface(
            setcolor=(*outline, 205),
            unsetcolor=(0, 0, 0, 0),
        ).convert_alpha()
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            self.screen.blit(silhouette, target.move(dx, dy))
    self.screen.blit(rendered, target)
    return target

def draw_portrait_backdrop(
    self, rect: pygame.Rect, accent: tuple[int, int, int]
) -> None:
    """Contraste neutro para uniformes pretos sem fingir transparência."""
    pygame.draw.rect(self.screen, (24, 35, 43), rect, border_radius=12)
    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(
        glow,
        (*accent, 38),
        (
            rect.width // 10,
            rect.height // 8,
            rect.width * 4 // 5,
            rect.height * 3 // 4,
        ),
    )
    self.screen.blit(glow, rect.topleft)
    pygame.draw.rect(self.screen, (*accent,), rect, width=1, border_radius=12)

def card_sprite(self, region: str, key: str, index: int) -> pygame.Surface:
    """Escolhe a silhueta da carta e do objeto já posicionado.

    Minas recebem sprites individuais onde a leitura do cenário importa:
    cidade usa duas cargas urbanas limpas, Praia usa duas minas de areia e
    a Bomba de Água é uma mina naval independente, sem plataforma.
    """
    actor_key = DEFENDER_ACTOR_BY_KEY.get(key)
    if actor_key and self.assets.production_clips is None:
        self.assets.prepare_production_animations()
    if actor_key and self.assets.production_clips:
        return self.assets.production_clips[actor_key]["idle"].frames[1]
    custom_asset = CARD_ART_ASSETS.get((region, key))
    if custom_asset:
        return self.assets.images[custom_asset]
    terrain_mine_assets = {
        "city": {"mina": "city_mine_n1", "mina_segura": "city_mine_n2"},
        "beach": {
            "mina": "beach_mine_land_n1",
            "mina_segura": "beach_mine_land_n2",
        },
    }
    if key == "atirador_lancha":
        return self.assets.images["beach_boat_shooter"]
    asset_key = terrain_mine_assets.get(region, {}).get(key)
    if asset_key:
        return self.assets.images[asset_key]
    if key == "bomba_agua":
        return self.assets.images["beach_mine_water"]
    if DEFENSES.get(key, {}).get("water_only"):
        water_index = {"lancha": 5, "submarino": 6}[key]
        return self.assets.base_unit("beach", water_index)
    level = int(DEFENSES.get(key, {}).get("level", 1))
    return self.assets.unit(region, regional_sprite_index(region, key), level)

@staticmethod
def card_metrics(data: dict) -> tuple[str, str]:
    """Converte a função em dois números úteis para a face da carta.

    A descrição continua no hover/dossiê. Aqui entram apenas estatísticas
    que o jogador usa para decidir rápido entre custo, alcance, munição,
    cura, recarga e contenção.
    """
    role = str(data["role"])
    level = int(data["level"])
    if role == "radio":
        gain = int(data.get("supply_gain", 14 if level == 1 else 28))
        return f"SUP +{gain}", f"CICLO {float(data['cooldown']):.1f}s"
    if role == "sonar":
        return "REVELA CANAL", f"PULSO {float(data['cooldown']):.1f}s"
    if role in {"shield", "blade"}:
        return (
            f"DANO {int(data['damage'])}",
            f"SEM MUNIÇÃO • ALC {int(data['range'])}",
        )
    if role == "waterjet":
        return (
            f"DANO {int(data['damage'])}",
            f"LENTO 32% • ALC {int(data['range'])}",
        )
    if role == "poison":
        return (
            f"DANO {int(data['damage'])}",
            f"VENENO 4.2s • ALC {int(data['range'])}",
        )
    if role == "gas_grenade":
        return (
            f"DANO {int(data['damage'])}",
            f"GÁS EM ÁREA • ALC {int(data['range'])}",
        )
    if role == "promoter":
        return "PROMOVE N1→N2", f"CICLO {int(data['cooldown'])}s"
    if role == "barrier":
        return f"HP {int(data['hp'])}", "EXPLODE" if level >= 2 else "BLOQUEIO"
    if role == "mine":
        area = (
            "ÁREA"
            if data.get("water_only")
            else ("SEGURA" if level >= 2 else "1 ALVO")
        )
        return f"DANO {int(data['damage'])}", area
    if role == "suicide_bomber":
        return f"DANO {int(data['damage'])}", "CONTATO • IMÓVEL"
    reload_time = weapon_reload_seconds(data)
    reload_label = f" • REC {reload_time:.1f}s" if reload_time else ""
    return f"DANO {int(data['damage'])}", f"MUN {int(data['ammo'])}{reload_label}"

def draw_wrapped(
    self,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    lines: int,
    center: bool = False,
) -> None:
    words = text.split()
    built: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if font.size(candidate)[0] <= rect.width:
            current = candidate
        else:
            built.append(current)
            current = word
    if current:
        built.append(current)
    for index, line in enumerate(built[:lines]):
        y = rect.y + index * (font.get_height() + 2)
        anchor = "midtop" if center else "topleft"
        x = rect.centerx if center else rect.x
        self.draw_text(line, font, color, (x, y), anchor)

def draw(self) -> None:
    # Atores OpenGL ficam entre o mundo e o HUD. A cada quadro as duas
    # superfícies são reconstruídas; nenhuma animação deixa rastros.
    self.screen = self.world_surface
    self.world_surface.fill((0, 0, 0, 255))
    self.actor_commands.clear()
    if self.overlay_surface is not None:
        self.overlay_surface.fill((0, 0, 0, 0))
    if self.scene == "loading":
        self.draw_loading()
    elif self.scene == "title":
        self.draw_title()
    elif self.scene == "difficulty":
        self.draw_difficulty()
    elif self.scene == "campaign":
        self.draw_campaign()
    elif self.scene == "characters":
        self.draw_characters()
    elif self.scene == "story":
        self.draw_story()
    elif self.scene == "settings":
        self.draw_settings()
    elif self.scene == "howto":
        self.draw_howto()
    elif self.scene.startswith("dossier"):
        self.draw_dossier()
    elif self.scene == "battle" and self.battle:
        self.draw_battle()

PRESENTATION_METHODS = ["button_rect","draw_text","panel","button","draw_loading","draw_title","draw_difficulty","draw_campaign","draw_selection","draw_selection_inspection","draw_characters","draw_comic_bubble","draw_comic_actor","draw_story","draw_settings","draw_howto","draw_unit_evolution_dossier","draw_dossier","draw_battle","draw_lane_guides","draw_lane_bombs","draw_battle_top","defender_sprite","enemy_sprite","draw_actor_sprite","draw_fallen","draw_linked_skill_effect","draw_gas_cloud","draw_visual_effects","blit_effect_frame","blit_muzzle_cycle","frame_has_muzzle_flash","eased","draw_reload_action","draw_weapon_action","draw_defender","draw_enemy","flow_points","ribbon_polygon","water_ribbon_polygon","draw_pressurized_water","draw_combustion_flame","draw_elemental_stream","draw_gas_grenade_projectile","draw_projectiles","draw_particles","draw_battle_status","draw_result_overlay","health_bar","ammo_bar","blit_sprite","blit_actor_in_rect","draw_portrait_backdrop","card_sprite","card_metrics","draw_wrapped","draw"]

def attach_presentation_methods(game_class: type) -> None:
    """Instala os métodos de apresentação na classe Game já criada."""
    for method_name in PRESENTATION_METHODS:
        setattr(game_class, method_name, globals()[method_name])
