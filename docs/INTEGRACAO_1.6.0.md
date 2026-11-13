# Integração 1.6.0 — Alfa Beta 5

Base ativa: Desenvolvimento_do_Jogo. Doadora: Sodados_vs_Zumbis 1.5.3.
A pasta doadora foi apenas lida; não recebeu alterações nesta integração.

## Escopo

- Contagem inicial de cinco segundos, preservada em pausa e retomada.
- Suprimentos sem teto em geração, abates e fim de onda; HUD ajusta o número.
- Vida e dano fixos por tipo, incluindo tiros, ácido, explosões e chefes.
- Multiplicadores por dificuldade e recompensas continuam conforme o jogo.
- Arquitetura modular, perfil, ranking, inventário e consumíveis preservados.
- Histórico Git importado da branch local existente, sem publicar no remoto.
- Automação Windows e ferramentas locais de construção preservadas.

## Salvamentos e banco

O schema 3 aceita os formatos 1 e 2. O formato 1 conserva a porcentagem de vida
ao remover a escalada por onda; o formato 2 já tem vida fixa. A conversão não
modifica o arquivo de origem durante a leitura e não se repete após salvar em 3.
Partidas antigas sem contagem não reiniciam a preparação da primeira onda.
Campos de consumíveis ausentes nas versões antigas recebem valor zero.

A pasta padrão agora é %LOCALAPPDATA%/SoldadosVsZumbis-Beta5. Quando ainda não
existe, a inicialização copia os arquivos conhecidos de SoldadosVsZumbis para
uma área temporária e publica a cópia inteira por renomeação. O banco SQLite é
copiado com sua API de backup, incluindo transações WAL confirmadas. Falhas não
publicam uma cópia parcial. Destinos existentes nunca são sobrescritos/mesclados.
O arquivo migracao-legado.json registra a origem e os arquivos copiados.

A migração é feita no primeiro uso normal do jogo. Diagnósticos e caminhos
explícitos SVZ_DATA_DIR/SVZ_SAVE_PATH não importam dados pessoais. Nenhum dado
pessoal foi migrado durante esta tarefa: as verificações usam dados sintéticos.
A versão anterior mantém seus dados; não há sincronização após a primeira cópia.

## Evidências

Backup anterior: reports/integracao-153/fontes-antes-da-integracao.zip.
Fixtures originais: tests/fixtures/alfa_schema1.json e v153_schema2.json.
Validação completa: reports/quality/latest.json.

Resultados finais (31/10/2026):
- 301 testes: zero falhas, erros ou testes ignorados.
- Verificação estática, cobertura, smoke, regressão e benchmark aprovados.
- Executável 1.6.0 construído e identidade dos fontes conferida.
- ZIP com 296 arquivos conferidos por SHA-256 e CRC; extração validada.
- Diagnóstico do executável extraído aprovado.
- Retomada dos dois formatos antigos aprovada no executável extraído, sem
  modificar os arquivos de origem; cada partida avançou 120 passos.
- Build 1.5.3 da pasta doadora novamente conferido e íntegro.
- HUD inspecionado em texto normal e ampliado, com reserva de 10^15.

Pacote: dist/SoldadosVsZumbis-1.6.0-Windows-x64.zip.
Comprovante: docs/VALIDACAO_1.6.0.json.
Evidência detalhada: reports/integracao-153/pacote-validado.json.
O histórico foi integrado localmente; nenhuma alteração foi enviada ao GitHub.

## Limites

A validação automatizada usa renderização por software e drivers simulados.
Ela não substitui a avaliação manual de áudio real, OpenGL e conforto de jogo.
O estoque SQLite e os efeitos da batalha JSON continuam em transações separadas.
Uma interrupção abrupta entre as gravações ainda pode perder o efeito de um item
já descontado; essa limitação preexistente não faz parte das melhorias da 1.5.3.


### Correcao do preparador (31/10/2026)

PREPARAR_AMBIENTE.bat chama PREPARAR_AMBIENTE.ps1, que valida a execucao real
em Python 3.12 x64, reutiliza um ambiente valido e recupera pip ausente.
Se o launcher py nao encontrar a versao, procura instalacoes locais, inclusive
o runtime local do Codex quando disponivel. Esse runtime precisa permanecer
instalado para o ambiente continuar funcionando. Ambientes invalidos sao
preservados em .venv-backup-* antes da recriacao. O marcador de ambiente pronto
so e gravado depois da instalacao e importacao das tres bibliotecas.
