"""Apresentação de cartões, retratos de atores e texto ajustado à área."""
from __future__ import annotations

import pygame

from .content import (
    CARD_ART_ASSETS,
    DEFENDER_ACTOR_BY_KEY,
    DEFENSES,
    regional_sprite_index,
    weapon_reload_seconds,
)


class CardRenderingMixin:
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
            (max(1, round(content.width * limiter)), max(1, round(content.height * limiter))),
        )
        target = rendered.get_rect(midbottom=(rect.centerx, rect.bottom - 4))
        if outline is not None:
            mask = pygame.mask.from_surface(rendered, threshold=8)
            silhouette = mask.to_surface(
                setcolor=(*outline, 205),
                unsetcolor=(0, 0, 0, 0),
            ).convert_alpha()
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                self.owner.screen.blit(silhouette, target.move(dx, dy))
        self.owner.screen.blit(rendered, target)
        return target

    def draw_portrait_backdrop(
        self, rect: pygame.Rect, accent: tuple[int, int, int]
    ) -> None:
        """Contraste neutro para uniformes pretos sem fingir transparência."""
        pygame.draw.rect(self.owner.screen, (24, 35, 43), rect, border_radius=12)
        glow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow,
            (*accent, 38),
            (rect.width // 10, rect.height // 8, rect.width * 4 // 5, rect.height * 3 // 4),
        )
        self.owner.screen.blit(glow, rect.topleft)
        pygame.draw.rect(self.owner.screen, (*accent,), rect, width=1, border_radius=12)

    def card_sprite(self, region: str, key: str, index: int) -> pygame.Surface:
        """Escolhe a silhueta da carta e do objeto já posicionado.

        Minas recebem sprites individuais onde a leitura do cenário importa:
        cidade usa duas cargas urbanas limpas, Praia usa duas minas de areia e
        a Bomba de Água é uma mina naval independente, sem plataforma.
        """
        actor_key = DEFENDER_ACTOR_BY_KEY.get(key)
        if actor_key and self.owner.assets.production_clips is None:
            self.owner.assets.prepare_production_animations()
        if actor_key and self.owner.assets.production_clips:
            return self.owner.assets.production_clips[actor_key]["idle"].frames[1]
        custom_asset = CARD_ART_ASSETS.get((region, key))
        if custom_asset:
            return self.owner.assets.images[custom_asset]
        terrain_mine_assets = {
            "city": {"mina": "city_mine_n1", "mina_segura": "city_mine_n2"},
            "beach": {"mina": "beach_mine_land_n1", "mina_segura": "beach_mine_land_n2"},
        }
        if key == "atirador_lancha":
            return self.owner.assets.images["beach_boat_shooter"]
        asset_key = terrain_mine_assets.get(region, {}).get(key)
        if asset_key:
            return self.owner.assets.images[asset_key]
        if key == "bomba_agua":
            return self.owner.assets.images["beach_mine_water"]
        if DEFENSES.get(key, {}).get("water_only"):
            water_index = {"lancha": 5, "submarino": 6}[key]
            return self.owner.assets.base_unit("beach", water_index)
        level = int(DEFENSES.get(key, {}).get("level", 1))
        return self.owner.assets.unit(region, regional_sprite_index(region, key), level)

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
            return f"DANO {int(data['damage'])}", f"SEM MUNIÇÃO • ALC {int(data['range'])}"
        if role == "waterjet":
            return f"DANO {int(data['damage'])}", f"LENTO 32% • ALC {int(data['range'])}"
        if role == "poison":
            return f"DANO {int(data['damage'])}", f"VENENO 4.2s • ALC {int(data['range'])}"
        if role == "gas_grenade":
            return f"DANO {int(data['damage'])}", f"GÁS EM ÁREA • ALC {int(data['range'])}"
        if role == "barrier":
            return f"HP {int(data['hp'])}", "EXPLODE" if level >= 2 else "BLOQUEIO"
        if role == "mine":
            area = "ÁREA" if data.get("water_only") else ("SEGURA" if level >= 2 else "1 ALVO")
            return f"DANO {int(data['damage'])}", area
        if role == "suicide_bomber":
            return f"DANO {int(data['damage'])}", "CONTATO • IMÓVEL"
        reload_time = weapon_reload_seconds(data)
        reload_label = f" • REC {reload_time:.1f}s" if reload_time else ""
        return f"DANO {int(data['damage'])}", f"MUN {int(data['ammo'])}{reload_label}"

    def draw_wrapped(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect, lines: int, center: bool = False) -> None:
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
