# Contribuir com Soldados vs Zumbis

O objetivo é desenvolver o jogo sem misturar mudanças inacabadas com a versão que as pessoas baixam. Faça alterações pequenas, rode os testes e explique o que você verificou.

## Preparar o ambiente

Requisitos: Python 3.12 ou superior e Git.

~~~bash
git clone https://github.com/vinicius589/soldados-vs-zumbis.git
cd soldados-vs-zumbis
python -m venv .venv
~~~

Ative o ambiente virtual:

~~~powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
~~~

~~~bash
# macOS / Linux
source .venv/bin/activate
~~~

Instale as dependências e inicie o jogo:

~~~bash
python -m pip install -r requirements.txt
python run.py
~~~

Para instalar as ferramentas de desenvolvimento e executar as verificações:

~~~bash
python -m pip install "pytest>=8.0" "ruff>=0.6"
python -m compileall -q src run.py
python -m ruff check src tests
python -m pytest -q
~~~

Os testes automatizados ajudam a proteger o conteúdo e as regras do jogo, mas não substituem uma partida real. Depois de alterar interface, áudio, animações ou combate, abra o jogo e confira o comportamento afetado.

## Como trabalhar

1. Atualize main e crie uma branch curta para sua mudança: feat/, fix/, refactor/, art/, docs/ ou test/.
2. Faça commits objetivos, seguindo a convenção em COMMIT_CONVENTION.md.
3. Atualize ou escreva testes quando mudar comportamento.
4. Abra um Pull Request para main, explicando o motivo da mudança, o que foi alterado e como foi testado.
5. Espere a revisão e as verificações automáticas antes de integrar.
6. Apague branches temporárias depois de integradas. Use tags e Releases para marcar versões; não crie uma branch permanente para cada versão.

## Ao reportar um erro

Informe a região, a onda, a unidade envolvida, o que você fez e o que aconteceu. Capturas de tela ou gravações ajudam a reproduzir o problema. Não marque uma validação manual como concluída se ela não foi executada.

## Cuidados com os arquivos

- Mantenha textos e mensagens do jogo em português.
- Use asset_paths.game_root() para encontrar os recursos.
- Durações de animação são medidas em segundos.
- Não envie executáveis, ambientes virtuais, saves de jogador, arquivos temporários ou cópias de pacotes ao código-fonte.
- Não remova recursos que o jogo carrega em tempo de execução sem validar a campanha e os testes.