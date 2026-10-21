# Revisão aplicada — Soldados vs Zumbis 1.3.0

Data: 13/10/2026. Versão instalada em
`C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis`.

Os nove defeitos confirmados na revisão de 11/10 foram corrigidos. A versão
1.3.0 substitui o executável da raiz e a distribuição em `dist/`. Os fontes
instalados correspondem ao executável por SHA-256. Os testes executados passaram;
isso não constitui garantia de ausência de qualquer bug.

## Correções verificadas

| ID | Correção | Evidência de aceite |
|---|---|---|
| D01 | Colocação por mouse e teclado obedece à recarga de 10 s da carta | 18 combinações de mapa, dificuldade e controle; tentativa repetida não gasta recursos |
| D02 | Pausa/término bloqueiam colocar, remover e antecipar onda na camada de combate | Testes dos comandos e do estado congelado nas nove combinações |
| D03 | Enter/Space na tela de resultado concluem a partida antes dos comandos de combate | Vitória e derrota, nos três mapas e três dificuldades |
| D04 | Derrota registra a onda atingida, preservando recordes maiores | Testes de gravação e falha de gravação; resultado retido quando não é possível salvar |
| D05 | Menus, mapas, fichas, história, configurações e confirmações aceitam Tab/setas/Enter | Foco visível; confirmação de nova partida começa em Cancelar; limites dos controles verificados |
| D06 | Ajuda explica oito cartas regionais e o fluxo atual | Verificação do texto e inspeção da tela ampliada |
| D07 | Dificuldade usa valores do próprio modelo | Iniciais 320/240/190; limites 650/430/330 para fácil/médio/difícil |
| D08 | Métricas do HUD usam até duas linhas, mantendo REMOVER visível | Medição das 24 cartas em ambos os tamanhos; capturas dos três mapas e tela cheia |
| D09 | Campanha inválida tem leitura limitada e tratamento de profundidade excessiva | Arquivos profundos, grandes e truncados; aviso recuperável e preservação durante a leitura |

## Melhorias da revisão

| ID | Resultado nesta versão |
|---|---|
| M01 | Preferências de controle, som, volumes e teclas persistem; verificadas ao iniciar outro processo |
| M02 | Pausa automática ao perder foco/minimizar, configurável; recuperar foco não retoma sozinho |
| M03 | Texto ampliado, fonte mínima maior e ficha por F1; contraste configurável e fonte distribuída permanecem como evolução |
| M04 | Dez ações remapeáveis, volumes de música/ambiente/efeitos e redução de tremor; gamepad e novas alternativas para alertas ainda não implementados |
| M05 | F5 salva; Continuar informa região, dificuldade, onda e horário; recuperação da cópia anterior, preservada também na primeira gravação após recuperar arquivo inválido; continua existindo um ponto de retomada por perfil |
| M06 | Passos fixos de 1/60 s, até 15 atualizações por quadro; dez segundos a 10/30/60 FPS produzem os mesmos 600 passos; travamentos longos têm recuperação limitada |
| M07 | Validação centralizada em Battle; preferências, foco, painéis e relógio em módulos próprios; removidos trechos inalcançáveis confirmados. Divisão adicional do combate fica gradual |
| M08 | Ferramenta de medição de carga, memória e tempos p50/p95/p99; doze cenários medidos. Não houve otimização especulativa |
| M09 | Balanceamento humano continua pendente. Os testes confirmam progressão/combate, sem simular a experiência de vencer nove campanhas |
| M10 | Ajuda atualizada e ficha da carta selecionada durante o combate. Tutorial jogável e prévia de onda ainda são propostas |
| M11 | Melhor onda e vitória por dificuldade, com registros antigos identificados como gerais. Estatísticas detalhadas de partida ainda não adicionadas |
| M12 | Suíte ampliada de 141 para 168 testes; cobre os defeitos, estados, entradas, arquivos inválidos, recuperação e distribuição desatualizada |
| M13 | Versão única, metadados do EXE, revisão dos fontes e bibliotecas conferidas; pasta de bibliotecas substituída integralmente. Ícone específico, assinatura e instalador continuam opcionais |
| M14 | Histórico Git local com marcos v1.2.0 e v1.3.0, changelog e documentação atualizados; fluxo de testes Windows preparado para GitHub, sem publicação remota |

## Validação executada

| Verificação | Resultado |
|---|---|
| Integridade e sintaxe | 109 recursos íntegros; 58 arquivos Python analisados |
| Suíte completa final | **168 aprovados, zero falhas**, 69.120 s |
| Smoke test | Passou |
| Progressão e combate | Nove combinações, 108 ondas e nove casos de combate; 28 capturas |
| Saves 1.2.0 → 1.3.0 | Nove snapshots restaurados exatamente e atualizados; EXE extraído também retomou save antigo e avançou 120 passos |
| Preferências entre processos | Controle, som, volumes, texto, tremor e tecla personalizada recuperados |
| EXE nativo Windows | Passou, driver windows; janela 1280×720, tela cheia 1920×1080; três mapas, cliques na fila SDL e estado preservado |
| Áudio nativo | Biblioteca carregada e mixer inicializado; qualidade audível não avaliada por escuta |
| EXE extraído | Passou com diretório de abertura diferente e PATH sem Python |
| Instalação principal | EXE 1.3.0 passou novamente; fontes e bibliotecas coincidem com a construção |
| ZIP | 292 arquivos conferidos, além do manifesto SHA256.json; conjunto exato, raiz e cópia extraída idênticos |
| Imagens | HUD, ajuda, dificuldade, personagens, configuração e teclas inspecionados; capturas nativas de tela cheia também examinadas |

O ensaio de 108 ondas remove inimigos após conferir seu nascimento para acelerar
a progressão; o combate tem casos separados. Não é uma campanha humana completa.
Os logs incluem falhas de escrita provocadas por testes: são cenários negativos
esperados, e o resultado final da suíte é OK.

Benchmark: carga de 4.443 s, maior p95 de 7.038 ms e
maior memória residente de 368.39 MiB nas amostras. Foram 60 quadros por
cenário, três mapas e ondas 1/4/8/12, dificuldade média, renderização simulada por
software a 1280×720. Estes valores não são FPS medidos no monitor. Hardware,
sistema e percentis completos: [benchmark.json](evidencias-1.3.0/benchmark.json).

Não foram executadas sessões humanas longas, avaliação de áudio por escuta,
testes em máquina limpa, múltiplos monitores, outros DPIs ou gamepads.

## Entrega e recuperação

- Jogar: `SoldadosVsZumbis.exe` na raiz; não exige instalar Python.
- Distribuir: `dist/SoldadosVsZumbis-1.3.0-Windows-x64.zip`. Extrair a pasta inteira.
- Salvamentos pessoais não foram alterados pelos testes nem incluídos no ZIP.
- Distribuição 1.2.0 retirada de `dist/` e preservada em
  `C:/Users/phill/.codex/visualizations/2026/10/06/01a11265-fd87-71b1-8872-fd529bed0290/review-fixes-1.3.0/retired-1.2.0`.
- Cópia prévia de fontes/documentos: `C:/Users/phill/.codex/visualizations/2026/10/06/01a11265-fd87-71b1-8872-fd529bed0290/review-fixes-1.3.0/backup-before-1.3.0`.
- Histórico local permite comparar os marcos sem depender de um serviço externo.

SHA-256 do ZIP: `c6f2d5f763090e4e4dae3f3f8bdfe742f1577179e6eb11ea7c84386f475273f0`.

Revisão dos fontes: `2eca5c170643a0c7ccd7af82aecc5b09b0dc76a5dc2c3ff1ef80fb40e4e92671`.

## Fontes e decisões

A aplicação parte da [revisão geral de 11/10](REVISAO_GERAL_2026-10-11.md), que
reúne as fontes primárias e reproduções. Foram reconferidas nesta continuação as
APIs de [eventos do Pygame-ce](https://pyga.me/docs/ref/event.html), a
[substituição de arquivos no Python](https://docs.python.org/3.12/library/os.html#os.replace)
e as opções de [empacotamento/metadados do PyInstaller](https://pyinstaller.org/en/v6.22.0/usage.html).
Essas fontes orientam o tratamento de foco, a gravação por arquivo temporário e
a distribuição com dependências; não certificam o jogo nem substituem os testes.

Dependências mantidas no arquivo fixado do projeto: pygame-ce 2.5.8,
Python 3.12.14 e PyInstaller 6.22.3 neste ambiente. As páginas consultadas podem
exibir revisões de documentação distintas; o comportamento acima foi executado
com as versões instaladas.

Resultados estruturados: [RESULTADOS_1.3.0.json](RESULTADOS_1.3.0.json).
Evidências detalhadas: [testes e construção](evidencias-1.3.0/testes-e-build.txt),
[EXE nativo](evidencias-1.3.0/exe-nativo.json),
[EXE instalado](evidencias-1.3.0/exe-instalado.json) e
[integridade do pacote](evidencias-1.3.0/integridade-pacote.json).
