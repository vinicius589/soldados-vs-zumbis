# Soldados vs Zumbis — Reconstrução v7.4

Este é um jogo tower defense militar original feito em Pygame. A v7 é uma reconstrução separada: usa uma direção visual nova, não reutiliza os cenários nem os sprites das versões anteriores durante a execução e mantém as versões antigas intactas em suas próprias pastas.

A v7.2 preserva as correções de estabilidade da v7.1 e reconstrói a **Praia de Maré Morta** em faixas físicas: areia, areia, canal de água, areia, areia. O canal está visualmente cercado por margem de madeira e pedra e coincide exatamente com a terceira linha de combate. As outras quatro linhas são areia sólida — ninguém fica flutuando sobre água, céu ou horizonte.

Esta atualização também devolve o **carrinho-bomba de contenção** a cada faixa, adiciona uma ferramenta segura para remover tropas, permite sair de uma missão diretamente para o menu inicial e recalibra as 15 ondas para começar leve e escalar de verdade até o fim.

A v7.3 completa a contenção por cenário: a Cidade usa o carrinho-bomba urbano, o Deserto usa uma carga das dunas, e a Praia usa carrinhos costeiros nas quatro faixas de areia mais uma **boia-bomba** no canal. Também reorganiza toda a interface da missão em uma aba superior, acrescenta pausa real e corrige os chefes para que a entrada especial não vire um bloqueio infinito de ataques.

A v7.4 transforma a evolução em algo que se vê e se joga: cada região agora pré-carrega um atlas próprio de **Nível 2**, separado da arte de Nível 1. A tela de Soldados exibe N1 imediatamente acima de N2 para cada evolução. A nova carta **Sargento de Promoção** promove, após 90 segundos em campo, uma tropa N1 próxima para sua versão N2. O Nível 3 continua sendo exclusivamente temporário e liberado pelo Núcleo recebido ao derrotar um chefe. Cidade, Deserto e Praia também ficam disponíveis para escolha desde o primeiro menu de campanha.

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
- Escolha livremente Cidade, Deserto ou Praia e monte uma equipe de 8 cartas.
- Clique numa carta e depois no terreno para posicionar a defesa.
- Teclas 1 a 8: selecionam as cartas da missão.
- Tecla E ou botão **N3**: ativa o Núcleo de Ascensão; depois clique numa defesa.
- Clique em **REMOVER** (ou pressione **R**) e depois em uma defesa para recolhê-la. São devolvidos 35% dos suprimentos; clique novamente em REMOVER para desligar a ferramenta.
- Clique em **PAUSA** (ou pressione **P**) para congelar inimigos, recargas, projéteis, cronômetros e ondas. Use o mesmo botão ou P para continuar.
- Clique em **PRÓXIMA** (ou pressione **Espaço** durante o intervalo) para iniciar a próxima onda antes da contagem terminar.
- Clique em **MENU** durante uma missão, ou pressione **Esc**, para voltar diretamente à tela inicial. Sair assim não marca vitória nem derrota.
- Clique no **Ladrão de Suprimentos** marcado com “CLIQUE” para recuperar a carga.
- Cada faixa começa com uma **Bomba de Contenção**. Quando o primeiro infectado cruza a linha final daquela faixa, ela percorre a linha uma única vez e elimina os invasores que encontrar. Cidade: carrinho urbano; Deserto: carga das dunas; Praia: carrinhos costeiros na areia e boia-bomba no canal. Quando a contenção já foi gasta, um invasor que escapar naquela faixa causa a derrota.

As faces das cartas exibem custo e estatísticas objetivas (dano, munição, alcance, vida, cura, recarga ou suprimento). Passe o mouse sobre uma carta para ver o nome temático e a habilidade completa, sem duplicar essa descrição no tabuleiro.

## Estrutura da campanha

Há três regiões disponíveis desde o início. Cada uma é uma rota completa de 15 ondas:

| Região | Terreno e identidade | Pressão inimiga |
| --- | --- | --- |
| Cidade Quarentenada | Avenida de asfalto integrada à cidade em ruínas | Tóxicos, blindados, policiais infectados, escudos e corredores |
| Deserto das Ruínas | Estrada de terra, pirâmides e tempestade de areia | Escavadores, ladrão mágico, curandeiro mortal, parasita e necromante |
| Praia de Maré Morta | Duas faixas de areia, um canal central de água e mais duas faixas de areia | Surfistas, boias, mergulhadores, caçadores e maré infectada |

Cada região possui **15 ondas**. Os chefes aparecem nas ondas **5, 10 e 15**, sempre com uma escolta e um alerta vermelho central de chegada. A progressão começa apenas com o inimigo-base, com pouca vida, pouco dano e intervalos maiores. A cada onda, a diretoria adiciona counters novos, aumenta a vida e o dano e reduz o intervalo de chegada; as últimas ondas trazem quase todo o elenco regional junto de grupos maiores. Recompensas de ondas, rádio e chefes foram reduzidas para que a economia não transforme o final em uma vitória automática.

Todo chefe possui duas camadas claras: uma **entrada especial**, usada uma única vez, e uma **habilidade recorrente localizada**, com recarga longa. Todos tiveram vida, dano, velocidade, escolta e controle de grupo recalibrados para serem ameaçadores sem travar uma partida. Exemplo: o Bruto Demolidor da Cidade paralisa os militares por 3 segundos ao entrar; depois, só o Martelo da faixa onde ele está interrompe os tiros por 1,2 segundo, com 18 segundos de intervalo. Assim o chefe exige reação, mas nunca cria uma cadeia infinita de atordoamento.

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

### Evolução Nível 1 → Nível 2

As cartas N1 e N2 estão disponíveis para a seleção. Elas não compartilham mais o mesmo retrato: cada cenário tem uniforme, silhueta e equipamento próprios para cada nível. Na tela **Soldados**, cada par aparece literalmente em duas faixas, com a carta N1 em cima e a respectiva N2 logo abaixo.

- **Sargento de Promoção**: carta de suporte N2 que custa 135 suprimentos. Ao sobreviver por 90 segundos, procura uma defesa N1 num raio de três blocos e nas faixas vizinhas e a promove permanentemente para a carta N2 correspondente.
- A promoção preserva uma parte proporcional de vida e munição, remove atordoamento/corrosão e reinicia os tempos de ataque com a ficha nova.
- O Sargento promove uma defesa por ciclo. Se não houver uma N1 próxima ao terminar o cronômetro, ele aguarda 8 segundos e verifica de novo; não desperdiça um ciclo completo.
- O Sargento não dá N3. O Nível 3 continua sendo um efeito separado, temporário e obtido somente de chefes derrotados.

### Água

Lancha Patrulha, Submarino e Bomba de Água podem entrar na seleção de cartas de qualquer região. Porém, só são posicionáveis no **canal central** da **Praia de Maré Morta**. Tropas de terra não são colocadas dentro da água.

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

Os zumbis têm animação de caminhada, balanço, passo com poeira/respingo, dash, salto, entrada de escavação, rotação de atordoamento, dano de fogo/corrosão, barras de vida, morte com partículas e efeitos de habilidades. Tiros agora criam clarões e partículas de boca de arma; granadas, morteiros, chamas, torpedos, ácido, impactos, cura, Núcleos e os carrinhos-bomba também possuem efeitos em tempo real.

O cenário não usa quadrados verdes coloridos: a área de posicionamento acompanha o cenário pintado. Uma borda fina só aparece sob o mouse para indicar o ponto de instalação; na Praia, a água recebe um brilho discreto.

## Tela de carregamento

Antes de liberar o menu, o jogo abre uma tela de carregamento real e coloca em memória a arte do menu, os três cenários, os **nove atlases** de personagens (N1, N2 e zumbis por região) e as quatro contenções de terreno — 17 recursos no total. Assim, a mudança de tela e a entrada na missão não precisam carregar imagens pesadas no meio da partida.

## Arquivos

- main.py — jogo completo.
- smoke_test.py — verificações automatizadas sem janela visível.
- assets/v7/ — artes originais desta reconstrução.
- ASSET_MANIFEST.md — inventário e direção das artes originais.
- requirements.txt — dependência.
- executar.bat — atalho de execução no Windows.
- campanha_v7.json — criado automaticamente para guardar melhores ondas e regiões concluídas; pode ser apagado para reiniciar esse histórico.

## Verificação técnica

~~~powershell
python -m py_compile main.py smoke_test.py
python smoke_test.py
~~~

O teste usa SDL_VIDEODRIVER=dummy, portanto não abre uma janela gráfica.
