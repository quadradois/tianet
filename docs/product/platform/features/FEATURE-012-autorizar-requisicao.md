# FEATURE-012 — Autorizar Requisição

**ID:** FEATURE-012

**Versão:** 1.1.0

**Status:** Concluido

---

# 1. Objetivo

Esta Feature é responsável por proteger os endpoints da API: validar o token de
acesso e resolver o Principal (Usuário + Tenant) a cada requisição, autorizar a
operação conforme o Perfil do Usuário (RBAC) e garantir que nenhum acesso
atravesse a fronteira de Tenant.

Seu objetivo é tornar o isolamento multi-tenant verificado pelo sistema — e não
dependente de disciplina —, de forma que todo endpoint protegido só execute com
um Principal autenticado e autorizado, conforme a ADR-004.

---

# 2. Valor de Negócio

O IAM é pré-requisito de segurança para produção (EPIC-006): sem ele, o backend
não pode receber dado real de cliente.

Esta Feature concretiza a proteção de cada requisição: quem opera é identificado,
o que cada um pode fazer é decidido pelo Perfil e nenhum Tenant alcança dados de
outro. A trilha de auditoria passa a registrar a negação de acesso, e `/health`
permanece público. Sem ela, os endpoints construídos a partir do EPIC-002
continuariam expostos sem controle de acesso.

---

# 3. Escopo

Esta Feature contempla:

- validar o token de acesso apresentado em toda requisição a endpoint protegido;
- autorizar apenas token válido, dentro da validade de 15 minutos;
- resolver o Principal (Usuário e Tenant) a partir do token validado;
- autorizar a operação conforme o Perfil do Usuário autenticado (RBAC);
- decidir a permissão por operação, não por recurso individual;
- barrar acesso a recurso de outro Tenant, respondendo 404 sem revelar existência;
- transmitir o Principal à requisição para as camadas subsequentes;
- disponibilizar ao próprio Principal autenticado seu contexto operacional
  corrente, incluindo Tenant, Carteira padrão, Perfil e Permissões efetivas;
- auditar eventos de acesso negado na trilha append-only (ADR-002);
- manter `/health` público.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- autenticação do Usuário e emissão de tokens (FEATURE-009 — Autenticar Usuário);
- gestão de credenciais (FEATURE-010 — Gerir Credenciais);
- criação e manutenção de Perfis e Permissões (FEATURE-011 — Gerir Perfis e Permissões);
- renovação da sessão por refresh token (FEATURE-009);
- autorização por atributo — ABAC (fora de escopo do épico, FOUNDATION-009 e ADR-004);
- autenticação de sistemas externos (API keys, service accounts);
- recuperação de senha, SSO, OIDC e MFA.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-039 — Validar Token e Resolver Principal;
- US-040 — Autorizar Operação por Perfil;
- US-041 — Barrar Acesso Cross-Tenant;
- US-042 — Auditar Eventos de Acesso Negado;
- US-125 — Consultar Contexto Operacional Corrente.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-001 — Stack oficial (JWT Bearer + Refresh Token);
- ADR-018 — Identidade externa do Devedor (dependência centralizada de rota);
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-018 — Entity Usuario;
- DOMAIN-017 — Aggregate Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03);
- FOUNDATION-009 — RBAC (autenticação autorização conforme Perfil);
- FEATURE-009 e FEATURE-011 — autonomia do token e regime de Perfis que
  autorizam a operação.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- endpoint protegido sem token válido responder 401;
- token válido sem permissão para a operação responder 403;
- recurso de outro Tenant responder 404, e não 403 — sem revelar existência
  (precedente da ADR-018);
- token expirado (após os 15 minutos de validade) não conceder acesso;
- o Principal (Usuário e Tenant) estiver resolvido e propagado a toda requisição
  protegida;
- o próprio Principal puder consultar Tenant, Carteira padrão, Perfil e
  Permissões efetivas sem informar `usuario_id` e sem exigir permissão
  administrativa adicional;
- a autorização for decidida pelo Perfil do Usuário autenticado (RBAC);
- eventos de acesso negado forem auditados na trilha append-only;
- `/health` permanecer acessível sem token.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 12/08/2026 | Complementa a Feature com US-125 para bootstrap autenticado do contexto operacional corrente. |
| 1.0.0 | 08/08/2026 | Primeira versão oficial da Feature Autorizar Requisição, criada no ciclo SDD do EPIC-006. |
