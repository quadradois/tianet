# EPIC-006 — IAM — Identidade e Controle de Acesso

**ID:** EPIC-006

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Épico é responsável por estabelecer quem opera a plataforma e o que cada um pode fazer.

Seu objetivo é autenticar Usuários por credencial própria, autorizar cada operação conforme o Perfil recebido e garantir que nenhum Tenant alcance dados de outro — transformando o isolamento multi-tenant de premissa em verificação.

---

# 2. Valor de Negócio

Nenhum dos 14 endpoints da plataforma exige autenticação hoje, e nenhuma rota verifica a que organização pertence o recurso acessado. Enquanto isso permanecer, o backend não pode receber dado real de cliente.

Este Épico não entrega funcionalidade de negócio: entrega a condição para que todas as demais possam ser usadas em produção. Ele é pré-requisito de segurança, e cada Épico construído antes dele aumenta o retrabalho de proteção posterior.

---

# 3. Escopo

Este Épico contempla:

- autenticação por credencial, com emissão de token de acesso e refresh token;
- renovação de sessão sem novo login e encerramento de sessão;
- definição, alteração e redefinição de credencial;
- ativação do Usuário no momento em que define sua credencial;
- criação e manutenção de Perfis de Acesso e suas Permissões;
- atribuição de Perfil a Usuário;
- autorização de cada operação conforme o Perfil (RBAC);
- resolução do Tenant autenticado e bloqueio de acesso a recursos de outra organização;
- auditoria dos eventos de acesso.

---

# 4. Fora do Escopo

Este Épico não contempla:

- SSO e federação de identidade (OIDC);
- autenticação multifator (MFA);
- autorização por atributo (ABAC) — o modelo adotado é RBAC;
- recuperação de credencial por e-mail — depende de Notification Service;
- autenticação de sistemas externos (chaves de API, contas de serviço);
- gestão de Configurações da Plataforma — capability própria, sem Épico atribuído;
- revogação imediata do token de acesso — a janela é de até 15 minutos, conforme ADR-004.

---

# 5. Features

Este Épico é composto pelas seguintes Features:

- FEATURE-009 — Autenticar Usuário;
- FEATURE-010 — Gerir Credenciais;
- FEATURE-011 — Gerir Perfis e Permissões;
- FEATURE-012 — Autorizar Requisição.

---

# 6. Dependências

Este Épico depende de:

- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map;
- ADR-001 — Stack Tecnológica Oficial do MVP;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-018 — Identidade Externa do Aggregate Devedor;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario.

---

# 7. Critérios de Aprovação

Este Épico será considerado concluído quando:

- todas as Features estiverem implementadas;
- os 13 endpoints protegidos recusarem requisição sem token válido, permanecendo apenas o healthcheck público;
- a autorização por Perfil estiver operacional em todas as operações de escrita;
- nenhum acesso atravessar a fronteira de organização, comprovado por teste de integração com dois Tenants distintos;
- a credencial não existir em texto legível em nenhum ponto do sistema;
- os eventos de acesso estiverem registrados na trilha de auditoria;
- a revogação de sessão interromper o acesso dentro da janela definida na ADR-004.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial do EPIC-006 — IAM, materializada a partir do Discovery e das decisões da ADR-004. |
