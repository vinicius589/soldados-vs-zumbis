# Desenvolvimento e construção

## Ambiente reproduzível

O jogador usa o executável pronto. Estes comandos destinam-se a quem vai modificar o código. O ambiente usado na construção foi Python 3.12.14, Windows x64.

Na raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test-lock.txt
.\.venv\Scripts\python.exe tools/manage.py test
.\.venv\Scripts\python.exe main.py
```

`requirements.txt` contém as dependências de execução. `requirements-dev.txt` inclui `requirements-test-lock.txt`, com Hypothesis e Coverage.py, além das dependências de construção. `requirements-build-lock.txt` registra todas as versões instaladas no ambiente de construção. Nenhum ambiente virtual é distribuído.

## Localizar uma alteração

| Responsabilidade | Arquivo em `src/svz/` |
|---|---|
| Inicialização e argumentos | `cli.py`, `paths.py` |
| Navegação e ciclo principal | `app.py` |
| Partida, ataques e habilidades | `battle.py` |
| Composição e avanço das ondas | `waves.py` |
| Desenho | `rendering.py` |
| Conteúdo, tropas e inimigos | `content.py`, `roster.py` |
| Entidades e tabuleiro | `entities.py`, `board.py` |
| Animações e cenários | `animation.py`, `production_animations.py`, `scenarios.py` |
| Imagens, áudio e memória | `assets.py`, `audio.py`, `cache.py` |
| Progresso | `persistence.py` |

`api.py` agrupa símbolos consumidos por testes e ferramentas. O jogo importa seus componentes diretamente; não introduza novas regras nessa fachada. Os nomes históricos de alguns arquivos de arte foram mantidos para preservar identidade e rastreabilidade, mas só os arquivos usados estão em `assets/`.

## Verificar e construir

```powershell
.\.venv\Scripts\python.exe tools/manage.py check
.\.venv\Scripts\python.exe tools/manage.py test
.\.venv\Scripts\python.exe tools/collect_licenses.py
.\.venv\Scripts\python.exe tools/manage.py build
.\.venv\Scripts\python.exe tools/manage.py package
```

`build` executa testes antes de gerar o executável e copia o resultado para a raiz. O empacotamento seleciona apenas executável, bibliotecas, recursos, instruções e créditos; fontes e testes continuam no projeto, fora do ZIP jogável. Escolha outro nome se um ZIP já existir.

Após trocar um recurso aprovado, atualize deliberadamente seu tamanho e SHA-256 em `assets/manifest.json`, execute os testes e examine a mudança visual. Não regenere o manifesto apenas para esconder uma falha de integridade.

O diagnóstico do próprio executável pode ser repetido sem usar Python:

```powershell
.\SoldadosVsZumbis.exe --headless --self-test reports/diagnostico.json
```

Ele confere os 109 hashes, carrega imagens/animações/áudio, desenha telas e executa passos nos três cenários. Use sem `--headless` para um ensaio automático com janela e dispositivo de áudio reais. O relatório só recebe `ok: true` ao concluir todas as verificações.

`SVZ_SAVE_PATH` altera o arquivo de save para integrações/testes. `SVZ_DATA_DIR` altera a pasta de registros. Testes usam caminhos temporários; o padrão do jogador fica em LocalAppData.

Para repetir o ensaio detalhado de telas, ondas e combates, use `python tools/regression.py --game-dir . --layout final --output-dir reports/regressao`. O arquivo `docs/REGRESSAO.json` guarda a referência desta entrega. O ensaio cria saves isolados dentro da pasta de saída e normaliza apenas o rótulo da versão para comparar imagens.

## Controle da versão

O número atual fica exclusivamente em `project.toml`; os módulos e o smoke test consultam essa origem. A suíte pode ser executada localmente ou em CI. A pasta entregue é local: esta tarefa não criou repositório, commit, tag, publicação ou assinatura digital.

Guarde marcos futuros em Git/tags e releases, sem recriar árvores completas de alfas e betas dentro do projeto ativo. `.gitignore` exclui saídas regeneráveis e ambientes. Na linha publicada a partir do commit `994ed2e`, os recursos são binários comuns no Git; `.gitattributes` não aplica filtro LFS. O ZIP jogável inclui os arquivos reais. Consulte [GITHUB_PASSO_A_PASSO.md](GITHUB_PASSO_A_PASSO.md) para o fluxo de envio e atualização.

O salvamento de partidas é descrito em SALVAMENTO_E_RETOMADA.md. Ao alterar o estado persistente, revise o schema em snapshot.py e os testes de retomada.


## Fluxo vigente da versão 1.3.3

Use Python 3.12 x64 em ambiente virtual e instale
`requirements-test-lock.txt`. Isso é necessário apenas para desenvolver.

```powershell
python tools/manage.py check
python tools/quality.py
python tools/manage.py build
python tools/manage.py package
```

O build executa a suíte antes de criar o EXE. `project.toml` é a única origem da
versão. `build-info.json` liga os fontes ao EXE e às bibliotecas. Não edite
fontes depois do build sem reconstruir. O empacotamento verifica os hashes e
executa o diagnóstico do próprio EXE. `reports/` guarda resultados temporários.

`settings.py` armazena preferências; `navigation.py` controla foco dos menus;
`ui_panels.py` desenha configurações/ajuda; `timing.py` limita passos da
simulação; `video.py` gerencia janela/tela cheia; `snapshot.py` valida o grafo
salvo; `session_store.py` mantém partida atual e anterior. `Battle` é a
autoridade para colocar/remover tropas e iniciar ondas.

Snapshots continuam no schema 1. Os saves 1.2.0 foram exercitados em processo
separado. Registros anteriores continuam no campo global; a interface os
identifica como “Anterior (geral)” quando falta informação da dificuldade.

`tools/benchmark.py` mede carga, memória e p50/p95/p99 em doze cenários
simulados. Seus tempos não representam FPS de apresentação em monitor real.
O fluxo `.github/workflows/windows.yml` executa testes no Windows se o projeto
for futuramente hospedado no GitHub; não houve publicação nem execução remota.
Os arquivos de arte são binários comuns no Git local, sem exigir Git LFS.

Pesquisa e contratos de teste: [PESQUISA-E-TESTES-1.3.3.md](PESQUISA-E-TESTES-1.3.3.md). O comando `quality.py` mede ramos e linhas, verifica limites por módulo e executa regressão e benchmark com saves isolados.
