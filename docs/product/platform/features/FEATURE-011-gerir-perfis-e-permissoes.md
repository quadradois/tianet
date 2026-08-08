# FEATURE-011 — Gerir Perfis e Permissões

**ID:** FEATURE-011

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por gerir Perfis de Acesso e Permissões dos Usuários do Tenant no Platform Context.

Seu objetivo é permitir que cada Tenant crie e mantenha seus próprios Perfis de Acesso, associe Permissões a esses Perfis, atribua Perfis aos seus Usuários e consulte as Permissões efetivas de um Usuário — estabelecendo, no registro, o que cada Usuário pode fazer dentro do seu Tenant. A consulta das Permissões efetivas fecha o ciclo: a autorização de cada operação, conforme o Perfil (RBAC), é exercida sobre essa base quando o Usuário opera a plataforma (FEATURE-012).

---

# 2. Valor de Negócio

O RBAC é o modelo de autorização aprovado para o IAM (FOUNDATION-009 §117 e ADR-004): decidir o que cada Usuário pode fazer pelo Perfil recebido, e não por atributo individual — ABAC está fora de escopo.

Esta Feature dá aos Tenants o controle sobre essa decisão: perfis nomeados de Permissões são criados e mantidos dentro do Tenant, sem depender do time de produto para cada ajuste, e são atribuídos aos Usuários de forma rastreável. Sem Perfis e Permissões não há base para autorizar ninguém — e nenhum endpoint protegido consegue diferenciar o que cada operador pode executar, tornando o isolamento por Tenant insuficiente para distinguir responsabilidades dentro do próprio Tenant.

---

# 3. Escopo

Esta Feature contempla (todas as operações restritas à fronteira do Tenant — nenhuma atravessa a fronteira):

- criar, consultar e manter Perfis de Acesso dentro do Tenant;
- associar e remover Permissões de um Perfil;
- listar e consultar as Permissões de um Perfil;
- atribuir, alterar e remover a atribuição de Perfil de um Usuário do mesmo Tenant;
- consultar as Permissões efetivas de um Usuário (perfil atribuído);
- decidir a autorização por operação, não por recurso individual (RBAC);
- garantir que nenhum Perfil de outro Tenant seja visível, consultável ou alterável;
- exigir autorização por perfil (RBAC) para gerir Perfis e atribuí-los a Usuários;
- registrar criação, alteração e atribuição de Perfil na trilha append-only (ADR-002).

---

# 4. Fora do Escopo

Esta Feature não contempla:

- autenticação do Usuário e emissão de tokens (FEATURE-009 — Autenticar Usuário);
- gestão de credenciais (FEATURE-010 — Gerir Credenciais);
- autorização de cada operação em execução conforme o Perfil (FEATURE-012 — Autorizar Requisição), que consome as Permissões aqui definidas;
- autorização por atributo — ABAC (fora do escopo do épico, FOUNDATION-009 e ADR-004);
- transição de estado do Usuário (ativação, inativação, remoção — a atribuição de Perfil aqui é independente do ciclo de vida, tratado em outras Features do EPIC-006);
- recuperação de senha por e-mail, SSO, OIDC, MFA e API keys (fora do escopo do épico).

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-035 — Criar e Manter Perfis;
- US-036 — Associar Permissões a Perfil;
- US-037 — Atribuir Perfil a Usuário;
- US-038 — Consultar Permissões Efetivas.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03, isolamento de Tenant);
- FOUNDATION-009 — RBAC (perfis e permissões, §117) e épico transversal (§185);
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario (todo Usuário pertence a exatamente um Tenant — INV-001);
- FEATURE-009 — Autenticar Usuário (a gestão de Perfis só é exercida por quem já autentica);
- FEATURE-012 — Autorizar Requisição (consome o modelo RBAC aqui criado para decidir cada operação).

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- um Perfil puder ser criado, consultado e mantido dentro do Tenant;
- Permissões puderem ser associadas e removidas do Perfil;
- a atribuição do Perfil a Usuário ocorrer dentro do mesmo Tenant;
- as Permissões efetivas de um Usuário refletirem as Permissões do Perfil atribuído;
- nenhum Perfil de outro Tenant for visível, consultável, alterável ou removível;
- recurso de outro Tenant responder 404, e não 403 — sem revelar existência (precedente da ADR-018);
- a autorização for decidida por permissão de operação, não por recurso individual (RBAC);
- a gestão de Perfis e a atribuição a Usuários exigirem autorização por perfil;
- cada criação, alteração e atribuição de Perfil ser registrada para auditoria na trilha append-only (ADR-002);
- as User Stories US-035, US-036, US-037 e US-038 estarem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da Feature Gerir Perfis e Permissões, criada no ciclo SDD do EPIC-006. |