# Histórico de versões

## Alfa Beta 5 — revisão local em andamento

- Recuperação da base modular com retomada de partida, pontuação por combate, perfil local, ranking e loja de consumíveis.
- Corrigida a ausência da tela de perfil/loja no renderizador, apesar de já existirem as rotas de entrada e compra.
- Corrigido o contrato da tela de pontuação: ranking e histórico usam estruturas diferentes, e o histórico contém sete campos, incluindo o nome do jogador.
- Alinhadas as áreas de clique do alternador ranking/histórico e dos botões de paginação com o que é desenhado.
- Evitada consulta ao banco SQLite em cada quadro do menu de perfil; os dados são atualizados ao entrar, salvar perfil, comprar ou usar um item.
- Atualizados testes de navegação, formato do histórico, ranking agregado e economia de consumíveis.
- Limpeza da cópia de revisão: removidas cópias `*.before`, caches e ambiente virtual, sem remover os recursos de runtime registrados em `assets/manifest.json`.

**Validação pendente:** os testes de jogo precisam ser executados em Windows com Python 3.12 e as dependências de `requirements-test-lock.txt`. Não foi publicado executável ou Release nesta revisão.

## 1.5.0 — base da Alfa, 2026-10-17

- Pontuação por tipo de inimigo, de 10 a 120 pontos, exibida no HUD e no resultado.
- Registro local de resultados e identidade da partida para impedir pontuação duplicada após retomada.
- Salvamento de campanha e snapshot para continuar depois de fechar o jogo.
- Código separado em módulos de interface, combate, animações, inimigos, efeitos e renderização.
- Ajustes de HUD e botão **VOLTAR À BASE**.

## 1.4.0 — 2026-10-16

- HUD reorganizado, cartas com retratos, custos, seleção e recarga.
- Menu e pausa no alto à direita; ondas concluídas e alertas de chefes separados.
- Geometria compartilhada entre desenho e cliques, com testes nos três mapas.

## 1.3.3 — 2026-10-16

- Validação de projéteis, impactos e relógios para evitar valores inválidos no estado salvo.
- Testes por propriedades e máquinas de estado com Hypothesis.
- Fluxo de CI Windows com evidências e diagnóstico do pacote.

## 1.3.2 — 2026-10-16

- Explosões e nuvens de gás persistem quando o alvo original morre.
- Dano em área usa o ponto de impacto mostrado.
- Resolução de impactos isolada em módulo específico, com regressões de retomada.

## 1.3.1 — 2026-10-15

- Corredores avançam em direção à base nas três regiões.
- Corrigidas a orientação do deserto e a virada da passada na cachoeira.

## 1.3.0 — 2026-10-13

- Correções de recarga, pausa, resultados via teclado, recorde após derrota e texto dos menus.
- Preferências persistentes, teclas configuráveis, volumes separados, texto ampliado e redução de tremor.
- Salvamento manual, contexto em Continuar e cópia anterior recuperável.

## 1.2.0 — marco anterior preservado

Tela cheia, retomada de partidas e controle de remoção.
