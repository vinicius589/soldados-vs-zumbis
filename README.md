# Soldados vs Zumbis — Reconstrução v7.1

Este é um jogo tower defense militar original feito em Pygame. A v7 é uma reconstrução separada: usa uma direção visual nova, não reutiliza os cenários nem os sprites das versões anteriores durante a execução e mantém as versões antigas intactas em suas próprias pastas.

A correção v7.1 troca os campos da Cidade e da Praia por arenas vistas de cima. Agora todos os pontos de movimentação ficam sobre asfalto, água ou areia; nenhuma faixa atravessa céu, prédios, paredões ou horizonte. Também corrige o erro de animação de projéteis que podia encerrar a partida quando um efeito de morteiro, fogo ou ácido era criado.

## Executar

No Windows, extraia o arquivo ZIP e dê duplo clique em executar.bat.

Ou abra um terminal dentro da pasta do jogo:

~~~powershell
python -m pip install -r requirements.txt
python main.py
~~~

Requer Python 3.10 ou superior e pygame-ce==2.5.8.

## Controles

- Clique em **Jogar Campanha** para abrir o mapa.
- Escolha uma região liberada e monte livremente uma equipe de 8 cartas.
- Clique numa carta e depois no terreno para posicionar a defesa.
- Teclas 1 a 8: selecionam as cartas da missão.
- Tecla E ou botão **Núcleo**: ativa o Núcleo de Ascensão; depois clique numa defesa.
- Clique no **Ladrão de Suprimentos** marcado com “CLIQUE” para recuperar a carga.
- Esc: volta para a tela anterior; durante a partida, retorna ao mapa.

## Estrutura da campanha

Há três regiões, desbloqueadas em sequência:

| Região | Terreno e identidade | Pressão inimiga |
| --- | --- | --- |
| Cidade Quarentenada | Avenida de asfalto integrada à cidade em ruínas | Tóxicos, blindados, policiais infectados, escudos e corredores |
| Deserto das Ruínas | Estrada de terra, pirâmides e tempestade de areia | Escavadores, ladrão mágico, curandeiro mortal, parasita e necromante |
| Praia de Maré Morta | Areia, enseada e faixas de água | Surfistas, boias, mergulhadores, caçadores e maré infectada |

Cada região possui **15 ondas**. Os chefes aparecem nas ondas **5, 10 e 15**, sempre com uma escolta. A progressão começa com poucas ameaças e aumenta tanto em quantidade quanto em resistência e composição inimiga.

## Regras principais

### Alcance real

Uma defesa só ataca quando o alvo entra na sua faixa de alcance. Escopetas resolvem o curto alcance; rifles e snipers cobrem a pista; granadas, morteiros e lança-chamas lidam com grupos de formas diferentes.

### Munição externa

Armas têm munição finita. Elas não se regeneram sozinhas:

- **Mecânico** reabastece aliados próximos.
- **Engenheiro** reabastece uma área maior e usa um drone de ataque leve.
- **Rádio** gera suprimentos para comprar novas cartas, mas não substitui a recarga.

Isso torna os suportes uma parte importante da formação em vez de uma carta decorativa.

### Núcleo de Ascensão: Nível 3 temporário

O chefe derrotado entrega um **Núcleo de Ascensão** (máximo de 3 guardados). Use-o em uma defesa já posicionada para ativar temporariamente seu Nível 3, limpar seus debuffs e completar sua munição.

Exemplos:

- Rifleiros cobrem a linha e acertam uma pequena área no fim do tiro.
- Escopetas ganham impacto maior em grupo.
- Snipers recebem dano de execução.
- Bombardeiros podem disparar uma bazuca que rasga a linha.
- Morteiros soltam bombas extras; lança-chamas mantém a queima.
- Engenheiros aceleram a logística, reforçam o drone e posicionam uma Torreta de bala infinita à frente enquanto a ascensão durar.
- Médicos curam e removem debuffs ao mesmo tempo.
- Barreiras passam a disparar e explodem ao cair.
- Minas limpam a linha inteira.

O Núcleo não altera a carta de forma permanente: ele é uma decisão de emergência ou de virada de onda.

### Água

Lancha Patrulha, Submarino e Bomba de Água podem entrar na seleção de cartas de qualquer região. Porém, só são posicionáveis nas faixas de água da **Praia de Maré Morta**. Tropas de terra não são colocadas dentro da água.

## Elenco e contrapontos

Cada região oferece mais de dez cartas temáticas. As roupas e silhuetas são próprias de Cidade, Deserto e Praia.

- **Rifles:** Recruta e Soldado controlam alvos simples; a ascensão libera o Fuzileiro.
- **Espingardas:** seguram corredores e saltadores perto da linha.
- **Snipers:** lidam com blindados e subchefes, mas exigem munição e proteção.
- **Explosivos:** quebram escudos e grupos; as granadas básicas podem acertar aliados próximos.
- **Fogo e morteiro:** aplicam dano em área por meios opostos: cone contínuo ou impacto de arco.
- **Engenharia, rádio e medicina:** sustentam munição, economia, vida e remoção de corrosão/atordoamento.
- **Contenção e minas:** compram tempo contra investidas, mas os saltadores conseguem ultrapassar a primeira linha.

Os zumbis possuem habilidades efetivas durante a batalha:

- Corredor e Surfista fazem dash inicial.
- Policial, Militar e Cowboy atiram de longe.
- Porta-Escudo e Salva-Vidas reduzem fogo frontal.
- Cuspidor Ácido e Cuspidor de Sal corroem armas e ferem à distância.
- Gritadores aceleram hordas.
- Escavador reaparece perto da tropa.
- Ladrão rouba suprimentos e pode ser clicado.
- Curandeiro recupera aliados e pode reanimar um infectado.
- Parasita e Mutantes atordoam ou desabilitam as defesas.
- Chefes aplicam eventos de campo, invocam aliados, aceleram a horda, soltam névoa ácida, ondas ou abalos.

## Animações e efeitos

Os zumbis têm animação de caminhada, balanço, dash, salto, entrada de escavação, rotação de atordoamento, dano de fogo/corrosão, barras de vida, morte com partículas e efeitos de habilidades. Tiros, granadas, morteiros, chamas, torpedos, ácido, impactos, cura e Núcleos também possuem efeitos em tempo real.

O cenário não usa quadrados verdes coloridos: a área de posicionamento acompanha o cenário pintado. Uma borda fina só aparece sob o mouse para indicar o ponto de instalação; na Praia, a água recebe um brilho discreto.

## Tela de carregamento

Antes de liberar o menu, o jogo abre uma tela de carregamento real e coloca em memória a arte do menu, os três cenários e os seis atlases de personagens. Assim, a mudança de tela e a entrada na missão não precisam carregar imagens pesadas no meio da partida.

## Arquivos

- main.py — jogo completo.
- smoke_test.py — verificações automatizadas sem janela visível.
- assets/v7/ — artes originais desta reconstrução.
- ASSET_MANIFEST.md — inventário e direção das artes originais.
- requirements.txt — dependência.
- executar.bat — atalho de execução no Windows.
- campanha_v7.json — criado automaticamente para guardar regiões liberadas; pode ser apagado para reiniciar a campanha.

## Verificação técnica

~~~powershell
python -m py_compile main.py smoke_test.py
python smoke_test.py
~~~

O teste usa SDL_VIDEODRIVER=dummy, portanto não abre uma janela gráfica.
