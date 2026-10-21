# Linha de base da refatoração

Este relatório registra o ponto de partida mensurável para a próxima fase de melhoria. A separação de módulos que já existe é útil, mas **mover código para outro arquivo não prova que o projeto ficou menor**. Por isso, os números abaixo distinguem transferência de responsabilidade de redução líquida.

## Estado conferido em 21/10/2026

### Snapshot executável da Beta 4 preservada

Na pasta histórica `betas/beta-4/`:

- 656 arquivos de todos os tipos.
- 65 arquivos Python, somando 967.844 bytes de conteúdo Python no Git tree.
- O `main.py` histórico tinha 362.384 bytes.
- A pasta inclui código do jogo, testes, scripts de QA, protótipos e ferramentas de produção. Assim, o total de 65 arquivos Python não é uma medida pura do runtime.

### Base modular candidata

Na branch `migracao/base-jogavel`:

- 311 entradas no Git tree, das quais 23 arquivos Python.
- 572.296 bytes de conteúdo Python no tree, incluindo código do jogo, testes e scripts de apoio.
- Os módulos principais ainda são extensos: `src/game/runtime.py` tem 3.373 linhas; `src/game/presentation.py`, 3.403; e `src/game/battle.py`, 2.780.
- Os 254 caminhos de assets presentes na pasta executável histórica da Beta 4 também aparecem na base modular. Isso confirma a correspondência dos caminhos, não substitui a validação visual de cada recurso dentro do jogo.

**Não é correto declarar uma redução percentual comparando 967.844 bytes com 572.296 bytes.** Os diretórios não têm o mesmo escopo: o histórico contém protótipos, ferramentas, QA e testes adicionais que não estão todos na base modular. Essa diferença será tratada como uma decisão de escopo, não como uma economia de código já comprovada.

## O que os commits de modularização realmente fizeram

Os commits abaixo, existentes na história de `migracao/base-jogavel`, foram conferidos nas estatísticas do GitHub:

| Commit | Resumo | Linhas adicionadas | Linhas removidas |
| --- | --- | ---: | ---: |
| `a6787fb0be` | Separar métodos de interface e desenho | 3.406 | 0 |
| `322931e6b5` | Separar apresentação e remover método duplicado | 3 | 3.401 |
| `7ffcff3102` | Dividir runtime em batalha, entidades e recursos | 15 | 3.353 |
| `067681f964` | Criar módulo de batalha | 2.779 | 0 |
| `b5e6faec15` | Separar modelos de unidades e projéteis | 227 | 0 |
| `b317549542` | Separar carregamento de recursos | 346 | 0 |
| `355e9d46e9` | Declarar dependências dos modelos | 19 | 1 |
| `e2b9ca2799` | Simplificar importação de símbolos da interface | 1 | 5 |
| **Total desses commits** | **Série de extração de módulos** | **6.796** | **6.760** |

O saldo agregado desses commits é **36 linhas a mais**, não uma redução líquida. Isso é compatível com uma refatoração de extração: grande parte do código foi movida do runtime para módulos de apresentação, batalha, entidades e recursos. A redução efetiva deve ser medida separadamente e não será atribuída artificialmente a essa série.

## Próxima fase: redução líquida e teste de regressão

Cada branch `refactor/*` futura deve registrar:

1. O problema concreto: duplicação, acoplamento excessivo, função longa ou estado mantido em mais de um lugar.
2. O escopo exato das linhas/módulos medidos antes e depois, sem contar assets binários nem somar código movido como se fosse removido.
3. A redução líquida no mesmo escopo, acompanhada de clareza das responsabilidades e número de testes.
4. Os testes automatizados executados e o caminho do jogo testado manualmente.
5. A lista de comportamentos e assets que precisam continuar funcionando.

O primeiro alvo para investigação é o acoplamento entre os módulos atuais: `battle.py`, `presentation.py` e `assets.py` importam símbolos da grande camada `runtime.py`. Antes de separar mais coisas, é necessário inventariar as dependências e escolher uma mudança pequena, verificável e com teste. Não será removida funcionalidade só para produzir uma redução de linhas.

## Limitações atuais

- A checagem do acervo confirma caminhos e existência dos arquivos, não a qualidade visual de todas as animações.
- A criação dos oito pacotes históricos verificou a presença de `main.py` e `executar.bat` e gerou SHA-256; não executou uma campanha gráfica completa no Windows.
- A redução líquida futura só será afirmada depois de um diff comparável e de testes correspondentes.
