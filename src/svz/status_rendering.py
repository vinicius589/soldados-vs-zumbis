"""Desenho dos avisos, estados de pausa e resultados da campanha.

O mixin mantém telas de status e histórico separadas do renderizador da partida.
Ele usa os helpers do renderizador composto e não importa rendering.py.
"""
from __future__ import annotations

import pygame

from .config import GOLD, GRAY, HEIGHT, RED, TEAL, TOTAL_WAVES, WHITE, WIDTH
from .content import REGIONS


class StatusRenderingMixin:
    def draw_battle_status(self) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        if battle.boss_warning > 0:
            banner = pygame.Rect(WIDTH // 2 - 330, 238, 660, 124)
            self.panel(banner, 244, RED, 12)
            self.draw_text("ALERTA: CHEFE CHEGANDO", self.owner.fonts.h1, RED, (banner.centerx, banner.y + 16), "center", True)
            self.draw_text(battle.boss_banner_name, self.owner.fonts.h2, WHITE, (banner.centerx, banner.y + 54), "center", True)
            self.draw_text(battle.boss_banner_subtitle, self.owner.fonts.small, GOLD, (banner.centerx, banner.y + 85), "center")
        if battle.paused:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((3, 8, 12, 132))
            self.owner.screen.blit(veil, (0, 0))
            pause_card = pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 74, 410, 148)
            self.panel(pause_card, 246, GOLD, 12)
            self.draw_text("PAUSADO", self.owner.fonts.title, GOLD, (pause_card.centerx, pause_card.y + 23), "center", True)
            self.draw_text(f"PAUSA ou {self.owner.settings.label('pause')}: continuar. F5: salvar.", self.owner.fonts.small, WHITE, (pause_card.centerx, pause_card.y + 86), "center")

    def draw_scores(self) -> None:
        """Desenha o ranking agregado ou o histórico detalhado de partidas."""
        owner = self.owner
        owner.screen.fill((12, 20, 25))
        is_history = owner.score_view == "history"
        title = "HISTÓRICO DE PARTIDAS" if is_history else "RANKING DOS JOGADORES"
        self.draw_text(title, owner.fonts.title, GOLD, (WIDTH / 2, 38), "center", True)
        subtitle = (
            "Veja os resultados recentes, incluindo região, dificuldade e pontuação."
            if is_history
            else "A classificação usa a soma dos pontos das partidas. Créditos da loja não contam."
        )
        self.draw_text(subtitle, owner.fonts.small, GRAY, (WIDTH / 2, 79), "center")

        if is_history:
            columns = (35, 205, 400, 575, 730, 850, 1035)
            headers = ("DATA", "JOGADOR", "REGIÃO", "DIFICULDADE", "ONDA", "RESULTADO", "PONTOS")
            for x, label in zip(columns, headers):
                self.draw_text(label, owner.fonts.tiny, TEAL, (x, 119))
            for index, row in enumerate(owner.score_rows):
                # O store retorna sete campos: data, jogador, região, modo,
                # onda, vitória/derrota e pontos. Não reduzir a tupla por índice.
                date, player_name, region, difficulty, wave, victory, points = row
                region_label = REGIONS.get(region, {}).get("short", str(region).upper())
                difficulty_label = {"easy": "Fácil", "medium": "Médio", "hard": "Difícil"}.get(
                    difficulty, str(difficulty).title()
                )
                labels = (
                    str(date)[:16], str(player_name)[:20], region_label,
                    difficulty_label, str(wave), "Vitória" if bool(victory) else "Derrota",
                    f"{int(points):,}".replace(",", "."),
                )
                y = 153 + index * 40
                if index % 2 == 0:
                    pygame.draw.rect(owner.screen, (20, 32, 38), pygame.Rect(24, y - 6, 1230, 32), border_radius=5)
                for x, label in zip(columns, labels):
                    self.draw_text(label, owner.fonts.tiny, WHITE, (x, y))
            total_label = f"Página {owner.score_page + 1} • {owner.score_total} partidas"
            empty_label = "Nenhuma partida concluída ainda. Termine uma partida para registrar seus pontos."
        else:
            columns = (75, 220, 540, 770, 920, 1070)
            headers = ("POSIÇÃO", "JOGADOR", "PONTOS TOTAIS", "PARTIDAS", "VITÓRIAS", "RECORDE")
            for x, label in zip(columns, headers):
                self.draw_text(label, owner.fonts.small, TEAL, (x, 119))
            for index, row in enumerate(owner.score_rows):
                place, player_name, total_points, matches, wins, best_score = row
                labels = (
                    f"{place}º", str(player_name)[:20],
                    f"{int(total_points):,}".replace(",", "."), str(matches), str(wins),
                    f"{int(best_score):,}".replace(",", "."),
                )
                y = 158 + index * 40
                if index % 2 == 0:
                    pygame.draw.rect(owner.screen, (20, 32, 38), pygame.Rect(55, y - 6, 1170, 32), border_radius=5)
                for x, label in zip(columns, labels):
                    self.draw_text(label, owner.fonts.small, GOLD if index == 0 else WHITE, (x, y))
            total_label = f"Página {owner.score_page + 1} • {owner.score_total} jogadores"
            empty_label = "O ranking ainda está vazio. Jogue uma partida para aparecer aqui."

        if not owner.score_rows:
            message = owner.score_store.error or empty_label
            self.draw_wrapped(message, owner.fonts.body, WHITE, pygame.Rect(190, 300, 900, 70), 2, center=True)
        else:
            self.draw_text(total_label, owner.fonts.small, GRAY, (WIDTH / 2, 600), "center")

        # As posições abaixo são compartilhadas com Game.handle_click; assim o
        # que aparece na tela é exatamente a área que responde ao clique.
        self.button("VOLTAR", pygame.Rect(50, 645, 170, 46), TEAL)
        toggle_label = "VER RANKING" if is_history else "VER HISTÓRICO"
        self.button(toggle_label, pygame.Rect(430, 645, 260, 46), TEAL)
        self.button("ANTERIOR", pygame.Rect(735, 645, 150, 46), TEAL, owner.score_page > 0)
        self.button(
            "PRÓXIMA", pygame.Rect(910, 645, 280, 46), TEAL,
            (owner.score_page + 1) * 10 < owner.score_total,
        )

    def draw_result_overlay(self) -> None:
        assert self.owner.battle is not None
        battle = self.owner.battle
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 6, 9, 188))
        self.owner.screen.blit(overlay, (0, 0))
        heading = "REGIÃO PROTEGIDA" if battle.victory else "BASE INVADIDA"
        color = GOLD if battle.victory else RED
        self.panel(pygame.Rect(WIDTH // 2 - 265, HEIGHT // 2 - 130, 530, 285), 242, color, 16)
        self.draw_text(heading, self.owner.fonts.title, color, (WIDTH / 2, HEIGHT / 2 - 85), "center", True)
        body = "Você venceu as 12 ondas e os três chefes da região. Todos os territórios continuam disponíveis." if battle.victory else "Um infectado atravessou a linha final. Refaça a equipe e preserve munição para as ondas finais."
        self.draw_wrapped(body, self.owner.fonts.body, WHITE, pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 30, 410, 55), 3, center=True)
        self.draw_text(f"Onda alcançada: {battle.wave}/{TOTAL_WAVES}", self.owner.fonts.small, GRAY, (WIDTH / 2, HEIGHT // 2 + 46), "center")
        self.draw_text(f"PONTUAÇÃO: {battle.score}", self.owner.fonts.h2, GOLD, (WIDTH / 2, HEIGHT / 2 + 76), "center")
        if self.owner.score_store.error:
            self.draw_text(self.owner.score_store.error, self.owner.fonts.tiny, RED, (WIDTH/2, HEIGHT/2+178), "center")
        self.button("VOLTAR AO MAPA • ENTER", pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50), color)
