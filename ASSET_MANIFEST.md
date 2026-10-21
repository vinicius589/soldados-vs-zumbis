# Manifesto de artes v7

Todas as imagens utilizadas pela Reconstrução v7 foram geradas como ilustrações originais para este projeto. Elas não são cópias nem arquivos extraídos de jogos de terceiros.

## Cenários

| Arquivo | Direção do prompt |
| --- | --- |
| assets/v7/city_grounded.png | Campo urbano de quarentena em 16:9 visto de cima, com arena contínua de asfalto, cinco faixas horizontais apoiadas no chão, posto militar nas bordas e contaminação à direita; sem céu no terreno, grade, texto ou personagens. |
| assets/v7/desert.png | Campo de batalha de deserto em 16:9, estrada de terra entre dunas e pirâmides, expedição à esquerda e tempestade mágica à direita; sem grade, texto ou personagens. |
| assets/v7/beach_grounded.png | Campo costeiro noturno em 16:9 visto de cima, com três faixas superiores de água e duas inferiores de areia, posto de guarda-costeira e caverna restritos às bordas; sem horizonte no terreno, grade, texto ou personagens. |
| assets/v7/menu.png | Ilustração de menu épica em 16:9 para Soldados vs Zumbis, unindo Cidade, Deserto e Praia, com espaço limpo à esquerda para menu e sem logotipo/texto embutido. |

## Atlases de personagens

Cada atlas tem grade 4 por 3, fundo transparente e estética de ilustração militar 2.5D consistente.

| Arquivo | Direção do prompt |
| --- | --- |
| assets/v7/city_soldiers_atlas.png | Doze defensores urbanos: recruta, M16, fuzileiro, escopeta, sniper, granadeiro, engenheiro com drone, rádio, médica, lança-chamas hazmat, barreira e mina. |
| assets/v7/city_zombies_atlas.png | Doze ameaças urbanas: caminhante, corredor, cone, policial, militar, escudo, cuspidor ácido, divisor, gritador, saltador, bruto e chefe tóxico. |
| assets/v7/desert_soldiers_atlas.png | Doze defensores de expedição: batedores, rifleiros de areia, escopeta, sniper, morteiro, granadeiro, engenharia, rádio solar, médica, lança-chamas e contenção. |
| assets/v7/desert_zombies_atlas.png | Doze zumbis de ruína: explorador, múmia rastejante, escavador, ladrão mágico, curandeiro, parasita, mutante, faraó de escudo, cuspidor, feral, necromante e colosso. |
| assets/v7/beach_soldiers_atlas.png | Doze defensores costeiros: guarda-costa, fuzileiro anfíbio, escopeta, sniper, lancha, submarino, arpoador, engenheiro de píer, rádio, médica e boia/mina. |
| assets/v7/beach_zombies_atlas.png | Doze zumbis da maré: turista de boia, surfista, salva-vidas de escudo, mergulhador, caçador, cowboy costeiro, cuspidor salino, gritador, nadador, bruto, caçador abissal e leviatã. |

## Uso no jogo

A tela de carregamento prepara as quatro artes de tela e os seis atlases antes de liberar o menu. O jogo usa apenas os arquivos listados em assets/v7 durante a execução. As animações de zumbi e os efeitos de tiro, ácido, fogo, explosão, cura e ascensão são produzidos em tempo real por Pygame sobre essas artes.
