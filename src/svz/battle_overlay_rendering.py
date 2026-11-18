"""Camadas sobre a batalha: defesas de faixa e textos de impacto."""
from __future__ import annotations

from .battle import Battle
from .board import lane_bomb_ground_y, lane_bomb_home_x, lane_depth


class BattleOverlayRenderingMixin:
    def draw_lane_bombs(self, battle: Battle) -> None:
        """Mostra a contenção visual própria de cada terreno antes da invasão."""
        for cart in battle.lane_bombs:
            if cart.state == "spent":
                continue
            y = lane_bomb_ground_y(battle.region, cart.row)
            x = cart.x if cart.state == "rolling" else lane_bomb_home_x(battle.region, cart.row)
            is_water_buoy = battle.region == "beach" and cart.row in battle.water_rows
            depth = lane_depth(battle.region, cart.row)
            # As bombas de Minas ficam plantadas no contato e somem no mesmo
            # instante em que disparam a cadeia de explosões. Trator e drone
            # percorrem a faixa e desaparecem antes da entrada inimiga.
            if battle.region == "beach" and cart.state == "rolling":
                continue
            sprite, base_size = self.owner.scenario_runtime.lane_defense_frame(
                battle.region,
                cart.row,
                moving=cart.state == "rolling",
                water=is_water_buoy,
            )
            width, height = base_size[0] * depth, base_size[1] * depth
            self.draw_actor_sprite(sprite, x, y, width, height, cart.motion, enemy=False)

    def draw_particles(self, battle: Battle) -> None:
        # Partículas circulares foram retiradas. Impactos e matéria usam folhas
        # rasterizadas; textos de dano continuam sendo informação de HUD.
        for text in battle.texts:
            self.draw_text(text.text, self.owner.fonts.tiny, text.color, (text.x, text.y), "center", True)
