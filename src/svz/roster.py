"""Catálogo validado dos defensores regionais integrados ao jogo."""

from __future__ import annotations


SOLDIER_ANIMATIONS = ("move", "idle", "shoot", "reload", "hit")


def _soldier(name: str, weapon: str, **stats: object) -> dict[str, object]:
    return {
        "name": name,
        "weapon": weapon,
        "status": "integrated",
        "requires_new_sheet": False,
        "animation_contract": SOLDIER_ANIMATIONS,
        **stats,
    }


EXPANSION_DEFENDERS: dict[str, dict[str, dict[str, object]]] = {
    "city": {
        "atirador_precisao_swat": _soldier(
            "Atirador de Precisão", "AWM", role="sniper", cost=118, hp=90,
            damage=92, range=7, cooldown=2.35, ammo=5, reload=4.8,
            ability="Prioriza o infectado de maior vida dentro da linha.",
        ),
        "agente_entrada": _soldier(
            "Agente de Entrada", "SPAS-12", role="shotgun", cost=94, hp=132,
            damage=48, range=1, cooldown=1.05, ammo=6, reload=4.1,
            ability="Disparo próximo em leque, próprio da Tropa de Choque.",
        ),
        "especialista_antipraga": _soldier(
            "Especialista Antipraga", "Lançador de granadas químicas",
            role="gas_grenade", cost=112, hp=104, damage=24, range=3,
            cooldown=1.15, ammo=6, reload=5.4,
            ability="Lança granadas de gás venenoso e reagente anticorrosivo; a nuvem corrói blindagem biológica em área.",
        ),
        "lancador_foguetes": _soldier(
            "Lançador de Foguetes", "RPG-7", role="rocket", cost=154, hp=98,
            damage=126, range=5, cooldown=2.8, ammo=1, reload=6.4,
            ability="Explosão pesada em área, com longo intervalo de recarga.",
        ),
        "escudeiro_tropa_choque": _soldier(
            "Escudeiro da Tropa de Choque", "Escudo balístico e bastão",
            role="shield", cost=86, hp=260, damage=24, range=1,
            cooldown=1.15, ammo=0, reload=0.0, footprint=1,
            tactical_unit="Tropa de Choque",
            ability="Segura o primeiro contato e interrompe a investida; não ataca além da casa adjacente.",
        ),
    },
    "desert": {
        "atirador_horizonte": _soldier(
            "Atirador do Horizonte", "Dragunov SVD", role="sniper", cost=114,
            hp=92, damage=82, range=7, cooldown=2.05, ammo=7, reload=4.9,
            ability="Cobertura de precisão contínua nas pistas abertas.",
        ),
        "tenente_artilheiro": _soldier(
            "Tenente Artilheiro", "MG3", role="heavy", cost=142, hp=138,
            damage=11, range=4, cooldown=0.22, ammo=50, reload=6.1,
            ability="Rajada sustentada que ganha cadência enquanto mantém o alvo.",
        ),
        "incinerador_deserto": _soldier(
            "Incinerador do Deserto", "Lança-chamas", role="flame", cost=126,
            hp=124, damage=10, range=2, cooldown=0.30, ammo=28, reload=5.3,
            ability="Queimadura contínua exclusiva da força egípcia.",
        ),
        "nomade_morteiro": _soldier(
            "Nômade do Morteiro", "Morteiro portátil", role="mortar", cost=148,
            hp=102, damage=104, range=6, cooldown=2.7, ammo=4, reload=6.6,
            ability="Projétil em arco que atinge grupos atrás da linha frontal.",
        ),
        "guardiao_laminas": _soldier(
            "Guardião de Lâminas", "Duas lâminas táticas", role="blade",
            cost=82, hp=238, damage=34, range=1, cooldown=0.72,
            ammo=0, reload=0.0, footprint=1,
            ability="Tanque móvel da força egípcia: contra-ataca em curta distância e não usa munição.",
        ),
    },
    "beach": {
        "atirador_precisao_marinha": _soldier(
            "Atirador de Precisão Naval", "TRG-42", role="sniper", cost=116,
            hp=91, damage=88, range=7, cooldown=2.20, ammo=6, reload=4.9,
            ability="Cobertura naval de longa distância nas margens da cachoeira.",
        ),
        "bombeiro_hidraulico": _soldier(
            "Bombeiro Hidráulico", "Lançador de água pressurizada", role="waterjet",
            cost=108, hp=122, damage=7, range=3, cooldown=0.34, ammo=24,
            reload=4.6, ability="Empurra e desacelera infectados sem fazê-los voar.",
        ),
        "granadeiro_profundidades": _soldier(
            "Granadeiro das Profundidades", "M32 MGL", role="grenade", cost=146,
            hp=108, damage=76, range=4, cooldown=1.65, ammo=6, reload=5.8,
            ability="Granadas em área próprias para conter grupos no canal.",
        ),
        "homem_bomba": _soldier(
            "Homem-Bomba", "Carga de demolição", role="suicide_bomber", cost=96,
            hp=142, damage=188, range=0, cooldown=0.0, ammo=0, reload=0.0,
            ability="Fica imóvel na casa escolhida e se sacrifica, explodindo imediatamente no primeiro contato com um infectado.",
        ),
        "operador_sonar": _soldier(
            "Operador de Sonar", "Estação hidroacústica", role="sonar",
            cost=84, hp=132, damage=0, range=4, cooldown=6.5,
            ammo=0, reload=0.0, footprint=1,
            ability="Revela inimigos submersos e reduz a velocidade deles por uma janela curta.",
        ),
        "barco_patrulha": _soldier(
            "Barco de Patrulha", "Metralhadora naval", role="boat",
            cost=124, hp=210, damage=14, range=4, cooldown=0.32,
            ammo=36, reload=4.8, footprint=2, water_only=True,
            ability="Ocupa duas casas do canal, cobre uma faixa inteira e recebe bônus contra nadadores.",
        ),
        "submarino_tatico": _soldier(
            "Submarino Tático", "Torpedo compacto", role="sub",
            cost=158, hp=260, damage=112, range=6, cooldown=2.8,
            ammo=3, reload=7.2, footprint=2, water_only=True,
            ability="Ocupa duas casas do canal e lança torpedos em área contra ameaças pesadas.",
        ),
    },
}




def validate_expansion_registry() -> None:
    """Falha cedo se o lote tentar entrar incompleto ou reciclando arte."""
    for category, regions, contract, expected_status, needs_sheet in (
        ("soldado", EXPANSION_DEFENDERS, SOLDIER_ANIMATIONS, "integrated", False),
    ):
        if set(regions) != {"city", "desert", "beach"}:
            raise ValueError(f"regiões incompletas no lote de {category}")
        for region, entries in regions.items():
            expected = {"city": 5, "desert": 5, "beach": 7}[region]
            if len(entries) != expected:
                raise ValueError(f"{region} precisa de {expected} novos {category}s")
            for key, data in entries.items():
                if data.get("status") != expected_status:
                    raise ValueError(f"estado incorreto no lote: {key}")
                if bool(data.get("requires_new_sheet")) != needs_sheet:
                    raise ValueError(f"controle de folha incorreto: {key}")
                if tuple(data.get("animation_contract", ())) != contract:
                    raise ValueError(f"contrato de animação incompleto: {key}")


validate_expansion_registry()
