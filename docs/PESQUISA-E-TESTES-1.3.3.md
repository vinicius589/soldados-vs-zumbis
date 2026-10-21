# Pesquisa aplicada e automação de testes — 1.3.3

Pesquisa em fontes primárias consultadas em 16/10/2026. Esta versão aprofunda
os contratos de combate e a validação automatizada, correspondentes a partes
de M02, M65, M66 e M69 do catálogo. Não implementa todas as 72 propostas.

## Referências e decisões

| Fonte primária | Aplicação no projeto |
|---|---|
| [Python 3.12: unittest](https://docs.python.org/3.12/library/unittest.html) | Mantido o executor existente, com descoberta de testes, subtestes e falhas propagadas ao processo. A automação rejeita suíte vazia ou testes ignorados. |
| [Hypothesis: testes com estado](https://hypothesis.readthedocs.io/en/latest/stateful.html) | Máquina de estados exercita sequências de avanços do relógio; uma invariante confere conservação do tempo e limite do trabalho por quadro. |
| [Hypothesis: reprodução de falhas](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html) | Exemplos determinísticos nesta versão das dependências, redução automática de casos que falham e logs preservados. A configuração não promete repetir os mesmos exemplos após mudar Python, Hypothesis ou o teste. |
| [Coverage.py: cobertura de ramos](https://coverage.readthedocs.io/en/latest/branch.html) | Medição de decisões além das linhas; barreiras por módulo impedem que uma média global esconda baixa cobertura em combate ou persistência. Cobertura não prova correção. |
| [Coverage.py: execução](https://coverage.readthedocs.io/en/latest/commands/cmd_run.html) | A suíte roda dentro de `coverage run --branch`; medir apenas o processo pai de um subprocesso não cobriria os testes. |
| [Python 3.12: dataclasses](https://docs.python.org/3.12/library/dataclasses.html) | A igualdade padrão compara campos. O rastreamento agora verifica identidade (`is`) para não confundir uma entidade retirada com outra de atributos iguais. |
| [Python 3.12: JSON](https://docs.python.org/3.12/library/json.html) | JSON válido não basta para uma partida válida. Mantidos limites de tamanho e números finitos; acrescentadas condições semânticas aos projéteis restaurados. |
| [Glenn Fiedler: Fix Your Timestep](https://gafferongames.com/post/fix_your_timestep/) | Preservados passos fixos e limite de recuperação, testando o tempo descartado. Valores não finitos são rejeitados antes de contaminar o relógio. |
| [Pygame-ce: Rect](https://pyga.me/docs/ref/rect.html) | A API diferencia limites e interseções; o contrato de área do jogo mantém explicitamente distância horizontal menor que o raio e seleção de faixa. Não substituímos isso por retângulos de sprites com dimensões visuais diferentes. |
| [GitHub Actions: testar Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) | CI Windows instala dependências fixadas, executa a mesma validação local e publica evidências. A execução manual também constrói e verifica o pacote. |

As documentações são referências de técnica. Os limites de dano, raio e faixa
são decisões específicas deste jogo, verificadas contra seus contratos; não
são regras prescritas por essas bibliotecas.

## Correções

1. **Projéteis restaurados:** viagem precisa ser positiva; dano e raio não
   podem ser negativos. O formato do save não mudou, e valores válidos, como
   dano zero e atraso de lançamento negativo, continuam aceitos.
2. **Faixa do impacto:** explosões usam a faixa do destino registrado, mesmo
   sem alvo/dono ou após mudança de faixa da entidade referenciada. O tiro
   dirigido continua acompanhando somente o seu alvo vivo e presente.
3. **Identidade:** uma cópia de uma entidade com campos iguais não representa
   a mesma entidade. A verificação de alvo presente segue essa distinção.
4. **Relógios:** o passo e o limite de recuperação são validados. `NaN` e
   infinitos são rejeitados; delta negativo de projétil também é rejeitado
   antes de qualquer alteração. O relógio geral mantém o contrato anterior
   de ignorar tempo negativo.

## Camadas da automação

- Testes de exemplos: dano direto/secundário, limite exclusivo do raio,
  inimigos mortos, tipos de impacto, chefes e isolamento entre facções.
- Testes por propriedades: regiões/faixas, raios, distribuições de inimigos,
  dados numéricos inválidos e retomada de projéteis válidos. Cada propriedade
  admite até 150 exemplos; domínios finitos podem produzir menos exemplos.
- Máquina de estados: até 100 sequências de até 60 ações, verificando
  invariantes depois de cada ação. Isso não equivale a 6.000 testes unittest.
- Integração: a suíte existente usa Game/Battle reais, saves isolados e SDL
  dummy. Mocks nos novos testes geométricos observam o dano solicitado; os
  testes de integração continuam verificando aplicação real de dano.
- Regressão: mapas, dificuldade, ondas, combate, menus, recursos e capturas.
- Pacote: hash dos fontes/runtime, diagnóstico do EXE e integridade do ZIP.

## Como executar

Com Python 3.12 e ambiente virtual ativo na pasta do projeto:

```powershell
python -m pip install -r requirements-test-lock.txt
python tools/quality.py
python tools/manage.py build
python tools/manage.py package
```

`quality.py` cria um diretório novo em `reports/quality` a cada execução:
logs por etapa, resumo JSON da suíte, cobertura JSON/XML/HTML, regressão e
benchmark. `latest.json` aponta para a execução mais recente. Uma etapa
reprovada encerra o processo com código diferente de zero. Os limites atuais
da cobertura combinada de linhas e ramos são 95% para projéteis e relógio e
85% para o módulo de snapshot completo. Eles não representam cobertura do
jogo inteiro. Os próprios bloqueios de cobertura têm testes automatizados.

Os saves de testes ficam isolados dos dados reais. Não há sleeps em testes
de temporização: o relógio é avançado por valores controlados. O benchmark
não participa da aprovação por FPS, pois depende da máquina e usa software
sem sincronização com o monitor.

## Limites da entrega

O CI foi configurado no repositório local; a execução remota só ocorre após
publicação e disparo no GitHub. Os resultados desta entrega são execuções
locais, não uma alegação de execução remota. Colisões contínuas, novas ondas,
modos e outras propostas do catálogo continuam fora deste ciclo. Testes
automatizados não substituem áudio/GPU reais nem uma campanha manual.
