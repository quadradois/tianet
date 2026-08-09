# FEATURE-017 — Integrar Proposta Aprovada

**ID:** FEATURE-017

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por disponibilizar proposta aprovada como contrato
lógico de entrada para o contexto Contratos futuro.

Seu objetivo é encerrar o EPIC-003 com uma saída clara: somente proposta
aprovada pode seguir para formalização, sem criar contrato ou operação
financeira dentro do Comercial.

---

# 2. Valor de Negócio

A integração da proposta aprovada reduz ambiguidade entre Comercial e Contratos
e preserva a sequência oficial do roadmap.

---

# 3. Escopo

Esta Feature contempla:

- expor dados lógicos da proposta aprovada;
- preservar Tenant, Carteira e Devedor como fronteiras de integração;
- impedir consumo de proposta não aprovada;
- registrar instante e ator da aprovação;
- definir contrato de dados para Contratos futuro;
- manter imutabilidade dos parâmetros aprovados.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- criar Contrato de Crédito;
- assinar contrato;
- liberar crédito;
- criar Empréstimo;
- executar Motor Financeiro;
- publicar evento em mensageria externa.

---

# 5. User Stories

Esta Feature é composta pela seguinte User Story:

- US-052 — Disponibilizar Proposta Aprovada para Contratos.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- FEATURE-016 — Decidir Proposta;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- apenas proposta aprovada estiver disponível para Contratos futuro;
- proposta recusada, cancelada, expirada ou em análise não puder ser consumida;
- o contrato lógico incluir proposta, Tenant, Carteira, Devedor e parâmetros aprovados;
- os parâmetros aprovados forem imutáveis;
- nenhuma formalização contratual ocorrer dentro do Comercial.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Feature Integrar Proposta Aprovada, criada no ciclo SDD do EPIC-003. |
