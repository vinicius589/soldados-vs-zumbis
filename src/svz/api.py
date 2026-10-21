"""API de integração usada pelos testes e pelas ferramentas da versão final."""
import sys

from svz.animation import AnimationManager
from svz.roster import EXPANSION_DEFENDERS
from svz.production_animations import build_production_clips
from svz.production_animations import new_production_animation
from svz.scenarios import ScenarioRuntime
from dataclasses import dataclass
from dataclasses import field
from svz.presenter import ActorCommand
from svz.presenter import OpenGLPresenter
from pathlib import Path
from typing import Callable
from svz.visual_layout import DEFENDER_WEAPON_PROFILES
from svz.visual_layout import ENEMY_ATTACK_ORIGINS
from svz.visual_layout import ENEMY_BODY_LAYOUTS
from svz.visual_layout import PROJECTILE_LAUNCH_GAPS
from svz.visual_layout import PROJECTILE_LAYOUTS
from svz.visual_layout import defender_layout
import json
import math
import os
import pygame
import random

from svz.config import (
    ASSET_DIR,
    AUDIO_DIR,
    BEACH_WATER_DEFENDERS,
    BEACH_WATER_ROWS,
    BOARD,
    CARD_RECHARGE_SECONDS,
    CELL_H,
    CELL_W,
    COLS,
    ENEMY_ENTRY_REVEAL_SECONDS,
    ENEMY_ENTRY_X,
    FPS,
    GOLD,
    GRAY,
    HEIGHT,
    INK,
    LANE_BOMB_HOME_X,
    LANE_BOUNDS,
    LANE_PROTECTION_COLUMN,
    LANE_PROTECTION_END_X,
    LAST_PLACEABLE_COLUMN,
    PRODUCTION_ASSET_DIR,
    RED,
    ROOT,
    ROWS,
    SAVE_PATH,
    TEAL,
    TOTAL_WAVES,
    VERSION,
    WHITE,
    WIDTH,
)
from svz.audio import (
    AudioSystem,
)
from svz.math_utils import (
    clamp,
    lerp,
    title_case,
)
from svz.motion import (
    ActorMotion,
    DefeatAnimation,
    VisualEffect,
)
from svz.balance import (
    boss_damage_scale,
    boss_wave_scale,
    enemy_damage_scale,
    enemy_wave_scale,
)
from svz.board import (
    cell_center,
    cell_rect,
    lane_bomb_ground_y,
    lane_bomb_home_x,
    lane_bounds,
    lane_depth,
    terrain_y,
)
from svz.content import (
    ACTIVE_ENEMY_SKILL_TAGS,
    BASIC_DEFENDER_BY_REGION,
    BASIC_ENEMY_BY_REGION,
    BEACH_WATER_ENEMIES,
    BOSSES,
    CARD_ART_ASSETS,
    CARD_ATLAS_INDEX,
    CARD_DETAILS,
    CITY_TACTICAL_UNITS,
    CRAWLER_ENEMIES,
    DEFENDER_ACTOR_BY_KEY,
    DEFENSES,
    DIFFICULTIES,
    ENEMIES,
    ENEMY_ACTOR_BY_KEY,
    ENEMY_DEFENSE_TRAITS,
    PROMOTIONS,
    REGIONS,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
    WEAPON_RELOAD_SECONDS,
    difficulty_profile,
    regional_sprite_index,
    wave_enemy_pool,
    weapon_reload_seconds,
)
from svz.persistence import (
    load_save,
    make_save,
    save_campaign,
)
from svz.assets import (
    Assets,
    FontBook,
)
from svz.entities import (
    Defender,
    Enemy,
    FloatingText,
    LaneBomb,
    Particle,
    Projectile,
    SpawnOrder,
)
from svz.actor_visuals import (
    actor_pose,
    animated_actor_render_scale,
    defender_animation_profile,
    defender_render_scale,
    defender_visual_layout,
    defender_weapon_origin,
    enemy_animation_profile,
    enemy_render_scale,
    sprite_emitter_contact,
)
from svz.battle import (
    Battle,
)
from svz.app import (
    Game,
)
from svz.rendering import (
    GameRenderer,
)
from svz.waves import (
    WaveDirector,
)
