# US-020 — Confirmar Criação do Devedor

**ID:** US-020

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** receber a confirmação da criação do Devedor

**Para** saber imediatamente que o cadastro foi formalizado e está apto a originar operações.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema retornar 201 após a criação;
- a resposta conter o identificador (ID) e o estado Ativo do Devedor;
- a resposta utilizar DTO único, sem expor dados internos de infraestrutura;
- replays com a mesma Idempotency-Key retornarem o resultado original (AD-002).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- AD-002 — Idempotency Key;
- FEATURE-005 — Criar Devedor;
- US-015 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- US-015 — Criar Devedor;
- US-016 — Validar Dados Obrigatórios do Devedor;
- US-017 — Validar Unicidade do Documento;
- US-018 — Registrar Contatos do Devedor;
- US-019 — Registrar Auditoria do Cadastro;
- FEATURE-005 — Criar Devedor.

---

# 5. Observações Técnicas

O DTO de resposta deve ser único (padrão EPIC-001 — RA-012), construído na Presentation a partir do Aggregate retornado pelo serviço. Idempotência aplicável à escrita de criação (AD-002).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Confirmar Criação do Devedor. |