# Soldados vs Zumbis — 1.2.0

Jogo de defesa por faixas para **Windows x64**. Escolha um dos três territórios, posicione tropas e sobreviva às 12 ondas de cada campanha.

## Jogar

Abra **SoldadosVsZumbis.exe** ou **JOGAR.bat**. Não é necessário instalar Python. Mantenha `assets/` e `_internal/` junto do executável. As instruções e os controles estão no menu **COMO JOGAR**.

O pacote para enviar a outras pessoas fica em `dist/SoldadosVsZumbis-1.2.0-Windows-x64.zip`. O destinatário deve extrair a pasta inteira e abrir o executável.

## Organização

| Caminho | Finalidade |
|---|---|
| `SoldadosVsZumbis.exe`, `JOGAR.bat` | Abrir o jogo |
| `assets/` | Somente os 109 recursos usados pela versão final e seu manifesto de integridade |
| `_internal/` | Python e bibliotecas incluídos no executável; não mover isoladamente |
| `src/svz/` | Código-fonte organizado por responsabilidade |
| `tests/` | Testes da versão final |
| `tools/` | Verificação, construção e empacotamento |
| `docs/` | Pesquisa, decisões e resultados de validação |
| `licenses/`, `CREDITOS.md` | Avisos das bibliotecas e procedência do áudio |
| `dist/` | ZIP para distribuição e checksum |

O progresso é salvo em `%LOCALAPPDATA%\SoldadosVsZumbis\campanha.json`; erros ficam em `jogo.log`, na mesma pasta. Esses dados pessoais não integram o ZIP.

Para manutenção, consulte [DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md). A pesquisa e as evidências desta organização estão em [LANCAMENTO_E_VALIDACAO.md](docs/LANCAMENTO_E_VALIDACAO.md).

## Retomar uma partida

Use **CONTINUAR** no menu. A partida volta pausada; clique em **PAUSA** ou pressione **P**. Funciona também após fechar e abrir o jogo. O salvamento ocorre a cada dez segundos e ao sair normalmente; iniciar outra partida exige confirmação para substituir a atual.

Confira a pesquisa e o funcionamento em [SALVAMENTO_E_RETOMADA.md](docs/SALVAMENTO_E_RETOMADA.md). Os documentos da versão 1.0.0 registram a organização anterior; a validação do salvamento fica em `docs/RESULTADOS_RETOMADA.json`.

## Remover tropas

O botão **REMOVER**, entre **PAUSA** e **PRÓXIMA**, funciona em todas as dificuldades. Clique nele e depois na casa da tropa. O atalho **R** alterna a ferramenta. A retirada devolve 35% do custo, arredondado para cima.

A correção e a validação da versão 1.1.1 estão em [CORRECAO_HUD.md](docs/CORRECAO_HUD.md).

## Tela cheia

Em **CONFIGURAÇÕES → VÍDEO**, clique em **TELA CHEIA**. **F11** ou **Alt+Enter** alternam entre janela e tela cheia durante o jogo. A preferência é lembrada na próxima abertura, e a partida continua preservada. A imagem mantém a proporção; outras proporções de monitor podem apresentar margens pretas.

Pesquisa, decisões e validação: [TELA_CHEIA.md](docs/TELA_CHEIA.md).
