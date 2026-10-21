"""Elenco regional detalhado da Beta 4, normalizado para o jogo real.

Cada região possui um elenco completo de defensores e doze ameaças próprias:
seis comuns, três subchefes e três chefes. Todas as folhas usam uma caixa comum
por ator, pivô estável e troca de quadros por ``dt``. As folhas detalhadas
aprovadas voltaram a ser a fonte; o código apenas corrige recorte e continuidade.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from animation2d import AnimationClip, AnimationManager, SpriteSheet


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "beta4_producao"

ACTOR_SHEETS = {
    "city_guard": ("sheriff_deagle_8x5_v2.png", "soldier"),
    "desert_guard": ("desert_pistol_magnum_8x5_v4.png", "soldier"),
    "beach_guard": ("beach_sailor_glock_8x5_v7.png", "soldier"),
    "city_zombie": ("infectado_urbano_8x4_v1.png", "zombie"),
    "desert_zombie": ("desperto_khepra_8x4_v1.png", "zombie"),
    "beach_zombie": ("afogado_veu_verde_8x4_v1.png", "zombie"),
    "city_auto": ("swat_mp5_8x5_v2.png", "soldier"),
    "desert_auto": ("desert_scar_8x5_v3.png", "soldier"),
    "beach_auto": ("beach_m16_8x5_v4.png", "soldier"),
    "city_radio": ("operador_radio_policial_8x5_v1.png", "support"),
    "desert_radio": ("torre_radio_egito_8x5_v1.png", "support"),
    "beach_radio": ("estacao_comunicacao_cachoeira_8x5_v1.png", "support"),
    "city_sniper": ("city_sniper_awm_8x5_v1.png", "soldier"),
    "city_entry": ("city_entry_spas12_8x5_v1.png", "soldier"),
    "city_antiplague": ("city_antiplague_8x5_v1.png", "soldier"),
    "city_rocket": ("city_rocket_rpg7_8x5_v1.png", "soldier"),
    "city_shield": ("city_riot_shield_8x5_v3.png", "soldier"),
    "desert_sniper": ("desert_sniper_svd_8x5_v1.png", "soldier"),
    "desert_heavy": ("desert_mg3_8x5_v1.png", "soldier"),
    "desert_incinerator": ("desert_incinerator_8x5_v1.png", "soldier"),
    "desert_mortar": ("desert_mortar_8x5_v1.png", "soldier"),
    "desert_blade": ("desert_blade_guard_8x5_v3.png", "soldier"),
    "beach_sniper": ("beach_sniper_trg42_8x5_v1.png", "soldier"),
    "beach_waterjet": ("beach_waterjet_8x5_v1.png", "soldier"),
    "beach_grenadier": ("beach_grenadier_m32_8x5_v1.png", "soldier"),
    "beach_bomber": ("homem_bomba_8x5_v3.png", "soldier"),
    "beach_sonar": ("beach_sonar_station_8x5_v2.png", "soldier"),
    "beach_boat": ("beach_patrol_boat_8x5_v2.png", "soldier"),
    "beach_sub": ("beach_tactical_sub_8x5_v3.png", "soldier"),
    "city_runner": ("corredor_cidade_8x4_v1.png", "runner"),
    "desert_runner": ("corredor_deserto_8x4_v1.png", "runner"),
    "beach_runner": ("corredor_cachoeira_8x4_v1.png", "runner"),
    "city_crawler": ("rastejador_cidade_8x4_v2.png", "crawler"),
    "desert_crawler": ("rastejador_deserto_8x4_v1.png", "crawler"),
    "beach_crawler": ("rastejador_cachoeira_8x4_v2.png", "crawler"),
}

# As folhas individuais 8x5 voltam a ser a fonte visual oficial. Elas têm
# desenho mais detalhado e oito quadros completos por estado. A folha 8x8
# simplificada ampliava poucos pixels no campo, achatava ações diferentes em
# quatro poses e fazia o elenco parecer inconsistente entre regiões.
DEFENDER_ROSTER_ROWS: dict[str, tuple[str, int, str]] = {}


# Elenco inimigo reconstruído do zero. Cada linha agora possui dezesseis
# poses próprias: quatro para locomoção, quatro para ataque, quatro para dano
# e quatro para a habilidade exclusiva. Nenhuma ação precisa reciclar um
# quadro de outra ação, e o pivô físico permanece estável na troca de estado.
ENEMY_ROSTER_ROWS: dict[str, tuple[str, int, str]] = {
    # Nova York / Félix-13
    "city_zombie_v2": ("city_zombies_hd_16x6_v3.png", 0, "common"),
    "city_runner_v2": ("city_zombies_hd_16x6_v3.png", 1, "runner"),
    "city_crawler_v2": ("city_zombies_hd_16x6_v3.png", 2, "crawler"),
    "city_police_infected": ("city_zombies_hd_16x6_v3.png", 3, "common"),
    "city_scientist": ("city_zombies_hd_16x6_v3.png", 4, "common"),
    "city_technician": ("city_zombies_hd_16x6_v3.png", 5, "common"),
    "city_demolisher": ("city_elites_hd_16x6_v3.png", 0, "subboss"),
    "city_quarantine_brute": ("city_elites_hd_16x6_v3.png", 1, "subboss"),
    "city_mutant_commander": ("city_elites_hd_16x6_v3.png", 2, "subboss"),
    "city_boss_director": ("city_elites_hd_16x6_v3.png", 3, "boss"),
    "city_boss_commander": ("city_elites_hd_16x6_v3.png", 4, "boss"),
    "city_boss_alpha": ("city_elites_hd_16x6_v3.png", 5, "boss"),
    # Egito / Escavação Khepra
    "desert_zombie_v2": ("desert_zombies_hd_16x6_v3.png", 0, "common"),
    "desert_runner_v2": ("desert_zombies_hd_16x6_v3.png", 1, "runner"),
    "desert_crawler_v2": ("desert_zombies_hd_16x6_v3.png", 2, "crawler"),
    "desert_archer": ("desert_zombies_hd_16x6_v3.png", 3, "common"),
    "desert_beetle_host": ("desert_zombies_hd_16x6_v3.png", 4, "common"),
    "desert_looter": ("desert_zombies_hd_16x6_v3.png", 5, "common"),
    "desert_sarcophagus_guard": ("desert_elites_hd_16x6_v3.png", 0, "subboss"),
    "desert_plague_priest": ("desert_elites_hd_16x6_v3.png", 1, "subboss"),
    "desert_mutant_enforcer": ("desert_elites_hd_16x6_v3.png", 2, "subboss"),
    "desert_boss_anubis": ("desert_elites_hd_16x6_v3.png", 3, "boss"),
    "desert_boss_commander": ("desert_elites_hd_16x6_v3.png", 4, "boss"),
    "desert_boss_colossus": ("desert_elites_hd_16x6_v3.png", 5, "boss"),
    # Minas Gerais / Cachoeira contaminada
    "beach_zombie_v2": ("beach_zombies_hd_16x6_v3.png", 0, "common"),
    "beach_runner_v2": ("beach_zombies_hd_16x6_v3.png", 1, "runner"),
    "beach_crawler_v2": ("beach_zombies_hd_16x6_v3.png", 2, "crawler"),
    "beach_surfer": ("beach_zombies_hd_16x6_v3.png", 3, "common"),
    "beach_diver": ("beach_zombies_hd_16x6_v3.png", 4, "common"),
    "beach_fisher": ("beach_zombies_hd_16x6_v3.png", 5, "common"),
    "beach_puffer": ("beach_elites_hd_16x6_v3.png", 0, "subboss"),
    "beach_lifeguard": ("beach_elites_hd_16x6_v3.png", 1, "subboss"),
    "beach_deep_hunter": ("beach_elites_hd_16x6_v3.png", 2, "subboss"),
    "beach_boss_brute": ("beach_elites_hd_16x6_v3.png", 3, "boss"),
    "beach_boss_hunter": ("beach_elites_hd_16x6_v3.png", 4, "boss"),
    "beach_boss_colossus": ("beach_elites_hd_16x6_v3.png", 5, "boss"),
}

ROSTER_GRID_ROWS = {
    "city_zombies_hd_16x6_v3.png": 6,
    "desert_zombies_hd_16x6_v3.png": 6,
    "beach_zombies_hd_16x6_v3.png": 6,
    "city_elites_hd_16x6_v3.png": 6,
    "desert_elites_hd_16x6_v3.png": 6,
    "beach_elites_hd_16x6_v3.png": 6,
    "city_zombies_rebuilt_16x12_v1.png": 12,
    "desert_zombies_rebuilt_16x12_v1.png": 12,
    "beach_zombies_rebuilt_16x12_v1.png": 12,
    "city_elites_rebuilt_16x6_v1.png": 6,
    "desert_elites_rebuilt_16x6_v1.png": 6,
    "beach_elites_rebuilt_16x6_v1.png": 6,
    "city_enemy_roster_8x12_v1.png": 12,
    "desert_enemy_roster_8x12_v6_alpha.png": 12,
    "city_enemies_retro_8x12_v2.png": 12,
    "desert_enemies_retro_8x12_v3.png": 12,
    "beach_enemies_retro_8x12_v4.png": 12,
    "city_crawler_rebuilt_16x1_v2.png": 1,
    "desert_crawler_rebuilt_16x1_v2.png": 1,
    "beach_crawler_rebuilt_16x1_v2.png": 1,
    "beach_enemy_common_8x6_v3.png": 6,
    "beach_enemy_subboss_8x3_v3.png": 3,
    "beach_enemy_boss_8x3_v3.png": 3,
}

ROSTER_GRID_COLUMNS = {
    "city_zombies_hd_16x6_v3.png": 16,
    "desert_zombies_hd_16x6_v3.png": 16,
    "beach_zombies_hd_16x6_v3.png": 16,
    "city_elites_hd_16x6_v3.png": 16,
    "desert_elites_hd_16x6_v3.png": 16,
    "beach_elites_hd_16x6_v3.png": 16,
    "city_zombies_rebuilt_16x12_v1.png": 16,
    "desert_zombies_rebuilt_16x12_v1.png": 16,
    "beach_zombies_rebuilt_16x12_v1.png": 16,
    "city_elites_rebuilt_16x6_v1.png": 16,
    "desert_elites_rebuilt_16x6_v1.png": 16,
    "beach_elites_rebuilt_16x6_v1.png": 16,
    "city_crawler_rebuilt_16x1_v2.png": 16,
    "desert_crawler_rebuilt_16x1_v2.png": 16,
    "beach_crawler_rebuilt_16x1_v2.png": 16,
}

# As folhas geradas têm espaçamento visual próprio: personagens baixos e
# chefes grandes não cabem em doze fatias matematicamente idênticas. Estes
# limites foram medidos na arte final e mantêm cada linha completa, sem puxar
# cabeça, bota ou arma da linha vizinha. O deserto já respeita a grade regular.
ROSTER_VERTICAL_BOUNDS: dict[str, tuple[int, ...]] = {
    "city_enemy_roster_8x12_v1.png": (
        0, 105, 212, 279, 383, 475, 572, 660, 747, 835, 920, 994, 1086,
    ),
    # As folhas de elites usam seis faixas visuais com bastante respiro. O
    # gerador manteve as linhas, mas distribuiu alturas diferentes para um
    # baiacu baixo e um colosso alto. Estes limites ficam exatamente nos
    # vazios entre linhas e impedem que a cabeça do chefe seguinte apareça no
    # retrato do subchefe anterior.
    "city_elites_rebuilt_16x6_v1.png": (0, 155, 289, 440, 600, 760, 941),
    "desert_elites_rebuilt_16x6_v1.png": (0, 162, 286, 420, 596, 748, 941),
    "beach_elites_rebuilt_16x6_v1.png": (0, 133, 261, 382, 546, 712, 941),
}


# Ritmo próprio por equipamento: armas pesadas não podem parecer pistolas e
# rajadas automáticas não podem ter o mesmo tempo de um morteiro. Suportes
# ficam fora desta tabela para preservar exatamente a animação aprovada.
SOLDIER_TIMING: dict[str, tuple[float, float, float]] = {
    "city_guard": (8.2, 9.0, 1.00),
    "city_auto": (8.0, 12.5, 0.92),
    "city_sniper": (7.2, 7.2, 1.08),
    "city_entry": (7.5, 8.4, 1.06),
    "city_antiplague": (7.2, 10.5, 1.00),
    "city_rocket": (6.8, 6.8, 1.12),
    "city_shield": (7.2, 7.6, 1.08),
    "desert_guard": (8.0, 8.8, 1.00),
    "desert_auto": (7.8, 10.8, 0.96),
    "desert_sniper": (7.0, 7.5, 1.08),
    "desert_heavy": (6.9, 13.2, 1.04),
    "desert_incinerator": (7.0, 11.2, 1.02),
    "desert_mortar": (6.5, 6.5, 1.12),
    "desert_blade": (7.8, 9.2, 1.06),
    "beach_guard": (8.2, 9.4, 1.00),
    "beach_auto": (7.8, 10.9, 0.96),
    "beach_sniper": (7.0, 7.2, 1.08),
    "beach_waterjet": (7.1, 10.6, 1.00),
    "beach_grenadier": (7.0, 7.8, 1.08),
    "beach_bomber": (6.8, 7.0, 1.12),
    "beach_sonar": (6.4, 7.0, 1.04),
    "beach_boat": (7.2, 10.8, 1.05),
    "beach_sub": (6.8, 7.0, 1.08),
}

# Segunda camada da reconstrução: cada equipamento ganha peso de recarga
# próprio. O tempo lógico continua vindo da ficha da carta, mas a distribuição
# dos oito quadros muda (retirada, pausa visível, inserção e retorno à mira).
SOLDIER_RELOAD_WEIGHT: dict[str, float] = {
    actor: (
        1.22 if any(token in actor for token in ("sniper", "rocket", "mortar", "sub"))
        else 1.12 if any(token in actor for token in ("heavy", "grenadier", "boat"))
        else 0.94 if any(token in actor for token in ("guard", "blade", "shield"))
        else 1.0
    )
    for actor in SOLDIER_TIMING
}

# Estes dois atores usam peças escuras separadas por pequenos vazios de alfa
# (pernas, colete, escudo e carga). A limpeza por maior componente apagava as
# partes desconectadas e deixava apenas metade do Homem-Bomba ou o escudo do
# policial. As folhas já estão recortadas por célula e devem ser preservadas.
PRESERVE_ALL_COMPONENTS = frozenset({"city_shield", "beach_bomber"})


def _rect_gap(a: pygame.Rect, b: pygame.Rect) -> tuple[int, int]:
    """Distância vazia entre dois componentes, sem depender da direção."""
    horizontal = max(0, max(a.left, b.left) - min(a.right, b.right))
    vertical = max(0, max(a.top, b.top) - min(a.bottom, b.bottom))
    return horizontal, vertical


def _sanitize_actor_frame(frame: pygame.Surface) -> pygame.Surface:
    """Remove pixels herdados de células vizinhas sem apagar arma e adereços.

    Algumas artes vieram com um pedaço da cápsula, da bota ou do clarão do
    quadro anterior encostado na borda da célula. O recorte tradicional incluía
    esse fragmento e fazia a cápsula parecer cair do céu. Mantemos o maior
    componente (o ator) e somente componentes internos próximos a ele, como
    carregador, cápsula, sangue e clarão legítimos.
    """
    mask = pygame.mask.from_surface(frame, threshold=8)
    components = mask.get_bounding_rects()
    if not components:
        raise ValueError("a animação contém um quadro completamente transparente")
    main = max(components, key=lambda rect: rect.width * rect.height)
    canvas = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
    width, height = frame.get_size()
    keep: list[pygame.Rect] = [main]
    for component in components:
        if component == main:
            continue
        # Fragmentos que chegam exatamente da célula anterior sempre tocam
        # uma das bordas do recorte. Nenhum estojo, pente ou clarão válido
        # precisa nascer fora de sua própria célula.
        touches_edge = (
            component.left <= 1
            or component.top <= 1
            or component.right >= width - 1
            or component.bottom >= height - 1
        )
        if touches_edge:
            continue
        gap_x, gap_y = _rect_gap(main, component)
        area = component.width * component.height
        if area >= 2 and gap_x <= 58 and gap_y <= 72:
            keep.append(component)
    for component in keep:
        canvas.blit(frame, component.topleft, component)
    return canvas


def _main_figure(frame: pygame.Surface) -> pygame.Rect:
    components = pygame.mask.from_surface(frame, threshold=8).get_bounding_rects()
    if not components:
        raise ValueError("a animação contém um quadro completamente transparente")
    return max(components, key=lambda rect: rect.width * rect.height)


def _isolate_main_component(frame: pygame.Surface) -> pygame.Surface:
    """Mantém somente os pixels conectados ao corpo principal da pose."""
    mask = pygame.mask.from_surface(frame, threshold=8)
    components = mask.connected_components(minimum=2)
    if not components:
        raise ValueError("a animação contém um quadro completamente transparente")
    main = max(components, key=lambda component: component.count())
    rect = main.get_bounding_rects()[0]
    component_surface = main.to_surface(
        setcolor=(255, 255, 255, 255),
        unsetcolor=(255, 255, 255, 0),
    )
    isolated = frame.copy()
    isolated.blit(component_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return isolated.subsurface(rect).copy()


def _extract_full_actor_component(
    sheet: SpriteSheet,
    *,
    columns: int,
    rows: int,
    row: int,
    column: int,
) -> pygame.Surface:
    """Extrai uma pose inclinada sem cortá-la na fronteira matemática.

    Corredores e rastejantes avançam o tronco para a célula seguinte. Um
    ``subsurface`` de grade cortava mãos, cabeça ou pernas mesmo quando a arte
    original estava íntegra. Aqui localizamos o vale de transparência mais
    próximo de cada separação. Isso também resolve fileiras de rastejantes
    cujas mãos se encostam e formam um único componente alfa.
    """
    surface = sheet.surface
    width, height = surface.get_size()
    row_top = row * height // rows
    row_bottom = (row + 1) * height // rows
    alpha = pygame.surfarray.array_alpha(surface)
    projection = (alpha[:, row_top:row_bottom] > 8).sum(axis=1)
    cell_width = width / columns
    boundaries = [0]
    for divider in range(1, columns):
        nominal = divider * cell_width
        radius = max(4, round(cell_width * 0.30))
        low = max(boundaries[-1] + 4, round(nominal) - radius)
        high = min(width - 1, round(nominal) + radius)
        if high <= low:
            boundaries.append(round(nominal))
            continue
        values = projection[low : high + 1]
        minimum = values.min()
        options = [low + index for index, value in enumerate(values) if value == minimum]
        boundaries.append(min(options, key=lambda x: abs(x - nominal)))
    boundaries.append(width)
    left, right = boundaries[column], boundaries[column + 1]
    if right - left < max(12, round(cell_width * 0.45)):
        left = round(column * cell_width)
        right = round((column + 1) * cell_width)
    return surface.subsurface((left, row_top, right - left, row_bottom - row_top)).copy()


def _normalize_actor_height(
    frames: list[pygame.Surface], target_actor_height: int, reference_height: int
) -> list[pygame.Surface]:
    """Aplica uma única escala física sem perder efeitos nem criar pulsação.

    Usar a altura da pose atual fazia um ator inclinado ser ampliado até o
    tamanho de uma pose ereta. O resultado era um corpo que crescia durante
    recarga, disparo e dano. Todos os quadros agora herdam o mesmo fator,
    calculado pelas poses eretas de locomoção e espera.
    """
    normalized: list[pygame.Surface] = []
    factor = target_actor_height / max(1, reference_height)
    for frame in frames:
        content = frame.get_bounding_rect(min_alpha=8)
        crop = frame.subsurface(content).copy()
        normalized.append(
            pygame.transform.scale(
                crop,
                (
                    max(1, round(crop.get_width() * factor)),
                    max(1, round(crop.get_height() * factor)),
                ),
            )
        )
    return normalized


def _pad_groups(
    groups: dict[str, list[pygame.Surface]],
    *,
    horizontal_padding: int = 8,
    top_padding: int = 5,
) -> dict[str, list[pygame.Surface]]:
    """Recompõe todos os estados numa caixa única com os pés no mesmo eixo."""
    frames = [frame for group in groups.values() for frame in group]
    geometry = [(frame, _main_figure(frame)) for frame in frames]
    min_x = min(-main.centerx for frame, main in geometry)
    max_x = max(frame.get_width() - main.centerx for frame, main in geometry)
    min_y = min(-main.bottom for frame, main in geometry)
    max_y = max(frame.get_height() - main.bottom for frame, main in geometry)
    width = max_x - min_x + horizontal_padding * 2
    height = max_y - min_y + top_padding
    actor_x = -min_x + horizontal_padding
    foot_y = -min_y + top_padding

    padded: dict[str, list[pygame.Surface]] = {}
    geometry_index = 0
    for state, state_frames in groups.items():
        padded[state] = []
        for frame in state_frames:
            _, main = geometry[geometry_index]
            geometry_index += 1
            canvas = pygame.Surface((width, height), pygame.SRCALPHA)
            canvas.blit(frame, (actor_x - main.centerx, foot_y - main.bottom))
            padded[state].append(canvas)
    return padded


def _sheet_rows(
    path: Path,
    rows: int,
    target_height: int,
    *,
    isolate_main: bool = False,
    sanitize: bool = False,
) -> list[list[pygame.Surface]]:
    cells = SpriteSheet.from_file(path).slice_equal(8, rows)
    if isolate_main:
        # Algumas folhas dos corredores trazem pixels do quadro vizinho junto
        # às bordas da célula. Preservar somente o componente corporal principal
        # impede a sobreposição sem redimensionar a pose nem alterar o pivô.
        cells = [cell.subsurface(_main_figure(cell)).copy() for cell in cells]
    if sanitize:
        # Limpar antes de medir evita que um fragmento vindo de outra célula
        # altere a escala física do personagem inteiro.
        cells = [_sanitize_actor_frame(cell) for cell in cells]
    # As duas primeiras linhas são movimento e espera: nelas o corpo está
    # ereto e oferece uma referência segura para toda a folha.
    upright_heights = [_main_figure(cell).height for cell in cells[:16]]
    reference_height = sorted(upright_heights)[len(upright_heights) // 2]
    scaled = _normalize_actor_height(
        cells,
        min(target_height, reference_height),
        reference_height,
    )
    return [scaled[row * 8 : (row + 1) * 8] for row in range(rows)]


def _soldier_clips(
    path: Path,
    *,
    sanitize: bool = False,
    move_fps: float = 8.0,
    shoot_fps: float = 10.0,
    hit_time_scale: float = 1.0,
    reload_weight: float = 1.0,
) -> dict[str, AnimationClip]:
    move, idle, shoot, reload, hit = _sheet_rows(
        path, 5, 130, sanitize=sanitize
    )
    groups = _pad_groups(
        {"move": move, "idle": idle, "shoot": shoot, "reload": reload, "hit": hit}
    )
    return {
        "move": AnimationClip.timed(
            groups["move"],
            tuple(value / move_fps for value in (0.82, 1.08, 1.22, 0.88, 0.82, 1.08, 1.22, 0.88)),
            name="implantação",
        ),
        "idle": AnimationClip.uniform(groups["idle"], fps=5.0, name="pronto"),
        "shoot": AnimationClip.timed(
            groups["shoot"],
            tuple(value / shoot_fps for value in (0.58, 0.72, 0.82, 1.36, 1.24, 0.96, 0.72, 0.60)),
            loop=False,
            name="disparo",
        ),
        "reload": AnimationClip.timed(
            groups["reload"],
            tuple(
                value * reload_weight
                for value in (0.18, 0.24, 0.31, 0.42, 0.38, 0.29, 0.22, 0.17)
            ),
            loop=False,
            name="recarga",
        ),
        "hit": AnimationClip.timed(
            groups["hit"],
            tuple(
                value * hit_time_scale
                for value in (0.07, 0.07, 0.09, 0.11, 0.10, 0.09, 0.08, 0.10)
            ),
            loop=False,
            name="dano",
        ),
    }


def _support_clips(path: Path) -> dict[str, AnimationClip]:
    move, idle, transmit, confirm, hit = _sheet_rows(path, 5, 126)
    groups = _pad_groups(
        {"move": move, "idle": idle, "support": transmit + confirm, "hit": hit}
    )
    return {
        "move": AnimationClip.uniform(groups["move"], fps=7.0, name="implantação"),
        "idle": AnimationClip.uniform(groups["idle"], fps=4.5, name="aguarda"),
        "support": AnimationClip.timed(
            groups["support"],
            (0.08, 0.09, 0.10, 0.11, 0.11, 0.10, 0.09, 0.08,
             0.08, 0.09, 0.10, 0.11, 0.11, 0.10, 0.09, 0.08),
            loop=False,
            name="solicitação de suprimentos",
        ),
        "hit": AnimationClip.timed(
            groups["hit"],
            (0.07, 0.07, 0.09, 0.11, 0.10, 0.09, 0.08, 0.10),
            loop=False,
            name="dano",
        ),
    }


def _zombie_clips(
    path: Path,
    *,
    target_height: int = 136,
    move_fps: float = 7.0,
    bite_speed: float = 1.0,
    isolate_main: bool = False,
) -> dict[str, AnimationClip]:
    move, idle, bite, hit = _sheet_rows(
        path, 4, target_height, isolate_main=isolate_main
    )
    # Mordida e dano também passam pela inspeção de componentes. Isso remove
    # mãos, botas e tiras de roupa que pertenciam à célula vizinha sem apagar
    # a silhueta principal do infectado.
    move = [_sanitize_actor_frame(frame) for frame in move]
    idle = [_sanitize_actor_frame(frame) for frame in idle]
    bite = [_sanitize_actor_frame(frame) for frame in bite]
    hit = [_sanitize_actor_frame(frame) for frame in hit]
    groups = _pad_groups({"move": move, "idle": idle, "bite": bite, "hit": hit})
    return {
        "move": AnimationClip.uniform(groups["move"], fps=move_fps, name="caminhada"),
        "idle": AnimationClip.uniform(groups["idle"], fps=4.5, name="ameaça"),
        "bite": AnimationClip.timed(
            groups["bite"],
            tuple(value / bite_speed for value in (0.11, 0.09, 0.09, 0.08, 0.11, 0.13, 0.11, 0.10)),
            loop=False,
            name="mordida",
        ),
        "hit": AnimationClip.timed(
            groups["hit"],
            (0.06, 0.07, 0.08, 0.10, 0.10, 0.10, 0.09, 0.12),
            loop=False,
            name="dano",
        ),
    }


def _roster_enemy_clips(path: Path, row: int, kind: str) -> dict[str, AnimationClip]:
    """Converte uma linha regional em cinco estados claros e temporizados.

    Não há interpolação suave: o movimento conserva degraus de pixel e troca
    poses discretas, como uma folha 16-bit autêntica. A caixa e o ponto de
    contato são recompostos uma única vez para eliminar pulsação de tamanho.
    """
    sheet = SpriteSheet.from_file(path)
    columns = ROSTER_GRID_COLUMNS.get(path.name, 8)
    custom_bounds = ROSTER_VERTICAL_BOUNDS.get(path.name)
    if custom_bounds is None:
        grid_rows = ROSTER_GRID_ROWS.get(path.name, 12)
        cells = sheet.slice_equal(columns, grid_rows)[
            row * columns : (row + 1) * columns
        ]
    else:
        width = sheet.surface.get_width()
        top, bottom = custom_bounds[row], custom_bounds[row + 1]
        cells = [
            sheet.surface.subsurface(
                (
                    column * width // columns,
                    top,
                    (column + 1) * width // columns - column * width // columns,
                    bottom - top,
                )
            ).copy()
            for column in range(columns)
        ]
    # Nas poses baixas ou inclinadas, a fronteira matemática pode atravessar o
    # próprio corpo. Recuperamos a figura completa diretamente da folha antes
    # da limpeza. Os quatro quadros de habilidade continuam com o recorte amplo
    # para preservar veneno, água, fumaça e ondas de impacto.
    if columns >= 16 and kind in {"runner", "crawler"}:
        cells[:12] = [
            _extract_full_actor_component(
                sheet,
                columns=columns,
                rows=ROSTER_GRID_ROWS.get(path.name, 6),
                row=row,
                column=column,
            )
            for column in range(12)
        ]
    # Folhas densas podem carregar uma bota, gota ou fragmento da linha
    # vizinha junto à borda. A mesma inspeção usada nos soldados remove esse
    # vazamento antes de medir a escala, preservando o corpo e os efeitos que
    # realmente pertencem à ação atual.
    cells = [_sanitize_actor_frame(frame) for frame in cells]
    # Caminhada, ataque e dano são movimentos exclusivamente corporais. Neles
    # mantemos apenas a figura conectada principal: isso remove cabeças, botas
    # e manchas herdadas da coluna vizinha. Somente os quatro quadros finais
    # podem preservar componentes soltos, pois representam efeitos reais das
    # habilidades (fumaça, água, veneno, projéteis ou ondas de impacto).
    for index in range(min(12, len(cells))):
        cells[index] = _isolate_main_component(cells[index])
    # Depois da limpeza, enquadramos todo o conteúdo legítimo. Usar somente o
    # maior componente apagava prancha, escudo, arpão e partes desconectadas
    # por um único pixel transparente.
    cells = [
        frame.subsurface(frame.get_bounding_rect(min_alpha=8)).copy()
        for frame in cells
    ]
    target_height = 88 if kind == "crawler" else (160 if kind == "boss" else (146 if kind == "subboss" else 128))
    heights = [_main_figure(frame).height for frame in cells]
    reference_height = sorted(heights[:4])[len(heights[:4]) // 2]
    frames = _normalize_actor_height(cells, target_height, reference_height)
    if columns >= 16:
        if kind in {"runner", "crawler"}:
            # Essas duas silhuetas possuem seis poses de aproximação antes do
            # contato. Usar 4..7 como ataque misturava a última passada com a
            # mordida e, na folha aquática, ainda capturava a cabeça da pose
            # vizinha. 6..9 contém extensão, contato e recuperação completos;
            # 9..12 concentra a reação física ao impacto.
            state_frames = {
                "move": frames[0:4],
                "idle": [frames[0], frames[1], frames[0], frames[3]],
                "bite": [frames[6], frames[7], frames[8], frames[9]],
                "hit": [frames[9], frames[10], frames[11], frames[12]],
                "skill": frames[12:16],
            }
        else:
            state_frames = {
                "move": frames[0:4],
                "idle": [frames[0], frames[1], frames[0], frames[3]],
                "bite": frames[4:8],
                "hit": frames[8:12],
                "skill": frames[12:16],
            }
    else:
        state_frames = {
            "idle": [frames[0], frames[1], frames[0], frames[1]],
            "move": [frames[2], frames[3], frames[2], frames[3]],
            "bite": [frames[4], frames[5], frames[5], frames[4]],
            "hit": [frames[6], frames[6], frames[1], frames[1]],
            "skill": [frames[4], frames[7], frames[7], frames[4]],
        }
    groups = _pad_groups(
        state_frames,
        horizontal_padding=12,
        top_padding=8,
    )
    # Ritmos assimétricos evitam o aspecto de apresentação de slides. O
    # apoio permanece um pouco mais tempo no chão; extensão e recuperação
    # passam mais rápido. A soma continua baseada em segundos e não no FPS.
    move_durations = {
        "runner": (0.075, 0.095, 0.075, 0.105),
        "crawler": (0.18, 0.14, 0.20, 0.15),
        "boss": (0.18, 0.22, 0.17, 0.24),
        "subboss": (0.14, 0.18, 0.13, 0.19),
        "common": (0.12, 0.15, 0.11, 0.16),
    }[kind]
    bite_durations = (
        (0.10, 0.075, 0.105, 0.16)
        if kind == "runner"
        else (0.14, 0.09, 0.13, 0.19)
    )
    skill_durations = (
        (0.16, 0.22, 0.19, 0.17)
        if kind in {"boss", "subboss"}
        else (0.12, 0.17, 0.15, 0.14)
    )
    return {
        "move": AnimationClip.timed(
            groups["move"], move_durations, loop=True, name="locomoção 16-bit fluida"
        ),
        "idle": AnimationClip.timed(
            groups["idle"], (0.24, 0.18, 0.24, 0.20), loop=True, name="ameaça"
        ),
        "bite": AnimationClip.timed(
            groups["bite"],
            bite_durations,
            loop=False,
            name="ataque físico",
        ),
        "hit": AnimationClip.timed(
            groups["hit"],
            (0.08, 0.11, 0.12, 0.10),
            loop=False,
            name="reação a dano",
        ),
        "skill": AnimationClip.timed(
            groups["skill"],
            skill_durations,
            loop=False,
            name="habilidade exclusiva",
        ),
    }


def _retro_defender_clips(
    path: Path, row: int, kind: str, actor: str
) -> dict[str, AnimationClip]:
    """Monta uma carta inteira a partir da nova linha 8x8 de poses físicas."""
    cells = SpriteSheet.from_file(path).slice_equal(8, 8)[row * 8 : (row + 1) * 8]
    # O gerador pode deixar alguns pixels da linha anterior exatamente no
    # limite superior da célula. A limpeza estrutural remove esses fragmentos
    # (pentes, botas ou canos flutuantes) antes de medir a caixa corporal.
    cells = [_sanitize_actor_frame(frame) for frame in cells]
    cells = [
        frame.subsurface(frame.get_bounding_rect(min_alpha=8)).copy()
        for frame in cells
    ]
    target_height = 78 if kind == "vehicle" else (96 if kind == "support" else 124)
    reference_height = sorted(_main_figure(frame).height for frame in cells[:4])[1]
    frames = _normalize_actor_height(cells, target_height, reference_height)
    groups = _pad_groups(
        {
            "idle": [frames[0], frames[1], frames[0], frames[1]],
            "move": [frames[2], frames[3], frames[2], frames[3]],
            "shoot": [frames[4], frames[5], frames[5], frames[4]],
            "reload": [frames[4], frames[6], frames[6], frames[1]],
            "hit": [frames[7], frames[7], frames[1], frames[1]],
            "support": [frames[4], frames[5], frames[6], frames[1]],
        },
        horizontal_padding=14,
        top_padding=8,
    )
    move_fps, shoot_fps, hit_scale = SOLDIER_TIMING.get(actor, (6.2, 8.5, 1.0))
    shot_scale = 9.0 / max(1.0, shoot_fps)
    reload_scale = SOLDIER_RELOAD_WEIGHT.get(actor, 1.0)
    clips = {
        "idle": AnimationClip.uniform(groups["idle"], fps=3.0, name="respiração 16-bit"),
        "move": AnimationClip.uniform(groups["move"], fps=move_fps, name="deslocamento apoiado"),
        "shoot": AnimationClip.timed(
            groups["shoot"], tuple(value * shot_scale for value in (0.10, 0.10, 0.13, 0.12)), loop=False, name="ação e recuo"
        ),
        "reload": AnimationClip.timed(
            groups["reload"], tuple(value * reload_scale for value in (0.18, 0.42, 0.48, 0.20)), loop=False, name="recarga visível"
        ),
        "hit": AnimationClip.timed(
            groups["hit"], tuple(value * hit_scale for value in (0.08, 0.11, 0.09, 0.07)), loop=False, name="impacto"
        ),
    }
    if kind == "support":
        return {
            "idle": clips["idle"],
            "move": clips["move"],
            "hit": clips["hit"],
            "support": AnimationClip.timed(
            groups["support"], (0.16, 0.24, 0.36, 0.18), loop=False, name="transmissão"
            ),
        }
    return clips


def build_production_clips() -> dict[str, dict[str, AnimationClip]]:
    clips: dict[str, dict[str, AnimationClip]] = {}
    for actor, (filename, kind) in ACTOR_SHEETS.items():
        if actor in DEFENDER_ROSTER_ROWS:
            continue
        path = ASSETS / filename
        if kind == "soldier":
            # Toda tropa armada usa a mesma limpeza estrutural. Assim cápsulas,
            # clarões, botas ou fragmentos nunca nascem no quadro vizinho.
            move_fps, shoot_fps, hit_time_scale = SOLDIER_TIMING[actor]
            clips[actor] = _soldier_clips(
                path,
                sanitize=actor not in PRESERVE_ALL_COMPONENTS,
                move_fps=move_fps,
                shoot_fps=shoot_fps,
                hit_time_scale=hit_time_scale,
                reload_weight=SOLDIER_RELOAD_WEIGHT[actor],
            )
        elif kind == "support":
            clips[actor] = _support_clips(path)
        elif kind == "runner":
            clips[actor] = _zombie_clips(
                path,
                move_fps=12.0,
                bite_speed=1.25,
                isolate_main=True,
            )
        elif kind == "crawler":
            clips[actor] = _zombie_clips(path, target_height=92, move_fps=4.4, bite_speed=0.88)
        else:
            clips[actor] = _zombie_clips(path)
    for actor, (filename, row, kind) in DEFENDER_ROSTER_ROWS.items():
        clips[actor] = _retro_defender_clips(ASSETS / filename, row, kind, actor)
    for actor, (filename, row, kind) in ENEMY_ROSTER_ROWS.items():
        clips[actor] = _roster_enemy_clips(ASSETS / filename, row, kind)
    return clips


def new_production_animation(
    clips: dict[str, dict[str, AnimationClip]], actor: str
) -> AnimationManager:
    initial = "move" if "bite" in clips[actor] else "idle"
    return AnimationManager(clips[actor], initial_state=initial)
