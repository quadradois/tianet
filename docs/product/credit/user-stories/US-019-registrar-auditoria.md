# US-019 — Registrar Auditoria do Cadastro

**ID:** US-019

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** que toda escrita no cadastro do Devedor seja registrada em trilha de auditoria

**Para** garantir rastreabilidade e conformidade das operações cadastrais.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a criação do Devedor for registrada com sucesso e falha;
- a trilha for append-only e sobreviver a rollback da transação de negócio;
- consultas de leitura não gerarem trilha;
- a trilha permitir reconstituir o histórico cadastral do Devedor.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-020 — Aggregate Devedor (INV-004);
- FEATURE-005 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- US-015 — Criar Devedor;
- FEATURE-005 — Criar Devedor.

---

# 5. Observações Técnicas

Reutilizar a infraestrutura de auditoria existente do EPIC-001 (SqlAlchemyAuditoriaRegistro, trilha append-only em sessão independente) conforme ADR-002.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Registrar Auditoria do Cadastro. |