# FEATURE-010 — Gerir Credenciais

**ID:** FEATURE-010

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por gerir a credencial de acesso dos Usuários do
Tenant no Platform Context.

Seu objetivo é definir a credencial inicial do Usuário — evento que o ativa,
transicionando-o de Convidado para Ativo —, permitir que cada Usuário altere a
própria credencial e possibilitar que um Usuário autorizado redefina a
credencial de outro Usuário do mesmo Tenant. Em nenhuma etapa a credencial é
armazenada ou recuperada em texto legível.

---

# 2. Valor de Negócio

Sem uma credencial definida, o Usuário permanece Convidado e não pode se
autenticar — a plataforma não recebe dado real sem um IAM (EPIC-006). Esta
Feature é o que torna cada Usuário realmente operável: a credencial ativa a
pessoa autorizada, garante que ela trafega exclusivamente por ela e permite
recuperar o acesso sem expor segredo algum.

Devolver o acesso a um Usuário que perdeu a credencial é ação administrativa
possível dentro do mesmo Tenant, sem depender de outros meios (fora do escopo
do épico).

---

# 3. Escopo

Esta Feature contempla:

- definir a credencial inicial do Usuário, transicionando-o de Convidado para
  Ativo;
- exigir que a definição da credencial inicial seja o evento de ativação do
  Usuário;
- alterar a própria credencial pelo Usuário autenticado;
- redefinir a credencial de um Usuário do mesmo Tenant (ação administrativa);
- garantir que a credencial nunca seja armazenada de forma legível e nunca seja
  reproduzível;
- registrar a definição, alteração e redefinição de credencial na trilha
  append-only (ADR-002);
- conduzir toda definição ou redefinição de credencial dentro da fronteira do
  Tenant — nenhum Usuário age sobre Usuário de outro Tenant;
- exigir Autorização por perfil para a redefinição administrativa de credencial
  (RBAC).

---

# 4. Fora do Escopo

Esta Feature não contempla:

- autenticação do Usuário e emissão de tokens (FEATURE-009 — Autenticar Usuário);
- renovação de sessão por refresh token (FEATURE-009);
- autorização de cada operação por perfil (FEATURE-012 — Autorizar Requisição);
- criação e manutenção de Perfis e Permissões (FEATURE-011 — Gerir Perfis e Permissões);
- recuperação de senha por e-mail (autoatendimento, pós-MVP);
- SSO, federação de identidade (OIDC) e MFA;
- gestão de credencial de Usuário de outro Tenant (isolamento absoluto).

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-032 — Definir Credencial Inicial;
- US-033 — Alterar a Própria Credencial;
- US-034 — Redefinir Credencial de Usuário.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-001 — Stack oficial (JWT Bearer + Refresh Token);
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuário (RN-001, INV-001, INV-002, INV-003);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03, isolamento);
- FOUNDATION-008 — MVP Scope (Usuários, Autenticação);
- FOUNDATION-009 — RBAC (autorização conforme Perfil);
- FEATURE-009 — Autenticar Usuário (o ciclo ativado por esta Feature só passa a
  ser exercido com autenticação).

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- o Usuário não ativado (Convidado) só poder ser ativado pela definição da
  credencial;
- a definição da credencial inicial transicionar o Usuário de Convidado para
  Ativo;
- a credencial nunca for armazenada nem persistida em texto legível;
- a credencial não poder ser recuperada, apenas redefinida;
- a alteração da própria credencial exigir a credencial anterior vigente;
- a redefinição de credencial de outro Usuário exigir autorização por perfil e
  manter-se dentro do mesmo Tenant;
- Usuário Inativo ou Removido não puder ter credencial definida ou alterada;
- a tentativa de agir sobre Usuário de outro Tenant responder 404, sem revelar
  sua existência;
- cada definição, alteração ou redefinição ser registrada para auditoria na
  trilha append-only (ADR-002);
- as User Stories US-032, US-033 e US-034 estarem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|-----|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da Feature Gerir Credenciais, criada no ciclo SDD do EPIC-006. |