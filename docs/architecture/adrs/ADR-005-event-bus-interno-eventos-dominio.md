# ADR-005: Event Bus Interno e Eventos de Dominio

> **Status:** Aceito
> **Data:** 2026-08-11
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura
> **Aprovacao:** Arquitetura / 2026-08-11
> **Substitui:** —
> **Substituido por:** —

---

## Contexto

O AMP-001 reserva a ADR-005 para Event Bus / Mensageria. A plataforma ainda e
um monolito modular e nao precisa de broker externo para o MVP, mas os EPICs ja
produzem fatos de dominio que serao consumidos por Operacao Diaria, relatorios,
projections e automacoes futuras.

Sem um contrato minimo, cada contexto tende a publicar ou consumir eventos de
forma propria, criando acoplamento invisivel.

---

## Decisao

Decidimos que o EPIC-008 introduz apenas um **contrato interno de eventos**:

- envelope padrao com `event_id`, `event_type`, `event_version`, `occurred_at`,
  `tenant_id`, `correlation_id` e `payload`;
- publicacao inicial por porta interna ou dispatcher em memoria;
- consumidores dentro do mesmo processo;
- idempotencia por `event_id` e versao;
- events/projections sempre reconstruiveis a partir das fontes oficiais.

Broker externo, outbox transacional completa, mensageria distribuida e Saga
ficam fora deste ciclo.

---

## Alternativas Consideradas

| Opcao | Pros | Contras | Decisao |
|---|---|---|---|
| Nenhum contrato de evento | simplicidade imediata | acoplamento crescente e dificil de auditar | rejeitada |
| Broker externo agora | prepara escala | complexidade operacional antes do MVP precisar | rejeitada |
| Outbox completa agora | confiabilidade forte | custo alto e fora do recorte do EPIC-008 | rejeitada |
| Porta interna com envelope padrao | desacopla sem infra extra | entrega confiabilidade limitada ao processo | escolhida |

---

## Consequencias

- Produtores e consumidores passam a falar por contrato estavel.
- Correlation ID acompanha eventos internos.
- Projections podem nascer sem virar verdade paralela.
- Falhas fora do processo ainda nao sao tratadas como mensageria confiavel.

---

## Validacao

- testes de envelope obrigatorio;
- testes de idempotencia por `event_id`;
- guardrail impedindo projection ou evento de calcular juros, saldo, quitacao,
  amortizacao ou memoria fora do Motor.

---

## Referencias

- AMP-001 - ADR-005 reservada para Event Bus / Mensageria;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- US-097 - Definir Contrato Inicial de Eventos Internos;
- US-098 - Proteger Projections contra Verdade Paralela;
- ADR-016 - Observability, Logging e Correlation ID.

---

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Decisao registrada com recorte minimo de Event Bus interno para o EPIC-008. |
