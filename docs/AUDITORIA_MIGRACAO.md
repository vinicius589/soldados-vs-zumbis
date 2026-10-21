# Auditoria inicial da migração

## Decisões tomadas

- A cópia parte da branch jogo do repositório histórico, usada como base da Beta 4.
- Serão preservados o runtime, os módulos de engine e game, os testes, a documentação útil, a licença e os recursos usados em execução.
- src/main.py será uma fachada de compatibilidade e a implementação ficará em src/game/runtime.py. Os testes e o ponto de entrada src.main:main precisam continuar funcionando.
- Os assets em assets/v7/, assets/beta4_producao/ e assets/audio_beta4/ serão mantidos porque o runtime os carrega.
- A pasta interna tools/, com laboratórios de sprites, variantes de cenários e material de QA/produção, ficará fora da linha principal. Ela não será apagada do repositório histórico.
- A documentação de branches usará o fluxo real: main mais branches temporárias. Não será criada uma develop artificial.
- O código e as mecânicas continuam sendo da Beta 4; não se anuncia Beta 5 antes de implementar e validar novas funcionalidades.

## Verificações exigidas

A automação deve executar compileall, Ruff e pytest, compilar o pacote Windows, conferir recursos essenciais e tentar manter o executável aberto por alguns segundos. Esse teste é útil, mas não equivale a validar uma partida completa, todas as animações e todos os mapas em um computador de jogador.

## Pontos ainda graduais

- O módulo de runtime continua grande. A extração completa de combate, UI, economia, áudio e renderização deve ocorrer em mudanças pequenas, com testes antes e depois; uma divisão automática de 400 KB sem executar o jogo seria arriscada.
- As artes de produção necessárias ao runtime precisam permanecer até que cada sprite sheet tenha sido rastreada.
- O material histórico fica preservado no repositório antigo durante a transição.