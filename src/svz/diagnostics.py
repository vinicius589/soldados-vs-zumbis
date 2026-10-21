"""Verifica o próprio executável com recursos reais, sem gravar progresso."""
import hashlib
import json
from pathlib import Path
import random
import tempfile


def verify(output: str) -> None:
    import pygame
    from .app import Game
    from .battle import Battle
    from .content import REGIONS, REGION_ROSTERS, REGION_BOSSES
    from .paths import ROOT
    from .config import VERSION

    report = {'version': VERSION, 'images': {}, 'regions': {}, 'renderer': '', 'audio_ready': False}
    destination = Path(output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    assets = json.loads((ROOT / 'assets/manifest.json').read_text(encoding='utf-8'))
    for relative, expected in assets.items():
        data = (ROOT / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected['sha256'], relative
    report['verified_assets'] = len(assets)
    with tempfile.TemporaryDirectory(prefix='svz-diagnostic-', dir=destination.parent) as temporary:
        game = Game(save_path=Path(temporary) / 'campaign.json')
        try:
            while not game.assets.complete:
                game.assets.load_next()
            assert not game.assets.error, game.assets.error
            game.assets.prepare_production_animations()
            assert game.audio.ready, game.audio.error
            report['audio_ready'] = game.audio.ready
            report['renderer'] = game.renderer_label
            game.audio.set_enabled(False)
            for scene in ('title', 'campaign', 'characters', 'story', 'settings', 'bindings', 'howto'):
                game.scene = scene
                game.draw()
                game.present_frame()
                report['images'][scene] = hashlib.sha256(pygame.image.tobytes(game.screen, 'RGB')).hexdigest()
            for region in REGIONS:
                random.seed(731)
                game.enter_selection(region)
                battle = Battle(game, region, list(REGION_ROSTERS[region]))
                game.battle = battle
                game.scene = 'battle'
                battle.supplies = 999
                battle.place(0, 2)
                battle.start_next_wave()
                for _ in range(120):
                    game.update(1 / 60)
                    game.handle_events()
                    game.draw()
                    game.present_frame()
                bosses = [next(order.key for order in battle.build_wave(wave) if order.boss) for wave in (4, 8, 12)]
                assert bosses == list(REGION_BOSSES[region])
                report['regions'][region] = {'wave': battle.wave, 'bosses': bosses, 'defenders': len(battle.defenders)}
                assert battle.defenders
            report['removal'] = verify_removal(game, destination)
            report['video'] = verify_video(game, destination)
            report['review'] = verify_review(game)
            report['runners'] = verify_runners(game, destination.parent)
            assert len(game.scenario_runtime.tractor) == 8
            assert len(game.scenario_runtime.drone) == 8
            assert len(game.scenario_runtime.splash) == 8
        finally:
            if game.presenter is not None:
                game.presenter.close()
            pygame.quit()
    from .version import BUILD_INFO
    report['build'] = BUILD_INFO
    report['ok'] = True
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def verify_runners(game, output_dir: Path) -> dict:
    """Confere a corrida real e as poses do EXE, inclusive após retomar."""
    import math
    import pygame
    from .entities import SpawnOrder
    from .snapshot import capture, activate

    def faces_left(frame):
        bounds = frame.get_bounding_rect(min_alpha=8)
        head = frame.subsurface(pygame.Rect(bounds.x, bounds.y, bounds.width, bounds.height // 4))
        mask = pygame.mask.from_surface(head, threshold=8)
        return mask.count() > 20 and mask.centroid()[0] < bounds.width / 2

    results = {}
    for region, key in (("city", "corredor_cidade"), ("desert", "corredor_deserto"),
                        ("beach", "corredor_cachoeira")):
        clip = game.assets.production_clips[f"{region}_runner_v2"]["move"]
        assert len(clip.frames) == 8 and all(faces_left(f) for f in clip.frames), region
        for difficulty in ("easy", "medium", "hard"):
            game.difficulty = difficulty
            game.enter_selection(region)
            battle = game.battle
            battle.intermission = 9999
            battle.spawn_enemy(SpawnOrder(0, key, 0))
            enemy = battle.enemies[-1]
            enemy.x, enemy.age, enemy.entry_reveal = 950.0, 2.0, 0.0
            initial_x = enemy.x
            seen = set()
            for _ in range(360):
                previous_x = enemy.x
                battle.update(1/60)
                assert enemy.x < previous_x, (region, difficulty, "direção")
                assert enemy.visual_animation.state in {"move", "skill"}, (
                    region, difficulty, enemy.motion.state, enemy.visual_animation.state)
                assert faces_left(enemy.visual_animation.frame), (region, difficulty, "pose")
                if enemy.visual_animation.state == "move":
                    seen.add(enemy.visual_animation.frame_index)
            assert seen == set(range(8)), (region, difficulty, seen)
            assert math.isclose(initial_x-enemy.x, float(enemy.data["speed"])*6, abs_tol=1e-6)
            battle.paused = True
            paused = capture(battle)
            battle.update(.5)
            assert capture(battle) == paused
            game.battle = activate(paused, game)
            assert capture(game.battle) == paused
            assert faces_left(game.battle.enemies[0].visual_animation.frame)
            game.battle.paused = False
            game.battle.update(1/60)
            game.draw()
            game.present_frame()
            if difficulty == "medium":
                pygame.image.save(game.screen, str(output_dir / f"runner-{region}.png"))
            results[f"{region}/{difficulty}"] = {
                "faces_base": True, "frames_seen": sorted(seen), "constant_speed": True,
                "pause_and_resume": True, "steps": 360}
    return results


def verify_resume(output: str, campaign_path: str) -> None:
    """Ensaio em outro processo, sem modificar o save fornecido."""
    import pygame
    from .app import Game
    from .snapshot import capture
    from .config import VERSION
    destination = Path(output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    game = Game(save_path=Path(campaign_path))
    try:
        while not game.assets.complete:
            game.assets.load_next()
        game.assets.prepare_production_animations()
        assert not game.assets.error, game.assets.error
        assert game.pending_snapshot is not None, game.session_notice
        expected = game.pending_snapshot
        expected['battle']['paused'] = not expected['battle']['finished']
        game.scene = 'title'
        game.draw()
        pygame.image.save(game.screen, str(destination.with_suffix('.menu.png')))
        assert game.resume_battle(), game.session_notice
        restored = capture(game.battle)
        assert restored == expected, 'Estado restaurado diverge do arquivo.'
        game.draw()
        pygame.image.save(game.screen, str(destination.with_suffix('.partida.png')))
        game.battle.paused = False
        for _ in range(120):
            game.battle.update(1 / 60)
            game.draw()
        report = {'version': VERSION, 'region': game.region,
                  'difficulty': game.difficulty, 'restored_exact_state': True,
                  'resumed_paused': restored['battle']['paused'],
                  'continued_steps': 120, 'fullscreen': game.video.fullscreen,
                  'window_size': list(pygame.display.get_window_size()), 'ok': True}
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        if game.presenter is not None:
            game.presenter.close()
        pygame.quit()


def verify_removal(game, destination: Path) -> dict:
    """Exercita o controle e a retomada com o código do próprio executável."""
    import math
    import pygame
    from .content import REGIONS

    results = {}
    for region in REGIONS:
        for difficulty in ("easy", "medium", "hard"):
            game.difficulty = difficulty
            game.control_mode = "mouse"
            game.enter_selection(region)
            battle = game.battle
            battle.supplies = 999
            battle.place(0, 2)
            assert len(battle.defenders) == 1
            battle.defenders[0].deployment_x = None
            before = battle.supplies
            refund = math.ceil(battle.defenders[0].stats["cost"] * .35)
            game.draw()
            game.present_frame()
            if difficulty == "easy":
                pygame.image.save(game.screen, str(destination.with_suffix(f".{region}-facil.png")))
            game.handle_click(battle.remove_rect().center)
            assert battle.remove_mode, (region, difficulty, "botão")
            game.handle_key(pygame.K_r)
            assert not battle.remove_mode, (region, difficulty, "atalho")
            game.handle_key(pygame.K_r)
            game.leave_battle_to_title()
            game.battle = None
            game.pending_snapshot = game.session_store.load()
            assert game.resume_battle(), game.session_notice
            battle = game.battle
            assert battle.paused and battle.remove_mode
            game.handle_click(battle.pause_rect().center)
            game.handle_click(battle.ground_cell_rect(0, 2).center)
            assert not battle.defenders, (region, difficulty, "remoção")
            assert battle.supplies == before + refund, (region, difficulty, "reembolso")
            game.handle_click(battle.ground_cell_rect(0, 2).center)
            assert battle.supplies == before + refund, "Reembolso duplicado."
            results[f"{region}/{difficulty}"] = {"button": True, "shortcut": True,
                                                "resumed_removal": True, "refund_once": True}
    return results


def verify_video(game, destination: Path) -> dict:
    """Alterna os modos e verifica cliques reais na fila SDL, sem usar saves pessoais."""
    import pygame
    from .config import WIDTH, HEIGHT
    from .content import REGIONS
    from .snapshot import capture
    from .video import fit_viewport

    if game.video.fullscreen:
        assert game.toggle_fullscreen()
    desktop = list(pygame.display.get_desktop_sizes())
    window_size = pygame.display.get_window_size()
    results = {}
    for region in REGIONS:
        game.difficulty = "easy"
        game.enter_selection(region)
        battle = game.battle
        before = capture(battle)
        game.handle_key(pygame.K_F11)
        assert game.video.fullscreen and pygame.display.is_fullscreen()
        assert capture(battle) == before
        assert game.world_surface.get_size() == (WIDTH, HEIGHT)
        viewport = fit_viewport(pygame.display.get_window_size())

        def click(point):
            physical = (viewport.x + round(point[0] * viewport.width / WIDTH),
                        viewport.y + round(point[1] * viewport.height / HEIGHT))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=physical, button=1))
            game.handle_events()

        click(battle.ground_cell_rect(0, 2).center)
        assert len(battle.defenders) == 1, (region, "posicionar")
        battle.defenders[0].deployment_x = None
        battle.start_next_wave()
        for _ in range(30):
            game.update(1 / 60)
            game.draw()
            game.present_frame()
        assert battle.wave == 1 and battle.started_wave
        if game.presenter is None:
            pygame.image.save(pygame.display.get_surface(), str(destination.with_suffix(f".{region}-fullscreen.png")))
        click(battle.remove_rect().center)
        assert battle.remove_mode
        click(battle.ground_cell_rect(0, 2).center)
        assert not battle.defenders, (region, "remover")
        before = capture(battle)
        game.handle_key(pygame.K_RETURN, pygame.KMOD_ALT)
        assert not game.video.fullscreen and not pygame.display.is_fullscreen()
        assert capture(battle) == before
        assert pygame.display.get_window_size() == window_size
        game.draw()
        game.present_frame()
        results[region] = {"roundtrip": True, "input_mapping": True, "state_preserved": True}
    game.scene = "settings"
    game.handle_click(game.settings_video_rect().center)
    assert game.video.fullscreen
    game.draw()
    game.present_frame()
    if game.presenter is None:
        pygame.image.save(pygame.display.get_surface(), str(destination.with_suffix(".settings-fullscreen.png")))
    game.handle_click(game.settings_video_rect().center)
    assert not game.video.fullscreen
    assert pygame.display.get_desktop_sizes() == desktop
    return {"driver": pygame.display.get_driver(), "desktop_sizes": desktop,
            "window_size": window_size, "logical_size": [WIDTH, HEIGHT],
            "settings_button": True, "regions": results}


def verify_review(game):
    """Valida as correções críticas com os módulos congelados no executável."""
    import pygame
    from .content import REGIONS, DIFFICULTIES
    from .snapshot import capture
    from .settings import Settings

    cases = {}
    for region in REGIONS:
        for difficulty in DIFFICULTIES:
            for mode in ("mouse", "keyboard"):
                game.control_mode = mode
                game.difficulty = difficulty
                game.enter_selection(region)
                b = game.battle
                b.supplies = 999
                def place(col):
                    if mode == "mouse":
                        game.handle_click(b.ground_cell_rect(0, col).center)
                    else:
                        b.keyboard_row, b.keyboard_col = 0, col
                        game.handle_key(pygame.K_RETURN)
                place(2)
                before = b.supplies
                place(4)
                assert len(b.defenders) == 1 and b.supplies == before
                game.handle_key(pygame.K_p)
                paused = capture(b)
                for key in (pygame.K_n, pygame.K_TAB, pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                    game.handle_key(key)
                game.update(1)
                assert capture(b) == paused
                b.finished = b.lost = True
                b.wave = 5
                game.handle_key(pygame.K_RETURN)
                assert game.scene == "campaign" and game.battle is None
                assert game.save["by_difficulty"][difficulty][region]["best_wave"] >= 5
                cases[f"{region}/{difficulty}/{mode}"] = True
    game.control_mode = "keyboard"
    game.settings.assign("pause", pygame.K_z)
    game.settings.music = .4
    game.audio.set_volume(.2)
    game.audio.set_enabled(False)
    game.save_settings()
    loaded = Settings(game.save_path)
    assert loaded.control_mode == "keyboard" and not loaded.sound
    assert loaded.volume == .2 and loaded.music == .4 and loaded.bindings["pause"] == pygame.K_z
    return {"cases": cases, "preferences": True}
