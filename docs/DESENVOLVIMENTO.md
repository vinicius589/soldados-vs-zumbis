# Desenvolvimento e construção

## Ambiente reproduzível

O jogador usa o executável pronto. Estes comandos destinam-se a quem vai modificar o código. O ambiente usado na construção foi Python 3.12.14, Windows x64.

Na raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build-lock.txt
.\.venv\Scripts\python.exe tools/manage.py test
.\.venv\Scripts\python.exe main.py
```

`requirements.txt` contém as dependências de execução. `requirements-dev.txt` acrescenta testes de imagem e empacotador. `requirements-build-lock.txt` registra todas as versões instaladas no ambiente de construção. Nenhum ambiente virtual é distribuído.

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
.\.venv\Scripts\python.exe tools/manage.py package --output dist/SoldadosVsZumbis-1.2.0-Windows-x64.zip
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

O número atual fica em `project.toml` e `src/svz/config.py`; ao lançar outra versão, altere ambos e a referência do smoke test. A suíte pode ser executada localmente ou em CI. A pasta entregue é local: esta tarefa não criou repositório, commit, tag, publicação ou assinatura digital.

Guarde marcos futuros em Git/tags e releases, sem recriar árvores completas de alfas e betas dentro do projeto ativo. `.gitignore` exclui saídas regeneráveis e ambientes; `.gitattributes` mantém os grandes recursos no Git LFS. O ZIP jogável inclui os arquivos reais e não depende de baixar LFS.

O salvamento de partidas é descrito em SALVAMENTO_E_RETOMADA.md. Ao alterar o estado persistente, revise o schema em snapshot.py e os testes de retomada.
