"""Testes de conteúdo: regiões, elenco, ondas e salvamento.

Travam o que o jogador encontra — não a implementação interna.
"""

from __future__ import annotations

from pathlib import Path

import src.main as game

RAIZ = Path(__file__).resolve().parents[1]

# Curva de liberação do elenco regional ao longo das 12 ondas.
CURVA_ESPERADA = (2, 3, 3, 3, 4, 5, 5, 5, 6, 6, 6, 6)


# --------------------------------------------------------------- regiões


def test_campanha_tem_três_regiões():
    assert list(game.REGIONS) == ["city", "desert", "beach"]


def test_regiões_são_desbloqueadas_em_sequência():
    """city → desert → beach. Nenhuma pula a anterior."""
    assert game.REGIONS["city"]["unlock_after"] is None
    assert game.REGIONS["desert"]["unlock_after"] == "city"
    assert game.REGIONS["beach"]["unlock_after"] == "desert"


def test_cada_região_tem_nome_curto_e_descrição():
    for regiao in game.REGIONS.values():
        assert regiao["name"].strip()
        assert regiao["short"].strip()
        assert regiao["description"].strip()
        assert len(regiao["accent"]) == 3, "cor de destaque é RGB"


def test_cada_região_tem_três_chefes():
    for chave, regiao in game.REGIONS.items():
        chefes = regiao["bosses"]
        assert len(chefes) == 3, f"{chave} deveria ter 3 chefes"
        assert all(nome.strip() for nome in chefes), f"{chave} tem chefe sem nome"
        assert len(set(chefes)) == 3, f"{chave} tem chefe repetido"


def test_campanha_tem_doze_ondas():
    assert game.TOTAL_WAVES == 12


# --------------------------------------------------------------- elenco


def test_cada_região_tem_elenco_próprio():
    for chave in game.REGIONS:
        elenco = game.REGION_ENEMIES[chave]
        assert len(elenco) > 0, chave


def test_elencos_regionais_não_se_cruzam():
    """Um inimigo apresentado no dossiê de uma região não vaza para outra."""
    vistos = {}
    for chave, elenco in game.REGION_ENEMIES.items():
        for inimigo in elenco:
            assert inimigo not in vistos, (
                f"{inimigo} aparece em {vistos[inimigo]} e {chave}"
            )
            vistos[inimigo] = chave


def test_elenco_regional_sem_duplicatas():
    for chave, elenco in game.REGION_ENEMIES.items():
        assert len(set(elenco)) == len(elenco), chave


# --------------------------------------------------------------- curva de ondas


def test_elenco_cresce_segundo_a_curva_de_liberação():
    for chave in game.REGIONS:
        for onda, esperado in enumerate(CURVA_ESPERADA, start=1):
            obtido = len(game.wave_enemy_pool(chave, onda))
            assert obtido == esperado, f"{chave} onda {onda}: {obtido} != {esperado}"


def test_elenco_da_onda_e_prefixo_do_dossiê():
    """Sem sorteio: a onda libera sempre os primeiros N do dossiê."""
    for chave, dossie in game.REGION_ENEMIES.items():
        for onda in range(1, game.TOTAL_WAVES + 1):
            pool = game.wave_enemy_pool(chave, onda)
            assert pool == tuple(dossie[: len(pool)]), f"{chave} onda {onda}"


def test_elenco_nunca_encolhe():
    for chave in game.REGIONS:
        tamanhos = [len(game.wave_enemy_pool(chave, w)) for w in
                    range(1, game.TOTAL_WAVES + 1)]
        assert tamanhos == sorted(tamanhos), chave


def test_onda_fora_do_intervalo_e_limitada():
    assert game.wave_enemy_pool("city", 0) == game.wave_enemy_pool("city", 1)
    assert (game.wave_enemy_pool("city", 999)
            == game.wave_enemy_pool("city", game.TOTAL_WAVES))


def test_primeira_onda_já_apresenta_dois_tipos():
    """A estreia não é monocromática."""
    assert len(game.wave_enemy_pool("city", 1)) == 2


# --------------------------------------------------------------- baralho


def test_baralho_global_tem_pelo_meno_oito_cartas():
    """Cada mapa escolhe 8 cartas de um baralho comum."""
    assert len(game.DEFENSES) >= 8


def test_toda_carta_tem_ficha_completa():
    for chave, ficha in game.DEFENSES.items():
        assert "role" in ficha, chave
        assert "sprite" in ficha, chave


def test_toda_carta_tem_recarga_valida():
    """Recarga fora de 8–15 s quebra o ritmo do jogador."""
    for chave, ficha in game.DEFENSES.items():
        segundos = game.weapon_reload_seconds(
            {"role": ficha.get("role", ""), "ammo": ficha.get("ammo", 1),
             "level": ficha.get("level", 1)}
        )
        if segundos:
            assert 8.0 <= segundos <= 15.0, chave


# --------------------------------------------------------------- salvamento


def test_save_novo_tem_as_três_regiões_liberadas():
    """Regiões são escolha de estilo, não trava de conteúdo."""
    save = game.make_save()
    assert save["unlocked"] == list(game.REGIONS)
    assert save["completed"] == []
    assert save["best_wave"] == {}


def test_load_save_sempre_retorna_estrutura_valida():
    """Save ausente, corrompido ou legado não pode quebrar o jogo."""
    save = game.load_save()
    assert isinstance(save, dict)
    for chave in ("unlocked", "completed", "best_wave"):
        assert chave in save, chave
    assert save["unlocked"] == list(game.REGIONS)


def test_progresso_pessoal_nao_entra_no_repositório():
    """O save do jogador é dado pessoal — precisa estar no .gitignore."""
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    ignorados = {linha.strip() for linha in gitignore.splitlines()
                 if linha.strip() and not linha.startswith("#")}
    assert game.SAVE_PATH.name in ignorados, (
        f"{game.SAVE_PATH.name} precisa estar no .gitignore"
    )
