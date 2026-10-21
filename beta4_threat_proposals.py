"""Elenco proposto de ameaças da Beta 4; ainda não ativado nas hordas."""

from __future__ import annotations


def threat(name: str, lore: str, behavior: str, ability: str, counterplay: str) -> dict[str, str]:
    return {
        "name": name,
        "lore": lore,
        "behavior": behavior,
        "ability": ability,
        "counterplay": counterplay,
        "status": "proposal",
    }


COMMON_THREATS = {
    "city": {
        "infectado_urbano": threat(
            "Infectado Urbano (Normal)",
            "Morador atingido pela primeira onda tóxica liberada pela Félix-13.",
            "Avança em velocidade média e morde a primeira defesa.",
            "Sem habilidade especial; serve de referência de balanceamento.",
            "Perde sozinho para tropas básicas, mas pressiona quando vem em grupo.",
        ),
        "corredor_cidade": threat(
            "Corredor da Félix",
            "Mensageiro de emergência alterado pela descarga do reator.",
            "Mantém velocidade alta constante e não sofre interrupção por tiros.",
            "Primeira mordida causa dano extra.",
            "Detecção antecipada, fogo automático ou bloqueio resistente.",
        ),
        "rastejador_cidade": threat(
            "Rastejador do Metrô",
            "Vítima esmagada nos túneis durante a evacuação de Nova York.",
            "Muito lento, baixo e difícil de perceber entre os escombros.",
            "Vida e mordida altas; devora classes iniciais se alcançar a casa.",
            "Precisão e dano concentrado antes que atravesse a metade da pista.",
        ),
        "policial_infectado": threat(
            "Policial Infectado",
            "Primeira linha policial abandonada pela diretoria da Félix.",
            "Marcha protegido pelo colete e absorve munição leve.",
            "Colete reduz os primeiros impactos balísticos.",
            "Antipraga, explosão ou sniper rompem a proteção.",
        ),
        "cientista_helix": threat(
            "Cientista da Félix",
            "Pesquisador fundido ao cilindro do composto que iniciou a contaminação.",
            "Fica atrás dos infectados resistentes e avança de forma cautelosa.",
            "Ao perder metade da vida, libera uma nuvem corrosiva curta.",
            "Eliminar de longe e não amontoar defensores na mesma área.",
        ),
        "tecnico_subestacao": threat(
            "Técnico da Subestação",
            "Operador reanimado com cabos e baterias da rede Félix presos ao corpo.",
            "Para por instantes para descarregar energia na defesa mais próxima.",
            "Pulso elétrico atrasa uma recarga, sem causar dano absurdo.",
            "Prioridade de alvo ou tropas com carregador curto.",
        ),
    },
    "desert": {
        "desperto_khepra": threat(
            "Desperto de Khepra (Normal)",
            "Corpo antigo reanimado quando a contaminação alcançou a escavação.",
            "Caminha em velocidade média e golpeia a primeira defesa.",
            "Sem habilidade especial; base estatística do Egito.",
            "É vencido em duelo por um Pistoleiro bem posicionado.",
        ),
        "corredor_deserto": threat(
            "Corredor das Dunas",
            "Batedor mumificado, leve e preservado pelo clima seco.",
            "Corre sem dash e ignora stagger.",
            "Primeiro golpe recebe bônus de impacto.",
            "MG3, SCAR ou tiro de precisão antes da linha intermediária.",
        ),
        "rastejador_deserto": threat(
            "Rastejador da Cripta",
            "Guardião mutilado pelo desabamento da câmara funerária.",
            "Rasteja devagar com muita vida.",
            "Ataque pesado contra classes 1 e 2.",
            "Morteiro e incinerador impedem sua aproximação.",
        ),
        "arqueiro_necropole": threat(
            "Arqueiro da Necrópole",
            "Soldado funerário ressuscitado com o arco ainda preservado.",
            "Mantém distância e lança flechas contaminadas.",
            "Dano remoto baixo, mas pode interromper uma unidade frágil.",
            "Sniper ou pressão rápida; possui pouca vida.",
        ),
        "hospedeiro_escaravelhos": threat(
            "Hospedeiro de Escaravelhos",
            "Múmia cuja cavidade foi tomada pela fauna alterada do complexo Khepra.",
            "Avança no centro do grupo e protege a colônia no torso.",
            "Ao morrer, libera escaravelhos que avançam poucos metros.",
            "Dano em área elimina corpo e enxame na mesma janela.",
        ),
        "saqueador_canopico": threat(
            "Saqueador Canópico",
            "Ladrão de sítio arqueológico reanimado segurando recipientes rituais.",
            "Procura a defesa de suprimento antes das unidades de tiro.",
            "Rouba uma pequena quantidade de suprimentos se alcançar a base.",
            "Proteja a torre de rádio e elimine-o por prioridade.",
        ),
    },
    "beach": {
        "afogado_cachoeira": threat(
            "Afogado da Cachoeira (Normal)",
            "Banhista contaminado pelo rejeito que desceu até Minas Gerais.",
            "Avança pela margem em velocidade média.",
            "Sem habilidade especial; base estatística da Cachoeira.",
            "Perde sozinho para o Marinheiro, mas força gasto de munição em grupo.",
        ),
        "corredor_cachoeira": threat(
            "Corredor da Margem",
            "Praticante de trilha alterado enquanto tentava fugir do vale.",
            "Corre em velocidade alta constante e não recebe stagger.",
            "Primeiro ataque causa dano extra.",
            "Fuzileiro naval e controle de água reduzem a pressão.",
        ),
        "rastejador_cachoeira": threat(
            "Rastejador do Barranco",
            "Vítima ferida pelas pedras quando a água contaminada transbordou.",
            "Muito lento, resistente e sempre preso ao chão.",
            "Mordida extremamente forte quando alcança tropas iniciais.",
            "TRG-42, granadas ou dano contínuo antes do contato.",
        ),
        "surfista_infectado": threat(
            "Surfista Infectado",
            "Turista levado pela corrente ainda agarrado a uma prancha quebrada.",
            "Usa canais de água e desacelera ao chegar à terra.",
            "Ignora bloqueios terrestres enquanto está no canal.",
            "Barco, submarino ou Bombeiro Hidráulico.",
        ),
        "mergulhador_afogado": threat(
            "Mergulhador Afogado",
            "Mergulhador de resgate preso ao cilindro oxidado após a contaminação.",
            "Some sob a água e emerge próximo da primeira defesa aquática.",
            "Trecho submerso reduz a detecção e o dano recebido.",
            "Sonar futuro, explosão em área ou defesa distribuída.",
        ),
        "pescador_da_praga": threat(
            "Pescador da Praga",
            "Morador ribeirinho reanimado com rede e anzóis contaminados.",
            "Para na média distância e lança a rede na unidade mais próxima.",
            "A rede reduz temporariamente a cadência de ataque.",
            "Atirador naval ou granadeiro antes do arremesso.",
        ),
    },
}


SUBBOSSES = {
    "city": {
        "demolidor_metro": threat(
            "Demolidor do Metrô",
            "Operário de manutenção fundido a ferramentas industriais.",
            "Lento, pesado e focado na primeira defesa da linha.",
            "Marretada em área danifica duas casas próximas.",
            "Antipraga e concentração de fogo antes do contato.",
        ),
        "bruto_quarentena": threat(
            "Bruto da Quarentena",
            "Segurança da Félix aprisionado dentro de um traje de contenção.",
            "Tanque urbano que protege infectados menores.",
            "Placas reduzem tiros frontais até serem quebradas.",
            "RPG-7, SPAS-12 próxima ou corrosão.",
        ),
    },
    "desert": {
        "guardiao_sarcofago": threat(
            "Guardião do Sarcófago",
            "Campeão funerário acordado para proteger a câmara principal.",
            "Avança com escudo ritual e abre espaço para a horda.",
            "Bloqueia os primeiros disparos e empurra uma defesa no golpe pesado.",
            "Fogo contínuo e morteiro quebram a formação.",
        ),
        "sacerdote_praga": threat(
            "Sacerdote da Praga",
            "Sacerdote reanimado cujo incensário absorveu o composto da Félix.",
            "Permanece atrás dos comuns e evita o combate direto.",
            "Fortalece temporariamente velocidade e resistência dos aliados próximos.",
            "Atirador do Horizonte deve eliminá-lo primeiro.",
        ),
    },
    "beach": {
        "baiacu_mutante": threat(
            "Baiacu Mutante",
            "Animal do rio transformado pelo rejeito concentrado nas piscinas naturais.",
            "Infla ao receber dano e avança pelo canal.",
            "Ao morrer, espalha espinhos em área sem trocar de faixa.",
            "Ataque de longa distância e espaçamento entre defensores.",
        ),
        "salva_vidas_colossal": threat(
            "Salva-Vidas Colossal",
            "Socorrista que absorveu resíduos enquanto retirava banhistas da água.",
            "Alterna margem e canal, protegendo afogados menores.",
            "Investida curta derruba cadência e causa dano em área.",
            "Jato d'água interrompe a preparação; granadas punem o grupo.",
        ),
    },
}


BOSSES = {
    "city": {
        "diretor_zero": threat(
            "Diretor Zero da Félix",
            "Executivo que autorizou o descarte e usou em si o protótipo de sobrevivência.",
            "Alterna marcha blindada, convocação de funcionários e sobrecarga do traje.",
            "Ativa chuva tóxica, corrompe uma faixa e invoca reforços da Félix.",
            "Trocar o foco entre reforços e núcleo exposto durante a sobrecarga.",
        ),
    },
    "desert": {
        "farao_khepra": threat(
            "Faraó Khepra Reanimado",
            "Soberano da pirâmide despertado quando o composto alcançou a câmara real.",
            "Comanda a horda em três fases e muda o ritmo das tochas da entrada.",
            "Tempestade de areia reduz alcance; decreto funerário revive um comum abatido.",
            "Destruir os guardiões e atacar durante o intervalo entre decretos.",
        ),
    },
    "beach": {
        "colosso_veu_verde": threat(
            "Colosso do Véu Verde",
            "Massa de algas, lixo, peixes e corpos formada no ponto de maior contaminação.",
            "Ocupa grande parte da entrada e alterna água e margem sem saltar.",
            "Tremor da cachoeira, onda contaminada e regeneração enquanto permanece na água.",
            "Forçar a saída para a margem e concentrar explosivos na fase seca.",
        ),
    },
}


def validate_proposal() -> None:
    for region in ("city", "desert", "beach"):
        if len(COMMON_THREATS[region]) != 6:
            raise ValueError(f"{region}: são necessários seis zumbis comuns")
        if len(SUBBOSSES[region]) != 2:
            raise ValueError(f"{region}: são necessários dois sub-bosses")
        if len(BOSSES[region]) != 1:
            raise ValueError(f"{region}: é necessário um boss")
    if sum(map(len, COMMON_THREATS.values())) != 18:
        raise ValueError("a proposta precisa totalizar 18 zumbis comuns")
    if sum(map(len, SUBBOSSES.values())) != 6:
        raise ValueError("a proposta precisa totalizar seis sub-bosses")
    if sum(map(len, BOSSES.values())) != 3:
        raise ValueError("a proposta precisa totalizar três bosses")


validate_proposal()
