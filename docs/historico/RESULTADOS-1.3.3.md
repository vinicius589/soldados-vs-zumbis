# Resultado verificado — Soldados vs. Zumbis 1.3.3

Versão aplicada à pasta principal, com fontes, executável e bibliotecas coerentes.
A pesquisa utilizou dez referências primárias de Python, Pygame-ce, Hypothesis,
Coverage.py, GitHub e desenvolvimento de simulação. Fontes, decisões e comandos:
[Pesquisa aplicada](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/PESQUISA-E-TESTES-1.3.3.md>).

## O que mudou

- Saves recusam projéteis com viagem não positiva, dano ou raio negativos.
- Explosões preservam a faixa do destino, independentemente de alvo ou dono.
- O rastreamento distingue identidade da entidade de igualdade dos seus campos.
- Relógios rejeitam valores não finitos antes de modificar o estado.
- Hypothesis gera dados e sequências de operações; Coverage.py mede linhas e ramos.
- A validação automatizada rejeita falhas, suíte vazia, skips e cobertura insuficiente.
- O CI Windows guarda evidências; na execução manual também constrói e verifica o pacote.
- Dependências de teste estão fixadas e excluídas do executável.

## Resultado após instalação

| Verificação | Resultado |
|---|---|
| Unittest | 207 aprovados, 0 falhas, 0 erros, 0 ignorados |
| Testes adicionados sobre a 1.3.2 | 22, incluindo propriedades, máquina de estados e barreira de cobertura |
| Tempo da suíte instalada | 105.219 segundos |
| Projéteis | 51/51 linhas e 22/22 ramos cobertos (100%) |
| Relógio | 25/25 linhas e 10/10 ramos cobertos (100%) |
| Snapshot | 188/190 linhas (98,95%) e 86/88 ramos (97,73%) |
| Recursos e sintaxe | 109 recursos e 65 arquivos Python verificados |
| Smoke, regressão e benchmark | Aprovados na pasta principal |
| Regressão | 9 combinações de mapa/dificuldade; 108 ondas; 9 cenários de combate |
| Habilidades adicionais | 108 combinações executadas sem exceção |
| Save anterior | Produzido com 1.3.2 e retomado corretamente na 1.3.3 |
| Imagens | 3 capturas de explosão sem alvo inspecionadas; regressão gera outras 28 |
| Executável instalado | Diagnóstico aprovado; revisão interna coincide com os fontes |
| ZIP | 292 arquivos; CRC e SHA-256 conferidos; conteúdo igual ao instalado |

Benchmark: 12 cenários, 60 amostras por cenário; p95 entre 6.896 e 9.87 ms.
É renderização por software, sem espera do monitor; não representa FPS reais
nem demonstra ganho de desempenho em relação a uma medição em outro momento.

A suíte nova foi executada antes das correções e reproduziu falhas. Após as
correções, a suíte completa passou com cobertura, novamente no build e depois
na pasta instalada. O traceback deliberado de falha de gravação nos logs faz
parte de um teste de recuperação; não representa reprovação da execução.

## Evidências e recuperação

- [Resumo da validação instalada](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/reports/quality/run-6j671dty/summary.json>)
- [Cobertura HTML](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/reports/quality/run-6j671dty/coverage_html/index.html>)
- [Resultados dos testes](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/reports/quality/run-6j671dty/unittest.json>)
- [Diagnóstico do executável instalado](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/validacao_pesquisada_2026-10-16/diagnostico_instalado.json>)
- [Integridade final do pacote](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/validacao_pesquisada_2026-10-16/entrega_final.json>)
- [ZIP jogável](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/dist/SoldadosVsZumbis-1.3.3-Windows-x64.zip>)

Backup coerente anterior: `validacao_pesquisada_2026-10-16/backup_1.3.2`.
A instalação detectou fontes revertidos à 1.3.1 junto de um runtime 1.3.2 e
parou antes de sobrescrever. A comparação confirmou a versão anterior
conhecida; esse estado também foi preservado em `estado_encontrado_antes_instalacao`
antes de sincronizar a entrega completa 1.3.3. Saves pessoais não foram usados.

SHA-256 do ZIP: `fdfd08d58c028934aec1518c2dc01abc51dca1c05654e7f5689ba40ebfe7a7cf`.
Revisão dos fontes: `aeab491be1b54c27682a2ce4f701ee7fe15db3ab6088e14c8fe5ade6efad5135`.

## Limites

Cobertura não comprova ausência de bugs e os percentuais acima se referem aos
módulos indicados, não ao jogo inteiro. As propriedades usam até 150 exemplos
por teste; a máquina usa até 100 sequências de até 60 ações, sem representar
milhares de testes unittest independentes. A regressão remove inimigos após
verificar sua geração, portanto não equivale a jogar campanhas completas.
CI configurado localmente, sem publicação nem execução remota no GitHub.
Áudio/GPU reais e campanha manual permanecem sem validação nesta entrega.
As demais propostas do catálogo de 72 melhorias não foram todas implementadas.
