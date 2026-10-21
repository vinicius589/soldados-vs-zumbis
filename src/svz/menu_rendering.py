"""Telas de menu e personagens, separadas da pintura da batalha."""
from __future__ import annotations

import math
import pygame

from .actor_visuals import animated_actor_render_scale
from .config import (
    GOLD,
    GRAY,
    HEIGHT,
    INK,
    RED,
    TEAL,
    TOTAL_WAVES,
    VERSION,
    WHITE,
    WIDTH,
)
from .content import (
    BASIC_DEFENDER_BY_REGION,
    BASIC_ENEMY_BY_REGION,
    BOSSES,
    CRAWLER_ENEMIES,
    DEFENDER_ACTOR_BY_KEY,
    DEFENSES,
    ENEMIES,
    ENEMY_ACTOR_BY_KEY,
    REGIONS,
    REGION_BOSSES,
    difficulty_profile,
    weapon_reload_seconds,
)
from .math_utils import clamp
from .scoring import SHOP_ITEMS
from .ui_panels import howto_panel, settings_panel


class MenuRenderingMixin:
    def draw_loading(self) -> None:
        loading_art = self.owner.assets.images.get("loading_beta3")
        if loading_art is not None:
            self.owner.screen.blit(loading_art, (0, 0))
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((3, 8, 12, 54))
            self.owner.screen.blit(veil, (0, 0))
        else:
            self.owner.screen.fill((8, 13, 18))
        asset_progress = self.owner.assets.loaded / max(1, self.owner.assets.total)
        if self.owner.presenter is not None:
            gpu_total = len(self.owner.gpu_preload_queue)
            gpu_progress = (self.owner.gpu_preloaded / gpu_total) if gpu_total else (1.0 if self.owner.assets.complete else 0.0)
            progress = asset_progress * 0.74 + gpu_progress * 0.26
        else:
            progress = asset_progress
        # A arte entregue pelo usuário já contém o título. O painel discreto
        # abaixo não a redesenha nem esconde o logotipo central.
        panel = pygame.Rect(WIDTH // 2 - 282, HEIGHT - 150, 564, 108)
        self.panel(panel, 204, (166, 130, 62), 12)
        self.draw_text(f"{VERSION} — CARREGANDO", self.owner.fonts.h2, WHITE, (panel.centerx, panel.y + 17), "center", True)
        bar = pygame.Rect(panel.x + 42, panel.y + 51, panel.width - 84, 18)
        pygame.draw.rect(self.owner.screen, (31, 42, 47), bar, border_radius=9)
        pygame.draw.rect(self.owner.screen, TEAL, (bar.x, bar.y, int(bar.width * progress), bar.height), border_radius=9)
        if self.owner.presenter is not None and self.owner.assets.complete:
            status = f"Enviando atores para a GPU  {self.owner.gpu_preloaded}/{len(self.owner.gpu_preload_queue)}"
        else:
            status = f"Preparando artes e animações  {self.owner.assets.loaded}/{self.owner.assets.total}"
        self.draw_text(status, self.owner.fonts.small, WHITE, (panel.centerx, panel.y + 79), "center")
        if self.owner.assets.error:
            self.draw_text(self.owner.assets.error, self.owner.fonts.small, RED, (panel.centerx, panel.y - 18), "center")

    def draw_title(self) -> None:
        self.owner.screen.blit(self.owner.assets.images["menu"], (0, 0))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((3, 8, 12, 92))
        self.owner.screen.blit(tint, (0, 0))
        self.panel(pygame.Rect(36, 80, 336, 588), 218, (74, 123, 132), 14)
        self.draw_text("SOLDADOS", self.owner.fonts.title, (242, 239, 218), (62, 108), shadow=True)
        self.draw_text("VS", self.owner.fonts.small, (225, 153, 91), (338, 153), "topright", True)
        self.draw_text("ZUMBIS", self.owner.fonts.title, (124, 202, 188), (62, 166), shadow=True)
        self.draw_text("DEFENDA. RECARREGUE. RESISTA.", self.owner.fonts.small, (184, 202, 204), (64, 224))
        for label, rect in self.owner.title_buttons():
            accent = TEAL if label in ("INICIAR", "CONTINUAR") else (66, 104, 116)
            self.button(label, rect, accent)
        if self.owner.can_continue():
            info = self.owner.continue_info()
            self.panel(pygame.Rect(430,526,800,86),235,TEAL,10)
            self.draw_text("PARTIDA SALVA",self.owner.fonts.h2,GOLD,(452,540))
            self.draw_text(info,self.owner.fonts.small,WHITE,(452,576))
        self.draw_text(f"{VERSION} • Cidade • Deserto • Cachoeira", self.owner.fonts.small, WHITE, (40, HEIGHT - 28))
        self.draw_text("Artes originais • campanha de 12 ondas", self.owner.fonts.small, WHITE, (WIDTH - 36, HEIGHT - 28), "topright")

    def draw_difficulty(self) -> None:
        self.owner.screen.blit(self.owner.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 178))
        self.owner.screen.blit(veil, (0, 0))
        self.draw_text("ESCOLHA A DIFICULDADE", self.owner.fonts.title, WHITE, (WIDTH / 2, 42), "center", True)
        self.draw_text("O modo altera recursos, força dos inimigos e ritmo das hordas.", self.owner.fonts.body, GOLD, (WIDTH / 2, 91), "center")
        descriptions = {}
        for key, subtitle in (("easy","COMEÇAR TRANQUILO"),("medium","CAMPANHA EQUILIBRADA"),("hard","SOBREVIVÊNCIA VETERANA")):
            p = difficulty_profile(key)
            descriptions[key] = (subtitle, (f"{p['initial_supplies']} suprimentos iniciais", f"Limite de reserva: {p['supply_cap']}", "12 ondas; chefes nas ondas 4, 8 e 12"))
        for index, (key, button_rect) in enumerate(self.owner.difficulty_buttons()):
            profile = difficulty_profile(key)
            card = pygame.Rect(button_rect.x - 25, 150, button_rect.width + 50, 370)
            self.panel(card, 235, profile["accent"], 14)
            subtitle, lines = descriptions[key]
            self.draw_text(profile["label"], self.owner.fonts.title, profile["accent"], (card.centerx, card.y + 32), "center", True)
            self.draw_text(subtitle, self.owner.fonts.small, WHITE, (card.centerx, card.y + 92), "center")
            for line_index, line in enumerate(lines):
                y = card.y + 148 + line_index * 53
                pygame.draw.circle(self.owner.screen, profile["accent"], (card.x + 31, y + 8), 5)
                self.draw_wrapped(line, self.owner.fonts.small, WHITE, pygame.Rect(card.x + 46, y - 7, card.width - 64, 31), 2)
            self.draw_wrapped(profile["summary"], self.owner.fonts.tiny, GRAY, pygame.Rect(card.x + 23, card.bottom - 71, card.width - 46, 38), 2, center=True)
            self.button(f"ESCOLHER {profile['label']}", button_rect, profile["accent"])
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_campaign(self) -> None:
        self.owner.screen.blit(self.owner.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 11, 16, 170))
        self.owner.screen.blit(veil, (0, 0))
        self.draw_text("MAPA DA CAMPANHA", self.owner.fonts.title, WHITE, (WIDTH / 2, 38), "center", True)
        if self.owner.save_error:
            self.draw_text("Não foi possível gravar o progresso. Verifique a pasta de dados do usuário.", self.owner.fonts.body, RED, (WIDTH / 2, 580), "center")
        profile = difficulty_profile(self.owner.difficulty)
        self.draw_text(f"Modo {profile['label']} — {profile['summary']}", self.owner.fonts.body, profile["accent"], (WIDTH / 2, 84), "center")
        self.draw_text("Escolha Cidade, Deserto ou Cachoeira. São 12 ondas: duas comuns, um sub-boss e um boss por ato.", self.owner.fonts.small, GOLD, (WIDTH / 2, 111), "center")
        for index, region in enumerate(("city", "desert", "beach")):
            info = REGIONS[region]
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            unlocked = True
            background = self.owner.assets.images[f"{region}_bg"]
            crop = pygame.Rect(index * 160, 150, 360, 208)
            image = pygame.Surface((360, 210))
            image.blit(background, (0, 0), crop)
            self.owner.screen.blit(image, rect)
            self.panel(rect, 105 if unlocked else 215, info["accent"] if unlocked else (75, 75, 75), 14)
            if not unlocked:
                lock = pygame.Rect(rect.centerx - 28, rect.y + 104, 56, 66)
                pygame.draw.rect(self.owner.screen, (49, 54, 60), lock, border_radius=9)
                pygame.draw.arc(self.owner.screen, GRAY, (lock.x + 9, lock.y - 27, 38, 40), 0, math.pi, 5)
                self.draw_text("BLOQUEADA", self.owner.fonts.h2, GRAY, (rect.centerx, rect.y + 184), "center")
            else:
                self.draw_text(info["short"], self.owner.fonts.h1, WHITE, (rect.centerx, rect.y + 222), "center", True)
                self.draw_text(info["tag"], self.owner.fonts.small, info["accent"], (rect.centerx, rect.y + 252), "center")
                record = self.owner.save.get("by_difficulty", {}).get(self.owner.difficulty, {}).get(region)
                legacy_best = self.owner.save["best_wave"].get(region, 0)
                if record is not None:
                    status = f"{profile['label']}: onda {record['best_wave']}/{TOTAL_WAVES}"
                elif legacy_best:
                    status = f"Anterior (geral): onda {legacy_best}/{TOTAL_WAVES}"
                else:
                    status = f"{profile['label']}: onda 0/{TOTAL_WAVES}"
                won = bool(record and record["victory"])
                self.draw_text(status, self.owner.fonts.small, GOLD if won else WHITE, (rect.centerx, rect.y + 286), "center")
                self.button("PREPARAR DEFESA", pygame.Rect(rect.x + 55, rect.y + 304, 250, 34), info["accent"])
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_characters(self) -> None:
        """Exibe todos os defensores e os infectados ativos da região."""
        region = self.owner.character_region
        info = REGIONS[region]
        self.owner.screen.blit(self.owner.assets.images[f"{region}_bg"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 184))
        self.owner.screen.blit(veil, (0, 0))
        self.draw_text("PERSONAGENS DO JOGO", self.owner.fonts.title, WHITE, (WIDTH / 2, 24), "center", True)
        for index, key in enumerate(("city", "desert", "beach")):
            rect = pygame.Rect(340 + index * 205, 82, 190, 42)
            self.button(REGIONS[key]["short"], rect, REGIONS[key]["accent"] if key == region else (76, 92, 98))
        self.button("SOLDADO", pygame.Rect(424, 136, 205, 40), info["accent"] if self.owner.dossier_kind == "units" else (70, 80, 85))
        self.button("ZUMBI", pygame.Rect(650, 136, 205, 40), (126, 196, 91) if self.owner.dossier_kind == "zombies" else (70, 80, 85))
        is_unit = self.owner.dossier_kind == "units"
        keys = self.owner.character_keys()
        if not keys:
            self.draw_text("Nenhum personagem disponível.", self.owner.fonts.h1, RED, (WIDTH / 2, 330), "center")
            self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
            return
        self.owner.character_index = int(clamp(self.owner.character_index, 0, len(keys) - 1))
        self.button("ANTERIOR", pygame.Rect(260, 184, 180, 40), (70, 88, 96))
        self.draw_text(f"{self.owner.character_index + 1}/{len(keys)}", self.owner.fonts.h2, WHITE, (WIDTH / 2, 204), "center")
        self.button("PRÓXIMO", pygame.Rect(WIDTH - 440, 184, 180, 40), (70, 88, 96))

        key = keys[self.owner.character_index]
        data = DEFENSES[key] if is_unit else ({**ENEMIES, **BOSSES})[key]
        actor = (DEFENDER_ACTOR_BY_KEY if is_unit else ENEMY_ACTOR_BY_KEY)[key]
        if self.owner.assets.production_clips is None:
            self.owner.assets.prepare_production_animations()
        clip_bank = self.owner.assets.production_clips or {}
        if actor not in clip_bank:
            self.draw_text("Arte do personagem ainda não foi carregada.", self.owner.fonts.h1, RED, (WIDTH / 2, 330), "center")
            self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
            return
        sprite = clip_bank[actor]["idle" if is_unit else "move"].frames[1]
        # Chefes largos não podem usar um quadro estreito da folha de combate
        # como retrato. Serra, tubos, braços e pernas atravessavam a fronteira
        # matemática da célula e apareciam cortados no dossiê. Os três retratos
        # completos de cada região têm fundo transparente e enquadramento
        # próprio, sem alterar as animações usadas no campo.
        boss_keys = REGION_BOSSES.get(region, ())
        if not is_unit and key in boss_keys:
            portraits = self.owner.assets.boss_portraits.get(region, [])
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
        self.draw_text(str(data.get("base", data.get("name"))), self.owner.fonts.h1, WHITE, (text_x, card.y + 32), shadow=True)
        faction = {
            "city": "Polícia dos Estados Unidos • Terminal Félix-13",
            "desert": "Forças Armadas do Egito • Escavação Khepra",
            "beach": "Marinha do Brasil • Cachoeira Contaminada",
        }[region]
        self.draw_text(faction if is_unit else info["tag"], self.owner.fonts.small, accent, (text_x, card.y + 72))
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
            action = "rastejar • morder" if crawler else ("correr • avançar" if "dash" in data.get("tags", ()) else "caminhar • morder")
            stats = (
                f"VIDA {int(data['hp'])}     DANO {int(data['damage'])}     VELOCIDADE {int(data['speed'])}",
                f"AÇÃO: {action} • receber dano • desaparecer",
            )
        for index, line in enumerate(stats):
            box = pygame.Rect(text_x, card.y + 105 + index * 49, 522, 37)
            pygame.draw.rect(self.owner.screen, (20, 31, 36), box, border_radius=8)
            self.draw_text(line, self.owner.fonts.small, GOLD if index == 0 else TEAL, (box.x + 14, box.y + 10))
        if is_unit:
            self.draw_wrapped(str(data["lore"]), self.owner.fonts.small, WHITE, pygame.Rect(text_x, card.y + 205, 522, 48), 2)
            self.draw_wrapped("FUNÇÃO: " + str(data["tactical_function"]), self.owner.fonts.tiny, TEAL, pygame.Rect(text_x, card.y + 261, 522, 30), 2)
            self.draw_wrapped("NECESSÁRIA: " + str(data["mechanical_need"]), self.owner.fonts.tiny, GOLD, pygame.Rect(text_x, card.y + 296, 522, 35), 2)
        else:
            counter = str(data.get("counter_label", "Dano concentrado"))
            defense = str(data.get("defense_name", "sem defesa especial"))
            self.draw_wrapped(str(data["ability"]), self.owner.fonts.body, WHITE, pygame.Rect(text_x, card.y + 205, 522, 62), 3)
            self.draw_wrapped(f"DEFESA: {defense} • COUNTER: {counter}", self.owner.fonts.tiny, GOLD, pygame.Rect(text_x, card.y + 282, 522, 38), 2)
        self.draw_text("INTEGRADO • arte, animação e ficha próprias desta região", self.owner.fonts.tiny, GRAY, (text_x, card.bottom - 22))
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

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
            self.owner.screen,
            fill,
            ((attach_x - 12, attach_y), (attach_x + 12, attach_y), tail),
        )
        pygame.draw.lines(
            self.owner.screen,
            border,
            False,
            ((attach_x - 12, attach_y), tail, (attach_x + 12, attach_y)),
            3,
        )
        pygame.draw.rect(self.owner.screen, fill, rect, border_radius=18)
        pygame.draw.rect(self.owner.screen, border, rect, 3, border_radius=18)
        self.draw_wrapped(text, self.owner.fonts.small, INK, rect.inflate(-18, -13), 3, center=True)

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
        assert self.owner.assets.production_clips is not None
        frames = self.owner.assets.production_clips[actor][state].frames
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
        rendered = pygame.transform.smoothscale(sprite, (max(1, round(width)), max(1, round(height))))
        if flip:
            rendered = pygame.transform.flip(rendered, True, False)
        rect = rendered.get_rect(midbottom=point)
        self.owner.screen.blit(rendered, rect)
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
        page = pages[self.owner.story_page]
        region = page["region"]
        accent = REGIONS[region]["accent"]
        bg = self.owner.assets.images[f"{region}_bg"]
        defender_actor = DEFENDER_ACTOR_BY_KEY[BASIC_DEFENDER_BY_REGION[region]]
        enemy_actor = ENEMY_ACTOR_BY_KEY[BASIC_ENEMY_BY_REGION[region]]

        self.owner.screen.fill((12, 11, 10))
        self.draw_text("HISTÓRIA DO JOGO", self.owner.fonts.title, WHITE, (WIDTH / 2, 18), "center", True)
        self.draw_text(page["title"], self.owner.fonts.h2, accent, (WIDTH / 2, 66), "center")
        panels = (
            (pygame.Rect(55, 103, 1170, 235), pygame.Rect(0, 70, 1280, 420)),
            (pygame.Rect(55, 356, 565, 246), pygame.Rect(0, 140, 690, 480)),
            (pygame.Rect(660, 356, 565, 246), pygame.Rect(590, 120, 690, 500)),
        )
        for index, (dest, source) in enumerate(panels):
            image = pygame.transform.smoothscale(bg.subsurface(source), dest.size)
            self.owner.screen.blit(image, dest)
            # Retícula e borda grossa deixam o quadro com leitura impressa,
            # sem transformar o cenário numa simples miniatura do mapa.
            shade = pygame.Surface(dest.size, pygame.SRCALPHA)
            shade.fill((15, 15, 18, 34 if index == 0 else 50))
            self.owner.screen.blit(shade, dest)
            for x in range(dest.left + 3, dest.right, 7):
                for y in range(dest.top + 3, dest.bottom, 7):
                    pygame.draw.circle(self.owner.screen, (0, 0, 0, 36), (x, y), 1)
            pygame.draw.rect(self.owner.screen, (246, 239, 205), dest, 6)

            narration = pygame.Rect(dest.x + 12, dest.y + 10, min(dest.width - 24, 430), 38)
            pygame.draw.rect(self.owner.screen, (246, 214, 113), narration, border_radius=3)
            pygame.draw.rect(self.owner.screen, INK, narration, 2, border_radius=3)
            self.draw_wrapped(page["captions"][index], self.owner.fonts.tiny, INK, narration.inflate(-12, -8), 2)

            floor = dest.bottom - 10
            if index == 0:
                guard = self.draw_comic_actor(defender_actor, "idle", 2, (dest.x + 250, floor), 132)
                self.draw_comic_actor(enemy_actor, "move", 4, (dest.right - 230, floor), 137)
                bubble = pygame.Rect(dest.x + 405, dest.y + 57, 355, 70)
                tail = (guard.centerx + 20, guard.top + 22)
            elif index == 1:
                guard = self.draw_comic_actor(defender_actor, "idle", 1, (dest.x + 92, floor), 112)
                self.draw_comic_actor(enemy_actor, "move", 1, (dest.centerx + 70, floor + 3), 112)
                self.draw_comic_actor(enemy_actor, "bite", 4, (dest.right - 58, floor), 120)
                bubble = pygame.Rect(dest.x + 148, dest.y + 54, 365, 66)
                tail = (guard.centerx + 8, guard.top + 18)
            else:
                guard = self.draw_comic_actor(defender_actor, "shoot", 3, (dest.centerx - 65, floor), 120)
                self.draw_comic_actor(enemy_actor, "hit", 3, (dest.right - 72, floor), 112)
                bubble = pygame.Rect(dest.x + 24, dest.y + 52, 310, 66)
                tail = (guard.centerx + 16, guard.top + 26)
            self.draw_comic_bubble(bubble, page["dialogue"][index], tail)
            self.draw_text(
                page["sfx"][index],
                self.owner.fonts.h2,
                (255, 234, 91),
                (dest.right - 22, dest.y + 18),
                "topright",
                True,
            )

        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))
        self.button("ANTERIOR", pygame.Rect(245, 646, 170, 44), accent, self.owner.story_page > 0)
        self.draw_text(f"PÁGINA {self.owner.story_page + 1}/3", self.owner.fonts.small, WHITE, (WIDTH / 2, 661), "center")
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 415, 646, 170, 44), accent, self.owner.story_page < 2)

    def draw_profile(self) -> None:
        """Tela de perfil e loja; o jogador local usa o nome escolhido no ranking."""
        owner = self.owner
        owner.screen.blit(owner.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 178))
        owner.screen.blit(veil, (0, 0))
        self.panel(pygame.Rect(150, 45, 980, 605), 238, (78, 126, 133), 16)
        self.draw_text("PERFIL E LOJA", owner.fonts.title, WHITE, (WIDTH / 2, 62), "center", True)
        self.draw_text(
            "Escolha o nome que aparecerá no ranking deste computador.",
            owner.fonts.body, GOLD, (WIDTH / 2, 111), "center",
        )

        name_rect = owner.profile_name_rect()
        self.panel(name_rect, 248, TEAL, 8)
        self.draw_text("NOME DO JOGADOR", owner.fonts.tiny, GRAY, (name_rect.x, name_rect.y - 22))
        draft = owner.profile_name_draft.strip()
        self.draw_text(
            draft if draft else "Digite seu nome (até 20 caracteres)",
            owner.fonts.h2 if draft else owner.fonts.body,
            WHITE if draft else GRAY,
            (name_rect.centerx, name_rect.centery), "center",
        )
        self.button("SALVAR PERFIL", owner.profile_save_rect(), TEAL)

        # O perfil é lido ao abrir a tela ou após uma compra/uso, nunca por quadro.
        profile = owner.profile_data
        self.draw_text(
            f"Perfil ativo: {profile['player_name'] or 'nenhum'}    •    Créditos: {profile['credits']}",
            owner.fonts.body, GOLD, (WIDTH / 2, 356), "center",
        )

        cards = (
            (owner.profile_medkit_rect(), "medkit", "KIT MÉDICO", "Recupera até 45% da vida perdida de uma tropa viva.", "medkits"),
            (owner.profile_ammo_rect(), "tactical_ammo", "MUNIÇÃO TÁTICA", "Por 30 segundos, uma tropa armada não gasta munição nem recarrega.", "tactical_ammo"),
        )
        active_profile = bool(owner.player_name)
        for rect, item_key, title, description, stock_key in cards:
            item = SHOP_ITEMS[item_key]
            self.panel(rect, 238, TEAL if item_key == "medkit" else GOLD, 12)
            self.draw_text(title, owner.fonts.h2, TEAL if item_key == "medkit" else GOLD,
                           (rect.centerx, rect.y + 16), "center", True)
            self.draw_wrapped(description, owner.fonts.small, WHITE,
                              pygame.Rect(rect.x + 22, rect.y + 48, rect.width - 44, 42), 2, center=True)
            self.draw_text(
                f"Estoque: {profile[stock_key]}   •   Preço: {item['price']} créditos",
                owner.fonts.tiny, GRAY, (rect.centerx, rect.y + 97), "center",
            )
            self.button(
                "COMPRAR ITEM" if active_profile else "SALVE SEU PERFIL PRIMEIRO",
                (owner.profile_medkit_buy_rect() if item_key == "medkit" else owner.profile_ammo_buy_rect()),
                TEAL if item_key == "medkit" else GOLD, active_profile,
            )

        if owner.profile_error:
            self.draw_wrapped(
                owner.profile_error, owner.fonts.small, RED,
                pygame.Rect(245, 552, 790, 45), 2, center=True,
            )
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_settings(self):
        settings_panel(self)

    def draw_howto(self):
        howto_panel(self)

    def draw_session_confirmation(self) -> None:
        self.draw_title()
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 12, 205))
        self.owner.screen.blit(veil, (0, 0))
        self.panel(pygame.Rect(285, 210, 710, 285), 250, GOLD, 12)
        exiting = self.owner.scene == "confirm_exit"
        heading = "SAIR SEM SALVAR?" if exiting else "INICIAR NOVA PARTIDA?"
        detail = ("A última gravação falhou. Sair agora pode perder os avanços recentes."
                  if exiting else "A nova partida substituirá a atual. Para mantê-la, volte e escolha CONTINUAR.")
        self.draw_text(heading, self.owner.fonts.h2, GOLD, (WIDTH // 2, 250), "center")
        self.draw_wrapped(detail, self.owner.fonts.body, WHITE,
                          pygame.Rect(335, 300, 610, 85), 3, center=True)
        self.button("SAIR SEM SALVAR" if exiting else "NOVA PARTIDA",
                    self.owner.confirm_accept_rect(), GOLD)
        self.button("VOLTAR", self.owner.confirm_cancel_rect(), TEAL)
