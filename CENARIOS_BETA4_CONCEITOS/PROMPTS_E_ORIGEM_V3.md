# Registro das artes originais — cenários Beta 4 V3 (histórico)

Este arquivo registra decisões antigas para rastreabilidade. A animação de
pirâmide descrita abaixo não pertence mais à versão ativa. A direção atual usa
tempestade de areia volumétrica e está em
`PROMPTS_ENTRADAS_DOS_ZUMBIS_V3.md`.

Todas as imagens abaixo foram geradas especialmente para **Soldados vs
Zumbis**. As versões V1 e V2 foram preservadas; a V3 é a versão preparada para
receber animações separadas.

## Fundos V3

### Nova York — Zona Hélix

- Referência editada: `01_nova_york_zona_helix_v1.png`.
- Saída final: `01_nova_york_zona_helix_v3.png`.
- Direção: preservar quatro pistas, base norte-americana e skyline; remover
  chuva; intensificar vapor radioativo verde, poças e sinalização no lado
  contaminado; manter toda a área jogável livre. A dupla estática da V2 foi
  removida por preenchimento para receber o sprite animado separado.

### Egito — Necrópole de Khepra

- Referência editada: `02_egito_necropole_khepra_v1.png`.
- Saída final: `02_egito_necropole_khepra_v3.png`.
- Direção: preservar pirâmides, base e quatro pistas; retirar a cabeça de
  estátua, pedras e ruínas que obstruíam a quarta linha; reforçar nascer do sol
  e pequenos focos mágicos turquesa fora do tabuleiro. A dupla estática da V2
  foi removida para receber animação.

### Minas Gerais — Cachoeira do Véu Verde

- Referência editada: `03_minas_cachoeira_veu_verde_v1.png`.
- Saída final: `03_minas_cachoeira_veu_verde_v3.png`.
- Direção: preservar terra/água/água/terra e bandeiras; transformar o local em
  área apocalíptica contaminada, com água verde-azulada e óleo, peixes mortos,
  barris, resíduos, mata queimada e base de resgate. A dupla estática da V2 foi
  removida para receber animação.

## Sprite sheets ambientais

### Soldados conversando

- Arquivo bruto: `animacao_ambiental/soldados_conversando_3x6_bruto.png`.
- Arquivo de trabalho: `animacao_ambiental/soldados_conversando_3x6_chroma.png`.
- Grade: três linhas por seis colunas.
- Linha 1: dupla dos Estados Unidos.
- Linha 2: dupla militar moderna do Egito.
- Linha 3: dupla brasileira de resgate.
- Ação: respiração, gesto de mão, resposta, concordância e retorno ao idle.
- O fundo foi corrigido em uma segunda passagem para verde-chroma uniforme; o
  visualizador remove o verde com tolerância sem apagar os uniformes.
- Revisão de uniforme: `soldados_conversando_3x6_chroma_v2.png`. A linha do
  Egito ganhou shemagh, óculos de areia, respirador, polainas, mochila de
  hidratação, bandeira egípcia e emblema Khepra.

### Cachoeira V4 conectada

- Referência editada: `03_minas_cachoeira_veu_verde_v3.png`.
- Saída: `03_minas_cachoeira_veu_verde_v4.png`.
- Os dois canais de água agora chegam diretamente à queda do lado direito,
  sem subida, rampa ou banco de pedras.
- A água da queda e dos canais usa a mesma cor tóxica.
- Peixes, barris, pneus, tábuas, pedras e resíduos foram retirados do interior
  jogável; a sujeira apocalíptica permanece somente nas bordas.

### Mina aquática brasileira

- Arquivo bruto: `animacao_ambiental/mina_aquatica_1x8_bruto.png`.
- Arquivo de trabalho: `animacao_ambiental/mina_aquatica_1x8_chroma.png`.
- Grade: uma linha por oito colunas.
- Sequência: boia dormente, luz de armação, pulso, faísca, explosão inicial,
  coluna d’água, onda de choque e dissipação.
- Restrições: sem ponte, sem plataforma e sem caixa de suprimentos.

## Preparação local

`preparar_cenarios.py` gera cópias V3 em 1280×720 sem deformar a proporção.
`visualizar_cenarios.py` recorta os sprite sheets, remove chroma e controla
toda a troca de quadros por delta time.

## Revisão de simetria e ambientação V5/V6

### Fundos sem bandeira estática

- Nova York V4: `01_nova_york_zona_helix_v4.png`; o tecido parado foi removido
  e o mastro preservado para receber a sequência animada.
- Egito V4: `02_egito_necropole_khepra_v4.png`; o tecido parado foi removido
  e o mastro preservado para receber a sequência animada.
- Minas V5: `03_minas_cachoeira_veu_verde_v5.png`; a geometria foi redesenhada
  com quatro superfícies estritamente horizontais até o lado direito na ordem
  terra/água/água/terra. Os canais foram limpos e igualados à cor da queda.

### Bandeiras animadas

- Bruto: `animacao_ambiental/bandeiras_4x6_bruto.png`.
- Chroma corrigido: `animacao_ambiental/bandeiras_4x6_chroma.png`.
- Grade: quatro linhas por seis colunas — Estados Unidos, Egito, Brasil e Minas.
- Direção: ondulação curta, pivô estável no mastro, sem cenário, texto ou UI.

### Carga terrestre de Minas

- Arquivo: `animacao_ambiental/carga_terrestre_minas_1x8_chroma.png`.
- Grade: uma linha por oito colunas.
- Direção: dispositivo baixo de aço e laranja, antena curta e luz âmbar; ciclo
  de prontidão sem caixa de suprimento, ponte, veículo ou elemento aquático.
- Uso: pistas terrestres 1 e 4; as pistas 2 e 3 continuam com mina aquática.

### Regras técnicas desta revisão

- defesa parada usa início próprio por cenário e linha, acompanhando a borda;
- dupla ambiental dimensionada como figurante e ancorada pelo ponto dos pés;
- não existe sombra artificial sob os personagens ambientais;
- tecidos das bandeiras, névoa, correnteza, cachoeira e luzes são atualizados
  por delta time, sem depender da taxa de quadros do computador.

## Revisão orientada pelas marcações do usuário — V7

- As sombras de contato dos figurantes foram removidas completamente.
- A cidade usa o centro das marcações como pivô: os tratores começam em
  `x=205`, `173`, `128` e `250`. Na linha 4, o ponto foi limitado à primeira
  área livre da rua para não encostar na grade permanente da base.
- Em Minas, as quatro defesas começam em `x=132`, dentro dos quatro pontos
  marcados na imagem do usuário.
- `mina_aquatica_v2_1x8.png`: bomba naval redonda, flutuação, inclinação,
  luz de armação, retração da trava, submersão e ignição.
- `carga_terrestre_minas_v2_1x8.png`: bomba terrestre redonda, antena,
  lâmpada, travas, compressão no solo e ignição.
- O antigo `portal_khepra_1x8.png` foi retirado do visualizador.
- `apice_khepra_1x8.png`: areia física forma um escaravelho e um feixe curto
  sobre a pirâmide, longe das pistas, e depois se dissipa.
- Folhas que chegaram com fundo preto são recortadas em tempo de carregamento
  por componente conectado às bordas; contornos pretos internos são mantidos.
- A cidade normal usa apenas fumaça muito discreta na área contaminada.
- Ao chamar o chefe da cidade, a chuva começa e continua após o aviso. No
  testador, pressionar `B` novamente representa a derrota do chefe e para a
  chuva imediatamente.

### Plataforma física da base de Nova York — V5

- Fundo ativo: `01_nova_york_zona_helix_v5.png`.
- A área apertada atrás da primeira rua foi substituída por um pátio de
  concreto largo, horizontal e fisicamente ligado à base.
- Caminhão, caixas e sacos foram deslocados para o fundo/perímetro.
- O pátio não contém personagens nem sombras pintadas; a dupla animada é
  encaixada separadamente pelo ponto dos pés em `(92, 272)`.
- As quatro pistas, a entrada diagonal, o skyline e a zona contaminada foram
  preservados.

### Metade direita do Egito — V5

- Fundo ativo: `02_egito_necropole_khepra_v5.png`.
- A metade esquerda, incluindo a base aprovada, foi preservada.
- Porta monumental, portal, escadaria e braseiros de pista foram removidos.
- A metade direita agora é deserto aberto com pirâmides e escavação no fundo.
- As quatro estradas seguem horizontalmente até a borda direita, sem estreitar,
  subir, virar escada, desaparecer sob ruína ou receber personagem pintado.
