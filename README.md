# Soldados vs Zumbis — Beta 3

Este é um jogo tower defense militar original feito em Pygame. A v7 é uma reconstrução separada: usa uma direção visual nova, não reutiliza os cenários nem os sprites das versões anteriores durante a execução e mantém as versões antigas intactas em suas próprias pastas.

A v7.2 preserva as correções de estabilidade da v7.1 e reconstrói a **Praia de Maré Morta** em faixas físicas: areia, areia, canal de água, areia, areia. O canal está visualmente cercado por margem de madeira e pedra e coincide exatamente com a terceira linha de combate. As outras quatro linhas são areia sólida — ninguém fica flutuando sobre água, céu ou horizonte.

Esta atualização também devolve o **carrinho-bomba de contenção** a cada faixa, adiciona uma ferramenta segura para remover tropas, permite sair de uma missão diretamente para o menu inicial e recalibra as 15 ondas para começar leve e escalar de verdade até o fim.

A v7.3 completa a contenção por cenário: a Cidade usa o carrinho-bomba urbano, o Deserto usa uma carga das dunas, e a Praia usa carrinhos costeiros nas quatro faixas de areia mais uma **boia-bomba** no canal. Também reorganiza toda a interface da missão em uma aba superior, acrescenta pausa real e corrige os chefes para que a entrada especial não vire um bloqueio infinito de ataques.

A v7.4 transforma a evolução em algo que se vê e se joga: cada região agora pré-carrega um atlas próprio de **Nível 2**, separado da arte de Nível 1. A tela de Soldados exibe N1 imediatamente acima de N2 para cada evolução. No modo **Difícil**, a carta especial **Sargento de Promoção** promove, após 90 segundos em campo, uma tropa N1 próxima para sua versão N2. O Nível 3 continua sendo exclusivamente temporário e liberado pelo Núcleo recebido ao derrotar um chefe. Cidade, Deserto e Praia também ficam disponíveis para escolha desde o primeiro menu de campanha.

A v7.5 resolve a leitura das minas e baixa a parede de dificuldade. As duas minas urbanas agora são explosivos isolados, sem caixas, suprimentos ou outros equipamentos anexados. Na Praia, as versões terrestre N1 e N2 são minas de areia independentes; a **Bomba de Água** virou uma mina naval própria, sem ponte, píer ou plataforma de madeira. Minas de pressão não podem mais ocupar o canal. Chefes receberam menos vida, menos dano e escoltas menores; blindados, subchefes e inimigos marítimos resistentes também tiveram a vida reduzida, enquanto os zumbis básicos permanecem intactos.

A v7.6 reconstrói a **Mecânica de Drones Costeira N1**: ela agora aparece diretamente no solo, com seu drone e tablet, sem ponte, píer ou madeira sob o personagem. Também adiciona o **Atirador de Lancha N1**, um rifleiro em barquinho que só pode ser colocado no canal e evolui para a Lancha Patrulha N2. Por fim, a mira corrige o caso em que um infectado ultrapassava poucos pixels da defesa e ela parava de atirar mesmo com alcance e munição: tropas agora continuam atacando quem já está travado em combate próximo.

A v7.7 adiciona a escolha de **Fácil, Médio ou Difícil** entre o menu e o mapa. Ela muda de verdade a partida: cartas permitidas, suprimentos/Núcleos iniciais, vida e dano dos inimigos, volume das hordas, velocidade de entrada e escolta de chefe. A seleção também passou a usar a mesma regra de arte do campo: no Médio, todo N1 aparece somente acima de sua N2 correspondente; no Fácil e no Difícil, só aparece o nível liberado, sem N1 duplicado, arte trocada ou sobreposição de cartas.

A v7.8 faz uma auditoria completa dessa regra de cartas. A origem do erro era uma tabela genérica que supunha que todas as folhas de arte guardavam N1 e N2 no mesmo índice; na realidade, Cidade, Deserto e Praia organizam as suas funções em posições diferentes. Agora há uma tabela explícita por **carta + região + nível**, usada pela seleção, tooltip, dossiê, card superior e defesa posicionada. Onde um atlas não tinha uma silhueta realmente exclusiva, foram criadas sete artes originais adicionais: os dois morteiros da Cidade, o morteiro N2 do Deserto, a mina N1 do Deserto, o lança-chamas N1 e os dois morteiros da Praia. A v7.8 também recalibra o Médio para começar mais gentil (130 SUP, inimigos 8% mais fracos, chefes 10% mais fracos e entradas 6% mais espaçadas), mantendo a progressão rumo às ondas finais sem transformá-lo em Fácil.

A v7.9 separa de vez os elencos marítimos. **Atirador de Lancha, Lancha Patrulha, Submarino e Bomba de Água existem apenas na Praia**; não aparecem nas cartas, evoluções ou fichas de Cidade e Deserto. A antiga dupla costeira de lança-chamas também foi substituída pelo **Lançador de Água N1** e pelo **Canhão de Maré N2**. Eles combatem da areia com jatos pressurizados: causam dano moderado, extinguem a queima e deixam os zumbis encharcados, reduzindo seu avanço por alguns segundos.

## Beta 3

Esta entrega fecha a revisão solicitada para a terceira beta, sem criar uma nova camada de conteúdo. Ela corrige a apresentação e a regra dos movimentos especiais, confere a curva dos três modos e torna toda a lista regional realmente encontrável em uma campanha de 15 ondas.

- A tela de carregamento usa **exatamente** a ilustração de referência enviada para esta beta como fundo, pré-carregada antes do menu; o arquivo não foi redesenhado nem substituído.
- O **Saltador** recebeu um retrato original sem pilar, ponte ou cenário embutido. No jogo, ele percorre um arco de salto visível e ultrapassa somente a primeira defesa bloqueadora.
- O **Rastejante urbano** agora tem uma silhueta própria, baixa e sem pernas funcionais; ele não reutiliza mais a arte nem a leitura visual do Corredor.
- A Cidade substitui o fogo por **Pulverizador de Veneno N1 → Canhão de Veneno N2**, com duas artes originais próprias. O estado **Envenenado** dura 4,2 segundos, causa dano periódico e reduz o avanço em 12%. O **Lança-Chamas** fica exclusivo do Deserto, recebeu mais dano e aplica **Queimadura** com duração finita.
- O **Escavador** não teleporta mais nem causa uma pancada grátis ao atravessar. Ele entra no chão, aparece como uma crista de terra com poeira percorrendo a faixa e emerge logo atrás da primeira defesa — uma única travessia por inimigo.
- A diretoria de ondas usa uma regra auditável: começa com o invasor-base, acrescenta ameaças em ordem e libera **100% do elenco de Cidade, Deserto ou Praia na onda 15**. Nenhum personagem regional fica cadastrado sem poder entrar em jogo.
- Fácil, Médio e Difícil continuam limitando cartas e regulando vida, dano, quantidade, intervalo, escolta e frequência dos poderes de maneira verificável: Fácil < Médio < Difícil. O Fácil permaneceu intacto; o Médio recebeu só uma pressão extra, enquanto o Difícil passou a ser o modo veterano, ainda vencível sem stun infinito ou paredes impossíveis de vida.

## Executar

No Windows, extraia o arquivo ZIP e dê duplo clique em executar.bat.

Ou abra um terminal dentro da pasta do jogo:

~~~powershell
python -m pip install -r requirements.txt
python main.py
~~~

Requer Python 3.10 ou superior e pygame-ce==2.5.8.

## Controles

- Clique em **Jogar Campanha**, escolha **Fácil**, **Médio** ou **Difícil** e então abra o mapa.
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

As faces das cartas exibem custo e estatísticas objetivas (dano, munição, alcance, vida, cura, recarga ou suprimento). Passe o mouse sobre uma carta para ver o nome temático e a habilidade completa, sem duplicar essa descrição no tabuleiro. Na missão, clicar em uma carta confirma brevemente o nome e o Nível escolhidos; a moldura dourada, a arte e a defesa posicionada usam a mesma chave de carta.

## Modos de dificuldade

| Modo | Cartas disponíveis | Preparação | Hordas e chefes |
| --- | --- | --- | --- |
| **Fácil** | Apenas cartas **N2** | 390 suprimentos e **3 Núcleos de Ascensão** já disponíveis para usar | Inimigos comuns têm 20% mais vida e dano; chefes têm 15% mais vida e dano. Hordas 15% maiores, escoltas 20% maiores, entradas 10% mais rápidas e poderes 15% mais frequentes. O arsenal N2 e os Núcleos mantêm o modo acessível, mas não existe botão nem atalho para remover tropas posicionadas. |
| **Médio** | Cartas **N1 e N2** | 128 suprimentos e nenhum Núcleo inicial | Inimigos comuns têm 36% mais vida e dano; chefes têm 24% mais vida e dano. Hordas 24% maiores, escoltas 36% maiores, entradas 23% mais rápidas e poderes 14% mais frequentes. É um desafio central exigente, mas ainda permite montar respostas com N1 e N2. |
| **Difícil** | Apenas cartas **N1** | 105 suprimentos para exigir uma formação mais consciente | Zumbis comuns têm 66% mais vida e 58% mais dano; chefes têm 62% mais vida e 50% mais dano, com horda 39% maior, escoltas 54% maiores, entradas 32% mais rápidas e poderes 16% mais frequentes. É a modalidade veterana, ainda vencível com munição, suportes e posicionamento. |

O Nível 3 não vira uma carta de seleção: ele é aplicado no campo por Núcleos. No Fácil, os três Núcleos iniciais equivalem aos upgrades N3 já liberados para a primeira missão; nos outros modos, eles continuam sendo conquistados ao derrotar chefes.

Todas as cartas, em todos os mapas e modos, têm **10 segundos de recarga depois de serem posicionadas**. Enquanto a carta recarrega, ela fica escurecida e exibe na própria interface quantos segundos ainda faltam.

## Estrutura da campanha

Há três regiões disponíveis desde o início. Cada uma é uma rota completa de 15 ondas:

| Região | Terreno e identidade | Pressão inimiga |
| --- | --- | --- |
| Cidade Quarentenada | Avenida de asfalto integrada à cidade em ruínas | Tóxicos, blindados, policiais infectados, escudos e corredores |
| Deserto das Ruínas | Estrada de terra, pirâmides e tempestade de areia | Escavadores, ladrão mágico, curandeiro mortal, parasita e necromante |
| Praia de Maré Morta | Duas faixas de areia, um canal central de água e mais duas faixas de areia | Surfistas, boias, mergulhadores, caçadores e maré infectada |

Cada região possui **15 ondas**. Os chefes aparecem nas ondas **5, 10 e 15**, sempre com uma escolta e um alerta vermelho central de chegada. A progressão começa apenas com o inimigo-base, com pouca vida, pouco dano e intervalos maiores. A cada onda, a diretoria adiciona counters novos, aumenta a vida e o dano e reduz o intervalo de chegada; as últimas ondas trazem quase todo o elenco regional junto de grupos maiores. Recompensas de ondas, rádio e chefes foram reduzidas para que a economia não transforme o final em uma vitória automática.

A curva é intencionalmente **fácil no começo e média–difícil no final**: a última parte reúne mais inimigos, vida e dano maiores, além dos chefes, mas mantém vida, escolta e intervalos em faixas vencíveis sem depender obrigatoriamente da contenção de última linha.

Todo chefe possui duas camadas claras: uma **entrada especial**, usada uma única vez, e uma **habilidade recorrente localizada**, com recarga longa. A v7.5 diminui o teto de vida e dano de todos os chefes e reduz uma unidade da escolta em cada marco, preservando a necessidade de montar uma linha funcional sem transformar o carrinho-bomba na única forma de vencer. Exemplo: o Bruto Demolidor da Cidade paralisa os militares por 3 segundos ao entrar; depois, só o Martelo da faixa onde ele está interrompe os tiros por 1,2 segundo, com 18 segundos de intervalo. Assim o chefe exige reação, mas nunca cria uma cadeia infinita de atordoamento.

## Regras principais

### Alcance real

Uma defesa só ataca quando o alvo entra na sua faixa de alcance. Escopetas resolvem o curto alcance; rifles e snipers cobrem a pista; granadas, morteiros e armas especiais lidam com grupos de formas diferentes.

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
- Morteiros soltam bombas extras; o lança-chamas do Deserto intensifica a Queimadura, o Canhão de Veneno urbano amplia a nuvem tóxica e o Canhão de Maré segura inimigos encharcados na Praia.
- Engenheiros aceleram a logística, reforçam o drone e posicionam uma Torreta de bala infinita à frente enquanto a ascensão durar.
- Médicos curam e removem debuffs ao mesmo tempo.
- Barreiras passam a disparar e explodem ao cair.
- Minas limpam a linha inteira.

O Núcleo não altera a carta de forma permanente: ele é uma decisão de emergência ou de virada de onda.

### Evolução Nível 1 → Nível 2

As cartas N1 e N2 estão disponíveis para a seleção. Elas não compartilham mais o mesmo retrato: cada cenário tem uniforme, silhueta e equipamento próprios para cada nível. A v7.8 valida essa identidade por carta e a v7.9 também a limita à região correta: uma N2 não pode carregar a arte, a habilidade ou o terreno de uma classe vizinha. Na tela **Soldados**, cada par aparece literalmente em duas faixas, com a carta N1 em cima e a respectiva N2 logo abaixo.

- **Sargento de Promoção**: carta especial exclusiva do modo **Difícil**, que custa 135 suprimentos. Ao sobreviver por 90 segundos, procura uma defesa N1 num raio de três blocos e nas faixas vizinhas e a promove permanentemente para a carta N2 correspondente. Não aparece no Fácil nem no Médio.
- A promoção preserva uma parte proporcional de vida e munição, remove atordoamento/corrosão e reinicia os tempos de ataque com a ficha nova.
- O Sargento promove uma defesa por ciclo. Se não houver uma N1 próxima ao terminar o cronômetro, ele aguarda 8 segundos e verifica de novo; não desperdiça um ciclo completo.
- O Sargento não dá N3. O Nível 3 continua sendo um efeito separado, temporário e obtido somente de chefes derrotados.

### Água

Atirador de Lancha, Lancha Patrulha, Submarino e Bomba de Água aparecem **somente** na seleção e nas fichas de soldados da **Praia de Maré Morta**. Eles só são posicionáveis no **canal central** desse mapa. Cidade e Deserto não mostram itens marítimos na montagem de equipe. Tropas de terra não são colocadas dentro da água.

As cartas **Mina de Areia** e **Mina Segura** são terrestres: ficam apenas nas quatro faixas secas da Praia. Elas têm sprites próprios, sem suprimentos, caixas ou ponte. A **Bomba de Água** é a alternativa naval e usa uma mina marítima independente, apenas no canal.

O **Atirador de Lancha N1** também é aquático: é uma carta de rifle de três blocos, com 10 disparos, montada em um pequeno barco. Ele só entra no canal e pode ser promovido pelo Sargento para a **Lancha Patrulha N2**.

O **Lançador de Água N1** e o **Canhão de Maré N2** são cartas terrestres exclusivas da Praia: ficam nas quatro faixas de areia, não no canal. Em vez de fogo, seus jatos de alta pressão atingem uma área curta, removem a queima e aplicam **Encharcado** por 2,4 segundos (3,6 s enquanto estiverem em N3), reduzindo em 32% a velocidade do zumbi. Eles têm dano menor que o lança-chamas, portanto servem para controlar avanço e abrir espaço, não para derreter uma horda sozinhos.

### Armas elementais por região

- **Cidade:** Pulverizador de Veneno N1 e Canhão de Veneno N2. Aplicam **Envenenado** por 4,2 segundos, com dano periódico, partículas verdes e 12% de redução de velocidade.
- **Deserto:** Lança-Chamas de Mão N1 e Lança-Chamas N2. São as únicas cartas incendiárias; agora causam 14 e 20 de dano-base e aplicam **Queimadura**.
- **Praia:** Lançador de Água N1 e Canhão de Maré N2. Aplicam **Encharcado**, não fogo nem veneno.

## Elenco e contrapontos

Cada região oferece mais de dez cartas temáticas. As roupas e silhuetas são próprias de Cidade, Deserto e Praia.

- **Rifles:** Recruta e Soldado controlam alvos simples; a ascensão libera o Fuzileiro.
- **Espingardas:** seguram corredores e saltadores perto da linha.
- **Snipers:** lidam com blindados e subchefes, mas exigem munição e proteção.
- **Explosivos:** quebram escudos e grupos; as granadas básicas podem acertar aliados próximos.
- **Elementais e morteiro:** Cidade usa veneno, Deserto usa fogo e Praia usa água; o morteiro continua como impacto explosivo de arco.
- **Engenharia, rádio e medicina:** sustentam munição, economia, vida e remoção de corrosão/atordoamento. A Mecânica de Drones Costeira N1 é terrestre e opera o drone a partir do solo, sem plataforma de madeira.
- **Contenção e minas:** compram tempo contra investidas, mas os saltadores conseguem ultrapassar a primeira linha. Carrinhos de contenção continuam separados visual e mecanicamente das minas que o jogador posiciona como carta.

Os zumbis possuem habilidades efetivas durante a batalha:

- Corredor e Surfista fazem dash inicial.
- Policial, Militar e Cowboy atiram de longe.
- Porta-Escudo e Salva-Vidas reduzem disparos frontais, mas fogo e veneno em área ajudam a quebrar a formação.
- Cuspidor Ácido e Cuspidor de Sal corroem armas e ferem à distância.
- Gritadores aceleram hordas.
- Escavador cava em três etapas visíveis e passa apenas pela primeira tropa bloqueadora.
- Ladrão rouba suprimentos e pode ser clicado.
- Curandeiro recupera aliados e pode reanimar um infectado.
- Parasita e Mutantes atordoam ou desabilitam as defesas.
- Chefes aplicam eventos de campo, invocam aliados, aceleram a horda, soltam névoa ácida, ondas ou abalos.

## Animações e efeitos

Os zumbis têm animação de caminhada, balanço, passo com poeira/respingo, dash, salto em arco, escavação em três etapas (entrar, túnel visível e emergir), rotação de atordoamento, Queimadura, Envenenado, corrosão, barras de vida, morte com partículas e efeitos de habilidades. Tiros agora criam clarões e partículas de boca de arma; veneno, granadas, morteiros, chamas, torpedos, ácido, impactos, cura, Núcleos e os carrinhos-bomba também possuem efeitos em tempo real.

O cenário não usa quadrados verdes coloridos: a área de posicionamento acompanha o cenário pintado. Uma borda fina só aparece sob o mouse para indicar o ponto de instalação; na Praia, a água recebe um brilho discreto.

## Tela de carregamento

Antes de liberar o menu, o jogo abre uma tela de carregamento real e coloca em memória a **ilustração Beta 3 enviada para o carregamento**, a arte do menu, os três cenários, os **nove atlases** de personagens (N1, N2 e zumbis por região), as quatro contenções de terreno, as cinco minas independentes, a Mecânica de Drones N1, o Atirador de Lancha, os retratos exclusivos de carta, os retratos individuais do Saltador e Rastejante e a nova dupla urbana de veneno — **37 recursos** no total. Assim, a mudança de tela e a entrada na missão não precisam carregar imagens pesadas no meio da partida.

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
