# US-049 — Consultar Trilha de Decisões Comerciais

**ID:** US-049

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Administrador do Tenant

**Quero** consultar a trilha de decisões comerciais de uma proposta

**Para** verificar quem decidiu, quando decidiu e qual transição foi executada.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir consultar a trilha de decisões de uma proposta da Carteira autenticada;
- cada decisão exibir estado anterior, estado posterior, ator e instante;
- proposta inexistente ou de outro Tenant responder como não encontrada;
- a trilha for append-only;
- a operação exigir Principal autenticado e permissão comercial adequada;
- a consulta não permitir alteração ou remoção de registros.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-015 — Consultar Propostas;
- FEATURE-016 — Decidir Proposta;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-015 — Consultar Propostas;
- FEATURE-016 — Decidir Proposta.

---

# 5. Observações Técnicas

A trilha comercial deve aproveitar o padrão append-only existente, sem criar
capacidade de edição ou remoção de decisões já registradas.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Consultar Trilha de Decisões Comerciais. |
