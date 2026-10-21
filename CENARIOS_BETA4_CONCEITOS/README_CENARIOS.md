# Soldados vs Zumbis — revisão animada dos cenários da Beta 4

## O que já está pronto para avaliação

Os três cenários-base foram recriados do zero em pixel art. A composição mantém
uma faixa lateral de base e sobreviventes à esquerda, região
temática/apocalíptica à direita e quatro faixas contínuas de combate. Eles ainda
não substituem os mapas do jogo principal. A galeria serve para aprovar
enquadramento, proporção, identidade, paleta e animação antes da integração.

**Estado desta revisão:** os três fundos V4 de entrada única estão ativos na
galeria de aprovação. Cada um possui base compacta à esquerda, quatro faixas
contínuas e uma única entrada monumental recuada no extremo direito. Eles não
substituem os mapas do jogo principal antes da aprovação visual.

1. **Nova York — Terminal Hélix-13**: quatro ruas contínuas desembocam em um
   único vão largo do laboratório contaminado; o interior não é mostrado.
2. **Egito — Escavação Hélix de Khepra**: quatro caminhos longos chegam a uma
   entrada egípcia única com o mesmo formato e proporção do vão de Nova York,
   mas com fachada de arenito e duas piras contaminadas. A versão V5 remove o
   fogo fixo do PNG-base: somente os sprites de oito quadros produzem chama.
3. **Minas Gerais — Cachoeira Hélix**: quatro faixas em terra/água/água/terra;
   as duas pistas secas continuam planas até o extremo direito e as duas pistas
   aquáticas encontram a cachoeira, sem exigir subida ou troca de altura.

Abra `..\TESTAR_CENARIOS_BETA4.bat`. Use as setas para trocar de cenário,
`1` a `4` para escolher a linha, `C` para testar a defesa de emergência e
`B` para chamar o chefe e iniciar o clima especial; pressione `B` outra vez
para simular a derrota do chefe e encerrar o clima da região.

As três propostas de movimento para as futuras entradas podem ser comparadas
separadamente em:

- `qa\cidade_sem_fumaca_animada.gif`;
- `qa\piras_egito_animadas.gif`;
- `qa\chefe_egito_nevoa_piras.gif`;
- `qa\cenario_minas_sem_animacao_agua.gif`;
- `qa\chefe_minas_tempestade.gif`;
- `qa\generais_saudacao_regional.gif`;
- `qa\defesas_encerram_no_fim_da_pista.gif`.

Esses GIFs validam ritmo, direção e leitura do VFX sobre os fundos V4. A
história, a composição e os assets pendentes estão especificados
em `DIRECAO_ENTRADAS_V4.md`.

Para abrir a galeria interativa diretamente, execute `VER_ENTRADAS_V4.bat` e
use as setas esquerda/direita para alternar entre os três ambientes.

## Animações já ligadas nesta revisão

### Nova York

- nenhuma camada animada de fumaça ou névoa verde é desenhada na cidade;
- a chuva permanece como efeito exclusivo do chefe de Nova York;
- um general norte-americano presta continência por oito quadros no grande
  corredor superior de piso livre da base, entre a barraca e a mureta, longe
  das caixas e divisórias;
- os pés usam âncora de solo; as sombras artificiais foram removidas;
- trator animado atravessa e limpa a linha selecionada;
- chegada do boss possui escurecimento, pulso vermelho e tremor.

### Egito

- quarta pista inteiramente desobstruída;
- nascer do sol pulsa lentamente;
- uma única entrada larga de arenito repete o formato do laboratório sem
  copiar sua arquitetura industrial;
- duas piras usam oito quadros de chama verde presos exatamente às bocas das
  taças existentes; não há chama solta nas pistas ou nas pedras;
- fora do alerta, as chamas usam uma caixa-base de `54×84`; durante os 3,2 s
  de aproximação elas crescem suavemente até `84×132`, sempre a partir da taça;
- a pira superior aplica escala de perspectiva de 82% e possui âncora própria,
  evitando que a chama distante pareça maior ou fique atrás da coluna;
- o fundo `02_egito_escavacao_helix_piras_apagadas_v5.png` contém as duas taças
  apagadas; não existe mais um segundo fogo estático por baixo da animação;
- fora da luta de chefe não existe névoa animada no Egito; durante a chegada e
  enquanto o chefe está ativo, ela nasce dentro da entrada e some na derrota;
- não há sarcófago no conjunto ativo;
- um general egípcio presta continência na área vazia da base, com uniforme de
  comando para clima quente e identificação própria;
- drone animado cruza a linha atirando para a direita;
- chegada do boss possui escurecimento, pulso vermelho e tremor.

### Minas Gerais

- quatro superfícies chegam até o limite direito: terra, água, água e terra;
  a queda foi deslocada para o fundo e não corta a quarta faixa;
- os canais jogáveis estão limpos e usam exatamente a paleta tóxica da queda;
- cachoeira, espuma e correnteza permanecem somente na pintura aprovada do
  fundo; todas as antigas camadas animadas de água foram removidas;
- o chefe de Minas escurece o ambiente e provoca clarões distantes de
  tempestade, sem desenhar riscos ou efeitos sobre a água;
- uma general brasileira presta continência na área vazia da base, com traje
  impermeável de resposta a desastre e identificação própria;
- linhas de água usam mina aquática; linhas de terra usam carga terrestre
  regional, ambas animadas no começo real e no centro vertical da pista;
- ao acionar a defesa, a detonação começa em 0,12 s, cada quadro toca uma única
  vez e a cadeia percorre somente a linha, desaparecendo ao terminar;
- chegada do boss possui escurecimento, pulso vermelho e tremor.

## Regras rígidas para a integração

- nenhuma faixa pode mudar de altura durante a partida;
- pivô dos personagens fica no centro da faixa e na linha real de contato;
- elementos de fundo usam pivô nos pés, sem sombra artificial;
- soldados atacam para a direita; zumbis e bosses atacam para a esquerda;
- animações ambientais são camadas separadas do fundo;
- trator, drone, projéteis e explosões desaparecem no fim útil da faixa, antes
  da entrada inimiga; nenhum efeito atravessa a decoração do cenário;
- o boss não fica desenhado permanentemente no cenário;
- nenhuma decoração pode bloquear a leitura das quatro faixas;
- não existem bandeiras soltas nos cenários; os generais usam pequenos patches
  nacionais de Estados Unidos, Egito e Brasil no uniforme;
- as artes não usam ativos de terceiros.
