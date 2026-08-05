# US-018 — Registrar Contatos do Devedor

**ID:** US-018

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** registrar os contatos do Devedor durante o cadastro

**Para** garantir um canal de comunicação válido e tipado com o tomador.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- ao menos um contato válido (telefone, e-mail ou WhatsApp) for registrado;
- cada contato possuir um tipo definido;
- o valor do contato for validado conforme o tipo;
- apenas um contato puder ser preferencial por tipo;
- contatos inválidos retornarem 422 sem criar cadastro.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-021 — Entity Contato (RN-002, RN-003, RN-005);
- DOMAIN-020 — Aggregate Devedor;
- FEATURE-005 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- US-015 — Criar Devedor;
- US-016 — Validar Dados Obrigatórios do Devedor;
- FEATURE-005 — Criar Devedor.

---

# 5. Observações Técnicas

Contatos são entidades filhas do Devedor (DOMAIN-021), persistidas na mesma transação de criação do cadastro (AD-001).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Registrar Contatos do Devedor. |