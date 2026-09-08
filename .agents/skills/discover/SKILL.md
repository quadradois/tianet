---
name: discover
description: Investigue o repositório e transforme uma ideia, problema ou pedido desconhecido em entendimento estruturado; use antes de planejar trabalho substancial e não use para implementar.
---

# Discover

## Propósito

Produzir contexto confiável e, quando necessário, um modelo de domínio antes de escolher solução técnica.

## Quando usar

Use para trabalho `STANDARD`, `SUBSTANTIAL` ou `ARCHITECTURAL`, requisitos novos, problemas pouco compreendidos ou retomada sem contexto suficiente.

## Quando não usar

Não use para uma alteração `TRIVIAL` já localizada nem para implementar código.

## Entradas

- Pedido do usuário.
- `AGENTS.md`, estado e decisões do projeto.
- Documentação, código e testes relacionados.
- Grafo existente, quando disponível.

## Procedimento

1. Leia `AGENTS.md`, `docs/README.md`, estado e decisões aplicáveis.
2. Consulte o grafo antes de uma varredura ampla quando `graphify-out/graph.json` existir.
3. Inspecione fontes relevantes e registre conflitos ou lacunas.
4. Produza: Problema, Objetivo, Contexto, Escopo, Não objetivos, Fatos, Desconhecidos, Hipóteses e Riscos iniciais.
5. Quando o domínio afetar a solução, modele entidades, relações, responsabilidades, estados, eventos, invariantes, ownership, entradas e saídas.
6. Separe explicitamente modelos de domínio, banco, API e interface; não presuma equivalência entre eles.
7. Classifique o trabalho usando [`classification-and-gates.md`](../../policies/classification-and-gates.md).

## Saídas

Relatório de descoberta em conversa ou documento solicitado, com classificação e recomendação do próximo workflow.

## Gates

Fecha G0 e G1. Fecha G2 somente quando o modelo de domínio estiver suficiente para orientar arquitetura.

## Handoff

Entregue achados, fontes, incertezas, riscos, classificação e próximo passo para `$architect` ou `$plan`.

## Modos de falha

- Pare se fontes oficiais conflitarem de forma material.
- Não transforme hipótese em fato.
- Não invente modelo quando o repositório não fornece evidência.
- Não altere produto, arquitetura ou código.
