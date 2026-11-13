# Soldados vs Zumbis

Jogo de estratégia 2D em Python/Pygame-CE, com três regiões, quatro faixas,
oito cartas por região e campanha de 12 ondas. Inclui retomada de partida,
perfil local, ranking e loja de consumíveis.

**Estado:** Alfa da Beta 5 integrada, versão técnica **1.6.0**. Combina a
estrutura modular, perfis e loja com as melhorias de jogabilidade da 1.5.3.
Construção local; nenhuma release foi publicada no GitHub.

## Jogar no Windows

1. Instale Python **3.12 x64**, com o Python Launcher (`py`).
2. Execute `PREPARAR_AMBIENTE.bat` uma vez (requer internet).
3. Execute `JOGAR.bat`.

O código usa renderização por software por padrão. OpenGL é opcional:
defina `SVZ_RENDERER=opengl` antes de abrir o jogo. Para jogar sem instalar Python, use o pacote Windows em `dist/` após a
construção. Na árvore de desenvolvimento, `JOGAR.bat` executa os fontes;
`SoldadosVsZumbis.exe` executa a construção local. `CRIAR_EXE.bat` recompila.

## Controles principais

- Mouse: menus, cartas e posicionamento de tropas.
- P: pausar; Esc: voltar ao menu; F5: salvar; F11: tela cheia.
- H: selecionar kit médico; T: selecionar munição tática. Clique na tropa;
  Esc cancela. Compre os itens no perfil/loja antes da batalha.
- Modo teclado e remapeamento: disponíveis em Configurações.
- A retomada usa o perfil ativo para os próximos pontos e consumíveis.

Campanha, perfil, pontuação e preferências ficam em
`%LOCALAPPDATA%\SoldadosVsZumbis-Beta5`. No primeiro uso, se essa pasta ainda
não existir, os dados da pasta antiga `SoldadosVsZumbis` são copiados sem alterar
os originais. Não há sincronização posterior entre as versões. Falhas são
registradas em `jogo.log` na pasta nova.

## Melhorias integradas

- Cinco segundos de preparação antes do primeiro zumbi; pausa e retomada preservam o contador.
- Reserva de suprimentos sem teto; geradores e recompensas entregam o valor completo.
- Vida e dano fixos por tipo de inimigo, preservando os ajustes por dificuldade.
- Leitura de partidas das duas linhas anteriores, com conversão para schema 3.

## Organização

| Pasta | Conteúdo |
|---|---|
| `src/svz/` | Código do jogo |
| `assets/` | Imagens, sons e manifesto de integridade |
| `tests/` | Testes automatizados |
| `tools/` | Verificação, diagnóstico, benchmark e build |
| `docs/` | Guias atuais e relatório da revisão |
| `docs/historico/` | Relatórios e evidências de versões anteriores |
| `licenses/` | Licenças das dependências |
| `reports/` | Saídas locais de validação e backup anterior à revisão |

Não mova `assets/` nem altere sua estrutura sem atualizar as referências.
Ambientes `.venv/`, builds e relatórios são locais e ignorados pelo Git.

## Documentação

- [Desenvolvimento e validação](docs/DESENVOLVIMENTO.md)
- [Integração da 1.5.3 e migração de dados](docs/INTEGRACAO_1.6.0.md)
- [Análise anterior da Alfa](docs/REVISAO_2026-10-30.md)
- [Histórico de alterações](CHANGELOG.md)
- [Contribuição](docs/CONTRIBUTING.md)
- [Créditos](CREDITOS.md) e [licença](LICENSE)

Os relatórios antigos são referências históricas, não evidência de aprovação
da cópia atual. Os resultados novos ficam em `reports/quality/latest.json`.
