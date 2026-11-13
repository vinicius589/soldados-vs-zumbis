# Correção do HUD — 1.1.1

O botão REMOVER estava oculto na dificuldade Fácil. A mesma condição também
bloqueava o clique, o atalho R e a retirada da tropa. As quatro restrições foram
removidas em app.py, battle.py e rendering.py, mantendo o posicionamento entre
PAUSA e PRÓXIMA e o reembolso existente de 35% do custo, arredondado para cima.

Para usar: clique em REMOVER e depois na casa da unidade. Clique novamente no
botão, pressione R ou selecione uma carta para sair da ferramenta. No modo
Teclado, R ativa a remoção e Enter confirma na casa selecionada. Ao retomar uma
partida pausada, use PAUSA ou P antes de continuar.

## Verificação

- Suíte completa: 127 testes aprovados em 59,166 segundos, mais smoke test.
- Seis novos testes, cada um cobrindo três mapas e três dificuldades: presença
  do botão sem sobreposição, clique com reembolso único, atalho de teclado,
  cancelamento da ferramenta, bloqueio do clique em pausa/fim e persistência
  da remoção após salvar/carregar.
- Diagnóstico do executável: recursos reais, combate, botão, atalho, retirada,
  reembolso e retomada em nove combinações de mapa/dificuldade.
- ZIP extraído: manifesto de 289 arquivos conferido e executável testado com
  PATH limitado ao Windows, sem Python externo.
- Capturas do HUD na dificuldade Fácil dos três mapas inspecionadas: botão
  legível entre PAUSA e PRÓXIMA.
- Formato do salvamento permanece inalterado. Os testes usam dados temporários
  separados das partidas do jogador.

Os ensaios de execução desta correção usam drivers SDL simulados. Não equivalem
a uma campanha inteira jogada manualmente nem a uma nova avaliação de áudio.
Os resultados e hashes estão em RESULTADOS_HUD.json.

