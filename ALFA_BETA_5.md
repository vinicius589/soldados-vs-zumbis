# Alfa da Beta 5 — prévia para revisão

Esta é a continuação modular do jogo, preservada separadamente da versão estável enquanto corrigimos problemas e validamos as mudanças. Ela não deve ser confundida com a Beta 4 pura nem anunciada como lançamento final.

## Funcionalidades presentes

- Campanha de 12 ondas, com três regiões temáticas.
- Salvamento local automático, ponto de retomada e confirmação antes de substituir uma partida.
- Pontos por inimigo e registro idempotente de resultados.
- Perfil local com nome de jogador, histórico de partidas e ranking pela soma de pontos.
- Créditos separados da pontuação e inventário persistente de consumíveis.
- Kit médico para tropa viva ferida e munição tática por tempo limitado.
- Menus de campanha, personagens, história, configurações, perfil/loja, ranking e histórico.
- Código em `src/svz/`, testes em `tests/` e ferramentas de verificação em `tools/`.

## Correções desta revisão local

- A tela de perfil/loja tinha métodos de interação no jogo, mas faltava sua implementação de desenho e o encaminhamento do estado `profile` pelo renderizador. A tela agora foi adicionada, e o inventário é carregado ao entrar nela, não a cada quadro.
- A tela de pontuação tentava interpretar a linha do ranking como histórico e desempacotava o histórico com seis campos, embora o banco entregue sete. As duas visualizações agora têm cabeçalhos e campos próprios.
- O ranking e o histórico compartilham as mesmas posições de botões para desenho e clique.
- A compra de consumíveis agora responde somente ao botão Comprar, não a qualquer clique sobre a descrição do cartão.
- A tela de perfil mostra falhas ao ler o banco, e avisos de falha ao salvar preferências não desaparecem ao trocar de menu.
- O campo de nome aceita Ctrl+A para limpar o nome antes de digitar outro.
- Os testes de pontuação foram atualizados para os sete campos reais do histórico e ganharam casos de ranking agregado, renderização e compra/consumo de item.

## Estado dos testes

A validação de sintaxe e integridade dos recursos deve passar antes da revisão do Git. Nesta sessão, não foi possível executar a suíte completa porque o ambiente local não contém `pygame-ce` nem `hypothesis` e não consegue acessar o PyPI. Por isso, os testes que dependem dessas bibliotecas **não são declarados como aprovados**; rode `tools/manage.py test` em um ambiente Windows com as dependências listadas em `requirements-test-lock.txt` antes de publicar uma versão jogável.
