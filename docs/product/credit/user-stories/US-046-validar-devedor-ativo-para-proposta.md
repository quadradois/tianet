# US-046 — Validar Devedor Ativo para Proposta

**ID:** US-046

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** que o sistema valide se o Devedor está ativo e pertence à minha Carteira

**Para** impedir proposta comercial sobre cadastro inválido, inativo ou de outro
Tenant.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- proposta para Devedor ativo da Carteira autenticada for permitida;
- proposta para Devedor inativo for recusada;
- proposta para Devedor inexistente for recusada como não encontrada;
- proposta para Devedor de outra Carteira/Tenant for recusada como não encontrada;
- a validação ocorrer antes da criação da proposta;
- o erro não revelar existência de recurso de outro Tenant.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-014 — Criar Proposta Comercial;
- EPIC-002 — Cadastro de Devedores;
- DOMAIN-020 — Aggregate Devedor;
- DOMAIN-001 — Aggregate Carteira;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-014 — Criar Proposta Comercial;
- EPIC-002 — Cadastro de Devedores.

---

# 5. Observações Técnicas

A validação deve consumir Cadastro por referência e preservar a fronteira do
contexto Comercial, sem copiar o ciclo de vida completo do Devedor.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Validar Devedor Ativo para Proposta. |
