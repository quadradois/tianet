# US-015 — Criar Devedor

**ID:** US-015

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** cadastrar um novo Devedor na minha Carteira

**Para** formalizar o relacionamento com o tomador e habilitar operações de crédito futuras de forma segura e rastreável.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir informar os dados obrigatórios do Devedor;
- os dados forem validados antes da criação;
- a unicidade do documento na Carteira for garantida;
- o Devedor for vinculado à Carteira;
- o estado inicial Ativo for definido;
- os contatos forem registrados;
- o processo for registrado para auditoria;
- o sistema confirmar a criação do Devedor.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-020 — Aggregate Devedor;
- DOMAIN-022 — Value Object Documento;
- DOMAIN-023 — Domain Service UnicidadeDevedorService;
- DOMAIN-024 — Business Rule Documento Único por Carteira;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-019 — Toda Carteira pertence exatamente a um Tenant;
- FEATURE-005 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-005 — Criar Devedor;
- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro.

---

# 5. Observações Técnicas

A implementação deverá tratar a criação do Devedor como um cadastro consistente: validação → unicidade → criação → vínculo com a Carteira → contatos → confirmação, em transação única (AD-001), com Idempotency-Key (AD-002) e auditoria append-only (ADR-002).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Criar Devedor. |
