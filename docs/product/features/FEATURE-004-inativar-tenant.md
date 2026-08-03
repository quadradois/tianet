# FEATURE-004 — Inativar Tenant

**ID:** FEATURE-004

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Permitir a alteração do estado operacional de uma organização (Tenant) entre **Ativo** e **Inativo**, preservando a integridade do domínio, a rastreabilidade da operação e o isolamento entre Tenants.

Esta capacidade pertence ao **Platform Context**.

Nenhuma operação financeira faz parte desta Feature.

---

# 2. Valor de Negócio

Permitir que organizações deixem temporariamente de operar sem perda de histórico, preservando a consistência dos dados e possibilitando futura reativação.

---

# 3. Escopo

Esta Feature contempla:

- inativação de Tenant ativo;
- reativação de Tenant inativo;
- validação das transições permitidas pela máquina de estados;
- preservação integral dos dados da organização;
- utilização da infraestrutura oficial de auditoria;
- retorno do estado atualizado da organização.

Esta Feature NÃO contempla:

- exclusão física de Tenant;
- alteração de dados cadastrais;
- gerenciamento de usuários;
- gerenciamento de carteiras;
- autenticação;
- autorização;
- qualquer operação do Credit Context.

---

# 4. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-013 — Inativar Tenant.
- US-014 — Reativar Tenant.

---

# 5. Dependências

Esta Feature depende dos seguintes documentos:

- FOUNDATION-006 — Arquitetura Multi-Tenant;
- DOMAIN-017 — Aggregate Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant;
- FEATURE-002 — Consultar Tenant;
- FEATURE-003 — Atualizar Tenant.

---

# 6. Critérios de Aprovação

A Feature será considerada concluída quando:

- apenas Tenants ativos puderem ser inativados;
- apenas Tenants inativos puderem ser reativados;
- a máquina de estados oficial for respeitada;
- nenhuma informação da organização for removida;
- a auditoria oficial registrar todas as mudanças de estado;
- a resposta utilizar DTO específico da camada Presentation;
- nenhuma regra de negócio for implementada fora do Domain;
- todos os testes previstos forem aprovados.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 02/08/2026 | Primeira versão oficial da Feature Inativar Tenant. |
