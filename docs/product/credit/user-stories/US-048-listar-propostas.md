# US-048 — Listar Propostas

**ID:** US-048

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** listar propostas da minha Carteira com filtros

**Para** acompanhar o funil comercial por Devedor, estado e período.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema listar apenas propostas da Carteira autenticada;
- a listagem aceitar filtros por Devedor, estado e período;
- a listagem tiver paginação e ordenação determinística;
- filtros inválidos responderem erro de validação;
- a operação exigir Principal autenticado e permissão comercial;
- a listagem não expuser dados de outro Tenant.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-015 — Consultar Propostas;
- EPIC-003 — Comercial / Propostas / Simulação;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-015 — Consultar Propostas.

---

# 5. Observações Técnicas

A ordenação determinística deve ser definida no plano de implementação para
evitar paginação instável conforme o volume de propostas crescer.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Listar Propostas. |
