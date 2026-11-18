"""Contrato visual de tamanho e ancoragem da Beta 4.

Arte e lógica consultam a mesma tabela. Assim o quadro pode mudar de pose sem
alterar a altura física, e tiro/efeito nasce sempre no equipamento correto.
Os valores são medidos no espaço lógico de uma pista e recebem a perspectiva
da faixa apenas no momento de desenhar.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorLayout:
    body_height: float
    source_height: float
    muzzle_forward: float = 0.0
    muzzle_height: float = 0.0
    muzzle_cycle: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class WeaponVisualProfile:
    """Leitura visual própria de uma arma real no campo.

    O tamanho é de leitura (pixels lógicos), não uma tentativa de desenhar o
    calibre em escala 1:1. A relação entre famílias, porém, segue a munição e
    o funcionamento reais: 9 mm é menor que .50 AE, projétil de escopeta não
    vira bala de pistola, e granada/foguete/torpedo mantêm silhuetas distintas.
    """

    projectile_kind: str
    flash_size: tuple[float, float]
    recoil: float
    reload_motion: str


# Identidade por personagem, e não um molde copiado da SWAT. O alinhamento é
# comum (sempre na boca do cano); tamanho, recuo e gesto continuam específicos.
DEFENDER_WEAPON_PROFILES: dict[str, WeaponVisualProfile] = {
    "xerife_rua": WeaponVisualProfile("pistol_50ae", (13.0, 8.0), 5.0, "pistol_magazine"),
    "pistoleiro_deserto": WeaponVisualProfile("revolver_357", (12.0, 7.0), 5.5, "revolver_cylinder"),
    "marinheiro": WeaponVisualProfile("pistol_9mm", (9.0, 6.0), 3.0, "pistol_magazine"),
    "agente_swat": WeaponVisualProfile("smg_9mm", (10.0, 6.0), 2.0, "smg_magazine"),
    "fuzileiro_deserto": WeaponVisualProfile("rifle_556_scar", (12.0, 7.0), 3.2, "rifle_magazine"),
    "fuzileiro_marinha": WeaponVisualProfile("rifle_556_m16", (13.0, 7.0), 3.0, "rifle_magazine"),
    "atirador_precisao_swat": WeaponVisualProfile("sniper_awm", (14.0, 8.0), 5.0, "bolt_action"),
    "atirador_horizonte": WeaponVisualProfile("sniper_762", (13.0, 7.0), 4.2, "rifle_magazine"),
    "atirador_precisao_marinha": WeaponVisualProfile("sniper_338", (15.0, 9.0), 5.8, "bolt_action"),
    "agente_entrada": WeaponVisualProfile("buckshot_12g", (18.0, 11.0), 7.0, "shotgun_shells"),
    "tenente_artilheiro": WeaponVisualProfile("mg_762", (15.0, 8.0), 4.0, "belt_box"),
    "especialista_antipraga": WeaponVisualProfile("gas_grenade", (7.0, 5.0), 3.5, "grenade_drum"),
    "lancador_foguetes": WeaponVisualProfile("rpg7_rocket", (5.0, 4.0), 8.0, "rocket_round"),
    "nomade_morteiro": WeaponVisualProfile("mortar_shell", (4.0, 4.0), 5.0, "mortar_shell"),
    "granadeiro_profundidades": WeaponVisualProfile("grenade_40mm", (7.0, 5.0), 4.0, "grenade_drum"),
    "barco_patrulha": WeaponVisualProfile("naval_round", (14.0, 8.0), 3.5, "box_magazine"),
    "submarino_tatico": WeaponVisualProfile("compact_torpedo", (3.0, 3.0), 2.0, "torpedo_tube"),
    "incinerador_deserto": WeaponVisualProfile("flame", (0.0, 0.0), 1.0, "fuel_tank"),
    "bombeiro_hidraulico": WeaponVisualProfile("waterjet", (0.0, 0.0), 1.4, "water_tank"),
}


DEFENDER_LAYOUTS: dict[str, ActorLayout] = {
    "city_guard": ActorLayout(100, 130, 27, 52),
    "desert_guard": ActorLayout(100, 130, 28, 52),
    "beach_guard": ActorLayout(100, 130, 27, 52),
    "city_auto": ActorLayout(102, 130, 37, 58),
    "desert_auto": ActorLayout(102, 130, 38, 58),
    "beach_auto": ActorLayout(102, 130, 38, 58),
    "city_radio": ActorLayout(88, 126),
    "desert_radio": ActorLayout(86, 126),
    "beach_radio": ActorLayout(86, 126),
    "city_sniper": ActorLayout(102, 130, 47, 62),
    "city_entry": ActorLayout(104, 130, 45, 59),
    "city_antiplague": ActorLayout(104, 130, 42, 55),
    "city_rocket": ActorLayout(106, 130, 50, 64),
    "city_shield": ActorLayout(108, 130, 25, 45),
    "desert_sniper": ActorLayout(102, 130, 47, 62),
    "desert_heavy": ActorLayout(106, 130, 42, 57),
    "desert_incinerator": ActorLayout(104, 130, 42, 55),
    "desert_mortar": ActorLayout(98, 130, 16, 49),
    "desert_blade": ActorLayout(104, 130, 28, 46),
    "beach_sniper": ActorLayout(102, 130, 47, 62),
    # O bocal muda poucos pixels com o apoio dos braços. A água consulta este
    # ciclo no mesmo quadro do corpo, em vez de nascer de uma coordenada fixa
    # à frente da mangueira.
    "beach_waterjet": ActorLayout(
        104,
        130,
        17,
        72,
        # Medido no último pixel opaco do bocal em cada um dos oito quadros.
        # O ciclo antigo estava cerca de 17 px abaixo do cano: horizontalmente
        # parecia próximo, mas a água começava no vazio diante do personagem.
        ((17, 72), (17, 72), (17, 73), (17, 72), (17, 72), (17, 72), (17, 72), (17, 73)),
    ),
    "beach_grenadier": ActorLayout(104, 130, 40, 55),
    "beach_bomber": ActorLayout(104, 130),
    "beach_sonar": ActorLayout(84, 130),
    "beach_boat": ActorLayout(74, 130, 55, 47),
    "beach_sub": ActorLayout(66, 130, 58, 45),
}

DEFAULT_DEFENDER_LAYOUT = ActorLayout(102, 130, 30, 54)

ENEMY_BODY_LAYOUTS: dict[str, tuple[float, float]] = {
    "crawler": (70.0, 88.0),
    "common": (100.0, 124.0),
    "subboss": (109.0, 132.0),
    "boss": (116.0, 140.0),
}

# Ponto de nascimento medido a partir do centro no chão. Valores horizontais
# negativos apontam para a esquerda, direção única dos infectados.
ENEMY_ATTACK_ORIGINS: dict[str, tuple[float, float]] = {
    "acid": (-20.0, 0.67),
    "enemy_bullet": (-24.0, 0.61),
    "mortar": (-18.0, 0.69),
    "torpedo": (-30.0, 0.36),
}

# linha, coluna, largura, altura. Cada munição mantém proporção própria.
PROJECTILE_LAYOUTS: dict[str, tuple[int, int, float, float]] = {
    # Munição é deliberadamente menor que o cano. O clarão comunica o
    # disparo; o projétil comunica direção e deslocamento, sem parecer uma
    # segunda arma voando pela pista.
    "rifle": (0, 0, 12, 4),
    "tracer": (0, 0, 14, 4),
    "shotgun": (0, 1, 8, 3),
    "sniper": (0, 2, 16, 4),
    "fuzileiro": (0, 3, 14, 4),
    "boat": (0, 3, 16, 5),
    "turret": (0, 3, 14, 4),
    "grenade": (1, 0, 13, 13),
    "mortar": (1, 1, 18, 11),
    "bazooka": (1, 2, 27, 12),
    "torpedo": (1, 3, 32, 14),
    "acid": (2, 0, 18, 13),
    "enemy_bullet": (2, 1, 13, 5),
    "drone": (2, 2, 24, 12),
    # Famílias usadas pelo elenco final. Compartilham células do atlas quando
    # a silhueta é equivalente, mas nunca o tamanho físico ou a animação.
    "pistol_9mm": (0, 0, 7, 3),
    "pistol_50ae": (0, 0, 10, 4),
    "revolver_357": (0, 0, 9, 3),
    "smg_9mm": (0, 0, 8, 3),
    "rifle_556_scar": (0, 3, 12, 4),
    "rifle_556_m16": (0, 3, 13, 4),
    "mg_762": (0, 3, 15, 4),
    "sniper_awm": (0, 2, 16, 4),
    "sniper_762": (0, 2, 15, 4),
    "sniper_338": (0, 2, 17, 4),
    "buckshot_12g": (0, 1, 7, 3),
    "grenade_40mm": (1, 0, 14, 10),
    "gas_grenade": (1, 0, 14, 12),
    "mortar_shell": (1, 1, 18, 11),
    "rpg7_rocket": (1, 2, 28, 12),
    "compact_torpedo": (1, 3, 32, 14),
    "naval_round": (0, 3, 14, 4),
}

# Distância livre depois da boca/tubo. Fluxos elementais não entram aqui:
# água, fogo e veneno precisam continuar fisicamente ligados ao emissor.
PROJECTILE_LAUNCH_GAPS: dict[str, float] = {
    "rifle": 5.0,
    "tracer": 5.0,
    "shotgun": 4.0,
    "sniper": 6.0,
    "fuzileiro": 5.0,
    "boat": 6.0,
    "turret": 5.0,
    "grenade": 4.0,
    "mortar": 4.0,
    "bazooka": 5.0,
    "torpedo": 5.0,
    "acid": 3.0,
    "enemy_bullet": 4.0,
    "drone": 4.0,
    "pistol_9mm": 5.0,
    "pistol_50ae": 6.0,
    "revolver_357": 5.5,
    "smg_9mm": 5.0,
    "rifle_556_scar": 6.0,
    "rifle_556_m16": 6.0,
    "mg_762": 6.5,
    "sniper_awm": 7.0,
    "sniper_762": 7.0,
    "sniper_338": 7.5,
    "buckshot_12g": 5.0,
    "grenade_40mm": 5.0,
    "gas_grenade": 5.0,
    "mortar_shell": 4.0,
    "rpg7_rocket": 7.0,
    "compact_torpedo": 7.0,
    "naval_round": 6.0,
}

# Contrato de interação. Não é apenas uma etiqueta de interface: os testes
# exigem que todo papel jogável e toda habilidade inimiga conhecida estejam
# classificados. Isso evita voltar ao erro de usar o mesmo clarão genérico em
# armas, equipamentos e poderes com funcionamento físico diferente.
DEFENDER_INTERACTIONS: dict[str, str] = {
    "rifle": "tiro_balístico",
    "shotgun": "dispersão_de_chumbos",
    "sniper": "tiro_de_precisão",
    "heavy": "rajada_pesada",
    "grenade": "granada_em_arco",
    "mortar": "morteiro_em_arco",
    "rocket": "foguete",
    "flame": "jato_de_fogo",
    "poison": "jato_químico",
    "gas_grenade": "granada_de_gás_em_arco",
    "waterjet": "jato_de_água",
    "boat": "canhão_do_barco",
    "sub": "torpedo",
    "shield": "golpe_de_escudo",
    "blade": "golpe_de_lâminas",
    "radio": "suprimento_por_rádio",
    "promoter": "promoção_tática",
    "barrier": "bloqueio_passivo",
    "mine": "explosão_por_contato",
    "suicide_bomber": "explosão_por_contato",
    "sonar": "pulso_de_sonar",
}

ENEMY_ACTIVE_INTERACTIONS: dict[str, str] = {
    "dash": "arrancada_aquática",
    "naval_hunter": "investida_submersa",
    "gun": "tiro_inimigo",
    "acid": "cuspe_ácido",
    "shock": "pulso_elétrico",
    "net": "lançamento_de_rede",
    "scream": "grito_de_comando",
    "heal": "cura_da_escolta",
    "parasite": "surto_parasita",
    "stomp": "impacto_no_solo",
    "steal": "roubo_de_suprimentos",
    "signal_jammer": "interferência_de_sinal",
}

ENEMY_PASSIVE_TRAITS = frozenset(
    {
        "constant_speed",
        "runner",
        "unstaggerable",
        "shield",
        "explode_death",
        "dig",
        "jump",
    }
)


def defender_layout(actor: str | None) -> ActorLayout:
    return DEFENDER_LAYOUTS.get(actor or "", DEFAULT_DEFENDER_LAYOUT)
