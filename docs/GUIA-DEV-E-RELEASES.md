# Guia de instalação, execução e publicação

Este guia é para quem quer executar o código ou contribuir com o desenvolvimento. O código-fonte fica nas branches do repositório; as Releases devem distribuir apenas pacotes de versão e explicar claramente como usá-los. Não é necessário duplicar todo o projeto-fonte como anexo em cada Release.

## 1. Requisitos para desenvolver

- Windows 10/11, macOS ou Linux.
- Python 3.12 (64-bit no Windows) e Git.
- Git LFS para baixar recursos históricos que tenham sido armazenados como objetos LFS.
- Conexão com a internet na primeira instalação, para baixar as dependências.

## 2. Baixar e preparar o projeto

Clone o repositório e entre na pasta:

~~~bash
git clone https://github.com/vinicius589/soldados-vs-zumbis.git
cd soldados-vs-zumbis
~~~

Se o clone contiver ponteiros Git LFS, instale o Git LFS e baixe os recursos reais:

~~~bash
git lfs install
git lfs pull
~~~

Crie e ative um ambiente virtual:

~~~bash
python -m venv .venv
~~~

No Windows PowerShell:

~~~powershell
.venv\Scripts\Activate.ps1
~~~

No macOS ou Linux:

~~~bash
source .venv/bin/activate
~~~

Instale as dependências do jogo:

~~~bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
~~~

## 3. Executar e verificar

O ponto de entrada atual da base modular é:

~~~bash
python run.py
~~~

Para verificar a sintaxe e a qualidade do código, instale as ferramentas de desenvolvimento:

~~~bash
python -m pip install "pytest>=8.0" "ruff>=0.6"
python -m compileall -q src run.py
python -m ruff check src tests
python -m pytest -q
~~~

Os comandos automatizados não substituem o teste gráfico. Depois de mexer em menus, arte, áudio, animações ou combate, inicie o jogo e teste o caminho afetado. Se alguma dependência, comando ou ponto de entrada mudar, este guia e o README precisam ser atualizados no mesmo Pull Request.

## 4. Como contribuir

1. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) e [COMMIT_CONVENTION.md](COMMIT_CONVENTION.md).
2. Atualize a branch que será a base do seu trabalho e crie uma branch específica para a tarefa.
3. Faça uma mudança por vez: correção, refatoração, recurso, arte, teste ou documentação.
4. Acrescente ou atualize testes quando houver alteração de comportamento.
5. Descreva no Pull Request o problema, o que mudou, os comandos executados e o que foi testado manualmente.
6. Integre somente depois da revisão e das verificações necessárias.

Não coloque executáveis, ambientes virtuais, saves pessoais, caches ou ZIPs de distribuição dentro do código-fonte. Os binários de versões publicadas pertencem às Releases.

## 5. Como ler Tags e Releases

No GitHub, **uma tag é um marcador de um commit específico**. Ela identifica exatamente qual código corresponde à versão. A tag não armazena um executável e não deve ser criada apontando para um código diferente apenas para aproveitar um nome de versão.

Uma **Release** é a página pública ligada a uma tag. Ela pode conter notas, instruções, checksum e anexos para baixar. O plano de publicação é:

- Tags com nomes claros, como **vX.Y.Z** para versões estáveis ou **vX.Y.Z-alpha.N** / **vX.Y.Z-beta.N** para prévias, sempre associadas ao commit correto.
- Uma Release por versão aprovada, com um pacote executável e/ou jogável como anexo quando esse pacote tiver sido gerado e verificado.
- Notas em português que expliquem o que mudou, como executar o pacote, os requisitos, a plataforma testada e os problemas conhecidos.
- Checksum SHA-256 para que seja possível conferir o download.
- Nenhuma alegação de teste manual, compatibilidade ou executável original sem comprovação.

Para as versões históricas, os pacotes preservados de cada Alfa/Beta serão associados ao respectivo marco somente depois de confirmar a pasta original e os recursos necessários. A Beta 1 original está documentada, mas seu código e executável não foram localizados; não haverá pacote reconstruído e apresentado como original. Os ZIPs históricos existentes também podem conter diversas versões em pastas independentes; eles não serão renomeados como um único executável de outra versão.

## 6. Modelo das notas de Release

Cada Release deve seguir uma estrutura parecida com esta:

~~~markdown
## O que mudou
- Mudanças de código e funcionalidades desta versão.

## Baixar e executar
1. Baixe o anexo correspondente ao seu sistema.
2. Extraia o pacote, se for ZIP.
3. Siga as instruções específicas incluídas no pacote.

## Para desenvolvedores
- Link para a branch/tag do código-fonte.
- Requisitos e passos de instalação: docs/GUIA-DEV-E-RELEASES.md.
- Testes executados e resultado.

## Validação
- Plataforma testada:
- Teste automatizado:
- Teste gráfico/manual:
- Limitações conhecidas:

## Integridade
- SHA-256 do arquivo distribuído.
~~~

A página de Release não deve ser usada para guardar todo o código-fonte nem substituir a documentação de desenvolvimento. Ela funciona como o histórico da versão publicada e ponto de download do pacote correspondente.
