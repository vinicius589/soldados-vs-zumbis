"""Exporta todo o elenco usando o renderizador e os cenários do jogo real.

Cada faixa de revisão é desenhada por ``Game.draw`` dentro de uma ``Battle``.
Assim, escala, pivô, terreno, sombra, barra de vida, clarão de tiro e efeitos de
habilidade são exatamente os usados durante a partida — não uma colagem externa
de sprites sobre fundo neutro.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SVZ_RENDERER", "software")

import pygame
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import (
    BEACH_WATER_DEFENDERS,
    BEACH_WATER_ENEMIES,
    BOSSES,
    BOARD,
    CELL_W,
    DEFENDER_ACTOR_BY_KEY,
    ENEMIES,
    ENEMY_ACTOR_BY_KEY,
    REGION_BOSSES,
    REGION_ENEMIES,
    REGION_ROSTERS,
    REGION_SUBBOSSES,
    Battle,
    Projectile,
    VisualEffect,
    Game,
    SpawnOrder,
    cell_center,
    defender_weapon_origin,
)
from visual_layout import DEFENDER_WEAPON_PROFILES


OUTPUT = ROOT / "visual_qa_beta4" / "elenco_no_jogo"
REGION_LABELS = {
    "city": "NOVA YORK",
    "desert": "EGITO",
    "beach": "MINAS GERAIS",
}
CROP_SIZE = (310, 196)
HEADER = 30


def _font(size: int) -> ImageFont.ImageFont:
    """Fonte Unicode para que nomes portugueses não saiam corrompidos."""
    for candidate in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _world_image(game: Game) -> Image.Image:
    raw = pygame.image.tobytes(game.world_surface, "RGB")
    return Image.frombytes("RGB", game.world_surface.get_size(), raw)


def _actor_crop(game: Game, x: float, y: float, caption: str) -> Image.Image:
    game.draw()
    world = _world_image(game)
    left = round(x - CROP_SIZE[0] / 2)
    top = round(y - CROP_SIZE[1] + 28)
    crop = world.crop((left, top, left + CROP_SIZE[0], top + CROP_SIZE[1]))
    panel = Image.new("RGB", (CROP_SIZE[0], CROP_SIZE[1] + HEADER), (9, 15, 20))
    panel.paste(crop, (0, HEADER))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, panel.width, HEADER), fill=(9, 15, 20))
    draw.text((8, 7), caption, fill=(240, 211, 119), font=_font(12))
    return panel


def _valid_defender_row(battle: Battle, key: str) -> int:
    preferred = (1, 2, 0, 3) if key in BEACH_WATER_DEFENDERS else (0, 3, 1, 2)
    for row in preferred:
        if battle.can_place(key, row, 3)[0]:
            return row
    raise AssertionError(f"nenhuma faixa válida para {key}")


def _defender_review(
    game: Game,
    region: str,
    key: str,
    display: str,
    *,
    show_projectile_origin: bool = False,
) -> tuple[list[Image.Image], list[int], list[Image.Image]]:
    battle = Battle(game, region, [(key, display)])
    battle.intermission = 9999.0
    battle.supplies = 9999
    row = _valid_defender_row(battle, key)
    battle.selected_card = 0
    battle.place(row, 3)
    defender = battle.defenders[-1]
    defender.deployment_x = None
    defender.deployment_target_x = None
    defender.attack_timer = 9999.0
    game.region, game.battle, game.scene = region, battle, "battle"
    animation = defender.visual_animation
    assert animation is not None
    states = (
        (("move", "ENTRADA"), ("support", "HABILIDADE"), ("idle", "PRONTO"), ("hit", "DANO"))
        if "support" in animation.animations
        else (("move", "ENTRADA"), ("shoot", "DISPARO"), ("reload", "RECARGA"), ("hit", "DANO"))
    )
    gif_frames: list[Image.Image] = []
    gif_durations: list[int] = []
    representative: list[Image.Image] = []
    motion_state = {
        "move": "walk",
        "idle": "idle",
        "shoot": "attack",
        "reload": "reload",
        "hit": "hit",
        "support": "support",
    }
    for state, label in states:
        animation.play(state, restart=True)
        clip = animation.animations[state]
        for index in range(len(clip.frames)):
            animation.seek_frame(index)
            defender.motion.state = motion_state[state]
            defender.motion.state_elapsed = sum(clip.frame_durations[:index])
            defender.motion.event_left = max(0.08, clip.duration - defender.motion.state_elapsed)
            if state == "reload":
                defender.ammo = 0
                defender.reload_total = clip.duration
                defender.reload_timer = max(0.05, clip.duration - defender.motion.state_elapsed)
            else:
                defender.ammo = defender.max_ammo
                defender.reload_timer = 0.0
                defender.reload_total = 0.0
            battle.projectiles.clear()
            battle.effects.clear()
            role = str(defender.stats["role"])
            if state == "shoot" and (
                role in {"flame", "waterjet", "poison", "gas_grenade"}
                or show_projectile_origin
            ):
                profile = DEFENDER_WEAPON_PROFILES.get(defender.key)
                kind = profile.projectile_kind if profile else {
                    "rifle": "rifle",
                    "heavy": "rifle",
                    "shotgun": "shotgun",
                    "sniper": "sniper",
                    "grenade": "grenade",
                    "mortar": "mortar",
                    "rocket": "bazooka",
                    "flame": "flame",
                    "waterjet": "waterjet",
                    "poison": "poison",
                    "gas_grenade": "gas_grenade",
                    "boat": "boat",
                    "sub": "torpedo",
                }.get(role)
                if kind is None:
                    frame = _actor_crop(game, defender.x, defender.y, f"{display} | {label} | {index + 1}/{len(clip.frames)}")
                    gif_frames.append(frame)
                    gif_durations.append(max(85, round(clip.frame_durations[index] * 1000)))
                    if index == len(clip.frames) // 2:
                        representative.append(frame.copy())
                    continue
                origin_x, origin_y = defender_weapon_origin(defender)
                progress = (
                    0.0
                    if show_projectile_origin
                    and kind not in {"flame", "waterjet", "poison"}
                    else (index + 1) / len(clip.frames)
                )
                if kind == "gas_grenade" and progress > 0.64:
                    cloud_progress = (progress - 0.64) / 0.36
                    battle.effects.append(
                        VisualEffect(
                            "toxic_wave", origin_x + 145, defender.y - 8,
                            (132, 239, 80), 1.05,
                            elapsed=cloud_progress * 1.05,
                            scale=1.08,
                        )
                    )
                else:
                    flight_progress = progress / 0.64 if kind == "gas_grenade" else progress
                    battle.projectiles.append(
                        Projectile(
                            origin_x,
                            origin_y,
                            None,
                            origin_x + 145,
                            defender.y - 10 if kind == "gas_grenade" else origin_y,
                            0,
                            kind,
                            defender,
                            travel=1.0,
                            elapsed=min(1.0, flight_progress),
                        )
                    )
            frame = _actor_crop(game, defender.x, defender.y, f"{display} | {label} | {index + 1}/{len(clip.frames)}")
            gif_frames.append(frame)
            gif_durations.append(max(85, round(clip.frame_durations[index] * 1000)))
            if index == len(clip.frames) // 2:
                representative.append(frame.copy())
    return gif_frames, gif_durations, representative


def _enemy_row(region: str, key: str, boss: bool) -> int:
    if region != "beach":
        return 1
    if boss or key in BEACH_WATER_ENEMIES or ENEMIES.get(key, {}).get("amphibious"):
        return 1
    return 3


def _enemy_review(
    game: Game,
    region: str,
    key: str,
    *,
    boss: bool,
    show_target: bool = False,
) -> tuple[list[Image.Image], list[int], list[Image.Image]]:
    # Um defensor real fica fora do recorte para que projéteis, redes, ácido e
    # outras habilidades tenham um alvo válido durante a demonstração.
    target_key, target_display = REGION_ROSTERS[region][0]
    if region == "beach" and (boss or key in BEACH_WATER_ENEMIES):
        target_key, target_display = next(
            item for item in REGION_ROSTERS[region] if item[0] == "barco_patrulha"
        )
    battle = Battle(game, region, [(target_key, target_display)])
    battle.intermission = 9999.0
    battle.supplies = 9999
    row = _enemy_row(region, key, boss)
    battle.selected_card = 0
    battle.place(row, 1)
    defender = battle.defenders[-1]
    defender.deployment_x = None
    defender.deployment_target_x = None
    defender.attack_timer = 9999.0
    battle.spawn_enemy(SpawnOrder(0.0, key, row, boss))
    # O Necromante invoca uma escolta na entrada; nesse caso o último item da
    # lista não é o chefe que estamos revisando. Selecionar pela chave mantém
    # a captura presa ao ator solicitado.
    enemy = next(candidate for candidate in reversed(battle.enemies) if candidate.key == key)
    enemy.entry_reveal = 0.0
    enemy.age = 2.0
    enemy.x = cell_center(row, 4, region)[0] + CELL_W * 0.56
    if show_target:
        # A revisão da interação precisa mostrar emissor, trajetória, alvo e
        # impacto no mesmo quadro. Antes o alvo ficava deliberadamente fora do
        # recorte e uma habilidade correta parecia simplesmente ausente.
        desired_x = enemy.x - 115.0
        defender.col = (desired_x - BOARD.left) / CELL_W - 0.5
        if key == "curandeiro":
            # Cura só é compreensível quando existe um aliado ferido recebendo
            # o efeito. A prévia anterior mostrava apenas uma cruz sobre o
            # emissor e parecia uma animação vazia.
            # Usa um infectado de superfície: o Escavador inicia parte do seu
            # ciclo enterrado e deixava só a sombra aparecer na prévia, o que
            # escondia justamente quem estava recebendo a cura.
            battle.spawn_enemy(SpawnOrder(0.0, "desperto_khepra", row, False))
            healed = battle.enemies[-1]
            healed.entry_reveal = 0.0
            healed.age = 2.0
            healed.x = enemy.x + 82.0
            healed.hp = max(1.0, healed.max_hp - 60.0)
    enemy.skill_timer = 9999.0
    game.region, game.battle, game.scene = region, battle, "battle"
    animation = enemy.visual_animation
    assert animation is not None, f"ator visual ausente: {region}:{key}"
    display = str((BOSSES if boss else ENEMIES)[key]["name"])
    states = (("move", "LOCOMOÇÃO"), ("bite", "ATAQUE"), ("hit", "DANO"), ("skill", "HABILIDADE"))
    motion_state = {"move": "walk", "bite": "attack", "hit": "hit", "skill": "skill"}
    gif_frames: list[Image.Image] = []
    gif_durations: list[int] = []
    representative: list[Image.Image] = []
    for state, label in states:
        battle.effects.clear()
        battle.projectiles.clear()
        if state == "skill":
            if boss:
                battle.boss_skill(enemy)
            else:
                battle.enemy_special(enemy)
        animation.play(state, restart=True)
        clip = animation.animations[state]
        for index in range(len(clip.frames)):
            animation.seek_frame(index)
            enemy.motion.state = motion_state[state]
            enemy.motion.state_elapsed = sum(clip.frame_durations[:index])
            enemy.motion.event_left = max(0.08, clip.duration - enemy.motion.state_elapsed)
            if state == "skill":
                progress = (index + 1) / len(clip.frames)
                for effect in battle.effects:
                    effect.elapsed = min(effect.duration * 0.96, effect.duration * progress)
                for projectile in battle.projectiles:
                    projectile.elapsed = min(projectile.travel * 0.96, projectile.travel * progress)
            crop_x = enemy.x - 25.0 if show_target else enemy.x
            frame = _actor_crop(game, crop_x, enemy.y, f"{display} | {label} | {index + 1}/{len(clip.frames)}")
            gif_frames.append(frame)
            gif_durations.append(max(95, round(clip.frame_durations[index] * 1000)))
            if index == len(clip.frames) // 2:
                representative.append(frame.copy())
    return gif_frames, gif_durations, representative


def _save_gif(frames: list[Image.Image], durations: list[int], path: Path) -> None:
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
        disposal=2,
    )


def _save_montage(title: str, rows: list[tuple[str, list[Image.Image]]], path: Path) -> None:
    columns = 4
    cell_w, cell_h = CROP_SIZE[0], CROP_SIZE[1] + HEADER
    top = 48
    canvas = Image.new("RGB", (cell_w * columns, top + cell_h * len(rows)), (8, 14, 19))
    draw = ImageDraw.Draw(canvas)
    draw.text((14, 13), title, fill=(244, 207, 103), font=_font(18))
    for row_index, (_label, frames) in enumerate(rows):
        for column, frame in enumerate(frames):
            canvas.paste(frame, (column * cell_w, top + row_index * cell_h))
    canvas.save(path)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    game = Game(integration_preview=True)
    while not game.assets.complete:
        game.assets.load_next()
    game.assets.prepare_production_animations()
    manifest = [
        "REVISÃO DO ELENCO DENTRO DO JOGO",
        "24 soldados: entrada/ação/recarga ou prontidão/dano",
        "36 zumbis: locomoção/ataque/dano/habilidade",
        "",
    ]

    for region in ("city", "desert", "beach"):
        region_dir = OUTPUT / region
        soldier_dir = region_dir / "soldados"
        enemy_dir = region_dir / "zumbis"
        soldier_dir.mkdir(parents=True, exist_ok=True)
        enemy_dir.mkdir(parents=True, exist_ok=True)

        soldier_rows: list[tuple[str, list[Image.Image]]] = []
        for key, display in REGION_ROSTERS[region]:
            frames, durations, samples = _defender_review(game, region, key, display)
            _save_gif(frames, durations, soldier_dir / f"{key}.gif")
            soldier_rows.append((display, samples))
            manifest.append(f"{region} SOLDADO {key}: {DEFENDER_ACTOR_BY_KEY[key]}")
        _save_montage(
            f"{REGION_LABELS[region]} — TODOS OS SOLDADOS NO JOGO",
            soldier_rows,
            region_dir / f"soldados_{region}_implementados.png",
        )

        enemy_rows: list[tuple[str, list[Image.Image]]] = []
        enemy_keys = (
            tuple((key, False) for key in REGION_ENEMIES[region])
            + tuple((key, False) for key in REGION_SUBBOSSES[region])
            + tuple((key, True) for key in REGION_BOSSES[region])
        )
        for key, boss in enemy_keys:
            frames, durations, samples = _enemy_review(game, region, key, boss=boss)
            _save_gif(frames, durations, enemy_dir / f"{key}.gif")
            display = str((BOSSES if boss else ENEMIES)[key]["name"])
            enemy_rows.append((display, samples))
            manifest.append(f"{region} ZUMBI {key}: {ENEMY_ACTOR_BY_KEY[key]}")
        _save_montage(
            f"{REGION_LABELS[region]} — TODOS OS ZUMBIS NO JOGO",
            enemy_rows,
            region_dir / f"zumbis_{region}_implementados.png",
        )

    (OUTPUT / "MANIFESTO.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    pygame.quit()
    print(f"ELENCO_NO_JOGO_EXPORTADO: {OUTPUT}")


if __name__ == "__main__":
    main()
