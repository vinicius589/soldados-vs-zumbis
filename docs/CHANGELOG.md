# Histórico de mudanças

Este arquivo resume mudanças que afetam o projeto. Os pacotes prontos para jogar e as instruções específicas de cada versão ficam nos [GitHub Releases](https://github.com/vinicius589/soldados-vs-zumbis/releases). A lista de snapshots e a origem de cada pacote estão no [Catálogo histórico de versões](HISTORICO-DE-VERSOES.md).

## Em desenvolvimento

- README ampliado com o histórico documentado de criação do jogo, a narrativa e a evolução de Alfas e Betas.
- Guias de instalação, contribuição, commits, branches, tags e Releases atualizados para corresponder ao fluxo real de migração.
- Criado o catálogo de snapshots históricos para as cinco Alfas preservadas e as Betas 2, 3 e 4.
- Criados oito snapshots isolados, com tags `arquivo/*`, branches `snapshot/*`, ZIP individual, checksum SHA-256 e Releases em rascunho.
- Importadas as branches históricas `historico/alfas-e-betas` e `historico/beta-1`, além das tags antigas que as permissões do GitHub permitiram.
- Atualizado o template de Pull Request para pedir evidências dos testes, limitações conhecidas e medidas antes/depois para refatorações.

## Em aberto

- A Beta 1 original permanece sem pacote executável porque o código e o executável originais não foram localizados.
- As tags antigas `v1.3.0` e `v1.3.1`, bem como as branches `jogo` e `beta5-dev`, ainda precisam de importação segura: a credencial da automação não pode publicar commits que incluam certos arquivos de workflow.
- As oito Releases históricas estão em rascunho. Os pacotes foram separados e os checksums foram gerados, mas ainda precisam de revisão e teste gráfico/manual antes de publicação.
- A migração do código-fonte principal para a linha estável permanece separada da documentação histórica; a `main` não foi alterada.

A reorganização não muda, por si só, as mecânicas do jogo. Funcionalidades novas só devem ser listadas quando forem implementadas e testadas. A redução de código será registrada junto de cada refatoração, com o motivo, as mudanças de responsabilidade e os testes realmente executados.
