---
name: architect
description: Desenhe mudanças substanciais ou arquiteturais, compare alternativas, defina invariantes e registre decisões; não use para implementar nem para mudanças triviais.
---

# Architect

## Propósito

Converter entendimento aprovado em arquitetura explícita, testável e reversível quando possível.

## Quando usar

Use para fronteiras, dados, APIs, segurança, integrações, infraestrutura, migrações ou decisões técnicas com impacto futuro.

## Quando não usar

Não use quando não existe escolha arquitetural real ou quando uma decisão vigente já determina a solução sem alteração material.

## Entradas

- Saída de `$discover`.
- Fontes de verdade e decisões vigentes.
- Restrições operacionais, de segurança, custo e testes.

## Procedimento

1. Confirme requisitos, restrições e arquitetura existente.
2. Identifique fronteiras e ownership.
3. Produza pelo menos duas alternativas reais para escolhas materiais.
4. Compare simplicidade, manutenção, extensibilidade, risco, testabilidade, custo e impacto futuro.
5. Recomende uma abordagem e declare condições que mudariam a recomendação.
6. Defina arquitetura alvo, dados, API, interface, infraestrutura, erros, autorização, observabilidade, rollout e rollback.
7. Extraia invariantes e indique quais merecem enforcement mecânico.
8. Registre decisão relevante usando [`adr.md`](../../templates/adr.md) e a governança do TiaNet.
9. Não modifique documentos congelados sem reabertura controlada.

## Saídas

Design arquitetural, ADR quando aplicável, riscos e estratégia de testes.

## Gates

Fecha G3. G4 fecha apenas quando a decisão necessária estiver formalmente aprovada.

## Handoff

Entregue arquitetura, decisão, invariantes, riscos e assuntos adiados para `$plan`.

## Modos de falha

- Pare diante de decisão aberta que bloqueie a arquitetura.
- Não escolha tecnologia por preferência sem critérios verificáveis.
- Não esconda custo de migração ou reversão.
- Não implemente.
