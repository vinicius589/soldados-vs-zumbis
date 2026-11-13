# HUD 1.4.0

A disposição segue a referência fornecida pelo usuário, com desenho próprio e os recursos militares existentes.

- Suprimentos e capacidade no alto à esquerda.
- Oito cartas no topo, com retrato, custo, seleção e máscara de recarga.
- Remoção ao lado das cartas, com indicação do reembolso de 35%.
- Menu e pausa no alto à direita.
- Ondas no canto inferior direito, com progresso das ondas concluídas, invasores vivos e pendentes e marcos dos chefes nas ondas 4, 8 e 12.
- A ficha com nome, habilidade e atributos aparece sobre a carta pelo mouse ou por F1 no controle por teclado.

A geometria em `src/svz/hud_layout.py` é compartilhada pelo desenho e pelas áreas de clique. As áreas inferiores ficam abaixo das faixas jogáveis dos três mapas. O estado salvo e as regras de combate são preservados.

## Validação

`tests/test_hud_layout.py` verifica limites e sobreposições, seleção das oito cartas nos três mapas, colocação e remoção com reembolso, pausa, retorno ao menu, avanço de onda e fichas por mouse e teclado. `tests/test_review_fixes.py` verifica os textos com as duas escalas de fonte.

As seis capturas dos três mapas, com fonte normal e ampliada, foram inspecionadas. A validação automatizada usa SDL dummy; ela não substitui avaliação manual de áudio, GPU ou monitores físicos.

Resultado da validação completa: 214 testes aprovados, zero falhas, erros ou testes ignorados. Integridade dos 109 recursos, smoke test, regressões e benchmark aprovados. Os relatórios detalhados estão em `reports/quality/` do candidato preservado em `hud_2026-10-16`.
