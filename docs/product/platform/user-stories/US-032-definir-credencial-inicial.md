# US-032 — Definir Credencial Inicial

**ID:** US-032

**Versão:** 1.1.0

**Status:** Concluido

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
- a ativação exigir token aleatório de uso único, expirável e persistido somente por hash;
- token desconhecido, expirado, já utilizado, pertencente a Usuário inexistente ou em estado divergente responder 401 uniforme, sem revelar qual condição ocorreu;
- não houver qualquer ação de definição de credencial sobre Usuário de outro Tenant;
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

O Usuário Convidado não pode se autenticar — apenas o estado Ativo autentica, conforme o ciclo de vida de DOMAIN-018 —, portanto a definição da credencial inicial usa um token descartável entregue somente no provisionamento inicial. Apenas o hash SHA-256 do segredo aleatório é persistido; o consumo é serializado na transação e a resposta nunca devolve a credencial nem material derivado dela. Falhas do token usam resposta 401 uniforme para impedir enumeração. A auditoria append-only usa sessão independente conforme ADR-002.

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 09/08/2026 | Formaliza token de ativação descartável, consumo atômico e falha 401 uniforme. |
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Definir Credencial Inicial, criada no ciclo SDD do EPIC-006. |
