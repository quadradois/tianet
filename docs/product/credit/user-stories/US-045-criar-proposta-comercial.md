# US-045 — Criar Proposta Comercial

**ID:** US-045

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** criar uma proposta comercial para um Devedor ativo

**Para** registrar uma intenção de crédito que possa ser analisada e decidida.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir informar parâmetros comerciais da proposta;
- a proposta for vinculada à Carteira autenticada;
- a proposta for vinculada a um Devedor ativo da mesma Carteira;
- a proposta nascer em estado inicial válido;
- a criação exigir Principal autenticado e permissão comercial;
- a criação for registrada para auditoria;
- a proposta não criar Contrato, Empréstimo, Parcela ou Pagamento.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-014 — Criar Proposta Comercial;
- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-014 — Criar Proposta Comercial;
- PRODUCT-003 — Capability Administrar Comercial.

---

# 5. Observações Técnicas

A proposta deve ser um artefato comercial. Mesmo quando derivada de uma
simulação, seus parâmetros aprováveis precisam ser registrados sem duplicar
regras do Motor Financeiro.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Criar Proposta Comercial. |
