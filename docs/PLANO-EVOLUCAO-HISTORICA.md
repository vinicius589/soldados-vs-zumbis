# Plano de preservação e evolução

## Repositórios

- Origem histórica: [soldados-vs-zumbis-beta-4](https://github.com/vinicius589/soldados-vs-zumbis-beta-4)
- Destino: [soldados-vs-zumbis](https://github.com/vinicius589/soldados-vs-zumbis)
- Branch de preparação desta etapa: `chore/importar-historico-legado`
- Base modular já disponível para revisão: `migracao/base-jogavel`

## O que foi conferido

- A branch histórica `historico/alfas-e-betas` da origem tem 1.546 entradas e reúne `alphas/`, `betas/` e `material-bruto/`.
- A branch `historico/beta-1` conserva uma versão histórica enxuta; nela, `src/game.py` é um arquivo de aproximadamente 76 KB. Isso serve como referência para comparar a evolução da organização do código, mas não prova por si só que todas as funcionalidades das versões posteriores existiam ali.
- Na origem, `jogo` e `beta5-dev` apontam atualmente para o mesmo commit (`ee2655cfc1683ec285cd9746ebca8eac0ddf2d94`). Portanto, os nomes das branches não representam dois estados de código diferentes nesse ponto do histórico.
- O destino tem uma `main` inicial com apenas o README. A branch `migracao/base-jogavel` contém 311 entradas e commits de refatoração, incluindo separação de runtime, combate, entidades e carregamento de recursos.
- O acervo histórico pode conter arquivos de arte representados por ponteiros Git LFS em alguns snapshots. Após a importação, será necessário conferir quais pacotes realmente contêm os binários e manter os releases originais como fonte de referência.

## Como vamos organizar a evolução

### Etapa 1 — Preservar as referências reais

Importar os commits, branches históricas e tags do repositório antigo sem reescrever seus hashes. A importação cria referências separadas; ela não altera a `main` nem integra automaticamente os projetos.

### Etapa 2 — Fixar a base jogável

Usar `migracao/base-jogavel` como candidata de trabalho, comparar seu conteúdo com a Beta 4 original e conferir se sprites, áudio, mapas, animações, regras de combate e campanha continuam presentes. A base só será promovida depois da revisão e dos testes.

### Etapa 3 — Evoluir por mudanças verificáveis

Criar branches curtas e focadas, por exemplo:

- `fix/<assunto>`: corrigir comportamento sem acrescentar funcionalidades não relacionadas.
- `refactor/<assunto>`: reduzir duplicação e complexidade preservando o comportamento.
- `feat/<assunto>`: acrescentar recurso novo depois que a base estiver validada.
- `test/<assunto>`: aumentar cobertura para regras e regressões.

Cada mudança deve ter commits próprios, testes pertinentes e comparação com a base anterior. Não vamos criar uma branch artificial para cada número de versão: versões publicadas devem ser marcadas com tags, enquanto branches representam linhas reais de trabalho.

### Etapa 4 — Medir redução e qualidade

Antes e depois de cada refatoração, registrar:
- quantidade de arquivos Python e linhas de código Python (sem misturar imagens e áudio);
- duplicações removidas e responsabilidades separadas;
- testes executados e resultado;
- recursos do jogo conferidos;
- diferenças de comportamento conhecidas.

Linhas removidas não são, sozinhas, um critério de sucesso. A meta é código menor ou mais simples quando isso não reduz recursos, legibilidade ou cobertura de testes.

## Regras de segurança para a migração

1. Não fazer push direto na `main`.
2. Não alterar os commits históricos nem inventar uma Beta que não tenha referência verificável.
3. Não substituir os assets originais por artes genéricas.
4. Não declarar a compilação ou a execução gráfica como testada sem evidência de teste.
5. Só abrir a integração principal depois de validar a base, os testes e o pacote jogável.

## Próximo marco

Concluir a importação das referências e comparar os snapshots históricos com `migracao/base-jogavel`. Com essa comparação será possível definir uma sequência fiel de marcos e calcular a redução real de código nas refatorações futuras.


## Situação da importação no novo repositório

Conferência em 21/10/2026:

- Importadas as branches históricas `historico/alfas-e-betas` e `historico/beta-1`.
- Importadas as tags de origem `beta-4.0`, `v1.2.0`, `historico-corrigido-2026-09-30` e `pacote-completo-2026-09-30`, preservando seus commits originais.
- A tentativa de importar `v1.3.0`, `v1.3.1`, `jogo` e `beta5-dev` foi bloqueada pelo GitHub porque os commits incluem arquivos em `.github/workflows/` e a credencial da automação não possui permissão para publicar esses caminhos. Os originais seguem disponíveis no repositório antigo; não recriamos refs falsas.
- README, guia de branches, guia de contribuição e guia de instalação/publicação foram atualizados na branch de preparação.
- Preparados oito snapshots isolados com branches `snapshot/*` e tags `arquivo/*`: cinco Alfas preservadas e as Betas 2, 3 e 4. Para cada etapa, foi criado um ZIP individual e um checksum SHA-256.
- Foram criadas oito Releases históricas em rascunho. Elas ainda não estão publicadas publicamente: precisam de revisão e de testes gráficos/manuais antes de serem tratadas como downloads oficialmente aprovados.
- O workflow de empacotamento terminou com sucesso e confirmou os arquivos dos pacotes, os checksums e a criação das Releases. Não executou uma campanha gráfica completa no Windows.
- A Beta 1 original continua sem pacote: o código e o executável originais não foram localizados.
- A importação de código não substitui a validação de assets LFS, testes automatizados nem teste gráfico no Windows.

O catálogo e os nomes de cada pacote estão em [docs/HISTORICO-DE-VERSOES.md](HISTORICO-DE-VERSOES.md). Links úteis: [repositório antigo e seus Releases](https://github.com/vinicius589/soldados-vs-zumbis-beta-4/releases), [branch histórica importada](https://github.com/vinicius589/soldados-vs-zumbis/tree/historico/alfas-e-betas), [Releases do novo repositório](https://github.com/vinicius589/soldados-vs-zumbis/releases) e [histórico de automação](https://github.com/vinicius589/soldados-vs-zumbis/actions).
