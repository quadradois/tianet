# FEATURE-016 — Decidir Proposta

**ID:** FEATURE-016

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por registrar a decisão comercial de uma proposta:
aprovar, recusar, cancelar ou expirar.

Seu objetivo é controlar o ciclo de vida da proposta e preservar a rastreabilidade
das decisões antes da formalização contratual.

---

# 2. Valor de Negócio

A decisão comercial garante que apenas propostas aprovadas avancem para
Contratos, evitando obrigações sem avaliação e mantendo histórico de recusas,
cancelamentos e expirações.

---

# 3. Escopo

Esta Feature contempla:

- aprovar proposta elegível;
- recusar proposta;
- cancelar proposta antes da aprovação;
- expirar proposta vencida;
- impedir transições inválidas;
- auditar cada transição de estado;
- exigir permissão comercial de decisão.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- editar proposta aprovada;
- reabrir proposta terminal;
- formalizar contrato;
- gerar desembolso;
- executar cálculo financeiro definitivo.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-050 — Aprovar Proposta;
- US-051 — Encerrar Proposta sem Aprovação.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- FEATURE-014 — Criar Proposta Comercial;
- FEATURE-015 — Consultar Propostas;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- proposta elegível puder ser aprovada;
- proposta puder ser recusada, cancelada ou expirada;
- transição inválida responder conflito de estado;
- proposta terminal não puder voltar a estado operacional;
- cada decisão comercial estiver auditada;
- proposta aprovada não puder ter seus parâmetros comerciais alterados.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Feature Decidir Proposta, criada no ciclo SDD do EPIC-003. |
