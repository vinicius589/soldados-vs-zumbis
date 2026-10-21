# Branches, tags e versões

O fluxo foi mantido simples de propósito: uma linha estável e branches temporárias para mudanças.

## main

main é a linha integrada do projeto. Toda mudança entra por Pull Request depois dos testes. Os arquivos de distribuição não devem ser commitados na raiz; são anexos de Releases.

## Branches de trabalho

Crie uma branch a partir de main e use um nome curto que explique o objetivo:

- feat/ — funcionalidade nova.
- fix/ — correção.
- refactor/ — reorganização interna sem mudar o comportamento esperado.
- art/ — alterações em artes e animações.
- docs/ — documentação.
- test/ — cobertura ou infraestrutura de testes.

Não mantenha branches permanentes duplicadas só para dar nome a uma versão. Se a equipe decidir manter uma linha de integração separada, documente o motivo e a regra de integração antes de adotá-la.

## Tags e Releases

Tags identificam um commit específico; Releases apresentam o pacote correspondente e as instruções para o jogador. As versões devem seguir vMAJOR.MINOR.PATCH, com sufixos como -alpha.1 para prévias. A automação de publicação precisa testar o código, montar o pacote e verificar a inicialização antes de anexá-lo à Release.

Não anuncie uma versão como jogável apenas porque o executável foi gerado. As notas da Release precisam dizer o sistema operacional testado e qualquer limitação conhecida.