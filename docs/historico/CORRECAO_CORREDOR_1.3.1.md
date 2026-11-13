# Correção da corrida — versão 1.3.1

Validada em 15/10/2026. O corredor agora avança de frente em todos os quadros
dos três mapas. A alteração funcional está concentrada na carga das animações.

## Causa e correção

A carga aplicava espelhamento horizontal a todas as folhas de corrida. A folha
do deserto já olha para a esquerda; esse espelhamento a fazia correr de costas.
A folha da cachoeira mistura quatro quadros para cada lado. A cidade já estava
correta. `RUNNER_MOVE_FLIP_FRAMES` registra os quadros que precisam de inversão:
cidade 0–7, deserto nenhum e cachoeira 0–3 (índices iniciados em zero).

Os arquivos de arte foram preservados. A orientação é corrigida uma vez,
durante a carga. Os estados que reutilizam a corrida recebem os mesmos quadros.
O teste visual reproduziu 36 falhas de subcasos antes da correção e passou
depois. Ele mede a posição da cabeça na silhueta destas folhas conhecidas;
uma futura troca de arte exige nova inspeção visual.

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Suíte completa | 172 testes aprovados, zero falhas; smoke test aprovado |
| Integridade | 109 recursos e sintaxe de 59 arquivos Python conferidos |
| Corrida | Oito quadros por mapa; variantes e estado de habilidade conferidos |
| Partidas com corredor | Nove combinações de mapa/dificuldade; 360 passos cada, velocidade constante, orientação, pausa e retomada |
| Comparação de imagens | 71 atores comparados; apenas os quadros invertidos do deserto/cachoeira mudaram |
| Regressão | Nove campanhas, 108 ondas, nove casos de combate e 28 capturas |
| EXE nativo | Windows, janela 1280×720 e tela cheia 1920×1080; controles e estado preservados |
| EXE extraído | Diagnóstico completo aprovado em outra pasta, com PATH sem Python |
| ZIP | 292 arquivos mais manifesto; CRC, SHA-256 e conteúdo extraído conferidos |

As 108 ondas são verificadas com progressão acelerada, removendo os inimigos
após conferir seu nascimento; os casos de combate são separados. Não equivalem
a campanhas humanas completas. A inspeção visual abrange os 24 quadros finais e
a captura da partida do deserto. O mixer inicializou, mas não houve avaliação
por escuta. Não foram testados outros computadores, monitores ou DPIs.
Esses resultados não constituem garantia de ausência absoluta de bugs.

O aviso de falha ao gravar visto no log geral é provocado por um teste de erro
de salvamento; o resultado final da suíte é OK. Os testes usam saves isolados.

## Entrega

Abra `SoldadosVsZumbis.exe` na raiz. Para distribuir, use
`dist/SoldadosVsZumbis-1.3.1-Windows-x64.zip` e extraia a pasta inteira.
Python não precisa ser instalado. A versão anterior fica fora da pasta ativa,
na cópia de recuperação `C:\Users\phill\.codex\visualizations\2026\10\06\01a11265-fd87-71b1-8872-fd529bed0290\runner-fix-1.3.1\backup-1.3.0`.

SHA-256 do ZIP: `cc1b648f11848d84fa7322b3b5d0caa1683ef455980e9c59762e73ffc4906acf`.

Revisão dos fontes: `6a5d3ce0f0dfbd2f86227c1a678f084f6e8b3e882ca9ddddf3731e2cd638d938`.

Evidências: [testes](evidencias-1.3.1/testes-e-build.txt),
[reprodução anterior](evidencias-1.3.1/direcao-antes.txt),
[teste do corredor](evidencias-1.3.1/testes-corredor.txt),
[quadros corrigidos](evidencias-1.3.1/quadros-corrigidos.png),
[EXE nativo](evidencias-1.3.1/exe-nativo.json),
[EXE extraído](evidencias-1.3.1/exe-extraido.json),
[integridade](evidencias-1.3.1/integridade-pacote.json).

## Conferência após instalação

A cópia da pasta principal passou novamente no diagnóstico. Fontes, executável,
bibliotecas, ZIP e cópia extraída correspondem à construção validada.
Evidências: [EXE instalado](evidencias-1.3.1/exe-instalado.json) e
[integridade instalada](evidencias-1.3.1/instalacao.txt).
