# Soldados vs Zumbis

**Um tower defense original feito em Python, com Pygame-CE e PyOpenGL.**

A proposta é simples: uma linha de defesa, recursos limitados e ondas de infectados ficando cada vez mais perigosas. O jogador escolhe suas tropas, decide onde posicioná-las e tenta segurar o avanço inimigo sem desperdiçar o que tem.

## A missão

A campanha leva o combate por três regiões com cenários e identidades próprias: **Nova York**, **Deserto do Egito** e **Cachoeira de Minas Gerais**. Cada frente pede atenção ao posicionamento e à composição do grupo. A cada ciclo, as ondas comuns dão lugar a um subchefe e depois a um chefe.

O projeto nasceu como uma atividade acadêmica e cresceu por protótipos, Alfas e Betas. Este repositório reúne a versão principal e atualizada do jogo.

## O que existe no jogo

- **Defesa por faixas:** quatro linhas de combate e uma grade de posicionamento.
- **Escolha de tropas:** monte uma equipe com até oito cartas por operação.
- **Campanha de 12 ondas:** ciclos com inimigos comuns, subchefes e chefes.
- **Três regiões:** Nova York, Deserto do Egito e Cachoeira de Minas Gerais.
- **Animações e efeitos próprios:** personagens, cenários e áudio organizados nos recursos do projeto.
- **Renderização 2D:** Pygame-CE com recursos de composição via PyOpenGL.

## Como executar o projeto

1. Clone o repositório:
   git clone https://github.com/vinicius589/soldados-vs-zumbis.git

2. Instale as dependências:
   pip install pygame-ce PyOpenGL

3. Inicie o jogo:
   python run.py
