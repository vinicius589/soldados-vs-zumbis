# Tela cheia — pesquisa e implementação da versão 1.2.0

Pesquisa realizada em 10/10/2026. As fontes abaixo são documentação dos
mantenedores do Pygame-ce, SDL e OpenGL. O projeto conserva pygame-ce 2.5.8 e
suas dependências fixadas; os recursos usados foram executados nessa versão.

## Decisão

Manter o jogo em um quadro lógico de 1280×720 e adaptar somente sua apresentação
à janela. Tela cheia usa a resolução atual do monitor selecionado, preserva a
proporção 16:9 e acrescenta margens pretas quando necessário. A janela inicial
cabe na área disponível em monitores menores.

A documentação de [pygame.display](https://pyga.me/docs/ref/display.html)
recomenda consultar get_desktop_sizes para evitar mudar a resolução física do
monitor. Também explica a diferença entre a superfície lógica e o tamanho da
janela. A distinção permite conservar o tabuleiro, as posições das unidades e
o HUD, sem recalcular a simulação.

Alternativas avaliadas:

| Alternativa | Avaliação para este projeto |
|---|---|
| Apenas FULLSCREEN com 1280×720 fixos | Pode solicitar mudança da resolução do monitor; não atende tão bem telas com proporções diferentes. |
| SCALED com toggle_fullscreen | Facilita a transformação automática dos cliques, mas SCALED é documentado como experimental. O projeto também tem um compositor OpenGL opcional. |
| Window.from_display_module | A [documentação de Window](https://pyga.me/docs/ref/window.html#pygame.Window.from_display_module) desaconselha essa ponte e a marca como obsoleta. Não foi usada. |
| Quadro lógico e apresentação separados | Escolhida: preserva a lógica existente, permite testar as transformações e mantém o renderizador por software como padrão. |

A [documentação de SDL_SetWindowFullscreen](https://wiki.libsdl.org/SDL2/SDL_SetWindowFullscreen)
diferencia modos que mudam a resolução dos que ocupam o desktop e alerta para
possíveis reinicializações de recursos de renderização. Nesta implementação,
a troca usa set_mode com as dimensões do desktop. No OpenGL opcional, os
recursos do compositor anterior são liberados antes da troca e reconstruídos
no novo contexto.

## Organização e comportamento

- src/svz/video.py concentra a preferência, a geometria, a conversão do mouse
  e a apresentação por software.
- app.py liga o controlador de vídeo à inicialização, aos eventos e ao menu.
  F11 e Alt+Enter alternam o modo em qualquer tela. Repetição automática dessas
  teclas é ignorada.
- rendering.py mostra TELA CHEIA: SIM/NÃO em Configurações, os atalhos e os avisos.
  Botões, destaque das cartas e indicação da casa usam a mesma conversão do mouse.
- presenter.py ajusta o viewport do OpenGL, mantendo as texturas no tamanho lógico.
- diagnostics.py e tests/test_fullscreen.py verificam o comportamento e as falhas.

O dimensionamento por software parte sempre do quadro original, sem acumular
transformações. O buffer de destino é reaproveitado entre quadros, conforme
a possibilidade descrita em [pygame.transform.smoothscale](https://pyga.me/docs/ref/transform.html#pygame.transform.smoothscale).
O enquadramento do OpenGL segue a transformação de viewport descrita na
[referência oficial glViewport](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Refpages/main/gl4/glViewport.xml).

A conversão do mouse desconta as margens e aplica a escala inversa. Cliques
nas margens são ignorados. Eventos, hover e tabuleiro compartilham essa regra.

A preferência fica em %LOCALAPPDATA%\SoldadosVsZumbis\campanha.video.json,
separada do progresso e da partida. Sua gravação reutiliza a substituição
atômica já existente. Um arquivo malformado retorna ao padrão em janela.
Falha ao ativar tela cheia recupera a apresentação anterior; falha ao guardar
a preferência mostra um aviso. A troca não recria a partida nem seus recursos
de áudio, e o formato dos saves de campanha permanece inalterado.

## Validação

Os resultados desta entrega estão em RESULTADOS_TELA_CHEIA.json.

A suíte cobre proporções 16:9, 4:3, 5:4 e ultrawide; limites das áreas clicáveis;
F11, Alt+Enter e botão de Configurações; repetição de teclas; gravação e leitura;
falhas de vídeo e de escrita; preservação integral do estado nas nove combinações
de mapas/dificuldades; posicionamento, remoção, pausa e retomada.

O diagnóstico do pacote também alterna os modos nos três mapas, avança a
simulação em tela cheia, envia cliques pela fila de eventos e verifica que a
resolução do desktop permanece igual. Testes com SDL dummy são separados das
execuções no driver real do Windows. Nenhuma suíte garante ausência absoluta
de bugs em todos os monitores e drivers.


### Resultado desta entrega

141 testes aprovados em 57,430 segundos, mais o smoke test. Os testes do código
com o driver Windows passaram em 1920×1080 e janela 1280×720, incluindo o
renderizador OpenGL NVIDIA GeForce GTX 1660 Ti. As capturas de Configurações e
do HUD em tela cheia foram inspecionadas.

**Limite da verificação nativa do executável:** o ambiente automatizado retornou
`pygame.error: No displays available` tanto para a versão 1.1.1 instalada quanto
para a nova versão 1.2.0. Portanto, a abertura gráfica nativa do `.exe` não está
certificada nesta execução. Os testes do executável/ZIP usam drivers SDL simulados;
a validação com dispositivos reais foi realizada pelo código-fonte durante a implementação. Posteriormente, o mesmo ambiente também deixou de disponibilizar monitores ao código-fonte. Os resultados
não devem ser apresentados como uma campanha manual completa ou como garantia de
ausência de bugs em qualquer configuração.

