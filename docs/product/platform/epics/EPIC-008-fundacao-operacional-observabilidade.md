# EPIC-008 - Fundacao Operacional e Observabilidade

**ID:** EPIC-008

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Epic estabelece a base operacional minima para que o backend possa evoluir
com seguranca: pipeline de qualidade, healthcheck real, correlation ID, logs
estruturados, tratamento tecnico de erros, runbook operacional e contratos
iniciais de eventos/projections.

O EPIC-008 e um pacote transversal da Plataforma. Ele nao adiciona regra de
negocio de credito e nao altera calculos financeiros.

---

# 2. Valor de Negócio

O backend ja cobre os fluxos principais do MVP, mas uma operacao real exige que
falhas sejam detectadas cedo, diagnosticadas rapidamente e rastreadas de ponta a
ponta. Este Epic reduz risco de regressao, deploy manual, erro silencioso e
debug sem contexto.

---

# 3. Escopo

Este Epic contempla:

- pipeline de qualidade para PR e `master`;
- validacao reproduzivel de migrations;
- healthcheck real da aplicacao e banco;
- correlation ID em toda requisicao HTTP;
- logs estruturados com mascaramento de dados sensiveis;
- tratamento tecnico de erros inesperados;
- runbook minimo de operacao;
- contrato inicial de eventos internos;
- diretrizes de projections/read models reconstruiveis;
- guardrails para impedir vazamento de segredo e calculo financeiro fora do
  Motor.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- Scheduler de producao, cron, batch ou job queue;
- Notification real, WhatsApp, SMS, e-mail ou push;
- broker externo, outbox completa ou mensageria distribuida;
- dashboards APM externos ou tracing distribuido completo;
- infraestrutura cloud/IaC completa;
- API publica, API Gateway ou rate limiting externo;
- frontend;
- qualquer mudanca em regra financeira, juros, saldo, quitacao, amortizacao ou
  memoria de calculo.

---

# 5. Features

Este Epic e composto pelas seguintes Features:

- FEATURE-032 - Automatizar Pipeline de Qualidade;
- FEATURE-033 - Validar Saude Operacional do Backend;
- FEATURE-034 - Rastrear Requisicoes com Correlation ID;
- FEATURE-035 - Padronizar Logs e Erros Tecnicos;
- FEATURE-036 - Preparar Eventos Internos e Projections.

---

# 6. Dependências

Este Epic depende de:

- PRODUCT-001 - Administrar Plataforma;
- EPIC-006 - IAM;
- EPIC-007 - Operacao Diaria;
- FOUNDATION-008 - Escopo Oficial do MVP;
- FOUNDATION-009 - Capability Map;
- ADR-001 - Stack Tecnologica Oficial do MVP;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- ADR-015 - CI/CD e Gates de Qualidade;
- ADR-016 - Observability, Logging e Correlation ID;
- Discovery/SDD do EPIC-008.

---

# 7. Critérios de Aprovação

Este Epic sera considerado pronto para implementacao quando:

- Product, ADRs, PLAN e backlog estiverem consistentes;
- pipeline minimo estiver definido com comandos locais equivalentes;
- healthcheck publico nao vazar dados sensiveis;
- correlation ID tiver contrato de entrada e saida;
- logs tecnicos forem separados da auditoria de negocio;
- eventos internos e projections forem explicitamente preparatorios;
- guardrails impedirem calculo financeiro fora do Motor;
- `npm run docs:validate` e `npm run docs:test` passarem sem erros.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao formal do EPIC-008 - Fundacao Operacional e Observabilidade. |
