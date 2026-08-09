# US-033 — Alterar a Própria Credencial

**ID:** US-033

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Usuário autenticado do Tenant

**Quero** alterar a minha própria credencial, apresentando a credencial vigente

**Para** manter o controle exclusivo sobre o meu acesso e garantir que sessões
anteriores sejam reavaliadas quando a credencial mudar.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o Usuário autenticado puder alterar a própria credencial informando a
  credencial atual vigente e a nova credencial, e a alteração for recusada sem a
  credencial atual;

- a credencial atual informada incorreta recusar a alteração com 401, sem
  distinguir a falha entre identificador e credencial e sem revelar a existência
  de credencial de outros Usuários;

- a nova credencial inválida for rejeitada com 422 (violação de regra de
  domínio) e a credencial anterior permanecer vigente;

- após a alteração, todos os refresh tokens existentes do Usuário serem
  revogados, de modo que as sessões ativas sejam reavaliadas e a renovação do
  acesso por sessão anterior seja recusada;

- o token de acesso emitido antes da alteração permanecer válido apenas até a
  expiração natural de até 15 minutos, conforme a janela de revogação da
  ADR-004;

- a nova credencial autenticar o Usuário em um novo login a partir de então;

- a credencial não ser armazenada, retornada em resposta ou registrada na trilha
  de auditoria em texto legível, e não poder ser recuperada — apenas redefinida;

- a alteração ser registrada na trilha append-only (ADR-002) e o estado do
  Usuário permanecer inalterado (a alteração da própria credencial não
  transita o estado).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM) — janela de revogação de até 15
  minutos, refresh token revogável;
- ADR-002 — Auditoria Independente da Transação (eventos de acesso na trilha
  append-only);
- DOMAIN-017 — Aggregate Tenant (a fronteira do Tenant é absoluta);
- DOMAIN-018 — Entity Usuario (RN-001, INV-001, INV-002, INV-003 — credencial
  pertence ao Usuário, Usuário pertence a exatamente um Tenant);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03, isolamento);
- FOUNDATION-008 — MVP Scope (Usuários, Autenticação);
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- FEATURE-010 — Gerir Credenciais.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-010 — Gerir Credenciais;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-001 — Stack oficial (JWT Bearer + Refresh Token);
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario;
- FEATURE-009 — Autenticar Usuário (o Usuário só altera a credencial já
  autenticado, com refresh revogável disponível).

---

# 5. Observações Técnicas

A alteração da própria credencial é exclusiva do Usuário autenticado (nunca de
outro Usuário) e exige a apresentação da credencial vigente — a verificação
da credencial atual é reautenticação e, em falha, não diferencia a causa. Após a
alteração, os refresh tokens do Usuário são revogados; o token de acesso
corrente segue válido até a expiração natural, de até 15 minutos pela ADR-004,
que é a janela de revogação.

A credencial nova só é armazenada por hash (nunca em texto legível) e não é
recuperável, apenas redefinível. A operação registra na trilha append-only
(ADR-002) e não altera o estado do Usuário. Idempotência e contrato de erro
seguem o padrão dos casos de uso de escrita (401/403/404 e 422), sem revelar
existência de Usuários, em linha com as decisões da ADR-004.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Alterar a Própria Credencial. |
