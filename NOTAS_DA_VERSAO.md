# Alfa da Beta 2 — arenas e estabilidade

Correções registradas no `README.md` original da reconstrução v7.1:

- Cidade e Praia passaram a usar arenas em que os pontos de movimento ficam
  sobre asfalto, areia ou água, não sobre céu, prédios ou paredões.
- Foi corrigida a falha na criação de efeitos de morteiro, fogo ou ácido que
  podia encerrar a partida.

Esta pasta também representa uma reconstrução visual separada, não apenas um
pequeno patch em cima dos arquivos da Beta 2. Por isso a comparação de
código deve considerar a mudança de base e não assumir que cada diferença é
uma correção de bug.

`python smoke_test.py` passou em 30/09/2026. A revisão preservada seguinte
está em [`../alfa-beta-3-v7-4/`](../alfa-beta-3-v7-4/).
