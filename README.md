# Soldados vs Zumbis — Campanha Cidade, Deserto e Praia

**Soldados vs Zumbis** é um tower defense militar original feito em Pygame. Monte oito cartas para cada operação, defenda um cenário integrado ao terreno e sobreviva à campanha de três regiões. Não há tabuleiro de quadrados verdes nem bônus genéricos antes da partida: as escolhas, os chefes, as cartas e a colocação determinam o resultado.

## Como executar

No Windows, extraia o ZIP e dê duplo clique em `executar.bat`.

Também é possível abrir um terminal dentro da pasta do jogo e executar:

```powershell
python -m pip install -r requirements.txt
python main.py
```

É necessário Python 3.10 ou superior e `pygame-ce==2.5.8`.

Ao abrir, o jogo exibe uma tela de carregamento real e depois o menu principal. As opções são **Jogar**, **Como jogar**, **Informações: Soldados**, **Informações: Zumbis** e **Sair**. O progresso das regiões é salvo automaticamente em `campaign_progress.json`.

## Abertura, carregamento e arquivos táticos

A abertura não é apenas uma barra decorativa: a janela aparece primeiro e prepara cada recurso visual em pequenos blocos. A partida só é liberada depois de carregar cenários, terrenos, soldados, zumbis, props, efeitos e camadas jogáveis para a memória. Isso evita carregamentos inesperados no meio da operação.

O menu foi recriado com uma arte de abertura urbana original e traz dois arquivos navegáveis:

- **Informações: Soldados:** cada ficha apresenta retrato, tipo de combatente, ataque, poder, emprego tático e dados de custo/vida/dano.
- **Informações: Zumbis:** cada ficha apresenta retrato, família de ameaça, ataque, poder especial, resposta tática e dados de vida/velocidade/dano.

Use os botões **< Anterior** e **Próxima >** ou as setas esquerda/direita para trocar de página. Clique em qualquer retrato para abrir a ficha detalhada.

## Campanha: 3 regiões × 15 ondas

As operações são desbloqueadas em sequência e cada uma possui exatamente **15 ondas**. As ondas 1–4 ensinam a defesa; a pressão cresce nos blocos seguintes; e as ondas 5, 10 e 15 encerram cada ato com um chefe.

| Região | Terreno jogável | Chefes nas ondas 5, 10 e 15 |
| --- | --- | --- |
| **Cidade** | Avenida rachada alinhada à perspectiva da cidade | Demolidor de Asfalto, Comandante da Horda, Colosso da Quarentena |
| **Deserto** | Estrada de terra entre dunas, ruínas e pirâmides | Mandíbula das Dunas, Oráculo Enterrado, Titã das Pirâmides |
| **Praia** | Faixa de areia, enseada, píer e três linhas de maré | Bruto da Maré Negra, Capitão Afogado, Leviatã da Ressaca |

Os pontos de posicionamento continuam precisos, com cinco linhas e nove posições, mas não são desenhados como uma grade artificial. Na Cidade, cada linha acompanha a largura real da avenida; no Deserto, a luta ocupa a trilha de terra; e na Praia, as três linhas do meio são água rasa animada.

## Chefes, Medalhas e evolução real

Não há bônus genéricos escondidos antes da partida. A evolução é mostrada dentro da própria operação.

- Todo chefe possui multiplicador próprio de vida, velocidade, dano e armadura; portanto, o chefe não é apenas um zumbi comum com nome diferente.
- Ao derrotar um chefe, o jogador recebe **Medalhas** e uma pequena recompensa de SUP. O total de Medalhas é mostrado no HUD.
- A carta **Instrutor Tático** é a promoção concreta: posicionada perto de aliados, ela consome uma Medalha e promove um defensor para o próximo nível.
- O **Recruta de Campo** é a evolução mais clara: começa barato, atira devagar e só alcança cerca de dois espaços. Nas patentes seguintes ganha vida, dano, recarga e alcance.
- Outros combatentes elegíveis também podem receber promoção. As estrelas douradas acima da barra de vida mostram a patente obtida em campo.

### Poderes dos chefes e debuffs

- **Pisoteio:** causa impacto e atordoa a linha atacada.
- **Grito de guerra:** dá aceleração temporária aos zumbis próximos.
- **Névoa corrosiva:** envenena os defensores da linha.
- **Tempestade de areia:** atordoa o destacamento por um instante.
- **Ritual:** invoca lacaios do próprio ambiente.
- **Abalo sísmico:** causa dano e atordoamento em larga escala.
- **Onda de choque:** aplica impacto e atordoamento na linha costeira.

## Cartas novas e mecânicas de linha

Cada cenário disponibiliza muito mais de dez cartas, mas o jogador leva apenas oito para a operação. As três novas cartas estão presentes nas três regiões, com nomes e roupas adequados ao local:

- **Recruta da Avenida / Batedor Novato / Fuzileiro Novato:** combatente inicial barato de curto alcance, feito para evoluir com Medalhas.
- **Instrutor de Quarentena / de Expedição / Naval:** converte Medalhas em promoções reais para aliados próximos.
- **Vanguardista Urbano / do Comboio / Costeiro:** veículo de blindagem muito alta, dano muito baixo e alcance mínimo. Seu arado desacelera zumbis à frente: ele segura a linha, não substitui o esquadrão inteiro.

O **Engenheiro** tem uma construção própria:

1. Ao ser posicionado com a célula frontal livre, ele implanta uma **Torreta de Engenheiro** uma posição à frente.
2. A torreta atira automaticamente e continua sendo reparada pelo dono.
3. Selecione novamente a carta do Engenheiro e clique na torreta para recolhê-la, removê-la do mapa e recuperar 30 SUP.
4. Se o Engenheiro for eliminado, sua torreta desliga; ela não vira uma unidade permanente grátis.

As demais funções continuam mecânicas, não apenas textos de carta: General dá aura próxima; Sniper e Rambo perfuram; Bombardeiro, Morteiro e Submarino explodem em área; Lança-Chamas e Escopeteiro controlam curta distância; Drone busca alvos em qualquer linha; rádios geram SUP por intervalos; Minas e Bomba de Água explodem na aproximação; a Ferramenta Médica trata um aliado.

## Economia e equilíbrio

- SUP inicial: **165** na Cidade, **175** no Deserto e **185** na Praia.
- Caixas manuais: **8–16 SUP**, com intervalos espaçados.
- Batedor de Suprimentos: **45 SUP**, +3 SUP a cada 4 s.
- Operador de Rádio: **85 SUP**, +7 SUP a cada 6 s.
- Torre de Rádio: **150 SUP**, +15 SUP a cada 5 s.
- Central de Comando: **295 SUP**, +26 SUP a cada 3,8 s.

Unidades explosivas, heróis e veículos têm custos, recargas e limites próprios. Bombardeiros, por exemplo, não podem preencher uma única linha. O Vanguardista tem vida alta justamente porque seu dano é baixo; o Instrutor só promove quando um chefe já foi vencido; e o Recruta precisa sobreviver para virar um combatente forte.

## Zumbis por ambiente e habilidades

Cada região tem elenco próprio, além de roupas e ilustrações regionais diretas para o Caminhante. Os sprites não recebem uma faixa azul pintada por cima.

- **Cidade:** Transeunte Infectado, Corredor de Rua, Conehead de Obras, Bandeireiro, Porta-Escudo, Cuspidor de Asfalto, Escavadeira do Metrô e Sirene Humana.
- **Deserto:** Viajante Ressecado, Feral, Sandstalker, Tóxico do Oásis, Cuspidor de Cacto, Necromante das Areias, Escavadeira Sepultada, Divisor das Dunas e Pulador de Ruínas.
- **Praia:** Turista Afogado, Nadador da Maré, Mergulhador Blindado, Salva-Vidas Corrompido, Cuspidor Salino, Doutor da Praia, Sereia Morta e Surfista Feral.

As habilidades afetam a partida: Corredor e Feral correm; Conehead, Blindado e Porta-Escudo absorvem dano; Divisor se divide; Bandeireiro e Gritador aceleram aliados; Cuspidor ataca de longe; Pulador e Escavadeira atravessam uma defesa; Tóxico envenena; Necromante e Doutor curam a horda; Nadador recebe impulso na água.

Os zumbis possuem animação de caminhada, corrida, rastejo, nado, salto, peso de chefe, investida de ataque, sombra dinâmica, poeira, ondulação, garra e efeitos de habilidade. Os chefes recebem escala visual maior, nome, barra de vida e cronômetro de poder.

## Artes originais incluídas

As imagens de interface, cenários, efeitos, props e personagens são arquivos PNG originais do projeto; nenhum ativo de outro jogo foi extraído ou copiado. As novas artes diretas desta versão ficam em:

- `assets/hd/units/recruta_city_v2.png`
- `assets/hd/units/recruta_desert_v2.png`
- `assets/hd/units/recruta_beach_v2.png`
- `assets/hd/units/instrutor_tatico_v2.png`
- `assets/hd/units/vanguardista_v2.png`
- `assets/hd/units/torreta_engenheiro_v2.png`
- `assets/hd/zombies/caminhante_city_v2.png`
- `assets/hd/zombies/caminhante_desert_v2.png`
- `assets/hd/zombies/caminhante_beach_v2.png`

Os cenários integrados estão em `assets/hd/scenes/city.png`, `assets/hd/scenes/desert_v2.png` e `assets/hd/scenes/beach.png`. A identidade visual nova do carregamento e menu está em `assets/hd/ui/abertura_urbana_v6.png`.

## Minas de contenção e derrota

Cada linha tem uma Mina de Contenção na retaguarda. Quando um zumbi alcança uma linha sem defensores, ela explode uma única vez e abre uma cratera. Se outra ameaça cruzar a mesma linha sem mina, surge a tela de **GAME OVER**, com a linha rompida e o número de minas restantes.

## Controles

- Clique em uma carta e depois em uma posição livre do cenário.
- Clique nas caixas de SUP para coletá-las.
- Pressione `E` ou use **Recolher** para retirar uma unidade.
- Selecione a Ferramenta Médica e clique em um aliado para curá-lo.
- Selecione o Engenheiro e clique em uma Torreta de Engenheiro para recolhê-la.
- Botão direito ou `Esc` cancela a carta atual.
- `Espaço` pausa ou retoma a operação.
- Depois de vencer ou perder, use **Tentar novamente** ou **Mapa**.

## Verificação técnica

Para executar o teste sem abrir uma janela:

```powershell
$env:SDL_VIDEODRIVER='dummy'
python smoke_test.py
```

O teste valida o carregamento progressivo de todos os recursos, o bloqueio do menu antes do fim da carga, a abertura das fichas de soldados e zumbis, os três mapas, 15 ondas, chefes nas ondas 5/10/15, Medalhas, promoção, alcance do Recruta, torreta/recolhimento do Engenheiro, economia, água da Praia, progressão de mapa, habilidades de zumbis, minas, Game Over e renderização headless.
