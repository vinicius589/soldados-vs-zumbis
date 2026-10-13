# Preparação da versão final — 7 de outubro de 2026

## Objetivo e resultado da organização

Preparar um jogo executável no Windows sem instalação de Python, retirar versões históricas e arquivos de experimentação da pasta ativa e conservar a capacidade de manutenção. A base escolhida é a versão mais recente que já estava funcionando, com arquitetura modular. A organização não altera regras de campanha ou balanceamento.

A estrutura agora distingue arquivos para jogar (`.exe`, `_internal`, `assets`), código-fonte (`src/svz`), testes (`tests`), ferramentas (`tools`) e documentação vigente (`docs`). O ZIP de distribuição inclui apenas o primeiro conjunto, instruções, créditos e avisos de bibliotecas. Essa separação permite uma entrega simples ao jogador sem destruir os testes e o fonte necessários para corrigir problemas depois do lançamento.

## Pesquisa em fontes primárias

As fontes foram consultadas nesta revisão. As decisões de estrutura são recomendações aplicadas a esta base, não uma arquitetura universal exigida por essas instituições.

| Fonte | O que sustenta | Aplicação |
|---|---|---|
| [PyInstaller: funcionamento e formatos](https://pyinstaller.org/en/stable/operating-mode.html) | O empacotador inclui interpretador/dependências, produz resultado específico da plataforma e admite distribuição em pasta. O modo de arquivo único extrai recursos temporários. | Executável Windows x64 em pasta, sem exigir Python; facilitar inspeção e diagnóstico. |
| [PyInstaller: caminhos de execução](https://pyinstaller.org/en/stable/runtime-information.html) | Distingue caminhos do pacote, executável e diretório de trabalho. | `paths.py` centraliza a raiz; recursos funcionam mesmo quando a abertura ocorre de outro diretório. |
| [PyInstaller: inclusão de dados](https://pyinstaller.org/en/stable/spec-files.html) | Recursos que não são módulos exigem tratamento explícito no empacotamento. | O pacote copia uma lista conhecida de recursos ao lado do executável e verifica seus hashes. |
| [PyPA: layouts de projeto](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) | O layout `src` separa código importável dos demais arquivos e exige configuração de importação/instalação. | O código fica em `src/svz`; o lançador e a ferramenta configuram esse caminho explicitamente. Não foi criada uma distribuição PyPI. |
| [Python: ambientes virtuais](https://docs.python.org/3/library/venv.html) | Ambientes são descartáveis e normalmente não portáveis. | Retirar `.venv` da entrega e construir com ambiente limpo, em vez de distribuir o ambiente antigo defeituoso. |
| [pip: instalações repetíveis](https://pip.pypa.io/en/stable/topics/repeatable-installs/) | Fixar versões reduz variação; hashes podem verificar os pacotes obtidos. | Dependências fixadas e lista completa do ambiente de construção. Os recursos e o ZIP também têm checksums; o arquivo de dependências não é um lock com hashes dos wheels. |
| [GitHub: releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) | Releases permitem distribuir binários e notas associados ao histórico. | Criar um ZIP específico da versão final; publicação externa fica separada da preparação local. |
| [GitHub: LFS em arquivos](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository) | O conteúdo LFS dos arquivos automáticos depende da configuração, e ponteiros podem substituir os arquivos reais. | Conferir todos os recursos e executar o pacote extraído; não entregar um ZIP de referências LFS. |
| [Pygame: driver de vídeo simulado](https://www.pygame.org/wiki/DummyVideoDriver) | Permite executar Pygame sem janela visível. | Regressão automatizada com limites explícitos; o resultado não substitui avaliação humana de som e jogabilidade. |
| [Git: arquivos ignorados](https://git-scm.com/docs/gitignore) | Regras de exclusão não removem por si só arquivos já controlados. | A limpeza desta revisão é efetiva na pasta; não consiste apenas em acrescentar `.gitignore`. |

## Auditoria dos recursos e limpeza

Foram rastreados imports, catálogos de animação, lista de carregamento de imagens, biblioteca de áudio e buscas dinâmicas de quadros. Os recursos ativos somam **109 arquivos e 115.933.639 bytes**:

| Grupo | Quantidade | Pasta final |
|---|---:|---|
| Atores, retratos e ciclo de disparo | 48 | `assets/actors` |
| Interface, cenários e efeitos | 9 | `assets/interface` |
| Áudio | 22 | `assets/audio` |
| Folhas ambientais | 6 | `assets/environment` |
| Quadros de veículos e respingo | 24 | `assets/frames` |

As pastas antigas de conceitos e sprites continham recursos efetivamente usados. Foram migrados seis arquivos ambientais e 24 quadros antes da retirada dessas pastas. Isso evita a limpeza baseada somente no nome do diretório, que teria removido animações em uso.

Saem da pasta ativa: alfas, betas anteriores, a árvore histórica duplicada, backups antigos, material bruto, protótipos de cartas/combate, galeria de cenários, laboratório de animações, geradores/exportadores antigos, capturas antigas, configurações de editor, ambientes virtuais e caches. O registro original de procedência do áudio foi preservado em `CREDITOS.md`; os avisos das bibliotecas ficam em `licenses/`.

Os módulos auxiliares ativos foram incorporados ao pacote `svz` com nomes ligados à função: animação, produção de animações, cenários, apresentação e catálogo. Foram atualizados os imports e os caminhos dos recursos. A etiqueta da versão mudou para 1.0.0; essa é a diferença intencional normalizada na comparação de pixels.

## Dependências e persistência

Foi preparado um ambiente isolado com Python 3.12.14, pygame-ce 2.5.8, NumPy 2.3.5, PyOpenGL 3.1.10, Pillow 12.3.0 e PyInstaller 6.22.3. O NumPy foi fixado na versão usada nas verificações anteriores e agora instalada no ambiente limpo; não se afirma que o antigo pin 2.5.3 tenha sido validado. Pillow é usado pelas verificações de imagens e não precisa ser incluído no executável.

Saves e registros são gravados em `%LOCALAPPDATA%\SoldadosVsZumbis`, separados das imagens e do código. Isso evita depender de permissão de escrita na pasta de instalação e preserva o progresso ao substituir o pacote. O exame da Beta 4 ativa não encontrou save para migrar. Os ensaios usam save temporário, sem progresso do usuário.

## Evidência funcional

O ensaio anterior à limpeza foi executado duas vezes e produziu o mesmo relatório. A versão reorganizada produziu **o mesmo SHA-256 integral**: `9131d2a4b5d701bdfb5af239535e77777acf3cd3fb65f9a9f85e0ea2d9e41f72`.

- 28 capturas de telas e combates comparadas.
- 9 combinações de cenário/dificuldade com dano dos dois lados.
- 108 ondas instanciadas: 12 ondas × 3 regiões × 3 dificuldades.
- 27 entradas de chefes: nove chefes regionais nas três dificuldades.
- 71 atores com 2.768 quadros, 88 quadros ambientais e 87 imagens carregadas.
- Carregamento de áudio, navegação, persistência e encerramento verificados.

No ensaio das ondas, inimigos são removidos depois de confirmar seu aparecimento para acelerar a conferência da progressão. O combate é exercitado separadamente. Isso verifica regressões do diretor e dos ataques, mas não equivale a vencer uma campanha manualmente.

Foram mantidos os testes relacionados ao jogo final. Saíram 30 testes vinculados a protótipos, laboratório, galeria e propostas retiradas. O teste de VFX antes examinava quatro imagens `_clean` não usadas; agora verifica dimensões e transparência das quatro imagens efetivamente carregadas. A redução da contagem não significa regressões escondidas: o escopo retirado e a substituição desse teste estão declarados.

**A suíte mantida passou: 101 testes.** O teste de inicialização também passou após atualizar sua expectativa do nome “BETA 4” para “1.0.0”. Os resultados adicionais do executável e do ZIP extraído são registrados em `RESULTADOS_FINAIS.json` ao concluir a entrega.

## Limites

Testes e comparações não demonstram ausência absoluta de bugs nem ganho de FPS. Não foi feita uma campanha humana completa. A comparação automatizada usa semente e passos fixados; isso não torna o jogo inteiro determinístico. O executável é para Windows x64, não foi assinado digitalmente e não foi publicado em loja ou serviço externo nesta tarefa.

O diagnóstico automático também foi tentado sem o driver simulado, mas o ambiente de execução retornou `pygame.error: No displays available` antes de abrir a janela. Portanto, vídeo/áudio em dispositivos reais e o renderizador opcional OpenGL permanecem sem validação nesta sessão. O executável e o ZIP foram efetivamente executados com os drivers simulados; isso não deve ser apresentado como teste humano ou audiovisual completo.

## Entrega aplicada

A organização foi aplicada em `C:\Users\phill\Documents\ChatGPT\Criaçao de Jogo\Sodados_vs_Zumbis`. Os 101 testes e o smoke test foram executados novamente nesse caminho e passaram. O executável instalado também concluiu seu diagnóstico com código de saída zero, iniciado a partir de outra pasta e sem Python externo no PATH.

O ZIP final tem **143,527,102 bytes** e **289 arquivos conferidos**, além do manifesto de distribuição. Foi extraído em outra pasta e seu executável produziu o mesmo diagnóstico. SHA-256 do ZIP: `66bf8bb5c10bd74a51d7b9f1fdca3873b9cf99797f7cf2b33c833f9fecedded1`.

Antes da revisão, a pasta continha 5142 arquivos e 2.49 GiB. A árvore reorganizada ocupa aproximadamente **318.3 MiB com o ZIP**, ou **181.4 MiB sem ele**. Isso mede a pasta ativa; o histórico continua em uma cópia de recuperação externa e, portanto, não representa a mesma quantidade de espaço liberado no disco.

Cópia de recuperação: `C:\Users\phill\Documents\ChatGPT\Criaçao de Jogo\soldados-vs-zumbis\release_work\recuperacao-original-20261007`. Essa cópia não faz parte do jogo nem do ZIP para os jogadores. Detalhes verificáveis estão em `RESULTADOS_FINAIS.json`, `REGRESSAO.json`, `DIAGNOSTICO_EXECUTAVEL.json` e `TESTES_FINAIS.txt`.
