# Melhorias de combate — 1.3.2

Implementação do primeiro ciclo prioritário da análise do PvZ, em código próprio.
Nenhum código, executável, biblioteca ou recurso do arquivo decompilado foi incorporado.

## Entrega

| Item do catálogo | Situação nesta versão |
|---|---|
| M01 — explosão independente do alvo | Implementado para granadas, morteiros, foguetes, gás e torpedos com área, incluindo ataques inimigos com área. |
| M02 — contratos de projéteis | Parcial: destino fixo para explosivos com área; alvo acompanhado por tiros dirigidos; sem troca automática de alvo. Colisão contínua com obstáculos fica pendente. |
| M57 — separar combate | Parcial: resolução de impactos extraída para `src/svz/projectile_combat.py`. Os demais sistemas permanecem em seus módulos atuais. |
| M65 — regressões de combate | Parcial: 13 testes novos para esta entrega. Os demais sistemas propostos terão testes próprios quando implementados. |
| M69 — validação de entrega | Aplicado o processo existente de testes, construção, diagnóstico e verificação de hashes. |

As demais propostas M03–M56, M58–M64, M66–M68 e M70–M72 continuam
no catálogo de planejamento, sem alegação de implementação nesta versão.
Novos modos, mudanças de seleção de cartas e reformulação das ondas são
alterações de produto e balanceamento separadas deste ciclo corretivo.

## Regras verificáveis

- A explosão acontece no destino visual escolhido no disparo, mesmo que o alvo
  tenha morrido. Um alvo que sair do raio deixa de receber o dano direto.
- Dano secundário preserva 72% para aliados e 50% para inimigos, antes das
  resistências existentes. O limite do raio continua exclusivo (`distância < raio`).
- Dano em área mantém a faixa; ataques de chefes preservam a exceção existente
  de alcance vertical de 75% da altura de célula.
- Um mesmo alvo não recebe simultaneamente dano primário e secundário.
  As vítimas são selecionadas antes do dano, evitando perdas durante remoções.
- Tiros dirigidos atualizam o destino visual durante o voo. Se seu alvo sair
  da batalha, não escolhem outro automaticamente.
- Atrasos de lançamento e pausa continuam respeitados. Cada projétil resolve
  seu impacto uma única vez, inclusive após um passo de tempo grande.
- O formato do snapshot permanece inalterado. A retomada preserva explosivos
  pendentes e referências aos seus alvos removidos.
- Corrigido também um argumento excedente em `signal_pulse`: ele usava o
  total de ondas (12) como duração e a duração da habilidade como tempo já
  decorrido. Agora o efeito começa em zero e dura o tempo correto do gesto.

## Validação e reprodução

Use Python 3.12 e as dependências de `requirements-build-lock.txt` em ambiente
isolado. `python tools/manage.py build` executa a suíte inteira e o smoke test
antes de gerar o executável. `python tools/manage.py package` verifica os
hashes dos fontes e do runtime e executa o diagnóstico do EXE.

A suíte desta entrega contém 185 testes. Há ainda regressão de 9 campanhas
simuladas (108 ondas geradas e 9 cenários de combate), verificação adicional
de 108 combinações de habilidade/mapa/dificuldade e benchmark em 12 cenários.
Na regressão de progressão, inimigos são removidos deliberadamente após
verificar seu nascimento; ela não mede a possibilidade de vencer uma campanha.

Os registros completos, backup 1.3.1 e imagens estão na pasta irmã
`melhorias_2026-10-16`. A aprovação automatizada não garante ausência de bugs:
áudio real, GPU, monitor e experiência de uma campanha completa ainda exigem
validação manual. O dano em área recuperado altera combates que antes perdiam
explosões; observar o balanceamento em partidas reais continua necessário.
