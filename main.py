"""Soldados vs Zumbis — an original Pygame tower-defense campaign.

No third-party game graphics or audio are used.  The PNG sprites and the menu
illustration in assets/ belong to this project and are loaded at runtime.
"""
from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Any

import pygame


WIDTH, HEIGHT = 1280, 720
FPS = 60
BOARD_X, BOARD_Y = 228, 176
COLS, ROWS, CELL_W, CELL_H = 9, 5, 108, 90
BOARD_W, BOARD_H = COLS * CELL_W, ROWS * CELL_H
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets")
SAVE_FILE = os.path.join(ROOT, "campaign_progress.json")

# The first wave must teach the player instead of punishing them.  Economy and
# card limits then prevent a late-game row of identical power units from
# trivialising the horde.
STARTING_SUPPLIES = (165, 175, 185)
PICKUP_VALUES = (8, 12, 16)
PICKUP_INTERVAL = (12.0, 16.0)
# Each support specialist carries its own income profile.  The inexpensive
# option is deliberately useful instead of making the basic radio feel like a
# luxury card, while the high-output command centre has a real strategic cost.
RADIO_SUPPLIES = 7
RADIO_INTERVAL = 6.0

# Every environment exposes a curated tactical roster.  All units remain in
# the project, but a city commander is not offered a submarine and a beach
# operation has its own coastal equipment.  The three new cards below are
# mechanics, not generic bonuses: Recruta earns ranks from boss medals,
# Instrutor converts medals into those ranks, and Vanguardista holds a lane.
UNIT_DATA: dict[str, dict[str, Any]] = {
    "fuzileiro": dict(label="Fuzileiro", cost=50, hp=135, damage=20, rate=.82, color=(112, 181, 87), kind="rifle", ability="Rifle de linha"),
    "tenente": dict(label="Tenente", cost=100, hp=180, damage=34, rate=.76, color=(90, 170, 199), kind="rifle", ability="Tiro de comando"),
    "general": dict(label="General", cost=260, hp=265, damage=66, rate=.72, color=(212, 145, 55), kind="rifle", max_total=1, cooldown=5.2, ability="Aura de comando"),
    "bombardeiro": dict(label="Bombardeiro", cost=215, hp=150, damage=115, rate=3.4, color=(203, 82, 57), kind="splash", splash=82, max_per_row=1, max_total=3, cooldown=5.4, ability="Explosão em área"),
    "sniper": dict(label="Sniper", cost=205, hp=115, damage=165, rate=2.5, color=(120, 141, 185), kind="rifle", pierce=1, max_total=3, cooldown=3.9, ability="Tiro perfurante"),
    "morteiro": dict(label="Morteiro", cost=230, hp=190, damage=120, rate=2.5, color=(135, 119, 75), kind="mortar", splash=110, max_total=3, cooldown=5.0, ability="Arco explosivo"),
    "rambo": dict(label="Rambo", cost=270, hp=325, damage=44, rate=.38, color=(178, 76, 65), kind="rifle", pierce=2, max_total=1, cooldown=4.8, ability="Rajada perfurante"),
    "forcas_especiais": dict(label="Forças Especiais", cost=145, hp=225, damage=46, rate=.65, color=(84, 113, 104), kind="rifle", ability="Fogo de elite"),
    "engenheiro": dict(label="Engenheiro", cost=120, hp=440, damage=0, rate=3.6, color=(209, 164, 57), kind="engineer", repair=42, cooldown=3.8, ability="Reparo de campo"),
    "lanca_chamas": dict(label="Lança-Chamas", cost=165, hp=220, damage=20, rate=.25, color=(238, 110, 49), kind="flame", range=185, ability="Chamas em cone"),
    "escopeteiro": dict(label="Escopeteiro", cost=135, hp=170, damage=58, rate=1.05, color=(177, 143, 71), kind="shotgun", range=305, ability="Disparo múltiplo"),
    "batedor_suprimentos": dict(label="Batedor de Suprimentos", cost=45, hp=96, damage=0, rate=4.0, income=3, color=(173, 191, 93), kind="radio", max_total=3, cooldown=3.2, tier=1, ability="+3 SUP / 4 s"),
    "operador_radio": dict(label="Operador de Rádio", cost=85, hp=138, damage=0, rate=RADIO_INTERVAL, income=RADIO_SUPPLIES, color=(205, 164, 55), kind="radio", max_total=2, cooldown=4.2, tier=2, ability="+7 SUP / 6 s"),
    "torre_radio": dict(label="Torre de Rádio", cost=150, hp=230, damage=0, rate=5.0, income=15, color=(204, 139, 59), kind="radio", max_total=1, cooldown=6.0, tier=3, ability="+15 SUP / 5 s"),
    "central_comando": dict(label="Central de Comando", cost=295, hp=330, damage=0, rate=3.8, income=26, color=(227, 104, 51), kind="radio", max_total=1, cooldown=7.4, tier=4, ability="+26 SUP / 3,8 s"),
    "operador_drone": dict(label="Operador de Drone", cost=180, hp=130, damage=34, rate=.65, color=(104, 182, 191), kind="drone", ability="Alvo global"),
    "buggy": dict(label="Buggy", cost=230, hp=410, damage=62, rate=.58, color=(130, 161, 88), kind="rifle", max_total=2, cooldown=4.2, ability="Canhão móvel"),
    "lancha_patrulha": dict(label="Lancha Patrulha", cost=185, hp=350, damage=41, rate=.58, color=(85, 155, 178), kind="rifle", aquatic=True, max_total=3, cooldown=4.0, ability="Patrulha costeira"),
    "submarino": dict(label="Submarino", cost=245, hp=430, damage=116, rate=1.8, color=(85, 162, 177), kind="splash", splash=78, aquatic=True, max_total=2, cooldown=5.2, ability="Torpedo em área"),
    "bomba_agua": dict(label="Bomba de Água", cost=150, hp=1, damage=390, rate=0, color=(78, 167, 192), kind="mine", aquatic=True, max_per_row=1, ability="Mina de maré"),
    "mina": dict(label="Mina Tática", cost=90, hp=1, damage=310, rate=0, color=(98, 124, 81), kind="mine", max_per_row=1, ability="Emboscada terrestre"),
    "ferramenta_medica": dict(label="Ferramenta Médica", cost=65, hp=0, damage=0, rate=3.8, color=(232, 72, 68), kind="medical", tool=True, ability="Cura 180 HP"),
    "recruta": dict(label="Recruta de Campo", cost=35, hp=92, damage=15, rate=1.82, range=222, color=(165, 186, 118), kind="rifle", evolvable=True, max_rank=3, ability="Tiro curto • evolui com Medalhas"),
    "instrutor_tatico": dict(label="Instrutor Tático", cost=125, hp=210, damage=0, rate=4.8, color=(177, 153, 83), kind="trainer", max_total=1, cooldown=5.0, ability="Promove aliado com Medalha"),
    "vanguardista": dict(label="Vanguardista", cost=175, hp=1050, damage=8, rate=1.55, range=150, color=(111, 122, 126), kind="vanguard", max_total=2, cooldown=5.2, ability="Blindagem de linha • dano mínimo"),
    "torreta_engenheiro": dict(label="Torreta de Engenheiro", cost=0, hp=190, damage=23, rate=.58, range=410, color=(118, 139, 88), kind="turret", hidden=True, cooldown=0, ability="Torreta automática destacável"),
}

# The logistics variants deliberately reuse the original Radio Operator
# silhouette.  At runtime they receive distinct colour, rank and environment
# treatments, so a missing duplicate PNG can never create a placeholder card.
UNIT_ASSET_KEYS = {
    "batedor_suprimentos": "operador_radio",
    "torre_radio": "operador_radio",
    "central_comando": "operador_radio",
    "instrutor_tatico": "instrutor_tatico_v2",
    "vanguardista": "vanguardista_v2",
    "torreta_engenheiro": "torreta_engenheiro_v2",
    # Recruta is replaced by a full, original regional uniform at runtime.
    "recruta": "recruta_city_v2",
}

ENVIRONMENT_STYLE = {
    "city": dict(
        uniform="DESTACAMENTO URBANO • CONCRETO, COURO E AÇO",
        callout="Cobertura entre carros e barricadas",
    ),
    "desert": dict(
        uniform="DESTACAMENTO DO DESERTO • LONA, AREIA E ÓCULOS",
        callout="Disciplina de comboio e poeira",
    ),
    "beach": dict(
        uniform="DESTACAMENTO COSTEIRO • COLETE NAVAL E SAL",
        callout="Patrulha entre areia, píer e maré",
    ),
}

ZOMBIE_DATA: dict[str, dict[str, Any]] = {
    "caminhante": dict(label="Caminhante Urbano", hp=105, speed=15, damage=20, color=(112, 154, 139), motion="shamble"),
    "corredor": dict(label="Corredor de Rua", hp=82, speed=29, damage=17, color=(128, 151, 112), motion="sprint"),
    "bruto": dict(label="Bruto", hp=720, speed=9, damage=40, color=(111, 135, 99), boss=True, motion="stomp"),
    "rastejante": dict(label="Rastejante", hp=55, speed=23, damage=14, color=(103, 152, 136), motion="crawl"),
    "toxico": dict(label="Tóxico do Oásis", hp=140, speed=16, damage=23, color=(149, 199, 71), motion="shamble"),
    "blindado": dict(label="Blindado Costeiro", hp=390, speed=11, damage=29, color=(103, 126, 128), armor=.35, motion="stomp"),
    "divisor": dict(label="Divisor das Dunas", hp=185, speed=14, damage=22, color=(160, 98, 75), split=True, motion="shamble"),
    "feral": dict(label="Feral do Deserto", hp=175, speed=25, damage=33, color=(117, 140, 100), motion="sprint"),
    "gritador": dict(label="Gritador de Rua", hp=130, speed=14, damage=20, color=(124, 103, 109), howl=True, motion="shamble"),
    "cuspidor": dict(label="Cuspidor", hp=135, speed=13, damage=19, color=(155, 196, 78), ranged=True, range=340, motion="shamble"),
    "pulador": dict(label="Pulador de Ruínas", hp=115, speed=21, damage=24, color=(154, 107, 68), jump=True, motion="leap"),
    "necromante": dict(label="Necromante das Areias", hp=255, speed=10, damage=25, color=(89, 72, 110), healer=True, motion="shamble"),
    "sandstalker": dict(label="Sandstalker", hp=145, speed=27, damage=26, color=(189, 146, 83), dig=True, motion="sprint"),
    "nadador": dict(label="Nadador da Maré", hp=115, speed=21, damage=20, color=(64, 154, 187), aquatic=True, motion="swim"),
    "tide_brute": dict(label="Tide Brute", hp=830, speed=10, damage=45, color=(80, 141, 133), aquatic=True, boss=True, motion="swim"),
    "conehead": dict(label="Conehead de Obras", hp=270, speed=13, damage=24, color=(227, 128, 48), armor=.18, motion="shamble"),
    "bandeireiro": dict(label="Bandeireiro", hp=150, speed=21, damage=19, color=(160, 64, 64), flag=True, motion="shamble"),
    "porta_escudo": dict(label="Porta-Escudo", hp=450, speed=10, damage=25, color=(94, 111, 117), armor=.25, motion="stomp"),
    "escavadeira": dict(label="Escavadeira das Ruínas", hp=210, speed=17, damage=30, color=(151, 119, 83), dig=True, motion="stomp"),
    "doutor_zumbi": dict(label="Doutor da Praia", hp=260, speed=12, damage=20, color=(204, 204, 185), healer=True, motion="shamble"),
    "general_morto": dict(label="General Morto", hp=1160, speed=9, damage=53, color=(58, 103, 92), boss=True, motion="stomp"),
    "mutante_titan": dict(label="Mutante Titã", hp=1500, speed=7, damage=65, color=(143, 191, 76), boss=True, motion="stomp"),
}

# These are direct regional illustrations, not colour overlays.  Every other
# card keeps its own original silhouette while the recruit and walker visibly
# change uniform/clothing with their battlefield.
REGIONAL_UNIT_ASSETS = {
    "recruta": {
        "city": "recruta_city_v2",
        "desert": "recruta_desert_v2",
        "beach": "recruta_beach_v2",
    },
}
REGIONAL_ZOMBIE_ASSETS = {
    "caminhante": {
        "city": "caminhante_city_v2",
        "desert": "caminhante_desert_v2",
        "beach": "caminhante_beach_v2",
    },
}

# Wave-five, ten and fifteen bosses are concrete units with independent health
# multipliers and a timed power.  Defeating one grants medals for the
# Instructor card instead of blanket stat increases.
BOSS_DATA: dict[str, dict[str, Any]] = {
    "city_demolisher": dict(sprite="bruto", label="Demolidor de Asfalto", hp_mult=3.5, damage_mult=1.10, speed_mult=.90, armor=.10, power="stomp", interval=5.0, medals=1, desc="Pisoteio: dano e atordoamento na linha"),
    "city_commander": dict(sprite="general_morto", label="Comandante da Horda", hp_mult=2.65, damage_mult=1.14, speed_mult=.86, armor=.14, power="rally", interval=6.2, medals=1, desc="Grito de guerra: acelera a horda"),
    "city_colossus": dict(sprite="mutante_titan", label="Colosso da Quarentena", hp_mult=2.15, damage_mult=1.20, speed_mult=.78, armor=.18, power="corrosion", interval=5.7, medals=2, desc="Névoa ácida: envenena a linha"),
    "desert_sandmaw": dict(sprite="sandstalker", label="Mandíbula das Dunas", hp_mult=9.5, damage_mult=1.18, speed_mult=.91, armor=.08, power="sandstorm", interval=5.3, medals=1, desc="Tempestade: atordoa os defensores"),
    "desert_oracle": dict(sprite="necromante", label="Oráculo Enterrado", hp_mult=7.6, damage_mult=1.12, speed_mult=.84, armor=.12, power="summon", interval=6.2, medals=1, desc="Ritual: convoca lacaios"),
    "desert_titan": dict(sprite="mutante_titan", label="Titã das Pirâmides", hp_mult=2.75, damage_mult=1.26, speed_mult=.77, armor=.16, power="quake", interval=5.5, medals=2, desc="Abalo sísmico: danifica e atordoa"),
    "beach_tidebrute": dict(sprite="tide_brute", label="Bruto da Maré Negra", hp_mult=3.6, damage_mult=1.13, speed_mult=.89, armor=.10, power="tidal", interval=5.1, medals=1, desc="Onda de choque: trava a linha"),
    "beach_captain": dict(sprite="blindado", label="Capitão Afogado", hp_mult=7.3, damage_mult=1.16, speed_mult=.83, armor=.22, power="rally", interval=6.0, medals=1, desc="Chamado náutico: acelera a horda"),
    "beach_leviathan": dict(sprite="mutante_titan", label="Leviatã da Ressaca", hp_mult=3.15, damage_mult=1.28, speed_mult=.75, armor=.18, power="tidal", interval=4.9, medals=2, desc="Ressaca: atordoa e causa impacto"),
}

# The HD artwork is intentionally rendered with different silhouettes.  Humans
# read tall, vehicles read wide, crawlers stay low, and bosses visibly overhang
# a normal cell.  The gameplay hit model remains deliberately simple.
UNIT_DRAW_SIZES = {key: (88, 108) for key in UNIT_DATA}
UNIT_DRAW_SIZES.update({
    "buggy": (114, 76), "lancha_patrulha": (114, 74), "submarino": (116, 70),
    "vanguardista": (128, 78), "torreta_engenheiro": (90, 86),
    "bomba_agua": (78, 78), "mina": (74, 64), "ferramenta_medica": (82, 70),
})
ZOMBIE_DRAW_SIZES = {key: (84, 110) for key in ZOMBIE_DATA}
ZOMBIE_DRAW_SIZES.update({
    "rastejante": (110, 66), "nadador": (112, 82), "porta_escudo": (104, 126),
    "bruto": (122, 146), "tide_brute": (126, 151), "general_morto": (130, 156),
    "mutante_titan": (146, 172),
})

MISSIONS = [
    dict(
        name="Cidade", code="city", scene="city", title="Operação Quarentena Urbana",
        desc="Feche a avenida antes que os mortos atravessem o centro da cidade.", water_rows=set(),
        doctrine="Cobertura urbana: carros abandonados, interdições e fogo de precisão.",
        pool=["caminhante", "corredor", "conehead", "bandeireiro", "porta_escudo", "cuspidor", "escavadeira", "gritador"],
        bosses={5: "city_demolisher", 10: "city_commander", 15: "city_colossus"},
        units=["recruta", "fuzileiro", "tenente", "general", "sniper", "forcas_especiais", "engenheiro", "instrutor_tatico", "vanguardista", "escopeteiro", "batedor_suprimentos", "operador_radio", "torre_radio", "central_comando", "operador_drone", "buggy", "mina", "ferramenta_medica"],
        unit_names={
            "recruta": "Recruta da Avenida", "fuzileiro": "Fuzileiro da Avenida", "tenente": "Tenente de Cerco", "general": "General da Quarentena",
            "sniper": "Sniper de Cobertura", "forcas_especiais": "Equipe Tática Urbana", "engenheiro": "Engenheiro de Barricada",
            "instrutor_tatico": "Instrutor de Quarentena", "vanguardista": "Vanguardista Urbano",
            "escopeteiro": "Patrulheiro de Brecha", "batedor_suprimentos": "Coletor de Caixas", "operador_radio": "Operador de Rádio Urbano",
            "torre_radio": "Torre Repetidora", "central_comando": "Central de Quarentena", "operador_drone": "Drone de Vigilância",
            "buggy": "Buggy de Interdição", "mina": "Mina de Contenção", "ferramenta_medica": "Socorrista de Rua",
        },
        zombie_names={
            "caminhante": "Transeunte Infectado", "corredor": "Corredor de Rua", "conehead": "Operário do Cone",
            "bandeireiro": "Bandeireiro da Horda", "porta_escudo": "Choque Corrompido", "cuspidor": "Cuspidor de Asfalto",
            "escavadeira": "Escavadeira do Metrô", "gritador": "Sirene Humana", "bruto": "Bruto de Demolição", "general_morto": "General Morto",
            "mutante_titan": "Colosso da Quarentena",
        },
        zombie_abilities={
            "caminhante": "Massa de rua", "corredor": "Arrancada de avenida", "conehead": "Capacete de obra",
            "bandeireiro": "Reúne a horda", "porta_escudo": "Escudo de choque", "cuspidor": "Lodo corrosivo",
            "escavadeira": "Passagem subterrânea", "gritador": "Alarme de sirene",
        },
    ),
    dict(
        name="Deserto", code="desert", scene="desert_v2", title="Operação Areia Escaldante",
        desc="Mantenha a estrada das pirâmides antes que a tempestade de areia engula o comboio.", water_rows=set(),
        doctrine="Disciplina das dunas: visão longa, explosivos e blindagem contra a areia.",
        pool=["caminhante", "feral", "sandstalker", "toxico", "cuspidor", "necromante", "escavadeira", "divisor", "pulador"],
        bosses={5: "desert_sandmaw", 10: "desert_oracle", 15: "desert_titan"},
        units=["recruta", "fuzileiro", "tenente", "bombardeiro", "sniper", "morteiro", "rambo", "engenheiro", "instrutor_tatico", "vanguardista", "lanca_chamas", "escopeteiro", "batedor_suprimentos", "operador_radio", "torre_radio", "central_comando", "buggy", "mina", "ferramenta_medica"],
        unit_names={
            "recruta": "Batedor Novato", "fuzileiro": "Batedor das Dunas", "tenente": "Tenente do Comboio", "bombardeiro": "Bombardeiro de Areia",
            "sniper": "Olho da Duna", "morteiro": "Morteiro de Expedição", "rambo": "Veterano do Deserto",
            "engenheiro": "Mecânico do Comboio", "lanca_chamas": "Purificador de Areia", "escopeteiro": "Vigia da Caravana",
            "instrutor_tatico": "Instrutor de Expedição", "vanguardista": "Vanguardista do Comboio",
            "batedor_suprimentos": "Coletor de Cantis", "operador_radio": "Rádio do Comboio", "torre_radio": "Repetidora das Dunas",
            "central_comando": "Comando da Expedição", "buggy": "Buggy de Escolta", "mina": "Mina de Areia", "ferramenta_medica": "Médico de Expedição",
        },
        zombie_names={
            "caminhante": "Viajante Ressecado", "feral": "Feral da Duna", "sandstalker": "Sandstalker", "toxico": "Tóxico do Oásis",
            "cuspidor": "Cuspidor de Cacto", "necromante": "Necromante das Areias", "escavadeira": "Escavadeira Sepultada",
            "divisor": "Divisor das Dunas", "pulador": "Pulador de Ruínas", "bruto": "Bruto de Pedra", "mutante_titan": "Mutante Titã",
        },
        zombie_abilities={
            "caminhante": "Passos arrastados na areia", "feral": "Corrida de tempestade", "sandstalker": "Mergulho na areia", "toxico": "Veneno do oásis",
            "cuspidor": "Espinho ácido", "necromante": "Ritual de cura", "escavadeira": "Túnel soterrado",
            "divisor": "Ninhada de areia", "pulador": "Salto entre ruínas",
        },
    ),
    dict(
        name="Praia", code="beach", scene="beach", title="Operação Costa Sombria",
        desc="Defenda a faixa de areia e controle a maré antes que a enseada seja tomada.", water_rows={1, 2, 3},
        doctrine="Tática costeira: fuzileiros navais, maré rasa e interdição do píer.",
        pool=["nadador", "blindado", "porta_escudo", "cuspidor", "doutor_zumbi", "gritador", "caminhante", "corredor"],
        bosses={5: "beach_tidebrute", 10: "beach_captain", 15: "beach_leviathan"},
        units=["recruta", "fuzileiro", "tenente", "engenheiro", "instrutor_tatico", "vanguardista", "escopeteiro", "batedor_suprimentos", "operador_radio", "torre_radio", "central_comando", "operador_drone", "lancha_patrulha", "submarino", "bomba_agua", "mina", "ferramenta_medica"],
        unit_names={
            "recruta": "Fuzileiro Novato", "fuzileiro": "Fuzileiro Naval", "tenente": "Tenente Costeiro", "engenheiro": "Engenheiro do Píer",
            "instrutor_tatico": "Instrutor Naval", "vanguardista": "Vanguardista Costeiro",
            "escopeteiro": "Guarda da Faixa", "batedor_suprimentos": "Coletor de Boias", "operador_radio": "Rádio Costeiro",
            "torre_radio": "Farol Repetidor", "central_comando": "Central de Maré", "operador_drone": "Drone de Salvamento",
            "lancha_patrulha": "Lancha de Patrulha", "submarino": "Submarino de Defesa", "bomba_agua": "Bomba de Maré",
            "mina": "Mina de Areia", "ferramenta_medica": "Socorrista Naval",
        },
        zombie_names={
            "nadador": "Nadador da Maré", "blindado": "Mergulhador Blindado", "porta_escudo": "Salva-Vidas Corrompido",
            "cuspidor": "Cuspidor Salino", "doutor_zumbi": "Doutor da Praia", "gritador": "Sereia Morta",
            "caminhante": "Turista Afogado", "corredor": "Surfista Feral", "tide_brute": "Tide Brute", "mutante_titan": "Titã da Ressaca",
        },
        zombie_abilities={
            "nadador": "Impulso de maré", "blindado": "Traje de mergulho", "porta_escudo": "Prancha-escudo",
            "cuspidor": "Jato salino", "doutor_zumbi": "Primeiros socorros mortos", "gritador": "Chamado da ressaca",
            "caminhante": "Areia pesada", "corredor": "Investida de espuma",
        },
    ),
]

# The city road widens toward the camera.  These bounds make the invisible
# placement cells follow the real avenue perspective instead of floating in a
# rectangular layer over the image.
CITY_ROW_BOUNDS = ((230, 1205), (208, 1222), (186, 1239), (164, 1256), (142, 1273))

# Fifteen waves make the arc deliberate: the opening teaches placement,
# waves 5/10/15 introduce bosses, and the final third escalates both the
# horde and individual enemy pressure.  It cannot be solved by one row of a
# single high-output card.
WAVE_PROFILES = (
    dict(count=3, unlock=1, hp=.72, speed=.80, damage=.66, spacing=1.46),
    dict(count=4, unlock=2, hp=.80, speed=.86, damage=.73, spacing=1.34),
    dict(count=5, unlock=2, hp=.91, speed=.91, damage=.82, spacing=1.22),
    dict(count=7, unlock=3, hp=1.04, speed=.97, damage=.92, spacing=1.10),
    dict(count=8, unlock=4, hp=1.20, speed=1.03, damage=1.04, spacing=1.00),
    dict(count=10, unlock=4, hp=1.34, speed=1.08, damage=1.14, spacing=.91),
    dict(count=12, unlock=5, hp=1.50, speed=1.13, damage=1.27, spacing=.82),
    dict(count=14, unlock=6, hp=1.70, speed=1.18, damage=1.40, spacing=.74),
    dict(count=16, unlock=6, hp=1.92, speed=1.23, damage=1.55, spacing=.67),
    dict(count=18, unlock=7, hp=2.17, speed=1.29, damage=1.71, spacing=.61),
    dict(count=20, unlock=7, hp=2.45, speed=1.35, damage=1.89, spacing=.56),
    dict(count=23, unlock=8, hp=2.76, speed=1.41, damage=2.08, spacing=.51),
    dict(count=26, unlock=8, hp=3.10, speed=1.47, damage=2.29, spacing=.47),
    dict(count=29, unlock=9, hp=3.47, speed=1.53, damage=2.52, spacing=.43),
    dict(count=33, unlock=9, hp=3.88, speed=1.60, damage=2.78, spacing=.39),
)


@dataclass
class Defender:
    key: str
    row: int
    col: int
    hp: float
    cooldown: float = .45
    pulse: float = 0
    attack: float = 0
    used: bool = False
    poison: float = 0
    rank: int = 1
    owner: tuple[int, int] | None = None
    stun: float = 0


@dataclass
class Zombie:
    key: str
    row: int
    x: float
    hp: float
    attack_timer: float = 0
    slow: float = 0
    jumped: bool = False
    flash: float = 0
    max_hp: float = 0
    speed_scale: float = 1.0
    damage_scale: float = 1.0
    walk_phase: float = 0.0
    attack_pulse: float = 0.0
    boss_id: str | None = None
    boss_power_timer: float = 0.0
    rally: float = 0.0


@dataclass
class Projectile:
    x: float
    y: float
    row: int
    damage: float
    speed: float
    color: tuple[int, int, int]
    splash: float = 0
    slow: float = 0
    pierce: int = 0
    target_any: bool = False
    flame: bool = False
    visual: str = "bullet"
    angle: float = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    life: float
    size: float


@dataclass
class Effect:
    key: str
    x: float
    y: float
    life: float
    max_life: float
    scale: float = 1.0
    angle: float = 0.0
    spin: float = 0.0


@dataclass
class Pickup:
    x: float
    y: float
    amount: int
    life: float = 7
    drift: float = 0


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Soldados vs Zumbis")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "tiny": pygame.font.SysFont("arial", 12, bold=True),
            "small": pygame.font.SysFont("arial", 15, bold=True),
            "body": pygame.font.SysFont("arial", 19),
            "med": pygame.font.SysFont("arial", 24, bold=True),
            "large": pygame.font.SysFont("arial", 42, bold=True),
            "title": pygame.font.SysFont("impact", 64),
        }
        self.rng = random.Random()
        self.running = True
        self.scene = "loading"
        self.loading_elapsed = 0.0
        # Assets are intentionally loaded after the window is visible. The
        # old opening only animated a progress bar after every image had
        # already been read from disk; this queue keeps the menu responsive
        # and leaves the battle with its resources in memory.
        self.loading_duration = 1.25
        self.loading_total = 0
        self.loading_completed = 0
        self.loading_status = "Inicializando posto de comando"
        self.assets_ready = False
        self.toast = ""
        self.toast_timer = 0.0
        self.time = 0.0
        self.progress = self.load_progress()
        self.stage = 0
        self.selection: list[str] = []
        self.selected_card: str | None = None
        self.card_cooldowns: dict[str, float] = {}
        self.remove_mode = False
        self.paused = False
        self.end_state: str | None = None
        self.defenders: list[Defender] = []
        self.zombies: list[Zombie] = []
        self.projectiles: list[Projectile] = []
        self.particles: list[Particle] = []
        self.effects: list[Effect] = []
        self.pickups: list[Pickup] = []
        self.supplies = STARTING_SUPPLIES[0]
        self.row_mines: list[bool] = [True] * ROWS
        self.defeat_reason = ""
        self.wave = 0
        self.total_waves = len(WAVE_PROFILES)
        self.wave_profile = WAVE_PROFILES[0]
        self.kills = 0
        self.medals = 0
        self.bosses_defeated = 0
        self.queue: list[tuple[str, str | None]] = []
        self.spawn_timer = 0
        self.intermission = 0
        self.pickup_timer = 5
        self.banner = 0
        self.dossier_kind = "units"
        self.dossier_page = 0
        self.dossier_key: str | None = None
        self.assets = self.empty_asset_store()
        self.ground_layers: dict[str, pygame.Surface] = {}
        self.loading_jobs = self.build_loading_jobs()
        self.loading_total = len(self.loading_jobs)

    def load_progress(self) -> int:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                return max(1, min(len(MISSIONS), int(json.load(file).get("unlocked", 1))))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 1

    def save_progress(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump({"unlocked": self.progress}, file, ensure_ascii=False, indent=2)

    def empty_asset_store(self) -> dict[str, Any]:
        """Return the in-memory cache before the loading screen starts."""
        return {
            "opening": None,
            "units": {},
            "zombies": {},
            "regional_units": {},
            "regional_zombies": {},
            "terrain": {},
            "scenes": {},
            "props": {},
            "effects": {},
        }

    def fullscreen_image(self, path: str) -> pygame.Surface | None:
        try:
            source = pygame.image.load(path).convert()
            return pygame.transform.smoothscale(source, (WIDTH, HEIGHT))
        except (pygame.error, FileNotFoundError):
            return None

    def build_loading_jobs(self) -> list[tuple[str, Any]]:
        """Build one small loading task per visual resource.

        Jobs run from the update loop after a first loading frame has been
        drawn. That makes the loading screen truthful: it is visible while
        resources are prepared and combat does not need to reopen image files.
        """
        jobs: list[tuple[str, Any]] = []

        def load_opening():
            path = os.path.join(ASSET_DIR, "hd", "ui", "abertura_urbana_v6.png")
            self.assets["opening"] = self.fullscreen_image(path)

        jobs.append(("Arte de abertura urbana", load_opening))

        for key in UNIT_DATA:
            asset_key = UNIT_ASSET_KEYS.get(key, key)

            def load_unit(key=key, asset_key=asset_key):
                hd_path = os.path.join(ASSET_DIR, "hd", "units", f"{asset_key}.png")
                path = hd_path if os.path.exists(hd_path) else os.path.join(ASSET_DIR, "units", f"{asset_key}.png")
                self.assets["units"][key] = self.safe_image(path, UNIT_DRAW_SIZES[key], UNIT_DATA[key]["color"])

            jobs.append((f"Soldado: {UNIT_DATA[key]['label']}", load_unit))

        for key in ZOMBIE_DATA:

            def load_zombie(key=key):
                hd_path = os.path.join(ASSET_DIR, "hd", "zombies", f"{key}.png")
                path = hd_path if os.path.exists(hd_path) else os.path.join(ASSET_DIR, "zombies", f"{key}.png")
                self.assets["zombies"][key] = self.safe_image(path, ZOMBIE_DRAW_SIZES[key], ZOMBIE_DATA[key]["color"])

            jobs.append((f"Ameaça: {ZOMBIE_DATA[key]['label']}", load_zombie))

        for key, variants in REGIONAL_UNIT_ASSETS.items():
            for code, asset_key in variants.items():

                def load_regional_unit(key=key, code=code, asset_key=asset_key):
                    path = os.path.join(ASSET_DIR, "hd", "units", f"{asset_key}.png")
                    self.assets["regional_units"].setdefault(key, {})[code] = self.safe_image(
                        path, UNIT_DRAW_SIZES[key], UNIT_DATA[key]["color"]
                    )

                jobs.append((f"Uniforme {code}: {UNIT_DATA[key]['label']}", load_regional_unit))

        for key, variants in REGIONAL_ZOMBIE_ASSETS.items():
            for code, asset_key in variants.items():

                def load_regional_zombie(key=key, code=code, asset_key=asset_key):
                    path = os.path.join(ASSET_DIR, "hd", "zombies", f"{asset_key}.png")
                    self.assets["regional_zombies"].setdefault(key, {})[code] = self.safe_image(
                        path, ZOMBIE_DRAW_SIZES[key], ZOMBIE_DATA[key]["color"]
                    )

                jobs.append((f"Variante {code}: {ZOMBIE_DATA[key]['label']}", load_regional_zombie))

        for mission in MISSIONS:
            code = mission["code"]

            def load_terrain(code=code):
                path = os.path.join(ASSET_DIR, "terrain", f"{code}.png")
                self.assets["terrain"][code] = self.safe_image(path, (CELL_W, CELL_H), (80, 120, 70))

            def load_scene(code=code, scene=mission.get("scene", code)):
                path = os.path.join(ASSET_DIR, "hd", "scenes", f"{scene}.png")
                self.assets["scenes"][code] = self.safe_image(path, (WIDTH, HEIGHT), (28, 47, 43))

            jobs.append((f"Terreno: {mission['name']}", load_terrain))
            jobs.append((f"Cenário: {mission['name']}", load_scene))

        for key in ("mina_contencao",):

            def load_prop(key=key):
                path = os.path.join(ASSET_DIR, "hd", "props", f"{key}.png")
                self.assets["props"][key] = self.safe_image(path, (100, 78), (90, 104, 82))

            jobs.append((f"Defesa: {key.replace('_', ' ')}", load_prop))

        for key in ("muzzle", "bullet", "grenade", "explosion", "flame", "heal", "water_splash"):

            def load_effect(key=key):
                path = os.path.join(ASSET_DIR, "hd", "effects", f"{key}.png")
                self.assets["effects"][key] = self.safe_image(path, (128, 128), (240, 190, 80))

            jobs.append((f"Efeito: {key.replace('_', ' ')}", load_effect))

        def load_ground_layers():
            self.ground_layers = self.build_ground_layers()

        jobs.append(("Ajustando terreno jogável", load_ground_layers))
        return jobs

    def update_loading(self):
        """Load a small batch every rendered frame until the cache is ready."""
        for _ in range(2):
            if not self.loading_jobs:
                break
            label, job = self.loading_jobs.pop(0)
            self.loading_status = label
            job()
            self.loading_completed += 1
        if not self.loading_jobs and not self.assets_ready:
            self.assets_ready = True
            self.loading_status = "Operação pronta"

    def safe_image(self, path: str, size: tuple[int, int], fallback: tuple[int, int, int]) -> pygame.Surface:
        try:
            source = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(source, size)
        except (pygame.error, FileNotFoundError):
            surface = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.ellipse(surface, (0, 0, 0, 65), (8, size[1] - 16, size[0] - 16, 10))
            pygame.draw.circle(surface, fallback, (size[0] // 2, size[1] // 2 - 10), min(size) // 3)
            return surface

    def mission(self) -> dict[str, Any]:
        return MISSIONS[self.stage]

    def unit_label(self, key: str) -> str:
        return self.mission().get("unit_names", {}).get(key, UNIT_DATA[key]["label"])

    def zombie_label(self, key: str) -> str:
        return self.mission().get("zombie_names", {}).get(key, ZOMBIE_DATA[key]["label"])

    def zombie_ability(self, key: str) -> str:
        return self.mission().get("zombie_abilities", {}).get(key, "Ameaça escalável")

    def defender_max_hp(self, key: str, rank: int = 1) -> float:
        """Ranks are earned visibly through boss medals, never pre-selected buffs."""
        return UNIT_DATA[key]["hp"] * (1 + .18 * max(0, rank - 1))

    def defender_damage(self, defender: Defender) -> float:
        rank_bonus = 1 + .26 * max(0, defender.rank - 1)
        return UNIT_DATA[defender.key]["damage"] * rank_bonus * self.command_bonus(defender)

    def defender_range(self, defender: Defender) -> float:
        base = UNIT_DATA[defender.key].get("range", float("inf"))
        if math.isinf(base):
            return base
        # The recruit begins at two cells, then earns genuinely useful reach.
        extension = 76 * max(0, defender.rank - 1) if defender.key == "recruta" else 28 * max(0, defender.rank - 1)
        return base + extension

    def defender_rate(self, defender: Defender) -> float:
        return max(.18, UNIT_DATA[defender.key]["rate"] * (1 - .07 * max(0, defender.rank - 1)))

    def radio_income(self, data: dict[str, Any]) -> int:
        return max(1, int(data.get("income", RADIO_SUPPLIES)))

    def unit_image(self, key: str) -> pygame.Surface:
        code = self.mission()["code"]
        regional = self.assets["regional_units"].get(key, {})
        return regional.get(code, self.assets["units"][key])

    def zombie_image(self, key: str) -> pygame.Surface:
        code = self.mission()["code"]
        regional = self.assets["regional_zombies"].get(key, {})
        return regional.get(code, self.assets["zombies"][key])

    def build_ground_layers(self) -> dict[str, pygame.Surface]:
        """Add only subtle map-specific texture over the integrated scenery.

        The generated city road, desert road and beach are the battlefield;
        these transparent overlays add small playable cues without returning a
        bordered rectangle or visible square grid.
        """
        return {mission["code"]: self.make_ground_layer(mission["code"]) for mission in MISSIONS}

    def make_ground_layer(self, code: str) -> pygame.Surface:
        rng = random.Random(f"soldados-vs-zumbis-ground-{code}")
        ground = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        if code == "city":
            ground.fill((18, 21, 21, 20))
            for row in range(1, ROWS):
                y = row * CELL_H - 5
                pygame.draw.line(ground, (240, 211, 139, 25), (0, y), (BOARD_W, y), 1)
            for _ in range(46):
                x, y = rng.randrange(-30, BOARD_W), rng.randrange(0, BOARD_H)
                pygame.draw.ellipse(ground, (15, 20, 21, rng.randrange(10, 28)), (x, y, rng.randrange(12, 75), rng.randrange(2, 9)))
        elif code == "desert":
            ground.fill((178, 92, 34, 18))
            for _ in range(80):
                x, y = rng.randrange(-30, BOARD_W), rng.randrange(0, BOARD_H)
                pygame.draw.arc(ground, (243, 194, 112, rng.randrange(18, 48)), (x, y, rng.randrange(38, 130), rng.randrange(6, 18)), .1, math.pi - .1, 1)
        else:  # beach
            pygame.draw.rect(ground, (40, 166, 188, 26), (0, CELL_H, BOARD_W, CELL_H * 3))
            for _ in range(74):
                y = rng.randrange(CELL_H + 4, CELL_H * 4 - 4)
                x = rng.randrange(-30, BOARD_W)
                pygame.draw.arc(ground, (223, 249, 240, rng.randrange(35, 78)), (x, y, rng.randrange(22, 78), rng.randrange(4, 12)), .12, math.pi - .12, 1)
            for _ in range(35):
                x = rng.randrange(-20, BOARD_W)
                y = rng.choice((rng.randrange(0, CELL_H), rng.randrange(CELL_H * 4, BOARD_H)))
                pygame.draw.ellipse(ground, (219, 179, 104, rng.randrange(12, 34)), (x, y, rng.randrange(9, 50), rng.randrange(2, 8)))
        return ground

    @staticmethod
    def fit_image(image: pygame.Surface, bound: tuple[int, int]) -> pygame.Surface:
        """Scale an image into a card without turning vehicles into tall blobs."""
        factor = min(bound[0] / image.get_width(), bound[1] / image.get_height())
        return pygame.transform.smoothscale(image, (max(1, int(image.get_width() * factor)), max(1, int(image.get_height() * factor))))

    def render_text(self, text: str, pos: tuple[int, int], font="body", color=(238, 235, 216), center=False, shadow=True):
        image = self.fonts[font].render(text, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        if shadow:
            shadow_img = self.fonts[font].render(text, True, (13, 18, 17))
            self.screen.blit(shadow_img, rect.move(2, 2))
        self.screen.blit(image, rect)
        return rect

    def panel(self, rect: pygame.Rect, fill=(30, 42, 40), border=(116, 130, 110), radius=10, inset=True):
        pygame.draw.rect(self.screen, (12, 20, 20), rect.inflate(5, 5), border_radius=radius + 2)
        pygame.draw.rect(self.screen, border, rect, border_radius=radius)
        pygame.draw.rect(self.screen, fill, rect.inflate(-4, -4), border_radius=max(2, radius - 2))
        if inset:
            pygame.draw.line(self.screen, (186, 179, 139), (rect.x + 8, rect.y + 4), (rect.right - 8, rect.y + 4), 1)

    def button(self, rect: pygame.Rect, label: str, color=(89, 129, 72), enabled=True, font="med"):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse) and enabled
        dark = tuple(max(0, c - 35) for c in color)
        self.panel(rect, color if hover else dark, (221, 191, 117) if hover else (75, 84, 72), 8)
        label_color = (255, 248, 218) if enabled else (123, 126, 112)
        self.render_text(label, rect.center, font, label_color, center=True)
        return rect

    def toast_message(self, message: str, duration=2.3):
        self.toast, self.toast_timer = message, duration

    def start_selection(self, stage: int):
        self.stage = stage
        self.selection = []
        self.scene = "select"
        self.toast_message("Monte até 8 cartas. Medalhas de chefe evoluem unidades durante a operação.", 3.2)

    def available_units(self) -> list[str]:
        return [key for key in MISSIONS[self.stage]["units"] if not UNIT_DATA[key].get("hidden")]

    def begin_game(self):
        if not self.selection:
            self.toast_message("Escolha pelo menos uma carta.")
            return
        self.scene = "game"
        self.supplies = STARTING_SUPPLIES[self.stage]
        self.defenders, self.zombies, self.projectiles, self.particles, self.effects, self.pickups = [], [], [], [], [], []
        self.row_mines = [True] * ROWS
        self.defeat_reason = ""
        self.selected_card = None
        self.card_cooldowns = {key: 0 for key in self.selection}
        self.remove_mode = False
        self.paused = False
        self.end_state = None
        self.wave = 0
        self.kills = 0
        self.medals = 0
        self.bosses_defeated = 0
        self.queue = []
        self.spawn_timer = .6
        self.intermission = .5
        self.pickup_timer = 11.5
        self.banner = 2.5
        self.next_wave()

    def next_wave(self):
        self.wave += 1
        if self.wave > self.total_waves:
            self.victory()
            return
        mission = MISSIONS[self.stage]
        self.wave_profile = WAVE_PROFILES[self.wave - 1]
        available = mission["pool"][: min(len(mission["pool"]), self.wave_profile["unlock"])]
        quantity = self.wave_profile["count"] + self.stage * 2
        minions: list[tuple[str, str | None]] = [(self.rng.choice(available), None) for _ in range(quantity)]
        if self.wave >= 8:
            minions.append((self.rng.choice(available[-min(3, len(available)):]), None))
        self.rng.shuffle(minions)
        boss_id = mission["bosses"].get(self.wave)
        # The queue is popped from the right.  Keeping the boss at the left
        # lets the wave show its own horde first and announces the boss when
        # the line has already had a moment to establish its threats.
        self.queue = [(BOSS_DATA[boss_id]["sprite"], boss_id)] + minions if boss_id else minions
        self.spawn_timer = self.wave_profile["spacing"]
        self.banner = 3.0
        if boss_id:
            boss = BOSS_DATA[boss_id]
            self.toast_message(f"ONDA {self.wave}/{self.total_waves} — CHEFE: {boss['label']}", 3.4)
        else:
            self.toast_message(f"ONDA {self.wave}/{self.total_waves} — ameaça {len(self.queue)}", 2.8)

    def victory(self):
        self.end_state = "victory"
        if self.stage < len(MISSIONS) - 1 and self.progress <= self.stage + 1:
            self.progress = min(len(MISSIONS), self.stage + 2)
            self.save_progress()
        self.toast_message("Operação concluída. Próxima região desbloqueada!", 4)

    def defeat(self, reason: str = "A horda atravessou a última linha de defesa."):
        self.end_state = "defeat"
        self.defeat_reason = reason
        self.toast_message("GAME OVER — a horda alcançou o posto. Reagrupe o esquadrão.", 4)

    def row_bounds(self, row: int) -> tuple[int, int]:
        if self.mission()["code"] == "city":
            return CITY_ROW_BOUNDS[row]
        return BOARD_X, BOARD_X + BOARD_W

    def cell_rect(self, row: int, col: int) -> pygame.Rect:
        left, right = self.row_bounds(row)
        cell_w = (right - left) / COLS
        x1 = round(left + col * cell_w)
        x2 = round(left + (col + 1) * cell_w)
        return pygame.Rect(x1, BOARD_Y + row * CELL_H, x2 - x1, CELL_H)

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        return self.cell_rect(row, col).center

    def row_ground_y(self, row: int) -> int:
        return self.cell_rect(row, COLS // 2).bottom - 4

    def row_spawn_x(self, row: int) -> int:
        return self.row_bounds(row)[1]

    def row_breach_x(self, row: int) -> int:
        return self.row_bounds(row)[0] - 26

    def defender_at(self, row: int, col: int) -> Defender | None:
        return next((d for d in self.defenders if d.row == row and d.col == col), None)

    def board_cell(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not BOARD_Y <= pos[1] < BOARD_Y + BOARD_H:
            return None
        row = int((pos[1] - BOARD_Y) // CELL_H)
        left, right = self.row_bounds(row)
        if not left <= pos[0] < right:
            return None
        col = int((pos[0] - left) / ((right - left) / COLS))
        return int(row), int(col)

    def card_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(226 + index * 127, 73, 119, 83)

    def selection_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(78 + (index % 5) * 226, 153 + (index // 5) * 114, 210, 104)

    @staticmethod
    def title_button_rect(index: int) -> pygame.Rect:
        return pygame.Rect(70, 409 + index * 48, 330, 39)

    @staticmethod
    def campaign_rect(index: int) -> pygame.Rect:
        card_w, gap = 338, 46
        total = len(MISSIONS) * card_w + (len(MISSIONS) - 1) * gap
        return pygame.Rect((WIDTH - total) // 2 + index * (card_w + gap), 208, card_w, 330)

    @staticmethod
    def dossier_item_rect(index: int) -> pygame.Rect:
        return pygame.Rect(46 + (index % 2) * 248, 196 + (index // 2) * 103, 232, 88)

    @staticmethod
    def dossier_back_rect() -> pygame.Rect:
        return pygame.Rect(46, 645, 188, 42)

    @staticmethod
    def dossier_previous_rect() -> pygame.Rect:
        return pygame.Rect(248, 645, 146, 42)

    @staticmethod
    def dossier_next_rect() -> pygame.Rect:
        return pygame.Rect(408, 645, 146, 42)

    def dossier_keys(self, kind: str | None = None) -> list[str]:
        kind = kind or self.dossier_kind
        if kind == "units":
            return [key for key, data in UNIT_DATA.items() if not data.get("hidden")]
        return list(ZOMBIE_DATA)

    def dossier_page_count(self) -> int:
        return max(1, math.ceil(len(self.dossier_keys()) / 8))

    def dossier_page_keys(self) -> list[str]:
        start = self.dossier_page * 8
        return self.dossier_keys()[start:start + 8]

    def open_dossier(self, kind: str):
        self.dossier_kind = kind
        self.dossier_page = 0
        entries = self.dossier_page_keys()
        self.dossier_key = entries[0] if entries else None
        self.scene = f"dossier_{kind}"

    def shift_dossier(self, offset: int):
        self.dossier_page = max(0, min(self.dossier_page_count() - 1, self.dossier_page + offset))
        entries = self.dossier_page_keys()
        self.dossier_key = entries[0] if entries else None

    def event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            self.running = False
        if event.type == pygame.KEYDOWN:
            if self.scene == "loading":
                if self.assets_ready:
                    self.scene = "title"
                else:
                    self.toast_message("Aguarde: os recursos ainda estão sendo preparados.")
                return
            if event.key == pygame.K_ESCAPE:
                if self.scene == "title": self.running = False
                elif self.scene in {"campaign", "about", "dossier_units", "dossier_zombies"}: self.scene = "title"
                elif self.scene == "select": self.scene = "campaign"
                elif self.scene == "game": self.selected_card = None; self.remove_mode = False
            if self.scene in {"dossier_units", "dossier_zombies"}:
                if event.key == pygame.K_LEFT: self.shift_dossier(-1)
                if event.key == pygame.K_RIGHT: self.shift_dossier(1)
            if self.scene == "game":
                if event.key == pygame.K_SPACE: self.paused = not self.paused
                if event.key == pygame.K_e: self.remove_mode = not self.remove_mode; self.selected_card = None
                if event.key == pygame.K_r and self.end_state: self.begin_game()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.scene == "loading":
                if self.assets_ready:
                    self.scene = "title"
                else:
                    self.toast_message("Carregamento em andamento.")
            elif self.scene == "title": self.click_title(event.pos)
            elif self.scene == "about":
                if pygame.Rect(516, 570, 248, 48).collidepoint(event.pos): self.scene = "title"
            elif self.scene in {"dossier_units", "dossier_zombies"}: self.click_dossier(event.pos)
            elif self.scene == "campaign": self.click_campaign(event.pos)
            elif self.scene == "select": self.click_selection(event.pos)
            elif self.scene == "game": self.click_game(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.scene == "game":
            self.selected_card = None; self.remove_mode = False

    def click_title(self, pos):
        if self.title_button_rect(0).collidepoint(pos): self.scene = "campaign"
        elif self.title_button_rect(1).collidepoint(pos): self.scene = "about"
        elif self.title_button_rect(2).collidepoint(pos): self.open_dossier("units")
        elif self.title_button_rect(3).collidepoint(pos): self.open_dossier("zombies")
        elif self.title_button_rect(4).collidepoint(pos): self.running = False

    def click_dossier(self, pos: tuple[int, int]):
        for index, key in enumerate(self.dossier_page_keys()):
            if self.dossier_item_rect(index).collidepoint(pos):
                self.dossier_key = key
                return
        if self.dossier_back_rect().collidepoint(pos):
            self.scene = "title"
        elif self.dossier_previous_rect().collidepoint(pos):
            self.shift_dossier(-1)
        elif self.dossier_next_rect().collidepoint(pos):
            self.shift_dossier(1)

    def click_campaign(self, pos):
        for i in range(len(MISSIONS)):
            rect = self.campaign_rect(i)
            if rect.collidepoint(pos):
                if i + 1 <= self.progress:
                    self.start_selection(i)
                else:
                    self.toast_message("Complete a operação anterior para desbloquear esta região.")
                return
        if pygame.Rect(72, 620, 230, 42).collidepoint(pos): self.scene = "title"
        if pygame.Rect(972, 620, 235, 42).collidepoint(pos):
            self.progress = 1; self.save_progress(); self.toast_message("Campanha reiniciada. Cidade é a única região liberada.")

    def click_selection(self, pos):
        keys = self.available_units()
        for i, key in enumerate(keys):
            if self.selection_rect(i).collidepoint(pos):
                if key in self.selection:
                    self.selection.remove(key)
                elif len(self.selection) < 8:
                    self.selection.append(key)
                else:
                    self.toast_message("O esquadrão já tem 8 cartas. Remova uma para trocar.")
                return
        if pygame.Rect(908, 630, 270, 50).collidepoint(pos): self.begin_game()
        if pygame.Rect(98, 630, 200, 50).collidepoint(pos): self.scene = "campaign"

    def click_game(self, pos):
        if self.end_state:
            if pygame.Rect(481, 518, 160, 49).collidepoint(pos): self.begin_game()
            if pygame.Rect(655, 518, 160, 49).collidepoint(pos): self.scene = "campaign"
            return
        if pygame.Rect(23, 124, 172, 31).collidepoint(pos):
            self.remove_mode = not self.remove_mode; self.selected_card = None
            return
        if pygame.Rect(24, 158, 171, 31).collidepoint(pos):
            self.paused = not self.paused; return
        for i, key in enumerate(self.selection):
            if self.card_rect(i).collidepoint(pos):
                info = UNIT_DATA[key]
                if self.card_cooldowns[key] > 0:
                    self.toast_message("Carta recarregando."); return
                if self.supplies < info["cost"]:
                    self.toast_message("Suprimentos insuficientes."); return
                self.remove_mode = False
                self.selected_card = key if self.selected_card != key else None
                return
        for pickup in list(self.pickups):
            if pygame.Rect(int(pickup.x - 26), int(pickup.y - 23), 52, 46).collidepoint(pos):
                self.supplies += pickup.amount; self.pickups.remove(pickup)
                self.toast_message(f"+{pickup.amount} suprimentos")
                return
        cell = self.board_cell(pos)
        if cell is None: return
        row, col = cell
        existing = self.defender_at(row, col)
        if self.remove_mode:
            if existing:
                self.defenders.remove(existing); self.toast_message("Unidade recolhida.")
            return
        if not self.selected_card: return
        key = self.selected_card
        info = UNIT_DATA[key]
        mission = MISSIONS[self.stage]
        if info.get("tool"):
            if existing:
                existing.hp = min(self.defender_max_hp(existing.key, existing.rank), existing.hp + 180)
                self.supplies -= info["cost"]; self.card_cooldowns[key] = info["rate"]; self.selected_card = None
                center_x, center_y = self.cell_center(row, col)
                self.spawn_effect("heal", center_x, center_y, .7, .68, spin=42)
                self.toast_message("Unidade tratada e estabilizada.")
            else: self.toast_message("A ferramenta médica precisa de uma unidade aliada.")
            return
        # An Engineer can reclaim a deployed turret.  The turret itself is
        # never a purchasable hidden card; it is a construction he manages.
        if info["kind"] == "engineer" and existing and existing.key == "torreta_engenheiro":
            self.defenders.remove(existing)
            self.supplies += 30
            self.card_cooldowns[key] = max(.8, info.get("cooldown", 3.8) * .38)
            self.selected_card = None
            center_x, center_y = self.cell_center(row, col)
            self.spawn_effect("heal", center_x, center_y, .46, .36, spin=-25)
            self.toast_message("Torreta recolhida: +30 SUP recuperados.")
            return
        if existing:
            self.toast_message("A célula já está ocupada."); return
        water = row in mission["water_rows"]
        if info.get("aquatic") and not water:
            self.toast_message("Unidade aquática: só pode ser colocada em uma linha de água."); return
        if not info.get("aquatic") and water:
            self.toast_message("Esta unidade terrestre não pode operar sobre a água."); return
        same_key = [d for d in self.defenders if d.key == key]
        same_row = [d for d in same_key if d.row == row]
        if info.get("max_total") and len(same_key) >= info["max_total"]:
            self.toast_message(f"Limite operacional: {info['max_total']} {self.unit_label(key)}(s).")
            return
        if info.get("max_per_row") and len(same_row) >= info["max_per_row"]:
            self.toast_message(f"A linha já tem o limite de {self.unit_label(key)}.")
            return
        self.defenders.append(Defender(key, row, col, self.defender_max_hp(key, 1)))
        self.supplies -= info["cost"]
        self.card_cooldowns[key] = info.get("cooldown", 2.6) if not info.get("tool") else info["rate"]
        self.selected_card = None
        self.toast_message(f"{self.unit_label(key)} em posição.", 1.2)

    def boss_spec(self, zombie: Zombie) -> dict[str, Any] | None:
        return BOSS_DATA.get(zombie.boss_id or "")

    def is_boss(self, zombie: Zombie) -> bool:
        return zombie.boss_id is not None or bool(ZOMBIE_DATA[zombie.key].get("boss"))

    def boss_label(self, zombie: Zombie) -> str:
        return (self.boss_spec(zombie) or {}).get("label", self.zombie_label(zombie.key))

    def make_zombie(self, key: str, row: int, x: float, hp_scale: float | None = None, speed_scale: float | None = None, damage_scale: float | None = None, boss_id: str | None = None) -> Zombie:
        info = ZOMBIE_DATA[key]
        stage_scale = 1 + self.stage * .08
        hp_scale = hp_scale if hp_scale is not None else self.wave_profile["hp"] * stage_scale
        speed_scale = speed_scale if speed_scale is not None else self.wave_profile["speed"] * (1 + self.stage * .025)
        damage_scale = damage_scale if damage_scale is not None else self.wave_profile["damage"] * stage_scale
        boss = BOSS_DATA.get(boss_id or "")
        if boss:
            hp_scale *= boss["hp_mult"]
            speed_scale *= boss["speed_mult"]
            damage_scale *= boss["damage_mult"]
        hp = info["hp"] * hp_scale
        return Zombie(
            key, row, x, hp, max_hp=hp, speed_scale=speed_scale,
            damage_scale=damage_scale, walk_phase=self.rng.random() * math.tau,
            boss_id=boss_id, boss_power_timer=(boss or {}).get("interval", 0) * .82,
        )

    def spawn_zombie(self, key: str, boss_id: str | None = None):
        mission = MISSIONS[self.stage]
        info = ZOMBIE_DATA[key]
        if info.get("aquatic"):
            rows = list(mission["water_rows"])
        else:
            rows = [r for r in range(ROWS) if r not in mission["water_rows"]]
        if not rows: rows = list(range(ROWS))
        row = self.rng.choice(rows)
        x = self.row_spawn_x(row) + (32 if boss_id else self.rng.randint(14, 80))
        self.zombies.append(self.make_zombie(key, row, x, boss_id=boss_id))
        if boss_id:
            self.spawn_effect("explosion", x, self.row_ground_y(row), .58, 1.14, spin=18)
            self.toast_message(f"CHEFE EM CAMPO — {BOSS_DATA[boss_id]['label']}", 2.7)

    def update(self, dt: float):
        self.time += dt
        self.toast_timer = max(0, self.toast_timer - dt)
        if self.scene == "loading":
            self.loading_elapsed += dt
            self.update_loading()
            if self.assets_ready and self.loading_elapsed >= self.loading_duration:
                self.scene = "title"
            return
        if self.scene != "game" or self.paused or self.end_state: return
        for key in self.card_cooldowns:
            self.card_cooldowns[key] = max(0, self.card_cooldowns[key] - dt)
        self.pickup_timer -= dt
        if self.pickup_timer <= 0:
            self.pickup_timer = self.rng.uniform(*PICKUP_INTERVAL)
            amount = self.rng.choice(PICKUP_VALUES)
            pickup_row = self.rng.randrange(ROWS)
            left, right = self.row_bounds(pickup_row)
            self.pickups.append(Pickup(self.rng.randint(left + 40, right - 40), self.rng.randint(BOARD_Y + pickup_row * CELL_H + 24, BOARD_Y + (pickup_row + 1) * CELL_H - 24), amount))
        for pickup in list(self.pickups):
            pickup.life -= dt; pickup.drift += dt
            pickup.y += math.sin(pickup.drift * 2) * .12
            if pickup.life <= 0: self.pickups.remove(pickup)
        if self.queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                key, boss_id = self.queue.pop()
                self.spawn_zombie(key, boss_id)
                self.spawn_timer = max(.42, self.wave_profile["spacing"] * self.rng.uniform(.84, 1.12))
        elif not self.zombies:
            self.intermission -= dt
            if self.intermission <= 0:
                self.intermission = 2.8
                self.next_wave()
        self.banner = max(0, self.banner - dt)
        self.update_defenders(dt)
        self.update_projectiles(dt)
        self.update_zombies(dt)
        self.update_particles(dt)
        self.update_effects(dt)

    def targets_for(self, defender: Defender, kind: str) -> list[Zombie]:
        candidates = [z for z in self.zombies if z.row == defender.row and z.x >= self.cell_rect(defender.row, defender.col).left - 7]
        if kind in {"mortar", "drone"}:
            candidates = self.zombies[:]
        else:
            distance = self.defender_range(defender)
            if not math.isinf(distance):
                origin = self.cell_rect(defender.row, defender.col).centerx
                candidates = [z for z in candidates if z.x - origin <= distance]
        return sorted(candidates, key=lambda z: z.x)

    def command_bonus(self, defender: Defender) -> float:
        """A single General rewards mixed placements around the command post."""
        for ally in self.defenders:
            if ally is defender or ally.key != "general":
                continue
            if abs(ally.row - defender.row) <= 1 and abs(ally.col - defender.col) <= 2:
                return 1.16
        return 1.0

    def promote_defender(self, defender: Defender) -> bool:
        data = UNIT_DATA[defender.key]
        max_rank = data.get("max_rank", 3)
        if defender.rank >= max_rank:
            return False
        old_max = self.defender_max_hp(defender.key, defender.rank)
        remaining = max(0, defender.hp / old_max)
        defender.rank += 1
        new_max = self.defender_max_hp(defender.key, defender.rank)
        # A promotion is a field refit, so it stabilizes a worn soldier
        # instead of merely increasing the denominator of their health bar.
        defender.hp = max(defender.hp, new_max * min(1.0, remaining + .20))
        x, y = self.cell_center(defender.row, defender.col)
        self.spawn_effect("heal", x, y, .72, .58, spin=34)
        self.impact_particles(x, y - 12, (237, 206, 92), 12)
        return True

    def update_defenders(self, dt: float):
        for d in list(self.defenders):
            d.cooldown -= dt; d.pulse += dt; d.attack = max(0, d.attack - dt)
            data = UNIT_DATA[d.key]
            if d.poison > 0:
                d.poison = max(0, d.poison - dt)
                d.hp -= 4.5 * dt
                if d.hp <= 0:
                    self.defenders.remove(d)
                    continue
            d.stun = max(0, d.stun - dt)
            if data["kind"] == "turret" and d.owner and not any(
                ally.key == "engenheiro" and (ally.row, ally.col) == d.owner for ally in self.defenders
            ):
                self.defenders.remove(d)
                self.toast_message("Torreta desligada: o Engenheiro foi perdido.")
                continue
            if d.stun > 0 and data["kind"] not in {"mine"}:
                continue
            rect = self.cell_rect(d.row, d.col)
            center_x, center_y = rect.center
            if data["kind"] == "mine":
                hit = next((z for z in self.zombies if z.row == d.row and abs(z.x - center_x) < max(45, rect.width * .42)), None)
                if hit:
                    self.explode(center_x, center_y, data["damage"], 110, (75, 201, 207))
                    self.defenders.remove(d)
                continue
            if data["kind"] == "engineer":
                front_col = d.col + 1
                owned_turret = next((ally for ally in self.defenders if ally.key == "torreta_engenheiro" and ally.owner == (d.row, d.col)), None)
                if not owned_turret and front_col < COLS and not self.defender_at(d.row, front_col):
                    turret = Defender(
                        "torreta_engenheiro", d.row, front_col,
                        self.defender_max_hp("torreta_engenheiro"), cooldown=.58,
                        owner=(d.row, d.col),
                    )
                    self.defenders.append(turret)
                    d.cooldown = max(data["rate"], 3.7)
                    tx, ty = self.cell_center(turret.row, turret.col)
                    self.spawn_effect("heal", tx, ty, .65, .56, spin=24)
                    self.toast_message("Engenheiro implantou uma Torreta à frente.", 1.7)
                elif d.cooldown <= 0:
                    damaged = [
                        ally for ally in self.defenders
                        if ally is not d and abs(ally.row - d.row) <= 1 and abs(ally.col - d.col) <= 1
                        and ally.hp < self.defender_max_hp(ally.key, ally.rank)
                    ]
                    if damaged:
                        target = min(damaged, key=lambda ally: ally.hp / self.defender_max_hp(ally.key, ally.rank))
                        target.hp = min(self.defender_max_hp(target.key, target.rank), target.hp + data["repair"])
                        tx, ty = self.cell_center(target.row, target.col)
                        self.spawn_effect("heal", tx, ty, .5, .44, spin=18)
                        d.cooldown = self.defender_rate(d)
                        d.attack = .12
                    else:
                        d.cooldown = .65
                continue
            if data["kind"] == "trainer":
                if d.cooldown <= 0 and self.medals > 0:
                    candidates = [
                        ally for ally in self.defenders
                        if ally is not d and not UNIT_DATA[ally.key].get("hidden")
                        and UNIT_DATA[ally.key]["kind"] not in {"trainer", "radio", "medical", "mine"}
                        and ally.rank < UNIT_DATA[ally.key].get("max_rank", 3)
                        and abs(ally.row - d.row) <= 1 and abs(ally.col - d.col) <= 2
                    ]
                    if candidates:
                        target = min(
                            candidates,
                            key=lambda ally: (
                                0 if UNIT_DATA[ally.key].get("evolvable") else 1,
                                ally.rank,
                                abs(ally.row - d.row) + abs(ally.col - d.col),
                            ),
                        )
                        if self.promote_defender(target):
                            self.medals -= 1
                            d.cooldown = self.defender_rate(d)
                            d.attack = .18
                            self.toast_message(f"{self.unit_label(target.key)} promovido para NÍVEL {target.rank}!", 2.2)
                            continue
                if d.cooldown <= 0:
                    d.cooldown = .7
                continue
            if data["kind"] == "radio" and d.cooldown <= 0:
                income = self.radio_income(data)
                self.supplies += income
                d.cooldown = self.defender_rate(d)
                self.spawn_effect("heal", center_x, rect.top + 29, .6, .42, spin=20)
                self.toast_message(f"{self.unit_label(d.key)}: +{income} suprimentos", 1.1)
                continue
            if data["kind"] == "vanguard":
                # The Vanguardista is deliberately a blocker, not a cheap
                # damage engine.  Its plow slows enemies only at the front.
                for enemy in self.zombies:
                    if enemy.row == d.row and 0 <= enemy.x - center_x <= data.get("range", 150):
                        enemy.slow = max(enemy.slow, .72)
            targets = self.targets_for(d, data["kind"])
            if not targets or d.cooldown > 0: continue
            x = rect.x + int(rect.width * .60)
            y = rect.centery
            damage = self.defender_damage(d)
            if data["kind"] == "flame":
                for z in targets:
                    if z.x - x <= data.get("range", 185): self.hit_zombie(z, damage * .46, slow=0)
                self.flame_particles(x + 25, y, data["color"])
                self.spawn_effect("flame", x + 72, y, .28, .7, spin=-3)
                d.attack = .17
                d.cooldown = self.defender_rate(d)
            elif data["kind"] == "shotgun":
                for z in targets[:3]:
                    if z.x - x <= data.get("range", 300): self.hit_zombie(z, damage * (1 if z is targets[0] else .55))
                self.flame_particles(x + 27, y, (244, 203, 92))
                self.spawn_effect("muzzle", x + 29, y, .18, .42, spin=15)
                d.attack = .16
                d.cooldown = self.defender_rate(d)
            else:
                target = targets[0]
                sx = x; sy = y
                splash = data.get("splash", 0)
                visual = "grenade" if splash else "bullet"
                projectile = Projectile(sx, sy, d.row, damage, 510 if data["kind"] != "mortar" else 260, data["color"], splash=splash, slow=data.get("slow", 0), pierce=data.get("pierce", 0), target_any=data["kind"] in {"mortar", "drone"}, visual=visual, angle=self.rng.uniform(0, 360))
                self.projectiles.append(projectile)
                d.cooldown = self.defender_rate(d)
                self.flame_particles(sx + 20, sy, (243, 184, 65), 3)
                self.spawn_effect("muzzle", sx + 20, sy, .16, .3, spin=18)
                d.attack = .15

    def update_projectiles(self, dt: float):
        for p in list(self.projectiles):
            p.x += p.speed * dt
            if p.visual == "grenade": p.angle += 560 * dt
            candidates = self.zombies if p.target_any else [z for z in self.zombies if z.row == p.row]
            target = next((z for z in candidates if abs(z.x - p.x) < 26 and abs(self.cell_rect(z.row, COLS // 2).centery - p.y) < 46), None)
            if target:
                if p.splash:
                    self.explode(p.x, p.y, p.damage, p.splash, p.color, p.slow)
                else:
                    self.hit_zombie(target, p.damage, p.slow)
                    if p.pierce > 0:
                        p.pierce -= 1; p.x += 30
                        continue
                    self.impact_particles(p.x, p.y, p.color)
                if p in self.projectiles: self.projectiles.remove(p)
            elif p.x > self.row_spawn_x(p.row) + 85:
                self.projectiles.remove(p)

    def hit_zombie(self, z: Zombie, damage: float, slow=0):
        data = ZOMBIE_DATA[z.key]
        boss = self.boss_spec(z)
        armor = min(.70, data.get("armor", 0) + (boss or {}).get("armor", 0))
        actual = damage * (1 - armor)
        z.hp -= actual; z.flash = .11
        if slow:
            z.slow = max(z.slow, slow)
        if z.hp <= 0: self.kill_zombie(z)

    @staticmethod
    def zombie_max_hp(z: Zombie) -> float:
        return z.max_hp or ZOMBIE_DATA[z.key]["hp"]

    def explode(self, x: float, y: float, damage: float, radius: float, color, slow=0):
        if radius > 0:
            effect = "water_splash" if color[2] > color[0] * 1.15 else "explosion"
            self.spawn_effect(effect, x, y, .62, max(.7, radius / 75), spin=22)
        for z in list(self.zombies):
            dist = math.hypot(z.x - x, self.cell_rect(z.row, COLS // 2).centery - y)
            if dist < radius:
                self.hit_zombie(z, damage * (1 - dist / (radius * 1.4)), slow)
        for _ in range(36):
            a = self.rng.random() * math.tau; speed = self.rng.uniform(55, 230)
            self.particles.append(Particle(x, y, math.cos(a)*speed, math.sin(a)*speed, color, self.rng.uniform(.35, .8), self.rng.uniform(2, 7)))

    def kill_zombie(self, z: Zombie, allow_split=True):
        if z not in self.zombies: return
        boss = self.boss_spec(z)
        self.zombies.remove(z)
        self.kills += 1
        ground_y = self.row_ground_y(z.row)
        self.explode(z.x, ground_y, 0, 0, ZOMBIE_DATA[z.key]["color"])
        self.impact_particles(z.x, ground_y, ZOMBIE_DATA[z.key]["color"], 15)
        if boss:
            medals = boss["medals"]
            self.medals += medals
            self.bosses_defeated += 1
            self.supplies += 12 * medals
            self.spawn_effect("explosion", z.x, ground_y, .84, 1.35, spin=27)
            self.impact_particles(z.x, ground_y - 16, (240, 204, 92), 28)
            self.toast_message(f"CHEFE ELIMINADO — +{medals} Medalha(s), +{12 * medals} SUP", 3.2)
        if allow_split and ZOMBIE_DATA[z.key].get("split"):
            split_hp = max(.70, self.zombie_max_hp(z) / ZOMBIE_DATA[z.key]["hp"] * .62)
            for _ in range(2):
                self.zombies.append(self.make_zombie("rastejante", z.row, z.x + self.rng.randint(-12, 12), hp_scale=split_hp, speed_scale=z.speed_scale * 1.08, damage_scale=z.damage_scale))
        if self.rng.random() < .14:
            self.pickups.append(Pickup(z.x, self.cell_rect(z.row, COLS // 2).centery, 5, 4))

    def trigger_row_mine(self, row: int):
        """Detonate the one-use containment mine after a row has been breached."""
        if not self.row_mines[row]:
            return
        self.row_mines[row] = False
        x, y = self.row_bounds(row)[0] - 43, self.cell_rect(row, COLS // 2).centery + 8
        self.spawn_effect("explosion", x, y, .82, 2.45, spin=18)
        for _ in range(58):
            angle = self.rng.random() * math.tau
            speed = self.rng.uniform(75, 285)
            color = self.rng.choice(((238, 174, 70), (224, 92, 55), (111, 105, 68), (228, 207, 148)))
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, color, self.rng.uniform(.35, .86), self.rng.uniform(2, 8)))
        # It is a safety device, not just a high-damage hit.  It clears the
        # breach zone, including a splitter, so the row does not lose in the
        # same frame that the player sees its emergency mine work.
        cleared = 0
        for enemy in list(self.zombies):
            row_left, row_right = self.row_bounds(row)
            if enemy.row == row and enemy.x <= row_left + (row_right - row_left) / COLS * 1.7:
                self.kill_zombie(enemy, allow_split=False)
                cleared += 1
        suffix = "invasor eliminado" if cleared == 1 else f"{cleared} invasores eliminados"
        self.toast_message(f"MINA DE CONTENÇÃO DETONADA — {suffix}.", 2.5)

    def hurt_defender(self, defender: Defender, damage: float, stun: float = 0, poison: float = 0):
        """Apply a boss debuff in one place so all powers remain readable."""
        defender.hp -= damage
        defender.stun = max(defender.stun, stun)
        defender.poison = max(defender.poison, poison)
        x, y = self.cell_center(defender.row, defender.col)
        if stun:
            self.impact_particles(x, y, (219, 184, 87), 8)
        if poison:
            self.impact_particles(x, y, (132, 208, 77), 7)
        if defender.hp <= 0 and defender in self.defenders:
            self.defenders.remove(defender)

    def cast_boss_power(self, z: Zombie):
        boss = self.boss_spec(z)
        if not boss:
            return
        power = boss["power"]
        z.boss_power_timer = boss["interval"]
        ground_y = self.row_ground_y(z.row)
        line = [d for d in self.defenders if d.row == z.row]
        frontline = max(line, key=lambda d: d.col) if line else None
        if power == "stomp":
            if frontline and abs(self.cell_center(frontline.row, frontline.col)[0] - z.x) < 300:
                self.hurt_defender(frontline, 34 * z.damage_scale, stun=1.05)
                self.spawn_effect("explosion", self.cell_center(frontline.row, frontline.col)[0], ground_y, .42, .62, spin=14)
                self.toast_message(f"{boss['label']}: PISOTEIO!", 1.5)
        elif power == "rally":
            for ally in self.zombies:
                if ally is not z and ally.row == z.row and abs(ally.x - z.x) < 400:
                    ally.rally = max(ally.rally, 4.2)
            self.impact_particles(z.x, ground_y - 26, (212, 112, 95), 20)
            self.toast_message(f"{boss['label']}: horda acelerada!", 1.5)
        elif power == "corrosion":
            for defender in line:
                self.hurt_defender(defender, 6 * z.damage_scale, poison=4.8)
            self.spawn_effect("flame", z.x - 20, ground_y - 25, .52, .82, spin=0)
            self.toast_message(f"{boss['label']}: névoa corrosiva!", 1.7)
        elif power == "sandstorm":
            for defender in self.defenders:
                self.hurt_defender(defender, 0, stun=.86)
            self.impact_particles(z.x, ground_y - 10, (232, 182, 93), 34)
            self.toast_message(f"{boss['label']}: tempestade de areia!", 1.7)
        elif power == "summon":
            terrain_water = z.row in self.mission()["water_rows"]
            candidates = [
                key for key in self.mission()["pool"]
                if bool(ZOMBIE_DATA[key].get("aquatic")) == terrain_water and key not in {"necromante", "tide_brute"}
            ]
            for i in range(2):
                if candidates:
                    self.zombies.append(self.make_zombie(self.rng.choice(candidates), z.row, z.x + 44 + i * 32, hp_scale=self.wave_profile["hp"] * .72, speed_scale=z.speed_scale, damage_scale=z.damage_scale * .80))
            self.impact_particles(z.x + 22, ground_y - 20, (171, 114, 213), 22)
            self.toast_message(f"{boss['label']}: lacaios convocados!", 1.7)
        elif power == "quake":
            for defender in self.defenders:
                self.hurt_defender(defender, 17 * z.damage_scale, stun=1.10)
            self.spawn_effect("explosion", z.x, ground_y, .58, 1.15, spin=18)
            self.toast_message(f"{boss['label']}: abalo sísmico!", 1.7)
        elif power == "tidal":
            for defender in line:
                self.hurt_defender(defender, 18 * z.damage_scale, stun=.92)
            self.spawn_effect("water_splash", z.x - 10, ground_y, .62, 1.24, spin=18)
            self.toast_message(f"{boss['label']}: onda de choque!", 1.7)

    def update_zombies(self, dt: float):
        for z in list(self.zombies):
            if z not in self.zombies:
                continue
            data = ZOMBIE_DATA[z.key]
            z.slow = max(0, z.slow - dt)
            z.flash = max(0, z.flash - dt)
            z.attack_pulse = max(0, z.attack_pulse - dt)
            z.rally = max(0, z.rally - dt)
            if z.boss_id:
                z.boss_power_timer -= dt
                if z.boss_power_timer <= 0:
                    self.cast_boss_power(z)
            z.walk_phase += dt * (4.0 + data["speed"] * .18 * z.speed_scale)
            if data.get("healer") and self.rng.random() < dt * .8:
                for ally in self.zombies:
                    if ally is not z and ally.row == z.row and abs(ally.x-z.x) < 105:
                        ally.hp = min(self.zombie_max_hp(ally), ally.hp + 7)
            collided = None
            candidates = [d for d in self.defenders if d.row == z.row and z.x <= self.cell_rect(d.row, d.col).right + 80]
            if candidates:
                collided = max(candidates, key=lambda d: d.col)
            if (data.get("jump") or data.get("dig")) and not z.jumped and collided:
                z.x -= self.cell_rect(collided.row, collided.col).width * (1.25 if data.get("jump") else .72)
                z.jumped = True
                collided = None
                z.attack_pulse = .32
                dust = (205, 160, 74) if data.get("jump") else (154, 112, 62)
                self.impact_particles(z.x, self.row_ground_y(z.row), dust, 9)
            if collided:
                z.attack_timer -= dt
                if z.attack_timer <= 0:
                    dealt = data["damage"] * z.damage_scale * (1.15 if self.is_boss(z) else 1)
                    collided.hp -= dealt
                    if self.mission()["code"] == "desert" and z.key == "toxico":
                        collided.poison = max(collided.poison, 3.6)
                    z.attack_timer = .9 if not data.get("ranged") else .7
                    z.attack_pulse = .34
                    self.impact_particles(self.cell_rect(collided.row, collided.col).centerx, self.row_ground_y(z.row), (192, 77, 61), 5)
                    if collided.hp <= 0:
                        self.defenders.remove(collided)
            else:
                # The Cuspidor stops outside melee range and damages its
                # target from afar, making it a priority instead of a walker
                # with a different sprite.
                ranged_targets = [d for d in self.defenders if d.row == z.row and self.cell_rect(d.row, d.col).right - 28 < z.x <= self.cell_rect(d.row, d.col).left + data.get("range", 0)]
                if data.get("ranged") and ranged_targets:
                    target = max(ranged_targets, key=lambda d: d.col)
                    z.attack_timer -= dt
                    if z.attack_timer <= 0:
                        target.hp -= data["damage"] * z.damage_scale * .58
                        z.attack_timer = 1.30
                        z.attack_pulse = .38
                        self.impact_particles(self.cell_rect(target.row, target.col).centerx, self.cell_rect(target.row, target.col).centery, (116, 200, 81), 7)
                        if target.hp <= 0:
                            self.defenders.remove(target)
                    continue
                speed = data["speed"] * z.speed_scale * (.44 if z.slow > 0 else 1)
                if self.mission()["code"] == "city" and z.key == "corredor":
                    speed *= 1.16  # Arrancada de avenida.
                if self.mission()["code"] == "desert" and z.key == "feral":
                    speed *= 1.11  # Corrida coberta pela tempestade.
                if self.mission()["code"] == "beach" and data.get("aquatic"):
                    speed *= 1.16  # Impulso de maré em linhas de água.
                if data.get("flag"): speed *= 1.08
                if z.rally > 0: speed *= 1.18
                if any(other is not z and other.row == z.row and other.key == "bandeireiro" and abs(other.x - z.x) < 200 for other in self.zombies):
                    speed *= 1.12
                if any(other is not z and other.row == z.row and ZOMBIE_DATA[other.key].get("howl") and abs(other.x - z.x) < 155 for other in self.zombies):
                    speed *= 1.07
                z.x -= speed * dt
            if z.x < self.row_breach_x(z.row):
                if self.row_mines[z.row]:
                    self.trigger_row_mine(z.row)
                    continue
                self.defeat(f"Linha {z.row + 1} rompida: não havia Mina de Contenção.")
                return

    def impact_particles(self, x, y, color, count=8):
        for _ in range(count):
            a = self.rng.random()*math.tau; sp = self.rng.uniform(30, 150)
            self.particles.append(Particle(x, y, math.cos(a)*sp, math.sin(a)*sp, color, self.rng.uniform(.22, .55), self.rng.uniform(1.5, 4)))

    def flame_particles(self, x, y, color, count=6):
        for _ in range(count):
            self.particles.append(Particle(x, y, self.rng.uniform(55, 155), self.rng.uniform(-30, 30), color, self.rng.uniform(.12, .27), self.rng.uniform(2, 5)))

    def spawn_effect(self, key: str, x: float, y: float, life=.35, scale=1.0, angle=0.0, spin=0.0):
        """Start a short-lived, animated PNG effect if the asset is present."""
        if self.assets["effects"].get(key):
            self.effects.append(Effect(key, x, y, life, life, scale, angle, spin))

    def update_effects(self, dt):
        for effect in list(self.effects):
            effect.life -= dt
            effect.angle += effect.spin * dt
            if effect.life <= 0: self.effects.remove(effect)

    def update_particles(self, dt):
        for p in list(self.particles):
            p.life -= dt; p.x += p.vx*dt; p.y += p.vy*dt; p.vy += 75*dt
            if p.life <= 0: self.particles.remove(p)

    def draw(self):
        if self.scene == "loading": self.draw_loading()
        elif self.scene == "title": self.draw_title()
        elif self.scene == "about": self.draw_about()
        elif self.scene == "dossier_units": self.draw_dossier("units")
        elif self.scene == "dossier_zombies": self.draw_dossier("zombies")
        elif self.scene == "campaign": self.draw_campaign()
        elif self.scene == "select": self.draw_selection()
        elif self.scene == "game": self.draw_game()
        self.draw_toast()
        pygame.display.flip()

    def backdrop(self, dim=105):
        opening = self.assets.get("opening")
        if opening:
            self.screen.blit(opening, (0, 0))
        else:
            # The very first frame appears before disk work starts. This
            # lightweight fallback avoids a black flash behind the loader.
            for y in range(0, HEIGHT, 24):
                blend = y / HEIGHT
                color = (
                    int(11 + 14 * blend),
                    int(19 + 21 * blend),
                    int(33 + 28 * blend),
                )
                pygame.draw.rect(self.screen, color, (0, y, WIDTH, 24))
            pygame.draw.ellipse(self.screen, (44, 66, 84), (WIDTH // 2 - 340, 115, 680, 215))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((8, 17, 20, dim)); self.screen.blit(overlay, (0, 0))

    def draw_logo(self, center_x: int, y: int, subtitle=True):
        self.render_text("SOLDADOS", (center_x - 164, y), "large", (235, 221, 181), center=True)
        self.render_text("VS", (center_x, y), "med", (245, 182, 80), center=True)
        self.render_text("ZUMBIS", (center_x + 166, y), "large", (159, 202, 104), center=True)
        if subtitle:
            self.render_text("DEFENDA A LINHA. SOBREVIVA À HORDA.", (center_x, y + 52), "small", (229, 203, 129), center=True)

    def draw_loading(self):
        self.backdrop(68)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (4, 10, 13, 190), (0, 0, WIDTH, 94))
        pygame.draw.rect(vignette, (4, 10, 13, 180), (0, 530, WIDTH, 190))
        self.screen.blit(vignette, (0, 0))
        self.panel(pygame.Rect(312, 78, 656, 151), (16, 27, 30, 222), (216, 174, 83), 18)
        self.draw_logo(640, 108)
        self.render_text("SISTEMA DE DEFESA TÁTICA", (640, 194), "tiny", (174, 210, 188), center=True)
        actual_progress = self.loading_completed / max(1, self.loading_total)
        progress = min(1.0, actual_progress)
        self.panel(pygame.Rect(330, 539, 620, 97), (17, 29, 31, 232), (107, 142, 117), 12)
        pygame.draw.rect(self.screen, (9, 17, 19), (361, 570, 558, 16), border_radius=8)
        pygame.draw.rect(self.screen, (213, 171, 72), (361, 570, max(3, int(558 * progress)), 16), border_radius=8)
        self.render_text(f"CARREGANDO OPERAÇÃO  {int(progress * 100):02d}%", (640, 552), "small", (245, 233, 191), center=True)
        status = "SISTEMAS PRONTOS — ABRINDO MENU" if self.assets_ready else self.loading_status.upper()
        self.render_text(status[:64], (640, 604), "tiny", (181, 208, 188), center=True)
        self.render_text(
            f"{self.loading_completed}/{self.loading_total} recursos preparados",
            (640, 618), "tiny", (153, 176, 160), center=True,
        )

    def draw_title(self):
        self.backdrop(80)
        self.panel(pygame.Rect(42, 30, 630, 143), (15, 27, 30, 226), (214, 174, 84), 17)
        self.draw_logo(357, 58, subtitle=False)
        self.render_text("DEFENDA A LINHA. SOBREVIVA À HORDA.", (357, 130), "small", (220, 204, 143), center=True)
        self.panel(pygame.Rect(43, 337, 385, 345), (16, 29, 31, 231), (103, 138, 112), 15)
        self.render_text("MENU PRINCIPAL", (70, 354), "med", (238, 216, 142))
        self.render_text("Escolha uma operação ou consulte o arquivo tático.", (70, 385), "tiny", (182, 207, 190))
        self.button(self.title_button_rect(0), "JOGAR", (77, 145, 78), font="small")
        self.button(self.title_button_rect(1), "COMO JOGAR", (151, 109, 54), font="small")
        self.button(self.title_button_rect(2), "INFORMAÇÕES: SOLDADOS", (69, 119, 132), font="tiny")
        self.button(self.title_button_rect(3), "INFORMAÇÕES: ZUMBIS", (132, 74, 70), font="tiny")
        self.button(self.title_button_rect(4), "SAIR", (109, 61, 55), font="small")
        self.panel(pygame.Rect(842, 538, 374, 126), (16, 29, 31, 229), (90, 126, 104), 13)
        self.render_text("CAMPANHA ATIVA", (870, 555), "small", (235, 213, 142))
        self.render_text(f"{self.progress}/{len(MISSIONS)} regiões liberadas", (870, 588), "body", (237, 241, 220))
        self.render_text("Cidade  →  Deserto  →  Praia", (870, 621), "tiny", (167, 208, 183))

    def draw_about(self):
        self.backdrop(132)
        self.panel(pygame.Rect(170, 72, 940, 580), (26, 38, 37), (120, 139, 108), 16)
        self.render_text("COMO JOGAR", (640, 115), "large", (225, 205, 133), center=True)
        paragraphs = [
            "Antes de cada operação, escolha até 8 cartas do destacamento específico da Cidade, do Deserto ou da Praia.",
            "Cada região tem 15 ondas. Chefes chegam nas ondas 5, 10 e 15; derrubá-los rende Medalhas.",
            "Use a carta Instrutor Tático perto de um aliado para transformar Medalhas em promoções de campo.",
            "",
            "CONTROLES", "Clique numa carta e depois numa célula vazia para posicionar. Clique nos suprimentos para coletá-los.",
            "E alterna a ferramenta de recolhimento; botão direito ou ESC cancela a carta; ESPAÇO pausa a operação.",
            "O Engenheiro implanta uma torreta uma célula à frente; selecione-o e clique na torreta para recolhê-la.",
            "Cada região possui elenco, zumbis, roupas, chefes e habilidades ligados ao próprio ambiente.",
            "Na Praia, equipamentos navais entram apenas nas linhas de maré. Na Cidade, as posições seguem a avenida.",
        ]
        y = 174
        for line in paragraphs:
            style = "med" if line == "CONTROLES" else "body"
            col = (230, 196, 108) if line == "CONTROLES" else (230, 232, 211)
            self.render_text(line, (222, y), style, col); y += 41 if style == "med" else 30
        self.button(pygame.Rect(516, 570, 248, 48), "VOLTAR", (83, 132, 79))
        if pygame.mouse.get_pressed()[0] and pygame.Rect(516, 570, 248, 48).collidepoint(pygame.mouse.get_pos()):
            pass

    def render_wrapped_text(self, text: str, x: int, y: int, width: int, font="body", color=(238, 235, 216), line_gap=4) -> int:
        """Render a concise paragraph without spilling across a dossier panel."""
        words = text.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and self.fonts[font].size(candidate)[0] > width:
                self.render_text(line, (x, y), font, color)
                y += self.fonts[font].get_height() + line_gap
                line = word
            else:
                line = candidate
        if line:
            self.render_text(line, (x, y), font, color)
            y += self.fonts[font].get_height() + line_gap
        return y

    def unit_dossier(self, key: str) -> tuple[str, str, str, str, str]:
        info = UNIT_DATA[key]
        styles = {
            "rifle": ("ATIRADOR", "Fogo direto contra alvos que entraram no alcance.", "Mantenha distância e cubra a linha."),
            "shotgun": ("BRECHA", "Disparo de dispersão para alvos próximos.", "Proteja entradas estreitas e a primeira fileira."),
            "splash": ("EXPLOSIVOS", "Projétil de impacto que acerta uma área.", "Guarde para grupos compactos."),
            "mortar": ("ARTILHARIA", "Bomba de arco com dano em área.", "Use atrás da linha de frente."),
            "flame": ("CONTROLE", "Chamas contínuas no curto alcance.", "Posicione quando a horda já estiver perto."),
            "engineer": ("ENGENHARIA", "Constrói e recupera uma torreta de campo.", "Abra espaço à frente para a torreta."),
            "trainer": ("COMANDO", "Promove aliados usando Medalhas de chefe.", "Proteja-o até o momento de promover."),
            "vanguard": ("CONTENÇÃO", "Dano mínimo, blindagem e muita resistência.", "Segure a linha enquanto atiradores trabalham."),
            "radio": ("SUPORTE", "Não ataca: converte tempo em suprimentos.", "Equilibre economia e defesa antes da horda crescer."),
            "drone": ("VIGILÂNCIA", "Drone ataca alvos prioritários à distância.", "Use para alcançar ameaças em linhas pressionadas."),
            "mine": ("ARMADILHA", "Explode ao contato com um inimigo.", "Coloque na rota de uma horda previsível."),
            "medical": ("ATENDIMENTO", "Ferramenta de cura aplicada em um aliado ferido.", "Salve defensores caros antes de reposicionar."),
            "turret": ("CONSTRUÇÃO", "Torreta automática liberada pelo Engenheiro.", "Ela não é uma carta comprável separada."),
        }
        category, attack, tactic = styles.get(info["kind"], ("ESPECIALISTA", "Ação tática de campo.", "Use conforme a pressão da linha."))
        if info.get("tool"):
            stats = f"Custo: {info['cost']} SUP • Cura: 180 HP"
        elif info["damage"] <= 0:
            stats = f"Custo: {info['cost']} SUP • Vida: {info['hp']}"
        else:
            stats = f"Custo: {info['cost']} SUP • Dano: {info['damage']} • Ação a cada {info['rate']:.2f}s"
        if "range" in info:
            stats += f" • Alcance: {info['range']:.0f}px"
        if info.get("max_total"):
            stats += f" • Limite: {info['max_total']}"
        return category, attack, info.get("ability", "Sem habilidade registrada."), tactic, stats

    def zombie_dossier(self, key: str) -> tuple[str, str, str, str, str]:
        data = ZOMBIE_DATA[key]
        family = {
            "caminhante": "COMUM", "corredor": "RÁPIDO", "rastejante": "RASTEJANTE",
            "bruto": "PESO-PESADO", "blindado": "BLINDADO", "porta_escudo": "BLOQUEADOR",
            "cuspidor": "TÓXICO", "divisor": "TÓXICO", "gritador": "SUPORTE",
            "pulador": "SALTADOR", "necromante": "ARCANO", "sandstalker": "ESCAVADOR",
            "feral": "FERAL", "nadador": "AQUÁTICO", "tide_brute": "AQUÁTICO",
            "conehead": "BLINDADO", "bandeireiro": "SUPORTE", "escavadeira": "ESCAVADOR",
            "doutor_zumbi": "CURANDEIRO", "general_morto": "COMANDANTE",
            "mutante_titan": "COLOSSO", "toxico": "TÓXICO",
        }.get(key, "AMEAÇA")
        attack = "Ataque corpo a corpo ao alcançar uma defesa."
        if data.get("ranged"):
            attack = "Projétil corrosivo contra uma defesa dentro do alcance."
        if data.get("boss"):
            attack = "Ataque pesado de chefe ao alcançar a linha de contenção."
        powers: list[str] = []
        if data.get("armor"): powers.append(f"armadura reduz {int(data['armor'] * 100)}% do dano")
        if data.get("jump"): powers.append("salta a defesa da frente")
        if data.get("dig"): powers.append("usa rota subterrânea")
        if data.get("healer"): powers.append("cura aliados próximos")
        if data.get("howl"): powers.append("acelera a horda")
        if data.get("split"): powers.append("divide a ameaça ao cair")
        if data.get("flag"): powers.append("reúne os aliados")
        if data.get("aquatic"): powers.append("opera nas linhas de água")
        if data.get("boss"): powers.append("executa um poder de chefe")
        power = "; ".join(powers).capitalize() if powers else "Avanço direto em direção à defesa."
        counter = "Concentre fogo antes que alcance a primeira defesa."
        if data.get("armor"): counter = "Use dano concentrado ou explosivos contra a proteção."
        elif data.get("ranged"): counter = "Não deixe que ele permaneça em alcance de ataque."
        elif data.get("jump") or data.get("dig"): counter = "Mantenha uma segunda camada de defesa na retaguarda."
        elif data.get("healer") or data.get("howl"): counter = "Elimine-o cedo para não fortalecer a horda."
        stats = f"Vida-base: {data['hp']} • Velocidade: {data['speed']} • Dano: {data['damage']}"
        return family, attack, power, counter, stats

    def draw_dossier(self, kind: str):
        is_units = kind == "units"
        title = "INFORMAÇÕES DOS SOLDADOS" if is_units else "INFORMAÇÕES DOS ZUMBIS"
        subtitle = "Arquivo tático: ataques, poderes e uso em combate." if is_units else "Arquivo de ameaça: ataques, poderes e resposta tática."
        accent = (91, 173, 183) if is_units else (192, 92, 77)
        self.backdrop(158)
        self.panel(pygame.Rect(34, 27, 1200, 94), (21, 34, 36, 238), accent, 14)
        self.render_text(title, (62, 44), "large", (239, 219, 151))
        self.render_text(subtitle, (64, 92), "small", (193, 214, 197))
        self.panel(pygame.Rect(34, 139, 536, 480), (21, 34, 36, 240), (101, 133, 113), 13)
        self.render_text("SELECIONE UMA FICHA", (58, 151), "small", (226, 213, 161))
        self.render_text("Clique em um retrato para ver os detalhes.", (58, 177), "tiny", (169, 194, 178))
        for index, key in enumerate(self.dossier_page_keys()):
            rect = self.dossier_item_rect(index)
            selected = key == self.dossier_key
            self.panel(rect, (35, 50, 51), accent if selected else (91, 112, 99), 8)
            image = self.unit_image(key) if is_units else self.zombie_image(key)
            portrait = self.fit_image(image, (52, 62))
            self.screen.blit(portrait, portrait.get_rect(center=(rect.x + 36, rect.centery + 2)))
            label = UNIT_DATA[key]["label"] if is_units else ZOMBIE_DATA[key]["label"]
            self.render_text(label.upper()[:24], (rect.x + 71, rect.y + 17), "tiny", (241, 238, 217))
            family = self.unit_dossier(key)[0] if is_units else self.zombie_dossier(key)[0]
            self.render_text(family, (rect.x + 71, rect.y + 47), "tiny", accent)

        self.panel(pygame.Rect(589, 139, 645, 480), (22, 35, 37, 242), accent, 13)
        key = self.dossier_key or (self.dossier_page_keys()[0] if self.dossier_page_keys() else None)
        if key:
            image = self.unit_image(key) if is_units else self.zombie_image(key)
            category, attack, power, tactic, stats = self.unit_dossier(key) if is_units else self.zombie_dossier(key)
            label = UNIT_DATA[key]["label"] if is_units else ZOMBIE_DATA[key]["label"]
            portrait_box = pygame.Rect(614, 194, 202, 337)
            self.panel(portrait_box, (28, 43, 44), (83, 109, 96), 11)
            portrait = self.fit_image(image, (174, 240))
            self.screen.blit(portrait, portrait.get_rect(center=(portrait_box.centerx, portrait_box.centery + 12)))
            self.render_text(label.upper(), (844, 167), "med", (245, 226, 166))
            self.render_text(category, (844, 201), "tiny", accent)
            y = 237
            for heading, body in (("ATAQUE", attack), ("PODER", power), ("TÁTICA", tactic), ("DADOS", stats)):
                self.render_text(heading, (844, y), "tiny", accent)
                y = self.render_wrapped_text(body, 844, y + 18, 353, "small", (227, 233, 215), 3) + 12

        page_text = f"PÁGINA {self.dossier_page + 1}/{self.dossier_page_count()}"
        self.button(self.dossier_back_rect(), "VOLTAR", (99, 108, 82), font="small")
        self.button(self.dossier_previous_rect(), "< ANTERIOR", (82, 105, 95), self.dossier_page > 0, "tiny")
        self.button(self.dossier_next_rect(), "PRÓXIMA >", (82, 105, 95), self.dossier_page < self.dossier_page_count() - 1, "tiny")
        self.render_text(page_text, (635, 660), "small", (225, 214, 169), center=True)

    def draw_campaign(self):
        self.backdrop(128)
        self.panel(pygame.Rect(49, 31, 1182, 91), (27, 40, 39, 238), (120, 139, 108), 13)
        self.render_text("MAPA DA CAMPANHA", (79, 47), "large", (232, 211, 139))
        self.render_text("As regiões são desbloqueadas em sequência. Operações liberadas também podem ser repetidas.", (81, 94), "small", (199, 213, 194))
        self.render_text(f"PROGRESSO: {self.progress}/{len(MISSIONS)}", (1066, 70), "med", (171, 207, 108), center=True)
        for i, mission in enumerate(MISSIONS):
            rect = self.campaign_rect(i)
            unlocked = i + 1 <= self.progress
            fill = (35, 55, 52) if unlocked else (30, 34, 35)
            self.panel(rect, fill, (177, 164, 107) if unlocked else (67, 74, 71), 14)
            tile = self.assets["scenes"].get(mission["code"]) or self.assets["terrain"][mission["code"]]
            tile = pygame.transform.smoothscale(tile, (rect.width - 28, 114))
            self.screen.blit(tile, (rect.x + 14, rect.y + 16))
            layer = pygame.Surface((rect.width - 28, 114), pygame.SRCALPHA); layer.fill((0, 0, 0, 68 if unlocked else 150)); self.screen.blit(layer, (rect.x + 14, rect.y + 16))
            self.render_text(str(i + 1), (rect.x + 30, rect.y + 36), "large", (235, 215, 142))
            self.render_text(mission["name"].upper(), (rect.centerx, rect.y + 151), "med", (238, 230, 203), center=True)
            self.render_text(mission["title"], (rect.centerx, rect.y + 178), "small", (170, 209, 144) if unlocked else (119, 126, 119), center=True)
            words = mission["desc"].split()
            line, y = "", rect.y + 210
            for word in words:
                if len(line + word) > 30:
                    self.render_text(line, (rect.x + 18, y), "tiny", (196, 205, 191) if unlocked else (101, 108, 104)); y += 17; line = ""
                line += word + " "
            self.render_text(line, (rect.x + 18, y), "tiny", (196, 205, 191) if unlocked else (101, 108, 104))
            self.button(pygame.Rect(rect.x + 36, rect.bottom - 58, rect.width - 72, 35), "PREPARAR" if unlocked else "BLOQUEADA", (79, 135, 70) if unlocked else (58, 62, 60), unlocked, "small")
        self.button(pygame.Rect(72, 620, 230, 42), "VOLTAR", (100, 107, 81), font="small")
        self.button(pygame.Rect(972, 620, 235, 42), "REINICIAR PROGRESSO", (141, 72, 56), font="small")

    def draw_selection(self):
        mission = MISSIONS[self.stage]
        self.backdrop(150)
        self.panel(pygame.Rect(42, 22, 1196, 105), (25, 39, 39, 240), (130, 148, 111), 13)
        self.render_text("SELEÇÃO DO DESTACAMENTO", (70, 38), "large", (231, 208, 132))
        self.render_text(f"{mission['title']} • {mission['name'].upper()}", (72, 86), "small", (168, 207, 143))
        self.render_text(f"ESQUADRÃO: {len(self.selection)}/8", (1090, 51), "med", (241, 231, 195), center=True)
        self.render_text("15 ONDAS • CHEFES: 5 / 10 / 15", (1010, 85), "small", (231, 199, 105), center=True)
        self.render_text(ENVIRONMENT_STYLE[mission["code"]]["uniform"], (642, 91), "tiny", (190, 202, 171), center=True)
        for i, key in enumerate(self.available_units()):
            info = UNIT_DATA[key]
            rect = self.selection_rect(i); chosen = key in self.selection
            card_color = info["color"] if chosen else tuple(max(15, c // 2) for c in info["color"])
            self.panel(rect, (39, 48, 45), (237, 207, 114) if chosen else card_color, 8)
            thumb = self.fit_image(self.unit_image(key), (78, 92))
            self.screen.blit(thumb, thumb.get_rect(center=(rect.x + 46, rect.centery)))
            label = self.unit_label(key).upper()
            self.render_text(label[:22], (rect.x + 93, rect.y + 15), "tiny", (243, 236, 207))
            type_label = f"SUPORTE • N{info.get('tier', 2)}" if info["kind"] == "radio" else "FERRAMENTA" if info.get("tool") else ("COSTA / ÁGUA" if info.get("aquatic") else mission["name"].upper())
            self.render_text(type_label, (rect.x + 93, rect.y + 35), "tiny", (112, 204, 222) if info.get("aquatic") else (226, 106, 95) if info.get("tool") else (160, 188, 135))
            self.render_text(f"{info['cost']} SUP", (rect.x + 93, rect.y + 55), "small", (235, 189, 68))
            if chosen:
                self.render_text("✓ SELECIONADA", (rect.x + 93, rect.y + 80), "tiny", (207, 237, 142))
            else:
                ability = info.get("ability", f"DMG {info['damage']}")
                self.render_text(ability[:19], (rect.x + 93, rect.y + 80), "tiny", (177, 191, 174))
        self.button(pygame.Rect(98, 630, 200, 50), "VOLTAR", (102, 104, 75))
        self.panel(pygame.Rect(375, 630, 430, 50), (38, 49, 43), (136, 151, 104), 8)
        self.render_text("MEDALHAS PROMOVEM UNIDADES EM CAMPO", (590, 655), "small", (221, 212, 157), center=True)
        self.button(pygame.Rect(908, 630, 270, 50), "INICIAR OPERAÇÃO", (79, 141, 71))

    def draw_game(self):
        self.draw_game_background()
        self.draw_board()
        self.draw_game_hud()
        self.draw_defenders()
        self.draw_projectiles()
        self.draw_zombies()
        self.draw_effects()
        self.draw_pickups()
        self.draw_particles()
        if self.selected_card or self.remove_mode: self.draw_cursor_hint()
        if self.banner > 0 and not self.end_state:
            self.panel(pygame.Rect(455, 130, 370, 36), (58, 34, 31), (230, 173, 77), 8)
            self.render_text(f"ONDA {self.wave}/{self.total_waves}", (640, 148), "med", (255, 225, 134), center=True)
        if self.paused and not self.end_state:
            self.draw_pause()
        if self.end_state: self.draw_end_overlay()

    def draw_game_background(self):
        mission = MISSIONS[self.stage]
        code = mission["code"]
        palette = {"city": (44, 43, 39), "desert": (122, 78, 36), "beach": (25, 91, 108)}[code]
        scene = self.assets["scenes"].get(code)
        if scene:
            self.screen.blit(scene, (0, 0))
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill((*palette, 14))
            self.screen.blit(tint, (0, 0))
        else:
            self.screen.fill(palette)
        atmosphere = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(22):
            x = int((i * 173 + self.time * (18 if code != "city" else 10)) % (WIDTH + 80)) - 40
            y = 155 + (i * 71) % 550
            if code == "desert":
                pygame.draw.circle(atmosphere, (240, 189, 101, 62), (x, y), 2 + i % 2)
            elif code == "beach":
                pygame.draw.arc(atmosphere, (174, 229, 236, 105), (x, y, 48, 12), 0, math.pi, 1)
            else:
                pygame.draw.circle(atmosphere, (216, 195, 156, 38), (x, y), 1 + i % 2)
        self.screen.blit(atmosphere, (0, 0))

    def draw_board(self):
        mission = MISSIONS[self.stage]
        field = pygame.Rect(BOARD_X, BOARD_Y, BOARD_W, BOARD_H)
        # The scenery itself is the battlefield: a road, dirt track or beach.
        # No framed board is painted over it; the grid remains input-only.
        if mission["code"] != "city":
            self.screen.blit(self.ground_layers[mission["code"]], field)

        if mission["code"] == "beach":
            # Fine moving ripples keep the tidal lanes alive without bringing
            # back blue tiles or a separate water rectangle.
            ripples = pygame.Surface((BOARD_W, CELL_H * 3), pygame.SRCALPHA)
            for i in range(20):
                x = int((i * 91 + self.time * 44) % (BOARD_W + 110)) - 55
                y = 5 + (i * 31) % (CELL_H * 3 - 12)
                width = 28 + (i * 17) % 68
                pygame.draw.arc(ripples, (190, 236, 238, 105), (x, y, width, 10), .12, math.pi - .12, 1)
            self.screen.blit(ripples, (BOARD_X, BOARD_Y + CELL_H))

        # The City containment posts follow the expanding avenue edge.  This
        # replaces the old vertical rail that made the foreground feel
        # detached from the perspective of the street.
        mine_points = [(self.row_bounds(r)[0] - 43, self.cell_rect(r, COLS // 2).centery + 5) for r in range(ROWS)]
        if mission["code"] == "city":
            road_edge = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.lines(road_edge, (15, 19, 20, 145), False, mine_points, 14)
            pygame.draw.lines(road_edge, (218, 184, 104, 150), False, mine_points, 2)
            self.screen.blit(road_edge, (0, 0))
        else:
            rail = pygame.Surface((82, BOARD_H - 16), pygame.SRCALPHA)
            rail_color = {"desert": (103, 68, 37, 130), "beach": (43, 86, 82, 118)}[mission["code"]]
            rail.fill(rail_color)
            pygame.draw.line(rail, (219, 186, 102, 150), (41, 8), (41, rail.get_height() - 8), 2)
            self.screen.blit(rail, (BOARD_X - 103, BOARD_Y + 8))
        for r in range(ROWS):
            mine_x, cy = mine_points[r]
            if self.row_mines[r]:
                glow = pygame.Surface((82, 52), pygame.SRCALPHA)
                alpha = int(44 + 30 * (1 + math.sin(self.time * 4.3 + r)) / 2)
                pygame.draw.ellipse(glow, (244, 164, 58, alpha), (14, 11, 56, 28))
                self.screen.blit(glow, (mine_x - 41, cy - 12))
                mine = self.assets["props"].get("mina_contencao")
                if mine:
                    self.screen.blit(mine, mine.get_rect(center=(mine_x, cy + 5)))
                else:
                    pygame.draw.circle(self.screen, (79, 92, 49), (mine_x, cy + 4), 17)
                    pygame.draw.circle(self.screen, (241, 163, 55), (mine_x + 8, cy - 3), 4)
            else:
                pygame.draw.ellipse(self.screen, (27, 29, 23), (mine_x - 28, cy - 5, 56, 22))
                pygame.draw.ellipse(self.screen, (76, 65, 45), (mine_x - 21, cy - 1, 42, 13))
                pygame.draw.circle(self.screen, (118, 81, 51), (mine_x - 12, cy + 4), 3)
                pygame.draw.circle(self.screen, (93, 95, 70), (mine_x + 9, cy + 8), 2)
        if self.selected_card:
            mouse_cell = self.board_cell(pygame.mouse.get_pos())
            if mouse_cell:
                row, col = mouse_cell
                rect = self.cell_rect(row, col)
                info = UNIT_DATA[self.selected_card]
                water = row in mission["water_rows"]
                valid = not self.defender_at(row, col) and (not info.get("aquatic") or water) and (info.get("aquatic") or not water)
                color = (132, 223, 128, 78) if valid else (228, 106, 87, 88)
                halo = pygame.Surface(rect.size, pygame.SRCALPHA)
                ellipse_rect = pygame.Rect(10, 22, max(1, rect.width - 20), CELL_H - 34)
                pygame.draw.ellipse(halo, color, ellipse_rect)
                pygame.draw.ellipse(halo, (240, 238, 183, 150) if valid else (239, 147, 119, 160), ellipse_rect, 2)
                self.screen.blit(halo, rect)

    def draw_game_hud(self):
        mission = MISSIONS[self.stage]
        self.panel(pygame.Rect(18, 16, 1244, 48), (23, 34, 33), (123, 139, 108), 10)
        self.render_text("SOLDADOS VS ZUMBIS", (33, 27), "med", (231, 211, 133))
        self.render_text(mission["title"].upper(), (34, 49), "tiny", (165, 204, 145))
        self.render_text(f"ONDA {self.wave}/{self.total_waves}", (602, 40), "med", (240, 223, 178), center=True)
        self.render_text(f"ZUMBIS: {len(self.zombies) + len(self.queue)}", (788, 30), "small", (224, 117, 96))
        self.render_text(f"BAIXAS: {self.kills}", (788, 50), "tiny", (181, 191, 176))
        self.render_text(f"MEDALHAS: {self.medals}", (902, 50), "tiny", (239, 205, 103))
        self.render_text("E: RECOLHER  •  ESPAÇO: PAUSAR  •  BOTÃO DIREITO: CANCELAR", (1045, 40), "tiny", (179, 193, 178), center=True)
        self.panel(pygame.Rect(23, 73, 176, 48), (44, 56, 43), (184, 157, 77), 8)
        self.render_text("SUP", (35, 81), "tiny", (226, 207, 137))
        self.render_text(str(self.supplies), (35, 97), "med", (245, 196, 65))
        self.render_text("MINAS", (112, 81), "tiny", (226, 207, 137))
        mines_color = (182, 221, 128) if any(self.row_mines) else (230, 109, 88)
        self.render_text(f"{sum(self.row_mines)}/{ROWS}", (112, 99), "med", mines_color)
        self.button(pygame.Rect(23, 124, 172, 31), "RECOLHER: " + ("LIGADO" if self.remove_mode else "DESLIGADO"), (130, 75, 56) if self.remove_mode else (78, 98, 77), font="tiny")
        self.button(pygame.Rect(24, 158, 171, 31), "RETOMAR" if self.paused else "PAUSAR", (91, 98, 74), font="tiny")
        for i, key in enumerate(self.selection):
            info = UNIT_DATA[key]; rect = self.card_rect(i)
            selected = key == self.selected_card
            cooling = self.card_cooldowns.get(key, 0)
            self.panel(rect, (42, 51, 48), (235, 200, 90) if selected else info["color"], 7)
            img = self.fit_image(self.unit_image(key), (50, 57)); self.screen.blit(img, img.get_rect(center=(rect.x + 28, rect.y + 48)))
            label = self.unit_label(key).upper()
            if len(label) > 15: label = label[:14] + "."
            self.render_text(label, (rect.x+55, rect.y+11), "tiny", (242, 238, 215))
            self.render_text(f"{info['cost']} SUP", (rect.x+55, rect.y+29), "tiny", (242, 195, 68))
            tag = f"SUP N{info.get('tier', 2)}" if info["kind"] == "radio" else "ÁGUA" if info.get("aquatic") else "CURA" if info.get("tool") else self.mission()["name"].upper()
            self.render_text(tag, (rect.x+55, rect.y+47), "tiny", (117, 205, 219) if tag == "ÁGUA" else (222, 103, 93) if tag == "CURA" else (160, 194, 140))
            if cooling > 0:
                cooldown_window = info.get("cooldown", 2.6)
                h = int(59 * min(1, cooling / cooldown_window)); shade = pygame.Surface((52, h), pygame.SRCALPHA); shade.fill((8, 15, 15, 165)); self.screen.blit(shade, (rect.x+2, rect.y+17))
                self.render_text(f"{cooling:.1f}", (rect.x+28, rect.y+48), "tiny", (240, 235, 214), center=True)

    def draw_defenders(self):
        for d in self.defenders:
            rect = self.cell_rect(d.row, d.col)
            bob = int(math.sin(self.time*3 + d.col) * 2)
            image = self.unit_image(d.key)
            recoil = int(5 * min(1, d.attack / .16))
            image_rect = image.get_rect(midbottom=(rect.centerx + 3 - recoil, rect.bottom - 6 + bob))
            self.screen.blit(image, image_rect)
            bar_w = min(76, max(52, rect.width - 28))
            self.draw_health(rect.centerx - bar_w // 2, rect.bottom - 13, bar_w, d.hp, self.defender_max_hp(d.key, d.rank), (91, 206, 101))
            if d.rank > 1:
                stars = "★" * d.rank
                self.render_text(stars, (rect.centerx, rect.bottom - 28), "tiny", (242, 206, 91), center=True)
            if d.poison > 0:
                pygame.draw.circle(self.screen, (130, 211, 83), (image_rect.right - 8, image_rect.y + 14), 4)
            if d.stun > 0:
                pygame.draw.circle(self.screen, (239, 205, 88), (image_rect.left + 8, image_rect.y + 14), 4)

    def draw_zombies(self):
        for z in self.zombies:
            data = ZOMBIE_DATA[z.key]
            img = self.zombie_image(z.key).copy()
            if z.flash > 0:
                flash = pygame.Surface(img.get_size(), pygame.SRCALPHA); flash.fill((255, 238, 208, 85)); img.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            # The pose includes more than a bob: every archetype changes its
            # horizontal stride, lean, vertical movement, ground effect and
            # attack lunge.  It makes a static PNG read like a living threat.
            phase = z.walk_phase
            motion = data.get("motion", "shamble")
            stride = math.sin(phase * 1.35)
            bob, lean, scale, sway = 0.0, 0.0, 1.0, 0.0
            if motion == "sprint":
                bob, lean, sway = abs(math.sin(phase * 1.7)) * 5.8, stride * 4.2, stride * 4.6
            elif motion == "crawl":
                bob, lean, scale, sway = abs(math.sin(phase * 1.8)) * 1.8, stride * 2.2, .98, stride * 3.2
            elif motion == "swim":
                bob, lean, scale, sway = math.sin(phase * 1.2) * 5.5, stride * 2.1, 1.02 + math.sin(phase * 1.2) * .025, stride * 2.6
            elif motion == "stomp":
                bob, lean, sway = abs(math.sin(phase * .75)) * 3.4, stride * 1.25, stride * 1.3
            elif motion == "leap":
                bob, lean, sway = abs(math.sin(phase * 1.35)) * 10.5, stride * 4.4, stride * 5.8
            else:
                bob, lean, sway = math.sin(phase * 1.15) * 2.8, stride * 2.2, stride * 2.4
            if self.is_boss(z):
                scale *= 1.16
            lunge = 0.0
            if z.attack_pulse > 0:
                punch = min(1, z.attack_pulse / .38)
                lean -= 7.0 * punch
                scale += .045 * punch
                lunge = 11.0 * punch
            if abs(lean) > .05 or abs(scale - 1) > .005:
                img = pygame.transform.rotozoom(img, lean, scale)
            ground_y = self.row_ground_y(z.row)
            shadow_w = max(28, int(img.get_width() * (.48 + abs(stride) * .12)))
            shadow_h = 9 if motion != "swim" else 7
            shadow_alpha = 75 if motion == "swim" else 105
            shadow = pygame.Surface((shadow_w + 8, shadow_h + 6), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (6, 13, 14, shadow_alpha), (4, 2, shadow_w, shadow_h))
            self.screen.blit(shadow, (int(z.x - shadow_w / 2 - 4), int(ground_y - 3)))
            if motion == "swim":
                for wave in range(2):
                    width = 38 + wave * 14 + int(abs(stride) * 8)
                    pygame.draw.arc(self.screen, (184, 235, 234), (int(z.x - width / 2), int(ground_y - 2 + wave * 5), width, 10), .10, math.pi - .10, 1)
            elif motion in {"sprint", "crawl", "leap"} and abs(stride) > .58:
                dust_color = (208, 171, 108) if self.mission()["code"] == "desert" else (127, 143, 128)
                pygame.draw.ellipse(self.screen, dust_color, (int(z.x + 18), int(ground_y - 2), 12, 4))
            elif motion == "stomp" and abs(stride) > .88:
                pygame.draw.arc(self.screen, (184, 137, 82), (int(z.x - 27), int(ground_y - 6), 54, 16), .15, math.pi - .15, 1)
            image_rect = img.get_rect(midbottom=(int(z.x + sway - lunge), int(ground_y + bob)))
            self.screen.blit(img, image_rect)
            if z.attack_pulse > 0:
                claw = pygame.Surface((52, 44), pygame.SRCALPHA)
                pygame.draw.arc(claw, (231, 91, 70, 205), (5, 4, 37, 31), .25, 1.75, 3)
                pygame.draw.arc(claw, (246, 167, 93, 145), (12, 11, 31, 26), .25, 1.75, 2)
                self.screen.blit(claw, (image_rect.left - 30, image_rect.centery - 23))
            if self.mission()["code"] == "desert" and z.key == "toxico":
                pygame.draw.circle(self.screen, (149, 225, 81), (image_rect.centerx + 6, image_rect.bottom - 26), 4 + int(abs(stride) * 2), 1)
            if data.get("howl"):
                pygame.draw.arc(self.screen, (205, 170, 226), (image_rect.left - 13, image_rect.y + 13, 27, 25), -1.1, 1.1, 1)
            maxhp = self.zombie_max_hp(z)
            bar_w = max(68, min(110, img.get_width() - 10))
            self.draw_health(int(image_rect.centerx - bar_w // 2), image_rect.y - 6, bar_w, z.hp, maxhp, (218, 82, 67))
            if self.is_boss(z):
                boss = self.boss_spec(z)
                label = self.boss_label(z).upper()
                self.render_text(label, (int(image_rect.centerx), image_rect.y-22), "tiny", (244, 185, 95), center=True)
                if boss:
                    remaining = max(0, z.boss_power_timer)
                    self.render_text(f"{boss['power'].upper()} {remaining:.1f}s", (int(image_rect.centerx), image_rect.y-10), "tiny", (232, 203, 139), center=True)
            if z.slow > 0:
                pygame.draw.circle(self.screen, (159, 231, 247), (int(image_rect.centerx), image_rect.bottom - 10), 7, 1)

    def draw_projectiles(self):
        for p in self.projectiles:
            sprite = self.assets["effects"].get(p.visual)
            if sprite:
                side = 44 if p.visual == "grenade" else 32 if p.visual == "bullet" else 50
                image = pygame.transform.smoothscale(sprite, (side, side))
                if p.visual == "grenade": image = pygame.transform.rotate(image, p.angle)
                self.screen.blit(image, image.get_rect(center=(int(p.x), int(p.y))))
            else:
                pygame.draw.line(self.screen, tuple(max(0, c-40) for c in p.color), (int(p.x-13), int(p.y)), (int(p.x), int(p.y)), 3)
                pygame.draw.circle(self.screen, p.color, (int(p.x), int(p.y)), 5)

    def draw_pickups(self):
        for pick in self.pickups:
            bob = int(math.sin(self.time*4 + pick.x)*4)
            rect = pygame.Rect(int(pick.x-22), int(pick.y-18+bob), 44, 36)
            self.panel(rect, (123, 91, 39), (239, 203, 89), 7)
            pygame.draw.circle(self.screen, (245, 201, 69), (rect.x+13, rect.centery), 8)
            self.render_text(f"+{pick.amount}", (rect.x+24, rect.y+10), "tiny", (252, 241, 184))

    def draw_particles(self):
        for p in self.particles:
            alpha = max(0, min(255, int(p.life * 350)))
            surf = pygame.Surface((int(p.size*3+2), int(p.size*3+2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, alpha), (surf.get_width()//2, surf.get_height()//2), max(1, int(p.size)))
            self.screen.blit(surf, (p.x-surf.get_width()//2, p.y-surf.get_height()//2))

    def draw_effects(self):
        for effect in self.effects:
            sprite = self.assets["effects"].get(effect.key)
            if not sprite: continue
            progress = 1 - effect.life / effect.max_life
            expansion = 1 + progress * (.58 if effect.key in {"explosion", "water_splash", "heal"} else .16)
            side = max(12, int(96 * effect.scale * expansion))
            image = pygame.transform.smoothscale(sprite, (side, side))
            if effect.angle: image = pygame.transform.rotate(image, effect.angle)
            image.set_alpha(max(0, min(255, int(255 * min(1, effect.life / (effect.max_life * .35))))))
            self.screen.blit(image, image.get_rect(center=(int(effect.x), int(effect.y))))

    def draw_health(self, x, y, w, hp, max_hp, color):
        pygame.draw.rect(self.screen, (17, 23, 22), (x-1, y-1, w+2, 7), border_radius=3)
        pygame.draw.rect(self.screen, (70, 79, 69), (x, y, w, 5), border_radius=2)
        pygame.draw.rect(self.screen, color, (x, y, int(w*max(0,hp)/max_hp), 5), border_radius=2)

    def draw_cursor_hint(self):
        if self.remove_mode:
            label = "RECOLHER UNIDADE"
        elif self.selected_card == "engenheiro":
            label = "ENGENHEIRO: POSICIONAR OU RECOLHER TORRETA"
        else:
            label = f"POSICIONAR: {self.unit_label(self.selected_card)}"
        col = (223, 112, 92) if self.remove_mode else (174, 219, 137)
        self.panel(pygame.Rect(452, 656, 376, 33), (31, 39, 37), col, 7)
        self.render_text(label + "  •  clique em uma célula", (640, 672), "small", (243, 238, 214), center=True)

    def draw_pause(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((5, 10, 10, 125)); self.screen.blit(overlay, (0,0))
        self.panel(pygame.Rect(475, 292, 330, 108), (29, 42, 40), (215, 181, 94), 12)
        self.render_text("OPERAÇÃO PAUSADA", (640, 327), "large", (242, 223, 158), center=True)
        self.render_text("Pressione ESPAÇO ou o botão Pausar para continuar.", (640, 368), "small", (208, 218, 198), center=True)

    def draw_end_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((4, 10, 11, 180)); self.screen.blit(overlay, (0,0))
        self.panel(pygame.Rect(382, 214, 516, 355), (31, 43, 39), (220, 182, 93) if self.end_state == "victory" else (203, 83, 68), 15)
        if self.end_state == "victory":
            title = "OPERAÇÃO CONCLUÍDA"
            body = "A posição foi mantida. O caminho para a próxima região está aberto."
            if self.stage == len(MISSIONS) - 1: body = "A campanha foi concluída. A praia está segura — por enquanto."
            color = (222, 218, 133)
        else:
            title, body, color = "GAME OVER", self.defeat_reason or "Uma linha de contenção foi rompida.", (231, 108, 91)
        self.render_text(title, (640, 273), "large", color, center=True)
        if self.end_state == "defeat":
            self.render_text("BASE TOMADA", (640, 317), "med", (245, 187, 130), center=True)
            self.render_text(body, (640, 349), "small", (228, 231, 212), center=True)
            self.render_text(f"Minas de contenção restantes: {sum(self.row_mines)}/{ROWS}", (640, 382), "small", (198, 204, 180), center=True)
            self.render_text("Mantenha soldados na linha ou preserve a mina de retaguarda.", (640, 410), "tiny", (172, 192, 173), center=True)
        else:
            self.render_text(body, (640, 331), "body", (228, 231, 212), center=True)
            self.render_text("Escolha uma opção para continuar.", (640, 374), "small", (172, 192, 173), center=True)
        self.button(pygame.Rect(481, 518, 160, 49), "TENTAR NOVAMENTE", (91, 137, 73), font="tiny")
        self.button(pygame.Rect(655, 518, 160, 49), "MAPA", (115, 101, 67), font="small")

    def draw_toast(self):
        if self.toast_timer <= 0 or not self.toast: return
        surface = self.fonts["small"].render(self.toast, True, (248, 239, 201))
        rect = surface.get_rect(center=(WIDTH//2, HEIGHT-24))
        self.panel(rect.inflate(32, 16), (37, 47, 43), (131, 149, 108), 7)
        self.screen.blit(surface, rect)

    def run(self):
        while self.running:
            dt = min(.05, self.clock.tick(FPS) / 1000)
            for event in pygame.event.get(): self.event(event)
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
