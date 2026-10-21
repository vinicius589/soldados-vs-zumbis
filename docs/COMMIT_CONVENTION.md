# 📝 Convenção de Commits

Este projeto segue **[Conventional Commits 1.0.0](https://www.conventionalcommits.org/pt-br/v1.0.0/)** de forma **estrita**. O padrão mantém o histórico legível e permite gerar changelogs automaticamente.

---

## 1. Formato

```
<tipo>[(<escopo>)][!]: <descrição>

<corpo opcional>

<rodapé opcional>
```

```
feat(campanha): adicionar onda 13 com mini-boss regional

O mini-boss usa a mesma tabela de escalamento dos chefes regionais,
mas com 40% do HP para não quebrar o ritmo do ciclo atual.

Closes #42
```

---

## 2. Tipos permitidos

O projeto usa o conjunto padrão **mais o tipo `art`**, específico para assets.

| Tipo | Quando usar | Exemplo |
| --- | --- | --- |
| `feat` | Nova funcionalidade **para o jogador** | `feat(campanha): adicionar onda 13 com mini-boss` |
| `fix` | Correção de bug | `fix(animacao): corrigir sprite do rastejador cortado` |
| `art` | **Assets** visuais ou sonoros | `art(deserto): nova folha do incinerador v2` |
| `docs` | **Apenas** documentação | `docs: inclui regras de proteção de branch` |
| `refactor` | Reestruturação **sem** mudar comportamento externo | `refactor(render): extrair shader de vinheta` |
| `test` | Criação ou correção de testes | `test: cobre escalamento de ondas` |
| `style` | Formatação **sem** mudança de lógica | `style: padronizar indentação em main.py` |
| `perf` | Ganho de desempenho medível | `perf(render): evita recriar Surface por quadro` |
| `chore` | CI, dependências, build, configuração | `chore: fixar numpy==2.5.3` |
| `ci` | Arquivos e jobs de CI | `ci: adiciona workflow de pytest` |
| `build` | Sistema de build | `build: corrige empacotamento do PyInstaller` |
| `revert` | Reverter commit anterior | `revert: desfaz feat(campanha): ...` |

> **Como decidir:** o que mudou?
> - O que o **jogador vê ou sente** → `feat` / `fix`
> - Um **arquivo de arte ou áudio** → `art`
> - **Só texto** → `docs`
> - **Só código, mesmo comportamento** → `refactor`
> - **Só formatação** → `style`

---

## 3. Escopos sugeridos

| Escopo | Área |
| --- | --- |
| `campanha` | Ondas e progressão |
| `carta` | Sistema de cartas |
| `boss` | Chefes e subchefes |
| `animacao` | Sistema de animação 2D |
| `render` | OpenGL / compositor |
| `audio` | Efeitos sonoros e música |
| `ui` | Interface do jogador |
| `cidade` | Mapa de Nova York |
| `deserto` | Mapa do Egito |
| `praia` | Mapa da Cachoeira-MG |
| `engine` | Código reutilizável |
| `save` | Persistência de progresso |
| `deps` | Dependências |
| `ci` | Integração contínua |
| `docs` · `tests` | Documentação · testes |

---

## 4. Regras da descrição

1. **Português** — mantém a consistência do projeto.
2. **Minúsculas**, **sem ponto final**.
3. **Infinitivo**: "adicionar", não "adicionou" nem "adicionando".
4. **Máximo de 72 caracteres** no total (tipo + escopo + descrição).
5. Sem emoji, sem `WIP`.
6. **Um commit, uma mudança lógica** — nada de "resolvi tudo".

✅ `fix(animacao): corrigir sprite do rastejador cortado na borda`
❌ `Fix bug`
❌ `feat: 🐛 corruda aquele negocio do sprite`

---

## 5. Corpo

Explique o **porquê**, não o **o quê** — o *diff* já mostra o quê.

- Máximo de **72 caracteres por linha**.
- Assuntos distintos em parágrafos separados.
- Listas com `-`.

---

## 6. Rodapé (encerramento de Issues)

| Sintaxe | Efeito |
| --- | --- |
| `Closes #42` | Fecha a Issue #42 ao mesclar |
| `Fixes #42` | Idem |
| `Refs #42` | Vincula sem fechar |

---

## 7. Mudanças incompatíveis (*Breaking Changes*)

**Obrigatório** marcar com `!` após o tipo/escopo **e** declarar no corpo:

```
feat(save)!: mudar formato de save para JSON v2

BREAKING CHANGE: saves da Beta 3 não são mais compatíveis.
```

---

## 8. Commits de merge

**Proibido** o merge genérico (`Merge branch 'main' into 'develop'`).
Use **Squash and merge** ou *fast-forward* — o histórico do `develop` fica linear e legível.

---

## 9. Validação

```bash
# Checagem rápida antes de commitar
git commit --dry-run -m "feat(ui): adicionar medidor de suprimentos"
```

Para reinstalar o hook de validação localmente:

```bash
git config core.hooksPath .githooks
```

---

## 10. Exemplos completos

```bash
# Funcionalidade nova
git commit -m "feat(campanha): adicionar onda 13 com mini-boss regional"

# Correção de bug
git commit -m "fix(animacao): corrigir sprite do rastejador cortado na borda"

# Asset
git commit -m "art(deserto): nova folha do incinerador v2"

# Documentação
git commit -m "docs(readme): atualizar instrucoes de instalacao"

# Testes
git commit -m "test(economia): cobre teto de suprimentos em 600"

# Refatoração
git commit -m "refactor(render): extrair shader de vinheta para funcao separada"

# Breaking change
git commit -m "feat(save)!: mudar formato de save para JSON v2" \
           -m "BREAKING CHANGE: saves da Beta 3 nao sao mais compativeis."
```
