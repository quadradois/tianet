# US-047 — Consultar Proposta por ID

**ID:** US-047

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** consultar uma proposta comercial por ID

**Para** revisar seus parâmetros, estado e dados de rastreabilidade.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir consultar proposta por ID;
- apenas proposta da Carteira autenticada for retornada;
- proposta inexistente ou de outro Tenant responder como não encontrada;
- a resposta incluir estado, parâmetros comerciais e referências a Carteira e Devedor;
- a operação exigir Principal autenticado e permissão comercial;
- a consulta não alterar estado nem criar auditoria de escrita.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-015 — Consultar Propostas;
- FEATURE-014 — Criar Proposta Comercial;
- EPIC-003 — Comercial / Propostas / Simulação;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-015 — Consultar Propostas;
- FEATURE-014 — Criar Proposta Comercial.

---

# 5. Observações Técnicas

A consulta deve usar a Carteira como fronteira operacional e manter o mesmo
contrato de não revelação usado para recursos cross-tenant.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Consultar Proposta por ID. |
