# Arquitetura atual

Soldados vs Zumbis é um tower defense 2D escrito em Python. Pygame-CE cuida da janela, entrada, áudio e superfícies; PyOpenGL é usado na composição gráfica.

## Mapa de pastas

~~~text
run.py
src/
  main.py                  entrada pública compatível com src.main:main
  engine/
    animation2d.py         sprites, clipes e efeitos
    opengl_presenter.py    apresentação via OpenGL
    asset_paths.py         resolução da raiz de recursos
  game/
    runtime.py             ciclo principal, estado do jogo e integração
    battle.py              estado e regras de uma batalha
    entities.py            soldados, inimigos, projéteis e efeitos de estado
    assets.py              fontes, recursos e preparação de animações
    presentation.py        métodos de interface, HUD e desenho
    visual_layout.py       geometria visual e ancoragem
    beta4_expansion_roster.py
    beta4_production_animations.py
    beta4_scenario_runtime.py
assets/
  v7/                      cenários e sprites usados pelo jogo
  beta4_producao/          folhas de produção ainda carregadas pelo runtime
  audio_beta4/             efeitos sonoros e música
  audio_sources_cc0/       registro de fontes CC0
tests/                     testes de geometria, conteúdo e balanceamento
docs/                      documentação e decisões do projeto
~~~

## Responsabilidade dos módulos

- **engine** contém componentes de animação, apresentação e resolução de caminhos sem decidir as regras da campanha.
- **entities.py** define os dados e estados das unidades. As funções de balanceamento e geometria ainda estão no runtime e são injetadas por imports explícitos.
- **assets.py** concentra o carregamento de recursos, fontes, sprites e animações preparadas.
- **battle.py** reúne a simulação de batalha: posicionamento, ondas, movimento, dano, combate, projéteis e atualização dos estados.
- **presentation.py** concentra o desenho das telas, cartões, HUD, sprites animados, efeitos visuais e resultados.
- **runtime.py** integra as telas e os módulos. O arquivo ainda contém parte importante da lógica e das tabelas globais, que serão separados em etapas menores.

## Estado da refatoração

O código veio da Beta 4. A interface pública em src/main.py e o comando run.py continuam disponíveis para preservar compatibilidade com os testes e com as formas existentes de executar o jogo.

A extração de módulos reduziu o runtime de cerca de 10.100 para pouco mais de 3.300 linhas, separando apresentação, batalha, entidades e recursos. A remoção da segunda definição de Game.click_story também eliminou um método duplicado que antes era silenciosamente sobrescrito.

A separação é intencionalmente gradual: estes módulos ainda compartilham parte do namespace do runtime, então o passo seguinte é explicitar as dependências entre as camadas e transferir dados/configuração para módulos independentes. Não apague ou mova recursos em lote sem conferir quem os carrega e sem testar os três mapas.

## Recursos e distribuição

O runtime carrega recursos de assets/v7/, assets/beta4_producao/ e assets/audio_beta4/. Eles continuam no repositório porque a Beta 4 usa esses arquivos. Materiais brutos, laboratórios de sprites, variantes de cenários e ferramentas internas da pasta tools/ ficam no repositório histórico, fora da linha principal.

Os testes headless validam regras, geometria, conteúdo e presença de recursos essenciais. A compilação do Windows também deve verificar os arquivos no pacote e executar a checagem embutida --verificar-pacote, que cria o menu inicial, desenha os quadros iniciais e confirma o carregamento das artes. Isso ainda não equivale a uma partida manual completa em diferentes computadores.
