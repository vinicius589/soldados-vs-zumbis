# Plano de sprints — Soldados vs Zumbis 1.5.x

Este é um backlog de engenharia, não uma promessa de que todos os itens já estão implementados. Cada sprint termina com uma entrega pequena, critérios de aceite e evidências.

## Sprint 0 — Limpeza segura e integridade do repositório

**Estado:** limpeza e Sprint 2 aprovadas na CI; Sprint 3 em andamento.

- [x] Remover métodos e renderizadores de seleção pré-partida sem rota ativa.
- [x] Remover a tela de evolução sem rota ativa e a chamada de promoção inativa.
- [x] Manter `PROMOTIONS = {}` como símbolo público de compatibilidade.
- [x] Remover os valores vazios de chefes que eram substituídos mais abaixo.
- [x] Corrigir link e texto do README.
- [x] Fazer a CI publicar o ZIP e seu checksum no workflow manual.
- [x] Adicionar teste de links locais do README.
- [ ] CI verde no commit final.
- [ ] Executar a pipeline manual para comprovar o download do ZIP.

**Aceite:** testes e lint aprovados; `main` não alterada; pacote gerado pela CI fica baixável junto de seu checksum.

## Sprint 1 — Contratos do elenco e regressões de campanha

- Garantir para cada uma das três regiões que as oito cartas ativas tenham ficha, sprite, perfil de animação e custo.
- Garantir que os 6 inimigos comuns, 3 subchefes e 3 chefes tenham dados coerentes e recursos visuais presentes.
- Testar por código a sequência fixa de 12 ondas e o chefe final de cada região.
- Conferir vitória, derrota, recordes, pontuação e retomada de partida.
- Testar que personagens exibidos no menu correspondem ao ator e aos atributos carregados na batalha.

**Aceite:** testes novos reproduzem falhas específicas; todos os testes existentes continuam passando; os mapeamentos usam a mesma chave entre catálogo, ficha e combate.

## Sprint 2 — Separar o combate em componentes menores

`src/svz/battle.py` caiu de 1.907 para aproximadamente 823 linhas. As habilidades dos inimigos ficam em `src/svz/enemy_abilities.py`, o movimento especial em `src/svz/enemy_motion.py` e dano/ataques/suporte/recarga em `src/svz/combat_actions.py`. O objetivo continua sendo separar por domínio sem criar classes para cada detalhe.

- [x] Isolar regras de habilidades dos inimigos em módulo próprio (`src/svz/enemy_abilities.py`).
- [x] Isolar colisões, salto, escavação e movimento especial em `src/svz/enemy_motion.py`.
- [x] Isolar dano, ataques, suporte e recarga em `src/svz/combat_actions.py`.
- Manter projéteis/impactos no módulo existente quando já couberem lá.
- Preservar `Battle` como fachada e proprietário do estado da partida.
- [x] Adicionar teste de arquitetura que impede as habilidades de voltarem para `Battle` ou criarem dependência circular.
- Adicionar testes de contrato antes de mover cada conjunto de métodos.

**Aceite:** nenhuma mudança de balanceamento escondida na refatoração; mesma entrada produz os mesmos resultados nos testes de regressão; nenhum ciclo de importação.

## Sprint 3 — Modularizar a renderização

`src/svz/rendering.py` foi reduzido pela extração dos primitivos de desenho para `src/svz/rendering_primitives.py`, das telas de menu para `src/svz/menu_rendering.py`, dos helpers de cartões, retratos e texto para `src/svz/card_rendering.py`, da geometria pura para `src/svz/rendering_geometry.py`, dos efeitos/quadros de disparo para `src/svz/effects_rendering.py`, das trajetórias e fluxos dos projéteis para `src/svz/projectile_rendering.py`, do desenho de soldados/inimigos para `src/svz/entity_rendering.py`, dos avisos, pausa, resultados e histórico para `src/svz/status_rendering.py`, da bandeja e barras do HUD para `src/svz/battle_hud_rendering.py` e das defesas de faixa/textos de impacto para `src/svz/battle_overlay_rendering.py`.

- [x] Remover wrappers de renderização e métodos sem chamadas deixados pelas telas antigas.
- [x] Extrair geometria de fluxos e água para `rendering_geometry.py` com testes dos vértices.
- [x] Extrair nuvens, VFX vinculados, quadros de efeitos e ciclo de flash de boca de arma para `effects_rendering.py`.
- [x] Extrair sprites, poses e desenho das entidades para `entity_rendering.py`.
- [x] Extrair avisos de chefe, pausa, tela de resultado e histórico de pontuações para `status_rendering.py`.
- [x] Extrair jatos de água, chamas, fluxos elementais, granadas e trajetórias para `projectile_rendering.py`.
- [x] Extrair a bandeja de cartas, suprimentos, recargas e controles da batalha para `battle_hud_rendering.py`.
- [x] Extrair helpers de cartões, enquadramento de retratos e texto multilinha para `card_rendering.py`.
- [x] Extrair retângulos de botões, desenho de texto, painéis e botões para `rendering_primitives.py`.
- [x] Extrair defesas de faixa e textos de impacto para `battle_overlay_rendering.py`; manter barras de vida e munição com o HUD.
- [x] Extrair telas de menu/personagens para `menu_rendering.py` sem dependência de volta no renderizador principal.
- [x] Separar desenho de efeitos/projéteis do desenho de atores e HUD.
- [x] Separar as telas de menu e consulta do código de renderização da batalha.
- Preservar geometria e âncoras do sprite durante ataques, dano e morte.
- Atualizar os testes de layout e gerar prévias antes/depois para revisão visual.

**Aceite:** nenhuma mudança involuntária no tamanho dos sprites ou na posição dos pés; todos os cenários continuam alinhados; regressões visuais documentadas.

## Sprint 4 — Balanceamento medido

- Rodar cenários em Cidade, Deserto e Cachoeira.
- Cobrir Fácil, Médio e Difícil, com registros por onda.
- Registrar suprimentos iniciais, receita, custo das cartas, frequência de recarga, tempo de sobrevivência e resultados.
- Detectar se uma composição simples domina todas as outras.
- Ajustar números só quando as medições e os testes manuais mostrarem o problema.

**Aceite:** progressão de pressão identificável do início ao fim; nenhuma dificuldade fica mais fácil que a anterior por erro de multiplicadores; resultados reproduzíveis por seed quando o cenário permitir.

## Sprint 5 — Auditoria visual de animações e assets

- Pré-visualizar todos os estados de soldado, zumbi e chefe usados pelo jogo.
- Verificar ordem dos quadros, direção, ponto dos pés, recortes, efeitos duplicados e escala.
- Gerar novas artes com ImageGen apenas para estados que não têm sequência adequada ou não podem ser corrigidos com o material existente.
- Atualizar o manifesto de assets e seus créditos se qualquer arte for substituída.

**Aceite:** nenhum quadro cortado ou sprite invisível nos testes de catálogo; revisão visual de movimento, ataque, dano e morte nas três regiões.

## Sprint 6 — Release confiável

- Executar workflow manual no Windows.
- Baixar o artefato ZIP da própria execução.
- Extrair em diretório limpo e verificar manifest/checksum.
- Iniciar sem Python externo no PATH e confirmar acesso a áudio e assets.
- Atualizar README/CHANGELOG e documentar limitações verificadas.

**Aceite:** o arquivo disponibilizado pela CI é o mesmo que passou no teste do executável; versão, checksum e notas de lançamento correspondem.

## Ordem de execução

1. Concluir Sprint 0 e validar CI.
2. Executar Sprint 1 antes de fazer refatorações profundas.
3. Fazer Sprint 2 e Sprint 3 em PRs separados e pequenos.
4. Fazer Sprint 4 com código já testável e estável.
5. Fazer Sprint 5 quando a auditoria determinar quais animações realmente precisam de novos assets.
6. Finalizar Sprint 6 para publicar uma versão confiável.
