# EPIC-001 — Gerenciar Tenant

**ID:** EPIC-001

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Este Épico é responsável por administrar o ciclo de vida dos Tenants da plataforma.

Seu objetivo é garantir que cada organização possa ser criada, identificada, mantida e administrada de forma independente, preservando o isolamento definido pela arquitetura Multi-Tenant.

---

# 2. Valor de Negócio

O gerenciamento de Tenants estabelece a base organizacional da plataforma.

Sem este Épico não é possível criar organizações, separar dados entre clientes nem garantir o isolamento operacional previsto pela arquitetura.

---

# 3. Escopo

Este Épico contempla:

- criação de Tenant;
- consulta de Tenant;
- atualização cadastral;
- ativação e inativação;
- administração do estado operacional do Tenant;
- consulta das informações institucionais.

---

# 4. Fora do Escopo

Este Épico não contempla:

- gerenciamento de Usuários;
- autenticação;
- perfis de acesso;
- permissões;
- configurações;
- operações de crédito.

---

# 5. Features

Este Épico é composto pelas seguintes Features:

- FEATURE-001 — Criar Tenant;
- FEATURE-002 — Consultar Tenant;
- FEATURE-003 — Atualizar Tenant;
- FEATURE-004 — Ativar/Inativar Tenant.

---

# 6. Dependências

Este Épico depende de:

- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-019 — Toda Carteira pertence exatamente a um Tenant.

---

# 7. Critérios de Aprovação

Este Épico será considerado concluído quando:

- todas as Features estiverem implementadas;
- o ciclo de vida do Tenant estiver operacional;
- o isolamento entre organizações estiver garantido;
- todas as funcionalidades estiverem aderentes ao escopo do MVP.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do EPIC-001 — Gerenciar Tenant. |
