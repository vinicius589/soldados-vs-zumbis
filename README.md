Soldados vs Zumbis

==================



Um jogo de estratégia 2D no estilo Tower Defense desenvolvido em Python, utilizando Pygame-CE e composição de iluminação/renderização via PyOpenGL.



\---



Como Surgiu o Projeto

\---------------------



A ideia do Soldados vs Zumbis nasceu de partidas de Plants vs. Zombies, aliada ao desejo de criar uma mecânica autoral de estratégia em tempo real. O projeto começou como uma atividade académica no curso de Ciência da Computação na UNIPAC, idealizado por Vinícius da Motta Campos.



O objetivo principal era aplicar na prática conceitos de arquitetura de software, matemática computacional, renderização gráfica 2D e física de combate em Python. O que começou como um protótipo inicial evoluiu ao longo de múltiplos ciclos de desenvolvimento até se tornar um jogo completo.



\---



A História do Jogo

\------------------



O mundo entrou em colapso após um surto biológico devastador que transforma os infectados em mutantes agressivos de rápida evolução. Com a queda das forças de segurança convencionais, cabe aos batalhões de elite remanescentes estabelecer linhas de defesa para conter o avanço da horda.



A campanha do jogo divide-se em três frentes de batalha:



1\. Nova York (Caos Urbano): O ponto zero da infecção. As batalhas ocorrem entre ruínas de arranha-céus e barricadas policiais contra cidadãos infectados e tropas especiais contagiadas.

2\. Deserto do Egito (Ruínas Escaldantes): O vírus espalhou-se pelas zonas áridas. A defesa precisa de lidar com tempestades de areia, infectados adaptados ao calor e zonas de visibilidade reduzida.

3\. Cachoeira de Minas Gerais (Resistência Nacional): A frente de combate em território brasileiro. Em meio à vegetação densa e rios, os soldados enfrentam mutações rápidas e terrenos de difícil posicionamento.



\---



Mecânicas do Jogo

\-----------------



\- Defesa por Faixas (Grid 4xN): Posicione as suas tropas estrategicamente em quatro linhas de combate para barrar as investidas dos infectados.

\- Gerenciamento de Tropas e Deck: Seleção de esquadrão com até 8 cartas por operação, equilibrando custo de recursos, tempo de recarga, dano e alcance.

\- Campanha de 12 Ondas: Ciclos progressivos de dificuldade, culminando no combate contra Subchefes e Chefes de área.

\- Inimigos Especiais: Enfrente desde infectados comuns e corredores velozes até rastejadores, blindados com escudo e unidades com explosivos.

\- Renderização e Efeitos: Composição gráfica em Pygame-CE combinada com PyOpenGL para iluminação e efeitos visuais em tempo real.



\---



Tecnologias Utilizadas

\----------------------



\- Linguagem: Python 3.10+

\- Motor 2D: Pygame-Community Edition (Pygame-CE)

\- Renderização Gráfica: PyOpenGL / OpenGL

\- Processamento Numérico: NumPy

\- Testes e Qualidade: Pytest e ferramentas de regressão internas



\---



Como Executar o Projeto

\-----------------------



1\. Clone o repositório:

&#x20;  git clone https://github.com/vinicius589/soldados-vs-zumbis.git

&#x20;  cd soldados-vs-zumbis



2\. Prepare o ambiente (no Windows):

&#x20;  Execute o ficheiro PREPARAR\_AMBIENTE.bat



3\. Inicie o jogo:

&#x20;  Execute o ficheiro JOGAR.bat ou rode no terminal:

&#x20;  py main.py



\---



Histórico de Desenvolvimento

\----------------------------



O repositório mantém a versão estável na branch main e preserva o histórico de evolução em branches dedicadas:

\- main: Versão de produção atualizada (Alfa da Beta 5).

\- historico/alfas-e-betas: Registos históricos dos protótipos e evolução de código/arte.

\- historico/beta-1: Base da primeira versão jogável estável.



\---



Licença

\-------



Este projeto está licenciado sob a MIT License - consulte o ficheiro LICENSE para mais detalhes.



Desenvolvido por Vinícius da Motta Campos.

