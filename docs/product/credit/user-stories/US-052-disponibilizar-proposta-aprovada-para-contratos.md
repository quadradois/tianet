# US-052 — Disponibilizar Proposta Aprovada para Contratos

**ID:** US-052

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Sistema

**Quero** disponibilizar propostas aprovadas como entrada lógica para Contratos

**Para** que a futura formalização contratual consuma apenas decisões comerciais
válidas e rastreáveis.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- apenas proposta aprovada puder ser disponibilizada para Contratos futuro;
- proposta em análise, recusada, cancelada ou expirada não puder ser consumida;
- a saída lógica incluir proposta, Tenant, Carteira, Devedor e parâmetros aprovados;
- os parâmetros aprovados forem imutáveis;
- a saída preservar instante e ator da aprovação;
- nenhuma formalização contratual ocorrer dentro do Comercial;
- nenhum cálculo financeiro definitivo for executado.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-017 — Integrar Proposta Aprovada;
- FEATURE-016 — Decidir Proposta;
- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- ADR-002 — Auditoria Independente da Transação.

---

# 4. Dependências

Esta User Story depende de:

- US-050 — Aprovar Proposta;
- FEATURE-017 — Integrar Proposta Aprovada.

---

# 5. Observações Técnicas

Esta User Story define apenas o contrato lógico de saída do Comercial. O
documento de implementação deverá impedir que esse contrato vire criação de
Contrato de Crédito, Empréstimo ou Pagamento dentro do EPIC-003.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Disponibilizar Proposta Aprovada para Contratos. |
