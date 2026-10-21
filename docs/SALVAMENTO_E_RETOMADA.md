# Salvamento e retomada — versão 1.1.0

Revisão de 9 de outubro de 2026.

## Como usar

Ao sair de uma partida pelo botão **MENU** ou pela tecla **Esc**, escolha **CONTINUAR** no menu principal. A mesma opção aparece ao abrir o jogo novamente. A partida volta pausada: clique em **PAUSA** ou pressione **P** para seguir.

Existe uma partida em andamento por perfil local, em qualquer um dos três mapas e em qualquer dificuldade. **NOVA PARTIDA** pede confirmação antes de substituir a atual. Cancelar mantém o salvamento. Vitórias e conquistas da campanha ficam separadas.

O jogo salva ao iniciar, a cada dez segundos de simulação, nas mudanças de onda, ao pausar, ao retornar ao menu e ao fechar normalmente. Um encerramento forçado ou queda de energia pode perder o trecho posterior à última gravação bem-sucedida. Se houver falha de escrita, a partida permanece na memória e aparece um aviso; sair sem salvar exige confirmação.

## Diagnóstico e escolha da solução

Antes desta revisão, `Game.leave_battle_to_title()` atribuía `None` à partida. O arquivo de campanha continha somente regiões concluídas e melhor onda; faltavam posições, tropas e temporizadores para reconstruir a batalha. A correção combina suspensão em memória com um retrato persistente do combate.

A opção aplicada é proporcional a este jogo local: JSON versionado, um ponto de retomada e uma gravação síncrona curta nos limites do ciclo de atualização. Evita coletar um estado parcialmente atualizado em outra thread. Não foram acrescentados banco de dados, conta online ou serviço de nuvem. O intervalo de dez segundos é uma decisão deste projeto, não uma exigência das fontes.

## Pesquisa em fontes primárias

| Fonte oficial | Aplicação ao projeto |
|---|---|
| [Godot — Saving games](https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html) | Identificar objetos persistentes, transformar estado em dados e reconstruir referências em ordem. O princípio foi aplicado ao Pygame; nenhuma migração de motor foi necessária. |
| [Python 3.12 — JSON](https://docs.python.org/3.12/library/json.html) | Dicionários, listas e números permitem dados inspecionáveis. Tuplas e conjuntos recebem representação explícita; tipos, tamanho, versões e números finitos são validados ao carregar. |
| [Python 3.12 — os.fsync e os.replace](https://docs.python.org/3.12/library/os.html) | Escrever um arquivo temporário vizinho, descarregar os buffers e substituir o destino somente após a escrita. Uma falha antes da substituição conserva a gravação anterior. Isso não é garantia contra todas as falhas físicas do disco. |
| [Python 3.12 — random.getstate/setstate](https://docs.python.org/3.12/library/random.html#random.getstate) | Guardar também a sequência de aleatoriedade para não alterar ataques e composição das próximas ondas ao restaurar. |
| [Python 3.12 — pickle](https://docs.python.org/3.12/library/pickle.html) | O formato pode executar código durante a desserialização. Aqui a carga aceita somente classes fixadas no código e dados JSON, sem `pickle`, `eval` ou importação de classes indicadas pelo arquivo. |

As referências sustentam os mecanismos; a seleção do ponto de salvamento, o botão de continuação e a pausa ao retomar são decisões de experiência do jogador.

## Estado preservado

- Mapa, dificuldade, cartas, suprimentos, onda, fila de aparecimento dos inimigos e avisos de chefe.
- Tropas e inimigos: posição, vida, munição, recarga, efeitos de status, habilidades, implantação, ataques e alvos.
- Projéteis em voo, seus proprietários e alvos; a identidade das referências é restaurada, inclusive quando um ator já saiu da lista ativa.
- Minas de emergência das faixas, recargas das cartas, histórico de mortos e temporizadores.
- Estado e quadro das animações dos atores, partículas, textos e efeitos vinculados.
- Estado aleatório e relógios do cenário.

Imagens, sons, fontes, janelas e caches são reconstruídos pelos recursos do jogo. A breve silhueta de desaparecimento de personagens mortos (`fallen`) não vai para o arquivo, pois contém superfícies gráficas; ao reabrir, esse efeito visual já terminado logicamente pode desaparecer. Nenhum dano, inimigo vivo, projétil ou recurso depende dessas silhuetas.

## Organização

| Componente | Responsabilidade |
|---|---|
| `src/svz/snapshot.py` | Representar e validar o estado; reconstruir os atores e ligar referências; restaurar animações e aleatoriedade. |
| `src/svz/session_store.py` | Arquivo separado, versão do formato, limite de tamanho, erros e descarte explícito do ponto de retomada. |
| `src/svz/persistence.py` | Escrita JSON compartilhada por campanha e partida, usando temporário e substituição. |
| `src/svz/app.py` | Gatilhos de salvamento, CONTINUAR, pausa ao restaurar, confirmação de nova partida e fechamento. |
| `src/svz/rendering.py` | Botões, confirmações e mensagens de erro. |
| `tests/test_resume.py` | Regressões de estado, navegação, combate, corrupção e falhas de gravação. |

O caminho padrão é `%LOCALAPPDATA%\SoldadosVsZumbis\campanha.partida.json`. As conquistas continuam em `campanha.json`. Para testes, um caminho de campanha personalizado gera um arquivo irmão `<nome>.partida.json`, evitando acesso ao progresso pessoal.

O formato de partida tem `schema = 1`; a versão do jogo é 1.1.0. Um formato futuro incompatível é recusado com aviso e o arquivo é preservado. O descarte grava um registro vazio explícito. Saves de conquistas da versão 1.0.0 continuam aceitos. Partidas descartadas pela versão antiga antes desta atualização não podem ser recuperadas retroativamente.

## Verificação e limites

A suíte mantém os testes anteriores e acrescenta cenários de retomada. Compara o combate restaurado com uma execução sem interrupção, além de conferir referências de projéteis, todos os atores regionais, chefes, três mapas e três dificuldades. Simula arquivos truncados, formato desconhecido, números inválidos, falhas de substituição, cancelamento e conclusão da partida.

O relatório `RESULTADOS_RETOMADA.json` registra a execução final da suíte, do executável e do ZIP extraído. Os ensaios usam dados temporários e não modificam o progresso pessoal. Testes aprovados não provam ausência absoluta de bugs nem substituem uma campanha humana completa ou a conferência em outros computadores.


## Resultados desta revisão

Os 121 testes (101 anteriores e 20 novos) e o smoke test passaram. O executável retomou partidas em nove processos novos, cobrindo três mapas × três dificuldades. O ZIP extraído teve 289 arquivos conferidos e foi testado novamente nos três mapas, sem Python externo no PATH. A regressão de 108 ondas, nove combates e 28 capturas manteve o mesmo relatório da versão 1.0.0.

O diagnóstico com os dispositivos reais do Windows também terminou com sucesso, incluindo inicialização de vídeo e áudio. Isso confirma a execução com esses dispositivos, mas não representa uma avaliação humana da qualidade do som nem uma campanha jogada por completo. As telas novas foram inspecionadas a partir de capturas produzidas pelo jogo.
