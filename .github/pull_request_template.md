<!--
  Pull Request — Soldados vs Zumbis
  Preencha todas as seções. PRs incompletos voltam para revisão.
  Convenção: docs/COMMIT_CONVENTION.md  ·  Fluxo: docs/BRANCHING.md
-->

## 🎯 Descrição

<!-- O que este PR faz e por quê. Uma ou duas frases. -->

## 🔗 Issue relacionada

<!-- Ex.: Closes #42 — fecha a Issue ao mesclar. Use "Refs #" se não fechar. -->

- **Issue:** #

## 🏷️ Tipo de mudança

- [ ] `feat` — Nova funcionalidade para o jogador
- [ ] `fix` — Correção de bug
- [ ] `art` — Mudança em assets (arte, som)
- [ ] `refactor` — Refatoração sem mudar comportamento externo
- [ ] `test` — Criação ou correção de testes
- [ ] `docs` — Apenas documentação
- [ ] `perf` — Ganho de desempenho
- [ ] `chore` — Configuração, dependências, CI

## 🗺️ Região / Sistema afetado

- [ ] Cidade (Nova York)
- [ ] Deserto (Egito)
- [ ] Praia (Cachoeira-MG)
- [ ] Sistema de cartas
- [ ] Campanha / Ondas
- [ ] Engine (animação, render)
- [ ] Áudio
- [ ] Interface do jogador
- [ ] Outro: ___

## ⚠️ Breaking change

- [ ] **Sim** — se marcado, o corpo do commit precisa conter `BREAKING CHANGE:`
- [ ] Não

## 🧪 Como testar

<!-- Passos objetivos que o revisor consegue reproduzir. -->

1. `pip install -r requirements.txt`
2. `python run.py`
3. Navegue até…
4. Verifique que…

## ✅ Checklist do autor

**Código**
- [ ] `pytest` passa localmente (`python -m pytest`)
- [ ] Novos comportamentos têm teste
- [ ] Sem `print` de depuração ou código comentado para trás

**Jogo**
- [ ] O jogo abre e roda sem erros
- [ ] Testei no mapa/afetado do PR
- [ ] Testei em 1280×720 **e** em tela cheia (se mexeu em UI)

**Repositório**
- [ ] Commits seguem [Conventional Commits](../docs/COMMIT_CONVENTION.md)
- [ ] Nenhum temporário incluído (`__pycache__`, `.venv`, `.ruff_cache`)
- [ ] Nenhum segredo ou credencial versionado
- [ ] Atualizei `docs/` se o comportamento mudou

## 📸 Capturas de tela

<!-- Obrigatório para mudança visual: antes / depois. -->

| Antes | Depois |
| --- | --- |
| | |

## 📝 Notas para o revisor

<!-- Arquivos sensíveis, decisões discutíveis, dívida técnica consciente. -->
