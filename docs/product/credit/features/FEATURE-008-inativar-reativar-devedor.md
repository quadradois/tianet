# FEATURE-008 — Inativar/Reativar Devedor

**ID:** FEATURE-008

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável pelas transições de estado operacional do Devedor.

Seu objetivo é permitir a inativação (Ativo → Inativo) e a reativação (Inativo → Ativo), preservando integralmente o histórico cadastral e financeiro.

---

# 2. Valor de Negócio

Esta Feature garante que o cadastro reflita o relacionamento real do Credor com o Devedor sem perda de rastreabilidade.

Ela impede que Devedores sem relacionamento ativo originem novas operações, mantendo o histórico para auditoria e relatórios.

---

# 3. Escopo

Esta Feature contempla:

- inativar Devedor Ativo;
- reativar Devedor Inativo;
- validar a unicidade do documento na reativação;
- registrar auditoria das transições.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- exclusão física do cadastro (proibida — DOMAIN-025);
- alteração de dados cadastrais (FEATURE-007);
- efeitos sobre operações de crédito existentes (nenhum retroativo);
- autenticação e autorização.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-025 — Inativar Devedor;
- US-026 — Reativar Devedor.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro;
- DOMAIN-020 — Aggregate Devedor (máquina de estados);
- DOMAIN-024 — Business Rule Documento Único por Carteira (reativação);
- DOMAIN-025 — Business Rule Exclusão Física Proibida;
- ADR-002 — Auditoria Independente da Transação.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- a inativação de Devedor Ativo funcionar preservando o histórico;
- a reativação de Devedor Inativo funcionar com validação de unicidade;
- transições inválidas retornarem erro de estado;
- as transições estiverem registradas para auditoria;
- todas as User Stories estiverem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Feature Inativar/Reativar Devedor, criada no ciclo SDD do EPIC-002. |