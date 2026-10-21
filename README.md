# Soldados vs Zumbis — Beta 4

Protótipo 2D de Tower Defense feito com Pygame e apresentação opcional por PyOpenGL. Esta reconstrução integra os três cenários aprovados, quatro faixas por mapa, animações quadro a quadro controladas por `dt` e elencos regionais completos para a campanha de 12 ondas.

## Executar

Dê dois cliques em `executar.bat`. Na primeira abertura, o arquivo instala automaticamente as dependências de `requirements.txt` e inicia o jogo.

Para testar o recorte integrado, use `TESTAR_INTEGRACAO_BETA4.bat`. Ele também
abre primeiro o menu principal; clique em **INICIAR**, escolha a dificuldade e
o mapa. Nenhum executável pula direto para o mapa ou para a partida.

## Escopo desta integração

A Beta 4 contém 26 cartas ativas: oito de Nova York, oito do Egito e dez da
Cachoeira. A missão permite escolher até três por vez. A campanha tem doze
ondas por mapa, incluindo seis zumbis comuns, três subchefes e três chefes
regionais. O ciclo de cada ato é: duas ondas comuns, uma de subchefe e uma de
chefe.

| Mapa | Facção | Cartas | Ameaça básica | Proteção inicial |
|---|---|---:|---|---|
| Nova York | Polícia dos Estados Unidos | 8 | Infectado Urbano | Trator de contenção |
| Egito | Forças Armadas do Egito | 8 | Desperto de Khepra | Drone de ataque |
| Cachoeira | Marinha do Brasil | 10 | Afogado da Cachoeira | Mina aquática ou carga terrestre |

O Xerife usa uma **Desert Eagle**, o Pistoleiro do Deserto usa uma **Magnum
.357** e o Marinheiro usa uma **Glock 19**. Os três alcançam exatamente dois
blocos, recarregam rapidamente e precisam de uma linha de tiro livre: não
disparam através de outra defesa. O Marinheiro é terrestre; somente Barco e
Submarino ocupam os canais como defesas. Surfista, Mergulhador, Pescador da
Praga e as ameaças aquáticas pesadas usam as faixas de água.

Soldados e zumbis usam uma escala física fixa para toda a folha de animação.
Uma pose inclinada, agachada ou atingida nunca é ampliada para compensar a
altura aparente; isso impede o corpo de crescer, encolher ou perder os pés ao
trocar de quadro.

As folhas novas ficam em `assets/beta4_producao`. Cada soldado contém caminhada, espera, disparo, recarga e dano; cada zumbi contém locomoção, espera, ataque, dano e ação especial. Todas as poses são normalizadas para a mesma caixa e o mesmo eixo dos pés, evitando mudança de tamanho e invasão de faixa durante a troca de estado.

Cada carta integrada tem arte, animações, história, função tática e necessidade
mecânica próprias. Cada região também possui doze inimigos visualmente
distintos, sem reutilizar o mesmo corpo para comuns, subchefes e chefes.

## Cenários e contenções

- Os três mapas têm quatro faixas com centros medidos diretamente na pintura.
- Tropas, zumbis, tratores, drones, minas e cargas usam o mesmo centro de faixa.
- O trator e o drone desaparecem antes de alcançar a entrada dos zumbis.
- Em Minas Gerais, a primeira colisão detona imediatamente a proteção e limpa toda a faixa com uma cadeia de explosões.
- Os infectados básicos da Cachoeira ocupam apenas as duas trilhas terrestres.
- Os infectados de cada mapa surgem visualmente de dentro da entrada direita e
  ganham opacidade ao atravessar o portão, a necrópole ou a cachoeira.
- As piras do Egito têm fogo animado e aumentam quando a horda começa.
- A chuva da cidade e a tempestade da cachoeira ficam reservadas aos futuros encontros de chefe.
- Nova York usa um tenente policial de comando, com animação de pegar o apito,
  assobiar e exibir `FIIIU!` somente durante o som; não há general comandando a polícia.
- O tenente da cidade e o general militar do Egito ficam recuados no piso livre da base,
  fora das pistas e de qualquer caixa.
- Minas usa um marinheiro praça com uniforme azul, gola de marinheiro e chapéu branco;
  o personagem ambiental usa uniforme azul-marinho de oficial com quepe e continência.

## Menu

- **Iniciar**: dificuldade, mapa e grade compacta de cartas. A grade mostra
  Vida, Dano e Recarga; o botão **Detalhes** abre história, função e necessidade.
- **Personagens**: carrossel individual por mapa, com abas Soldado/Zumbi e
  navegação Anterior/Próximo.
- **História do jogo**: prólogo em três páginas com personagens em primeiro
  plano, ações próprias, caixas de narração, balões de fala com cauda e
  onomatopeias; não são recortes vazios do mapa.
- **Configurações**: alternância entre Mouse e Teclado, liga/desliga do áudio e
  ajuste de volume. O Mouse continua sendo o padrão.
- **Como jogar**: instruções atualizadas para a integração mínima.

Não há progressão de nível, promoção de carta ou Núcleo N3 nesta reconstrução.

## Controles

- Mouse: selecionar carta, posicionar tropa e usar botões.
- Teclado opcional: WASD ou setas movem o cursor; `Q`/`E` trocam a carta;
  `1`–`8` selecionam diretamente; `Enter`, `F` ou `Espaço` posicionam;
  `R` alterna remoção; `N` ou `Tab` chama a próxima onda.
- `1`: selecionar a carta disponível.
- `Espaço`: iniciar a próxima onda.
- `P`: pausar ou continuar.
- `R`: ativar ou desativar a remoção no Médio e no Difícil.
- `Esc`: voltar ao menu inicial durante a partida.

No Fácil, a remoção de tropas permanece desativada.

## Dificuldade

- **Fácil**: 240 suprimentos; infectados com 82% da vida e 80% do dano; 84% da densidade; apoio gera 18% mais e 12% mais rápido.
- **Médio**: 150 suprimentos e todos os multiplicadores em 100%; é a referência oficial do balanceamento.
- **Difícil**: 105 suprimentos; infectados com 132% da vida e 128% do dano; 124% da densidade; apoio gera 22% menos e 18% mais devagar.

O escalonamento é monotônico: do Fácil ao Difícil, recurso e dano aliado diminuem,
enquanto vida, dano, quantidade e frequência dos invasores aumentam.

## Regras atuais de combate

- Soldados simples detectam e atiram somente para a frente por até 2 blocos; avançados, por até 3.
- A primeira coluna fica bloqueada enquanto o trator, drone ou bomba da faixa ainda existe.
- Todo zumbi sofre uma pausa curta ao tomar dano, exceto o Corredor.
- O Corredor não usa dash: corre em velocidade constante, não atravessa a hitbox e causa dano dobrado apenas no primeiro ataque.
- O Rastejador é lento e resistente; se alcançar uma tropa de Classe 1 ou 2, a mordida é letal.
- O zumbi padrão perde o duelo individual contra o defensor básico regional, mas cinco atacando juntos vencem a linha.
- Explosivos sofrem redução forte contra elites e todos os chefes; RPG, morteiro
  e granada não formam mais uma composição universal.
- Imunidades exibem `IMUNE` até a carta-counter romper a defesa por cinco segundos.
- A Tropa de Choque abre a guarda dos Brutos urbanos, o Guardião de Lâminas
  neutraliza o Zumbi de Lâmina e o Sonar revela o Mergulhador.
- Tiros de precisão, química, fogo, água e torpedos possuem canais próprios;
  cada um resolve uma proteção diferente.

## Validação

```powershell
python -m unittest discover -s . -p "test_*.py"
python smoke_test.py
python exportar_qa_producao.py
```

`exportar_qa_producao.py` produz capturas reais dos três mapas, do menu, dos personagens,
das páginas da história e o GIF `tenente_cidade_apito.gif` em
`visual_qa_beta4/producao_regional`.

## Arquivos principais

- `main.py`: fluxo do jogo, combate, menus e integração regional.
- `animation2d.py`: infraestrutura genérica de animação por `dt`, estado, câmera e VFX.
- `beta4_production_animations.py`: recorte e normalização das seis folhas novas.
- `beta4_scenario_runtime.py`: comando regional, piras, clima e proteções de faixa.
- `opengl_presenter.py`: composição opcional pela GPU, com fallback seguro em Pygame.
- `smoke_test.py`: validação funcional headless da produção atual.
