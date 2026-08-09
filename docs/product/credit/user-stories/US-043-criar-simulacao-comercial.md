# US-043 — Criar Simulação Comercial

**ID:** US-043

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** criar uma simulação comercial para um Devedor ativo da minha Carteira

**Para** avaliar um cenário de crédito antes de criar uma proposta formal.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir informar parâmetros comerciais da simulação;
- a simulação for vinculada à Carteira autenticada;
- a simulação for vinculada a um Devedor ativo da mesma Carteira;
- Devedor inexistente, inativo ou de outra Carteira impedir a criação;
- a operação exigir Principal autenticado e permissão comercial;
- a criação for registrada para auditoria;
- nenhum cálculo financeiro definitivo for executado.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- EPIC-003 — Comercial / Propostas / Simulação;
- FEATURE-013 — Simular Crédito;
- PRODUCT-003 — Capability Administrar Comercial;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-013 — Simular Crédito;
- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial.

---

# 5. Observações Técnicas

A implementação deve tratar a simulação como registro comercial não vinculante.
Ela pode armazenar parâmetros informados pelo Credor, mas não pode se tornar
memória de cálculo financeira nem gerar obrigação contratual.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Criar Simulação Comercial. |
