---
name: plan
description: Transforme design ou requisitos compreendidos em plano executável com slices, aceite, testes, riscos e porta de aprovação; pare antes da implementação.
---

# Plan

## Propósito

Criar um plano que outra sessão consiga executar sem redescobrir o desenho.

## Quando usar

Use para trabalho `STANDARD` ou maior e para qualquer mudança que exija vários passos coordenados.

## Quando não usar

Não crie plano durável para patch `TRIVIAL`, local e reversível. Não use para executar código.

## Entradas

- Saída de `$discover` e, quando aplicável, `$architect`.
- Decisões e design aprovados.
- Critérios de aceite e estratégia de testes vigentes.

## Procedimento

1. Confirme que arquitetura e decisões bloqueadoras estão resolvidas.
2. Use [`exec-plan.md`](../../templates/exec-plan.md) para plano durável.
3. Divida o trabalho em slices pequenos, cada um entregando comportamento independentemente verificável.
4. Para cada slice registre propósito, arquivos prováveis, justificativa, dependências, aceite, testes, verificação e rollback.
5. Monte matriz de testes por risco, não por cobertura artificial.
6. Registre rollout, rollback, riscos, decisões, revisão e progresso.
7. Responda o que tornaria o plano errado, o que forçaria redesign, o que ficou fora e qual evolução futura seria facilitada ou dificultada.
8. Registre a autorização e seu escopo em G5. Se a aprovação necessária ainda não existe, pare para obtê-la; não peça novamente aprovação já dada para o mesmo escopo.

## Saídas

Plano em `docs/governance/agents` ou no local oficial indicado pela governança, com estado `Aguardando aprovação`.

## Gates

Fecha G5 somente com aprovação explícita do proprietário. A decomposição fecha G6 para o primeiro slice apenas quando limites e checks estiverem claros.

## Handoff

Após aprovação, entregue o caminho do plano, slice atual, orçamento de mudança, riscos e checks para `$execute`.

## Modos de falha

- Pare se faltar critério de aceite testável.
- Pare se o plano presumir decisão aberta.
- Não use slices como “implementar tudo”.
- Não implemente antes da aprovação.
