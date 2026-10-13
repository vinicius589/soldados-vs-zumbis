"""Estado versionado da partida; só dados e tipos conhecidos, nunca código."""
from __future__ import annotations
from dataclasses import fields
import math
import random
import types
from typing import get_args, get_origin, get_type_hints, Union

from .battle import Battle
from .config import ROWS, COLS, TOTAL_WAVES
from .content import (REGIONS, DIFFICULTIES, DEFENSES, ENEMIES, BOSSES,
                      DEFENDER_ACTOR_BY_KEY, ENEMY_ACTOR_BY_KEY, REGION_ROSTERS)
from .entities import Defender, Enemy, Projectile, Particle, FloatingText, SpawnOrder, LaneBomb
from .motion import ActorMotion, VisualEffect

SCHEMA = 1
CLASSES = {c.__name__: c for c in (Defender, Enemy, Projectile, Particle, FloatingText,
                                 SpawnOrder, LaneBomb, ActorMotion, VisualEffect)}
EXCLUDED = {'app', 'wave_director', 'difficulty_data', 'water_rows', 'fallen'}
ENTITY_EXCLUDED = {'visual_animation', 'stats', 'data'}
ANIMATION_FIELDS = ('state', 'frame_index', 'frame_elapsed', 'finished', 'paused',
                    'playback_rate', 'loop_count')
SCENARIO_FIELDS = ('elapsed', 'horde_flame', '_was_horde', '_last_city_whistle_cycle',
                   '_last_beach_alarm_cycle', '_last_storm_cycle')
COLLECTIONS = {'defenders': Defender, 'enemies': Enemy, 'projectiles': Projectile,
               'particles': Particle, 'texts': FloatingText, 'effects': VisualEffect,
               'orders': SpawnOrder, 'lane_bombs': LaneBomb}
MAX_OBJECTS = 12000


def require(condition, message='Partida salva inválida.'):
    if not condition:
        raise ValueError(message)


def typed(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (types.UnionType, Union):
        return any(typed(value, a) for a in args)
    if annotation is type(None):
        return value is None
    if annotation is float:
        return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e12
    if annotation in (bool, int, str):
        return type(value) is annotation and (annotation is not str or len(value) <= 4096)
    if annotation is object:
        return value is None or type(value) in (Defender, Enemy)
    if origin is tuple:
        return type(value) is tuple and len(value) == len(args) and all(typed(v, a) for v, a in zip(value, args))
    return isinstance(value, annotation)


def capture(battle):
    nodes, identifiers = [], {}

    def encode(value):
        if type(value) in CLASSES.values():
            marker = id(value)
            if marker in identifiers:
                return {'ref': identifiers[marker]}
            index = len(nodes)
            require(index < MAX_OBJECTS, 'Partida grande demais para salvar.')
            identifiers[marker] = index
            node = {'type': type(value).__name__, 'fields': {}}
            nodes.append(node)
            node['fields'] = {f.name: encode(getattr(value, f.name)) for f in fields(value)
                              if f.name not in ENTITY_EXCLUDED}
            if isinstance(value, (Defender, Enemy)):
                animation = value.visual_animation
                node['animation'] = ({k: getattr(animation, k) for k in ANIMATION_FIELDS}
                                     if animation is not None else None)
            return {'ref': index}
        if type(value) in (tuple, set):
            return {'tuple' if type(value) is tuple else 'set':
                    [encode(v) for v in (sorted(value) if type(value) is set else value)]}
        if type(value) is list:
            return [encode(v) for v in value]
        if type(value) is dict:
            return {k: encode(v) for k, v in value.items()}
        require(value is None or type(value) in (str, bool, int, float))
        if type(value) is float:
            require(math.isfinite(value))
        return value

    state = {k: encode(v) for k, v in vars(battle).items() if k not in EXCLUDED}
    return {'schema': SCHEMA, 'battle': state, 'objects': nodes,
            'random': encode(random.getstate()),
            'scenario': {k: getattr(battle.app.scenario_runtime, k) for k in SCENARIO_FIELDS},
            'scene_elapsed': battle.app.scene_elapsed,
            'integration_preview': battle.app.integration_preview}


def restore(snapshot, app):
    """Constrói fora da partida ativa e valida tudo antes de alterar a aplicação."""
    require(type(snapshot) is dict and type(snapshot.get('schema')) is int and snapshot['schema'] == SCHEMA,
            'Formato de partida incompatível com esta versão.')
    state = snapshot.get('battle')
    records = snapshot.get('objects')
    require(type(state) is dict and type(records) is list and len(records) <= MAX_OBJECTS)
    require(state.get('region') in REGIONS and state.get('difficulty') in DIFFICULTIES)
    objects = []
    for record in records:
        require(type(record) is dict and record.get('type') in CLASSES)
        objects.append(object.__new__(CLASSES[record['type']]))

    def decode(value, depth=0):
        require(depth <= 32, 'Estrutura da partida excede o limite.')
        if type(value) is list:
            require(len(value) <= MAX_OBJECTS)
            return [decode(v, depth + 1) for v in value]
        if type(value) is dict:
            if set(value) == {'ref'}:
                index = value['ref']
                require(type(index) is int and 0 <= index < len(objects))
                return objects[index]
            if set(value) in ({'tuple'}, {'set'}):
                tag = next(iter(value))
                require(type(value[tag]) is list and len(value[tag]) <= MAX_OBJECTS)
                decoded = [decode(v, depth + 1) for v in value[tag]]
                return tuple(decoded) if tag == 'tuple' else set(decoded)
            return {k: decode(v, depth + 1) for k, v in value.items()}
        require(value is None or type(value) in (str, bool, int, float))
        if type(value) in (int, float):
            require(math.isfinite(value) and abs(value) <= 1e12)
        if type(value) is str:
            require(len(value) <= 4096)
        return value

    for obj, record in zip(objects, records):
        attributes = record.get('fields')
        expected = {f.name for f in fields(obj)} - ENTITY_EXCLUDED
        require(type(attributes) is dict and set(attributes) == expected)
        hints = get_type_hints(type(obj))
        for name, raw in attributes.items():
            value = decode(raw)
            require(typed(value, hints[name]), 'Tipo inválido: ' + name)
            setattr(obj, name, value)
        if isinstance(obj, (Defender, Enemy, SpawnOrder, LaneBomb)):
            require(0 <= obj.row < ROWS)
        if isinstance(obj, Defender):
            require(obj.key in DEFENSES and obj.region == state['region'] and 0 <= obj.col < COLS)
            require(0 <= obj.sprite_index < 256 and obj.ammo >= 0)
            obj.stats = DEFENSES[obj.key]
        if isinstance(obj, Enemy):
            require(obj.key in ENEMIES or obj.key in BOSSES)
            require(obj.region == state['region'] and obj.difficulty == state['difficulty'])
            require(0 <= obj.wave <= TOTAL_WAVES)
            obj.data = BOSSES.get(obj.key) or ENEMIES[obj.key]
        if isinstance(obj, SpawnOrder):
            require(obj.key in ENEMIES or obj.key in BOSSES)
            require(not obj.boss or obj.key in BOSSES)
        if isinstance(obj, LaneBomb):
            require(obj.state in ('armed', 'rolling', 'spent'))
        if isinstance(obj, (Particle, FloatingText, VisualEffect)):
            require(all(0 <= c <= 255 for c in obj.color))
        if isinstance(obj, (Defender, Enemy)):
            obj.visual_animation = None

    selected = decode(state.get('selected'))
    require(type(selected) is list and 1 <= len(selected) <= 8)
    available = {key for key, _ in REGION_ROSTERS[state['region']]}
    require(all(type(item) is tuple and len(item) == 2 and
                type(item[0]) is str and item[0] in available and type(item[1]) is str for item in selected))
    # Battle.__init__ não consome aleatoriedade nem grava arquivos.
    battle = Battle(app, state['region'], selected)
    expected = set(vars(battle)) - EXCLUDED
    require(set(state) == expected, 'Campos da partida incompatíveis.')
    for name, raw in state.items():
        value = decode(raw)
        default = getattr(battle, name)
        if name in COLLECTIONS:
            require(type(value) is list and all(type(v) is COLLECTIONS[name] for v in value))
        elif name == 'selected':
            require(value == selected)
        elif name == 'card_cooldowns':
            require(type(value) is list and len(value) == len(selected) and all(typed(v, float) and v >= 0 for v in value))
        elif name == 'boss_seen':
            require(type(value) is set and all(type(v) is int and 0 <= v <= TOTAL_WAVES for v in value))
        elif name == 'dead_history':
            require(type(value) is list and all(type(v) is tuple and len(v) == 3 and
                    (v[0] in ENEMIES or v[0] in BOSSES) and type(v[1]) is int and 0 <= v[1] < ROWS and typed(v[2], float) for v in value))
        else:
            annotation = float if type(default) in (int, float) and type(default) is not bool else type(default)
            require(typed(value, annotation), 'Estado inválido: ' + name)
        setattr(battle, name, value)
    for name, limit in (('wave', TOTAL_WAVES + 1), ('selected_card', len(selected)),
                        ('keyboard_row', ROWS), ('keyboard_col', COLS)):
        require(type(getattr(battle, name)) is int and 0 <= getattr(battle, name) < limit)
    require(len(battle.lane_bombs) == ROWS and sorted(b.row for b in battle.lane_bombs) == list(range(ROWS)))
    require(len({(d.row, d.col) for d in battle.defenders}) == len(battle.defenders))
    from .content import difficulty_profile
    battle.difficulty_data = difficulty_profile(battle.difficulty)

    # As referências já foram ligadas; os clipes vêm dos recursos confiáveis do jogo.
    for obj, record in zip(objects, records):
        if not isinstance(obj, (Defender, Enemy)):
            continue
        saved = record.get('animation')
        if saved is None:
            continue
        require(type(saved) is dict and set(saved) == set(ANIMATION_FIELDS))
        actor = (DEFENDER_ACTOR_BY_KEY if isinstance(obj, Defender) else ENEMY_ACTOR_BY_KEY).get(obj.key)
        animation = app.assets.new_production_animation(actor) if actor else None
        require(animation is not None and saved['state'] in animation.animations)
        for name in ANIMATION_FIELDS:
            require(typed(saved[name], type(getattr(animation, name))))
        require(0 <= saved['frame_index'] < len(animation.animations[saved['state']].frames))
        require(saved['frame_elapsed'] >= 0 and saved['playback_rate'] >= 0 and saved['loop_count'] >= 0)
        for name in ANIMATION_FIELDS:
            setattr(animation, name, saved[name])
        obj.visual_animation = animation

    scenario = snapshot.get('scenario')
    require(type(scenario) is dict and set(scenario) == set(SCENARIO_FIELDS))
    require(all(typed(v, type(getattr(app.scenario_runtime, k))) for k, v in scenario.items()))
    require(typed(snapshot.get('scene_elapsed'), float) and type(snapshot.get('integration_preview')) is bool)
    rng = decode(snapshot.get('random'))
    random.Random().setstate(rng)  # Valida sem mexer no gerador em uso.
    return battle, rng


def activate(snapshot, app):
    battle, rng = restore(snapshot, app)
    random.setstate(rng)
    for name, value in snapshot['scenario'].items():
        setattr(app.scenario_runtime, name, value)
    app.scene_elapsed = snapshot['scene_elapsed']
    app.integration_preview = snapshot['integration_preview']
    return battle

