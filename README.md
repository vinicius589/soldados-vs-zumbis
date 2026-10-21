🧟‍♂️ Soldados vs Zumbis



O \*\*Soldados vs Zumbis\*\* é um jogo de estratégia 2D no estilo \*Tower Defense\* desenvolvido em Python. O projeto combina o motor Pygame-CE com recursos avançados de iluminação e composição visual renderizados via PyOpenGL.



A ideia nasceu da paixão por jogos como \*Plants vs. Zombies\*, unida ao objetivo acadêmico de aplicar na prática conceitos de arquitetura de software, matemática computacional, física de combate e renderização gráfica no curso de Ciência da Computação na UNIPAC.



\---



📱 Funcionalidades e Mecânicas do Jogo



🏠 Menu Principal

\- Navegação centralizada pelas opções do jogo.

\- Seleção de frentes de batalha (cenários) e configurações.

\- Acesso rápido a instruções de controles e créditos.



🛡️ Defesa por Faixas (Grid 4xN)

\- Posicionamento tático de soldados em 4 linhas paralelas de combate.

\- Controle espacial para otimizar o alcance de tiro e barrar o avanço inimigo.



🎴 Gerenciamento de Tropas e Deck

\- Escolha de até 8 cartas de unidades por operação.

\- Equilíbrio entre custo de suprimentos, tempo de recarga (cooldown), alcance e poder de fogo.



🌊 Campanha de 12 Ondas

\- Ondas progressivas com diferentes padrões de aparecimento de inimigos.

\- Enfrentamento de Subchefes intermediários e Chefes de área ao final dos ciclos.

\- Progressão por três frentes de batalha com identidades visuais próprias:

&#x20; - 🏙️ \*\*Nova York (Caos Urbano):\*\* Batalhas entre ruínas de arranha-céus e barricadas.

&#x20; - 🏜️ \*\*Deserto do Egito (Ruínas Escaldantes):\*\* Enfrente a horda sob tempestades de areia e calor.

&#x20; - 🌊 \*\*Cachoeira de Minas Gerais (Resistência Nacional):\*\* Combate em vegetação densa e terreno acidentado.



🧟 Inimigos Especiais

\- Corredores velozes de reação rápida.

\- Rastejadores de baixo perfil.

\- Unidades blindadas com escudos táticos.

\- Infectados portadores de explosivos.



💡 Renderização e Efeitos Gráficos

\- Composição 2D integrada via PyOpenGL.

\- Efeitos visuais de iluminação, transparências e iluminação ambiente em tempo real.



\---



🚀 Tecnologias Utilizadas



| Tecnologia | Finalidade |

| :--- | :--- |

| Python 3.10+ | Linguagem principal do projeto |

| Pygame-CE (2.5.8) | Motor 2D, janela, eventos e reprodução de áudio |

| PyOpenGL (3.1.10) | Renderização gráfica, iluminação e composição de cena |

| NumPy (2.3.5) | Operações vetoriais e matrizes de transformação |

| Pytest | Suíte automatizada de testes unitários e de integração |

| Git / GitHub | Controle de versão e hospedagem do repositório |



\---



📁 Estrutura de Pastas



soldados-vs-zumbis/

├── assets/                          # Imagens, spritesheets e efeitos sonoros

│   ├── actors/                      # Sprites de soldados, zumbis e chefes

│   ├── audio/                       # Efeitos sonoros (tiros, explosões, horda) e música

│   ├── environment/                 # Elementos e cenários de fundo

│   └── interface/                   # Telas de UI, cards e HUD de combate

│

├── docs/                            # Documentação técnica e relatórios de auditoria

├── licenses/                        # Licenças das dependências e bibliotecas

│

├── src/

│   └── svz/                         # Código-fonte principal da aplicação

│       ├── app.py                   # Loop principal da aplicação e estados

│       ├── battle.py                # Lógica de batalha e detecção de colisões

│       ├── board.py                 # Grade (grid) de combate 4xN

│       ├── content.py               # Mapeamento de tropas, inimigos e atributos

│       ├── entities.py              # Entidades, projéteis e comportamentos

│       ├── rendering.py             # Pipeline de renderização com PyOpenGL

│       └── waves.py                 # Gerenciamento e spawn das ondas de infectados

│

├── tests/                           # Suíte com mais de 60 testes automatizados

├── tools/                           # Ferramentas de benchmark e verificação de qualidade

├── JOGAR.bat                        # Script para iniciar o jogo diretamente no Windows

├── PREPARAR\_AMBIENTE.bat            # Script para criação do .venv e instalação automática

├── main.py                          # Ponto de entrada da aplicação

├── project.toml                     # Configurações do projeto

├── requirements.txt                 # Dependências do projeto

├── LICENSE                          # Licença MIT

├── CONTRIBUTING.md                  # Diretrizes de contribuição

└── README.md                        # Documentação principal do projeto



\---



⚙️ Como Executar o Projeto



Opção 1: Inicialização Automática (Windows)

1\. Dê um duplo clique em `PREPARAR\_AMBIENTE.bat` (cria o ambiente virtual e instala as dependências).

2\. Dê um duplo clique em `JOGAR.bat` para iniciar o jogo.



Opção 2: Pelo Terminal / PowerShell

1\. Instale as dependências:

&#x20;  pip install -r requirements.txt



2\. Execute o projeto:

&#x20;  py main.py



\---



📦 Dependências Principais



Caso seja necessário instalar manualmente as dependências principais:

pip install pygame-ce

pip install PyOpenGL

pip install numpy



\---



🧮 Regras de Negócio e Lógica do Jogo



Recursos e Invocação

\- Cada tropa possui um custo específico em recursos de suprimento.

\- Ao posicionar uma unidade no grid, o card entra em \*cooldown\* (tempo de recarga) antes de poder ser utilizado novamente.



Controle de Dano e Colisão

\- Projéteis disparados pelos soldados possuem velocidade e valores de dano distintos conforme o tipo de arma (pistolas, fuzis, escopetas, lança-granadas).

\- Colisões são processadas em tempo real verificando a interseção entre a posição dos projéteis e o \*hitbox\* dos infectados na mesma faixa.



Sistema de Ondas

\- A dificuldade escala gradativamente a cada onda.

\- Ao atingir a onda 6, um Subchefe entra em campo; na onda 12, o Chefe da região deve ser derrotado para concluir a missão.



\---



📌 Status do Projeto



O projeto encontra-se totalmente funcional (Versão Alfa da Beta 5).



Funcionalidades disponíveis:

\- Sistema de menu e navegação.

\- Seleção de 3 frentes de batalha.

\- Posicionamento tático no grid.

\- Sistema de ondas com 12 níveis por região.

\- Subchefes e Chefes com mecânicas próprias.

\- Iluminação e efeitos gráficos via PyOpenGL.

\- Suíte automatizada de testes com mais de 60 verificações passando.



\---



👨‍💻 Autor



Vinícius da Motta Campos

