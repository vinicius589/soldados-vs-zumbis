"""Testes do balanceamento e das fórmulas puras da campanha.

Todas as funções aqui são puras: não tocam em tela, áudio nem arquivos.
"""

from __future__ import annotations

import pytest
import src.main as game

# --------------------------------------------------------------- utilidades


def test_clamp_limites():
    assert game.clamp(5, 0, 10) == 5
    assert game.clamp(-1, 0, 10) == 0
    assert game.clamp(99, 0, 10) == 10
    assert game.clamp(0, 0, 10) == 0
    assert game.clamp(10, 0, 10) == 10


def test_clamp_com_float():
    assert game.clamp(3.7, 0.0, 1.0) == 1.0
    assert game.clamp(-0.2, 0.0, 1.0) == 0.0


def test_lerp_extremos_e_meio():
    assert game.lerp(0, 10, 0.0) == 0
    assert game.lerp(0, 10, 1.0) == 10
    assert game.lerp(0, 10, 0.5) == 5
    assert game.lerp(100, 200, 0.25) == 125


def test_title_case_substitui_underscore():
    assert game.title_case("arma_de_assalto") == "Arma De Assalto"
    assert game.title_case("bomba_agua") == "Bomba Agua"


# --------------------------------------------------------------- escalamento de onda


def test_ondas_primeira_e_ultima_valores_conhecidos():
    """A onda 1 é acolhedora e a 12 é o ápice da campanha."""
    assert game.enemy_wave_scale(1) == pytest.approx(0.66)
    assert game.enemy_wave_scale(game.TOTAL_WAVES) == pytest.approx(2.16)


def test_escalamento_de_inimigo_e_monotonamente_crescente():
    escalas = [game.enemy_wave_scale(w) for w in range(1, game.TOTAL_WAVES + 1)]
    assert escalas == sorted(escalas)
    assert len(set(escalas)) == len(escalas), "nenhuma onda pode repetir escala"


def test_escalamento_de_dano_e_monotonamente_crescente():
    danos = [game.enemy_damage_scale(w) for w in range(1, game.TOTAL_WAVES + 1)]
    assert danos == sorted(danos)


def test_dano_cresce_mais_devagar_que_vida():
    """A reta final não pode virar só uma esponja de vida."""
    vida = game.enemy_wave_scale(game.TOTAL_WAVES) - game.enemy_wave_scale(1)
    dano = game.enemy_damage_scale(game.TOTAL_WAVES) - game.enemy_damage_scale(1)
    assert dano < vida


def test_chefe_escala_mais_devagar_que_horda_comum():
    """Um chefe muda a montagem da linha, não vence por HP bruto."""
    horda = game.boss_wave_scale(game.TOTAL_WAVES) - game.boss_wave_scale(1)
    comum = game.enemy_wave_scale(game.TOTAL_WAVES) - game.enemy_wave_scale(1)
    assert horda < comum


def test_chefe_nasce_mais_forte_que_um_comum():
    assert game.boss_wave_scale(1) > game.enemy_wave_scale(1)


@pytest.mark.parametrize("fn", [game.enemy_wave_scale, game.enemy_damage_scale,
                                game.boss_wave_scale, game.boss_damage_scale])
def test_escala_e_limitada_fora_da_campanha(fn):
    """Ondas fora do intervalo não quebram a fórmula (clamp aplicado)."""
    dentro = [fn(w) for w in range(1, game.TOTAL_WAVES + 1)]
    assert fn(0) == pytest.approx(min(dentro))
    assert fn(999) == pytest.approx(max(dentro))
    assert fn(-50) == pytest.approx(min(dentro))


def test_dano_do_chefe_contido():
    """O dano físico do chefe é contido nas ondas altas (< 2x)."""
    assert game.boss_damage_scale(game.TOTAL_WAVES) < 2.0
    assert game.boss_damage_scale(1) == pytest.approx(0.70)


# --------------------------------------------------------------- recarga de arma


def test_recarga_legada_usa_tabela_do_papel():
    assert game.weapon_reload_seconds({"role": "rifle", "ammo": 5}) == pytest.approx(9.0)


def test_recarga_promovida_e_mais_rapida_com_piso_de_8s():
    base = game.weapon_reload_seconds({"role": "rifle", "ammo": 5})
    promovida = game.weapon_reload_seconds({"role": "rifle", "ammo": 5}, ascended=True)
    assert promovida < base
    assert promovida >= 8.0


def test_recarga_fica_entre_8_e_15_segundos():
    for papel in game.WEAPON_RELOAD_SECONDS:
        for nivel in (1, 2):
            segundos = game.weapon_reload_seconds(
                {"role": papel, "ammo": 6, "level": nivel}
            )
            assert 8.0 <= segundos <= 15.0, papel


def test_unidade_sem_municao_nao_atira():
    assert game.weapon_reload_seconds({"role": "rifle", "ammo": 0}) == 0.0


def test_papel_desconhecido_nao_crasha():
    assert game.weapon_reload_seconds({"role": "nao_existe", "ammo": 5}) == 0.0


def test_recarga_explícita_da_ficha_eh_respeitada():
    stats = {"reload": 2.0, "ammo": 3, "role": "rifle"}
    assert game.weapon_reload_seconds(stats) == pytest.approx(2.0)
    assert game.weapon_reload_seconds(stats, ascended=True) == pytest.approx(1.64)


# --------------------------------------------------------------- dificuldade


def test_dificuldade_desconhecida_cai_no_medio():
    """Salvamentos antigos com modo inválido não podem quebrar o jogo."""
    perfil = game.difficulty_profile("nao_existe")
    assert perfil["initial_supplies"] == 240
    assert perfil["enemy_hp"] == 1.0


def test_as_tres_dificuldades_existem():
    for chave in ("easy", "medium", "hard"):
        perfil = game.difficulty_profile(chave)
        assert perfil["label"]
        assert perfil["initial_supplies"] > 0


def test_dificuldade_facil_e_mais_branda_que_a_dura():
    facil = game.difficulty_profile("easy")
    dura = game.difficulty_profile("hard")
    assert facil["enemy_hp"] <= dura["enemy_hp"]
    assert facil["enemy_damage"] <= dura["enemy_damage"]
