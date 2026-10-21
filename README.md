# Soldados vs Zumbis

**Um tower defense original sobre estratégia, contenção e sobrevivência.** *Soldados vs Zumbis* é um jogo 2D desenvolvido em Python, com Pygame-CE e recursos de renderização via PyOpenGL. A ideia central é simples: escolher tropas com funções diferentes, posicioná-las nas faixas certas e administrar os suprimentos para impedir que os infectados atravessem a defesa.

> **Estado deste repositório:** a nova casa do projeto está sendo organizada. A linha jogável de referência e as etapas antigas estão preservadas enquanto a migração, os testes e a refatoração são revisados. A presença de uma branch ou tag não significa, sozinha, que uma versão foi testada e aprovada para distribuição.

## A história do jogo

O projeto começou como uma atividade acadêmica e cresceu por protótipos, Alfas e Betas. O histórico que restou mostra uma evolução prática: primeiro veio a lógica de defender as linhas; depois, os cenários e sprites próprios; em seguida, menus, seleção de tropas, habilidades regionais, equilíbrio, animações e uma campanha mais organizada.

A documentação preservada não aponta uma obra específica como origem da ideia. Por isso, este README não atribui a inspiração a um jogo, filme ou pessoa sem registro. A identidade do projeto está na combinação de defesa tática por faixas, unidades militares, zumbis com comportamentos diferentes e uma campanha que atravessa ambientes distintos.

### Como o projeto evoluiu

| Etapa preservada | O que ela representa |
| --- | --- |
| **Protótipo inicial / Beta 1 original** | A primeira versão é descrita como um jogo de formas simples, ainda sem sprites. O código e o pacote executável originais não foram encontrados no acervo disponível; não vamos inventar um executável nem afirmar que conseguimos compará-lo. |
| **Alfa inicial** | É a primeira etapa preservada com arte própria. A campanha já tinha cidade, deserto e costa, tropas por cartas e ondas de dificuldade crescente. As versões daquela família trabalhavam com 15 ondas por região. |
| **Abertura e carregamento** | Um marco posteriormente classificado como Beta 2 acrescentou menu de abertura, tela de carregamento, instruções e consulta aos arquivos de soldados e zumbis. Os documentos antigos nem sempre usavam os números Alfa/Beta da mesma forma; as notas preservadas registram as correções de classificação. |
| **Alfas de correção e reconstrução** | O trabalho passou por ajustes de terreno e posicionamento, correções em efeitos de projéteis que podiam derrubar a partida, organização de unidades N1/N2, promoção pelo Sargento, revisão de minas e balanceamento da dificuldade. Essas etapas são importantes para estudar o código, mas não devem ser tratadas como lançamentos independentes sem evidência. |
| **Beta 3** | O jogo ganhou mais identidade regional: unidades e mecânicas costeiras, tipos de dano específicos por ambiente e escolha de dificuldade. As revisões v7.6–v7.9 registram adições e correções acumuladas, em vez de mudanças isoladas em cada número. |
| **Alfa de revisão da Beta 4** | Foi uma rodada de revisão ampla: folhas e continuidade das animações, escala dos personagens, interface, controles, áudio, equilíbrio e integração dos cenários. A pasta histórica é um retrato do trabalho em revisão, não uma alegação de que tudo já estava aprovado. |
| **Beta 4** | Consolida a linha jogável de referência com três regiões, quatro faixas por mapa, elenco regional, sprites e áudio próprios, além de uma campanha de 12 ondas organizada em ciclos de inimigos comuns, subchefes e chefes. |
| **Nova etapa de organização** | No novo repositório, o foco é preservar o comportamento do jogo, tornar o código mais fácil de manter e medir as refatorações. Separar módulos e remover duplicação só conta como melhoria quando os testes e as verificações do jogo continuam passando. |

O acervo das Alfas e Betas está na branch histórica [historico/alfas-e-betas](https://github.com/vinicius589/soldados-vs-zumbis/tree/historico/alfas-e-betas). A referência separada da Beta 1 está em [historico/beta-1](https://github.com/vinicius589/soldados-vs-zumbis/tree/historico/beta-1). O repositório anterior continua disponível como fonte de comparação em [soldados-vs-zumbis-beta-4](https://github.com/vinicius589/soldados-vs-zumbis-beta-4).

## A história dentro do jogo

A campanha liga os mapas por um mesmo desastre biológico. A Nexora Biotecnologia Integrada se apresenta como uma empresa dedicada à medicina, à biotecnologia e à energia limpa, mas conduz pesquisas clandestinas no **Projeto Lázaro**. O projeto combina regeneração biológica, nanofármacos e um reator experimental chamado **Reator Hélix**.

O **Agente R-13** foi criado para reativar tecidos e permitir que organismos resistissem a danos extremos. Ele, porém, não devolve a consciência: reativa músculos, intensifica impulsos agressivos e sofre mutações de acordo com o ambiente. A Nexora esconde falhas e tenta controlar as provas até que uma catástrofe no Reator Hélix espalha contaminação e provoca o que ficou conhecido como **Incidente da Meia-Noite Verde**.

### Capítulo 1 — Nova York: Zona Hélix

O surto começa na cidade. Ruas, hospitais, delegacias e instalações de pesquisa ficam comprometidos. A resposta é feita por forças de contenção urbanas, enquanto moradores, trabalhadores e funcionários contaminados se transformam em ameaças. Este capítulo apresenta o perigo do R-13 e os primeiros sinais de que a empresa ocultou a dimensão do desastre.

### Capítulo 2 — Egito: Necrópole de Khepra

Antes do incidente, a Nexora financiou uma expedição arqueológica para estudar um mineral encontrado sob as ruínas de Khepra. O material reagia ao R-13 e foi usado na pesquisa do Reator Hélix. Depois do acidente, uma tentativa de apagar rastros rompe uma área contaminada na necrópole, e o agente desperta cadáveres, guardiões e criaturas que estavam preservadas sob a areia. O combate passa a envolver terrenos e inimigos que não existiam na cidade.

### Capítulo 3 — Cachoeira de Minas Gerais

A contaminação alcança os sistemas de água e se espalha até a região da Cachoeira, em Minas Gerais. A ameaça já não está restrita ao local da explosão: ela acompanha a água e transforma a área em mais uma frente de contenção. A resposta envolve a Marinha e unidades adequadas ao ambiente aquático, mantendo a mesma lógica estratégica com perigos diferentes.

O material de produção mais antigo também preserva nomes provisórios e propostas alternativas para o terceiro capítulo. Eles serão mantidos como registro histórico; não substituem automaticamente o cenário de Cachoeira nem autorizam trocar os sprites, mapas ou a identidade visual já adotados.

## Identidade de jogo e direção visual

- **Estratégia por faixas:** colocar a unidade certa no lugar certo é mais importante que simplesmente acumular tropas.
- **Recursos e recarga:** a defesa depende de administrar suprimentos, munição e tempo de recuperação.
- **Três regiões próprias:** Nova York, o Deserto do Egito e a Cachoeira de Minas Gerais têm terrenos e elenco regional.
- **Campanha da Beta 4:** 12 ondas em ciclos de duas ondas comuns, uma de subchefe e uma de chefe, repetidos pelas três regiões.
- **Arte e áudio originais do projeto:** os sprites, folhas de animação, cenários e sons preservados devem continuar sendo a referência; refatorar o código não é motivo para substituir a identidade visual.
- **Código em evolução:** módulos de combate, entidades, interface e recursos devem ter responsabilidades claras, com testes que ajudem a impedir regressões.

## Versões, branches, tags e Releases

Cada recurso novo deve mostrar seu caminho no código por meio de commits pequenos e bem nomeados. Branches são linhas de trabalho para mudanças em andamento; tags apontam para um estado exato do código; Releases apresentam aquele estado, suas notas e, quando houver um pacote validado, os arquivos para baixar.

Uma tag não contém um executável por si só. Quando uma versão Alfa ou Beta tiver um pacote independente e verificável, o pacote será anexado à **Release associada à tag**. Não vamos fabricar uma Beta 1 executável enquanto o arquivo original não for encontrado, nem chamar um pacote de testado sem evidência de execução.

Veja o [catálogo de versões históricas e seus pacotes](docs/HISTORICO-DE-VERSOES.md), o [plano de preservação e evolução histórica](docs/PLANO-EVOLUCAO-HISTORICA.md), o [guia de branches, tags e versões](docs/BRANCHING.md) e o [guia de instalação e desenvolvimento](docs/GUIA-DEV-E-RELEASES.md) e o [relatório da linha de base da refatoração](docs/RELATORIO-BASE-REFATORACAO.md).

## Jogar ou desenvolver

- **Para jogar:** confira primeiro as [Releases deste repositório](https://github.com/vinicius589/soldados-vs-zumbis/releases). Enquanto a migração não tiver sua primeira versão aprovada, as distribuições de referência continuam nas [Releases do repositório antigo](https://github.com/vinicius589/soldados-vs-zumbis-beta-4/releases).
- **Para desenvolver:** comece em [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). O [guia de arquitetura](docs/ARCHITECTURE.md) explica a organização dos módulos e os testes.
- **Para estudar as versões anteriores:** use o [catálogo histórico](docs/HISTORICO-DE-VERSOES.md), que aponta para os snapshots por tag e os pacotes separados nas Releases. Não misture pastas de versões distintas como se fossem uma única instalação.

O botão **Code → Download ZIP** baixa o estado do código-fonte que está em uma branch; não garante, por si só, um pacote de jogo preparado para execução. Alguns recursos históricos foram guardados via Git LFS, então confirme os arquivos de arte e áudio antes de avaliar uma cópia extraída.

## Licença e créditos

A licença do código está em [LICENSE](LICENSE). Ela não substitui as condições de uso dos sprites, imagens e sons: consulte os créditos e manifestos junto aos recursos antes de reutilizá-los.
