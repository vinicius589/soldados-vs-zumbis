"""Testes de geometria: faixas, células e escala de perspectiva.

A arte e a lógica consultam a mesma fonte (``LANE_BOUNDS`` / ``BOARD``).
Estes testes travam esse contrato para que uma mudança de cenário não
desloque soldados e zumbis em silêncio.
"""

from __future__ import annotations

import pygame
import pytest
import src.main as game

REGIOES = tuple(game.REGIONS)
FAIXAS = range(game.ROWS)


@pytest.fixture(scope="module", autouse=True)
def _headless():
    """Garante o subsistema de vídeo antes de criar Rects."""
    if not pygame.get_init():
        pygame.init()


# --------------------------------------------------------------- faixas


def test_todas_as_regioes_tem_limites_ordenados():
    """O topo de cada faixa sempre vem acima da base."""
    for regiao in REGIOES:
        for linha in FAIXAS:
            topo, base = game.lane_bounds(regiao, linha)
            assert topo < base, f"{regiao} linha {linha}: {topo} >= {base}"


def test_faixas_se_contiguas_sem_buracos_nem_sobreposicao():
    """A base de uma faixa é exatamente o topo da seguinte."""
    for regiao in REGIOES:
        for linha in range(game.ROWS - 1):
            _, base = game.lane_bounds(regiao, linha)
            topo_prox, _ = game.lane_bounds(regiao, linha + 1)
            assert base == pytest.approx(topo_prox), f"{regiao} linha {linha}"


def test_linha_fora_do_intervalo_eh_limitada():
    """Clique fora do tabuleiro não pode quebrar a leitura da faixa."""
    assert game.lane_bounds("city", -50) == game.lane_bounds("city", 0)
    assert game.lane_bounds("city", 999) == game.lane_bounds("city", game.ROWS - 1)


def test_regiao_desconhecida_cai_na_cidade():
    assert game.lane_bounds("regiao_inexistente", 0) == game.lane_bounds("city", 0)


# --------------------------------------------------------------- linha de contato


def test_contato_do_pe_e_independente_de_x():
    """Rotas horizontais: um zumbi nunca deriva verticalmente."""
    for regiao in REGIOES:
        for linha in FAIXAS:
            y_esq = game.terrain_y(regiao, linha, 0)
            y_dir = game.terrain_y(regiao, linha, 1280)
            assert y_esq == pytest.approx(y_dir), f"{regiao} linha {linha}"


def test_contato_do_pe_fica_dentro_da_faixa():
    for regiao in REGIOES:
        for linha in FAIXAS:
            topo, base = game.lane_bounds(regiao, linha)
            y = game.terrain_y(regiao, linha, 640)
            assert topo <= y <= base, f"{regiao} linha {linha}: {y} fora de [{topo}, {base}]"


def test_contato_e_no_centro_optico_da_pista():
    """60% da altura deixa a silhueta centrada sem apoiar na mureta."""
    topo, base = game.lane_bounds("city", 0)
    esperado = topo + 0.60 * (base - topo)
    assert game.terrain_y("city", 0, 0) == pytest.approx(esperado)


# --------------------------------------------------------------- profundidade


def test_profundidade_monotonamente_crescente():
    """Faixa distante menor, frente maior — em todas as regiões."""
    for regiao in REGIOES:
        profundidades = [game.lane_depth(regiao, linha) for linha in FAIXAS]
        assert profundidades == sorted(profundidades), regiao


def test_profundidade_limitada_e_positiva():
    for regiao in REGIOES:
        for linha in FAIXAS:
            d = game.lane_depth(regiao, linha)
            assert 0.0 < d <= 1.0, f"{regiao} linha {linha}: {d}"


def test_litoral_tem_perspectiva_mais_rasa():
    """O litoral usa projeção quase ortográfica (variação menor)."""
    city = [game.lane_depth("city", linha) for linha in FAIXAS]
    beach = [game.lane_depth("beach", linha) for linha in FAIXAS]
    assert (max(beach) - min(beach)) < (max(city) - min(city))


# --------------------------------------------------------------- células


def test_largura_da_faixa_cobre_o_tabuleiro():
    assert game.BOARD.width == pytest.approx(game.COLS * game.CELL_W)


def test_centro_da_celula_fica_dentro_do_tabuleiro():
    for linha in FAIXAS:
        for coluna in range(game.COLS):
            x, y = game.cell_center(linha, coluna)
            assert game.BOARD.left <= x <= game.BOARD.right, (linha, coluna)
            assert y > 0


def test_centro_da_celula_fica_na_sua_faixa():
    for linha in FAIXAS:
        topo, base = game.lane_bounds("city", linha)
        _, y = game.cell_center(linha, 0, "city")
        assert topo <= y <= base, f"linha {linha}: {y} fora de [{topo}, {base}]"


def test_celula_e_um_rect_com_largura_de_coluna():
    """``cell_rect`` opera em pixels inteiros, com arredondamento de no máx. 1px."""
    rect = game.cell_rect(0, 0)
    assert isinstance(rect, pygame.Rect)
    assert abs(rect.width - game.CELL_W) < 1.0
    assert rect.width == int(game.CELL_W)
    assert rect.height > 0


def test_primeira_coluna_comeca_na_borda_esquerda_do_tabuleiro():
    assert game.cell_rect(0, 0).left == pytest.approx(game.BOARD.left)

# --------------------------------------------------------------- HUD da batalha


def test_botao_voltar_a_base_cabe_sem_sobrepor_proxima_onda():
    """O rótulo maior mantém os comandos separados no HUD."""
    voltar = game.Battle.remove_rect()
    proxima = game.Battle.next_wave_rect()
    assert voltar.width == 156
    assert not voltar.colliderect(proxima)
    assert proxima.right == 496


def test_acao_de_recolher_usa_rotulo_voltar_a_base():
    """A interface usa o nome da ação, sem o rótulo antigo de remoção."""
    import inspect

    desenho = inspect.getsource(game.Game.draw_battle_top)
    assert '"VOLTAR À BASE"' in desenho
    assert '"REMOVER"' not in desenho
