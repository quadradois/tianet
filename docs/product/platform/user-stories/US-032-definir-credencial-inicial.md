# US-032 — Definir Credencial Inicial

**ID:** US-032

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuário do Tenant recém-criado, em estado Convidado

**Quero** definir minha credencial inicial

**Para** transicionar meu acesso de Convidado para Ativo e, a partir daí, poder me autenticar na plataforma e operar conforme meu Perfil.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a definição da credencial inicial somente for aceita para Usuário em estado Convidado;
- a definição da credencial inicial transicionar o Usuário de Convidado para Ativo, sendo esse o único evento de ativação;
- a credencial for armazenada de forma que nunca possa ser reproduzida, permanecendo irreversível e nunca legível;
- a operação de definição de credencial não devolver a credencial nem seu valor derivado em nenhuma resposta;
- Usuário inexistente responder 404, sem distinguir entre inexistência e não localização;
- Credencial inicial para Usuário em estado Ativo, Inativo ou Removido responder 409 (estado divergente);
- não houver qualquer ação de definição de credencial sobre Usuário de outro Tenant — recurso de outro Tenant responder 404, jamais revelando a existência;
- a definição da credencial inicial for registrada para auditoria na trilha append-only.

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): credencial nunca armazenada em texto legível; RBAC; IAM no Platform Context;
- DOMAIN-018 — Entity Usuário (RN-001, RN-002, INV-001, INV-002, INV-003) e o ciclo de vida Convidado → Ativo → Inativo → Removido;
- DOMAIN-017 — Aggregate Tenant: Usuário obrigatoriamente vinculado a um único Tenant (INV-001);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03): nenhum acesso cruza a fronteira de Tenant;
- ADR-002 — Auditoria Independente da Transação (INV-003 de DOMAIN-018);
- ADR-018 — precedente de não revelar existência de recurso de outro Tenant (404);
- FEATURE-010 — Gerir Credenciais (User Story US-032);
- EPIC-006 — IAM (o ciclo de ativação hoje não executado fora do provisionamento);
- PRODUCT-001 — Capability Administrar Plataforma.

# 4. Dependências

- FEATURE-010 — Gerir Credenciais;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM).

# 5. Observações Técnicas

O Usuário Convidado não pode se autenticar — apenas o estado Ativo autentica, conforme o ciclo de vida de DOMAIN-018 —, portanto a definição da credencial inicial ocorre por fluxo que não depende da autenticação do próprio Usuário; o formato desse fluxo é decisão da Fase de Domínio, dentro do Platform Context (ADR-004). A credencial é tratada como dado de segurança de ponta a ponta: capturada uma única vez na definição e apenas no sentido de escrita — nunca lida, reproduzida ou devolvida em resposta. A operação executa em transação única, com auditoria append-only (ADR-002), e respeita a fronteira de Tenant (FOUNDATION-006, RN-003 de DOMAIN-018).

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Definir Credencial Inicial, criada no ciclo SDD do EPIC-006. |