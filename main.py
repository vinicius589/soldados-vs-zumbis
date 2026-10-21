"""Soldados vs Zumbis — Reconstrução v7.

Um tower defense original em Pygame. Esta versão usa somente as artes v7
carregadas durante a tela de abertura e implementa campanha, cartas, munição,
suporte externo, chefes, Núcleos de Ascensão e elencos temáticos por região.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pygame


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "v7"
SAVE_PATH = ROOT / "campanha_v7.json"
WIDTH, HEIGHT = 1280, 720
FPS = 60
VERSION = "7.4"
ROWS, COLS = 5, 9
BOARD = pygame.Rect(164, 288, 1090, 382)
CELL_W = BOARD.width / COLS
CELL_H = BOARD.height / ROWS
WHITE = (242, 244, 239)
INK = (15, 20, 25)
GOLD = (240, 187, 72)
RED = (218, 68, 57)
TEAL = (72, 198, 192)
GRAY = (148, 160, 166)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def enemy_wave_scale(wave: int) -> float:
    """Mantém as primeiras ondas acolhedoras e endurece a reta final.

    A versão anterior começava com vida cheia e liberava ameaças depressa;
    assim, o primeiro contato parecia mais duro que a metade da campanha.
    """
    return 0.72 + max(0, wave - 1) * 0.10


def enemy_damage_scale(wave: int) -> float:
    """Escala separada para que o fim não seja só uma esponja de vida."""
    return 0.78 + wave * 0.07


def boss_wave_scale(wave: int) -> float:
    """Chefes escalam com a campanha sem virar paredes de vida.

    Um chefe deve mudar a montagem da linha, não exigir uma composição
    perfeita ou prender o jogador numa sequência infinita de atordoamentos.
    Por isso sua vida cresce mais devagar que a de uma horda comum.
    """
    return 0.82 + max(0, wave - 1) * 0.045


def boss_damage_scale(wave: int) -> float:
    """Contém o dano físico dos chefes nas ondas altas."""
    return 0.70 + wave * 0.035


def terrain_y(region: str, row: int, x: float) -> float:
    """Posiciona os pés nas superfícies pintadas de cada cenário.

    Os três fundos atuais foram alinhados como campos táticos quase
    ortogonais, então as faixas permanecem horizontais. Isso evita inimigos
    caminhando sobre céu, construções, paredões ou horizonte.
    """
    y = BOARD.top + (row + 0.5) * CELL_H
    return min(HEIGHT - 26, y)


def cell_center(row: int, col: int, region: str = "city") -> tuple[float, float]:
    x = BOARD.left + (col + 0.5) * CELL_W
    return x, terrain_y(region, row, x)


def cell_rect(row: int, col: int) -> pygame.Rect:
    return pygame.Rect(
        int(BOARD.left + col * CELL_W),
        int(BOARD.top + row * CELL_H),
        int(CELL_W),
        int(CELL_H),
    )


def title_case(value: str) -> str:
    return value.replace("_", " ").title()


REGIONS = {
    "city": {
        "name": "Cidade Quarentenada",
        "short": "CIDADE",
        "tag": "Tóxico urbano",
        "bg": "city_grounded.png",
        "soldiers": "city_soldiers_atlas.png",
        "soldiers_l2": "city_soldiers_l2_atlas_v74.png",
        "zombies": "city_zombies_atlas.png",
        "accent": (90, 207, 166),
        "unlock_after": None,
        "description": "Asfalto verdadeiro, prédios em ruína e uma névoa ácida que alimenta os infectados.",
        "bosses": ("bruto_demolidor", "comandante_mortos", "cuspidor_alfa"),
    },
    "desert": {
        "name": "Deserto das Ruínas",
        "short": "DESERTO",
        "tag": "Magia e escavação",
        "bg": "desert.png",
        "soldiers": "desert_soldiers_atlas.png",
        "soldiers_l2": "desert_soldiers_l2_atlas_v74.png",
        "zombies": "desert_zombies_atlas.png",
        "accent": (235, 179, 76),
        "unlock_after": "city",
        "description": "Uma estrada de terra leva às pirâmides; escavadores e magia antiga quebram a formação.",
        "bosses": ("mutante_ruinas", "necromante", "colosso_mutante"),
    },
    "beach": {
        "name": "Praia de Maré Morta",
        "short": "PRAIA",
        "tag": "Maré e costa",
        "bg": "beach_banded_v72.png",
        "soldiers": "beach_soldiers_atlas.png",
        "soldiers_l2": "beach_soldiers_l2_atlas_v74.png",
        "zombies": "beach_zombies_atlas.png",
        "accent": (78, 177, 232),
        "unlock_after": "desert",
        "description": "Duas faixas de areia, um canal central e mais duas faixas de areia formam uma defesa costeira legível.",
        "bosses": ("tide_brute", "cacador_abissal", "leviata"),
    },
}


# Cada carta possui Nível 1 ou Nível 2. O terceiro nível é temporário e só
# existe quando um Núcleo de Ascensão, recebido ao derrotar um chefe, é usado.
DEFENSES = {
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
        "ability": "M16: quatro blocos de alcance e fogo sustentado; depende de munição externa.",
    },
    "escopeteiro": {
        "base": "Espingarda de Mão",
        "role": "shotgun",
        "level": 1,
        "cost": 55,
        "hp": 122,
        "damage": 38,
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
        "damage": 14,
        "range": 3,
        "cooldown": 0.35,
        "ammo": 14,
        "sprite": 9,
        "ability": "Cone de fogo até três blocos; aplica queima contínua em quem entra no alcance.",
    },
    "lanca_chamas_bolso": {
        "base": "Lança-Chamas de Mão",
        "role": "flame",
        "level": 1,
        "cost": 78,
        "hp": 108,
        "damage": 10,
        "range": 1,
        "cooldown": 0.62,
        "ammo": 8,
        "sprite": 9,
        "ability": "Jato curto e lento de um bloco. Barato para segurar a primeira aproximação, mas precisa de recarga.",
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
    "mecanico": {
        "base": "Mecânico",
        "role": "reload",
        "level": 1,
        "cost": 65,
        "hp": 102,
        "damage": 0,
        "range": 1,
        "cooldown": 4.20,
        "ammo": 0,
        "sprite": 6,
        "ability": "Entrega munição às tropas próximas. Não atira e não gera créditos.",
    },
    "engenheiro": {
        "base": "Engenheiro",
        "role": "reload",
        "level": 2,
        "cost": 118,
        "hp": 122,
        "damage": 12,
        "range": 2,
        "cooldown": 2.90,
        "ammo": 0,
        "sprite": 6,
        "ability": "Recarrega uma área de dois blocos e solta um drone de ataque leve.",
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
    "medico": {
        "base": "Ajudante Médico",
        "role": "medic",
        "level": 1,
        "cost": 65,
        "hp": 94,
        "damage": 0,
        "range": 2,
        "cooldown": 4.30,
        "ammo": 0,
        "sprite": 8,
        "ability": "Remove corrosão, veneno e atordoamento, mas não restaura vida.",
    },
    "medico_experiente": {
        "base": "Médico de Campo",
        "role": "medic",
        "level": 2,
        "cost": 115,
        "hp": 112,
        "damage": 0,
        "range": 2,
        "cooldown": 3.35,
        "ammo": 0,
        "sprite": 8,
        "ability": "Cura vida dos feridos. O Núcleo a transforma em médica experiente, que também limpa debuffs.",
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
        "ability": "Carta aquática selecionável em qualquer fase; só pode ser posicionada nas faixas de água da Praia.",
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
        "ability": "Torpedos de grande alcance. Carta aquática: fica indisponível em solo seco.",
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
        "ability": "Depois de 90 s no campo, promove uma defesa N1 próxima para sua versão N2. Promove uma por ciclo e não cria N3.",
    },
}


# Promoção permanente de campo. As cartas N1 e N2 continuam livres na seleção;
# o Sargento só economiza uma segunda colocação quando sobrevive ao ciclo inteiro.
PROMOTIONS = {
    "recruta": "soldado",
    "escopeteiro": "escopeteiro_regular",
    "sniper": "sniper_regular",
    "bombardeiro": "granadeiro",
    "morteiro_basico": "morteiro",
    "lanca_chamas_bolso": "lanca_chamas",
    "mecanico": "engenheiro",
    "radio": "torre_radio",
    "medico": "medico_experiente",
    "barreira": "barreira_reativa",
    "mina": "mina_segura",
}


REGION_ROSTERS = {
    "city": (
        ("recruta", "Patrulheiro Urbano"),
        ("soldado", "Fuzileiro de Asfalto"),
        ("escopeteiro_regular", "Escopeteiro de Brecha"),
        ("sniper_regular", "Vigia de Telhado"),
        ("bombardeiro", "Granadeiro de Quarentena"),
        ("engenheiro", "Engenheiro de Rua"),
        ("radio", "Operador de Rádio"),
        ("medico", "Socorrista de Quarentena"),
        ("lanca_chamas", "Purificador Hazmat"),
        ("barreira_reativa", "Vanguarda Reativa"),
        ("mina_segura", "Mina de Sarjeta"),
        ("lancha", "Lancha Patrulha"),
        ("submarino", "Submarino de Resgate"),
        ("escopeteiro", "Espingarda de Mão"),
        ("sniper", "Vigia Recruta"),
        ("mecanico", "Mecânico de Rua"),
        ("lanca_chamas_bolso", "Lança-Chamas de Mão"),
        ("morteiro_basico", "Morteiro de Uma Bomba"),
        ("granadeiro", "Lançador de Quarentena"),
        ("barreira", "Barreira de Rua"),
        ("mina", "Mina Instável"),
        ("instrutor", "Sargento de Promoção Urbano"),
    ),
    "desert": (
        ("recruta", "Batedor do Oásis"),
        ("soldado", "Rifleiro das Dunas"),
        ("escopeteiro_regular", "Escopeteiro de Caravana"),
        ("sniper_regular", "Atirador das Dunas"),
        ("morteiro", "Morteiro de Ruínas"),
        ("granadeiro", "Granadeiro de Escavação"),
        ("engenheiro", "Engenheiro de Campo"),
        ("torre_radio", "Torre de Rádio Solar"),
        ("medico_experiente", "Médica de Caravana"),
        ("lanca_chamas", "Lança-Chamas do Oásis"),
        ("barreira_reativa", "Caminhão de Contenção"),
        ("mina_segura", "Mina Solar"),
        ("lancha", "Lancha Patrulha"),
        ("submarino", "Submarino de Resgate"),
        ("escopeteiro", "Espingarda de Caravana"),
        ("sniper", "Vigia das Dunas"),
        ("bombardeiro", "Bombardeiro do Oásis"),
        ("morteiro_basico", "Morteiro de Uma Bomba"),
        ("mecanico", "Mecânico de Caravana"),
        ("radio", "Operador de Rádio de Campo"),
        ("barreira", "Barreira de Caravana"),
        ("instrutor", "Sargento de Promoção das Dunas"),
    ),
    "beach": (
        ("recruta", "Guarda-Costa Recruta"),
        ("soldado", "Fuzileiro Anfíbio"),
        ("escopeteiro_regular", "Escopeteiro de Resgate"),
        ("sniper_regular", "Sniper Costeiro"),
        ("bombardeiro", "Arpoador Explosivo"),
        ("engenheiro", "Engenheiro de Píer"),
        ("torre_radio", "Torre de Sinal Marítimo"),
        ("medico_experiente", "Médica de Maré"),
        ("lanca_chamas", "Lança-Chamas Náutico"),
        ("barreira_reativa", "Boia de Contenção"),
        ("bomba_agua", "Bomba de Água"),
        ("lancha", "Lancha Patrulha"),
        ("submarino", "Submarino Costeiro"),
        ("escopeteiro", "Espingarda de Resgate"),
        ("sniper", "Vigia Costeiro"),
        ("granadeiro", "Granadeiro de Arpão"),
        ("mecanico", "Mecânico de Píer"),
        ("radio", "Operador de Rádio Costeiro"),
        ("medico", "Ajudante de Maré"),
        ("barreira", "Boia de Contenção Básica"),
        ("mina", "Mina de Areia"),
        ("instrutor", "Sargento de Promoção da Guarda-Costa"),
    ),
}


ENEMIES = {
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
        "hp": 215,
        "speed": 11,
        "damage": 15,
        "attack": 1.0,
        "sprite": 2,
        "ability": "Cone e colete reflexivo absorvem fogo leve. Força foco ou explosão.",
        "armor": 0.18,
    },
    "policial": {
        "name": "Policial Infectado",
        "hp": 265,
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
        "hp": 390,
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
        "hp": 330,
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
        "hp": 385,
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
        "ability": "Salta minas, bombas, veículos e a primeira tropa da frente.",
        "tags": ("jump",),
    },
    "bruto": {
        "name": "Bruto de Demolição",
        "hp": 610,
        "speed": 7,
        "damage": 48,
        "attack": 0.9,
        "sprite": 10,
        "ability": "Sub-chefe pesado; seus impactos deixam a linha vulnerável.",
        "tags": ("stomp",),
    },
    "digger": {
        "name": "Escavador",
        "hp": 220,
        "speed": 13,
        "damage": 42,
        "attack": 0.88,
        "sprite": 2,
        "ability": "Enterra-se e reaparece perto de uma tropa para um golpe surpresa de picareta.",
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
        "hp": 330,
        "speed": 9,
        "damage": 30,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Agarra uma tropa, corta seu ataque e atordoa até dois blocos à frente.",
        "tags": ("parasite",),
    },
    "mutante": {
        "name": "Mutante de Ruínas",
        "hp": 520,
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
        "hp": 285,
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
        "hp": 365,
        "speed": 10,
        "damage": 33,
        "attack": 0.92,
        "sprite": 3,
        "ability": "Armadura de mergulho espessa; pode atingir embarcações com força.",
        "armor": 0.30,
    },
    "cacador": {
        "name": "Caçador da Costa",
        "hp": 218,
        "speed": 15,
        "damage": 32,
        "attack": 0.85,
        "sprite": 4,
        "ability": "Persegue a defesa mais próxima com investida de arpão.",
        "tags": ("jump",),
    },
    "cowboy": {
        "name": "Cowboy da Maré",
        "hp": 250,
        "speed": 12,
        "damage": 18,
        "attack": 1.0,
        "sprite": 5,
        "ability": "Dispara de longe na costa e coloca pressão em médicos e rádio.",
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
        "hp": 205,
        "speed": 18,
        "damage": 25,
        "attack": 0.92,
        "sprite": 8,
        "ability": "Movimenta-se bem nas faixas de água e passa por minas terrestres.",
    },
}


BOSSES = {
    "bruto_demolidor": {
        "name": "BRUTO DEMOLIDOR",
        "hp": 1450,
        "speed": 6,
        "damage": 38,
        "attack": 1.05,
        "sprite": 10,
        "ability": "Entrada: paralisa militares por 3 s. Depois, o Martelo fecha só a própria faixa por 1,2 s a cada 18 s.",
        "type": "bruto_demolidor",
    },
    "comandante_mortos": {
        "name": "COMANDANTE DOS MORTOS",
        "hp": 1700,
        "speed": 9,
        "damage": 31,
        "attack": 0.88,
        "sprite": 11,
        "ability": "Entrada: dá fúria breve à escolta. Depois, dispara rajadas duplas leves e reacelera somente aliados próximos.",
        "type": "comandante",
    },
    "cuspidor_alfa": {
        "name": "CUSPIDADOR ALFA",
        "hp": 2200,
        "speed": 11,
        "damage": 34,
        "attack": 0.95,
        "sprite": 11,
        "ability": "Entrada: névoa ácida global de 1,2 s. Depois, cospe em um alvo na própria faixa, com corrosão curta.",
        "type": "alfa",
    },
    "mutante_ruinas": {
        "name": "MUTANTE DAS RUÍNAS",
        "hp": 1550,
        "speed": 6,
        "damage": 40,
        "attack": 0.98,
        "sprite": 6,
        "ability": "Entrada: abalo leve nas faixas vizinhas. Depois, golpeia somente tropas próximas por 1 s de atordoamento.",
        "type": "mutante",
    },
    "necromante": {
        "name": "NECROMANTE",
        "hp": 1850,
        "speed": 7,
        "damage": 28,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: invoca uma múmia. Depois, invoca uma por ciclo e cura pouco os aliados próximos.",
        "type": "necromante",
    },
    "colosso_mutante": {
        "name": "COLOSSO MUTANTE",
        "hp": 2600,
        "speed": 4,
        "damage": 48,
        "attack": 1.05,
        "sprite": 11,
        "ability": "Entrada: tremor global de 1,2 s. Depois, arremessa uma rocha leve contra uma faixa-alvo.",
        "type": "colosso",
    },
    "tide_brute": {
        "name": "BRUTO DA MARÉ",
        "hp": 1500,
        "speed": 6,
        "damage": 42,
        "attack": 1.0,
        "sprite": 9,
        "ability": "Entrada: uma onda leve abala a faixa de água. Depois, golpeia boias e embarcações apenas perto da maré.",
        "type": "tide",
    },
    "cacador_abissal": {
        "name": "CAÇADOR ABISSAL",
        "hp": 1950,
        "speed": 11,
        "damage": 32,
        "attack": 0.95,
        "sprite": 10,
        "ability": "Entrada: avança uma distância curta no canal. Depois, mergulha pouco e ataca uma embarcação próxima.",
        "type": "hunter",
    },
    "leviata": {
        "name": "LEVIATÃ",
        "hp": 2850,
        "speed": 5,
        "damage": 52,
        "attack": 1.0,
        "sprite": 11,
        "ability": "Entrada: uma maré moderada atinge o canal. Depois, lança um jato concentrado numa embarcação da própria faixa.",
        "type": "leviathan",
    },
}


REGION_ENEMIES = {
    "city": ("caminhante", "corredor", "rastejante", "conehead", "policial", "militar", "escudo", "cuspidor", "divisor", "gritador", "saltador", "bruto"),
    "desert": ("caminhante", "rastejante", "conehead", "digger", "ladrao", "curandeiro", "parasita", "mutante", "necromante_minion", "escudo", "cuspidor"),
    "beach": ("boia", "surfista", "salva_vidas", "mergulhador", "cacador", "cowboy", "sal_cuspidor", "mar_gritador", "nadador", "saltador"),
}


def make_save() -> dict:
    # As regiões são escolhas de estilo e desafio, não uma trava de conteúdo.
    return {"unlocked": list(REGIONS), "completed": [], "best_wave": {}}


def load_save() -> dict:
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "unlocked" not in data:
            raise ValueError
        data.setdefault("completed", [])
        data.setdefault("best_wave", {})
        # Atualiza saves antigos sem apagar os melhores resultados já gravados.
        data["unlocked"] = list(REGIONS)
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return make_save()


def save_campaign(data: dict) -> None:
    try:
        SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


class FontBook:
    def __init__(self) -> None:
        self.title = pygame.font.SysFont("arial", 45, bold=True)
        self.h1 = pygame.font.SysFont("arial", 28, bold=True)
        self.h2 = pygame.font.SysFont("arial", 20, bold=True)
        self.body = pygame.font.SysFont("arial", 16)
        self.small = pygame.font.SysFont("arial", 13)
        self.tiny = pygame.font.SysFont("arial", 11)


class Assets:
    """Carrega uma única fonte por quadro para manter a abertura leve."""

    def __init__(self) -> None:
        self.images: dict[str, pygame.Surface] = {}
        self.unit_sprites: dict[str, list[pygame.Surface]] = {}
        self.unit_l2_sprites: dict[str, list[pygame.Surface]] = {}
        self.zombie_sprites: dict[str, list[pygame.Surface]] = {}
        self.scale_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self.jobs: list[tuple[str, Path, str]] = []
        for region, info in REGIONS.items():
            self.jobs.extend(
                [
                    (f"{region}_bg", ASSET_DIR / info["bg"], "image"),
                    (f"{region}_units", ASSET_DIR / info["soldiers"], "units"),
                    (f"{region}_units_l2", ASSET_DIR / info["soldiers_l2"], "units_l2"),
                    (f"{region}_zombies", ASSET_DIR / info["zombies"], "zombies"),
                ]
            )
        self.jobs.insert(0, ("menu", ASSET_DIR / "menu.png", "image"))
        # Cada cenário usa sua própria contenção de última linha. Todas são
        # carregadas antes do menu, sem travar quando uma faixa é invadida.
        self.jobs[1:1] = [
            ("lane_bomb_cart", ASSET_DIR / "lane_bomb_cart_v72.png", "sprite"),
            ("desert_lane_bomb_cart", ASSET_DIR / "desert_lane_bomb_cart_v73.png", "sprite"),
            ("beach_land_bomb_cart", ASSET_DIR / "beach_land_bomb_cart_v73.png", "sprite"),
            ("beach_water_bomb", ASSET_DIR / "beach_water_bomb_v73.png", "sprite"),
        ]
        self.loaded = 0
        self.error: str | None = None

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def complete(self) -> bool:
        return self.loaded >= self.total

    def load_next(self) -> None:
        if self.complete:
            return
        key, path, kind = self.jobs[self.loaded]
        try:
            source = pygame.image.load(str(path)).convert_alpha()
            if kind == "image":
                if key == "beach_bg":
                    self.images[key] = self.fit_beach_background(source)
                else:
                    self.images[key] = pygame.transform.smoothscale(source, (WIDTH, HEIGHT))
            elif kind == "sprite":
                self.images[key] = source
            else:
                sprites = self.slice_atlas(source)
                if kind == "units":
                    self.unit_sprites[key.split("_")[0]] = sprites
                elif kind == "units_l2":
                    self.unit_l2_sprites[key.split("_")[0]] = sprites
                else:
                    self.zombie_sprites[key.split("_")[0]] = sprites
        except pygame.error as exc:
            self.error = f"Falha ao carregar {path.name}: {exc}"
            placeholder = pygame.Surface((128, 128), pygame.SRCALPHA)
            pygame.draw.circle(placeholder, RED, (64, 64), 42)
            if kind == "image":
                self.images[key] = pygame.transform.smoothscale(placeholder, (WIDTH, HEIGHT))
            elif kind == "sprite":
                self.images[key] = placeholder
            elif kind == "units":
                self.unit_sprites[key.split("_")[0]] = [placeholder] * 12
            elif kind == "units_l2":
                self.unit_l2_sprites[key.split("_")[0]] = [placeholder] * 12
            else:
                self.zombie_sprites[key.split("_")[0]] = [placeholder] * 12
        self.loaded += 1

    @staticmethod
    def fit_beach_background(source: pygame.Surface) -> pygame.Surface:
        """Alinha a arte da Praia às cinco faixas reais de combate.

        A ilustração contém areia/canal/areia. Este enquadramento preserva a
        textura pintada e coloca o canal no centro da terceira faixa (em vez
        de deixar a água ocupar as faixas superiores da tela).
        """
        source_width, source_height = source.get_size()
        source_water_top = int(source_height * 0.49)
        source_water_bottom = int(source_height * 0.62)
        target_water_top = int(HEIGHT * 0.61)
        target_water_bottom = int(HEIGHT * 0.72)
        canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        bands = (
            (0, source_water_top, 0, target_water_top),
            (source_water_top, source_water_bottom, target_water_top, target_water_bottom),
            (source_water_bottom, source_height, target_water_bottom, HEIGHT),
        )
        for source_top, source_bottom, target_top, target_bottom in bands:
            source_rect = pygame.Rect(0, source_top, source_width, max(1, source_bottom - source_top))
            target_size = (WIDTH, max(1, target_bottom - target_top))
            band = source.subsurface(source_rect)
            canvas.blit(pygame.transform.smoothscale(band, target_size), (0, target_top))
        return canvas

    @staticmethod
    def slice_atlas(source: pygame.Surface) -> list[pygame.Surface]:
        width, height = source.get_size()
        tiles: list[pygame.Surface] = []
        for row in range(3):
            for col in range(4):
                rect = pygame.Rect(col * width // 4, row * height // 3, width // 4, height // 3)
                tile = source.subsurface(rect).copy()
                if tile.get_flags() & pygame.SRCALPHA == 0:
                    tile.set_colorkey((0, 0, 0))
                tiles.append(tile)
        return tiles

    def base_unit(self, region: str, index: int) -> pygame.Surface:
        sprites = self.unit_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def unit(self, region: str, index: int, level: int = 1) -> pygame.Surface:
        """N1 usa o atlas base; N2 recebe silhueta e uniforme próprios."""
        if level >= 2:
            sprites = self.unit_l2_sprites.get(region, [])
            if sprites:
                return sprites[index % len(sprites)]
        return self.base_unit(region, index)

    def zombie(self, region: str, index: int) -> pygame.Surface:
        sprites = self.zombie_sprites.get(region, [])
        if not sprites:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        return sprites[index % len(sprites)]

    def scaled(self, sprite: pygame.Surface, width: float, height: float) -> pygame.Surface:
        """Evita redimensionar os mesmos retratos gigantes a cada quadro."""
        size = (max(1, int(width)), max(1, int(height)))
        key = (id(sprite), *size)
        cached = self.scale_cache.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(sprite, size)
            self.scale_cache[key] = cached
        return cached


@dataclass
class Defender:
    key: str
    display_name: str
    row: int
    col: int
    stats: dict
    sprite_index: int
    hp: float = field(init=False)
    ammo: int = field(init=False)
    attack_timer: float = 0.0
    utility_timer: float = 0.0
    stun: float = 0.0
    corrosion: float = 0.0
    ascended: float = 0.0
    drone_timer: float = 0.0
    turret_timer: float = 0.0
    pulse: float = 0.0
    region: str = "city"

    def __post_init__(self) -> None:
        self.hp = float(self.stats["hp"])
        self.ammo = int(self.stats["ammo"])
        if self.stats["role"] == "promoter":
            self.utility_timer = float(self.stats["cooldown"])

    @property
    def x(self) -> float:
        return cell_center(self.row, self.col, self.region)[0]

    @property
    def y(self) -> float:
        return cell_center(self.row, self.col, self.region)[1]

    @property
    def max_hp(self) -> float:
        return float(self.stats["hp"])

    @property
    def max_ammo(self) -> int:
        return int(self.stats["ammo"])

    def has_ammo(self) -> bool:
        return self.max_ammo == 0 or self.ammo > 0

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 38), int(self.y - 48), 76, 82)


@dataclass
class Enemy:
    key: str
    row: int
    data: dict
    region: str
    wave: int
    x: float = field(default_factory=lambda: BOARD.right + 100)
    hp: float = field(init=False)
    attack_timer: float = 0.0
    skill_timer: float = 1.8
    age: float = 0.0
    stun: float = 0.0
    burn: float = 0.0
    corrosion: float = 0.0
    jump_used: bool = False
    burrowed: bool = False
    stolen: float = 0.0
    revived: bool = False
    rage: float = 0.0
    boss_announced: bool = False
    step_timer: float = 0.0

    def __post_init__(self) -> None:
        scale = boss_wave_scale(self.wave) if self.key in BOSSES else enemy_wave_scale(self.wave)
        self.hp = float(self.data["hp"]) * scale

    @property
    def y(self) -> float:
        return terrain_y(self.region, self.row, self.x)

    @property
    def max_hp(self) -> float:
        scale = boss_wave_scale(self.wave) if self.is_boss else enemy_wave_scale(self.wave)
        return float(self.data["hp"]) * scale

    @property
    def is_boss(self) -> bool:
        return self.key in BOSSES

    @property
    def tags(self) -> tuple:
        return tuple(self.data.get("tags", ()))

    def hitbox(self) -> pygame.Rect:
        size = 96 if self.is_boss else 68
        return pygame.Rect(int(self.x - size / 2), int(self.y - size * 0.78), size, size)


@dataclass
class Projectile:
    x: float
    y: float
    target: Enemy | Defender | None
    target_x: float
    target_y: float
    damage: float
    kind: str
    owner: Defender | Enemy | None
    radius: float = 0.0
    friendly: bool = True
    travel: float = 0.22
    elapsed: float = 0.0
    effect: str = ""

    def __post_init__(self) -> None:
        # Protege o loop de animação contra chamadas antigas que passaram o
        # efeito como último argumento posicional (onde elapsed ficava string).
        if isinstance(self.elapsed, str):
            if not self.effect:
                self.effect = self.elapsed
            self.elapsed = 0.0
        self.elapsed = float(self.elapsed)
        self.travel = max(0.01, float(self.travel))


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    ttl: float
    size: float
    color: tuple[int, int, int]
    gravity: float = 0.0


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    ttl: float = 1.0


@dataclass
class SpawnOrder:
    wait: float
    key: str
    row: int
    boss: bool = False


@dataclass
class LaneBomb:
    """Carrinho-bomba de emergência, um por faixa de combate."""

    row: int
    x: float = field(default_factory=lambda: BOARD.left - 32)
    state: str = "armed"  # armed -> rolling -> spent
    kills: int = 0


class Battle:
    def __init__(self, app: "Game", region: str, selected: list[tuple[str, str]]) -> None:
        self.app = app
        self.region = region
        self.selected = selected
        self.defenders: list[Defender] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        # O suficiente para experimentar a primeira formação, mas sem tornar
        # a economia da campanha irrelevante.
        self.supplies = 110
        self.wave = 0
        self.wave_banner = 0.0
        self.intermission = 2.5
        self.orders: list[SpawnOrder] = []
        self.spawn_timer = 0.0
        self.started_wave = False
        self.finished = False
        self.lost = False
        self.victory = False
        self.message = "Posicione a equipe. A primeira horda começa leve."
        self.message_timer = 4.0
        self.selected_card = 0
        self.use_core = False
        self.remove_mode = False
        self.cores = 0
        self.boss_seen: set[int] = set()
        self.ambient_phase = 0.0
        self.shake = 0.0
        self.global_toxic = 0.0
        self.boss_warning = 0.0
        self.boss_banner_name = ""
        self.boss_banner_subtitle = ""
        self.boss_alert_pending = False
        self.paused = False
        self.dead_history: list[tuple[str, int, float]] = []
        # Cinco faixas: areia, areia, CANAL, areia, areia. Como esta versão
        # usa cinco linhas, o canal central ocupa só a terceira linha.
        self.water_rows = {2} if region == "beach" else set()
        self.lane_bombs = [LaneBomb(row) for row in range(ROWS)]
        self.card_cooldowns = [0.0 for _ in selected]

    def announce(self, message: str, seconds: float = 2.5, color: tuple[int, int, int] = WHITE) -> None:
        self.message = message
        self.message_timer = seconds
        # Alertas de interface são exibidos na aba superior. Assim eles não
        # atravessam as cartas nem reintroduzem uma faixa de texto na partida.

    def cell_is_water(self, row: int, col: int) -> bool:
        if self.region != "beach":
            return False
        # O canal da Praia é a única faixa aquática utilizável.
        return row in self.water_rows

    def ground_cell_rect(self, row: int, col: int) -> pygame.Rect:
        x, y = cell_center(row, col, self.region)
        return pygame.Rect(int(x - CELL_W / 2 + 7), int(y - CELL_H / 2 + 7), int(CELL_W - 14), int(CELL_H - 14))

    def board_cell_at(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """Traduz um clique no terreno para a faixa mais próxima desenhada."""
        if not BOARD.left <= pos[0] <= BOARD.right:
            return None
        col = int(clamp((pos[0] - BOARD.left) / CELL_W, 0, COLS - 1))
        row = min(range(ROWS), key=lambda candidate: abs(pos[1] - cell_center(candidate, col, self.region)[1]))
        if abs(pos[1] - cell_center(row, col, self.region)[1]) > CELL_H * 0.68:
            return None
        return row, col

    def card(self) -> tuple[str, str]:
        return self.selected[self.selected_card]

    def can_place(self, key: str, row: int, col: int) -> tuple[bool, str]:
        if not (0 <= row < ROWS and 0 <= col < COLS):
            return False, "Fora da área de combate."
        if any(d.row == row and d.col == col for d in self.defenders):
            return False, "Este ponto já está ocupado."
        data = DEFENSES[key]
        water = self.cell_is_water(row, col)
        if data.get("water_only") and not water:
            return False, "Unidade aquática: só pode ser instalada nas faixas de água da Praia."
        if water and not data.get("water_only") and key not in {"barreira", "barreira_reativa", "mina", "mina_segura"}:
            return False, "Nesta faixa há água. Posicione uma embarcação, uma mina marítima ou uma barreira."
        if self.supplies < data["cost"]:
            return False, "Suprimentos insuficientes."
        return True, ""

    def place(self, row: int, col: int) -> None:
        key, display = self.card()
        allowed, reason = self.can_place(key, row, col)
        if not allowed:
            self.announce(reason, 1.7, RED)
            return
        data = DEFENSES[key]
        self.supplies -= data["cost"]
        sprite_index = int(data["sprite"])
        if self.region == "beach":
            if key == "lancha":
                sprite_index = 5
            elif key == "submarino":
                sprite_index = 6
            elif key in {"bombardeiro", "granadeiro", "lanca_chamas", "lanca_chamas_bolso"}:
                sprite_index = 7
            elif key in {"engenheiro", "mecanico"}:
                sprite_index = 8
            elif key in {"radio", "torre_radio"}:
                sprite_index = 9
            elif key in {"medico", "medico_experiente"}:
                sprite_index = 10
            elif key in {"barreira", "barreira_reativa", "mina", "mina_segura", "bomba_agua"}:
                sprite_index = 11
        elif self.region == "desert":
            if key in {"morteiro", "morteiro_basico"}:
                sprite_index = 5
            elif key in {"bombardeiro", "granadeiro"}:
                sprite_index = 6
            elif key in {"engenheiro", "mecanico"}:
                sprite_index = 7
            elif key in {"radio", "torre_radio"}:
                sprite_index = 8
            elif key in {"medico", "medico_experiente"}:
                sprite_index = 9
            elif key in {"lanca_chamas", "lanca_chamas_bolso"}:
                sprite_index = 10
            elif key in {"barreira", "barreira_reativa", "mina", "mina_segura"}:
                sprite_index = 11
        else:
            if key in {"bombardeiro", "granadeiro", "morteiro", "morteiro_basico"}:
                sprite_index = 5
            elif key in {"engenheiro", "mecanico"}:
                sprite_index = 6
            elif key in {"radio", "torre_radio"}:
                sprite_index = 7
            elif key in {"medico", "medico_experiente"}:
                sprite_index = 8
            elif key in {"lanca_chamas", "lanca_chamas_bolso"}:
                sprite_index = 9
            elif key in {"barreira", "barreira_reativa", "mina", "mina_segura"}:
                sprite_index = 10 if key in {"barreira", "barreira_reativa"} else 11
        defender = Defender(key, display, row, col, data, sprite_index, region=self.region)
        self.defenders.append(defender)
        self.card_cooldowns[self.selected_card] = 0.55
        self.pulse(defender.x, defender.y, self.region_color(), 20)
        self.announce(f"{display} em posição.", 1.2, self.region_color())

    def remove_defender(self, row: int, col: int) -> None:
        """Retira uma defesa por escolha do jogador e devolve parte do custo."""
        defender = next((d for d in self.defenders if d.row == row and d.col == col), None)
        if defender is None:
            self.announce("Nenhuma tropa nesta faixa para remover.", 1.4, GRAY)
            return
        self.defenders.remove(defender)
        refund = max(1, math.ceil(float(defender.stats["cost"]) * 0.35))
        self.supplies += refund
        self.pulse(defender.x, defender.y, (188, 206, 214), 12)
        self.announce(f"{defender.display_name} recolhido: +{refund} SUP.", 1.8, TEAL)

    def trigger_lane_bomb(self, row: int) -> bool:
        cart = self.lane_bombs[row]
        if cart.state != "armed":
            return False
        cart.state = "rolling"
        cart.x = BOARD.left - 42
        self.shake = max(self.shake, 0.16)
        label, color = self.lane_bomb_info(row)
        self.announce(f"{label} — faixa {row + 1} ativada!", 1.8, color)
        self.pulse(cart.x + 24, cell_center(row, 0, self.region)[1], color, 16)
        return True

    def lane_bomb_info(self, row: int) -> tuple[str, tuple[int, int, int]]:
        """Retorna a contenção própria de cada terreno/faixa."""
        if self.region == "city":
            return "BOMBA URBANA", GOLD
        if self.region == "desert":
            return "CARGA DAS DUNAS", (235, 181, 88)
        if row in self.water_rows:
            return "BOIA-BOMBA", (95, 209, 236)
        return "CARGA COSTEIRA", (104, 201, 207)

    def lane_bomb_asset_key(self, row: int) -> str:
        if self.region == "city":
            return "lane_bomb_cart"
        if self.region == "desert":
            return "desert_lane_bomb_cart"
        return "beach_water_bomb" if row in self.water_rows else "beach_land_bomb_cart"

    def update_lane_bombs(self, dt: float) -> None:
        """Move o carrinho-bomba e limpa somente a faixa invadida uma vez."""
        for cart in self.lane_bombs:
            if cart.state != "rolling":
                continue
            cart.x += 720 * dt
            y = cell_center(cart.row, 0, self.region)[1]
            if random.random() < dt * 18:
                _, trail_color = self.lane_bomb_info(cart.row)
                gravity = 0 if cart.row in self.water_rows else 18
                self.particles.append(Particle(cart.x - 28, y + 12, random.uniform(-55, -20), random.uniform(-15, 15), 0.42, 2.6, trail_color, gravity))
            for enemy in self.enemies[:]:
                if enemy.row == cart.row and abs(enemy.x - cart.x) < 67:
                    self.take_enemy_damage(enemy, 99999, "explosion")
                    cart.kills += 1
            if cart.x > BOARD.right + 82:
                cart.state = "spent"
                _, explosion_color = self.lane_bomb_info(cart.row)
                self.explosion(BOARD.right - 18, y, explosion_color, 22)

    @staticmethod
    def menu_rect() -> pygame.Rect:
        return pygame.Rect(16, 126, 90, 34)

    @staticmethod
    def pause_rect() -> pygame.Rect:
        return pygame.Rect(112, 126, 92, 34)

    @staticmethod
    def remove_rect() -> pygame.Rect:
        return pygame.Rect(210, 126, 112, 34)

    @staticmethod
    def core_rect() -> pygame.Rect:
        return pygame.Rect(328, 126, 118, 34)

    @staticmethod
    def next_wave_rect() -> pygame.Rect:
        return pygame.Rect(452, 126, 144, 34)

    def apply_core(self, row: int, col: int) -> None:
        target = next((d for d in self.defenders if d.row == row and d.col == col), None)
        if target is None:
            self.announce("Escolha uma tropa já posicionada para usar o Núcleo.", 1.8, RED)
            return
        if target.ascended > 0:
            self.announce("Esta tropa já está ascensionada.", 1.6, GOLD)
            return
        if self.cores <= 0:
            self.use_core = False
            return
        self.cores -= 1
        self.use_core = False
        target.ascended = 18.0
        target.ammo = target.max_ammo
        target.stun = 0
        target.corrosion = 0
        self.announce(f"NÚCLEO DE ASCENSÃO: {target.display_name} no Nível 3!", 2.8, GOLD)
        self.pulse(target.x, target.y, GOLD, 38)

    def start_next_wave(self) -> None:
        if self.wave >= 15:
            return
        self.wave += 1
        self.started_wave = True
        self.wave_banner = 3.0
        self.orders = self.build_wave(self.wave)
        self.spawn_timer = 0.35
        self.intermission = 0.0
        if self.wave % 5 == 0:
            boss_key = REGIONS[self.region]["bosses"][self.wave // 5 - 1]
            self.boss_banner_name = BOSSES[boss_key]["name"]
            self.boss_banner_subtitle = "A ESCOLTA ABRE CAMINHO"
            self.announce(f"Onda {self.wave}: a escolta do chefe está a caminho.", 2.6, RED)
        else:
            self.announce(f"ONDA {self.wave}/15", 2.0, WHITE)

    def build_wave(self, wave: int) -> list[SpawnOrder]:
        pool = list(REGION_ENEMIES[self.region])
        # Começa apenas com o invasor-base e introduz os counters de forma
        # gradativa. No fim, quase todo o elenco da região pode aparecer.
        unlocked_count = min(len(pool), 1 + (wave - 1) // 2 + wave // 10)
        pool = pool[:unlocked_count]
        orders: list[SpawnOrder] = []
        count = 2 + wave + (wave * wave) // 11
        difficulty = wave / 15
        for index in range(count):
            if index < 3:
                key = pool[min(index, len(pool) - 1)]
            else:
                weighted = pool.copy()
                if difficulty > 0.35:
                    weighted.extend(pool[-min(3, len(pool)):])
                if difficulty > 0.70:
                    weighted.extend(pool[-min(5, len(pool)):])
                key = random.choice(weighted)
            wait = 0.92 - min(0.58, wave * 0.038) + random.random() * 0.22
            orders.append(SpawnOrder(wait, key, random.randrange(ROWS)))
        if wave % 5 == 0:
            boss_key = REGIONS[self.region]["bosses"][wave // 5 - 1]
            # A escolta cria pressão, mas não enterra o jogador sob uma segunda
            # horda no mesmo instante em que o chefe entra.
            for _ in range(2 + wave // 5):
                orders.insert(random.randrange(len(orders) + 1), SpawnOrder(0.32, random.choice(pool[-min(4, len(pool)):]), random.randrange(ROWS)))
            boss_row = random.choice(tuple(self.water_rows)) if self.region == "beach" else random.randrange(ROWS)
            orders.append(SpawnOrder(1.15, boss_key, boss_row, True))
        return orders

    def spawn_enemy(self, order: SpawnOrder) -> None:
        data = BOSSES.get(order.key) or ENEMIES[order.key]
        enemy = Enemy(order.key, order.row, data, self.region, self.wave)
        if order.boss:
            enemy.x = BOARD.right + 110
            enemy.boss_announced = True
            self.shake = 0.38
        self.enemies.append(enemy)
        if order.boss:
            self.boss_banner_name = str(data["name"])
            self.boss_banner_subtitle = "ENTRADA ESPECIAL ATIVADA"
            self.boss_entrance(enemy)

    def region_color(self) -> tuple[int, int, int]:
        return REGIONS[self.region]["accent"]

    def target_in_range(self, defender: Defender, min_distance: float = 0) -> Enemy | None:
        maximum = float(defender.stats["range"]) * CELL_W
        choices = [
            enemy
            for enemy in self.enemies
            if enemy.row == defender.row
            and enemy.x >= defender.x + min_distance
            and enemy.x - defender.x <= maximum
            and enemy.hp > 0
        ]
        return min(choices, key=lambda e: e.x) if choices else None

    def blocker_for(self, enemy: Enemy) -> Defender | None:
        choices = [
            defender
            for defender in self.defenders
            if defender.row == enemy.row and defender.hp > 0 and defender.x <= enemy.x + 38
        ]
        if not choices:
            return None
        nearest = max(choices, key=lambda d: d.x)
        if enemy.x - nearest.x < 55:
            return nearest
        return None

    def take_enemy_damage(self, enemy: Enemy, amount: float, effect: str = "", source: Defender | None = None) -> None:
        if enemy.hp <= 0:
            return
        armor = float(enemy.data.get("armor", 0))
        if "shield" in enemy.tags and effect not in {"flame", "explosion", "mortar"}:
            armor = max(armor, 0.52)
        if source and source.ascended > 0:
            amount *= 1.55
        enemy.hp -= amount * (1 - armor)
        if effect == "flame":
            enemy.burn = max(enemy.burn, 3.3)
        if effect == "acid":
            enemy.corrosion = max(enemy.corrosion, 2.5)
        self.texts.append(FloatingText(str(int(amount)), enemy.x, enemy.y - 52, GOLD if source and source.ascended else WHITE, 0.55))
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def damage_defender(self, defender: Defender, amount: float, effect: str = "") -> None:
        if defender.hp <= 0:
            return
        defender.hp -= amount
        if effect == "stun":
            defender.stun = max(defender.stun, 2.2)
        elif effect == "acid":
            defender.corrosion = max(defender.corrosion, 4.0)
        elif effect == "acid_brief":
            defender.corrosion = max(defender.corrosion, 1.8)
        self.texts.append(FloatingText(str(int(amount)), defender.x, defender.y - 48, RED, 0.6))
        if defender.hp <= 0:
            self.kill_defender(defender)

    def kill_defender(self, defender: Defender) -> None:
        if defender not in self.defenders:
            return
        self.defenders.remove(defender)
        self.pulse(defender.x, defender.y, RED, 25)
        if defender.stats["role"] == "barrier" and defender.stats["level"] >= 2:
            for enemy in self.enemies[:]:
                if enemy.row == defender.row and abs(enemy.x - defender.x) < CELL_W * 1.35:
                    self.take_enemy_damage(enemy, defender.stats["damage"], "explosion")
            self.explosion(defender.x, defender.y, RED, 28)
        self.announce(f"{defender.display_name} foi perdido.", 1.5, RED)

    def kill_enemy(self, enemy: Enemy) -> None:
        if enemy not in self.enemies:
            return
        self.enemies.remove(enemy)
        self.dead_history.append((enemy.key, enemy.row, enemy.x))
        if len(self.dead_history) > 12:
            self.dead_history.pop(0)
        color = (130, 230, 145) if not enemy.is_boss else GOLD
        self.explosion(enemy.x, enemy.y, color, 26 if enemy.is_boss else 12)
        if "explode_death" in enemy.tags:
            for defender in self.defenders[:]:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 1.15:
                    self.damage_defender(defender, 52 + self.wave * 2, "acid")
            self.explosion(enemy.x, enemy.y, (114, 212, 99), 25)
        if enemy.is_boss:
            self.cores = min(3, self.cores + 1)
            self.supplies += 60
            self.boss_seen.add(self.wave)
            self.announce("Chefe neutralizado: +1 Núcleo de Ascensão e +60 suprimentos.", 3.4, GOLD)
            self.pulse(WIDTH / 2, HEIGHT / 2, GOLD, 75)
        else:
            self.supplies += 1 if self.wave < 8 else 2

    def pulse(self, x: float, y: float, color: tuple[int, int, int], amount: int) -> None:
        for _ in range(amount):
            angle = random.random() * math.tau
            speed = random.uniform(35, 125)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, random.uniform(0.35, 0.9), random.uniform(2, 5), color, 42)
            )

    def explosion(self, x: float, y: float, color: tuple[int, int, int], amount: int) -> None:
        self.pulse(x, y, color, amount)
        self.shake = max(self.shake, 0.16)

    def fire_defender(self, defender: Defender, target: Enemy) -> None:
        role = defender.stats["role"]
        level = defender.stats["level"]
        ascending = defender.ascended > 0
        if role in {"reload", "radio", "medic", "promoter", "barrier", "mine"}:
            return
        if defender.max_ammo > 0:
            defender.ammo -= 1
        defender.attack_timer = float(defender.stats["cooldown"]) * (0.68 if ascending else 1.0)
        # Pequeno clarão e fumaça deixam a cadência das armas legível sem
        # substituir as artes dos soldados por uma animação pesada.
        for _ in range(4 if role in {"shotgun", "grenade", "mortar"} else 2):
            self.particles.append(
                Particle(
                    defender.x + 24,
                    defender.y - 28,
                    random.uniform(24, 70),
                    random.uniform(-18, 18),
                    0.16,
                    random.uniform(1.5, 3.2),
                    GOLD,
                )
            )
        if role == "sniper" and level == 1 and not ascending and random.random() < 0.28:
            self.texts.append(FloatingText("ERROU", target.x, target.y - 42, GRAY, 0.7))
            self.projectiles.append(Projectile(defender.x + 15, defender.y - 22, None, target.x, target.y - 18, 0, "tracer", defender, travel=0.22))
            return
        damage = float(defender.stats["damage"])
        kind = "bullet"
        radius = 0.0
        effect = ""
        if role == "rifle":
            kind = "rifle"
            if ascending:
                kind, radius = "fuzileiro", CELL_W * 0.72
                damage *= 1.25
        elif role == "shotgun":
            kind, radius = "shotgun", CELL_W * (0.45 if ascending else 0.25)
            distance = max(1, (target.x - defender.x) / CELL_W)
            damage *= 1.45 if distance < 1.2 else 0.9
            if ascending:
                damage *= 1.4
        elif role == "sniper":
            kind = "sniper"
            if ascending:
                damage *= 2.55
        elif role in {"grenade", "mortar"}:
            kind = "mortar" if role == "mortar" else "grenade"
            radius = CELL_W * (1.05 if ascending else 0.78)
            effect = "mortar"
            if ascending and role == "mortar":
                for offset in (-1, 1):
                    clone = self.closest_enemy_at(target.row + offset, target.x)
                    if clone:
                        self.projectiles.append(
                            Projectile(defender.x, defender.y - 24, clone, clone.x, clone.y - 15, damage * 0.72, kind, defender, radius, True, 0.45, effect=effect)
                        )
            if ascending and role == "grenade":
                kind, radius, damage = "bazooka", BOARD.width, damage * 1.45
        elif role == "flame":
            kind, radius, effect = "flame", CELL_W * 0.55, "flame"
            damage *= 0.62
        elif role == "boat":
            kind = "boat"
        elif role == "sub":
            kind, radius = "torpedo", CELL_W * 0.42
        self.projectiles.append(
            Projectile(defender.x + 16, defender.y - 22, target, target.x, target.y - 16, damage, kind, defender, radius, True, 0.24 if kind in {"rifle", "flame"} else 0.42, effect=effect)
        )

    def closest_enemy_at(self, row: int, x: float) -> Enemy | None:
        candidates = [enemy for enemy in self.enemies if enemy.row == row and enemy.hp > 0]
        return min(candidates, key=lambda e: abs(e.x - x)) if candidates else None

    def promote_defender(self, instructor: Defender) -> bool:
        """Converte uma tropa N1 real em sua carta N2 correspondente.

        O alcance considera também as faixas vizinhas para não punir a posição
        visual do Sargento, mas o alvo mais perto ainda é previsível para quem
        quer escolher qual carta vai subir primeiro.
        """
        radius = float(instructor.stats["range"]) * CELL_W
        candidates = [
            defender
            for defender in self.defenders
            if defender is not instructor
            and defender.key in PROMOTIONS
            and int(defender.stats["level"]) == 1
            and defender.ascended <= 0
            and abs(defender.x - instructor.x) <= radius
            and abs(defender.row - instructor.row) <= 1
        ]
        if not candidates:
            # Não reinicia o minuto inteiro se ainda não houver uma tropa N1
            # válida por perto: o jogador ganha uma pequena janela para criar
            # ou reposicionar a candidata.
            instructor.utility_timer = 8.0
            return False

        target = min(candidates, key=lambda defender: (abs(defender.x - instructor.x), abs(defender.row - instructor.row)))
        target_key = PROMOTIONS[target.key]
        upgraded = DEFENSES[target_key]
        old_hp_ratio = target.hp / max(1.0, target.max_hp)
        old_ammo_ratio = target.ammo / max(1, target.max_ammo) if target.max_ammo else 1.0
        target.key = target_key
        target.stats = upgraded
        target.sprite_index = int(upgraded["sprite"])
        target.hp = max(1.0, float(upgraded["hp"]) * max(0.55, old_hp_ratio))
        target.ammo = int(round(int(upgraded["ammo"]) * old_ammo_ratio)) if int(upgraded["ammo"]) else 0
        target.attack_timer = 0.0
        target.utility_timer = 0.0
        target.stun = 0.0
        target.corrosion = 0.0
        target.display_name = self.display_name_for(target_key)
        instructor.utility_timer = float(instructor.stats["cooldown"])
        self.announce(f"PROMOÇÃO CONCLUÍDA: {target.display_name} agora é N2!", 2.5, GOLD)
        self.pulse(target.x, target.y - 12, GOLD, 28)
        return True

    def display_name_for(self, key: str) -> str:
        """Mantém a nomenclatura regional quando uma carta muda de nível."""
        for roster_key, display in REGION_ROSTERS[self.region]:
            if roster_key == key:
                return display
        return str(DEFENSES[key]["base"])

    def utility_defender(self, defender: Defender, dt: float) -> None:
        role = defender.stats["role"]
        if role == "reload":
            if defender.utility_timer <= 0:
                radius = float(defender.stats["range"]) * CELL_W
                reloaded = 0
                for ally in self.defenders:
                    if ally is defender or ally.row != defender.row:
                        continue
                    if abs(ally.x - defender.x) <= radius + 1 and ally.max_ammo > 0:
                        amount = 4 if defender.stats["level"] == 1 else 7
                        if ally.ascended > 0:
                            amount += 2
                        previous = ally.ammo
                        ally.ammo = min(ally.max_ammo, ally.ammo + amount)
                        reloaded += ally.ammo - previous
                defender.utility_timer = float(defender.stats["cooldown"]) * (0.34 if defender.ascended else 1.0)
                if reloaded:
                    self.pulse(defender.x, defender.y - 18, TEAL, 7)
                    self.texts.append(FloatingText(f"+{reloaded} munição", defender.x, defender.y - 56, TEAL, 0.8))
            if defender.stats["level"] >= 2:
                defender.drone_timer -= dt
                target = self.target_in_range(defender)
                if defender.drone_timer <= 0 and target:
                    defender.drone_timer = 1.1 if not defender.ascended else 0.7
                    self.projectiles.append(Projectile(defender.x + 18, defender.y - 55, target, target.x, target.y - 24, 17 if not defender.ascended else 32, "drone", defender, 0, True, 0.25))
                if defender.ascended:
                    defender.turret_timer -= dt
                    turret_targets = [
                        enemy
                        for enemy in self.enemies
                        if enemy.row == defender.row
                        and enemy.x >= defender.x
                        and enemy.x - defender.x <= CELL_W * 4.2
                    ]
                    if defender.turret_timer <= 0 and turret_targets:
                        target = min(turret_targets, key=lambda enemy: enemy.x)
                        turret_x = min(BOARD.right - 18, defender.x + CELL_W * 0.7)
                        self.projectiles.append(
                            Projectile(turret_x, defender.y - 31, target, target.x, target.y - 20, 31, "turret", defender, 0, True, 0.16)
                        )
                        defender.turret_timer = 0.31
        elif role == "radio" and defender.utility_timer <= 0:
            gain = 14 if defender.stats["level"] == 1 else 28
            if defender.ascended:
                gain = 52
            self.supplies += gain
            defender.utility_timer = float(defender.stats["cooldown"]) * (0.48 if defender.ascended else 1.0)
            self.texts.append(FloatingText(f"+{gain} SUP", defender.x, defender.y - 55, GOLD, 1.0))
            self.pulse(defender.x, defender.y - 18, GOLD, 8)
        elif role == "medic" and defender.utility_timer <= 0:
            radius = float(defender.stats["range"]) * CELL_W
            healed = False
            for ally in self.defenders:
                if abs(ally.x - defender.x) <= radius and abs(ally.row - defender.row) <= 1:
                    if defender.stats["level"] >= 2 and ally.hp < ally.max_hp:
                        ally.hp = min(ally.max_hp, ally.hp + 26 + (16 if defender.ascended else 0))
                        healed = True
                    if defender.stats["level"] == 1 or defender.ascended:
                        if ally.stun > 0 or ally.corrosion > 0:
                            ally.stun = 0
                            ally.corrosion = 0
                            healed = True
            defender.utility_timer = float(defender.stats["cooldown"]) * (0.65 if defender.ascended else 1.0)
            if healed:
                self.pulse(defender.x, defender.y - 16, (104, 225, 164), 9)
        elif role == "promoter" and defender.utility_timer <= 0:
            self.promote_defender(defender)

    def update_defenders(self, dt: float) -> None:
        for defender in self.defenders[:]:
            defender.attack_timer -= dt
            defender.utility_timer -= dt
            defender.stun = max(0.0, defender.stun - dt)
            defender.corrosion = max(0.0, defender.corrosion - dt)
            defender.ascended = max(0.0, defender.ascended - dt)
            defender.pulse += dt
            if defender.corrosion > 0 and random.random() < dt * 1.6:
                self.damage_defender(defender, 1.6)
            if defender.stats["role"] == "mine":
                target = next((enemy for enemy in self.enemies if enemy.row == defender.row and abs(enemy.x - defender.x) < 49), None)
                if target:
                    is_safe = defender.stats["level"] >= 2
                    if is_safe or random.random() < 0.72:
                        if defender.ascended:
                            for enemy in self.enemies[:]:
                                if enemy.row == defender.row:
                                    self.take_enemy_damage(enemy, 9999, "explosion", defender)
                            self.announce("Mina ascensionada: linha inteira limpa!", 1.7, GOLD)
                        else:
                            radius = CELL_W * (0.82 if defender.key == "bomba_agua" else 0.35)
                            for enemy in self.enemies[:]:
                                if enemy.row == defender.row and abs(enemy.x - defender.x) < radius:
                                    self.take_enemy_damage(enemy, defender.stats["damage"], "explosion", defender)
                        self.explosion(defender.x, defender.y, GOLD, 18)
                    else:
                        self.announce("A mina falhou!", 1.2, RED)
                    self.defenders.remove(defender)
                continue
            if defender.stun > 0:
                continue
            self.utility_defender(defender, dt)
            role = defender.stats["role"]
            minimum = CELL_W * 1.05 if role == "mortar" else 0
            target = self.target_in_range(defender, minimum)
            if target and defender.attack_timer <= 0 and defender.has_ammo():
                self.fire_defender(defender, target)

    @staticmethod
    def is_military_defender(defender: Defender) -> bool:
        """Tropas humanas recebem os efeitos globais de entrada dos chefes.

        Minas e barreiras são equipamentos fixos; elas continuam como opção de
        contenção quando uma chegada especial fecha temporariamente os tiros.
        """
        return defender.stats["role"] not in {"barrier", "mine"}

    def boss_entrance(self, enemy: Enemy) -> None:
        """Executa uma única ação de entrada. Ela nunca é reutilizada no ciclo.

        Cada chefe ganha um impacto memorável ao aparecer, mas a ação recorrente
        que vem depois é menor, localizada e possui um intervalo legível.
        """
        boss_type = enemy.data.get("type", "")
        self.shake = max(self.shake, 0.42)
        if boss_type == "bruto_demolidor":
            for defender in self.defenders:
                if self.is_military_defender(defender):
                    defender.stun = max(defender.stun, 3.0)
            enemy.skill_timer = 18.0
            self.announce("BRUTO DEMOLIDOR: tropas militares paralisadas por 3 s!", 2.8, RED)
        elif boss_type == "comandante":
            for other in self.enemies:
                if other is not enemy and abs(other.x - enemy.x) < CELL_W * 4.2:
                    other.rage = max(other.rage, 2.4)
            enemy.skill_timer = 14.0
            self.announce("Comandante dos Mortos: a escolta recebeu fúria!", 2.4, RED)
        elif boss_type == "alfa":
            self.global_toxic = 1.2
            for defender in self.defenders:
                defender.corrosion = max(defender.corrosion, 1.0)
            enemy.skill_timer = 14.0
            self.announce("Cuspidor Alfa: névoa ácida global por um instante!", 2.4, (150, 232, 112))
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if abs(defender.row - enemy.row) <= 1 and abs(defender.x - enemy.x) < CELL_W * 2.25:
                    self.damage_defender(defender, 8)
                    defender.stun = max(defender.stun, 1.15)
            enemy.skill_timer = 14.0
            self.announce("Mutante das Ruínas: o abalo atingiu apenas a vanguarda próxima.", 2.2, RED)
        elif boss_type == "necromante":
            self.enemies.append(Enemy("necromante_minion", enemy.row, ENEMIES["necromante_minion"], self.region, self.wave, x=enemy.x + 48))
            enemy.skill_timer = 15.0
            self.announce("Necromante: uma múmia foi invocada na chegada.", 2.3, (197, 128, 238))
        elif boss_type == "colosso":
            for defender in self.defenders:
                if self.is_military_defender(defender):
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce("Colosso Mutante: tremor inicial interrompeu os tiros por 1,2 s.", 2.4, RED)
        elif boss_type == "tide":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, 8)
                    defender.stun = max(defender.stun, 0.9)
            enemy.skill_timer = 14.0
            self.announce("Bruto da Maré: a primeira onda abalou o canal.", 2.1, (95, 195, 239))
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 4.8, enemy.x - CELL_W * 0.7)
            enemy.skill_timer = 13.0
            self.announce("Caçador Abissal: mergulhou e surgiu mais perto no canal.", 2.1, (95, 195, 239))
        elif boss_type == "leviathan":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and defender.stats.get("water_only"):
                    self.damage_defender(defender, 14)
                    defender.stun = max(defender.stun, 1.2)
            enemy.skill_timer = 18.0
            self.announce("LEVIATÃ: uma onda de entrada atingiu a faixa de água.", 2.4, (95, 195, 239))
        else:
            enemy.skill_timer = 12.0

    def boss_skill(self, enemy: Enemy) -> None:
        """Habilidade recorrente, sempre mais justa que a entrada do chefe."""
        boss_type = enemy.data.get("type", "")
        cooldowns = {
            "bruto_demolidor": 18.0,
            "comandante": 14.0,
            "alfa": 14.0,
            "mutante": 14.0,
            "necromante": 15.0,
            "colosso": 18.0,
            "tide": 14.0,
            "hunter": 13.0,
            "leviathan": 18.0,
        }
        enemy.skill_timer = cooldowns.get(boss_type, 12.0)
        self.shake = max(self.shake, 0.24)

        if boss_type == "bruto_demolidor":
            # Regra central do primeiro chefe: sem stun global repetido. O
            # martelo fecha somente a faixa na qual o chefe está por 1,2 s.
            targets = [d for d in self.defenders if d.row == enemy.row and self.is_military_defender(d)]
            for defender in targets:
                defender.stun = max(defender.stun, 1.2)
                self.pulse(defender.x, defender.y - 22, RED, 7)
            self.announce(f"Martelo do Bruto: faixa {enemy.row + 1} interrompida por 1,2 s.", 2.0, RED)
        elif boss_type == "comandante":
            escorts = [
                other for other in self.enemies
                if other is not enemy and abs(other.row - enemy.row) <= 1 and abs(other.x - enemy.x) < CELL_W * 2.8
            ]
            for other in escorts:
                other.rage = max(other.rage, 2.2)
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.5]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                for vertical in (-11, 9):
                    self.projectiles.append(Projectile(enemy.x - 14, enemy.y + vertical - 24, victim, victim.x, victim.y - 24, 10 + self.wave, "enemy_bullet", enemy, 0, False, 0.32))
            self.announce("Comandante: escolta próxima acelerada e rajada dupla disparada.", 1.9, RED)
        elif boss_type == "alfa":
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0]
            for victim in sorted(targets, key=lambda defender: defender.x, reverse=True)[:1]:
                self.projectiles.append(Projectile(enemy.x - 12, enemy.y - 27, victim, victim.x, victim.y - 18, 10 + self.wave, "acid", enemy, 0, False, 0.45, effect="acid_brief"))
            self.announce(f"Cuspidor Alfa: saliva corrosiva na faixa {enemy.row + 1}.", 1.8, (150, 232, 112))
        elif boss_type == "mutante":
            for defender in self.defenders[:]:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 2.15:
                    self.damage_defender(defender, 12)
                    defender.stun = max(defender.stun, 1.0)
            self.announce(f"Mutante: punho de ruína na faixa {enemy.row + 1}.", 1.8, RED)
        elif boss_type == "necromante":
            self.enemies.append(Enemy("necromante_minion", enemy.row, ENEMIES["necromante_minion"], self.region, self.wave, x=enemy.x + 42))
            for other in self.enemies:
                if other is not enemy and abs(other.x - enemy.x) < CELL_W * 1.65:
                    other.hp = min(other.max_hp, other.hp + 28)
            self.announce("Necromante: novas múmias e cura localizada da escolta.", 2.0, (197, 128, 238))
        elif boss_type == "colosso":
            targets = [d for d in self.defenders if d.x < enemy.x and enemy.x - d.x < CELL_W * 4.0]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.projectiles.append(Projectile(enemy.x - 12, enemy.y - 34, victim, victim.x, victim.y - 24, 18, "mortar", enemy, 0, False, 0.52))
            self.announce("Colosso: rocha arremessada contra uma faixa-alvo.", 1.9, RED)
        elif boss_type == "tide":
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, 12)
                victim.stun = max(victim.stun, 0.8)
            self.announce("Bruto da Maré: golpe concentrado no canal.", 1.8, (95, 195, 239))
        elif boss_type == "hunter":
            enemy.x = max(BOARD.left + CELL_W * 3.4, enemy.x - CELL_W * 0.85)
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.damage_defender(victim, 10)
                victim.stun = max(victim.stun, 0.7)
            self.announce("Caçador Abissal: mergulho ofensivo no canal.", 1.8, (95, 195, 239))
        elif boss_type == "leviathan":
            targets = [d for d in self.defenders if d.row == enemy.row and d.stats.get("water_only") and d.x < enemy.x]
            if targets:
                victim = max(targets, key=lambda defender: defender.x)
                self.projectiles.append(Projectile(enemy.x - 22, enemy.y - 25, victim, victim.x, victim.y - 12, 24, "torpedo", enemy, 0, False, 0.42))
            self.announce("LEVIATÃ: jato de pressão concentrado na faixa de água.", 2.0, (95, 195, 239))

    def enemy_special(self, enemy: Enemy) -> None:
        if enemy.is_boss:
            self.boss_skill(enemy)
            return
        enemy.skill_timer = random.uniform(3.4, 5.8)
        if "gun" in enemy.tags:
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 4]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                self.projectiles.append(Projectile(enemy.x - 12, enemy.y - 25, victim, victim.x, victim.y - 20, 20 + self.wave * 1.3, "enemy_bullet", enemy, 0, False, 0.30))
        if "acid" in enemy.tags:
            targets = [d for d in self.defenders if d.row == enemy.row and d.x < enemy.x and enemy.x - d.x < CELL_W * 3.2]
            if targets:
                victim = max(targets, key=lambda d: d.x)
                self.projectiles.append(Projectile(enemy.x - 12, enemy.y - 22, victim, victim.x, victim.y - 18, 16 + self.wave, "acid", enemy, CELL_W * 0.34, False, 0.48, effect="acid"))
        if "scream" in enemy.tags:
            for other in self.enemies:
                if other.row == enemy.row and abs(other.x - enemy.x) < CELL_W * 2.6:
                    other.rage = max(other.rage, 3.5)
            if random.random() < 0.36:
                self.enemies.append(Enemy("caminhante" if self.region != "beach" else "boia", enemy.row, ENEMIES["caminhante" if self.region != "beach" else "boia"], self.region, self.wave, x=BOARD.right + 20))
            self.announce("Grito: a horda ganhou velocidade.", 1.2, RED)
        if "heal" in enemy.tags:
            nearby = [other for other in self.enemies if other is not enemy and abs(other.x - enemy.x) < CELL_W * 1.8]
            for other in nearby:
                other.hp = min(other.max_hp, other.hp + 42)
            if self.dead_history and not enemy.revived and random.random() < 0.4:
                key, row, x = self.dead_history[-1]
                if key in ENEMIES:
                    revived = Enemy(key, row, ENEMIES[key], self.region, self.wave, x=x + 42)
                    revived.hp = revived.max_hp * 0.40
                    self.enemies.append(revived)
                    enemy.revived = True
        if "parasite" in enemy.tags:
            for defender in self.defenders:
                if defender.row == enemy.row and defender.x < enemy.x and enemy.x - defender.x < CELL_W * 2.1:
                    defender.stun = max(defender.stun, 2.6)
            self.announce("Parasita: tiro das tropas foi desabilitado.", 1.4, RED)
        if "stomp" in enemy.tags:
            for defender in self.defenders:
                if defender.row == enemy.row and abs(defender.x - enemy.x) < CELL_W * 1.8:
                    self.damage_defender(defender, 24, "stun")
        if "steal" in enemy.tags:
            stolen = min(18, self.supplies)
            self.supplies -= stolen
            enemy.stolen += stolen
            self.announce("Ladrão de Suprimentos roubou carga — clique nele!", 2.0, GOLD)

    def update_enemies(self, dt: float) -> None:
        for enemy in self.enemies[:]:
            enemy.age += dt
            enemy.attack_timer -= dt
            enemy.skill_timer -= dt
            enemy.stun = max(0.0, enemy.stun - dt)
            enemy.burn = max(0.0, enemy.burn - dt)
            enemy.corrosion = max(0.0, enemy.corrosion - dt)
            enemy.rage = max(0.0, enemy.rage - dt)
            enemy.step_timer -= dt
            if enemy.burn > 0:
                self.take_enemy_damage(enemy, 5.2 * dt, "flame")
                if enemy not in self.enemies:
                    continue
            if enemy.corrosion > 0:
                self.take_enemy_damage(enemy, 2.0 * dt, "acid")
                if enemy not in self.enemies:
                    continue
            if enemy.skill_timer <= 0:
                self.enemy_special(enemy)
                if enemy not in self.enemies:
                    continue
            if enemy.stun > 0:
                continue
            speed = float(enemy.data["speed"]) * (1.55 if enemy.rage > 0 else 1.0)
            if "dash" in enemy.tags and enemy.age < 1.7:
                speed *= 1.95
            if "dig" in enemy.tags and not enemy.burrowed and enemy.age > 1.1:
                victims = [d for d in self.defenders if d.row == enemy.row]
                if victims:
                    victim = max(victims, key=lambda d: d.x)
                    enemy.x = victim.x + 48
                    self.damage_defender(victim, 46, "stun")
                    enemy.burrowed = True
                    self.explosion(enemy.x, enemy.y, (194, 160, 77), 16)
            blocker = self.blocker_for(enemy)
            if blocker:
                if "jump" in enemy.tags and not enemy.jump_used:
                    enemy.x = max(BOARD.left + 8, blocker.x - 60)
                    enemy.jump_used = True
                    self.announce("Saltador ultrapassou a linha de frente!", 1.4, RED)
                    continue
                if enemy.attack_timer <= 0:
                    scale = boss_damage_scale(self.wave) if enemy.is_boss else enemy_damage_scale(self.wave)
                    damage = float(enemy.data["damage"]) * scale
                    self.damage_defender(blocker, damage)
                    enemy.attack_timer = float(enemy.data["attack"])
                continue
            enemy.x -= speed * dt
            if enemy.step_timer <= 0:
                water_step = self.region == "beach" and enemy.row in self.water_rows
                step_color = (112, 221, 235) if water_step else ((208, 177, 105) if self.region == "desert" else (124, 136, 138))
                for _ in range(2 if water_step else 1):
                    self.particles.append(
                        Particle(
                            enemy.x + random.uniform(-14, 12),
                            enemy.y + 18,
                            random.uniform(-16, 16),
                            random.uniform(-18, -4),
                            0.30,
                            random.uniform(1.8, 3.3),
                            step_color,
                            22 if not water_step else 0,
                        )
                    )
                enemy.step_timer = 0.18 if "dash" in enemy.tags and enemy.age < 1.7 else 0.34
            if enemy.x <= BOARD.left + 8:
                cart = self.lane_bombs[enemy.row]
                if cart.state == "armed":
                    self.trigger_lane_bomb(enemy.row)
                if cart.state == "rolling":
                    # O zumbi é segurado por um instante na saída, dando ao
                    # carrinho tempo para alcançá-lo visualmente na faixa.
                    enemy.x = max(enemy.x, BOARD.left - 2)
                    continue
            if enemy.x < BOARD.left - 42:
                self.lost = True
                self.finished = True
                self.announce("BASE INVADIDA", 10, RED)

    def update_projectiles(self, dt: float) -> None:
        for projectile in self.projectiles[:]:
            projectile.elapsed += dt
            t = clamp(projectile.elapsed / projectile.travel, 0, 1)
            current_x = lerp(projectile.x, projectile.target_x, t)
            current_y = lerp(projectile.y, projectile.target_y, t) - (math.sin(t * math.pi) * 46 if projectile.kind in {"grenade", "mortar", "bazooka"} else 0)
            if random.random() < dt * 50:
                color = GOLD if projectile.friendly else (119, 224, 96)
                self.particles.append(Particle(current_x, current_y, random.uniform(-20, 20), random.uniform(-20, 20), 0.25, 2.2, color))
            if t < 1:
                continue
            self.projectiles.remove(projectile)
            if projectile.friendly:
                target = projectile.target
                if isinstance(target, Enemy) and target in self.enemies:
                    self.take_enemy_damage(target, projectile.damage, projectile.effect, projectile.owner if isinstance(projectile.owner, Defender) else None)
                    if projectile.radius > 0:
                        for other in self.enemies[:]:
                            if other is target:
                                continue
                            if abs(other.y - target.y) < CELL_H * 0.75 and abs(other.x - target.x) < projectile.radius:
                                self.take_enemy_damage(other, projectile.damage * 0.72, projectile.effect, projectile.owner if isinstance(projectile.owner, Defender) else None)
                    if projectile.kind in {"grenade", "mortar", "bazooka", "torpedo"}:
                        self.explosion(projectile.target_x, projectile.target_y, GOLD, 16)
            else:
                target = projectile.target
                if isinstance(target, Defender) and target in self.defenders:
                    self.damage_defender(target, projectile.damage, projectile.effect)
                    if projectile.radius:
                        for other in self.defenders[:]:
                            if other is target:
                                continue
                            if abs(other.y - target.y) < CELL_H * 0.75 and abs(other.x - target.x) < projectile.radius:
                                self.damage_defender(other, projectile.damage * 0.5, projectile.effect)
                    self.explosion(projectile.target_x, projectile.target_y, (106, 219, 91), 10)

    def update_particles(self, dt: float) -> None:
        for particle in self.particles[:]:
            particle.ttl -= dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += particle.gravity * dt
            if particle.ttl <= 0:
                self.particles.remove(particle)
        for text in self.texts[:]:
            text.ttl -= dt
            text.y -= 20 * dt
            if text.ttl <= 0:
                self.texts.remove(text)

    def update_wave(self, dt: float) -> None:
        if self.finished:
            return
        if not self.started_wave:
            self.intermission -= dt
            if self.intermission <= 0:
                self.start_next_wave()
            return
        if self.orders:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                # O alerta grande pertence à chegada do chefe, e não ao início
                # genérico da onda. Enquanto ele está visível, a ordem fica
                # segurada; terminado o aviso, o chefe entra de fato.
                next_order = self.orders[0]
                if next_order.boss:
                    if not self.boss_alert_pending:
                        boss_data = BOSSES[next_order.key]
                        self.boss_alert_pending = True
                        self.boss_warning = 3.0
                        self.boss_banner_name = str(boss_data["name"])
                        self.boss_banner_subtitle = "CHEFE E ESCOLTA EM APROXIMAÇÃO"
                        self.announce(f"ALERTA: {self.boss_banner_name} chegando!", 3.0, RED)
                        return
                    if self.boss_warning > 0:
                        return
                    self.boss_alert_pending = False
                order = self.orders.pop(0)
                self.spawn_enemy(order)
                self.spawn_timer = order.wait
        elif not self.enemies:
            if self.wave >= 15:
                self.finished = True
                self.victory = True
                self.announce("REGIÃO PROTEGIDA!", 10, GOLD)
                return
            self.started_wave = False
            self.intermission = 5.0
            self.supplies += 10 + self.wave
            self.announce(f"Onda {self.wave} concluída. Prepare a próxima.", 2.4, GOLD)

    def update(self, dt: float) -> None:
        # Pausa congela relógios, recargas, projéteis, inimigos e contagens. A
        # interface continua recebendo clique para MENU ou para retomar.
        if self.paused:
            return
        self.ambient_phase += dt
        self.shake = max(0, self.shake - dt)
        self.global_toxic = max(0, self.global_toxic - dt)
        self.boss_warning = max(0, self.boss_warning - dt)
        self.message_timer = max(0, self.message_timer - dt)
        for index, value in enumerate(self.card_cooldowns):
            self.card_cooldowns[index] = max(0, value - dt)
        self.update_wave(dt)
        self.update_defenders(dt)
        self.update_enemies(dt)
        self.update_lane_bombs(dt)
        self.update_projectiles(dt)
        self.update_particles(dt)

    def enemy_at(self, pos: tuple[int, int]) -> Enemy | None:
        for enemy in reversed(self.enemies):
            if enemy.hitbox().inflate(16, 16).collidepoint(pos):
                return enemy
        return None

    def click_enemy(self, enemy: Enemy) -> bool:
        if "steal" not in enemy.tags:
            return False
        returned = int(enemy.stolen) + 28
        self.supplies += returned
        self.announce(f"Carga recuperada: +{returned} suprimentos!", 2.0, GOLD)
        self.kill_enemy(enemy)
        return True

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.finished:
            return
        if self.menu_rect().collidepoint(pos):
            self.app.leave_battle_to_title()
            return
        if self.pause_rect().collidepoint(pos):
            self.paused = not self.paused
            self.announce("Partida pausada." if self.paused else "Partida retomada.", 1.5, GOLD)
            return
        if self.paused:
            return
        if self.remove_rect().collidepoint(pos):
            self.remove_mode = not self.remove_mode
            self.use_core = False
            self.announce("Ferramenta de remoção ativada: clique em uma defesa." if self.remove_mode else "Ferramenta de remoção desativada.", 1.8, TEAL)
            return
        if self.next_wave_rect().collidepoint(pos):
            if not self.started_wave:
                self.intermission = 0
                self.start_next_wave()
            else:
                self.announce("A horda atual ainda está em andamento.", 1.3, GRAY)
            return
        thief = self.enemy_at(pos)
        if thief and self.click_enemy(thief):
            return
        for index, rect in enumerate(self.card_rects()):
            if rect.collidepoint(pos):
                if self.card_cooldowns[index] <= 0:
                    self.selected_card = index
                    self.use_core = False
                    self.remove_mode = False
                return
        if self.core_rect().collidepoint(pos):
            if self.cores > 0:
                self.use_core = not self.use_core
                self.remove_mode = False
                self.announce("Clique em uma defesa para ascensioná-la." if self.use_core else "Núcleo cancelado.", 1.5, GOLD)
            else:
                self.announce("Derrote um chefe para receber um Núcleo.", 1.6, GRAY)
            return
        cell = self.board_cell_at(pos)
        if cell:
            row, col = cell
            if self.use_core:
                self.apply_core(row, col)
            elif self.remove_mode:
                self.remove_defender(row, col)
            else:
                self.place(row, col)

    def card_rects(self) -> list[pygame.Rect]:
        count = len(self.selected)
        width = min(138, (WIDTH - 185) // max(1, count))
        return [pygame.Rect(10 + index * width, 8, width - 5, 102) for index in range(count)]


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(f"Soldados vs Zumbis — Reconstrução v{VERSION}")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = FontBook()
        self.assets = Assets()
        self.running = True
        self.scene = "loading"
        self.scene_elapsed = 0.0
        self.save = load_save()
        self.region = "city"
        self.selection: list[tuple[str, str]] = []
        self.battle: Battle | None = None
        self.dossier_kind = "units"
        self.dossier_page = 0
        self.hover_card: tuple[str, str] | None = None

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.scene_elapsed += dt
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def update(self, dt: float) -> None:
        if self.scene == "loading":
            self.assets.load_next()
            if self.assets.complete:
                self.scene = "title"
                self.scene_elapsed = 0
        elif self.scene == "battle" and self.battle:
            self.battle.update(dt)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self.hover_card = None
                if self.scene == "select":
                    for key, display, rect in self.selection_cards():
                        if rect.collidepoint(event.pos):
                            self.hover_card = (key, display)

    def handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.scene == "title":
                self.running = False
            elif self.scene == "battle":
                self.leave_battle_to_title()
            else:
                self.scene = "title"
            return
        if self.scene == "title" and key in (pygame.K_RETURN, pygame.K_SPACE):
            self.scene = "campaign"
        elif self.scene == "campaign" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            target = ("city", "desert", "beach")[key - pygame.K_1]
            self.enter_selection(target)
        elif self.scene == "battle" and self.battle:
            if pygame.K_1 <= key <= pygame.K_8:
                choice = key - pygame.K_1
                if choice < len(self.battle.selected):
                    self.battle.selected_card = choice
                    self.battle.use_core = False
                    self.battle.remove_mode = False
            elif key == pygame.K_e:
                if self.battle.cores:
                    self.battle.use_core = not self.battle.use_core
                    self.battle.remove_mode = False
            elif key == pygame.K_r:
                self.battle.remove_mode = not self.battle.remove_mode
                self.battle.use_core = False
                self.battle.announce("Ferramenta de remoção ativada." if self.battle.remove_mode else "Ferramenta de remoção desativada.", 1.4, TEAL)
            elif key == pygame.K_p:
                self.battle.paused = not self.battle.paused
                self.battle.announce("Partida pausada." if self.battle.paused else "Partida retomada.", 1.4, GOLD)
            elif key == pygame.K_SPACE and not self.battle.started_wave:
                self.battle.intermission = 0
                self.battle.start_next_wave()
            elif self.battle.finished and key == pygame.K_RETURN:
                self.finish_battle()

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.scene == "loading":
            return
        if self.scene == "title":
            self.click_title(pos)
        elif self.scene == "campaign":
            self.click_campaign(pos)
        elif self.scene == "select":
            self.click_selection(pos)
        elif self.scene.startswith("dossier"):
            self.click_dossier(pos)
        elif self.scene == "howto":
            if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
                self.scene = "title"
        elif self.scene == "battle" and self.battle:
            if self.battle.finished:
                if pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50).collidepoint(pos):
                    self.finish_battle()
            else:
                self.battle.handle_click(pos)

    def title_buttons(self) -> list[tuple[str, pygame.Rect]]:
        return [
            ("JOGAR CAMPANHA", pygame.Rect(62, 282, 274, 54)),
            ("COMO JOGAR", pygame.Rect(62, 348, 274, 48)),
            ("SOLDADOS", pygame.Rect(62, 408, 130, 46)),
            ("ZUMBIS", pygame.Rect(206, 408, 130, 46)),
            ("SAIR", pygame.Rect(62, 468, 274, 42)),
        ]

    def click_title(self, pos: tuple[int, int]) -> None:
        for label, rect in self.title_buttons():
            if not rect.collidepoint(pos):
                continue
            if label == "JOGAR CAMPANHA":
                self.scene = "campaign"
            elif label == "COMO JOGAR":
                self.scene = "howto"
            elif label == "SOLDADOS":
                self.scene, self.dossier_kind, self.dossier_page = "dossier_units", "units", 0
            elif label == "ZUMBIS":
                self.scene, self.dossier_kind, self.dossier_page = "dossier_zombies", "zombies", 0
            elif label == "SAIR":
                self.running = False

    def click_campaign(self, pos: tuple[int, int]) -> None:
        for index, region in enumerate(("city", "desert", "beach")):
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            if rect.collidepoint(pos):
                self.enter_selection(region)
                return
        if self.button_rect("Voltar", 50, 645, 170, 46).collidepoint(pos):
            self.scene = "title"

    def enter_selection(self, region: str) -> None:
        self.region = region
        roster = REGION_ROSTERS[region]
        # A seleção começa com oito opções equilibradas, mas é inteiramente livre.
        starting_keys = {item[0] for item in roster[:8]}
        self.selection = [item for item in roster if item[0] in starting_keys][:8]
        self.scene = "select"

    def selection_cards(self) -> list[tuple[str, str, pygame.Rect]]:
        """Organiza pares de evolução em duas fileiras explícitas.

        Em cada bloco, N1 ocupa a faixa de cima e a sua N2 fica exatamente
        abaixo, na mesma coluna. Assim o jogador vê que são duas cartas e não
        a mesma arte repetida. As cartas aquáticas e o Sargento ficam nos
        espaços especiais restantes do segundo bloco.
        """
        cards: list[tuple[str, str, pygame.Rect]] = []
        names = {key: display for key, display in REGION_ROSTERS[self.region]}
        for pair_index, (level_one, level_two) in enumerate(PROMOTIONS.items()):
            block, col = divmod(pair_index, 7)
            for level_offset, key in enumerate((level_one, level_two)):
                display = names.get(key, str(DEFENSES[key]["base"]))
                row = block * 2 + level_offset
                rect = pygame.Rect(44 + col * 174, 100 + row * 126, 154, 116)
                cards.append((key, display, rect))
        for index, key in enumerate(("lancha", "submarino", "bomba_agua", "instrutor")):
            row = 2 if index < 3 else 3
            col = 4 + (index % 3)
            display = names.get(key, str(DEFENSES[key]["base"]))
            rect = pygame.Rect(44 + col * 174, 100 + row * 126, 154, 116)
            cards.append((key, display, rect))
        return cards

    def click_selection(self, pos: tuple[int, int]) -> None:
        for key, display, rect in self.selection_cards():
            if not rect.collidepoint(pos):
                continue
            item = (key, display)
            if item in self.selection:
                self.selection.remove(item)
            elif len(self.selection) < 8:
                self.selection.append(item)
            return
        launch = pygame.Rect(WIDTH - 290, 650, 240, 46)
        if launch.collidepoint(pos):
            if len(self.selection) == 8:
                self.battle = Battle(self, self.region, self.selection[:])
                self.scene = "battle"
            else:
                return
        if self.button_rect("Voltar", 45, 650, 160, 46).collidepoint(pos):
            self.scene = "campaign"

    def dossier_items(self) -> list[dict]:
        if self.dossier_kind == "units":
            items = [
                {"kind": "evolution", "l1": l1, "l2": l2}
                for l1, l2 in PROMOTIONS.items()
            ]
            items.append({"kind": "promoter", "key": "instrutor"})
            return items
        return [
            {"name": data["name"], "sub": "Chefe" if key in BOSSES else "Inimigo", "ability": data["ability"], "hp": int(data["hp"]), "key": key}
            for key, data in {**ENEMIES, **BOSSES}.items()
        ]

    def click_dossier(self, pos: tuple[int, int]) -> None:
        if self.button_rect("Voltar", 40, 648, 160, 42).collidepoint(pos):
            self.scene = "title"
            return
        if pygame.Rect(WIDTH - 180, 648, 140, 42).collidepoint(pos):
            items = self.dossier_items()
            pages = max(1, math.ceil(len(items) / 6))
            self.dossier_page = (self.dossier_page + 1) % pages

    def finish_battle(self) -> None:
        if not self.battle:
            self.scene = "campaign"
            return
        if self.battle.victory:
            region = self.battle.region
            if region not in self.save["completed"]:
                self.save["completed"].append(region)
            self.save["unlocked"] = list(REGIONS)
            self.save["best_wave"][region] = max(self.save["best_wave"].get(region, 0), 15)
            save_campaign(self.save)
        self.battle = None
        self.scene = "campaign"

    def leave_battle_to_title(self) -> None:
        """Saída voluntária sem registrar vitória, derrota ou progresso falso."""
        self.battle = None
        self.scene = "title"
        self.scene_elapsed = 0.0

    def button_rect(self, label: str, x: int, y: int, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(x, y, w, h)

    def draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[float, float], anchor: str = "topleft", shadow: bool = False) -> pygame.Rect:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        if shadow:
            shadow_surface = font.render(text, True, (0, 0, 0))
            shadow_rect = shadow_surface.get_rect()
            setattr(shadow_rect, anchor, (int(pos[0] + 2), int(pos[1] + 2)))
            self.screen.blit(shadow_surface, shadow_rect)
        self.screen.blit(surface, rect)
        return rect

    def panel(self, rect: pygame.Rect, alpha: int = 210, border: tuple[int, int, int] = (91, 106, 112), radius: int = 10) -> None:
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (12, 20, 25, alpha), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, (*border, min(255, alpha + 25)), surface.get_rect(), width=2, border_radius=radius)
        self.screen.blit(surface, rect)

    def button(self, label: str, rect: pygame.Rect, accent: tuple[int, int, int], enabled: bool = True) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
        outer = tuple(min(255, c + 25) for c in accent) if hover else accent
        color = outer if enabled else (67, 73, 76)
        pygame.draw.rect(self.screen, (8, 13, 17), rect.inflate(4, 4), border_radius=8)
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.screen, (228, 235, 228), rect, width=1, border_radius=7)
        self.draw_text(label, self.fonts.h2, INK if enabled else GRAY, rect.center, "center")

    def draw_loading(self) -> None:
        self.screen.fill((8, 13, 18))
        progress = self.assets.loaded / max(1, self.assets.total)
        pygame.draw.circle(self.screen, (39, 62, 72), (WIDTH // 2, 268), 92)
        pygame.draw.circle(self.screen, GOLD, (WIDTH // 2, 268), 92, 4)
        self.draw_text("SOLDADOS VS ZUMBIS", self.fonts.title, WHITE, (WIDTH / 2, 150), "center", True)
        self.draw_text(f"RECONSTRUÇÃO V{VERSION}", self.fonts.h2, GOLD, (WIDTH / 2, 202), "center")
        bar = pygame.Rect(WIDTH // 2 - 240, 390, 480, 18)
        pygame.draw.rect(self.screen, (31, 42, 47), bar, border_radius=9)
        pygame.draw.rect(self.screen, TEAL, (bar.x, bar.y, int(bar.width * progress), bar.height), border_radius=9)
        self.draw_text(f"Preparando artes e animações  {self.assets.loaded}/{self.assets.total}", self.fonts.body, WHITE, (WIDTH / 2, 425), "center")
        self.draw_text("Carregamento antecipado: a partida não precisa travar para buscar as artes.", self.fonts.small, GRAY, (WIDTH / 2, 463), "center")
        if self.assets.error:
            self.draw_text(self.assets.error, self.fonts.small, RED, (WIDTH / 2, 510), "center")

    def draw_title(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((3, 8, 12, 92))
        self.screen.blit(tint, (0, 0))
        self.panel(pygame.Rect(36, 80, 336, 462), 210, (166, 130, 62), 14)
        self.draw_text("SOLDADOS", self.fonts.title, (242, 239, 218), (62, 108), shadow=True)
        self.draw_text("VS", self.fonts.small, GOLD, (338, 153), "topright", True)
        self.draw_text("ZUMBIS", self.fonts.title, (154, 206, 127), (62, 166), shadow=True)
        self.draw_text("DEFENDA. RECARREGUE. RESISTA.", self.fonts.small, GRAY, (64, 224))
        for label, rect in self.title_buttons():
            accent = GOLD if label == "JOGAR CAMPANHA" else (81, 145, 137)
            self.button(label, rect, accent)
        self.draw_text(f"v{VERSION} • Cidade • Deserto • Praia", self.fonts.small, WHITE, (40, HEIGHT - 28))
        self.draw_text("Artes originais • campanha de 15 ondas", self.fonts.small, WHITE, (WIDTH - 36, HEIGHT - 28), "topright")

    def draw_campaign(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 11, 16, 170))
        self.screen.blit(veil, (0, 0))
        self.draw_text("MAPA DA CAMPANHA", self.fonts.title, WHITE, (WIDTH / 2, 38), "center", True)
        self.draw_text("Escolha livremente Cidade, Deserto ou Praia. Cada região possui 15 ondas e chefes nas ondas 5, 10 e 15.", self.fonts.body, GOLD, (WIDTH / 2, 84), "center")
        for index, region in enumerate(("city", "desert", "beach")):
            info = REGIONS[region]
            rect = pygame.Rect(72 + index * 402, 182, 360, 350)
            unlocked = True
            background = self.assets.images[f"{region}_bg"]
            crop = pygame.Rect(index * 160, 150, 360, 208)
            image = pygame.Surface((360, 210))
            image.blit(background, (0, 0), crop)
            self.screen.blit(image, rect)
            self.panel(rect, 105 if unlocked else 215, info["accent"] if unlocked else (75, 75, 75), 14)
            if not unlocked:
                lock = pygame.Rect(rect.centerx - 28, rect.y + 104, 56, 66)
                pygame.draw.rect(self.screen, (49, 54, 60), lock, border_radius=9)
                pygame.draw.arc(self.screen, GRAY, (lock.x + 9, lock.y - 27, 38, 40), 0, math.pi, 5)
                self.draw_text("BLOQUEADA", self.fonts.h2, GRAY, (rect.centerx, rect.y + 184), "center")
            else:
                self.draw_text(info["short"], self.fonts.h1, WHITE, (rect.centerx, rect.y + 222), "center", True)
                self.draw_text(info["tag"], self.fonts.small, info["accent"], (rect.centerx, rect.y + 252), "center")
                best = self.save["best_wave"].get(region, 0)
                status = "REGIÃO PROTEGIDA" if region in self.save["completed"] else f"Melhor: onda {best}/15"
                self.draw_text(status, self.fonts.small, GOLD if region in self.save["completed"] else WHITE, (rect.centerx, rect.y + 286), "center")
                self.button("PREPARAR CARTAS", pygame.Rect(rect.x + 55, rect.y + 304, 250, 34), info["accent"])
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_selection(self) -> None:
        region = REGIONS[self.region]
        self.screen.blit(self.assets.images[f"{self.region}_bg"], (0, 0))
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 11, 14, 157))
        self.screen.blit(shade, (0, 0))
        self.draw_text(f"SELEÇÃO DE CARTAS — {region['name'].upper()}", self.fonts.h1, WHITE, (WIDTH / 2, 22), "center", True)
        self.draw_text("Escolha 8 cartas. N1 fica sobre N2; cartas de água só cabem no canal da Praia.", self.fonts.small, GOLD, (WIDTH / 2, 55), "center")
        self.draw_text(f"{len(self.selection)}/8 selecionadas", self.fonts.h2, region["accent"], (WIDTH - 48, 82), "topright")
        for key, display, rect in self.selection_cards():
            data = DEFENSES[key]
            chosen = (key, display) in self.selection
            self.panel(rect, 230, region["accent"] if chosen else (91, 105, 107), 10)
            sprite = self.card_sprite(self.region, key, int(data["sprite"]))
            self.blit_sprite(sprite, rect.x + 6, rect.y + 15, 54, 64)
            # O rosto da carta é uma ficha curta de decisão. Nome e habilidade
            # aparecem exclusivamente ao passar o mouse, sem texto duplicado.
            metric_a, metric_b = self.card_metrics(data)
            self.draw_text(f"{data['cost']} SUP", self.fonts.small, GOLD, (rect.x + 66, rect.y + 14))
            self.draw_text(metric_a, self.fonts.tiny, WHITE, (rect.x + 66, rect.y + 38))
            self.draw_text(metric_b, self.fonts.tiny, TEAL if data["ammo"] or data["role"] in {"radio", "reload", "medic", "promoter"} else (208, 218, 213), (rect.x + 66, rect.y + 55))
            level = f"N{data['level']}" + (" • ÁGUA" if data.get("water_only") else "")
            self.draw_text(level, self.fonts.tiny, TEAL if data.get("water_only") else region["accent"], (rect.x + 12, rect.y + 93))
            self.draw_text(f"HP {int(data['hp'])}", self.fonts.tiny, GRAY, (rect.right - 12, rect.y + 93), "topright")
            if chosen:
                self.draw_text("✓", self.fonts.h1, GOLD, (rect.right - 15, rect.y + 10), "topright")
        self.button("VOLTAR", self.button_rect("Voltar", 45, 650, 160, 46), (98, 126, 137))
        self.button("INICIAR MISSÃO", pygame.Rect(WIDTH - 290, 650, 240, 46), region["accent"], len(self.selection) == 8)
        if self.hover_card:
            key, display = self.hover_card
            data = DEFENSES[key]
            tooltip = pygame.Rect(250, 600, 780, 42)
            self.panel(tooltip, 235, region["accent"], 8)
            self.draw_text(display, self.fonts.tiny, GOLD, (tooltip.x + 12, tooltip.y + 7))
            self.draw_wrapped(data["ability"], self.fonts.tiny, WHITE, pygame.Rect(tooltip.x + 126, tooltip.y + 7, tooltip.width - 138, 27), 2)

    def draw_howto(self) -> None:
        self.screen.blit(self.assets.images["menu"], (0, 0))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 10, 14, 186))
        self.screen.blit(veil, (0, 0))
        card = pygame.Rect(116, 72, WIDTH - 232, 560)
        self.panel(card, 238, GOLD, 16)
        self.draw_text("COMO JOGAR", self.fonts.title, WHITE, (card.centerx, card.y + 30), "center")
        lines = [
            ("1. Escolha 8 cartas", "Antes da missão, monte uma equipe. Cada região tem uniformes, armas e funções próprias."),
            ("2. Posicione por alcance", "As tropas só atacam quando um zumbi entra no alcance de seus blocos. Escopetas seguram perto; snipers cobrem a linha."),
            ("3. Munição é limitada", "Armas não recarregam sozinhas. Mecânicos e Engenheiros reabastecem tropas próximas; proteja-os."),
            ("4. Suprimentos e saúde", "Rádio gera créditos. Médicos limpam debuffs ou curam vida, conforme o nível da carta."),
            ("5. Chefes e N3", "Nas ondas 5, 10 e 15 há chefes. Ao derrubá-los, use N3 em uma defesa para ativar o Nível 3 temporário."),
            ("6. Comandos e água", "A aba superior reúne MENU, PAUSA, REMOVER, N3 e PRÓXIMA. Cartas aquáticas só entram no canal da Praia."),
        ]
        y = card.y + 102
        for head, body in lines:
            self.draw_text(head, self.fonts.h2, GOLD, (card.x + 48, y))
            self.draw_wrapped(body, self.fonts.body, WHITE, pygame.Rect(card.x + 48, y + 27, card.width - 96, 46), 2)
            y += 76
        self.button("VOLTAR", self.button_rect("Voltar", 50, 645, 170, 46), (92, 126, 137))

    def draw_unit_evolution_dossier(self) -> None:
        """Mostra a progressão literalmente em duas faixas: N1 sobre N2."""
        self.screen.blit(self.assets.images["menu"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 14, 190))
        self.screen.blit(overlay, (0, 0))
        accent = REGIONS[self.region]["accent"]
        self.draw_text("EVOLUÇÃO DOS SOLDADOS", self.fonts.title, WHITE, (WIDTH / 2, 20), "center", True)
        self.draw_text("N1 em cima • N2 embaixo • N3 é prêmio de chefe • o Sargento promove uma N1 próxima após 90 s", self.fonts.small, accent, (WIDTH / 2, 70), "center")
        items = self.dossier_items()
        start = self.dossier_page * 6
        for index, item in enumerate(items[start:start + 6]):
            row, col = divmod(index, 3)
            rect = pygame.Rect(52 + col * 404, 110 + row * 247, 372, 226)
            self.panel(rect, 238, accent, 12)
            if item["kind"] == "promoter":
                data = DEFENSES["instrutor"]
                sprite = self.card_sprite(self.region, "instrutor", int(data["sprite"]))
                self.blit_sprite(sprite, rect.x + 18, rect.y + 48, 106, 126)
                self.draw_text("CARTA DE PROMOÇÃO", self.fonts.tiny, GOLD, (rect.x + 140, rect.y + 25))
                self.draw_text(data["base"], self.fonts.h2, WHITE, (rect.x + 140, rect.y + 48))
                self.draw_text(f"Custo {data['cost']} SUP • HP {data['hp']}", self.fonts.tiny, GOLD, (rect.x + 140, rect.y + 78))
                self.draw_wrapped(data["ability"], self.fonts.small, (219, 229, 225), pygame.Rect(rect.x + 140, rect.y + 104, 210, 74), 4)
                continue
            for tier_index, key in enumerate((item["l1"], item["l2"])):
                data = DEFENSES[key]
                tier = pygame.Rect(rect.x + 10, rect.y + 27 + tier_index * 96, rect.width - 20, 88)
                tier_color = (102, 128, 135) if tier_index == 0 else GOLD
                self.panel(tier, 205, tier_color, 8)
                sprite = self.card_sprite(self.region, key, int(data["sprite"]))
                self.blit_sprite(sprite, tier.x + 5, tier.y + 8, 60, 72)
                self.draw_text(f"N{data['level']}", self.fonts.tiny, tier_color, (tier.x + 74, tier.y + 9), shadow=True)
                self.draw_text(str(data["base"]), self.fonts.small, WHITE, (tier.x + 103, tier.y + 7))
                self.draw_text(f"HP {int(data['hp'])} • DANO {int(data['damage'])} • ALC {int(data['range'])}", self.fonts.tiny, GOLD, (tier.x + 74, tier.y + 29))
                self.draw_wrapped(str(data["ability"]), self.fonts.tiny, (219, 229, 225), pygame.Rect(tier.x + 74, tier.y + 45, tier.width - 84, 34), 2)
        pages = max(1, math.ceil(len(items) / 6))
        self.draw_text(f"Página {self.dossier_page + 1}/{pages} • uniforme atual: {REGIONS[self.region]['short'].title()}", self.fonts.small, WHITE, (WIDTH / 2, 664), "center")
        self.button("VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137))
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

    def draw_dossier(self) -> None:
        is_units = self.dossier_kind == "units"
        if is_units:
            self.draw_unit_evolution_dossier()
            return
        self.screen.blit(self.assets.images["menu"], (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 14, 190))
        self.screen.blit(overlay, (0, 0))
        heading = "INFORMAÇÕES DOS SOLDADOS" if is_units else "INFORMAÇÕES DOS ZUMBIS"
        accent = TEAL if is_units else (139, 222, 106)
        self.draw_text(heading, self.fonts.title, WHITE, (WIDTH / 2, 24), "center", True)
        self.draw_text("As fichas abaixo mostram função, poder e contraponto tático.", self.fonts.body, accent, (WIDTH / 2, 70), "center")
        items = self.dossier_items()
        start = self.dossier_page * 6
        page_items = items[start:start + 6]
        for index, item in enumerate(page_items):
            row, col = divmod(index, 3)
            rect = pygame.Rect(52 + col * 404, 123 + row * 235, 372, 208)
            self.panel(rect, 236, accent, 12)
            icon_index = DEFENSES[item["key"]]["sprite"] if is_units else ({**ENEMIES, **BOSSES}[item["key"]]["sprite"])
            sprite_region = "city" if is_units else ("city" if item["key"] in {"caminhante", "corredor", "rastejante", "conehead", "policial", "militar", "escudo", "cuspidor", "divisor", "gritador", "saltador", "bruto", "bruto_demolidor", "comandante_mortos", "cuspidor_alfa"} else ("desert" if item["key"] in {"digger", "ladrao", "curandeiro", "parasita", "mutante", "necromante_minion", "mutante_ruinas", "necromante", "colosso_mutante"} else "beach"))
            sprite = self.card_sprite(sprite_region, item["key"], int(icon_index)) if is_units else self.assets.zombie(sprite_region, int(icon_index))
            self.blit_sprite(sprite, rect.x + 14, rect.y + 44, 105, 118)
            self.draw_text(item["name"], self.fonts.h2, WHITE, (rect.x + 132, rect.y + 22))
            self.draw_text(item["sub"], self.fonts.small, accent, (rect.x + 132, rect.y + 51))
            stat = f"Custo: {item['cost']} SUP • Nível {item['level']}" if is_units else f"Vida base: {item['hp']}"
            self.draw_text(stat, self.fonts.tiny, GOLD, (rect.x + 132, rect.y + 76))
            self.draw_wrapped(item["ability"], self.fonts.small, (219, 229, 225), pygame.Rect(rect.x + 132, rect.y + 100, 220, 83), 4)
        pages = max(1, math.ceil(len(items) / 6))
        self.draw_text(f"Página {self.dossier_page + 1}/{pages}", self.fonts.small, WHITE, (WIDTH / 2, 664), "center")
        self.button("VOLTAR", self.button_rect("Voltar", 40, 648, 160, 42), (92, 126, 137))
        self.button("PRÓXIMA", pygame.Rect(WIDTH - 180, 648, 140, 42), accent)

    def draw_battle(self) -> None:
        assert self.battle is not None
        battle = self.battle
        background = self.assets.images[f"{battle.region}_bg"]
        shake_x = int(math.sin(self.scene_elapsed * 55) * 4 * battle.shake)
        shake_y = int(math.cos(self.scene_elapsed * 37) * 3 * battle.shake)
        self.screen.blit(background, (shake_x, shake_y))
        # A área usa faixas de terreno reais. Não há quadrados coloridos: só
        # limites horizontais discretos onde os pés realmente caminham.
        ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if battle.region == "beach":
            for row in battle.water_rows:
                water_rect = pygame.Rect(BOARD.left, int(BOARD.top + row * CELL_H), BOARD.width, int(CELL_H))
                pygame.draw.rect(ambient, (56, 163, 232, 22), water_rect, border_radius=14)
        if battle.global_toxic > 0:
            ambient.fill((92, 202, 86, int(30 + battle.global_toxic * 8)))
        self.screen.blit(ambient, (0, 0))
        self.draw_lane_guides(battle)
        self.draw_lane_bombs(battle)
        self.draw_battle_top()
        mouse = pygame.mouse.get_pos()
        hovered_cell = battle.board_cell_at(mouse)
        if hovered_cell and not battle.finished:
            row, col = hovered_cell
            outline = battle.ground_cell_rect(row, col)
            color = RED if battle.remove_mode else (GOLD if battle.use_core else battle.region_color())
            pygame.draw.rect(self.screen, color, outline, 2, border_radius=12)
            if battle.cell_is_water(row, col):
                pygame.draw.arc(self.screen, (110, 213, 250), outline.inflate(-22, -28), 0, math.pi, 2)
        for defender in battle.defenders:
            self.draw_defender(defender)
        for enemy in battle.enemies:
            self.draw_enemy(enemy)
        self.draw_projectiles(battle)
        self.draw_particles(battle)
        self.draw_battle_status()
        if battle.finished:
            self.draw_result_overlay()

    def draw_lane_guides(self, battle: Battle) -> None:
        """Delimita as faixas sem reapresentar a antiga grade de quadrados."""
        guides = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        default = {
            "city": (202, 216, 218, 82),
            "desert": (128, 93, 49, 82),
            "beach": (177, 132, 75, 74),
        }[battle.region]
        for boundary in range(1, ROWS):
            y = int(BOARD.top + boundary * CELL_H)
            is_shore = battle.region == "beach" and boundary in {2, 3}
            color = (181, 241, 249, 145) if is_shore else default
            thickness = 3 if is_shore else 2
            for x in range(BOARD.left + 8, BOARD.right - 8, 96):
                pygame.draw.line(guides, color, (x, y), (min(x + 54, BOARD.right - 8), y), thickness)
        self.screen.blit(guides, (0, 0))

    def draw_lane_bombs(self, battle: Battle) -> None:
        """Mostra a contenção visual própria de cada terreno antes da invasão."""
        for cart in battle.lane_bombs:
            if cart.state == "spent":
                continue
            y = cell_center(cart.row, 0, battle.region)[1]
            x = cart.x if cart.state == "rolling" else BOARD.left - 18
            sprite = self.assets.images.get(battle.lane_bomb_asset_key(cart.row))
            is_water_buoy = battle.region == "beach" and cart.row in battle.water_rows
            if sprite and sprite.get_width() > 1:
                width, height = (66, 52) if is_water_buoy else (74, 50)
                self.blit_sprite(sprite, x - width / 2, y - height + 14, width, height)
            else:
                pygame.draw.rect(self.screen, (85, 94, 95), (int(x - 29), int(y - 23), 50, 24), border_radius=5)
                pygame.draw.rect(self.screen, GOLD, (int(x - 8), int(y - 32), 23, 14), border_radius=4)
            beacon = 4 + int(abs(math.sin(self.scene_elapsed * 8 + cart.row)) * 3)
            _, accent = battle.lane_bomb_info(cart.row)
            pygame.draw.circle(self.screen, accent, (int(x - 11), int(y - 39)), beacon)
            if cart.state == "armed":
                label = "BOIA" if is_water_buoy else "CARGA"
                self.draw_text(label, self.fonts.tiny, accent, (x - 2, y + 16), "center", True)

    def draw_battle_top(self) -> None:
        assert self.battle is not None
        battle = self.battle
        rects = battle.card_rects()
        for index, ((key, display), rect) in enumerate(zip(battle.selected, rects)):
            data = DEFENSES[key]
            active = index == battle.selected_card and not battle.use_core
            self.panel(rect, 238, GOLD if active else battle.region_color(), 7)
            if battle.card_cooldowns[index] > 0:
                dark = pygame.Surface(rect.size, pygame.SRCALPHA)
                dark.fill((0, 0, 0, 125))
                self.screen.blit(dark, rect)
            self.blit_sprite(self.card_sprite(battle.region, key, int(data["sprite"])), rect.x + 5, rect.y + 25, 44, 56)
            self.draw_text(str(index + 1), self.fonts.tiny, GOLD, (rect.x + 7, rect.y + 6))
            metric_a, metric_b = self.card_metrics(data)
            self.draw_text(f"{data['cost']} SUP", self.fonts.tiny, GOLD, (rect.x + 51, rect.y + 15))
            self.draw_text(metric_a, self.fonts.tiny, WHITE, (rect.x + 51, rect.y + 35))
            self.draw_text(metric_b, self.fonts.tiny, TEAL if data["ammo"] or data["role"] in {"radio", "reload", "medic", "promoter"} else GRAY, (rect.x + 51, rect.y + 54))
            if data.get("water_only"):
                self.draw_text("ÁGUA", self.fonts.tiny, TEAL, (rect.centerx, rect.bottom - 15), "center")
        self.panel(pygame.Rect(WIDTH - 176, 8, 166, 104), 230, battle.region_color(), 8)
        self.draw_text(f"{battle.supplies} SUP", self.fonts.h2, GOLD, (WIDTH - 93, 18), "center")
        self.draw_text(f"ONDA {battle.wave}/15", self.fonts.small, WHITE, (WIDTH - 93, 48), "center")
        self.draw_text(f"{len(battle.enemies) + len(battle.orders)} INVASORES", self.fonts.tiny, GRAY, (WIDTH - 93, 78), "center")

        # Comandos de missão em uma única aba, sempre acima do terreno.
        shelf = pygame.Rect(10, 118, WIDTH - 20, 50)
        self.panel(shelf, 221, battle.region_color(), 8)
        self.button("MENU", battle.menu_rect(), battle.region_color())
        self.button("PAUSA", battle.pause_rect(), GOLD)
        self.button("REMOVER", battle.remove_rect(), RED if battle.remove_mode else (88, 125, 132))
        self.button(f"N3 x{battle.cores}", battle.core_rect(), GOLD if battle.cores else (70, 73, 75), battle.cores > 0)
        self.button("PRÓXIMA", battle.next_wave_rect(), battle.region_color(), not battle.started_wave)
        if battle.started_wave:
            tactical_status = f"HORDA ATIVA • {len(battle.enemies) + len(battle.orders)} invasores"
        else:
            tactical_status = f"INTERVALO TÁTICO • {max(0, math.ceil(battle.intermission))} s"
        ticker = battle.message if battle.message_timer > 0 else "Equipe em posição."
        if len(ticker) > 62:
            ticker = ticker[:59] + "..."
        self.draw_text(tactical_status, self.fonts.tiny, WHITE, (615, 127))
        self.draw_text(ticker, self.fonts.tiny, GOLD if battle.message_timer > 0 else GRAY, (615, 147))
        self.draw_text("P", self.fonts.tiny, GRAY, (WIDTH - 26, 136), "topright")

        # Ficha completa apenas por hover: remove a redundância sem esconder a
        # informação tática para quem quer comparar as cartas.
        mouse = pygame.mouse.get_pos()
        hovered = next(((key, display, rect) for (key, display), rect in zip(battle.selected, rects) if rect.collidepoint(mouse)), None)
        if hovered:
            key, display, rect = hovered
            data = DEFENSES[key]
            tooltip_x = int(clamp(rect.centerx - 170, 154, WIDTH - 350))
            tooltip = pygame.Rect(tooltip_x, 178, 340, 72)
            self.panel(tooltip, 239, battle.region_color(), 8)
            self.draw_text(display, self.fonts.small, GOLD, (tooltip.x + 13, tooltip.y + 9))
            self.draw_wrapped(data["ability"], self.fonts.tiny, WHITE, pygame.Rect(tooltip.x + 13, tooltip.y + 29, tooltip.width - 26, 35), 2)
        elif battle.core_rect().collidepoint(mouse):
            tooltip = pygame.Rect(365, 178, 362, 58)
            self.panel(tooltip, 239, GOLD, 8)
            self.draw_text("N3", self.fonts.small, GOLD, (tooltip.x + 13, tooltip.y + 9))
            self.draw_text("Prêmio do chefe: ascende uma defesa por 18 s e recarrega a munição.", self.fonts.tiny, WHITE, (tooltip.x + 13, tooltip.y + 30))

    def draw_defender(self, defender: Defender) -> None:
        assert self.battle is not None
        battle = self.battle
        x, y = defender.x, defender.y
        shadow = pygame.Surface((100, 32), pygame.SRCALPHA)
        if battle.cell_is_water(defender.row, defender.col):
            pygame.draw.ellipse(shadow, (90, 220, 235, 105), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (7, 36, 52, 85), shadow.get_rect().inflate(-18, -10))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        self.screen.blit(shadow, (int(x - 50), int(y + 18)))
        bob = math.sin(self.scene_elapsed * 2.1 + defender.col) * 1.3
        # Veículos e embarcações preservam seus retratos funcionais próprios;
        # soldados, suporte e armadilhas recebem a arte do nível real da carta.
        if defender.stats["role"] in {"boat", "sub"}:
            sprite = self.assets.base_unit("beach", defender.sprite_index)
        else:
            sprite = self.assets.unit(battle.region, defender.sprite_index, int(defender.stats["level"]))
        scale = (86, 98) if defender.stats["role"] not in {"barrier", "boat", "sub"} else (105, 82)
        self.blit_sprite(sprite, x - scale[0] / 2, y - scale[1] + bob, *scale)
        if defender.ascended > 0:
            pygame.draw.circle(self.screen, GOLD, (int(x), int(y - 16)), 42, 2)
            pygame.draw.circle(self.screen, (255, 232, 116), (int(x), int(y - 16)), 31, 1)
            self.draw_text("N3", self.fonts.tiny, GOLD, (x, y - 73), "center")
            if defender.stats["role"] == "reload" and defender.stats["level"] >= 2:
                turret_x = min(BOARD.right - 18, x + CELL_W * 0.7)
                turret_y = y + 17
                pygame.draw.ellipse(self.screen, (17, 28, 32), (int(turret_x - 19), int(turret_y - 8), 38, 15))
                pygame.draw.rect(self.screen, (118, 147, 151), (int(turret_x - 13), int(turret_y - 25), 26, 21), border_radius=4)
                pygame.draw.rect(self.screen, TEAL, (int(turret_x + 8), int(turret_y - 20), 24, 6), border_radius=3)
                self.draw_text("INF", self.fonts.tiny, GOLD, (turret_x, turret_y - 37), "center")
        if defender.stun > 0:
            self.draw_text("STUN", self.fonts.tiny, GOLD, (x, y - 94), "center", True)
        if defender.corrosion > 0:
            self.draw_text("COR", self.fonts.tiny, (143, 232, 104), (x, y - 82), "center")
        self.health_bar(x - 38, y + 36, 76, defender.hp / defender.max_hp, (89, 214, 144))
        if defender.max_ammo:
            self.ammo_bar(x - 30, y + 47, 60, defender.ammo / max(1, defender.max_ammo))

    def draw_enemy(self, enemy: Enemy) -> None:
        assert self.battle is not None
        battle = self.battle
        bob_speed = 10 if enemy.is_boss else 14
        bob = math.sin(enemy.age * bob_speed + enemy.row * 0.9) * (2.5 if enemy.is_boss else 1.8)
        stride = math.sin(enemy.age * bob_speed * 0.5) * 2
        shadow = pygame.Surface((120 if enemy.is_boss else 76, 26), pygame.SRCALPHA)
        water_enemy = battle.region == "beach" and enemy.row in battle.water_rows
        if water_enemy:
            pygame.draw.ellipse(shadow, (91, 221, 238, 112), shadow.get_rect(), width=2)
            pygame.draw.ellipse(shadow, (8, 37, 50, 88), shadow.get_rect().inflate(-16, -8))
        else:
            pygame.draw.ellipse(shadow, (0, 0, 0, 115), shadow.get_rect())
        self.screen.blit(shadow, (int(enemy.x - shadow.get_width() / 2), int(enemy.y + 18)))
        sprite = self.assets.zombie(battle.region, int(enemy.data["sprite"]))
        scale = (132, 142) if enemy.is_boss else (82, 96)
        if enemy.stun > 0:
            angle = math.sin(enemy.age * 18) * 8
        else:
            angle = stride
        rendered = pygame.transform.rotate(self.assets.scaled(sprite, *scale), angle)
        if enemy.burrowed:
            rendered.set_alpha(208)
        self.screen.blit(rendered, (int(enemy.x - scale[0] / 2), int(enemy.y - scale[1] + bob)))
        if enemy.burn > 0:
            pygame.draw.circle(self.screen, (244, 133, 47), (int(enemy.x), int(enemy.y - 35)), 13, 2)
        if enemy.corrosion > 0:
            pygame.draw.circle(self.screen, (121, 225, 96), (int(enemy.x), int(enemy.y - 35)), 16, 1)
        if "steal" in enemy.tags:
            pygame.draw.circle(self.screen, GOLD, (int(enemy.x), int(enemy.y - 75)), 14, 2)
            self.draw_text("CLIQUE", self.fonts.tiny, GOLD, (enemy.x, enemy.y - 96), "center")
        width = 104 if enemy.is_boss else 64
        self.health_bar(enemy.x - width / 2, enemy.y + 31, width, enemy.hp / enemy.max_hp, RED)
        if enemy.is_boss:
            self.draw_text(enemy.data["name"], self.fonts.tiny, RED, (enemy.x, enemy.y - 103), "center")

    def draw_projectiles(self, battle: Battle) -> None:
        for projectile in battle.projectiles:
            t = clamp(projectile.elapsed / projectile.travel, 0, 1)
            x = lerp(projectile.x, projectile.target_x, t)
            y = lerp(projectile.y, projectile.target_y, t) - (math.sin(t * math.pi) * 46 if projectile.kind in {"grenade", "mortar", "bazooka"} else 0)
            colors = {
                "rifle": (245, 223, 126),
                "sniper": (215, 241, 255),
                "shotgun": (255, 206, 91),
                "grenade": (237, 148, 60),
                "mortar": (255, 139, 78),
                "bazooka": (246, 109, 60),
                "flame": (246, 142, 45),
                "torpedo": (74, 207, 237),
                "drone": (123, 223, 207),
                "turret": (154, 237, 226),
                "acid": (119, 231, 90),
                "enemy_bullet": (240, 100, 85),
            }
            color = colors.get(projectile.kind, WHITE)
            size = 7 if projectile.kind in {"grenade", "mortar", "bazooka", "torpedo"} else 4
            pygame.draw.circle(self.screen, color, (int(x), int(y)), size)

    def draw_particles(self, battle: Battle) -> None:
        for particle in battle.particles:
            alpha = int(255 * clamp(particle.ttl / 0.9, 0, 1))
            surf = pygame.Surface((int(particle.size * 2 + 2), int(particle.size * 2 + 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*particle.color, alpha), (surf.get_width() // 2, surf.get_height() // 2), int(particle.size))
            self.screen.blit(surf, (int(particle.x - surf.get_width() / 2), int(particle.y - surf.get_height() / 2)))
        for text in battle.texts:
            self.draw_text(text.text, self.fonts.tiny, text.color, (text.x, text.y), "center", True)

    def draw_battle_status(self) -> None:
        assert self.battle is not None
        battle = self.battle
        if battle.boss_warning > 0:
            banner = pygame.Rect(WIDTH // 2 - 330, 238, 660, 124)
            self.panel(banner, 244, RED, 12)
            self.draw_text("ALERTA: CHEFE CHEGANDO", self.fonts.h1, RED, (banner.centerx, banner.y + 16), "center", True)
            self.draw_text(battle.boss_banner_name, self.fonts.h2, WHITE, (banner.centerx, banner.y + 54), "center", True)
            self.draw_text(battle.boss_banner_subtitle, self.fonts.small, GOLD, (banner.centerx, banner.y + 85), "center")
        if battle.paused:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((3, 8, 12, 132))
            self.screen.blit(veil, (0, 0))
            pause_card = pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 74, 410, 148)
            self.panel(pause_card, 246, GOLD, 12)
            self.draw_text("PAUSADO", self.fonts.title, GOLD, (pause_card.centerx, pause_card.y + 23), "center", True)
            self.draw_text("Clique em PAUSA ou pressione P para continuar.", self.fonts.small, WHITE, (pause_card.centerx, pause_card.y + 86), "center")

    def draw_result_overlay(self) -> None:
        assert self.battle is not None
        battle = self.battle
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 6, 9, 188))
        self.screen.blit(overlay, (0, 0))
        heading = "REGIÃO PROTEGIDA" if battle.victory else "BASE INVADIDA"
        color = GOLD if battle.victory else RED
        self.panel(pygame.Rect(WIDTH // 2 - 265, HEIGHT // 2 - 130, 530, 285), 242, color, 16)
        self.draw_text(heading, self.fonts.title, color, (WIDTH / 2, HEIGHT / 2 - 85), "center", True)
        body = "Você venceu as 15 ondas. Todos os territórios continuam disponíveis para escolher sua próxima missão." if battle.victory else "Um infectado atravessou a linha final. Refaça a equipe e preserve munição para as ondas finais."
        self.draw_wrapped(body, self.fonts.body, WHITE, pygame.Rect(WIDTH // 2 - 205, HEIGHT // 2 - 30, 410, 55), 3, center=True)
        self.draw_text(f"Onda alcançada: {battle.wave}/15", self.fonts.small, GRAY, (WIDTH / 2, HEIGHT // 2 + 46), "center")
        self.button("VOLTAR AO MAPA", pygame.Rect(WIDTH // 2 - 145, HEIGHT // 2 + 100, 290, 50), color)

    def health_bar(self, x: float, y: float, width: float, ratio: float, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 6)
        pygame.draw.rect(self.screen, (22, 26, 28), rect, border_radius=3)
        pygame.draw.rect(self.screen, color, (rect.x, rect.y, int(rect.width * clamp(ratio, 0, 1)), rect.height), border_radius=3)

    def ammo_bar(self, x: float, y: float, width: float, ratio: float) -> None:
        rect = pygame.Rect(int(x), int(y), int(width), 4)
        pygame.draw.rect(self.screen, (19, 28, 33), rect, border_radius=2)
        pygame.draw.rect(self.screen, TEAL, (rect.x, rect.y, int(rect.width * clamp(ratio, 0, 1)), rect.height), border_radius=2)

    def blit_sprite(self, sprite: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
        if sprite.get_width() <= 1:
            return
        scaled = self.assets.scaled(sprite, width, height)
        self.screen.blit(scaled, (int(x), int(y)))

    def card_sprite(self, region: str, key: str, index: int) -> pygame.Surface:
        """Cartas marítimas preservam a silhueta naval mesmo fora da Praia."""
        if DEFENSES.get(key, {}).get("water_only"):
            water_index = {"lancha": 5, "submarino": 6, "bomba_agua": 11}[key]
            return self.assets.base_unit("beach", water_index)
        level = int(DEFENSES.get(key, {}).get("level", 1))
        return self.assets.unit(region, index, level)

    @staticmethod
    def card_metrics(data: dict) -> tuple[str, str]:
        """Converte a função em dois números úteis para a face da carta.

        A descrição continua no hover/dossiê. Aqui entram apenas estatísticas
        que o jogador usa para decidir rápido entre custo, alcance, munição,
        cura, recarga e contenção.
        """
        role = str(data["role"])
        level = int(data["level"])
        if role == "radio":
            gain = 14 if level == 1 else 28
            return f"SUP +{gain}", f"CICLO {float(data['cooldown']):.1f}s"
        if role == "reload":
            ammo = 4 if level == 1 else 7
            return f"RECARGA +{ammo}", f"RAIO {int(data['range'])}"
        if role == "medic":
            return ("LIMPA DEBUFF", f"RAIO {int(data['range'])}") if level == 1 else ("CURA +26", f"RAIO {int(data['range'])}")
        if role == "promoter":
            return "PROMOVE N1→N2", f"CICLO {int(data['cooldown'])}s"
        if role == "barrier":
            return f"HP {int(data['hp'])}", "EXPLODE" if level >= 2 else "BLOQUEIO"
        if role == "mine":
            area = "ÁREA" if data.get("water_only") else ("SEGURA" if level >= 2 else "1 ALVO")
            return f"DANO {int(data['damage'])}", area
        return f"DANO {int(data['damage'])}", f"MUN {int(data['ammo'])} • ALC {int(data['range'])}"

    def draw_wrapped(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect, lines: int, center: bool = False) -> None:
        words = text.split()
        built: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                built.append(current)
                current = word
        if current:
            built.append(current)
        for index, line in enumerate(built[:lines]):
            y = rect.y + index * (font.get_height() + 2)
            anchor = "midtop" if center else "topleft"
            x = rect.centerx if center else rect.x
            self.draw_text(line, font, color, (x, y), anchor)

    def draw(self) -> None:
        if self.scene == "loading":
            self.draw_loading()
        elif self.scene == "title":
            self.draw_title()
        elif self.scene == "campaign":
            self.draw_campaign()
        elif self.scene == "select":
            self.draw_selection()
        elif self.scene == "howto":
            self.draw_howto()
        elif self.scene.startswith("dossier"):
            self.draw_dossier()
        elif self.scene == "battle" and self.battle:
            self.draw_battle()


if __name__ == "__main__":
    Game().run()
