# FEATURE-009 — Autenticar Usuário

**ID:** FEATURE-009

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. Objetivo

Esta Feature é responsável por estabelecer a identidade de quem opera a
plataforma.

Seu objetivo é autenticar o Usuário por credencial e emitir um token de acesso
de curta duração acompanhado de um refresh token revogável, permitir a renovação
da sessão sem novo login, encerrar a sessão quando solicitado e recusar
tentativas inválidas sem revelar informação sobre a existência do identificador.

---

# 2. Valor de Negócio

Sem autenticação, qualquer requisição alcança qualquer organização — situação
atual da plataforma, registrada como dívida perigosa no AMP-001. Esta Feature é
a porta de entrada do sistema: nada do que as demais Features do EPIC-006
oferecem faz sentido antes que se saiba quem está do outro lado.

Ela também estabelece o custo operacional do acesso: o token curto obriga
renovação frequente, mas é o que permite revogar uma sessão comprometida em
minutos, e não em dias.

---

# 3. Escopo

Esta Feature contempla:

- autenticar o Usuário por identificador e credencial;
- emitir token de acesso com validade de 15 minutos e refresh token com validade
  de 7 dias, conforme ADR-004;
- renovar o token de acesso mediante refresh token válido, sem exigir novamente
  a credencial;
- encerrar a sessão, revogando o refresh token;
- recusar autenticação quando a credencial for inválida, o identificador não
  existir ou o Usuário não estiver em estado Ativo, sempre com a mesma resposta;
- registrar na trilha append-only (ADR-002) as autenticações bem-sucedidas, as
  tentativas recusadas e os encerramentos de sessão;
- resolver o Tenant do Usuário no momento da autenticação, para que o Principal
  carregue essa informação.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- definição, alteração ou redefinição de credencial (FEATURE-010 — Gerir
  Credenciais);
- criação e manutenção de Perfis e Permissões (FEATURE-011 — Gerir Perfis e
  Permissões);
- validação do token a cada requisição e autorização da operação (FEATURE-012 —
  Autorizar Requisição);
- SSO, federação de identidade (OIDC) e autenticação multifator (MFA);
- recuperação de credencial por e-mail;
- autenticação de sistemas externos (chaves de API, contas de serviço);
- revogação imediata do token de acesso — a janela é de até 15 minutos, conforme
  decidido na ADR-004.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-028 — Autenticar com Credencial;
- US-029 — Renovar Token de Acesso;
- US-030 — Encerrar Sessão;
- US-031 — Recusar Autenticação Inválida.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-001 — Stack Tecnológica Oficial do MVP (JWT Bearer + Refresh Token);
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização (IAM);
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map;
- FEATURE-010 — Gerir Credenciais (o Usuário precisa ter credencial definida e
  estar Ativo para autenticar).

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- a autenticação com credencial correta emitir token de acesso e refresh token;
- o token de acesso expirar em 15 minutos e o refresh token em 7 dias;
- a renovação com refresh token válido emitir novo token de acesso sem exigir a
  credencial;
- o refresh token revogado ou expirado não permitir renovação;
- o encerramento de sessão revogar o refresh token;
- credencial inválida, identificador inexistente e Usuário não-Ativo produzirem
  a mesma resposta, sem distinção observável;
- as tentativas recusadas serem registradas na trilha de auditoria;
- as User Stories US-028, US-029, US-030 e US-031 estarem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da Feature Autenticar Usuário, criada no ciclo SDD do EPIC-006. |
