<!--
  Pull Request — Soldados vs Zumbis
  Preencha as seções aplicáveis. Não marque um teste que não foi executado.
  Convenção: ../docs/COMMIT_CONVENTION.md · Fluxo: ../docs/BRANCHING.md
-->

## Descrição

O que este PR faz e por quê? Qual problema ou necessidade está resolvendo?

## Issue relacionada

- **Issue:** # ou "não se aplica"

## Tipo de mudança

- [ ] `feat` — Nova funcionalidade para o jogador
- [ ] `fix` — Correção de bug
- [ ] `art` — Mudança em arte, som ou animação
- [ ] `refactor` — Refatoração sem mudança intencional de comportamento
- [ ] `test` — Testes
- [ ] `docs` — Documentação
- [ ] `perf` — Desempenho
- [ ] `chore` — Configuração, dependências ou CI

## Área afetada

- [ ] Cidade / Nova York
- [ ] Deserto / Egito
- [ ] Cachoeira / Minas Gerais
- [ ] Cartas e unidades
- [ ] Combate e ondas
- [ ] Recursos, saves ou perfil
- [ ] Engine, animações ou renderização
- [ ] Áudio
- [ ] Interface
- [ ] Documentação ou pipeline

## O que mudou

- 
- 

## Como testar

Registre comandos e resultados reais. Se algo não foi executado, declare como pendente.

~~~bash
python -m compileall -q src run.py
python -m ruff check src tests
python -m pytest -q
python run.py
~~~

**Teste manual realizado:** descreva região, onda, unidades, menu ou fluxo conferido.

**Não testado / limitações:** informe aqui o que faltou conferir.

## Se for uma refatoração

| Medida | Antes | Depois | Como foi obtida |
| --- | --- | --- | --- |
| Linhas Python do escopo | | | |
| Arquivos/módulos afetados | | | |
| Testes relevantes | | | |
| Comportamentos mantidos | | | |

Explique a razão da redução ou divisão do código. Menos linhas, por si só, não comprova uma melhoria: registre também legibilidade, responsabilidades, cobertura de teste e qualquer diferença intencional.

## Se alterar assets

- [ ] Preservei a identidade visual e as animações aprovadas.
- [ ] Conferi caminhos e manifestos de recursos.
- [ ] Mantive créditos e licenças dos arquivos.
- [ ] Testei no jogo os assets alterados.
- [ ] Incluí capturas de antes/depois quando a mudança é visual.

## Checklist

- [ ] Os commits seguem [Conventional Commits](../docs/COMMIT_CONVENTION.md).
- [ ] Adicionei ou atualizei testes quando necessário.
- [ ] Revisei o diff e removi arquivos temporários, caches e saves pessoais.
- [ ] Não incluí credenciais ou segredos.
- [ ] Atualizei a documentação se comandos, comportamento ou requisitos mudaram.
- [ ] Não marquei como aprovado um teste que não executei.

## Observações para revisão

Arquivos sensíveis, decisões técnicas, riscos ou dívida técnica que ficou para outra etapa.
