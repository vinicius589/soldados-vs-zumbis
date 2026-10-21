🧟‍♂️ Soldados vs Zumbis
==================

O Soldados vs Zumbis e um jogo de estrategia 2D em tempo real no estilo Tower Defense tatico desenvolvido em Python. O projeto utiliza o motor Pygame-CE para gerenciamento de janelas, entrada de usuario e audio, integrado a um pipeline de renderizacao customizado via PyOpenGL com suporte a iluminacao dinamica e composicao de shaders.

Desenvolvido como projeto do curso de Ciencia da Computacao na UNIPAC por Vinicius da Motta Campos, o jogo aplica conceitos avancados de arquitetura de software, estruturacao de game loop, deteccao de colisoes, programacao orientada a objetos e matematica computacional aplicada a jogos.

--------------------------------------------------

🎮 Mecanicas e Arquitetura de Gameplay
-----------------------------------

🏠 Loop de Interface e Menu Principal
- Gerenciamento de estados de jogo (Menu, Selecao de Fase, Gameplay, Pause, Game Over).
- Acesso direto as configuracoes taticas, instrucoes de controle e creditos.

🛡️ Sistema de Posicionamento Tatico (Grid 4xN)
- Matriz de combate dividida em 4 faixas independentes de defesa.
- Controle de posicionamento espacial de unidades com checagem de ocupacao de celula.

🎴 Deck de Tropas e Economia de Suprimentos
- Selecao de ate 8 cartas taticas por partida.
- Economia baseada em suprimentos para invocacao e gerenciamento de tempo de recarga (cooldown).

🌊 Motor de Ondas e Progressao de Dificuldade
- Algoritmo de spawn incremental para controle de densidade da horda ao longo de 12 ondas.
- Batalhas contra Subchefes e Chefes de fase com padroes comportamentais especificos.
- Tres cenarios com identidades visuais e layouts proprios:
  - 🏙️ Nova York (Caos Urbano): Combate urbano com barricadas e destrocos.
  - 🏜️ Deserto do Egito (Ruinas Escaldantes): Visibilidade reduzida e tempestades de areia.
  - 🌊 Cachoeira de Minas Gerais (Resistencia Nacional): Terreno acidentado e densa vegetacao.

🧟 Inteligencia dos Infectados e Variedade de Inimigos
- Unidades com diferentes atributos de velocidade, vida e tipos de ataque (corredores, rastejadores, unidades blindadas e infectados explosivos).

💡 Pipeline de Renderizacao e Shaders (PyOpenGL)
- Pipeline 2D hibrido utilizando PyOpenGL para aceleracao via GPU.
- Composicao visual com suporte a transparencias, iluminacao ambiente e efeitos de luz em tempo real.

--------------------------------------------------

🚀 Stack Tecnologica
------------------

| Tecnologia | Modulo / Aplicacao |
| :--- | :--- |
| Python 3.10+ | Linguagem base do projeto |
| Pygame-CE (2.5.8) | Eventos, janela, input de usuario e mixagem de audio |
| PyOpenGL (3.1.10) | Pipeline de renderizacao 2D, shaders e iluminacao |
| NumPy (2.3.5) | Vetores, matrizes e calculos matematicos de transformacao |
| Pytest | Suite automatizada de testes unitarios e de integracao |
| Git / GitHub | Controle de versao e repositorio |

--------------------------------------------------

⚙️ Como Executar o Jogo
----------------------

Opcao 1: Execucao Rapida no Windows
1. Executar PREPARAR_AMBIENTE.bat (configura o ambiente virtual .venv e instala dependencias).
2. Executar JOGAR.bat para abrir o jogo.

Opcao 2: Execucao Via Terminal
1. Instalar as dependencias do arquivo requirements.txt:
   pip install -r requirements.txt

2. Iniciar a aplicacao:
   py main.py

--------------------------------------------------

📦 Instalacao Manual de Dependencias
-----------------------------------

Caso opte por instalar manualmente no seu ambiente Python:
pip install pygame-ce
pip install PyOpenGL
pip install numpy

--------------------------------------------------

🧠 Engenharia e Logica de Combate
---------------------------------

Sistema de Cooldown e Invocacao
- Cada carta de unidade consome uma quantidade de recursos taticos.
- Posicionar uma unidade ativa o tempo de recarga (cooldown) especifico da tropa, impedindo invocacoes repetidas instantaneas.

Fisica de Projeteis e Dano por Faixa
- Os projeteis sao processados individualmente em termos de trajetoria, velocidade e valor de dano.
- As verificacoes de colisao sao isoladas por faixa (linha do grid), otimizando a performance do loop de fisica.

Comportamento dos Infectados
- Cada tipo de inimigo implementa algoritmos de navegacao em linha reta com verificacao de obstaculo frontal.
- Inimigos atacam tropas ao entrar no raio de contato e alteram para estado de marcha na ausencia de alvos.

--------------------------------------------------

📌 Status de Desenvolvimento
--------------------------

Versao atual: Alfa da Beta 5 (Estavel e funcional).

Recursos implementados:
- Engine 2D com Game Loop estruturado.
- Suporte a 3 cenarios completos de batalha.
- Sistema de grid tatico 4xN funcional.
- Motor de ondas com 12 niveis de progressao.
- Batalhas de chefes com mecanicas proprias.
- Renderizador OpenGL com iluminacao e composicao.
- Cobertura de testes automatizados com mais de 60 verificacoes validadas.

--------------------------------------------------

