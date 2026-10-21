# Arquitetura atual

Soldados vs Zumbis é um tower defense 2D escrito em Python. Pygame-CE cuida da janela, entrada, áudio e superfícies; PyOpenGL é usado na composição gráfica.

## Mapa de pastas

~~~text
run.py
src/
  main.py                  ponto de entrada compatível
  game/
    runtime.py             implementação atual do jogo, em decomposição gradual
    visual_layout.py       geometria visual e ancoragem
    beta4_expansion_roster.py
    beta4_production_animations.py
    beta4_scenario_runtime.py
  engine/
    animation2d.py         sprites, clipes e efeitos
    opengl_presenter.py    apresentação via OpenGL
    asset_paths.py         resolução da raiz de recursos
assets/
  v7/                      cenários e sprites finais usados pelo jogo
  beta4_producao/           folhas de produção carregadas pelo runtime
  audio_beta4/              efeitos sonoros e música
  audio_sources_cc0/        registro de fontes CC0
tests/                      testes de geometria, conteúdo e balanceamento
docs/                       documentação do projeto
~~~

## Estado do código

O runtime veio da Beta 4 e ainda concentra boa parte do loop, da interface e da lógica em um único módulo. A primeira reorganização separa o ponto de entrada (src/main.py) da implementação (src/game/runtime.py) e mantém a API pública esperada pelos testes e ferramentas. Isso é uma etapa de transição, não uma alegação de que todo o monólito já foi dividido.

A decomposição seguinte deve mover módulos coesos, começando por regras puras e dados de campanha, e só depois separar combate, interface e renderização. Cada etapa precisa preservar os testes e incluir testes específicos antes de apagar a implementação antiga.

## Recursos e distribuição

O runtime usa assets/v7/, assets/beta4_producao/ e assets/audio_beta4/; esses diretórios precisam continuar presentes porque o jogo os carrega. O material bruto, os protótipos e as ferramentas internas da antiga pasta tools/ serão deixados no repositório histórico, fora da cópia principal.

Os testes headless validam regras, geometria e conteúdo. A automação Windows também deve validar os arquivos essenciais dentro do pacote compilado e tentar abrir o executável antes de produzir um artefato.