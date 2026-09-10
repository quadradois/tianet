---
name: verify
description: Verifique uma entrega do TiaNet por evidências, reconcilie plano e documentação, prepare handoff e transforme aprendizados duráveis em proteção; não adicione novo escopo.
---

# Verify

## Propósito

Provar o resultado, tornar riscos residuais explícitos e permitir continuidade sem histórico de chat.

## Quando usar

Use ao concluir slice relevante, conjunto de slices, Harness, pré-commit, pré-PR ou handoff.

## Quando não usar

Não use para iniciar implementação, ampliar produto ou esconder trabalho incompleto.

## Entradas

- Plano, diff, critérios, testes, revisões e documentos relacionados.
- Estado atual do repositório.

## Procedimento

1. Delimite o diff e separe alterações intencionais de mudanças alheias.
2. Reconcilie cada slice, decisão, risco e critério com a implementação observada.
3. Use [`verification.md`](../../templates/verification.md) para ligar requisito, evidência esperada, check, resultado e status.
4. Execute ou confirme o conjunto final mínimo de checks; registre o que não pôde ser executado.
5. Classifique revisão final com [`review.md`](../../templates/review.md).
6. Atualize o handoff usando [`handoff.md`](../../templates/handoff.md), mantendo-o curto e operacional.
7. Pergunte “o que aprendemos?” e converta somente aprendizado durável em documento, ADR, invariante, teste, lint, script ou regra.
8. Declare separadamente prontidão para verificação humana e prontidão para commit/PR.

## Saídas

Matriz de evidências, riscos residuais, revisão, handoff e aprendizado incorporado quando justificável.

## Gates

Fecha G10 quando os requisitos materiais possuem evidência. Fecha G11 quando uma sessão sem histórico consegue identificar estado e próxima ação.

## Handoff

Informe estado, concluído, em andamento, bloqueios, decisões, riscos, arquivos, testes, evidências, próximo slice e próxima ação.

## Modos de falha

- Não declare `VERIFICADO` sem resultado observado.
- Pare se plano e implementação divergirem materialmente.
- Reporte blocker não resolvido; não o esconda em ressalvas.
- Não faça commit, push ou PR sem pedido explícito.
