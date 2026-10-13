# Revisão geral — Soldados vs Zumbis 1.2.0

Data: 11/10/2026. Projeto examinado: `C:\Users\phill\Documents\ChatGPT\Criaçao de Jogo\Sodados_vs_Zumbis`.

**Parecer: corrigir os problemas de controle e progressão antes do lançamento final.** A versão passa nos testes existentes, mas a auditoria encontrou **nove problemas confirmados**, incluindo falhas que esses testes não cobrem. A investigação incluiu código, execução isolada, imagens da interface, integridade do ZIP e pesquisa em fontes primárias. É uma revisão abrangente, não uma prova de que todos os defeitos possíveis foram encontrados.

Esta entrega documenta os problemas e propõe sua solução. Não aplica correções ao jogo. Os ensaios usaram salvamentos temporários; o progresso pessoal ficou preservado.

## 1. Defeitos e limitações funcionais confirmados

Prioridade **P1**: corrigir antes de divulgar a versão final, pois afeta regras centrais. **P2**: corrigir na revisão de qualidade, pois prejudica funcionamento, informação ou recuperação. Não foi identificado um defeito P0 que afete todas as inicializações normais.

| ID | Prioridade | Problema | Evidência |
|---|---|---|---|
| D01 | P1 | Mouse permite colocar a mesma carta durante a recarga de 10 segundos | Duas unidades colocadas consecutivamente; teclado permite apenas uma. Reproduzido nas 9 combinações de mapa/dificuldade. |
| D02 | P1 | Partida pausada aceita ações de jogo pelo teclado | Posicionamento, remoção e início de onda funcionam durante a pausa; Espaço também inicia onda no modo mouse. Reproduzido nas 9 combinações. |
| D03 | P2 | Enter não confirma o resultado no modo teclado | Na vitória, Enter continua no estado de batalha e pode colocar uma unidade. Reproduzido nas 9 combinações. |
| D04 | P2 | Melhor onda não é registrada após derrota | Derrota efetiva na onda 7 retorna ao mapa com registro vazio, exibindo onda 0/12. |
| D05 | P2 | Operação exclusivamente por teclado fica incompleta | Confirmação de nova partida ignora Enter; menus, abas e detalhes dependem do mouse. |
| D06 | P2 | Ajuda ensina uma etapa de seleção que foi removida | “Como jogar” orienta escolher até três tropas no carrossel; o fluxo real entrega oito cartas e entra diretamente na partida. |
| D07 | P2 | Tela de dificuldade apresenta valores antigos | Suprimentos e limites escritos manualmente divergem dos perfis usados pela partida. |
| D08 | P2 | Textos das cartas excedem sua área no HUD | 11 métricas ultrapassam a largura disponível no ambiente examinado; há sobreposição/corte visível. |
| D09 | P2 | Arquivo de campanha profundamente aninhado não é recuperado | JSON artificial de 10.001 bytes causa `RecursionError` em `load_save`; exceção não é tratada nessa função. |

### D01 — Recarga ignorada pelo mouse

**Como reproduzir:** iniciar qualquer mapa, manter uma carta selecionada e clicar em duas casas livres seguidas, dispondo de recursos. A segunda tropa aparece mesmo com o contador marcando 10 segundos. A preparação automatizada usa 999 suprimentos para isolar a regra; o problema também é viável com os recursos iniciais normais e uma carta barata.

**Causa:** [Battle.place, linha 199](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/battle.py:199>) valida terreno, ocupação e custo, mas não recarga. O mouse verifica recarga ao selecionar a carta, porém não ao posicioná-la na casa. O teclado faz sua própria verificação em [Game.handle_key, linha 353](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:353>).

**Correção proposta:** validar recarga dentro da ação de posicionamento, compartilhada pelos dois controles. Fazer a operação retornar sucesso/falha e uma razão. Não basta adicionar outra condição somente no clique.

**Aceite:** nenhum recurso é debitado e nenhuma unidade é criada durante recarga; após dez segundos simulados a colocação volta a funcionar, em todos os mapas/dificuldades e pelos dois controles.

### D02 — Pausa não bloqueia os comandos

**Como reproduzir:** selecionar Teclado, iniciar partida, pressionar P, depois Enter numa casa vazia. A unidade aparece. R e Enter removem uma tropa e reembolsam recursos. N inicia uma onda. No modo Mouse, P seguido de Espaço também inicia a onda enquanto a partida continua marcada como pausada.

**Causa:** [handle_key, linha 324](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:324>) aceita ações sem uma barreira de pausa. [Battle.handle_click, linha 1896](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/battle.py:1896>) tem essa barreira, produzindo comportamentos diferentes.

**Correção proposta:** estados explícitos de partida e validação comum das ações. Durante a pausa, permitir retomar, ir ao menu e mudar vídeo; decisões de combate devem seguir uma regra única e documentada. O comentário atual de `Battle.update` promete congelamento.

**Aceite:** colocar, remover e iniciar onda não alteram unidades, suprimentos, onda ou recarga durante a pausa; o teste deve passar por eventos reais de entrada, incluindo Espaço no modo mouse.

### D03 — Enter é consumido antes de concluir a partida

**Como reproduzir:** concluir uma partida no modo Teclado e pressionar Enter. O ramo de posicionamento recebe a tecla antes do ramo de conclusão. Na reprodução controlada de vitória, a cena permaneceu `battle`, uma unidade foi acrescentada e a conclusão não foi registrada.

**Local:** [app.py, linha 353](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:353>) e [linha 376](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:376>).

**Impacto:** o resultado não responde à confirmação esperada pelo teclado e o campo terminado ainda aceita alterações. Há alternativas atuais: clicar no botão do resultado ou usar Esc. Portanto, não é um bloqueio absoluto sem saída.

**Correção/aceite:** tratar o estado terminado antes dos comandos de combate; Enter deve concluir o resultado uma única vez. Testar vitória e derrota, com mouse e teclado, sem permitir novas unidades ou reembolso após o término.

### D04 — Recorde intermediário é perdido

**Evidência:** um invasor foi colocado além da última defesa, com a contenção já gasta, provocando derrota real na onda 7. Após `finish_battle()`, o registro em disco de `best_wave` continuou vazio.

**Causa:** [finish_battle, linha 672](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:672>) atualiza campanha apenas dentro do ramo de vitória, sempre para 12. A tela [draw_campaign, linha 224](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:224>) promete mostrar “Melhor: onda”.

**Correção proposta:** definir se o recorde significa “onda alcançada” ou “onda concluída”, gravá-lo também na derrota e manter o maior valor. A vitória continua sendo registrada separadamente.

**Aceite:** derrota na onda 7 deve mostrar 7, se a regra for alcançada, ou 6, se concluída; nunca 0. Um recorde anterior maior deve sobreviver a uma derrota posterior.

### D05 — Modo teclado não cobre toda a navegação

**Evidência:** após pedir uma nova partida com uma partida suspensa, Enter mantém a cena `confirm_new`. [app.py, linha 293](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:293>) ignora todas as teclas de confirmação por escolha explícita do código. O menu principal também não possui foco navegável para acessar todas as opções; as abas regionais de personagens e os detalhes por hover dependem do ponteiro.

É uma **limitação funcional confirmada**, não um travamento geral. Para quem precisa operar só pelo teclado, porém, impede completar o fluxo.

**Correção proposta:** foco visível, Tab/setas, Enter e Esc consistentes. Em confirmação destrutiva, iniciar com foco em Cancelar e exigir uma ativação deliberada da opção de confirmar; isso preserva a proteção contra descarte acidental.

**Aceite:** abrir configurações, escolher mapa, consultar tropas/inimigos, retomar, confirmar nova partida e sair sem mouse. A ficha de carta deve aparecer também quando selecionada/focada por teclado.

### D06 — Tutorial incompatível com o fluxo atual

**Local/evidência:** [draw_howto, linha 618](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:618>), imagem [como jogar](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/howto.png>), comparados com [enter_selection, linha 557](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:557>). A ajuda mantém a seleção de três cartas; a implementação entrega oito imediatamente.

**Correção/aceite:** explicar equipe regional de oito cartas, colocação, dois tipos de recarga, remoção, pausa, retorno ao menu, Continuar e F11. Ler a ajuda e executar suas instruções deve funcionar na versão distribuída. Preferir “tropa indicada contra a defesa inimiga” ou explicar o termo “counter”.

### D07 — Dificuldade com números contraditórios

| Dificuldade | Início escrito na tela | Início real | Limite escrito | Limite real |
|---|---:|---:|---:|---:|
| Fácil | 175 | 320 | 420 | 650 |
| Médio | 135 | 240 | Não informado no item | 430 |
| Difícil | 105 | 190 | 240 | 330 |

Os resumos inferiores já usam os perfis atuais, portanto a mesma tela se contradiz.

**Local:** [rendering.py, linha 166](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:166>) versus [content.py, linha 638](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/content.py:638>). Ver [imagem da dificuldade](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/difficulty.png>).

**Correção/aceite:** gerar todas as quantidades exibidas a partir de `difficulty_profile`. Conferir a tela contra os recursos da partida para os três modos. Não alterar o balanceamento apenas para fazer os textos antigos coincidirem.

### D08 — Métricas ultrapassam as cartas

**Evidência:** [HUD da Cidade](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/hud-city.png>). O espaço após o retrato é de 80 pixels; “GÁS EM ÁREA • ALC 3” mede 98 e “SEM MUNIÇÃO • ALC 1” mede 102 no ambiente testado. A medição encontrou 11 métricas largas demais, somando os três mapas. A carta seguinte é desenhada por cima de parte do texto.

**Local:** [draw_battle_top, linha 800](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:800>). As fontes vêm de `SysFont`; métricas podem variar entre máquinas.

**Correção/aceite:** reorganizar as métricas em linhas ou abreviações compreensíveis e manter ficha completa acessível por foco/hover. Verificar limites geométricos e imagens a 1280×720 e nas escalas físicas suportadas. Reduzir ainda mais a fonte de 11 pixels pioraria a legibilidade.

### D09 — Recuperação incompleta de campanha inválida

**Reprodução isolada:** arquivo temporário contendo 5.000 listas aninhadas (`[` repetido 5.000 vezes, `0` e os fechamentos). A leitura lançou `RecursionError`. Um caso de 2.000 níveis foi aceito pelo decodificador e normalizado; o limite não deve ser presumido pela quantidade isolada de níveis.

**Local:** [load_save, linha 45](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/persistence.py:45>). O tratamento captura `OSError` e `ValueError`, mas não `RecursionError`, e lê o arquivo inteiro. A leitura de partida em `SessionStore` já possui limite de tamanho e captura essa exceção.

**Impacto:** esse arquivo inválido, se colocado como campanha, pode impedir a inicialização até ser reparado; a exceção propaga para o tratador geral da CLI. Não foi encontrado arquivo pessoal corrompido nem uma falha observada durante uma gravação normal.

**Correção/aceite:** limitar leitura, tratar profundidade inválida, preservar o arquivo problemático e mostrar aviso recuperável. Testar JSON truncado, estrutura profunda, tipos errados e arquivo grande. Preservar a gravação por temporário e substituição já existente.

## 2. Melhorias recomendadas

As propostas abaixo são melhorias de produto/manutenção, distintas dos nove problemas acima. A prioridade é minha avaliação aplicada a este projeto, não uma exigência automática das fontes.

| ID | Melhoria | Aplicação concreta e validação |
|---|---|---|
| M01 | Lembrar controles e áudio | Hoje reiniciar troca Teclado por Mouse, som desligado por ligado e volume 20% por 65%. Usar preferências versionadas para controles, volume e vídeo; testar um segundo processo. |
| M02 | Pausar ao perder foco | Um evento de perda de foco deixou a partida ativa; o intervalo passou de 2,5 para 1,5 s. Oferecer pausa automática ao minimizar/alternar aplicativo e retomada deliberada. Tratar os eventos oficiais de janela do Pygame. |
| M03 | Acessibilidade da interface | Fonte ajustável, contraste configurável, informação além da cor e ficha acessível sem hover. As fontes atuais incluem 11 e 13 px na imagem lógica. Validar conteúdo completo após aumento de texto. |
| M04 | Personalizar entradas e áudio | Remapear ações; depois avaliar controle/gamepad. Separar volumes de música, ambiente e efeitos. Acrescentar opção de reduzir tremores/efeitos e sinais visuais para alertas importantes. |
| M05 | Salvamento com contexto e recuperação | Exibir mapa, dificuldade, onda e horário em Continuar. Acrescentar salvamento manual, uma cópia anterior recuperável e, se útil, múltiplos slots. Manter schema e migrações explícitas. |
| M06 | Simulação menos dependente do FPS | O loop limita cada passo a 0,05 s: com 10 quadros/s, dez segundos reais só avançam cinco simulados. Avaliar acumulador com passos fixos e limite de atualizações por quadro. Testar sequências temporais e evitar excesso de atualizações após Alt+Tab. |
| M07 | Arquitetura proporcional ao jogo | Centralizar ações e estados, extrair partes de combate/renderização conforme responsabilidade e retirar trechos comprovadamente mortos. Preservar a separação existente de ondas, áudio, vídeo, recursos e persistência. |
| M08 | Medir desempenho antes de otimizar | Registrar tempo de carga, memória e tempos de quadro p50/p95/p99 por mapa e onda, com hardware/resolução anotados. Investigar superfícies e efeitos recriados por quadro; expandir caches somente onde a medição justificar. |
| M09 | Balanceamento com partidas completas | Medir mortes por onda, economia, tempo para eliminar chefes e uso das 24 cartas regionais. Fazer sessões humanas nos nove cenários de dificuldade/mapa. O ensaio de 108 ondas confirma progressão, não a qualidade da dificuldade. |
| M10 | Melhor orientação tática | Tutorial jogável curto, prévia opcional da próxima onda, indicadores claros de munição versus recarga da carta e explicação de imunidades. Informações de tropas/inimigos devem estar disponíveis durante a decisão de combate. |
| M11 | Progresso mais informativo | Depois de corrigir D04, registrar resultados por dificuldade, estatísticas da partida e objetivos concluídos. Evitar misturar uma vitória fácil com um recorde difícil sem identificação. |
| M12 | Testes por comportamento e sequência | Cobrir mapa × dificuldade × controle × estado; eventos físicos com escala de vídeo; vitória/derrota; cliques rápidos; pausa → menu → reinício → Continuar. Usar dados temporários e testes determinísticos. |
| M13 | Entrega Windows rastreável | Uma origem para a versão, identificador da revisão/fontes dentro do build, pasta nova a cada empacotamento e comparação de todos os arquivos. Acrescentar ícone/metadados do produto e avaliar assinatura para distribuição. |
| M14 | Histórico e documentação de manutenção | Inicializar controle de versão, registrar marcos/tags e automatizar testes em Windows. Atualizar o mapa de módulos para incluir vídeo, snapshots e retomada. Guardar relatórios históricos datados e uma referência inequívoca para a versão vigente. |

Sobre M06: os números são uma consequência calculada do código em [app.py:211](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/app.py:211>), não um benchmark que mostre este computador rodando a 10 FPS.

Sobre M07: `rendering.py` tem 2.346 linhas; `battle.py`, 1.934; `content.py`, 1.790. Tamanho não é defeito por si só, mas recomenda divisões graduais orientadas pelos problemas encontrados. Há código inalcançável após `return` em [draw_reload_action:1342](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:1342>) e [draw_weapon_action:1415](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/src/svz/rendering.py:1415>), além de seleção/dossiês legados. Não apagar arquivos de arte pelo nome “beta”: recursos com nome histórico continuam usados e fazem parte do manifesto.

## 3. Riscos de manutenção e pontos ainda não comprovados

| Ponto | O que foi verificado | O que permanece pendente |
|---|---|---|
| Vídeo e áudio reais | Executável e Pygame mínimo falharam com `No displays available` nesta sessão; o diagnóstico com drivers simulados passou | Executável em desktop interativo, áudio audível, Alt+Tab, DPI, múltiplos monitores e OpenGL |
| Correspondência fontes/binário | Os 289 arquivos do ZIP coincidem com a raiz e a cópia extraída; versão interna 1.2.0 | O comando `package` não vincula o EXE ao hash da revisão dos fontes; uma edição futura pode ser empacotada com binário antigo |
| Limpeza de bibliotecas | [manage.py:66](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/tools/manage.py:66>) copia `_internal` com `dirs_exist_ok=True` | Bibliotecas removidas de um build futuro podem sobrar na pasta anterior; não foi encontrada divergência no pacote atual |
| Distribuição pública | EXE sem assinatura Authenticode e sem metadados de versão/produto na inspeção | Política de distribuição, instalador opcional e ensaio em máquina limpa; não significa que o EXE esteja defeituoso ou seja inseguro |
| Desempenho e equilíbrio | Ensaios de lógica e imagens passaram | FPS real, sessões longas, consumo máximo de memória e campanhas humanas completas não foram medidos |
| Salvamentos futuros | JSON versionado, tipos permitidos, temporário + flush/fsync + substituição | Migração entre mudanças de schema, recuperação de cópia anterior e conflito entre duas instâncias abertas |
| Fontes visuais | Uso de fontes do sistema confirmado | A aparência pode variar no Windows de outro jogador; escolher e distribuir uma fonte apropriada torna o layout previsível |

## 4. Pesquisa em fontes confiáveis e decisões aplicáveis

Foram priorizadas documentações oficiais e material do próprio autor. As diretrizes Xbox são referências de qualidade/acessibilidade aplicáveis ao raciocínio do projeto; não são apresentadas como uma certificação deste jogo para Xbox.

| Fonte primária consultada | O que sustenta nesta revisão |
|---|---|
| [Pygame-ce — eventos](https://pyga.me/docs/ref/event.html) | Processar eventos a cada quadro e tratar eventos de perda de foco/minimização. O jogo já processa a fila; falta uma política de foco. |
| [Robert Nystrom — State, fonte do livro](https://raw.githubusercontent.com/munificent/game-programming-patterns/master/book/state.markdown) | Organizar transições pelo estado atual reduz combinações inválidas e condicionais dispersas. Aplicação: validar pausa/término antes de executar comandos. |
| [Robert Nystrom — Game Loop, fonte do livro](https://raw.githubusercontent.com/munificent/game-programming-patterns/master/book/game-loop.markdown) | Separar cadência de simulação e apresentação, com passos fixos e limite de recuperação. Aplicação: M06, depois de medir e criar testes temporais. |
| [Microsoft XAG 112 — navegação](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/112) | Navegação consistente, foco previsível e operação por entradas digitais. Aplicação: D05 e fichas acessíveis por teclado. |
| [Microsoft XAG 101 — texto](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/101) | Texto legível e redimensionável sem perda de conteúdo. A referência para PC a 1080p é 18 px; o tamanho físico e a escala precisam ser considerados. Aplicação: D08/M03. |
| [Microsoft XAG 107 — entradas](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/107) | Remapear ações e oferecer alternativas de controle. Aplicação: M04 após completar os fluxos atuais. |
| [Microsoft XAG 108 — dificuldade](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/108) | Dificuldade acessível, pausa e opções de salvamento. Aplicação: M05/M09; os três modos atuais não são classificados como bug por serem três. |
| [Microsoft XAG 117 — movimento/efeitos](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/117) | Opções para reduzir distrações visuais e movimento. Aplicação: tremores e intensidade de efeitos configuráveis. |
| [Python 3.12 — JSON](https://docs.python.org/3.12/library/json.html) | Limitar dados decodificados e tratar entradas inválidas. Aplicação: D09 e testes de recuperação. |
| [Python 3.12 — os.replace](https://docs.python.org/3.12/library/os.html#os.replace) | Substituição de arquivo de destino. Aplicação: preservar o padrão atual de gravação com arquivo temporário, sem alegar proteção absoluta contra falhas de hardware. |
| [Python 3.12 — unittest](https://docs.python.org/3.12/library/unittest.html) | Casos independentes, fixtures, subtestes e automação. Aplicação: M12 e inclusão das reproduções encontradas. |
| [PyInstaller — funcionamento](https://pyinstaller.org/en/stable/operating-mode.html) e [uso](https://pyinstaller.org/en/stable/usage.html) | O pacote inclui interpretador e dependências; opções de construção e metadados. Aplicação: continuar entregando Windows sem exigir Python externo. |
| [Microsoft — SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool) | Assinar, verificar e carimbar arquivos de distribuição. Aplicação opcional de M13; assinatura não é uma correção dos bugs de jogo. |
| [Git — controle de versão](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control) | Histórico recuperável de alterações e comparação entre versões. A pasta examinada não contém repositório `.git`. |

As APIs consultadas do Pygame incluem documentação publicada como 2.5.9; a execução foi feita com a dependência fixada do projeto, **pygame-ce 2.5.8**. Nenhuma atualização de dependência foi aplicada por causa da pesquisa.

## 5. Arquitetura recomendada para as correções

A base modular atual é adequada ao porte do jogo. A principal mudança deve ser a forma como comandos e estados são validados.

Fluxo proposto:

`evento de mouse/teclado → ação do jogador → validação do estado da partida → alteração do modelo → feedback visual/sonoro`.

`Game` continua controlando cenas e comandos globais. `Battle` passa a ser a autoridade para colocar, remover e iniciar onda, validando pausa, término, custo e recarga. O renderizador apenas apresenta o estado. Os dois dispositivos de entrada chamam as mesmas ações. A tela de resultado recebe Enter antes dos comandos de combate.

Depois, dividir o renderizador em telas de menu, HUD e combate; extrair habilidades/efeitos do combate quando houver testes cobrindo o comportamento. Manter conteúdo e balanceamento em definições centrais e produzir os textos numéricos a partir delas. Criar um armazenamento pequeno de preferências, reutilizando gravação segura.

Não há evidência nesta auditoria de que trocar de engine ou adotar um ECS completo traria benefício superior a essas mudanças localizadas.

## 6. Ordem de execução sugerida

1. **Regras e progressão:** D01–D04, com testes que primeiro reproduzam cada falha e depois comprovem a correção. Centralização de ações deve ocorrer aqui.
2. **Uso e informação:** D05–D09, preferências persistentes e pausa ao perder foco. Verificar novamente tutorial, dificuldade, HUD e teclado.
3. **Validação de lançamento:** suíte completa, diagnóstico do EXE, ZIP extraído em máquina limpa e ensaios audiovisuais reais. Jogar as nove combinações até vitória/derrota, registrando balanceamento.
4. **Evolução planejada:** acessibilidade ampliada, melhorias de salvamento, medição de desempenho, refatoração gradual e automação do build.

Uma próxima versão só deve ser considerada pronta após corrigir os defeitos escolhidos para o lançamento e registrar o resultado dos testes nativos pendentes.

## 7. Testes executados e limites

| Verificação atual | Resultado |
|---|---|
| Análise sintática e integridade | 49 arquivos Python analisados; 109 recursos íntegros |
| Suíte `manage.py test` | 141 testes passaram em 60,496 s |
| Smoke test | Passou para versão, regiões, grade, inspeção e counters |
| Ensaio estendido | 9 cenários de combate, 108 ondas geradas/progredidas e 28 capturas; passou |
| Integridade da distribuição | 289 arquivos verificados no ZIP; nenhum divergente na raiz ou cópia extraída |
| Diagnóstico do EXE sem tela | Passou: recursos, navegação, remoção e alternância de vídeo/mapeamento de entrada simulados |
| Reprodução adicional | D01–D03 reproduzidos nas nove combinações; D04 por derrota efetiva; D05 por entrada; D06–D08 por código/imagens/medição; D09 por arquivo inválido isolado |
| Inspeção visual | Imagens de HUD, dificuldade, ajuda, campanha, configurações e personagens examinadas |
| EXE e Pygame com vídeo nativo | Não concluídos: `pygame.error: No displays available` em ambos |

**Interpretação:** passar nos 141 testes não elimina os nove problemas; a suíte ainda não contém esses casos negativos. No ensaio de 108 ondas, inimigos são retirados após a confirmação do nascimento para acelerar a progressão. O combate é verificado separadamente. Isso não equivale a vencer nove campanhas jogando normalmente.

Áudio carregado com driver simulado não comprova que o som foi ouvido. Capturas lógicas e testes de tela cheia com driver dummy não comprovam comportamento de monitor, GPU, DPI ou Alt+Tab reais. Nenhuma taxa de cobertura de código foi medida.

ZIP examinado: `SoldadosVsZumbis-1.2.0-Windows-x64.zip`.

SHA-256: `acf488a2f33fec65b6ba8337f0c81acb421b4c607e97b40357e1359bace1c6fd`.

## 8. Evidências e reprodução

- [Resultados das reproduções e integridade](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/evidencias-revisao.json>)
- [Medições de HUD, derrota e campanha inválida](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/evidencias-adicionais.json>)
- [Log da suíte](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/suite.log>)
- [Relatório do ensaio estendido](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/regressao.json>)
- [Diagnóstico do executável](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/exe-headless.json>)
- [Resultado das execuções do EXE](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/exe-runs.json>)
- [Falha nativa no jogo](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/native-game.log>) e [no Pygame mínimo](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/native-pygame.log>)
- [Script da auditoria](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/audit.py>) e [ensaios adicionais](<C:/Users/phill/Documents/ChatGPT/Criaçao de Jogo/Sodados_vs_Zumbis/docs/revisao-geral-2026-10-11/audit-extra.py>)

Os scripts recebem o caminho do projeto como primeiro argumento, usam arquivos temporários e escrevem evidências ao lado do próprio script. Requerem o ambiente de desenvolvimento descrito em `docs/DESENVOLVIMENTO.md`. São instrumentos de diagnóstico; registram o comportamento observado e não corrigem os problemas. As capturas do primeiro script usam 999 suprimentos para isolar regras; as imagens `hud-city.png`, `hud-desert.png` e `hud-beach.png` preservadas nesta entrega mostram os recursos iniciais normais.

