# Levar a versão revisada para o novo repositório

Este documento descreve a preparação local após você revisar e aprovar o ZIP. A `main` atual do novo repositório tem apenas o commit inicial; a Alfa Beta 5 ainda não foi integrada nem publicada.

Repositório de destino: <https://github.com/vinicius589/soldados-vs-zumbis>

## 1. Preservar o original

Guarde o ZIP de revisão como cópia de segurança. Não apague nem reutilize a pasta da Beta 4. Não copie a pasta `.venv`, caches, logs ou executáveis antigos para o repositório de fontes.

## 2. Clonar a `main` limpa

Abra PowerShell na pasta onde você guarda projetos:

~~~powershell
git clone https://github.com/vinicius589/soldados-vs-zumbis.git
Set-Location soldados-vs-zumbis
git status --short --branch
~~~

A branch inicial é `main`. Antes de copiar os arquivos, confirme que o clone está limpo e que `origin` aponta para o repositório novo:

~~~powershell
git remote -v
git log --oneline --decorate -5
~~~

## 3. Criar a branch de revisão

~~~powershell
git switch -c feat/alfa-beta5-revisada
~~~

Extraia o ZIP corrigido em outra pasta. Copie o conteúdo dessa pasta para a pasta clonada, **sem copiar qualquer diretório `.git`** e sem sobrescrever a pasta `.git` do clone. A cópia deverá incluir `main.py`, `src/`, `assets/`, `tests/`, `tools/`, `docs/`, os arquivos de dependências e a documentação.

## 4. Conferir e testar antes do commit

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test-lock.txt
.\.venv\Scripts\python.exe tools/manage.py check
.\.venv\Scripts\python.exe tools/manage.py test
git diff --check
git status --short
git diff --stat
~~~

Não continue se a verificação de recursos ou os testes falharem. Se o teste da interface falhar, registre a mensagem exata e corrija antes de publicar o commit.

## 5. Registrar a mudança

~~~powershell
git add -A
git diff --cached --check
git diff --cached --stat
git status --short
git commit -m "fix: corrigir perfil e ranking da Alfa Beta 5"
~~~

Revise a lista preparada antes de confirmar. Não inclua `.venv/`, logs, saves de jogador, `dist/`, `build/` ou executáveis temporários.

## 6. Enviar a branch para revisão

~~~powershell
git push -u origin feat/alfa-beta5-revisada
~~~

Abra o GitHub, entre na branch enviada e use **Compare & pull request** para propor a integração em `main`. Confira os arquivos, os resultados do Actions e a descrição antes de fazer merge. O push da branch **não altera a `main` por conta própria**.

## Regra para tags e Releases

Não crie a tag final agora. Primeiro integre apenas após revisão e testes. Depois prepare o build Windows, execute a verificação do próprio executável e confira o ZIP extraído. A Release deve conter um único download principal para jogar, instruções de extração/abertura e notas sobre o que foi testado. Alfas, Betas antigas e materiais brutos não devem ser anexados todos juntos ao lançamento vigente.
