# FEATURE-006 — Consultar Devedor

**ID:** FEATURE-006

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por disponibilizar a consulta dos dados cadastrais dos Devedores da Carteira.

Seu objetivo é permitir a recuperação de um Devedor por ID ou por documento, e a listagem paginada com ordenação determinística, garantindo visibilidade operacional e governança sobre o cadastro.

---

# 2. Valor de Negócio

Esta Feature dá suporte à operação diária do Credor e à integração com os fluxos comerciais futuros.

Sem esta Feature, não há como verificar cadastros existentes, validar unicidade por consulta ou acompanhar o conjunto de Devedores da Carteira.

---

# 3. Escopo

Esta Feature contempla:

- consultar Devedor por ID (UUID);
- consultar Devedor por documento (CPF);
- listar Devedores com paginação, ordenação e filtros;
- consultar o histórico cadastral do Devedor (US-027);
- retornar apenas dados cadastrais e de estado;
- preservar o isolamento por Carteira/Tenant.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- atualização de dados cadastrais (FEATURE-007);
- inativação/reativação (FEATURE-008);
- autenticação e autorização (EPIC-006);
- qualquer operação de escrita.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-021 — Consultar Devedor por ID;
- US-022 — Consultar Devedor por Documento;
- US-023 — Listar Devedores;
- US-027 — Consultar Histórico Cadastral do Devedor.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro;
- FEATURE-005 — Criar Devedor (produz os dados consultados);
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- DOMAIN-020 — Aggregate Devedor;
- ADR-002 — Auditoria Independente da Transação (consultas não são auditadas).

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- o Devedor puder ser consultado por ID e por documento;
- a listagem paginada funcionar com ordenação determinística;
- dados inexistentes retornarem 404;
- o isolamento por Carteira/Tenant for preservado;
- todas as User Stories estiverem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Feature Consultar Devedor, criada no ciclo SDD do EPIC-002. |
