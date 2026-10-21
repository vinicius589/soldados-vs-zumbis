# Contribuir com Soldados vs Zumbis

O objetivo é fazer o jogo evoluir sem misturar mudanças inacabadas à versão que as pessoas baixam. Trabalhe em etapas pequenas, rode os testes e deixe registrado o que mudou e o que você realmente conseguiu verificar.

## Preparar o ambiente

Requisitos: Python 3.12, Git e, quando os recursos estiverem armazenados via Git LFS, Git LFS. Os passos completos estão em [GUIA-DEV-E-RELEASES.md](GUIA-DEV-E-RELEASES.md).

~~~bash
git clone https://github.com/vinicius589/soldados-vs-zumbis.git
cd soldados-vs-zumbis
git lfs install
git lfs pull
python -m venv .venv
~~~

Ative o ambiente virtual.

Windows PowerShell:

~~~powershell
.venv\Scripts\Activate.ps1
~~~

macOS/Linux:

~~~bash
source .venv/bin/activate
~~~

Instale dependências e ferramentas de desenvolvimento:

~~~bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install "pytest>=8.0" "ruff>=0.6"
~~~

Execute o jogo e as verificações pertinentes:

~~~bash
python run.py
python -m compileall -q src run.py
python -m ruff check src tests
python -m pytest -q
~~~

A suíte automatizada ajuda a detectar regressões, mas não substitui uma partida real. Depois de alterar interface, áudio, animações, mapas ou combate, confira o caminho afetado no jogo.

## Em qual branch trabalhar

Durante a transição, a base candidata é **migracao/base-jogavel**; consulte o [guia de branches](BRANCHING.md) antes de iniciar uma tarefa. Crie uma branch curta para cada mudança, como **fix/**, **refactor/**, **feat/**, **art/**, **docs/** ou **test/**.

As branches **historico/** são um arquivo de versões antigas e não devem receber novas funcionalidades. Não faça push direto em **main** e não use branches históricas como base de uma versão atual.

## Commits que explicam o que aconteceu

Um commit é um ponto salvo do trabalho. A mensagem precisa ajudar outra pessoa a entender a mudança sem abrir cada arquivo. Siga [COMMIT_CONVENTION.md](COMMIT_CONVENTION.md), por exemplo:

- **fix(combat): corrigir recarga depois do disparo**
- **refactor(assets): centralizar caminhos dos recursos**
- **test(campaign): cobrir o ciclo de ondas**
- **docs(history): registrar a origem das versões**

Evite mensagens genéricas como “arrumei”, “mudanças”, “teste” ou “versão final”. Sempre que possível, separe em commits diferentes uma correção, uma refatoração, uma nova funcionalidade e uma mudança de arte.

## Medir uma refatoração

Quando reduzir ou dividir código, registre antes e depois:

1. Quais módulos ou funções mudaram e por quê.
2. O que foi removido, consolidado ou separado.
3. Quantidade aproximada de linhas Python alteradas/removidas, sem contar assets binários.
4. Testes executados e seus resultados.
5. Quais mapas, cartas, animações, sons e comportamentos foram conferidos.
6. Qualquer diferença intencional de comportamento.

Reduzir linhas não é suficiente se quebrar uma mecânica ou tornar o código mais difícil de entender. Refatoração deve preservar o comportamento esperado e ganhar cobertura de teste quando isso fizer sentido.

## Pull Request

Cada Pull Request deve conter:

- **Motivo:** qual problema ou necessidade está sendo resolvido.
- **Mudanças:** o que foi alterado e onde.
- **Testes:** comandos executados e resultados reais.
- **Teste manual:** mapa, onda, unidade ou menu que foi aberto e conferido.
- **Riscos/pendências:** o que ficou sem verificar e por quê.

Não declare que a execução gráfica, a compilação Windows ou uma campanha completa passou se isso não foi executado. Espere a revisão e as verificações automáticas antes de integrar. Depois da integração, branches temporárias podem ser apagadas; tags e Releases marcam versões, não branches permanentes.

## Ao reportar um erro

Informe região, onda, unidade, passos para reproduzir e resultado esperado versus resultado observado. Capturas de tela, logs e gravações ajudam. Não envie dados pessoais nem saves de jogador.

## Cuidados com o projeto

- Mantenha textos e mensagens do jogo em português.
- Use a resolução de caminhos de recursos definida pelo projeto; não espalhe caminhos absolutos do seu computador.
- Durações de animação são medidas em segundos.
- Não envie executáveis, ambientes virtuais, saves pessoais, caches ou ZIPs de distribuição ao código-fonte.
- Não remova arte ou áudio que o jogo carrega em tempo de execução sem revisar manifesto, créditos, testes e a campanha.
- Para a história do jogo, consulte o README. Para a história técnica, consulte as branches históricas, as mensagens de commit e as Releases correspondentes.
