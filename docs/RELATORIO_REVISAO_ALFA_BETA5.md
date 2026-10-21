# Relatório da revisão local — Alfa da Beta 5

**Estado:** pacote de código-fonte para revisão, ainda não aprovado como versão jogável.

## Base usada

A revisão parte do arquivo `SoldadosVsZumbis-Alfa-Beta-5-codigo-fonte.zip`, que contém a linha modular da Alfa Beta 5. Não é a Beta 4 monolítica e não tenta reconstruir as mudanças da Alfa a partir da Beta 4. O código foi mantido em `src/svz/`, e os recursos de execução foram mantidos conforme `assets/manifest.json`.

## Correções feitas nesta revisão

- Implementada a pintura da tela de perfil/loja e ligada ao despacho de telas do renderizador. Antes, as rotas de entrada e interação existiam, mas o estado `profile` não tinha uma tela completa para mostrar.
- Separadas visualmente as duas formas de consultar pontuação: o ranking usa seis campos (posição, jogador, pontos acumulados, partidas, vitórias e recorde); o histórico usa sete campos (data, jogador, região, dificuldade, onda, resultado e pontos). O desenho não tenta mais interpretar uma linha de ranking como uma linha de histórico.
- Alinhadas as áreas clicáveis dos botões do ranking/histórico, paginação e retorno com as áreas que o renderizador mostra.
- Corrigida a interação da loja para que clicar na descrição do item não compre o consumível. A compra acontece somente no botão de compra.
- Ajustado o tamanho da fonte dos botões ao espaço disponível: rótulos longos, como “VOLTAR À BASE”, agora reduzem a fonte para caber no controle, mantendo o estilo de interface existente.
- Forçado o registro de diagnóstico na inicialização empacotada, para que uma falha de abertura não resulte em um `jogo.log` vazio quando outra biblioteca já tiver configurado o logger raiz.
- Refeito `JOGAR.bat` para iniciar o código desta revisão e `PREPARAR_AMBIENTE.bat` para criar o ambiente local; acrescentado `CRIAR_EXE.bat` para compilar e validar um executável a partir do mesmo código no Windows.
- Removidos os arquivos locais `*.before` que eram cópias de comparação, não componentes do jogo.
- A tela de perfil carrega os dados do banco ao entrar, salvar, comprar ou consumir itens, e não em todos os quadros de renderização.
- Falhas ao consultar o perfil local passam a ficar visíveis. Se a preferência do nome não puder ser gravada, o jogo avisa que o nome vale apenas na sessão atual.
- Adicionado suporte a Ctrl+A para limpar o nome durante a edição do perfil.
- Corrigidos os índices usados nos testes do histórico: vitória e pontuação estavam sendo lidas nas posições erradas para o contrato atual de sete campos.
- Acrescentados testes para ranking agregado por jogador, renderização das duas estruturas de pontuação, abertura da tela de perfil sem jogador registrado e compra acionada apenas pelo botão.
- Removidas cópias de segurança locais `*.before`, caches e o ambiente virtual temporário do pacote final. Nenhum recurso que consta no manifesto de assets foi removido.

## Funcionalidades preservadas

- Salvamento local de campanha e snapshot de partida em andamento, com retomada e cópia anterior para recuperação.
- Nome local do jogador e ranking baseado na soma de pontos das partidas.
- Histórico de partidas, com região, dificuldade, onda, vitória/derrota e pontos.
- Créditos de loja separados dos pontos usados no ranking; a mesma partida não deve creditar pontos/créditos duas vezes.
- Kit médico consumível para uma tropa viva ferida e munição tática temporária para uma tropa que usa munição recarregável.
- Menus de história, personagens, campanha, configurações, perfil/loja, ranking/histórico, pausa e resultado.
- Recursos visuais e sonoros validados pelo manifesto de 109 arquivos.

## Verificações feitas aqui

| Verificação | Resultado |
|---|---|
| Parse sintático de arquivos Python por AST | Aprovado |
| `python -m compileall -q main.py src tests tools` | Aprovado |
| `python tools/manage.py check` | Aprovado — 109 recursos íntegros e 85 arquivos Python analisados |
| Ajustes adicionais desta entrega | Fonte de botões adaptativa, registro de inicialização forçado, `JOGAR.bat` e `PREPARAR_AMBIENTE.bat` atualizados |
| `python -m pytest -q tests/test_documentation_links.py tests/test_release_metadata.py` | Aprovado — 5 testes |
| `python tools/manage.py test` | **Bloqueado por dependências ausentes:** erros de importação de `pygame` e `hypothesis` durante a coleta; 37 testes chegaram a ser descobertos, mas a suíte não foi aprovada |
| Partida manual no Windows | **Pendente:** requer executar o pacote num computador com as dependências instaladas |

Os testes estáticos não comprovam que a janela, as animações, o áudio ou uma campanha completa funcionam. Não foi recompilado um executável a partir do código desta revisão nem criada uma Release. O artefato Windows anterior corresponde ao código-base 1.5.0 anterior a estas alterações; por isso não foi apresentado como executável atualizado.

## Próxima validação no Windows

Na pasta extraída do projeto, use Python 3.12 x64 e execute:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test-lock.txt
.\.venv\Scripts\python.exe tools/manage.py check
.\.venv\Scripts\python.exe tools/manage.py test
.\.venv\Scripts\python.exe main.py
```

Na partida manual, confira pelo menos: criar/trocar perfil, iniciar partida, salvar e continuar, terminar uma partida e comparar o ranking com o histórico, ganhar créditos, comprar item e utilizá-lo numa tropa válida. Antes de publicar, qualquer falha precisa ser corrigida e a suíte deve ser executada novamente.

## Situação do GitHub

Este arquivo descreve a revisão local. A `main` do repositório novo não foi alterada por esta revisão e não deve receber a Alfa Beta 5 até o pacote ser aprovado. O fluxo para copiar a pasta ao clone limpo, criar a branch, revisar e abrir Pull Request está em [GITHUB_PASSO_A_PASSO.md](GITHUB_PASSO_A_PASSO.md).
