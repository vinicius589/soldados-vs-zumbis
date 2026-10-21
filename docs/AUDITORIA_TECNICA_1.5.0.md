# Auditoria técnica da linha 1.5.0

## Base analisada

- Branch candidata: `chore/atualizacoes-1-4-0`
- Commit-base: `de791878efb164553a7e7a80e3229499bfa332db`
- A CI publicada para esse commit concluiu com sucesso em 17/10/2026: validações, testes, cobertura, smoke test, regressão e benchmark.
- A árvore dessa versão tem 38 módulos Python em `src/svz/` e 23 arquivos de teste. Isso é uma base bem melhor para continuar do que a `main` antiga com mais de 10 mil linhas em um único arquivo.

A `main` e a linha 1.5.0 não compartilham uma base de commits. Por isso, o trabalho novo fica nesta branch da 1.5.0; as mudanças anteriores na `main` foram fechadas sem merge e permanecem como branches separadas para referência.

## Defeitos confirmados e corrigidos nesta branch

### 1. Código de seleção de cartas desconectado do fluxo real

`Game.enter_selection()` monta as oito cartas regionais e muda direto para `battle`. Não há rota que entre na cena `selection`, mas ainda existiam os métodos de seleção, a tela de inspeção, os controles para selecionar de uma a três cartas e wrappers sem chamadas.

**Ação:** removi os métodos e renderizadores inacessíveis, mas preservei o fechamento da partida (`finish_battle`) e o mapeamento visual necessário ao posicionamento (`regional_sprite_index`), ambos ainda usados pelo runtime. A suíte foi usada para encontrar e corrigir essas dependências. O comportamento atual da linha 1.5.0 continua sendo: cada região inicia com seu conjunto de oito cartas disponível no HUD.

**Não fiz:** não recoloquei uma seleção pré-partida diferente sem evidência de que essa é a regra atual aprovada para a 1.5.0.

### 2. Tela de evolução/promotor sem caminho ativo

O menu atual envia `PERSONAGENS` para a cena `characters`, que usa `draw_characters()`. O antigo renderizador de dossiê de evolução não tinha caminho ativo. Além disso, o registro `PROMOTIONS` é um dicionário vazio, então o código do instrutor não poderia promover nenhuma unidade nessa versão.

**Ação:** removi os caminhos de dossiê/evolução inacessíveis e a chamada de promoção inativa. Mantive `PROMOTIONS = {}` como símbolo público de compatibilidade, pois a suíte e outros consumidores ainda o importam. A tela atual de informações de soldados e zumbis foi mantida. O catálogo legado de fichas não foi apagado em massa; ele será eliminado somente depois de uma revisão de compatibilidade com salvamentos e referências indiretas.

### 3. Fonte duplicada de metadados dos chefes

Cada região declarava inicialmente `"bosses": ()`, mas o módulo preenchia o mesmo campo depois com `REGION_BOSSES`.

**Ação:** removi os valores vazios intermediários. A lista regional de chefes passa a ser definida no ponto que já era usado para preenchê-la.

### 4. O ZIP era gerado, mas não ficava disponível como artefato

A etapa manual da pipeline executa `build` e `package`, mas o upload existente guardava apenas relatórios e checksum; não incluía o próprio ZIP jogável.

**Ação:** acrescentei um passo condicional de upload do pacote e do checksum quando o workflow é iniciado manualmente. Esse passo só poderá ser validado de ponta a ponta após uma execução `workflow_dispatch` com o executável sendo construído e empacotado.

### 5. README com link interno quebrado

O README apontava para `docs/PESQUISA-E-TESTES-1.5.0.md`, inexistente nessa árvore. Também havia uma frase de configurações mal redigida.

**Ação:** corrigi o link para o relatório de validação existente e acrescentei `tests/test_documentation_links.py`, que falha se voltar a existir um link local inexistente.

## Redução acumulada

O ponto de partida é a linha 1.5.0 antes desta auditoria. As habilidades de inimigos, a geometria pura dos efeitos e as telas de menu foram isoladas em módulos próprios; a tabela inclui esses arquivos novos para não confundir movimentação de código com remoção.

| Arquivo | Base | Atual | Diferença |
|---|---:|---:|---:|
| `src/svz/app.py` | 1.033 | 925 | −108 |
| `src/svz/rendering.py` | 2.297 | 1.582 | −715 |
| `src/svz/battle.py` | 1.907 | 1.380 | −527 |
| `src/svz/content.py` | 1.791 | 1.788 | −3 |
| `src/svz/enemy_abilities.py` | 0 | 481 | +481 |
| `src/svz/rendering_geometry.py` | 0 | 95 | +95 |
| `src/svz/menu_rendering.py` | 0 | 459 | +459 |
| **Total combinado** | **7.028** | **6.710** | **−318 linhas** |

A classe principal de renderização agora fica concentrada na pintura da batalha e nos helpers compartilhados; menu, geometria e habilidades de inimigos têm contratos separados. A divisão não altera a lógica de layout nem os ciclos de combate.

Os totais contam os módulos de runtime listados, não testes e documentação. Ainda há módulos grandes que merecem divisão gradual.
## O que ainda precisa de trabalho

### Correções/validação
- Validar no Windows o artefato ZIP gerado pelo workflow manual, extraí-lo numa pasta limpa e executar o teste de inicialização.
- Executar uma campanha completa em cada região e dificuldade; a CI headless não substitui uma partida observada.
- Revisar a progressão dos recursos e a curva de pressão até a 12ª onda.
- Conferir movimento, ataque e dano dos corredores e dos chefes nas três regiões.
- Conferir se a tela `PERSONAGENS` apresenta todos os atores regionais e se nenhuma ficha usa uma arte de outra unidade.

### Candidatos a remoção depois de comprovar ausência de uso
- Catálogos antigos que ainda coexistem com o elenco ativo de oito cartas por região.
- Constantes de fichas que só tenham sido usadas por telas legadas removidas.
- Recursos duplicados/obsoletos e evidências de build antigas que já não correspondam à versão 1.5.0.

### O que não apagar
- Spritesheets, sons, tabelas de inimigos ou campos usados por salvamentos antes de comprovar que estão órfãos.
- Relatórios históricos úteis para rastreabilidade. Devem ser identificados por versão em vez de misturados com a validação vigente.

## Regra de aceite

Uma remoção precisa ter: referência de uso verificada, testes relevantes aprovados e ausência de regressão no comportamento. Uma correção visual também exige prévia ou teste no jogo; passar no lint não prova que o sprite está correto.
