"""Conteúdo da reconstrução narrativa de Soldados vs Zumbis.

Este módulo é a fonte única para elenco, histórias, dificuldades e recompensas.
Não existem níveis, promoções ou versões N1/N2/N3: cada carta é um personagem
independente, com nome, silhueta, arma e função próprias.
"""

from __future__ import annotations


CAMPAIGN_STORY = {
    "title": "OPERAÇÃO TRÊS ECOS",
    "prologue": (
        "A Félix Atomics prometia energia limpa para Nova Manhattan. Na noite "
        "do Teste Aurora, o reator abriu uma fenda biológica: mortos se ergueram, "
        "a chuva ficou verde e a cidade entrou em quarentena. Entre os destroços, "
        "uma equipe encontrou o mesmo símbolo gravado em uma peça trazida do Egito."
    ),
    "connection": (
        "A investigação segue o símbolo até a Necrópole de Khepra. Quando o selo "
        "da pirâmide é quebrado, a maldição desperta sacerdotes, xamãs e múmias. "
        "A energia escapa pelo lençol subterrâneo, alcança o oceano e transforma "
        "afogados, mergulhadores e criaturas marinhas na Maré Morta."
    ),
    "ending": (
        "As nove evidências provam que a Félix usou um artefato de Khepra para "
        "alimentar o reator. Destruir o núcleo abissal corta o ciclo entre átomo, "
        "maldição e mar — mas a gravação final menciona um quarto artefato desaparecido."
    ),
}


REGION_PATCHES = {
    "city": {
        "name": "Nova Manhattan: Zona Zero",
        "short": "CIDADE",
        "tag": "Radiação, toxina e quarentena",
        "soldiers": "city_defenders_story_atlas.png",
        "description": (
            "A Félix Atomics explodiu durante o Teste Aurora. Quatro corredores da "
            "avenida de evacuação agora conduzem diretamente ao reator contaminado."
        ),
        "briefing": (
            "Conter os infectados urbanos, recuperar três provas do acidente e "
            "impedir que o Coração do Reator espalhe a praga para fora da ilha."
        ),
        "exclusive": (
            "A Liga Antipraga aplica Envenenado e Bloqueio de Regeneração: é a resposta "
            "da cidade aos curandeiros e à alta resistência dos mutantes nucleares."
        ),
        "bosses": ("diretor_demolidor", "comandante_isotopico", "coracao_reator"),
    },
    "desert": {
        "name": "Egito: Necrópole de Khepra",
        "short": "EGITO",
        "tag": "Maldição, areia e invocação",
        "soldiers": "desert_defenders_story_atlas.png",
        "description": (
            "Uma expedição encontrou nas pirâmides o artefato usado pela Félix. "
            "O selo rompido desperta guardiões, magos, xamãs e legiões mumificadas."
        ),
        "briefing": (
            "Avançar pelas quatro trilhas da escavação, impedir os rituais de "
            "ressurreição e selar a câmara onde a maldição foi libertada."
        ),
        "exclusive": (
            "O Incendiário das Dunas aplica Queimadura prolongada, capaz de interromper "
            "rituais e destruir bandagens encantadas antes que sacerdotes as restaurem."
        ),
        "bosses": ("guardiao_anubis", "sumo_necromante", "colosso_piramide"),
    },
    "beach": {
        "name": "Costa Atlântica: Maré Morta",
        "short": "MAR",
        "tag": "Afogados, anfíbios e abismo",
        "soldiers": "beach_defenders_story_atlas.png",
        "description": (
            "A contaminação desceu ao oceano. Areia, dois canais de água e areia "
            "formam quatro rotas ocupadas por afogados, mergulhadores e fauna mutante."
        ),
        "briefing": (
            "Defender a estação costeira, rastrear a origem da Maré Morta e impedir "
            "que o Leviatã leve o núcleo contaminado para o oceano aberto."
        ),
        "exclusive": (
            "O Bombeiro de Resgate usa água pressurizada: Encharcado reduz a velocidade, "
            "interrompe investidas e expõe criaturas marinhas ao fogo concentrado."
        ),
        "bosses": ("colosso_mare", "cacador_abissal", "leviata"),
    },
}


DIFFICULTIES = {
    "easy": {
        "label": "FÁCIL",
        "initial_supplies": 390,
        "enemy_hp": 1.16,
        "enemy_damage": 1.12,
        "boss_hp": 1.10,
        "boss_damage": 1.08,
        "spawn_count": 1.08,
        "spawn_wait": 0.96,
        "escort_count": 1.12,
        "skill_cooldown": 1.08,
        "accent": (112, 212, 139),
        "summary": "390 SUP, entradas legíveis e espaço para aprender counters e recargas.",
    },
    "medium": {
        "label": "MÉDIO",
        "initial_supplies": 178,
        "enemy_hp": 1.32,
        "enemy_damage": 1.29,
        "boss_hp": 1.25,
        "boss_damage": 1.23,
        "spawn_count": 1.22,
        "spawn_wait": 0.82,
        "escort_count": 1.30,
        "skill_cooldown": 0.90,
        "accent": (240, 187, 72),
        "summary": "178 SUP, pressão crescente e necessidade real de combinar funções.",
    },
    "hard": {
        "label": "DIFÍCIL",
        "initial_supplies": 122,
        "enemy_hp": 1.60,
        "enemy_damage": 1.53,
        "boss_hp": 1.48,
        "boss_damage": 1.43,
        "spawn_count": 1.38,
        "spawn_wait": 0.70,
        "escort_count": 1.48,
        "skill_cooldown": 0.80,
        "accent": (218, 68, 57),
        "summary": "122 SUP, decisões duras desde cedo e final severo, mas sem stun infinito.",
    },
}


def _defender(
    name: str,
    role: str,
    sprite: int,
    cost: int,
    hp: int,
    damage: int,
    reach: float,
    cooldown: float,
    ammo: int,
    reload: float,
    ability: str,
    **extra: object,
) -> dict:
    data = {
        "base": name,
        "role": role,
        "sprite": sprite,
        "cost": cost,
        "hp": hp,
        "damage": damage,
        "range": reach,
        "cooldown": cooldown,
        "ammo": ammo,
        "reload": reload,
        "ability": ability,
    }
    data.update(extra)
    return data


DEFENSES = {
    # Nova Manhattan — resposta urbana à contaminação.
    "guarda_rua": _defender(
        "Guarda de Rua", "revolver", 0, 45, 112, 18, 2, 0.82, 12, 8.2,
        "Dois revólveres alternados. Curto alcance, implantação barata e recarga rápida.",
        burst=2, accuracy=0.88,
    ),
    "operador_bope": _defender(
        "Operador Tático", "rifle", 1, 92, 142, 21, 4, 0.56, 24, 9.0,
        "Rifle militar confiável. Mantém pressão em quatro blocos sem efeito em área.",
    ),
    "breacher_urbano": _defender(
        "Breacher Urbano", "shotgun", 2, 86, 166, 58, 2, 1.05, 6, 10.4,
        "Espingarda tática. Espalha pellets e empurra o primeiro invasor da linha.",
        splash=0.34, knockback=18,
    ),
    "metralhador_quarentena": _defender(
        "Metralhador de Quarentena", "machinegun", 3, 148, 176, 13, 5, 0.19, 48, 12.8,
        "Rajadas de supressão. Excelente contra volume, mas sofre uma recarga longa.",
        burst=4, accuracy=0.83,
    ),
    "fogueteiro_interdicao": _defender(
        "Fogueteiro de Interdição", "rocket", 4, 178, 128, 126, 6, 2.75, 4, 14.5,
        "Foguete antiblindado atravessa a proteção frontal e explode num bloco inteiro.",
        splash=0.82, pierce_armor=0.55,
    ),
    "granadeiro_quarentena": _defender(
        "Granadeiro de Quarentena", "grenade", 5, 126, 138, 76, 4, 1.68, 6, 11.8,
        "Lançador de granadas para grupos médios. Não acerta alvos colados à posição.",
        splash=0.64,
    ),
    "morteirista_urbano": _defender(
        "Morteirista Urbano", "mortar", 6, 164, 116, 112, 7, 2.55, 4, 14.8,
        "Arco alto até a retaguarda. Grande área, cadência baixa e zona morta de um bloco.",
        splash=0.92,
    ),
    "sniper_cobertura": _defender(
        "Sniper de Cobertura", "sniper", 7, 138, 96, 104, 9, 1.82, 7, 12.6,
        "Mira precisa na linha inteira. Prioriza inimigos especiais e perfura parte da armadura.",
        accuracy=0.98, pierce_armor=0.36, target_priority="special",
    ),
    "operadora_drone_tatico": _defender(
        "Operadora de Drone Tático", "drone", 8, 132, 104, 30, 5, 1.20, 10, 10.8,
        "Drone marca um alvo e faz uma rajada curta; o alvo marcado recebe 12% mais dano.",
        mark=3.0,
    ),
    "radio_emergencia": _defender(
        "Operador de Rádio de Emergência", "radio", 9, 78, 108, 0, 0, 7.2, 0, 0,
        "Solicita 18 SUP por entrega. O operador precisa sobreviver para manter a economia.",
        supply_gain=18,
    ),
    "guarda_antimotim": _defender(
        "Guarda Antimotim", "shield", 10, 82, 520, 16, 1, 0.88, 0, 0,
        "Combatente vivo de contenção: absorve dano frontal, usa cassetete e atrai tiros.",
        armor=0.38, taunt=True,
    ),
    "agente_antipraga": _defender(
        "Agente da Liga Antipraga", "poison", 11, 124, 136, 22, 3, 0.52, 18, 10.0,
        "Nuvem química causa Envenenado, reduz o avanço e bloqueia cura por quatro segundos.",
        splash=0.60, anti_heal=4.0,
    ),
    "mina_urbana": _defender(
        "Claymore Urbana", "mine", 11, 54, 1, 190, 0, 0, 0, 0,
        "Explosivo direcional confiável. Detona quando o primeiro zumbi entra na célula.",
        splash=0.52, land_only=True, art="city_mine_n2",
    ),

    # Egito — equipe de expedição e contenção arqueológica.
    "batedor_caravana": _defender(
        "Batedor da Caravana", "revolver", 0, 46, 108, 22, 2, 0.92, 10, 8.0,
        "Revólver pesado que causa dano extra em inimigos recém-emergidos da areia.",
        accuracy=0.91, anti_burrow=1.30,
    ),
    "fuzileiro_dunas": _defender(
        "Fuzileiro das Dunas", "rifle", 1, 94, 140, 22, 4, 0.60, 22, 9.2,
        "Rifle selado contra areia. Tiros constantes interrompem preparação de rituais.",
        interrupt=0.12,
    ),
    "guarda_medjai": _defender(
        "Guarda Medjai", "shotgun", 2, 90, 170, 62, 2, 1.08, 6, 10.6,
        "Espingarda de guarda da tumba. Dano alto em escavadores e parasitas próximos.",
        splash=0.32, anti_burrow=1.22,
    ),
    "metralhador_legionario": _defender(
        "Metralhador Legionário", "machinegun", 3, 150, 174, 14, 5, 0.20, 46, 12.6,
        "Suprime múmias invocadas; cada quarta bala perfura um segundo alvo.",
        burst=4, pierce_every=4,
    ),
    "fogueteiro_solar": _defender(
        "Fogueteiro Solar", "rocket", 4, 180, 126, 132, 6, 2.80, 4, 14.6,
        "Carga térmica quebra golems e escudos encantados em uma explosão concentrada.",
        splash=0.78, pierce_armor=0.62,
    ),
    "granadeiro_escavacao": _defender(
        "Granadeiro da Escavação", "grenade", 5, 128, 136, 80, 4, 1.72, 6, 11.6,
        "Granadas de pó mineral revelam unidades enterradas e atingem um pequeno grupo.",
        splash=0.66, reveal=True,
    ),
    "morteirista_ruinas": _defender(
        "Morteirista das Ruínas", "mortar", 6, 166, 114, 118, 7, 2.62, 4, 14.9,
        "Bombardeio de retaguarda interrompe sacerdotes e invocadores protegidos.",
        splash=0.94, target_priority="support",
    ),
    "atirador_oasis": _defender(
        "Atirador do Oásis", "sniper", 7, 140, 94, 108, 9, 1.86, 7, 12.8,
        "Disparo preciso atravessa bandagens e remove bênçãos mágicas do alvo.",
        accuracy=0.98, pierce_armor=0.32, dispel=True,
    ),
    "falcoeira_drone": _defender(
        "Falcoeira de Reconhecimento", "drone", 8, 134, 106, 28, 6, 1.18, 10, 10.6,
        "Drone-falcão revela túneis e ataca o inimigo oculto mais avançado.",
        reveal=True, target_priority="burrow",
    ),
    "radio_expedicao": _defender(
        "Rádio da Expedição", "radio", 9, 80, 110, 0, 0, 7.4, 0, 0,
        "Transmite descobertas ao acampamento e recebe 18 SUP por entrega.",
        supply_gain=18,
    ),
    "protetor_tumba": _defender(
        "Protetor da Tumba", "shield", 10, 86, 535, 18, 1, 0.92, 0, 0,
        "Escudo balístico com bronze aterra magia e segura o primeiro atacante da faixa.",
        armor=0.40, magic_resist=0.42, taunt=True,
    ),
    "incendiario_dunas": _defender(
        "Incendiário das Dunas", "flame", 11, 132, 148, 28, 3, 0.38, 20, 10.4,
        "Exclusivo do Egito. Cone de fogo aplica Queimadura e interrompe cura e invocação.",
        splash=0.58, anti_heal=3.5,
    ),
    "mina_escaravelho": _defender(
        "Mina Escaravelho", "mine", 11, 56, 1, 200, 0, 0, 0, 0,
        "Armadilha sísmica confiável: emerge da areia e detona num grupo compacto.",
        splash=0.56, land_only=True, art="desert_mine_n1",
    ),

    # Maré Morta — guarda costeira e defesa anfíbia.
    "guarda_porto": _defender(
        "Guarda do Porto", "revolver", 0, 45, 112, 19, 2, 0.84, 12, 8.1,
        "Revólver marítimo simples, barato e confiável nas faixas de areia.",
        accuracy=0.90, land_only=True,
    ),
    "fuzileiro_anfibio": _defender(
        "Fuzileiro Anfíbio", "rifle", 1, 96, 146, 22, 4, 0.58, 24, 9.1,
        "Rifle anticorrosão. Pode operar na areia ou em plataforma rasa do canal.",
        amphibious=True,
    ),
    "breacher_resgate": _defender(
        "Breacher de Resgate", "shotgun", 2, 90, 174, 60, 2, 1.04, 6, 10.2,
        "Espingarda de resgate repele surfistas e anfíbios que alcançam a margem.",
        splash=0.34, knockback=22, land_only=True,
    ),
    "metralhador_costeiro": _defender(
        "Metralhador Costeiro", "machinegun", 3, 152, 180, 13, 5, 0.19, 48, 12.7,
        "Fogo de cobertura contra grandes cardumes; perde precisão sob ataque de onda.",
        burst=4, accuracy=0.84, land_only=True,
    ),
    "arpoador_explosivo": _defender(
        "Arpoador Explosivo", "rocket", 4, 176, 132, 124, 6, 2.70, 4, 14.4,
        "Arpão com carga explosiva perfura mergulhadores e detona atrás do escudo.",
        splash=0.76, pierce_armor=0.58, amphibious=True,
    ),
    "granadeiro_salva": _defender(
        "Granadeiro de Salva", "grenade", 5, 126, 140, 74, 4, 1.64, 6, 11.5,
        "Carga flutuante explode no ponto de impacto e alcança inimigos agrupados no canal.",
        splash=0.66, amphibious=True,
    ),
    "morteirista_costeiro": _defender(
        "Morteirista Costeiro", "mortar", 6, 162, 118, 108, 7, 2.48, 4, 14.6,
        "Salva de costa cobre água e areia, mas mantém uma zona morta próxima.",
        splash=0.90, land_only=True,
    ),
    "vigia_farol": _defender(
        "Vigia do Farol", "sniper", 7, 136, 98, 102, 9, 1.78, 7, 12.4,
        "Mira térmica prioriza mergulhadores e criaturas submersas.",
        accuracy=0.99, target_priority="water", land_only=True,
    ),
    "pilota_drone_marinho": _defender(
        "Pilota de Drone Marinho", "drone", 8, 130, 108, 29, 6, 1.16, 10, 10.4,
        "Drone impermeável lança um marcador sonar; alvos revelados ficam mais vulneráveis.",
        mark=3.2, land_only=True,
    ),
    "operador_sonar": _defender(
        "Operador de Sonar", "radio", 9, 82, 112, 0, 0, 7.0, 0, 0,
        "Recebe 17 SUP e revela o próximo inimigo aquático especial da onda.",
        supply_gain=17, sonar=True, land_only=True,
    ),
    "bombeiro_resgate": _defender(
        "Bombeiro de Resgate", "waterjet", 10, 128, 154, 18, 3, 0.40, 22, 9.8,
        "Exclusivo do Mar. Água pressurizada aplica Encharcado e interrompe dash e salto.",
        splash=0.52, interrupt_dash=True, land_only=True,
    ),
    "atirador_bote": _defender(
        "Atirador de Bote", "boat", 11, 118, 260, 34, 5, 0.68, 18, 9.4,
        "Bote armado exclusivo do canal. Resiste a ondas e cobre cinco blocos de água.",
        water_only=True, wave_resist=0.45,
    ),
    "mina_areia_costeira": _defender(
        "Mina de Areia Costeira", "mine", 11, 54, 1, 188, 0, 0, 0, 0,
        "Carga terrestre camuflada. Só pode ser armada nas duas faixas de areia.",
        splash=0.50, land_only=True, art="beach_mine_land_n2",
    ),
    "mina_naval": _defender(
        "Mina Naval", "mine", 11, 62, 1, 215, 0, 0, 0, 0,
        "Carga submersa exclusiva dos dois canais. Detona num pequeno raio aquático.",
        splash=0.60, water_only=True, art="beach_mine_water",
    ),
}


REGION_ROSTERS = {
    "city": tuple((key, DEFENSES[key]["base"]) for key in (
        "guarda_rua", "operador_bope", "breacher_urbano", "metralhador_quarentena",
        "fogueteiro_interdicao", "granadeiro_quarentena", "morteirista_urbano",
        "sniper_cobertura", "operadora_drone_tatico", "radio_emergencia",
        "guarda_antimotim", "agente_antipraga", "mina_urbana",
    )),
    "desert": tuple((key, DEFENSES[key]["base"]) for key in (
        "batedor_caravana", "fuzileiro_dunas", "guarda_medjai", "metralhador_legionario",
        "fogueteiro_solar", "granadeiro_escavacao", "morteirista_ruinas",
        "atirador_oasis", "falcoeira_drone", "radio_expedicao", "protetor_tumba",
        "incendiario_dunas", "mina_escaravelho",
    )),
    "beach": tuple((key, DEFENSES[key]["base"]) for key in (
        "guarda_porto", "fuzileiro_anfibio", "breacher_resgate", "metralhador_costeiro",
        "arpoador_explosivo", "granadeiro_salva", "morteirista_costeiro", "vigia_farol",
        "pilota_drone_marinho", "operador_sonar", "bombeiro_resgate", "atirador_bote",
        "mina_areia_costeira", "mina_naval",
    )),
}


CARD_ATLAS_INDEX = {
    region: {key: int(DEFENSES[key]["sprite"]) for key, _display in roster}
    for region, roster in REGION_ROSTERS.items()
}

CARD_ART_ASSETS = {
    (region, key): str(DEFENSES[key]["art"])
    for region, roster in REGION_ROSTERS.items()
    for key, _display in roster
    if "art" in DEFENSES[key]
}
CARD_ART_ASSETS.update(
    {
        ("city", "guarda_rua"): "city_guard_dual_pistols",
        ("city", "operadora_drone_tatico"): "city_drone_operator_story",
        ("city", "agente_antipraga"): "city_antiplague_aim",
        ("desert", "guarda_medjai"): "desert_shotgun_modern",
        ("desert", "protetor_tumba"): "desert_shield_modern",
    }
)


def _enemy(
    name: str,
    sprite: int,
    hp: int,
    speed: float,
    damage: int,
    attack: float,
    ability: str,
    *,
    tags: tuple[str, ...] = (),
    armor: float = 0.0,
    **extra: object,
) -> dict:
    data = {
        "name": name,
        "sprite": sprite,
        "hp": hp,
        "speed": speed,
        "damage": damage,
        "attack": attack,
        "ability": ability,
        "tags": tags,
    }
    if armor:
        data["armor"] = armor
    data.update(extra)
    return data


ENEMIES = {
    # Cidade: todos nasceram da evacuação e da contaminação da Félix.
    "irradiado_civil": _enemy("Irradiado Civil", 0, 108, 12, 12, 1.20, "Infectado urbano básico; avança devagar em massa."),
    "corredor_evacuacao": _enemy("Corredor da Evacuação", 1, 96, 24, 26, 0.76, "Arranque curto ao nascer; pune linhas sem resposta imediata.", tags=("dash",)),
    "rastejante_esgoto": _enemy("Rastejante do Esgoto", 2, 154, 9, 30, 1.02, "Baixo e lento, mas morde com força quando alcança a tropa.", tags=("crawler",)),
    "operario_chumbo": _enemy("Operário de Chumbo", 3, 210, 10, 16, 1.02, "Avental e máscara de chumbo reduzem tiros frontais.", armor=0.24),
    "policial_contaminado": _enemy("Policial Contaminado", 4, 235, 10, 18, 0.98, "Colete e arma curta atacam a defesa antes do contato.", tags=("gun",), armor=0.28),
    "escudo_quarentena": _enemy("Escudo da Quarentena", 5, 275, 8, 30, 1.05, "Escudo policial bloqueia fogo frontal e protege quem vem atrás.", tags=("shield",), armor=0.46),
    "cuspidor_radiativo": _enemy("Cuspidor Radiativo", 6, 182, 12, 15, 1.08, "Ácido a três blocos corrói armas e causa dano contínuo.", tags=("acid",)),
    "sirene_mutante": _enemy("Sirene Mutante", 7, 168, 11, 14, 1.08, "Grito acelera aliados próximos e pode chamar reforços.", tags=("scream",)),
    "divisor_isotopico": _enemy("Divisor Isotópico", 8, 315, 7, 34, 1.06, "Corpo instável explode em ácido quando derrotado.", tags=("acid", "explode_death")),
    "saltador_mutageno": _enemy("Saltador Mutagênico", 9, 156, 16, 24, 0.92, "Salta somente a primeira tropa que bloquear sua faixa.", tags=("jump",)),
    "bruto_reator": _enemy("Bruto do Reator", 10, 430, 7, 46, 0.94, "Soco pesado atordoa uma área curta da própria faixa.", tags=("stomp",)),
    "parasita_nuclear": _enemy("Parasita Nuclear", 11, 260, 9, 28, 1.00, "Agarra um defensor e interrompe seus ataques até ser repelido.", tags=("parasite",)),

    # Egito: mortos e criaturas da necrópole, sem cópias urbanas.
    "mumia_operaria": _enemy("Múmia Operária", 0, 116, 11, 13, 1.18, "Múmia comum de bandagens secas; fraca sozinha, perigosa em grupo."),
    "guardiao_chacal": _enemy("Guardião Chacal", 1, 124, 20, 24, 0.82, "Investida ritual curta ao entrar na trilha.", tags=("dash",)),
    "rastejante_sarcofago": _enemy("Rastejante do Sarcófago", 2, 164, 8, 32, 1.00, "Torso mumificado rasteja sob a linha de tiro e ataca com força.", tags=("crawler",)),
    "escavador_tumba": _enemy("Escavador da Tumba", 3, 188, 13, 40, 0.90, "Cava com animação visível e ultrapassa apenas a primeira tropa.", tags=("dig",)),
    "ladrao_reliquias": _enemy("Ladrão de Relíquias", 4, 142, 14, 11, 1.15, "Rouba suprimentos se não for eliminado a tempo.", tags=("steal",)),
    "sacerdote_canopico": _enemy("Sacerdote Canópico", 5, 194, 10, 12, 1.10, "Cura aliados e tenta reviver uma múmia uma única vez.", tags=("heal",)),
    "sentinela_farao": _enemy("Sentinela do Faraó", 6, 286, 8, 32, 1.04, "Escudo funerário reduz projéteis e protege o ritual.", tags=("shield",), armor=0.48),
    "xama_areia": _enemy("Xamã da Areia", 7, 184, 10, 16, 1.06, "Tempestade acelera mortos e atrasa a mira dos humanos.", tags=("scream", "sandstorm")),
    "acolito_necromante": _enemy("Acólito Necromante", 8, 205, 9, 17, 1.08, "Invoca uma múmia fraca e sustenta aliados próximos.", tags=("summon", "heal")),
    "parasita_escaravelho": _enemy("Parasita Escaravelho", 9, 268, 10, 29, 0.98, "Enxame agarra uma tropa e silencia a arma por alguns segundos.", tags=("parasite",)),
    "golem_canopico": _enemy("Golem Canópico", 10, 420, 6, 45, 0.96, "Vaso funerário vivo: muita vida, armadura e impacto sísmico.", tags=("stomp",), armor=0.25),
    "cuspidor_maldicao": _enemy("Cuspidor da Maldição", 11, 180, 11, 15, 1.08, "Esfera amaldiçoada corrói a arma como ácido ritual.", tags=("acid",)),

    # Mar: afogados, profissionais aquáticos e fauna mutante — nenhum cowboy.
    "afogado_costeiro": _enemy("Afogado Costeiro", 0, 112, 12, 14, 1.16, "Infectado trazido pela arrebentação; ameaça básica da costa."),
    "turista_boia": _enemy("Turista de Boia", 1, 142, 9, 15, 1.10, "Boia absorve parte do dano, mas reduz a velocidade.", armor=0.14),
    "surfista_infectado": _enemy("Surfista Infectado", 2, 126, 25, 25, 0.80, "Prancha cria uma arrancada rápida no canal.", tags=("dash",)),
    "nadador_mutante": _enemy("Nadador Mutante", 3, 176, 18, 24, 0.94, "Braçadas rápidas ignoram minas terrestres."),
    "mergulhador_corrompido": _enemy("Mergulhador Corrompido", 4, 284, 10, 32, 0.94, "Roupa de mergulho e cilindro formam armadura espessa.", armor=0.32),
    "salva_vidas_afogado": _enemy("Salva-Vidas Afogado", 5, 238, 10, 25, 1.00, "Boia rígida funciona como escudo para a maré atrás dele.", tags=("shield",), armor=0.40),
    "cuspidor_salmoura": _enemy("Cuspidor de Salmoura", 6, 186, 12, 16, 1.02, "Jato salino corrói metal e atrasa a próxima recarga.", tags=("acid",)),
    "sereia_gritadora": _enemy("Sereia Gritadora", 7, 178, 11, 15, 1.02, "Canto acelera criaturas aquáticas e chama uma pequena escolta.", tags=("scream",)),
    "pescador_abissal": _enemy("Pescador Abissal", 8, 202, 13, 20, 0.96, "Arpão de médio alcance puxa a primeira tropa para o perigo.", tags=("gun", "harpoon")),
    "anfibio_saltador": _enemy("Anfíbio Saltador", 9, 160, 17, 25, 0.90, "Salta da água sobre apenas a primeira defesa.", tags=("jump",)),
    "caranguejo_mutante": _enemy("Caranguejo Mutante", 10, 390, 7, 43, 0.98, "Carapaça blindada e pinça que atordoa a defesa próxima.", tags=("stomp",), armor=0.28),
    "enguia_parasita": _enemy("Enguia Parasita", 11, 244, 15, 27, 0.96, "Enrola-se numa embarcação e desabilita seu ataque temporariamente.", tags=("parasite",)),
}


def _boss(name: str, hp: int, speed: float, damage: int, attack: float, sprite: int, ability: str, boss_type: str) -> dict:
    return {
        "name": name,
        "hp": hp,
        "speed": speed,
        "damage": damage,
        "attack": attack,
        "sprite": sprite,
        "ability": ability,
        "type": boss_type,
    }


BOSSES = {
    "diretor_demolidor": _boss(
        "DIRETOR DEMOLIDOR", 880, 6, 29, 1.05, 10,
        "Entrada: martelo eletromagnético atrasa todas as armas por 3 s. Recorrente: atordoa somente sua faixa por 1,2 s, com 18 s de intervalo.",
        "bruto_demolidor",
    ),
    "comandante_isotopico": _boss(
        "COMANDANTE ISOTÓPICO", 1080, 9, 25, 0.90, 11,
        "Entrada: acelera a escolta. Recorrente: rajada dupla e novo comando apenas nos aliados próximos.",
        "comandante",
    ),
    "coracao_reator": _boss(
        "CORAÇÃO DO REATOR", 1380, 10, 27, 0.96, 11,
        "Entrada: névoa radiativa breve. Recorrente: três cuspes telegrafados na própria faixa, sem travar todo o campo.",
        "alfa",
    ),
    "guardiao_anubis": _boss(
        "GUARDIÃO DE ANÚBIS", 940, 6, 31, 0.99, 10,
        "Entrada: abalo nas faixas vizinhas. Recorrente: golpe curto que abre espaço para os escavadores.",
        "mutante",
    ),
    "sumo_necromante": _boss(
        "SUMO NECROMANTE", 1180, 7, 22, 0.98, 10,
        "Entrada: invoca uma múmia. Recorrente: alterna invocação e cura moderada com gesto visível.",
        "necromante",
    ),
    "colosso_piramide": _boss(
        "COLOSSO DA PIRÂMIDE", 1580, 4, 37, 1.06, 11,
        "Entrada: tremor de 1,2 s. Recorrente: rocha telegrafada contra uma única faixa.",
        "colosso",
    ),
    "colosso_mare": _boss(
        "COLOSSO DAS MARÉS", 920, 6, 32, 1.02, 9,
        "Entrada: onda curta no canal. Recorrente: impacto somente contra a faixa em que nada.",
        "tide",
    ),
    "cacador_abissal": _boss(
        "CAÇADOR ABISSAL", 1210, 10, 25, 0.96, 10,
        "Entrada: mergulho curto. Recorrente: arpão telegrafado contra uma embarcação próxima.",
        "hunter",
    ),
    "leviata": _boss(
        "LEVIATÃ", 1680, 5, 40, 1.02, 11,
        "Entrada: maré moderada. Recorrente: jato concentrado na própria faixa e mordida devastadora no contato.",
        "leviathan",
    ),
}


REGION_ENEMIES = {
    "city": (
        "irradiado_civil", "corredor_evacuacao", "rastejante_esgoto", "operario_chumbo",
        "policial_contaminado", "escudo_quarentena", "cuspidor_radiativo", "sirene_mutante",
        "divisor_isotopico", "saltador_mutageno", "bruto_reator", "parasita_nuclear",
    ),
    "desert": (
        "mumia_operaria", "guardiao_chacal", "rastejante_sarcofago", "escavador_tumba",
        "ladrao_reliquias", "sacerdote_canopico", "sentinela_farao", "xama_areia",
        "acolito_necromante", "parasita_escaravelho", "golem_canopico", "cuspidor_maldicao",
    ),
    "beach": (
        "afogado_costeiro", "turista_boia", "surfista_infectado", "nadador_mutante",
        "mergulhador_corrompido", "salva_vidas_afogado", "cuspidor_salmoura", "sereia_gritadora",
        "pescador_abissal", "anfibio_saltador", "caranguejo_mutante", "enguia_parasita",
    ),
}


BEACH_WATER_ENEMIES = frozenset({
    "surfista_infectado", "mergulhador_corrompido",
})


BOSS_EVIDENCE = {
    "city": (
        ("AMOSTRA AURORA", "O tecido dos infectados contém o mesmo isótopo do Teste Aurora."),
        ("GRAVAÇÃO DA FÉLIX", "A diretoria sabia que a peça egípcia reagia ao reator."),
        ("CHAVE DO NÚCLEO", "O símbolo de Khepra foi gravado dentro da câmara de energia."),
    ),
    "desert": (
        ("SELO PARTIDO", "O artefato da Félix foi retirado desta porta funerária."),
        ("TÁBUA DO SACERDOTE", "A maldição precisa de água para atravessar continentes."),
        ("PEDRA SOLAR", "A energia da pirâmide e a radiação são partes do mesmo ciclo."),
    ),
    "beach": (
        ("CORAL NEGRO", "A mutação oceânica cresce ao redor de fragmentos do artefato."),
        ("REGISTRO DO MERGULHADOR", "Uma criatura levou o núcleo para a fossa marítima."),
        ("NÚCLEO ABISSAL", "A queda do Leviatã fecha o elo final da Operação Três Ecos."),
    ),
}


def difficulty_profile(key: str) -> dict:
    return DIFFICULTIES.get(key, DIFFICULTIES["medium"])


def wave_enemy_pool(region: str, wave: int) -> tuple[str, ...]:
    roster = REGION_ENEMIES[region]
    clamped = max(1, min(15, int(wave)))
    unlocked = 1 + ((clamped - 1) * (len(roster) - 1)) // 14
    return tuple(roster[:unlocked])


__all__ = [
    "BEACH_WATER_ENEMIES", "BOSSES", "BOSS_EVIDENCE", "CAMPAIGN_STORY",
    "CARD_ART_ASSETS", "CARD_ATLAS_INDEX", "DEFENSES", "DIFFICULTIES",
    "ENEMIES", "REGION_ENEMIES", "REGION_PATCHES", "REGION_ROSTERS",
    "difficulty_profile", "wave_enemy_pool",
]
