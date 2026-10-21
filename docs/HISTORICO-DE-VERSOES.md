# Catálogo histórico de versões

Este índice separa **o pacote que a pessoa baixa**, **o código que ela consulta** e **o que foi realmente preservado no histórico**. Os snapshots abaixo foram montados a partir das pastas do acervo publicado; cada snapshot tem um novo commit de arquivo nesta migração. Eles não são apresentados como se fossem os commits originais de cada versão.

## Como interpretar os nomes

- `arquivo/*` é uma tag que identifica o snapshot histórico da pasta preservada.
- `snapshot/*` é a branch independente cuja raiz contém os arquivos daquela etapa, sem obrigar a pessoa a procurar a versão dentro do acervo inteiro.
- A [página de Releases](https://github.com/vinicius589/soldados-vs-zumbis/releases) contém um ZIP individual e seu checksum SHA-256 para cada etapa empacotada. As Releases históricas foram criadas como **rascunhos**: precisam de revisão e teste antes de publicação pública.
- O acervo completo original continua preservado em [historico/alfas-e-betas](https://github.com/vinicius589/soldados-vs-zumbis/tree/historico/alfas-e-betas) e no [repositório antigo](https://github.com/vinicius589/soldados-vs-zumbis-beta-4).

## Alfas preservadas

| Etapa | Tag do snapshot | Branch independente | Arquivo da Release |
| --- | --- | --- | --- |
| Alfa inicial — primeira etapa preservada com arte | [arquivo/alfa-inicial](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/alfa-inicial) | [snapshot/alfa-inicial](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/alfa-inicial) | `soldados-vs-zumbis-alfa-inicial.zip` |
| Alfa da Beta 2 — arenas e estabilidade | [arquivo/alfa-beta-2](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/alfa-beta-2) | [snapshot/alfa-beta-2](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/alfa-beta-2) | `soldados-vs-zumbis-alfa-beta-2.zip` |
| Alfa da Beta 3 — v7.4, elenco e promoção | [arquivo/alfa-beta-3-v7.4](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/alfa-beta-3-v7.4) | [snapshot/alfa-beta-3-v7-4](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/alfa-beta-3-v7-4) | `soldados-vs-zumbis-alfa-beta-3-v7-4.zip` |
| Alfa da Beta 3 — v7.5, minas e equilíbrio | [arquivo/alfa-beta-3-v7.5](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/alfa-beta-3-v7.5) | [snapshot/alfa-beta-3-v7-5](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/alfa-beta-3-v7-5) | `soldados-vs-zumbis-alfa-beta-3-v7-5.zip` |
| Alfa de revisão da Beta 4 | [arquivo/alfa-beta-4](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/alfa-beta-4) | [snapshot/alfa-beta-4](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/alfa-beta-4) | `soldados-vs-zumbis-alfa-beta-4.zip` |

## Betas preservadas

| Etapa | Tag do snapshot | Branch independente | Arquivo da Release |
| --- | --- | --- | --- |
| Beta 1 original | — | [historico/beta-1](https://github.com/vinicius589/soldados-vs-zumbis/tree/historico/beta-1) | **Não há executável original conhecido.** O código da primeira versão de formas simples não foi localizado; não vamos criar um substituto e apresentá-lo como se fosse o original. |
| Beta 2 — menu e carregamento | [arquivo/beta-2](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/beta-2) | [snapshot/beta-2](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/beta-2) | `soldados-vs-zumbis-beta-2.zip` |
| Beta 3 — unidades regionais e dificuldades | [arquivo/beta-3](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/beta-3) | [snapshot/beta-3](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/beta-3) | `soldados-vs-zumbis-beta-3.zip` |
| Beta 4 — campanha regional de 12 ondas | [arquivo/beta-4](https://github.com/vinicius589/soldados-vs-zumbis/tree/arquivo/beta-4) | [snapshot/beta-4](https://github.com/vinicius589/soldados-vs-zumbis/tree/snapshot/beta-4) | `soldados-vs-zumbis-beta-4.zip` |

## O que significam os downloads

Cada pacote ZIP reúne apenas os arquivos da pasta correspondente, incluindo `main.py`, `executar.bat`, `requirements.txt` e os recursos daquela versão. O arquivo `.sha256` permite conferir a integridade do ZIP baixado.

Para executar uma versão no Windows, baixe o ZIP indicado na Release correspondente, extraia a pasta inteira e abra `executar.bat). Consulte o README e o `requirements.txt` dentro do pacote para os requisitos próprios daquela etapa. Não misture assets ou código de outra versão.

Para alterar o projeto, consulte o [guia de instalação, execução e publicação](GUIA-DEV-E-RELEASES.md) e o [guia de branches, commits, tags e versões](BRANCHING.md). As Releases históricas permanecem em rascunho até passar por uma revisão dos pacotes e testes em ambiente adequado. A criação de um pacote e seu checksum não prova, sozinha, que a campanha inteira foi validada graficamente.

## Proveniência e limites

Os nomes, diferenças e funções das etapas foram extraídos das notas preservadas em `alphas/`, `betas/` e `material-bruto/textos/`. Algumas pastas Alfa são revisões de reconstrução, não patches mínimos aplicados linha a linha sobre uma Beta. Por isso, ao comparar código, considere a proveniência e não atribua cada diferença a uma única correção sem olhar o histórico e o conteúdo.

As tags originais que já existiam na origem também foram importadas separadamente quando as permissões do GitHub permitiram. A cópia das tags originais e os snapshots de pasta cumprem funções diferentes:
- tag original: preserva o commit histórico existente;
- tag `arquivo/*`: oferece um estado navegável e isolado da pasta específica;
- Release: reúne o ZIP e as instruções para baixar e experimentar a etapa.
