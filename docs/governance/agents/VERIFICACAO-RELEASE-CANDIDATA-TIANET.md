# Verificação — candidata local do TiaNet

**Data:** 2026-09-08
**Branch:** `feat/imp-370-worker-le-o-token`
**Baseline anterior:** `b737c20`
**Série candidata local:** `7d3a5e3`, `f1b3c8d`, `9473e0d` e o commit documental que contém esta verificação
**Parecer:** `CANDIDATA LOCAL VERIFICADA`

## Escopo observado

Esta verificação reúne o Harness adotado, o IMP-370 e a recertificação visual da interface na série local autorizada pelo proprietário. Não identifica uma imagem de release, não inspeciona a VPS e não autoriza push, PR, merge ou publicação.

Os três primeiros commits separam Harness, backend/migration e frontend/testes. O quarto consolida documentação e 44 evidências PNG regeneradas. Os gates materiais foram repetidos sobre `b99cb81`; esta reconciliação posterior altera somente os registros documentais do quarto commit. Um CSV alheio encontrado em `docs/whatsapp` foi preservado fora da série.

## Gates executados

| Superfície | Evidência observada | Resultado |
|---|---|---|
| Backend estático | Ruff, Black e mypy sobre 271 arquivos-fonte | APROVADO |
| Backend funcional | `uv run pytest tests/ -q` concluído até 100%, além das matrizes focais do IMP-370 | APROVADO |
| Migration | PostgreSQL 16 descartável: `upgrade head → downgrade base → upgrade head`; head único `c1d2e3f4a5b6` | APROVADO |
| Frontend de produção | `api:check`, typecheck, lint e build | APROVADO |
| Frontend automatizado | 72 unitários, 82 de componentes, 42 de contrato e 137 de BFF | APROVADO |
| Navegador | Matriz principal com 156 cenários: sessão, módulos, acessibilidade, WhatsApp e 8 jornadas compostas na stack real; mais 10 reexecuções focais, totalizando 166 invocações aprovadas | APROVADO |
| Visual | 56 evidências: 28 desktop, 28 mobile; 44 regeneradas e 12 preservadas | APROVADO |
| Certificação visual/segurança | 56/56 arquivos listados uma vez, SHA-256 vigente, bundle público, Client Components, diretrizes de interface e antirrecalculo | APROVADO |
| Governança | `docs:validate`, `harness:check`, `harness:test` e `git diff --check` | APROVADO |

## Estabilidade visual

A primeira recertificação revelou variação entre execuções causada por rolagem suave, regiões temporárias e um UUID recortado no limite de um campo. A correção ficou restrita aos helpers Playwright de Devedores, Comercial, Contratos, Motor, Cobrança e Agenda/Comunicação; código de produção e assertions funcionais não foram alterados.

A prova de estabilidade foi feita em duas etapas:

1. duas execuções consecutivas das seis suítes produziram 55 das 56 evidências byte a byte idênticas;
2. após a correção reduzida do único campo restante, duas execuções consecutivas de Motor produziram seus quatro PNGs byte a byte idênticos.

O inventário vigente está no [relatório aditivo de recertificação](../../audits/reports/tianet-release-candidate-visual-recertification-2026-09-08.md). A validação independente encontrou 56 linhas únicas, 56 arquivos, zero ausências, zero itens não listados e zero divergências de SHA-256.

## Coordenação OpenCode e revisão

O OpenCode recebeu tarefas delimitadas para auditoria, correções de contrato, acessibilidade, estabilização visual e atualização mecânica de evidências. Toda mutação aceita ficou dentro de paths declarados e foi revalidada pelo coordenador.

Na estabilização final, a tarefa `607238ad-4373-47ca-b2f8-6fa0d97f07d2` precisou de três tentativas: as duas primeiras foram devolvidas por instabilidade residual observada; a terceira foi aprovada após lint, diff check, duas execuções de Motor e igualdade dos quatro hashes. A tarefa documental `72c07fa4-49ee-4508-932a-c44575997286` foi interrompida por silêncio do provedor depois de escrever o relatório; por isso não recebeu aprovação do executor. O artefato foi adotado somente após validação independente.

## Falhas transitórias classificadas

- Durante sequências longas, o servidor Next encerrou em Configurações e, mais tarde, em Motor. Todos os casos falharam por `ERR_CONNECTION_REFUSED` antes de exercitar a lógica testada. As mesmas suítes passaram em ambiente limpo.
- Na repetição pós-commit, o processo agregado perdeu o controle ao iniciar Sessão e deixou a fixture na porta 3201. O processo exato foi encerrado; Sessão passou 22/22 e todas as suítes seguintes passaram isoladamente.
- A queda da sessão deixou o Docker Desktop desligado; a primeira chamada das jornadas parou antes dos testes. Após reiniciar o Docker, as 8 jornadas da stack real passaram.
- O comando agregado `test:harness` não terminou verde em uma única invocação por esses eventos de ciclo de vida do ambiente. Seus blocos foram executados e aprovados individualmente, preservando as evidências em vez de usar o `gate:full`, que restaura PNGs via Git.

Esses eventos não indicaram falha funcional do produto. Permanecem registrados para que o gate do tip final seja executado em ambiente limpo e com Docker iniciado somente para as jornadas.

## Estado do ambiente ao concluir

- Container descartável `tianet-release-check`: removido.
- Docker Desktop iniciado apenas para as jornadas e encerrado ao final.
- VPS: não acessada.
- Quatro commits locais: autorizados e formados nesta série.
- Push, PR, merge e deploy: não realizados.

## Próximo gate

Os gates locais da candidata foram concluídos. O próximo passo é identificar a imagem de release, preparar o procedimento de rollback e inspecionar a VPS antes de qualquer publicação. Esta conclusão não constitui uma release publicada.
