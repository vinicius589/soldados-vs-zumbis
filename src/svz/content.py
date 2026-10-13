"""Catálogo de regiões, tropas, inimigos e regras de conteúdo."""
from __future__ import annotations

from svz.roster import EXPANSION_DEFENDERS

from .config import (
    GOLD,
    RED,
    TOTAL_WAVES,
)
from .math_utils import (
    clamp,
)


REGIONS = {
    "city": {
        "name": "Nova York — Terminal Félix",
        "short": "NOVA YORK",
        "tag": "Contaminação urbana",
        "bg": "city_beta4_integrated_v4.png",
        "soldiers": "city_soldiers_atlas.png",
        "soldiers_l2": "city_soldiers_l2_atlas_v74.png",
        "zombies": "city_zombies_atlas.png",
        "accent": (90, 207, 166),
        "unlock_after": None,
        "description": "Uma avenida de quarentena com quatro pistas largas de asfalto, base de emergência e ruínas tóxicas nas bordas.",
        # Chefes voltam quando suas novas folhas forem aprovadas.
        "bosses": (),
    },
    "desert": {
        "name": "Egito — Escavação Félix",
        "short": "EGITO",
        "tag": "Necrópole contaminada",
        "bg": "desert_beta4_integrated_v4.png",
        "soldiers": "desert_soldiers_atlas.png",
        "soldiers_l2": "desert_soldiers_l2_atlas_v74.png",
        "zombies": "desert_zombies_atlas.png",
        "accent": (235, 179, 76),
        "unlock_after": "city",
        "description": "Quatro trilhas largas de areia compactada cruzam uma expedição militar rumo às ruínas e pirâmides antigas.",
        "bosses": (),
    },
    "beach": {
        "name": "Minas Gerais — Cachoeira Contaminada",
        "short": "CACHOEIRA",
        "tag": "Água contaminada",
        "bg": "beach_beta4_integrated_v6.png",
        "soldiers": "beach_soldiers_beta4_rebuilt.png",
        "soldiers_l2": "beach_soldiers_l2_beta4_rebuilt.png",
        "zombies": "beach_zombies_beta4_rebuilt.png",
        "accent": (78, 177, 232),
        "unlock_after": "desert",
        "description": "Duas trilhas terrestres e dois canais contaminados defendem a base diante da cachoeira de Minas Gerais.",
        "bosses": (),
    },
}


# Catálogo legado preservado somente como dados internos. A produção ativa
# abaixo expõe um único protótipo novo por mapa, sem níveis ou promoções.
DEFENSES = {
    "xerife_rua": {
        "base": "Xerife de Rua",
        "role": "rifle",
        "level": 1,
        "cost": 42,
        "hp": 100,
        "damage": 22,
        "range": 2,
        "cooldown": 0.82,
        "ammo": 7,
        "reload": 2.0,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Desert Eagle de serviço. Alcance de dois blocos, recarga ágil e linha de tiro limpa: não dispara através de outra defesa.",
    },
    "pistoleiro_deserto": {
        "base": "Pistoleiro do Deserto",
        "role": "rifle",
        "level": 1,
        "cost": 44,
        "hp": 102,
        "damage": 26,
        "range": 2,
        "cooldown": 0.94,
        "ammo": 6,
        "reload": 2.2,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Magnum .357. Alcance de dois blocos, tiro pesado, recarga ágil e linha de tiro limpa: não dispara através de outra defesa.",
    },
    "marinheiro": {
        "base": "Marinheiro",
        "role": "rifle",
        "level": 1,
        "cost": 42,
        "hp": 101,
        "damage": 14,
        "range": 2,
        "cooldown": 0.68,
        "ammo": 15,
        "reload": 1.8,
        "shoot_through_allies": False,
        "combat_class": 1,
        "sprite": 0,
        "ability": "Glock 19 de serviço. Alcance de dois blocos, recarga ágil e linha de tiro limpa. É uma tropa terrestre; os canais ficam reservados a barco e submarino.",
    },
    "agente_swat": {
        "base": "Agente Tático da SWAT",
        "role": "rifle",
        "level": 1,
        "cost": 72,
        "hp": 108,
        "damage": 8,
        "range": 3,
        "cooldown": 0.34,
        "ammo": 30,
        "reload": 3.4,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "MP5 automática. Dispara depressa por três blocos e pode cobrir aliados à frente; o pente maior cobra uma recarga mais longa.",
    },
    "fuzileiro_deserto": {
        "base": "Fuzileiro do Deserto",
        "role": "rifle",
        "level": 1,
        "cost": 78,
        "hp": 110,
        "damage": 15,
        "range": 3,
        "cooldown": 0.46,
        "ammo": 24,
        "reload": 3.7,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "SCAR preparada para areia. Rajadas precisas por três blocos atravessam a formação aliada; a arma pesada demora mais para recarregar.",
    },
    "fuzileiro_marinha": {
        "base": "Fuzileiro da Marinha",
        "role": "rifle",
        "level": 1,
        "cost": 74,
        "hp": 109,
        "damage": 12,
        "range": 3,
        "cooldown": 0.39,
        "ammo": 30,
        "reload": 3.6,
        "shoot_through_allies": True,
        "sprite": 1,
        "combat_class": 2,
        "ability": "M16 naval. Mantém fogo rápido por três blocos e cobre quem está à frente; uniforme e equipamento são próprios da Marinha do Brasil.",
    },
    "operador_radio_policial": {
        "base": "Operador de Rádio Policial",
        "role": "radio",
        "level": 1,
        "cost": 58,
        "hp": 94,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Aciona a central pelo rádio portátil e entrega exatamente 12 suprimentos a cada 12 segundos. Não ataca e precisa ser protegido.",
    },
    "torre_radio_egito": {
        "base": "Torre de Rádio do Egito",
        "role": "radio",
        "level": 1,
        "cost": 72,
        "hp": 165,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Retransmissor militar fixo da escavação Khepra. Gera exatamente 12 suprimentos a cada 12 segundos e resiste mais que os operadores humanos.",
    },
    "estacao_comunicacao_cachoeira": {
        "base": "Estação Móvel da Cachoeira",
        "role": "radio",
        "level": 1,
        "cost": 68,
        "hp": 150,
        "damage": 0,
        "range": 0,
        "cooldown": 12.0,
        "ammo": 0,
        "supply_gain": 12,
        "sprite": 7,
        "ability": "Maleta-relé impermeável da Defesa Civil e da Marinha. Abre antenas e libera exatamente 12 suprimentos a cada 12 segundos; não é um personagem reciclado.",
    },
    "recruta": {
        "base": "Recruta",
        "role": "rifle",
        "level": 1,
        "cost": 45,
        "hp": 92,
        "damage": 11,
        "range": 2,
        "cooldown": 1.05,
        "ammo": 10,
        "sprite": 0,
        "ability": "Pistola: tiro cadenciado em até 2 blocos. Dez tiros derrubam um Caminhante.",
    },
    "soldado": {
        "base": "Soldado",
        "role": "rifle",
        "level": 2,
        "cost": 95,
        "hp": 128,
        "damage": 20,
        "range": 4,
        "cooldown": 0.60,
        "ammo": 18,
        "sprite": 1,
        "ability": "M16: quatro blocos de alcance e fogo sustentado. Ao esvaziar, executa uma recarga própria temporizada.",
    },
    "escopeteiro": {
        "base": "Espingarda de Mão",
        "role": "shotgun",
        "level": 1,
        "cost": 55,
        "hp": 122,
        "damage": 43,
        "range": 1,
        "cooldown": 1.10,
        "ammo": 2,
        "sprite": 3,
        "ability": "Dois cartuchos e alcance curto. Quanto mais perto, mais pellets acertam.",
    },
    "escopeteiro_regular": {
        "base": "Escopeteiro Regular",
        "role": "shotgun",
        "level": 2,
        "cost": 105,
        "hp": 150,
        "damage": 52,
        "range": 3,
        "cooldown": 0.95,
        "ammo": 5,
        "sprite": 3,
        "ability": "Espingarda regular de três blocos; segura os corredores antes da linha.",
    },
    "sniper": {
        "base": "Atirador de Vigia",
        "role": "sniper",
        "level": 1,
        "cost": 75,
        "hp": 82,
        "damage": 58,
        "range": 9,
        "cooldown": 2.10,
        "ammo": 5,
        "sprite": 4,
        "ability": "Mira instável: pode errar. Dano alto, sem execução instantânea.",
    },
    "sniper_regular": {
        "base": "Sniper Regular",
        "role": "sniper",
        "level": 2,
        "cost": 135,
        "hp": 95,
        "damage": 88,
        "range": 9,
        "cooldown": 1.85,
        "ammo": 6,
        "sprite": 4,
        "ability": "Mira garantida e dano alto; ainda não é um hit-kill.",
    },
    "bombardeiro": {
        "base": "Bombardeiro",
        "role": "grenade",
        "level": 1,
        "cost": 100,
        "hp": 112,
        "damage": 70,
        "range": 2,
        "cooldown": 2.25,
        "ammo": 3,
        "sprite": 5,
        "ability": "Granada curta em área. A explosão pode ferir aliados próximos.",
    },
    "granadeiro": {
        "base": "Granadeiro",
        "role": "grenade",
        "level": 2,
        "cost": 150,
        "hp": 124,
        "damage": 88,
        "range": 4,
        "cooldown": 1.75,
        "ammo": 5,
        "sprite": 5,
        "ability": "Lançador de granadas de quatro blocos; controla grupos, mas gasta muita munição.",
    },
    "morteiro": {
        "base": "Morteiro de Campo",
        "role": "mortar",
        "level": 2,
        "cost": 165,
        "hp": 105,
        "damage": 105,
        "range": 3,
        "cooldown": 2.30,
        "ammo": 4,
        "sprite": 5,
        "ability": "Bomba de arco com área ampla. Não mira o primeiro bloco da própria posição.",
    },
    "lanca_chamas": {
        "base": "Lança-Chamas",
        "role": "flame",
        "level": 2,
        "cost": 128,
        "hp": 144,
        "damage": 20,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Exclusivo do Deserto. Cone de fogo reforçado até três blocos; aplica Queimadura contínua.",
    },
    "lanca_chamas_bolso": {
        "base": "Lança-Chamas de Mão",
        "role": "flame",
        "level": 1,
        "cost": 78,
        "hp": 108,
        "damage": 14,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Exclusivo do Deserto. Jato de fogo curto de um bloco; causa dano maior e aplica Queimadura.",
    },
    "lancador_veneno": {
        "base": "Lançador de Veneno",
        "role": "poison",
        "level": 1,
        "cost": 82,
        "hp": 110,
        "damage": 12,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Exclusivo da Cidade. Pulveriza veneno a um bloco e aplica Envenenado: dano contínuo e avanço 12% menor.",
    },
    "canhao_veneno": {
        "base": "Canhão de Veneno",
        "role": "poison",
        "level": 2,
        "cost": 132,
        "hp": 146,
        "damage": 18,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Exclusivo da Cidade. Nuvem tóxica em área até três blocos; mantém grupos Envenenados e mais lentos.",
    },
    "lancador_agua": {
        "base": "Lançador de Água",
        "role": "waterjet",
        "level": 1,
        "cost": 78,
        "hp": 108,
        "damage": 9,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Jato de água curto e pressurizado. Encharca o alvo, apaga queima e reduz o avanço por alguns segundos.",
    },
    "canhao_mare": {
        "base": "Canhão de Maré",
        "role": "waterjet",
        "level": 2,
        "cost": 128,
        "hp": 144,
        "damage": 12,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Canhão de água de três blocos. Pulveriza pequenos grupos, apaga fogo e reduz a velocidade dos encharcados.",
    },
    "morteiro_basico": {
        "base": "Morteiro de Uma Bomba",
        "role": "mortar",
        "level": 1,
        "cost": 82,
        "hp": 88,
        "damage": 66,
        "range": 2,
        "cooldown": 4.35,
        "ammo": 1,
        "sprite": 5,
        "ability": "Lança uma única bomba em área e recarrega muito devagar. É o estágio inicial do morteiro.",
    },
    "radio": {
        "base": "Operador de Rádio",
        "role": "radio",
        "level": 1,
        "cost": 72,
        "hp": 90,
        "damage": 0,
        "range": 0,
        "cooldown": 7.00,
        "ammo": 0,
        "sprite": 7,
        "ability": "Pede suprimento à base: pouca quantidade e entrega lenta. É barato de manter.",
    },
    "torre_radio": {
        "base": "Torre de Rádio",
        "role": "radio",
        "level": 2,
        "cost": 128,
        "hp": 118,
        "damage": 0,
        "range": 0,
        "cooldown": 4.80,
        "ammo": 0,
        "sprite": 7,
        "ability": "Sinal reforçado: suprimento e ritmo médios, sem travar a economia no início.",
    },
    "barreira": {
        "base": "Barreira de Contenção",
        "role": "barrier",
        "level": 1,
        "cost": 58,
        "hp": 360,
        "damage": 0,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 10,
        "ability": "Veículo estático com muita vida para atrasar a horda. Não possui armas.",
    },
    "barreira_reativa": {
        "base": "Barreira Reativa",
        "role": "barrier",
        "level": 2,
        "cost": 104,
        "hp": 470,
        "damage": 70,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 10,
        "ability": "Ao ser destruída, explode e atinge inimigos adjacentes. Continua sem arma.",
    },
    "mina": {
        "base": "Mina de Pressão",
        "role": "mine",
        "level": 1,
        "cost": 42,
        "hp": 1,
        "damage": 105,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "ability": "Elimina um alvo, mas possui chance de falha. Um Núcleo transforma-a em limpeza de linha.",
    },
    "mina_segura": {
        "base": "Mina Segura",
        "role": "mine",
        "level": 2,
        "cost": 74,
        "hp": 1,
        "damage": 150,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "ability": "Disparo garantido contra um único invasor. Reage quando ele pisa na célula.",
    },
    "lancha": {
        "base": "Lancha Patrulha",
        "role": "boat",
        "level": 2,
        "cost": 125,
        "hp": 275,
        "damage": 38,
        "range": 4,
        "cooldown": 0.70,
        "ammo": 16,
        "sprite": 5,
        "water_only": True,
        "ability": "Carta marítima exclusiva da Praia; só pode ser posicionada nas faixas de água do canal.",
    },
    "atirador_lancha": {
        "base": "Atirador de Lancha",
        "role": "boat",
        "level": 1,
        "cost": 78,
        "hp": 158,
        "damage": 22,
        "range": 3,
        "cooldown": 0.86,
        "ammo": 10,
        "sprite": 5,
        "water_only": True,
        "ability": "Barquinho leve com rifle: cobre até três blocos do canal. Tem dez disparos e evolui para a Lancha Patrulha.",
    },
    "submarino": {
        "base": "Submarino",
        "role": "sub",
        "level": 2,
        "cost": 175,
        "hp": 235,
        "damage": 90,
        "range": 6,
        "cooldown": 1.80,
        "ammo": 6,
        "sprite": 6,
        "water_only": True,
        "ability": "Torpedos de grande alcance. Carta marítima exclusiva da Praia: fica indisponível em solo seco.",
    },
    "bomba_agua": {
        "base": "Bomba de Água",
        "role": "mine",
        "level": 2,
        "cost": 80,
        "hp": 1,
        "damage": 190,
        "range": 0,
        "cooldown": 0,
        "ammo": 0,
        "sprite": 11,
        "water_only": True,
        "ability": "Mina marítima segura: só pode ficar submersa e explode em pequenos grupos.",
    },
    "instrutor": {
        "base": "Sargento de Promoção",
        "role": "promoter",
        "level": 2,
        "cost": 135,
        "hp": 120,
        "damage": 0,
        "range": 3,
        "cooldown": 90.0,
        "ammo": 0,
        "sprite": 2,
        "ability": "Personagem legado fora da produção atual.",
    },
}


# Os quatro novos soldados de cada região agora fazem parte da Beta 4 ativa.
# O registro de produção continua sendo a fonte de balanceamento, mas o jogo
# completa aqui os campos comuns usados por seleção, combate e dossiê.
_EXPANSION_COMBAT_CLASS = {
    "sniper": 2,
    "shotgun": 2,
    "poison": 2,
    "gas_grenade": 2,
    "rocket": 3,
    "heavy": 3,
    "flame": 2,
    "mortar": 3,
    "waterjet": 2,
    "grenade": 3,
    "suicide_bomber": 3,
    "shield": 2,
    "blade": 2,
    "sonar": 2,
    "boat": 2,
    "sub": 3,
}
for _region_entries in EXPANSION_DEFENDERS.values():
    for _key, _source in _region_entries.items():
        _data = dict(_source)
        _data["base"] = _data.pop("name")
        _data.setdefault("level", 1)
        _data.setdefault("sprite", 0)
        _data.setdefault("combat_class", _EXPANSION_COMBAT_CLASS[_data["role"]])
        _data.setdefault(
            "shoot_through_allies",
            _data["role"] not in {"shotgun", "flame", "waterjet", "suicide_bomber", "shield", "blade"},
        )
        _data.setdefault("footprint", 1)
        DEFENSES[_key] = _data


# Tempo de troca de carregador/cano por família de arma. A recarga automática
# só começa depois da última pose de disparo e deixa a unidade sem atacar. O
# intervalo intencional de 8 a 15 segundos substitui por completo a antiga
# dependência de Mecânico/Engenheiro de munição.
WEAPON_RELOAD_SECONDS: dict[str, tuple[float, float]] = {
    "rifle": (9.0, 8.0),
    "shotgun": (11.5, 9.5),
    "sniper": (13.0, 11.0),
    "grenade": (13.5, 11.5),
    "mortar": (15.0, 13.0),
    "flame": (10.5, 9.0),
    "poison": (10.5, 9.0),
    "gas_grenade": (12.0, 10.5),
    "waterjet": (10.0, 8.5),
    "boat": (10.5, 9.0),
    "sub": (14.5, 13.0),
}


def weapon_reload_seconds(stats: dict, ascended: bool = False) -> float:
    """Retorna a recarga da ficha atual, preservando o catálogo legado."""
    if "reload" in stats and int(stats.get("ammo", 0)) > 0:
        seconds = max(0.1, float(stats["reload"]))
        return seconds * (0.82 if ascended else 1.0)
    role = str(stats.get("role", ""))
    level = 2 if int(stats.get("level", 1)) >= 2 else 1
    pair = WEAPON_RELOAD_SECONDS.get(role)
    if pair is None or int(stats.get("ammo", 0)) <= 0:
        return 0.0
    seconds = pair[level - 1]
    if ascended:
        seconds = max(8.0, seconds * 0.82)
    return float(clamp(seconds, 8.0, 15.0))


# O sistema de evolução foi desligado integralmente nesta reconstrução.
PROMOTIONS: dict[str, str] = {}


# Cada degrau de dificuldade cresce na mesma direção: menos economia para o
# jogador, mais vida/dano/densidade para os infectados e intervalos menores.
# Assim não existe mais o caso antigo em que o Fácil tinha inimigos mais fortes
# que o Médio e compensava isso apenas despejando suprimentos no início.
DIFFICULTIES = {
    "easy": {
        "label": "FÁCIL",
        "levels": (2,),
        "initial_supplies": 320,
        "enemy_hp": 0.76,
        "enemy_damage": 0.66,
        "boss_hp": 0.80,
        "boss_damage": 0.70,
        "spawn_count": 0.78,
        "spawn_wait": 1.28,
        "escort_count": 0.70,
        "skill_cooldown": 1.28,
        "defender_damage": 1.18,
        "supply_gain": 1.40,
        "supply_cycle": 0.74,
        "supply_cap": 650,
        "accent": (112, 212, 139),
        "summary": "320 SUP e começo acolhedor; a pressão cresce de forma contínua até a onda 12.",
    },
    "medium": {
        "label": "MÉDIO",
        "levels": (1, 2),
        "initial_supplies": 240,
        "enemy_hp": 1.00,
        "enemy_damage": 1.00,
        "boss_hp": 1.00,
        "boss_damage": 0.98,
        "spawn_count": 1.00,
        "spawn_wait": 1.00,
        "escort_count": 1.00,
        "skill_cooldown": 1.00,
        "defender_damage": 1.00,
        "supply_gain": 1.00,
        "supply_cycle": 1.00,
        "supply_cap": 430,
        "accent": GOLD,
        "summary": "240 SUP; início ensinável, meio exigente e reta final de alta pressão.",
    },
    "hard": {
        "label": "DIFÍCIL",
        "levels": (1,),
        "initial_supplies": 190,
        "enemy_hp": 1.20,
        "enemy_damage": 1.20,
        "boss_hp": 1.25,
        "boss_damage": 1.20,
        "spawn_count": 1.18,
        "spawn_wait": 0.88,
        "escort_count": 1.20,
        "skill_cooldown": 0.82,
        "defender_damage": 0.94,
        "supply_gain": 0.86,
        "supply_cycle": 1.12,
        "supply_cap": 330,
        "accent": RED,
        "summary": "190 SUP; dá para montar a defesa inicial, mas a onda 12 exige counters e economia.",
    },
}


def difficulty_profile(key: str) -> dict:
    """Retorna sempre um modo válido, inclusive em salvamentos antigos."""
    return DIFFICULTIES.get(key, DIFFICULTIES["medium"])


REGION_ROSTERS = {
    "city": (
        ("xerife_rua", "Xerife de Rua"),
        ("agente_swat", "Agente Tático da SWAT"),
        ("operador_radio_policial", "Operador de Rádio Policial"),
        ("atirador_precisao_swat", "Atirador de Precisão"),
        ("agente_entrada", "Agente de Entrada"),
        ("especialista_antipraga", "Especialista Antipraga"),
        ("lancador_foguetes", "Lançador de Foguetes"),
        ("escudeiro_tropa_choque", "Escudeiro da Tropa de Choque"),
    ),
    "desert": (
        ("pistoleiro_deserto", "Pistoleiro do Deserto"),
        ("fuzileiro_deserto", "Fuzileiro do Deserto"),
        ("torre_radio_egito", "Torre de Rádio do Egito"),
        ("atirador_horizonte", "Atirador do Horizonte"),
        ("tenente_artilheiro", "Tenente Artilheiro"),
        ("incinerador_deserto", "Incinerador do Deserto"),
        ("nomade_morteiro", "Nômade do Morteiro"),
        ("guardiao_laminas", "Guardião de Lâminas"),
    ),
    "beach": (
        ("marinheiro", "Marinheiro"),
        ("fuzileiro_marinha", "Fuzileiro da Marinha"),
        ("estacao_comunicacao_cachoeira", "Estação Móvel da Cachoeira"),
        ("atirador_precisao_marinha", "Atirador de Precisão Naval"),
        ("bombeiro_hidraulico", "Bombeiro Hidráulico"),
        ("granadeiro_profundidades", "Granadeiro das Profundidades"),
        ("barco_patrulha", "Barco de Patrulha"),
        ("submarino_tatico", "Submarino Tático"),
    ),
}


# Cada carta ativa possui uma identidade narrativa e, principalmente, uma
# razão mecânica própria para existir. O carrossel usa esta fonte única; assim
# a seleção não promete uma função que o combate desconhece.
CARD_DETAILS = {
    "xerife_rua": {
        "lore": "Primeiro policial a isolar o Terminal Félix-13, manteve as ruas abertas com uma arma curta e decisões rápidas.",
        "function": "Patrulha econômica de dois blocos, tiro forte e recarga curta.",
        "need": "É a resposta barata para segurar as primeiras linhas sem consumir a economia das cartas pesadas.",
    },
    "agente_swat": {
        "lore": "Agente da equipe de contenção de Nova York, treinado para sustentar corredores estreitos sob pressão contínua.",
        "function": "Supressão rápida a três blocos, atravessando a formação aliada.",
        "need": "Mantém Corredores sob fogo sem bloquear a própria linha; troca potência por cadência.",
    },
    "operador_radio_policial": {
        "lore": "Ligação móvel entre as patrulhas isoladas e o depósito de emergência da cidade.",
        "function": "Geração periódica de suprimentos, sem capacidade ofensiva.",
        "need": "Sustenta formações caras nas ondas longas; sem ele a reserva acaba antes dos chefes.",
    },
    "atirador_precisao_swat": {
        "lore": "Observador da SWAT posicionado nos telhados que ainda não cederam à contaminação.",
        "function": "Perfuração de armadura e eliminação prioritária de alvos resistentes.",
        "need": "O tiro de precisão contorna imunidade a munição convencional de coletes infectados.",
    },
    "agente_entrada": {
        "lore": "Especialista de entrada da Tropa de Choque, acostumado a romper portas e formações compactas.",
        "function": "Escopeta de impacto a curta distância e quebra de guarda.",
        "need": "Com o Escudeiro, é a única doutrina capaz de abrir a defesa dos Brutos urbanos.",
    },
    "especialista_antipraga": {
        "lore": "Pesquisador de campo que converteu reagentes confiscados da Félix em composto anticontaminação.",
        "function": "Granadas de gás venenoso e reagente anticorrosivo que abrem uma nuvem química em área.",
        "need": "Remove a blindagem biológica do Policial Infectado, imune a balas comuns enquanto protegido.",
    },
    "lancador_foguetes": {
        "lore": "Operador pesado chamado quando veículos e estruturas da quarentena viraram cobertura para a horda.",
        "function": "Demolição estrutural em área, lenta e de alto impacto.",
        "need": "Quebra alvos estruturais; inimigos anti-explosão impedem que seja uma solução universal.",
    },
    "escudeiro_tropa_choque": {
        "lore": "Vanguarda da Tropa de Choque, responsável por receber a primeira colisão e manter o corredor aberto.",
        "function": "Bloqueio corpo a corpo e ruptura de investidas pesadas.",
        "need": "Neutraliza a guarda dos Brutos e impede que a primeira carga atravesse soldados frágeis.",
    },
    "pistoleiro_deserto": {
        "lore": "Batedor egípcio da escavação Khepra, habituado a conservar munição durante patrulhas no deserto.",
        "function": "Magnum de dois blocos, tiro forte e recarga curta.",
        "need": "Interrompe conjurações menores sem consumir o grande pente das tropas automáticas.",
    },
    "fuzileiro_deserto": {
        "lore": "Fuzileiro das forças egípcias adaptado à areia e aos corredores estreitos das ruínas.",
        "function": "Rajada de três blocos que cobre aliados posicionados à frente.",
        "need": "Suprime enxames de múmias e protege as unidades de counter enquanto trabalham.",
    },
    "torre_radio_egito": {
        "lore": "Retransmissor blindado erguido quando as paredes da necrópole bloquearam o contato com o comando.",
        "function": "Economia resistente e estável, porém fixa e sem ataque.",
        "need": "Financia armamento pesado no deserto sem expor um operador humano às maldições.",
    },
    "atirador_horizonte": {
        "lore": "Vigia de longo alcance que identifica o núcleo luminoso por trás das faixas contaminadas.",
        "function": "Precisão contra curandeiros e hospedeiros protegidos.",
        "need": "Perfura núcleos que ignoram balas convencionais e impede a recuperação da horda.",
    },
    "tenente_artilheiro": {
        "lore": "Oficial que manteve a metralhadora da expedição funcionando depois da queda do comboio.",
        "function": "Fixação de subchefes por fogo pesado contínuo.",
        "need": "Mantém Mutantes sob supressão para que counters corpo a corpo consigam alcançá-los.",
    },
    "incinerador_deserto": {
        "lore": "Especialista criado após a equipe descobrir que as faixas funerárias continuavam se regenerando.",
        "function": "Dano térmico contínuo e bloqueio de regeneração.",
        "need": "É a resposta direta às múmias regenerativas e aos Curandeiros da necrópole.",
    },
    "nomade_morteiro": {
        "lore": "Artilheiro móvel que calcula disparos por cima das dunas e das colunas destruídas.",
        "function": "Bombardeio indireto contra concentrações e inimigos entrincheirados.",
        "need": "Atinge ameaças enterradas, mas a resistência explosiva dos elites exige apoio especializado.",
    },
    "guardiao_laminas": {
        "lore": "Duelista da guarda de Khepra que estudou o ritmo das lâminas reanimadas dentro da pirâmide.",
        "function": "Aparo corpo a corpo e desarme de inimigos laminados.",
        "need": "Única unidade que rompe a guarda do Zumbi de Lâmina; sem ela o alvo rejeita tiro e explosão.",
    },
    "marinheiro": {
        "lore": "Marinheiro da base mineira que organizou a primeira defesa terrestre após a água mudar de cor.",
        "function": "Pistola de dois blocos, econômica e de recarga rápida.",
        "need": "Segura as margens com baixo consumo e libera recursos para a defesa cara dos canais.",
    },
    "fuzileiro_marinha": {
        "lore": "Fuzileiro naval destacado para impedir que a infestação suba da cachoeira até as cidades próximas.",
        "function": "Cobertura automática terrestre de três blocos.",
        "need": "Protege operadores aquáticos e derruba corredores antes que alcancem a margem.",
    },
    "estacao_comunicacao_cachoeira": {
        "lore": "Estação móvel construída com rádio naval e sensores locais, sem reciclar equipamento de Nova York ou do Egito.",
        "function": "Geração de suprimentos para a força brasileira.",
        "need": "Mantém Barco e Submarino operacionais; ambos têm custo incompatível com uma economia sem suporte.",
    },
    "atirador_precisao_marinha": {
        "lore": "Observador naval treinado para enxergar cilindros, válvulas e pontos fracos sob a água turva.",
        "function": "Perfuração precisa contra mergulhadores e criaturas infladas.",
        "need": "Acerta componentes que munição convencional espalhada não consegue atravessar.",
    },
    "bombeiro_hidraulico": {
        "lore": "Bombeiro de resgate que transformou a bomba de alta pressão em ferramenta de descontaminação.",
        "function": "Jato hidráulico que desacelera e remove cobertura tóxica.",
        "need": "Lava a proteção química dos infectados e cria tempo para as armas terrestres finalizarem o alvo.",
    },
    "granadeiro_profundidades": {
        "lore": "Granadeiro naval equipado para lançar cargas sobre pedras e curvas do canal.",
        "function": "Controle explosivo de grupos na água e nas margens.",
        "need": "Interrompe enxames aquáticos, mas elites resistentes a explosão exigem Sonar ou precisão.",
    },
    "homem_bomba": {
        "lore": "Voluntário da contenção que permanece imóvel junto à carga para impedir uma ruptura inevitável da linha.",
        "function": "Armadilha humana fixa com detonação instantânea por contato.",
        "need": "Último bloqueio contra um alvo que atravessou o fogo; não pode perseguir nem ser reutilizado.",
    },
    "operador_sonar": {
        "lore": "Hidrografista naval que adaptou um sonar portátil para localizar mutações abaixo da superfície.",
        "function": "Revelação do canal e ruptura de camuflagem submersa.",
        "need": "Única unidade que expõe a blindagem do Mergulhador antes que tiros e torpedos possam feri-lo.",
    },
    "barco_patrulha": {
        "lore": "Lancha leve enviada por um canal de manutenção até a zona isolada da cachoeira.",
        "function": "Fogo sustentado exclusivo das duas linhas de água.",
        "need": "Oferece cadência onde tropas terrestres não podem ser colocadas e segura nadadores numerosos.",
    },
    "submarino_tatico": {
        "lore": "Submersível compacto de inspeção convertido para caçar organismos grandes na água contaminada.",
        "function": "Torpedo de perfuração contra blindados e chefes aquáticos.",
        "need": "É a resposta pesada do canal: pouca cadência, mas multiplicador contra carapaças e chefes submersos.",
    },
}

for _region, _roster in REGION_ROSTERS.items():
    for _card_key, _display in _roster:
        _detail = CARD_DETAILS[_card_key]
        DEFENSES[_card_key]["lore"] = _detail["lore"]
        DEFENSES[_card_key]["tactical_function"] = _detail["function"]
        DEFENSES[_card_key]["mechanical_need"] = _detail["need"]
        # Identificador estável usado por testes e pela interface. Nenhuma
        # carta ativa pode compartilhar a mesma utilidade mecânica.
        DEFENSES[_card_key]["unique_utility"] = _card_key


# Doutrinas da força urbana de Nova York. A Unidade não é somente um rótulo:
# ela define ocupação, alvo preferencial e uma vantagem com contrapartida.
CITY_TACTICAL_UNITS = {
    "xerife_rua": ("Patrulha Básica", 1, "Tiro forte e recarga curta por baixo custo.", "Alcance curto e não atravessa aliados."),
    "agente_swat": ("SWAT de Supressão", 1, "Rajada atravessa a formação aliada.", "Dano por projétil baixo e recarga longa."),
    "operador_radio_policial": ("Comando e Logística", 1, "Gera suprimentos durante a onda sem exigir outra carta.", "Não ataca e precisa ser protegido."),
    "atirador_precisao_swat": ("SWAT de Observação", 1, "Prioriza alvos de maior vida.", "Cadência baixa e fraco contra enxames."),
    "agente_entrada": ("Tropa de Choque", 1, "Leque devastador à queima-roupa.", "Só cobre a casa imediatamente à frente."),
    "especialista_antipraga": ("Unidade Antipraga", 2, "A nuvem química corrói blindagem biológica e contamina grupos.", "Ocupa duas casas, usa tambor de seis granadas e recarrega lentamente."),
    "lancador_foguetes": ("Resposta Pesada", 2, "Explosão quebra grupos e blindados.", "Ocupa duas casas, um disparo e recarga longa."),
    "escudeiro_tropa_choque": ("Tropa de Choque", 1, "Interrompe a primeira investida recebida.", "Corpo a corpo e sem resposta a atacantes distantes."),
}
for _key, (_unit, _space, _advantage, _disadvantage) in CITY_TACTICAL_UNITS.items():
    DEFENSES[_key]["tactical_unit"] = _unit
    DEFENSES[_key]["footprint"] = _space
    DEFENSES[_key]["situational_advantage"] = _advantage
    DEFENSES[_key]["situational_disadvantage"] = _disadvantage
    DEFENSES[_key]["ability"] = f"{DEFENSES[_key]['ability']} Unidade {_unit}: {_advantage} Limite: {_disadvantage}"


# Índices de atlas por carta, região e nível. Eles não podem ser inferidos
# apenas pelo "papel" da unidade: as três folhas de arte têm ordens próprias
# e uma célula N1 não representa automaticamente sua evolução N2. Esta é a
# única fonte usada pela seleção, pelo HUD, pelo dossiê e pela tropa em campo.
CARD_ATLAS_INDEX = {
    "city": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "bombardeiro": 5, "granadeiro": 5,
        "morteiro_basico": 5, "morteiro": 5,
        "radio": 7, "torre_radio": 7,
        "lanca_chamas_bolso": 9, "lanca_chamas": 9,
        "lancador_veneno": 9, "canhao_veneno": 9,
        "barreira": 10, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
    },
    "desert": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "morteiro_basico": 5, "morteiro": 5,
        "bombardeiro": 6, "granadeiro": 5,
        "radio": 8, "torre_radio": 7,
        "lanca_chamas_bolso": 10, "lanca_chamas": 9,
        "barreira": 11, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
    },
    "beach": {
        "recruta": 0, "soldado": 1, "instrutor": 2,
        "escopeteiro": 3, "escopeteiro_regular": 3,
        "sniper": 4, "sniper_regular": 4,
        "morteiro_basico": 5, "morteiro": 5,
        "bombardeiro": 7, "granadeiro": 5,
        "radio": 9, "torre_radio": 7,
        "lancador_agua": 9, "canhao_mare": 9,
        "barreira": 11, "barreira_reativa": 10,
        "mina": 11, "mina_segura": 11,
    },
}


# Estas cartas não possuíam um retrato exclusivo na folha regional. Cada uma
# recebe uma arte v7.8 que representa precisamente a classe indicada, em vez
# de reutilizar uma arte de outra carta só por ocupar a mesma célula do atlas.
CARD_ART_ASSETS = {
    ("city", "lancador_veneno"): "city_poison_sprayer_n1",
    ("city", "canhao_veneno"): "city_poison_cannon_n2",
    ("city", "morteiro_basico"): "city_mortar_n1",
    ("city", "morteiro"): "city_mortar_n2",
    ("desert", "mina"): "desert_mine_n1",
    ("desert", "morteiro"): "desert_mortar_n2",
    ("beach", "lancador_agua"): "beach_water_launcher_n1",
    ("beach", "canhao_mare"): "beach_water_cannon_n2",
    ("beach", "morteiro_basico"): "beach_mortar_n1",
    ("beach", "morteiro"): "beach_mortar_n2",
}


def regional_sprite_index(region: str, key: str) -> int:
    """Escolhe a célula correta da folha de artes para a região e o nível.

    A grade de seleção e o objeto posicionado usam esta mesma regra. Antes,
    a carta usava o índice genérico enquanto a tropa no campo recebia um
    remapeamento regional separado; daí surgiam N1 e N2 com artes trocadas
    em alguns mapas. Uma única fonte elimina essa mistura.
    """
    return int(CARD_ATLAS_INDEX.get(region, {}).get(key, DEFENSES[key]["sprite"]))


ENEMIES = {
    "infectado_urbano": {
        "name": "Infectado Urbano",
        "hp": 124,
        "speed": 11,
        "damage": 17,
        "attack": 1.2,
        "sprite": 0,
        "ability": "Infectado básico de Nova York. Avança mancando e ataca com uma mordida curta.",
    },
    "desperto_khepra": {
        "name": "Desperto de Khepra",
        "hp": 130,
        "speed": 10.5,
        "damage": 17,
        "attack": 1.18,
        "sprite": 0,
        "ability": "Múmia básica despertada pela contaminação. É um pouco mais resistente, mas não possui poder especial.",
    },
    "afogado_cachoeira": {
        "name": "Afogado da Cachoeira",
        "hp": 126,
        "speed": 11,
        "damage": 16,
        "attack": 1.16,
        "sprite": 0,
        "ability": "Infectado terrestre da área da cachoeira. Avança somente pelas margens; não ocupa os canais.",
    },
    "corredor_cidade": {
        "name": "Corredor do Metrô",
        "hp": 340,
        "speed": 24,
        "damage": 46,
        "attack": 0.78,
        "sprite": 1,
        "armor": 0.25,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed", "signal_jammer"),
        "ability": "Infectado urbano resistente. Corre em velocidade constante, ignora interrupções por tiro e causa dano dobrado somente na primeira mordida.",
    },
    "corredor_deserto": {
        "name": "Corredor da Necrópole",
        "hp": 360,
        "speed": 22,
        "damage": 54,
        "attack": 0.82,
        "sprite": 1,
        "armor": 0.26,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed"),
        "ability": "Múmia leve e resistente. Mantém corrida constante, não sofre interrupção por dano e abre o combate com um golpe dobrado.",
    },
    "corredor_cachoeira": {
        "name": "Corredor da Trilha",
        "hp": 350,
        "speed": 23,
        "damage": 39,
        "attack": 0.80,
        "sprite": 1,
        "armor": 0.25,
        "first_attack_multiplier": 2.0,
        "contact_distance": 72,
        "tags": ("runner", "unstaggerable", "constant_speed"),
        "ability": "Turista contaminado das trilhas. Corre sem dash, ignora stagger e desfere um primeiro ataque dobrado antes de voltar ao dano normal.",
    },
    "rastejador_cidade": {
        "name": "Rastejador dos Túneis",
        "hp": 420,
        "speed": 6,
        "damage": 34,
        "attack": 1.30,
        "sprite": 1,
        "armor": 0.18,
        "devour_classes": (1, 2),
        "ability": "Ex-funcionário dos túneis, com as duas pernas amputadas. É lento e muito resistente; ao alcançar tropas de Classe 1 ou 2, devora o alvo.",
    },
    "rastejador_deserto": {
        "name": "Rastejador Mumificado",
        "hp": 450,
        "speed": 5.5,
        "damage": 38,
        "attack": 1.40,
        "sprite": 1,
        "armor": 0.20,
        "devour_classes": (1, 2),
        "ability": "Múmia sem as pernas, coberta por faixas e areia contaminada. É extremamente resistente e devora tropas de Classe 1 ou 2 ao alcançá-las.",
    },
    "rastejador_cachoeira": {
        "name": "Rastejador do Cânion",
        "hp": 435,
        "speed": 6,
        "damage": 36,
        "attack": 1.35,
        "sprite": 1,
        "armor": 0.19,
        "devour_classes": (1, 2),
        "ability": "Antigo guia de resgate de Minas, com as duas pernas amputadas. Avança lentamente e devora tropas de Classe 1 ou 2 ao alcançar a defesa.",
    },
    "caminhante": {
        "name": "Caminhante",
        "hp": 108,
        "speed": 12,
        "damage": 12,
        "attack": 1.2,
        "sprite": 0,
        "ability": "Lento, pouca vida e pouco dano. Pressiona apenas pelo número.",
    },
    "corredor": {
        "name": "Corredor",
        "hp": 94,
        "speed": 24,
        "damage": 27,
        "attack": 0.75,
        "sprite": 1,
        "ability": "Dá um arranque inicial; pune linhas sem escopeta, mina ou barreira.",
        "tags": ("dash",),
    },
    "rastejante": {
        "name": "Rastejante",
        "hp": 158,
        "speed": 9,
        "damage": 29,
        "attack": 1.05,
        "sprite": 1,
        "ability": "Mais lento que o Caminhante, mas morde com força quando alcança uma defesa.",
    },
    "conehead": {
        "name": "Blindado de Cone",
        "hp": 185,
        "speed": 11,
        "damage": 15,
        "attack": 1.0,
        "sprite": 2,
        "ability": "Cone e colete reflexivo absorvem fogo leve. Força foco ou explosão.",
        "armor": 0.18,
    },
    "policial": {
        "name": "Policial Infectado",
        "hp": 220,
        "speed": 10,
        "damage": 17,
        "attack": 1.0,
        "sprite": 3,
        "ability": "Colete balístico e tiros curtos contra a linha de defesa.",
        "armor": 0.25,
        "tags": ("gun",),
    },
    "militar": {
        "name": "Militar Infectado",
        "hp": 300,
        "speed": 9,
        "damage": 25,
        "attack": 0.9,
        "sprite": 4,
        "ability": "Armadura reforçada e arma de fogo. Exige dano concentrado ou corrosão controlada.",
        "armor": 0.38,
        "tags": ("gun",),
    },
    "escudo": {
        "name": "Porta-Escudo",
        "hp": 260,
        "speed": 8,
        "damage": 33,
        "attack": 1.05,
        "sprite": 5,
        "ability": "Escudo bloqueia boa parte do fogo frontal; a granada e o lança-chamas ajudam a quebrar a coluna.",
        "armor": 0.48,
        "tags": ("shield",),
    },
    "cuspidor": {
        "name": "Cuspidor Ácido",
        "hp": 178,
        "speed": 12,
        "damage": 14,
        "attack": 1.1,
        "sprite": 6,
        "ability": "Cospe até três blocos: corrosão reduz o desempenho e o ácido causa dano contínuo.",
        "tags": ("acid",),
    },
    "divisor": {
        "name": "Divisor",
        "hp": 300,
        "speed": 7,
        "damage": 34,
        "attack": 1.05,
        "sprite": 7,
        "ability": "Robusto e lento; sua morte explode em área, com dano físico e corrosivo.",
        "tags": ("acid", "explode_death"),
    },
    "gritador": {
        "name": "Gritador",
        "hp": 160,
        "speed": 11,
        "damage": 14,
        "attack": 1.1,
        "sprite": 8,
        "ability": "Acelera infectados próximos e pode chamar uma pequena horda.",
        "tags": ("scream",),
    },
    "saltador": {
        "name": "Saltador",
        "hp": 152,
        "speed": 16,
        "damage": 24,
        "attack": 0.9,
        "sprite": 9,
        "ability": "Ultrapassa somente a primeira defesa que bloquear seu caminho; depois precisa enfrentar a próxima.",
        "tags": ("jump",),
    },
    "bruto": {
        "name": "Bruto de Demolição",
        "hp": 450,
        "speed": 7,
        "damage": 48,
        "attack": 0.9,
        "sprite": 10,
        "ability": "Sub-chefe pesado; seus impactos deixam a linha vulnerável.",
        "tags": ("stomp",),
    },
    "digger": {
        "name": "Escavador",
        "hp": 185,
        "speed": 13,
        "damage": 42,
        "attack": 0.88,
        "sprite": 2,
        "ability": "Cava visivelmente sob o terreno e atravessa apenas a primeira defesa da frente, como um salto subterrâneo.",
        "tags": ("dig",),
    },
    "ladrao": {
        "name": "Ladrão de Suprimentos",
        "hp": 135,
        "speed": 14,
        "damage": 10,
        "attack": 1.2,
        "sprite": 3,
        "ability": "Mago das ruínas: rouba créditos. Clique nele antes que alcance a linha para recuperar a carga.",
        "tags": ("steal",),
    },
    "curandeiro": {
        "name": "Curandeiro Mortal",
        "hp": 190,
        "speed": 10,
        "damage": 12,
        "attack": 1.1,
        "sprite": 4,
        "ability": "Arremessa poções que curam aliados e pode devolver um derrotado à luta uma vez.",
        "tags": ("heal",),
    },
    "parasita": {
        "name": "Parasita das Dunas",
        "hp": 255,
        "speed": 9,
        "damage": 30,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Agarra uma tropa, corta seu ataque e atordoa até dois blocos à frente.",
        "tags": ("parasite",),
    },
    "mutante": {
        "name": "Mutante de Ruínas",
        "hp": 400,
        "speed": 7,
        "damage": 42,
        "attack": 0.9,
        "sprite": 6,
        "ability": "Sub-chefe com hospedeiro armado nas costas e soco que atordoa uma área.",
        "tags": ("stomp", "gun"),
    },
    "necromante_minion": {
        "name": "Múmia Invocada",
        "hp": 130,
        "speed": 15,
        "damage": 18,
        "attack": 1.0,
        "sprite": 7,
        "ability": "Múmia fraca convocada pelo Necromante; existe para consumir munição e cobertura.",
    },
    "boia": {
        "name": "Turista de Boia",
        "hp": 135,
        "speed": 9,
        "damage": 15,
        "attack": 1.1,
        "sprite": 0,
        "ability": "Lento na água, mas a boia o protege de uma parte do dano.",
        "armor": 0.12,
    },
    "surfista": {
        "name": "Surfista Infectado",
        "hp": 122,
        "speed": 25,
        "damage": 25,
        "attack": 0.8,
        "sprite": 1,
        "ability": "A prancha cria um dash aquático, obrigando reação rápida nas faixas molhadas.",
        "tags": ("dash",),
    },
    "salva_vidas": {
        "name": "Salva-Vidas de Escudo",
        "hp": 225,
        "speed": 10,
        "damage": 25,
        "attack": 1.0,
        "sprite": 2,
        "ability": "Boia-escudo reduz o dano frontal e protege a maré atrás dele.",
        "armor": 0.40,
        "tags": ("shield",),
    },
    "mergulhador": {
        "name": "Mergulhador Blindado",
        "hp": 275,
        "speed": 10,
        "damage": 33,
        "attack": 0.92,
        "sprite": 3,
        "ability": "Armadura de mergulho espessa; pode atingir embarcações com força.",
        "armor": 0.30,
        "tags": ("naval_hunter",),
    },
    "cacador": {
        "name": "Caçador da Costa",
        "hp": 180,
        "speed": 15,
        "damage": 32,
        "attack": 0.85,
        "sprite": 4,
        "ability": "Persegue a defesa mais próxima com investida de arpão.",
        "tags": ("jump",),
    },
    "cowboy": {
        "name": "Cowboy da Maré",
        "hp": 205,
        "speed": 12,
        "damage": 18,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Dispara de longe na costa e pressiona o rádio e a retaguarda.",
        "tags": ("gun",),
    },
    "sal_cuspidor": {
        "name": "Cuspidor de Sal",
        "hp": 182,
        "speed": 12,
        "damage": 15,
        "attack": 1.0,
        "sprite": 6,
        "ability": "Sal pressurizado corrói metal e descarrega as armas em contato.",
        "tags": ("acid",),
    },
    "mar_gritador": {
        "name": "Gritador de Maré",
        "hp": 175,
        "speed": 11,
        "damage": 15,
        "attack": 1.0,
        "sprite": 7,
        "ability": "O grito acelera nadadores e chama reforços vindos da arrebentação.",
        "tags": ("scream",),
    },
    "nadador": {
        "name": "Nadador",
        "hp": 180,
        "speed": 18,
        "damage": 25,
        "attack": 0.92,
        "sprite": 8,
        "ability": "Movimenta-se bem nas faixas de água e passa por minas terrestres.",
    },
}

# Três ameaças adicionais por região completam seis zumbis comuns próprios.
# Nenhuma delas depende de magia: toda habilidade nasce de equipamento
# contaminado, mutação biológica ou das condições físicas do desastre.
ENEMIES.update({
    "policial_helix": {
        "name": "Policial Infectado da Félix",
        "hp": 218, "speed": 9.2, "damage": 18, "attack": 1.05, "sprite": 3,
        "armor": 0.34, "tags": ("shield",),
        "ability": "Colete e capacete absorvem os primeiros tiros; corrosão e precisão quebram a proteção.",
    },
    "cientista_helix": {
        "name": "Cientista da Félix",
        "hp": 164, "speed": 9.5, "damage": 15, "attack": 1.15, "sprite": 6,
        "tags": ("acid",),
        "ability": "O cilindro rompido lança composto corrosivo a até três blocos, sem qualquer poder sobrenatural.",
    },
    "tecnico_subestacao": {
        "name": "Técnico da Subestação",
        "hp": 176, "speed": 11.0, "damage": 16, "attack": 1.05, "sprite": 8,
        "tags": ("shock",),
        "ability": "Baterias presas ao corpo descarregam um pulso curto que atrasa a tropa mais próxima.",
    },
    "arqueiro_necropole": {
        "name": "Arqueiro da Necrópole",
        "hp": 152, "speed": 10.8, "damage": 17, "attack": 1.08, "sprite": 3,
        "tags": ("gun",),
        "ability": "Ataca à distância com um arco físico preservado; é perigoso, mas possui pouca vida.",
    },
    "hospedeiro_escaravelhos": {
        "name": "Hospedeiro de Escaravelhos",
        "hp": 238, "speed": 8.2, "damage": 21, "attack": 1.12, "sprite": 7,
        "armor": 0.16, "tags": ("explode_death",),
        "ability": "A colônia alterada no torso se espalha no impacto final e pune tropas amontoadas.",
    },
    "saqueador_canopico": {
        "name": "Saqueador Canópico",
        "hp": 146, "speed": 13.0, "damage": 12, "attack": 1.18, "sprite": 3,
        "tags": ("steal",),
        "ability": "Prioriza a retaguarda e rouba uma pequena carga de suprimentos usando recipientes da escavação.",
    },
    "pescador_praga": {
        "name": "Pescador da Praga",
        "hp": 186, "speed": 10.4, "damage": 18, "attack": 1.10, "sprite": 6,
        "tags": ("net",), "amphibious": True,
        "ability": "Lança uma rede contaminada que reduz por instantes a cadência da defesa mais próxima.",
    },
    "baiacu_mutante": {
        "name": "Baiacu Mutante",
        "hp": 520, "speed": 6.8, "damage": 36, "attack": 1.12, "sprite": 9,
        "armor": 0.28, "tags": ("explode_death", "stomp"),
        "ability": "Subchefe aquático: infla sob fogo e espalha espinhos somente na própria faixa ao ser abatido.",
    },
})

ENEMIES["bruto"].update({
    "name": "Demolidor do Metrô",
    "ability": "Subchefe industrial: marreta duas casas próximas e exige contenção antes do contato.",
})
ENEMIES["divisor"].update({
    "name": "Bruto da Quarentena",
    "ability": "Subchefe dentro de um traje Félix rompido; as placas reduzem explosões frontais.",
})
ENEMIES["policial"].update({
    "name": "Comandante Infectado",
    "ability": "Subchefe policial mutado: coordena a faixa e dispara rajadas curtas contra a retaguarda.",
})
ENEMIES["parasita"].update({
    "name": "Guardião do Sarcófago",
    "ability": "Escudo funerário contaminado desvia fogo frontal até o Guardião de Lâminas abrir sua postura.",
})
ENEMIES["curandeiro"].update({
    "name": "Sacerdote da Praga",
    "ability": "Incensário químico restaura tecido infectado próximo; o Incinerador interrompe a regeneração.",
})
ENEMIES["mutante"].update({
    "name": "Executor da Escavação",
    "ability": "Subchefe pesado fundido a ferramentas do sítio; golpeia o chão e quebra formações compactas.",
})
ENEMIES["salva_vidas"].update({
    "name": "Salva-Vidas Colossal",
    "ability": "Subchefe anfíbio: investida de resgate mutada derruba a cadência das tropas na própria faixa.",
})
ENEMIES["cacador"].update({
    "name": "Caçador das Profundidades",
    "ability": "Subchefe de mergulho blindado que avança com arpão; sonar e precisão naval expõem suas placas.",
})


BOSSES = {
    "bruto_demolidor": {
        "name": "BRUTO DEMOLIDOR",
        "hp": 1000,
        "speed": 6,
        "damage": 30,
        "attack": 1.05,
        "sprite": 10,
        "ability": "Entrada: paralisa militares por 3 s. Depois, o Martelo fecha só a própria faixa por 1,2 s a cada 18 s.",
        "type": "bruto_demolidor",
    },
    "comandante_mortos": {
        "name": "COMANDANTE DOS MORTOS",
        "hp": 1200,
        "speed": 9,
        "damage": 26,
        "attack": 0.88,
        "sprite": 11,
        "ability": "Entrada: dá fúria breve à escolta. Depois, dispara rajadas duplas leves e reacelera somente aliados próximos.",
        "type": "comandante",
    },
    "cuspidor_alfa": {
        "name": "CUSPIDADOR ALFA",
        "hp": 1600,
        "speed": 11,
        "damage": 28,
        "attack": 0.95,
        "sprite": 11,
        "ability": "Entrada: névoa ácida global de 1,2 s. Depois, cospe em um alvo na própria faixa, com corrosão curta.",
        "type": "alfa",
    },
    "mutante_ruinas": {
        "name": "MUTANTE DAS RUÍNAS",
        "hp": 1100,
        "speed": 6,
        "damage": 32,
        "attack": 0.98,
        "sprite": 6,
        "ability": "Entrada: abalo leve nas faixas vizinhas. Depois, golpeia somente tropas próximas por 1 s de atordoamento.",
        "type": "mutante",
    },
    "necromante": {
        "name": "NECROMANTE",
        "hp": 1350,
        "speed": 7,
        "damage": 23,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: invoca uma múmia. Depois, invoca uma por ciclo e cura pouco os aliados próximos.",
        "type": "necromante",
    },
    "colosso_mutante": {
        "name": "COLOSSO MUTANTE",
        "hp": 1850,
        "speed": 4,
        "damage": 38,
        "attack": 1.05,
        "sprite": 11,
        "ability": "Entrada: tremor global de 1,2 s. Depois, arremessa uma rocha leve contra uma faixa-alvo.",
        "type": "colosso",
    },
    "tide_brute": {
        "name": "BRUTO DA MARÉ",
        "hp": 1050,
        "speed": 6,
        "damage": 34,
        "attack": 1.0,
        "sprite": 9,
        "ability": "Entrada: uma onda leve abala a faixa de água. Depois, golpeia boias e embarcações apenas perto da maré.",
        "type": "tide",
    },
    "cacador_abissal": {
        "name": "CAÇADOR ABISSAL",
        "hp": 1450,
        "speed": 11,
        "damage": 26,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: avança uma distância curta no canal. Depois, mergulha pouco e ataca uma embarcação próxima.",
        "type": "hunter",
    },
    "leviata": {
        "name": "LEVIATÃ",
        "hp": 2050,
        "speed": 5,
        "damage": 42,
        "attack": 1.0,
        "sprite": 11,
        "ability": "Entrada: uma maré moderada atinge o canal. Depois, lança um jato concentrado numa embarcação da própria faixa.",
        "type": "leviathan",
    },
}

BOSSES["bruto_demolidor"]["name"] = "DIRETOR DEMOLIDOR DA FÉLIX"
BOSSES["comandante_mortos"]["name"] = "COMANDANTE ISOTÓPICO"
BOSSES["cuspidor_alfa"]["name"] = "DIRETOR ZERO CORROSIVO"
BOSSES["mutante_ruinas"]["name"] = "GUARDIÃO ANÚBIS CONTAMINADO"
BOSSES["necromante"]["name"] = "COMANDANTE DA NECRÓPOLE"
BOSSES["colosso_mutante"]["name"] = "COLOSSO DA PIRÂMIDE"
BOSSES["tide_brute"]["name"] = "BRUTO DA CACHOEIRA"
BOSSES["cacador_abissal"]["name"] = "CAÇADOR ABISSAL"
BOSSES["leviata"]["name"] = "COLOSSO DO VÉU VERDE"

REGION_SUBBOSSES = {
    "city": ("bruto", "divisor", "policial"),
    "desert": ("parasita", "curandeiro", "mutante"),
    "beach": ("baiacu_mutante", "salva_vidas", "cacador"),
}
REGION_BOSSES = {
    "city": ("bruto_demolidor", "comandante_mortos", "cuspidor_alfa"),
    "desert": ("mutante_ruinas", "necromante", "colosso_mutante"),
    "beach": ("tide_brute", "cacador_abissal", "leviata"),
}
for _region, _bosses in REGION_BOSSES.items():
    REGIONS[_region]["bosses"] = _bosses
for _subbosses in REGION_SUBBOSSES.values():
    for _subboss_key in _subbosses:
        ENEMIES[_subboss_key]["subboss"] = True


# Defesas especiais fazem composição importar. ``immunities`` bloqueia um
# canal até que a carta-counter rompa a proteção; ``resistances`` reduz dano
# sem anulá-lo. Assim RPG, granada e morteiro continuam úteis, mas não vencem
# sozinhos todas as doze ondas.
ENEMY_DEFENSE_TRAITS = {
    "policial": {
        "immunities": ("ballistic",),
        "counter_keys": ("especialista_antipraga", "atirador_precisao_swat"),
        "counter_label": "Antipraga ou tiro de precisão",
        "defense_name": "colete Félix selado",
    },
    "divisor": {
        "resistances": {"explosive": 0.82},
        "weaknesses": {"chemical": 1.45, "thermal": 1.30},
        "counter_label": "Especialista Antipraga",
        "defense_name": "bolsa de dispersão explosiva",
    },
    "bruto": {
        "immunities": ("explosive",),
        "resistances": {"ballistic": 0.48},
        "counter_keys": ("agente_entrada", "escudeiro_tropa_choque"),
        "counter_label": "Tropa de Choque",
        "defense_name": "guarda de demolição",
    },
    "parasita": {
        "immunities": ("ballistic", "explosive"),
        "counter_keys": ("guardiao_laminas",),
        "counter_label": "Guardião de Lâminas",
        "defense_name": "guarda de lâminas amaldiçoadas",
    },
    "curandeiro": {
        "resistances": {"explosive": 0.78, "ballistic": 0.30},
        "weaknesses": {"thermal": 1.55},
        "counter_label": "Incinerador do Deserto",
        "defense_name": "faixas regenerativas",
    },
    "mutante": {
        "resistances": {"explosive": 0.76},
        "weaknesses": {"ballistic": 1.15},
        "counter_label": "Tenente Artilheiro",
        "defense_name": "placas de ruína",
    },
    "mergulhador": {
        "immunities": ("ballistic", "explosive"),
        "counter_keys": ("atirador_precisao_marinha", "submarino_tatico"),
        "counter_label": "Precisão naval ou Submarino Tático",
        "defense_name": "camuflagem submersa",
    },
    "salva_vidas": {
        "resistances": {"explosive": 0.78, "ballistic": 0.42},
        "weaknesses": {"hydraulic": 1.55},
        "counter_label": "Bombeiro Hidráulico",
        "defense_name": "boia contaminada pressurizada",
    },
    "cacador": {
        "resistances": {"explosive": 0.72},
        "weaknesses": {"precision": 1.50, "piercing": 1.35},
        "counter_label": "Precisão naval ou Submarino",
        "defense_name": "placas abissais",
    },
}

for _enemy_key, _traits in ENEMY_DEFENSE_TRAITS.items():
    ENEMIES[_enemy_key].update(_traits)

# O Zumbi de Lâmina é a leitura final do antigo Parasita: agora sua ficha e a
# regra de combate comunicam a mesma ameaça e o mesmo counter obrigatório.
ENEMIES["parasita"]["name"] = "Zumbi de Lâmina"
ENEMIES["parasita"]["ability"] = (
    "As lâminas amaldiçoadas desviam balas e explosões. Somente o Guardião "
    "de Lâminas consegue aparar o golpe e abrir sua defesa por alguns segundos."
)

for _boss_key, _boss_data in BOSSES.items():
    _boss_data.setdefault("resistances", {})["explosive"] = 0.68
    _boss_data.setdefault("defense_name", "massa mutante anti-impacto")

BOSSES["bruto_demolidor"].update({
    "counter_keys": ("agente_entrada", "escudeiro_tropa_choque"),
    "counter_label": "Tropa de Choque",
})
BOSSES["necromante"].update({
    "weaknesses": {"thermal": 1.45},
    "counter_label": "Incinerador do Deserto",
})
BOSSES["leviata"].update({
    "weaknesses": {"piercing": 1.55},
    "counter_label": "Submarino Tático",
})


REGION_ENEMIES = {
    "city": (
        "infectado_urbano", "corredor_cidade", "rastejador_cidade",
        "policial_helix", "cientista_helix", "tecnico_subestacao",
    ),
    "desert": (
        "desperto_khepra", "corredor_deserto", "rastejador_deserto",
        "arqueiro_necropole", "hospedeiro_escaravelhos", "saqueador_canopico",
    ),
    "beach": (
        "afogado_cachoeira", "corredor_cachoeira", "rastejador_cachoeira",
        "surfista", "mergulhador", "pescador_praga",
    ),
}

# Fonte única para o protótipo regional. O ensaio de integração antigo
# criava sempre o infectado urbano, mesmo quando o cenário ativo era Egito ou
# Cachoeira; como não existia animação cruzada para esse par, o ator acabava
# transparente. Todas as entradas (campanha, ensaio e testes) usam este mapa.
BASIC_DEFENDER_BY_REGION = {
    "city": "xerife_rua",
    "desert": "pistoleiro_deserto",
    "beach": "marinheiro",
}
BASIC_ENEMY_BY_REGION = {
    "city": "infectado_urbano",
    "desert": "desperto_khepra",
    "beach": "afogado_cachoeira",
}
DEFENDER_ACTOR_BY_KEY = {
    "xerife_rua": "city_guard",
    "agente_swat": "city_auto",
    "operador_radio_policial": "city_radio",
    "pistoleiro_deserto": "desert_guard",
    "fuzileiro_deserto": "desert_auto",
    "torre_radio_egito": "desert_radio",
    "marinheiro": "beach_guard",
    "fuzileiro_marinha": "beach_auto",
    "estacao_comunicacao_cachoeira": "beach_radio",
    "atirador_precisao_swat": "city_sniper",
    "agente_entrada": "city_entry",
    "especialista_antipraga": "city_antiplague",
    "lancador_foguetes": "city_rocket",
    "escudeiro_tropa_choque": "city_shield",
    "atirador_horizonte": "desert_sniper",
    "tenente_artilheiro": "desert_heavy",
    "incinerador_deserto": "desert_incinerator",
    "nomade_morteiro": "desert_mortar",
    "guardiao_laminas": "desert_blade",
    "atirador_precisao_marinha": "beach_sniper",
    "bombeiro_hidraulico": "beach_waterjet",
    "granadeiro_profundidades": "beach_grenadier",
    "barco_patrulha": "beach_boat",
    "submarino_tatico": "beach_sub",
}
ENEMY_ACTOR_BY_KEY = {
    "infectado_urbano": "city_zombie_v2",
    "corredor_cidade": "city_runner_v2",
    "rastejador_cidade": "city_crawler_v2",
    "policial_helix": "city_police_infected",
    "cientista_helix": "city_scientist",
    "tecnico_subestacao": "city_technician",
    "bruto": "city_demolisher",
    "divisor": "city_quarantine_brute",
    "policial": "city_mutant_commander",
    "bruto_demolidor": "city_boss_director",
    "comandante_mortos": "city_boss_commander",
    "cuspidor_alfa": "city_boss_alpha",
    "desperto_khepra": "desert_zombie_v2",
    "corredor_deserto": "desert_runner_v2",
    "rastejador_deserto": "desert_crawler_v2",
    "arqueiro_necropole": "desert_archer",
    "hospedeiro_escaravelhos": "desert_beetle_host",
    "saqueador_canopico": "desert_looter",
    "parasita": "desert_sarcophagus_guard",
    "curandeiro": "desert_plague_priest",
    "mutante": "desert_mutant_enforcer",
    "mutante_ruinas": "desert_boss_anubis",
    "necromante": "desert_boss_commander",
    "colosso_mutante": "desert_boss_colossus",
    "afogado_cachoeira": "beach_zombie_v2",
    "corredor_cachoeira": "beach_runner_v2",
    "rastejador_cachoeira": "beach_crawler_v2",
    "surfista": "beach_surfer",
    "mergulhador": "beach_diver",
    "pescador_praga": "beach_fisher",
    "baiacu_mutante": "beach_puffer",
    "salva_vidas": "beach_lifeguard",
    "cacador": "beach_deep_hunter",
    "tide_brute": "beach_boss_brute",
    "cacador_abissal": "beach_boss_hunter",
    "leviata": "beach_boss_colossus",
}
CRAWLER_ENEMIES = frozenset(
    {"rastejador_cidade", "rastejador_deserto", "rastejador_cachoeira"}
)
ACTIVE_ENEMY_SKILL_TAGS = frozenset(
    {
        "dash",
        "naval_hunter",
        "gun",
        "acid",
        "shock",
        "net",
        "scream",
        "heal",
        "parasite",
        "stomp",
        "steal",
        "signal_jammer",
    }
)

# A Praia tem um canal real na terceira faixa. Criaturas de maré não podem
# simplesmente reaproveitar qualquer linha terrestre, pois isso quebraria a
# leitura do cenário e faria nadadores parecerem caminhar sobre a areia.
# Cowboy e Saltador são ameaças costeiras terrestres; o restante desta lista
# nasce exclusivamente no canal.
BEACH_WATER_ENEMIES = frozenset(
    {
        "surfista",
        "mergulhador",
        "pescador_praga",
        "baiacu_mutante",
        "cacador",
    }
)


def wave_enemy_pool(region: str, wave: int) -> tuple[str, ...]:
    """Retorna o elenco regional já liberado em uma onda, sem sorteio.

    A função é usada pela diretoria e pelo teste de regressão. Isso garante
    que um inimigo apresentado no dossiê regional não fique preso fora da
    campanha por uma fórmula de aleatoriedade escondida.
    """
    roster = REGION_ENEMIES[region]
    clamped_wave = int(clamp(wave, 1, TOTAL_WAVES))
    # As duas ondas comuns de cada ato nunca repetem um único zumbi. A estreia
    # já mistura dois tipos; a segunda apresenta um terceiro e a variedade
    # chega aos seis antes do ato final.
    unlock_curve = (2, 3, 3, 3, 4, 5, 5, 5, 6, 6, 6, 6)
    unlocked_count = min(len(roster), unlock_curve[clamped_wave - 1])
    return tuple(roster[:unlocked_count])
