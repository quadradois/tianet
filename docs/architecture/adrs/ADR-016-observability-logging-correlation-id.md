# ADR-016: Observability, Logging e Correlation ID

> **Status:** Aceito
> **Data:** 2026-08-11
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura
> **Aprovacao:** Arquitetura / 2026-08-11
> **Substitui:** —
> **Substituido por:** —

---

## Contexto

O AMP-001 aponta ausencia de observabilidade, logs estruturados e correlation ID
como divida perigosa. O EPIC-008 precisa tornar falhas diagnosticaveis sem
transformar logs em auditoria de negocio nem expor dados sensiveis.

---

## Decisao

Decidimos que toda requisicao HTTP deve possuir correlation ID:

- header de entrada e saida: `X-Correlation-ID`;
- valor valido do cliente e preservado;
- valor ausente ou invalido gera novo ID;
- respostas 2xx, 4xx e 5xx devolvem o ID;
- logs tecnicos incluem correlation ID.

Logs tecnicos devem ser estruturados e mascarar dados sensiveis. Healthcheck
publico deve expor somente informacao minima. Auditoria de negocio continua
governada pela ADR-002.

---

## Alternativas Consideradas

| Opcao | Pros | Contras | Decisao |
|---|---|---|---|
| Logs textuais atuais | simples | baixa rastreabilidade | rejeitada |
| Tracing distribuido completo | poderoso | complexo antes de servicos externos | rejeitada |
| Logs estruturados + correlation ID | alto ganho operacional com baixo custo | nao substitui APM completo | escolhida |

---

## Consequencias

- Suporte pode pedir correlation ID ao cliente.
- Erros 500 deixam de vazar stack trace.
- Logs precisam de politica de mascaramento.
- Observability permanece fundacao tecnica dentro de Platform/Engineering, sem
  inaugurar Bounded Context autonomo neste ciclo.

---

## Validacao

- teste de propagacao de `X-Correlation-ID`;
- teste de geracao quando header ausente;
- teste de resposta 500 segura;
- teste negativo contra vazamento de token, senha, DSN, documento pessoal e
  stack trace;
- teste de healthcheck publico minimo.

---

## Referencias

- AMP-001 - ADR-016 reservada para Observability / Logging / Tracing;
- ADR-002 - Auditoria Independente da Transacao;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- FEATURE-033 - Validar Saude Operacional do Backend;
- FEATURE-034 - Rastrear Requisicoes com Correlation ID;
- FEATURE-035 - Padronizar Logs e Erros Tecnicos.

---

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Decisao registrada para observabilidade basica, logs estruturados e correlation ID. |
