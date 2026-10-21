# Coleção de sprite sheets 16-bit — Beta 4

Coleção original em pixel art para um tower defense 2D com perspectiva
lateral-isométrica. Todas as folhas finais são PNGs opacos com fundo chroma key
exatamente `RGB(0, 255, 0)` / `#00FF00`.

## Pastas

- `final/`: as 12 folhas prontas para uso.
- `frames/`: os 268 quadros individuais já recortados.
- `source_generated/`: fontes originais preservadas antes da normalização do
  chroma key.

## Mapa das folhas

| Arquivo | Grade | Linhas, de cima para baixo |
|---|---:|---|
| `01_ambiente_6x6.png` | 6×6 | ondas do mar; água da trincheira; luzes do píer; brilho da caverna; névoa; relâmpagos |
| `02_tropa_fuzil_3x6.png` | 3×6 | idle; atirando; recarregando |
| `03_tropa_lancachamas_3x6.png` | 3×6 | idle; atirando; recarregando |
| `04_tropa_morteiro_3x6.png` | 3×6 | idle; disparando; recarregando |
| `05_tropa_operadora_drone_3x6.png` | 3×6 | idle; acionando drone; trocando bateria |
| `06_tropa_socorrista_3x6.png` | 3×6 | idle; prestando socorro; repondo maleta |
| `07_veiculos_4x8.png` | 4×8 | barco; submarino; trator; drone |
| `08_zumbi_classico_3x6.png` | 3×6 | andando; atacando; morrendo |
| `09_zumbi_mergulhador_3x6.png` | 3×6 | andando; atacando com arpão; morrendo |
| `10_zumbi_baiacu_3x6.png` | 3×6 | andando; inflando/atacando; morrendo |
| `11_boss_mutante_gigante_4x6.png` | 4×6 | idle; andando; ataque pesado; morrendo |
| `12_vfx_4x8.png` | 4×8 | muzzle flash; chamas; explosão; respingo de água |

O primeiro número da grade indica linhas e o segundo indica colunas. Exemplo:
`3×6` representa três animações, cada uma com seis quadros.

## Recorte automático

Os quadros já estão recortados. Para refazer o recorte a qualquer momento,
basta dar dois cliques em `GERAR_FRAMES_INDIVIDUAIS.bat`.

O mapeamento também está disponível em `sheet_manifest.json`, pronto para ser
lido por ferramentas de build ou pelo próprio jogo.

## Remoção do chroma no Pygame

```python
image = pygame.image.load("frame_00.png").convert()
image.set_colorkey((0, 255, 0))
```

O fundo é opaco de propósito, conforme a especificação. Não é necessário
processar transparência alfa antes de usar `set_colorkey`.
