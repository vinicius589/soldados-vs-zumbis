# Branches, commits, tags e versões

A estrutura precisa mostrar a evolução verdadeira do código sem transformar cada pasta ou correção em uma versão fictícia. O projeto usa branches para trabalhar, commits para registrar mudanças pequenas, tags para marcar estados exatos e Releases para distribuir versões.

## Branches que existem nesta etapa

| Branch | Função |
| --- | --- |
| `main` | Destino estável, mantido sem alterações diretas enquanto a migração e os testes são revisados. |
| `migracao/base-jogavel` | Base candidata com o código modular e os recursos do jogo. Ainda precisa passar pela revisão de integração antes de ser promovida. |
| `chore/importar-historico-legado` | Organização da documentação e preservação do histórico no novo repositório. É uma branch temporária de preparação. |
| `historico/alfas-e-betas` | Cópia histórica importada do acervo de Alfas, Betas e material bruto. Deve ser consultada, não usada para novas funcionalidades. |
| `historico/beta-1` | Referência histórica da Beta 1. Não contém o executável original que não foi localizado. |

A linha antiga `jogo` e `beta5-dev` aponta para o mesmo commit no repositório de origem neste momento. A transferência direta dessas referências exige tratar os workflows antigos separadamente, porque a credencial de integração não pode publicar arquivos de workflow sem a permissão correspondente. Até essa etapa ser concluída, não vamos afirmar que essas duas referências já estão espelhadas no novo repositório.

## Branches de trabalho

Crie uma branch a partir da linha de desenvolvimento que está sendo revisada — por enquanto, `migracao/base-jogavel`. Depois que a migração for aprovada e a base integrada, o destino normal passa a ser `main`.

| Prefixo | Quando usar |
| --- | --- |
| `fix/` | Corrigir um defeito reproduzível. |
| `refactor/` | Reduzir duplicação ou melhorar a organização sem alterar intencionalmente o comportamento. |
| `feat/` | Acrescentar uma funcionalidade nova. |
| `art/` | Alterar sprites, cenários, áudio ou animações. |
| `test/` | Acrescentar testes ou melhorar validações automatizadas. |
| `docs/` | Atualizar explicações, instruções ou histórico. |

Exemplos de nomes de branch: `fix/reload-do-soldado`, `refactor/estado-da-batalha`, `feat/perfil-local`, `art/animacao-chefe`.

As branches históricas são exceção: elas preservam os arquivos antigos e não devem receber correções novas. Também não é necessário manter uma branch permanente para cada versão; a linha do tempo de código fica nos commits, Pull Requests e tags.

## O que é um commit?

Um commit é um ponto salvo da evolução do projeto. Ele registra quais arquivos mudaram e uma mensagem curta que explica **o que foi feito e por quê**. Commits pequenos facilitam comparar a versão anterior, descobrir quando um defeito apareceu e desfazer uma mudança sem perder outras.

Exemplos de mensagens boas:

- `fix(combat): corrigir recarga após disparo`
- `refactor(assets): centralizar resolução de caminhos`
- `test(save): cobrir retomada de campanha`
- `docs(readme): registrar a história do projeto`

Evite mensagens vagas, como “mudanças”, “arrumando” ou “versão final”. Não misture uma refatoração ampla, uma nova habilidade e uma alteração de arte no mesmo commit se puder separá-las.

## Como fica a evolução do código

A sequência será documentada a partir das diferenças reais entre o acervo histórico e a base modular:

1. preservar os snapshots originais de Alfa/Beta, para consulta e comparação;
2. validar a base jogável que veio da linha Beta 4;
3. separar defeitos em branches `fix/*`;
4. fazer refatorações independentes em `refactor/*`, registrando testes e métricas antes/depois;
5. desenvolver funcionalidades novas em `feat/*`;
6. integrar por Pull Request depois de revisar o código e os testes.

Uma refatoração só será considerada bem-sucedida se a lógica que precisa continuar existir for preservada. Linhas de código removidas são uma métrica, não o objetivo isolado: também registraremos testes, módulos afetados e eventuais diferenças de comportamento.

## Tags e Releases

- **Tag:** marcador de um commit preciso. Ela identifica o código exato de uma versão.
- **Release:** página associada a uma tag. Reúne o resumo da versão, instruções de execução, validações, limitações conhecidas, checksum e anexos de distribuição.

Para versões novas, use versionamento coerente: `vX.Y.Z` para uma versão estável e sufixos como `-alpha.1` ou `-beta.1` para prévias. Uma tag não é um arquivo executável. Quando for tecnicamente possível reconstruir e conferir um pacote histórico original, o pacote executável será anexado à Release da tag correspondente.

Não crie uma tag de Beta 1 executável: o código original não foi localizado. Também não mova uma tag para outro commit só para fazer a página de downloads parecer completa. Para cada Alfa/Beta preservada, primeiro confirme a origem da pasta, os recursos LFS e o comando de inicialização.

## Revisão e integração

1. Faça commits focados na sua branch.
2. Rode os testes pertinentes e registre o resultado no Pull Request.
3. Revise a diferença completa, incluindo assets removidos, dependências e caminhos de recursos.
4. Aguarde a revisão e as verificações automáticas.
5. Só então integre à branch-base. A publicação de uma versão aprovada deve criar uma tag e uma Release; não depende de abrir uma branch permanente nova.

Para instruções de instalação, execução local e publicação, veja o [Guia de desenvolvimento e Releases](GUIA-DEV-E-RELEASES.md). O plano e os critérios de comparação estão no [Plano de preservação e evolução histórica](PLANO-EVOLUCAO-HISTORICA.md).
