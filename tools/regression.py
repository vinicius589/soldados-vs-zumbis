"""Compare the original game and release with deterministic, headless execution.

This is a regression harness, not a human playthrough, FPS benchmark, or hardware
audio/GPU check. Wave progression deliberately removes enemies after checking
their actual spawn. Combat is checked separately using the normal update path.
Only the displayed release version is normalized for image comparisons.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--layout', choices=('original', 'final'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.game_dir = args.game_dir.resolve()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    os.environ['SVZ_RENDERER'] = 'software'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    sys.dont_write_bytecode = True
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Retain isolated test saves as evidence; do not remove game or user files.
    with nullcontext(tempfile.mkdtemp(prefix='isolated-save-', dir=args.output_dir)) as temporary:
        save_path = Path(temporary) / 'campaign.json'
        os.environ['SVZ_SAVE_PATH'] = str(save_path)
        sys.path.insert(0, str(args.game_dir / 'src' if args.layout == 'final' else args.game_dir))
        api = importlib.import_module('svz.api' if args.layout == 'final' else 'main')
        import pygame

        # Labels intentionally change on release; game behavior and art must not.
        for module in list(sys.modules.values()):
            name = getattr(module, '__name__', '')
            if (name == 'main' or name == 'svz' or name.startswith('svz.')) and hasattr(module, 'VERSION'):
                module.VERSION = '1.0.0'

        loaded_images = {}
        image_load = pygame.image.load

        def checked_image_load(file, *load_args, **load_kwargs):
            surface = image_load(file, *load_args, **load_kwargs)
            if isinstance(file, (str, bytes, os.PathLike)):
                path = Path(file)
                content = path.read_bytes()
                assert not content.startswith(b'version https://git-lfs.github.com/spec/v1'), path
                loaded_images[str(path)] = hashlib.sha256(content).hexdigest()
            assert surface.get_width() > 1 and surface.get_height() > 1, str(file)
            assert surface.get_bounding_rect(min_alpha=8).width > 0, str(file)
            return surface

        pygame.image.load = checked_image_load
        random.seed(20261007)
        game = api.Game(integration_preview=False, save_path=save_path)
        for _ in range(game.assets.total + 20):
            game.update(1 / 60)
            if game.scene == 'title':
                break
        assert game.scene == 'title', game.scene
        assert game.assets.complete and not game.assets.error, game.assets.error
        assert game.assets.production_clips
        assert game.audio.ready, game.audio.error
        assert set(game.audio.sounds) == set(game.audio.FILES)
        assert all(sound.get_length() > 0 for sound in game.audio.sounds.values())
        assert game.save == api.make_save(), 'Verification must start with a fresh save'
        report = {'render_hashes': {}, 'combat': {}, 'campaigns': {}, 'navigation': []}

        def surface_ok(surface, label):
            assert surface.get_bounding_rect(min_alpha=8).width > 0, label
            assert surface.get_size() != (1, 1), label

        for key, surface in game.assets.images.items():
            surface_ok(surface, key)
        blank_effect_frames = {}
        for collection_name in ('animation_frames', 'effect_frames', 'boss_portraits'):
            for key, frames in getattr(game.assets, collection_name).items():
                assert frames, (collection_name, key)
                visible = [surface for surface in frames if surface.get_bounding_rect(min_alpha=8).width > 0]
                assert visible, (collection_name, key)
                # A muzzle flash legitimately ends in transparent frames.
                blank_effect_frames[f'{collection_name}/{key}'] = len(frames) - len(visible)
        actor_frames = 0
        for actor, states in game.assets.production_clips.items():
            assert states, actor
            for state, clip in states.items():
                assert clip.frames and clip.duration > 0, (actor, state)
                for surface in clip.frames:
                    surface_ok(surface, (actor, state))
                    actor_frames += 1
        scenario_counts = {}
        for name in ('generals', 'city_lieutenant', 'beach_alarm', 'brazier', 'aquatic_mine', 'land_charge', 'tractor', 'drone', 'splash'):
            frames = getattr(game.scenario_runtime, name)
            assert frames, f'Missing mandatory scenario frames: {name}'
            if name == 'generals':
                assert all(frames), 'Missing regional general'
                frames = [frame for sequence in frames for frame in sequence]
            for surface in frames:
                surface_ok(surface, name)
            scenario_counts[name] = len(frames)

        def snapshot(name):
            game.draw()
            image = pygame.image.tobytes(game.screen, 'RGBA')
            report['render_hashes'][name] = hashlib.sha256(image).hexdigest()
            pygame.image.save(game.screen, str(args.output_dir / f'{name}.png'))

        for scene in ('title', 'difficulty', 'campaign', 'characters', 'story', 'settings', 'howto'):
            game.scene = scene
            game.battle = None
            game.scene_elapsed = 1.25
            snapshot(scene)

        def battle_state(battle):
            return {
                'wave': battle.wave, 'supplies': battle.supplies,
                'finished': battle.finished, 'lost': battle.lost, 'victory': battle.victory,
                'enemies': [[e.key, e.row, round(e.x, 6), round(e.hp, 6),
                             e.visual_animation.state if e.visual_animation else None]
                            for e in battle.enemies],
                'defenders': [[d.key, d.row, d.col, round(d.hp, 6),
                               d.visual_animation.state if d.visual_animation else None]
                              for d in battle.defenders],
                'projectiles': len(battle.projectiles), 'fallen': len(battle.fallen),
            }

        for difficulty_index, difficulty in enumerate(('easy', 'medium', 'hard')):
            for region_index, region in enumerate(('city', 'desert', 'beach')):
                seed = 7100 + difficulty_index * 100 + region_index
                random.seed(seed)
                game.scene = 'title'
                game.handle_key(pygame.K_RETURN)
                assert game.scene == 'difficulty'
                game.handle_key(pygame.K_1 + difficulty_index)
                assert game.scene == 'campaign' and game.difficulty == difficulty
                game.handle_key(pygame.K_1 + region_index)
                assert game.scene == 'battle' and game.battle.region == region
                assert game.battle.difficulty == difficulty
                report['navigation'].append([difficulty, region, len(game.battle.selected)])

                battle = game.battle
                battle.intermission = 9999.0
                battle.supplies = 999
                row = 0 if region == 'beach' else 1
                battle.place(row, 2)
                assert len(battle.defenders) == 1
                defender = battle.defenders[0]
                defender.deployment_x = None
                defender.deployment_target_x = None
                battle.spawn_enemy(api.SpawnOrder(0.0, api.REGION_ENEMIES[region][0], row))
                enemy = battle.enemies[0]
                enemy.entry_reveal = 0.0
                enemy.age = 2.0
                enemy.x = defender.x + float(defender.stats['range']) * api.CELL_W - 1
                enemy_initial_hp = enemy.hp
                trace = []
                game.scene_elapsed = 0.0
                game.scenario_runtime.elapsed = 0.0
                for frame in range(600):
                    game.scene_elapsed += 1 / 60
                    game.update(1 / 60)
                    if frame % 60 == 59:
                        trace.append(battle_state(battle))
                    if frame == 119:
                        snapshot(f'combat_{region}_{difficulty}')
                assert enemy.hp < enemy_initial_hp, f'No attack damage: {region}/{difficulty}'

                # Prove actual damage in the opposite direction independently.
                bite = api.Battle(game, region, list(api.REGION_ROSTERS[region]))
                bite.supplies = 999
                bite.intermission = 9999
                bite.place(row, 2)
                victim = bite.defenders[0]
                victim.deployment_x = None
                victim.deployment_target_x = None
                victim.attack_timer = 999
                bite.spawn_enemy(api.SpawnOrder(0.0, api.REGION_ENEMIES[region][0], row))
                attacker = bite.enemies[0]
                attacker.entry_reveal = 0.0
                attacker.age = 2.0
                attacker.x = victim.x + 44
                attacker.attack_timer = 0
                before = victim.hp
                for _ in range(120):
                    bite.update(1 / 60)
                assert victim.hp < before, f'No bite damage: {region}/{difficulty}'
                report['combat'][f'{region}_{difficulty}'] = {
                    'enemy_hp_before': enemy_initial_hp, 'enemy_hp_after': enemy.hp,
                    'defender_hp_before_bite': before, 'defender_hp_after_bite': victim.hp,
                    'trace': trace,
                }

                # Exercise the real director, including its warning before every
                # boss. Enemies are removed only AFTER spawn has been recorded.
                random.seed(seed + 1000)
                waves = api.Battle(game, region, list(api.REGION_ROSTERS[region]))
                game.battle = waves
                waves.intermission = 0
                records = []
                for wave in range(1, api.TOTAL_WAVES + 1):
                    for _ in range(150):
                        waves.update_wave(0.05)
                        if waves.started_wave:
                            break
                    assert waves.wave == wave and waves.started_wave
                    orders = [asdict(order) for order in waves.orders]
                    assert orders
                    expected_boss = api.REGION_BOSSES[region][(wave - 1) // 4] if wave % 4 == 0 else None
                    expected_subboss = api.REGION_SUBBOSSES[region][(wave - 1) // 4] if wave % 4 == 3 else None
                    boss_orders = [order for order in waves.orders if order.boss]
                    assert [order.key for order in boss_orders] == ([expected_boss] if expected_boss else [])
                    if expected_subboss:
                        assert expected_subboss in [order.key for order in waves.orders]
                    warning_seen = False
                    for _ in range(3000):
                        waves.boss_warning = max(0.0, waves.boss_warning - 0.05)
                        waves.update_wave(0.05)
                        warning_seen |= waves.boss_alert_pending
                        if not waves.orders:
                            break
                    assert not waves.orders, f'Wave stalled: {region}/{difficulty}/{wave}'
                    spawned_keys = [enemy.key for enemy in waves.enemies]
                    assert spawned_keys[:len(orders)] == [order['key'] for order in orders]
                    expected_extra = ['necromante_minion'] if expected_boss and api.BOSSES[expected_boss].get('type') == 'necromante' else []
                    assert spawned_keys[len(orders):] == expected_extra
                    if expected_boss:
                        assert warning_seen
                        boss = next(enemy for enemy in waves.enemies if enemy.key == expected_boss)
                        assert boss.is_boss and boss.hp > 0 and boss.boss_announced
                        if difficulty == 'medium':
                            for index, enemy in enumerate(waves.enemies):
                                enemy.x = 740 + (index % 4) * 90
                                enemy.entry_reveal = 0
                            game.scene_elapsed = 1.25
                            game.scenario_runtime.elapsed = 1.25
                            waves.shake = 0
                            snapshot(f'boss_{region}_{wave:02d}')
                    records.append({'wave': wave, 'orders': orders, 'warning_seen': warning_seen,
                                    'spawned': [[enemy.key, enemy.row, round(enemy.hp, 6)] for enemy in waves.enemies]})
                    waves.enemies.clear()
                    waves.update_wave(0.05)
                    if wave < api.TOTAL_WAVES:
                        assert not waves.started_wave and not waves.finished
                assert waves.finished and waves.victory and not waves.lost
                report['campaigns'][f'{region}_{difficulty}'] = records
                if difficulty == 'medium':
                    snapshot(f'victory_{region}')
                game.finish_battle()
                assert game.scene == 'campaign' and not game.save_error
                assert region in game.save['completed']
                assert api.load_save(save_path) == game.save

        report['save_roundtrip'] = api.load_save(save_path)
        assert set(report['save_roundtrip']['completed']) == set(api.REGIONS)
        assert all(value == api.TOTAL_WAVES for value in report['save_roundtrip']['best_wave'].values())
        report['assets'] = {
            'images_loaded': len(loaded_images),
            'image_content_sha256': sorted(loaded_images.values()),
            'actors': len(game.assets.production_clips), 'actor_frames': actor_frames,
            'blank_effect_frames': blank_effect_frames,
            'scenario_frames': scenario_counts,
            'audio_keys': sorted(game.audio.sounds),
            'audio_content_sha256': sorted(hashlib.sha256((api.AUDIO_DIR / filename).read_bytes()).hexdigest()
                                           for filename, _volume in game.audio.FILES.values()),
        }
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        game.handle_events()
        assert not game.running, 'Window-close event must terminate the loop'
        pygame.quit()
        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
        (args.output_dir / 'report.json').write_text(serialized, encoding='utf-8')
        print(json.dumps({'status': 'passed', 'layout': args.layout,
                          'screenshots': len(report['render_hashes']),
                          'campaigns': len(report['campaigns']),
                          'waves_spawned': sum(len(v) for v in report['campaigns'].values()),
                          'combat_scenarios': len(report['combat']),
                          'images_loaded': report['assets']['images_loaded'],
                          'actors': report['assets']['actors'],
                          'report_sha256': hashlib.sha256(serialized.encode()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
