# US-038 — Consultar Permissões Efetivas

**ID:** US-038

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Administrador do Tenant

**Quero** consultar quais Permissões um Usuário efetivamente possui

**Para** conferir se o acesso concedido corresponde ao que se pretendia antes de descobrir a diferença por um erro em produção.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a consulta retornar as Permissões que o Usuário possui por meio do Perfil atribuído;
- a consulta refletir o estado vigente, incluindo alterações recentes de Perfil ou de Permissões;
- Usuário sem Perfil atribuído retornar lista vazia, e não erro;
- a consulta a Usuário de outro Tenant responder 404, sem revelar sua existência;
- a operação ser exclusivamente de leitura e **não** gerar registro na trilha de auditoria, conforme ADR-002 — somente escrita é auditada;
- a consulta exigir autenticação e a Permissão correspondente.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FOUNDATION-009 — Capability Map: autorização por RBAC, com Permissões derivadas do Perfil;
- ADR-002 — Auditoria Independente da Transação: consultas não geram trilha;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-018 — Identidade Externa do Aggregate Devedor: precedente de responder 404, e não 403, para recurso de outra fronteira;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- DOMAIN-018 — Entity Usuario;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- FEATURE-011 — Gerir Perfis e Permissões.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-011 — Gerir Perfis e Permissões;
- US-035 — Criar e Manter Perfis de Acesso;
- US-036 — Associar Permissões a Perfil;
- US-037 — Atribuir Perfil a Usuário;
- EPIC-006 — IAM (Identidade e Controle de Acesso).

---

# 5. Observações Técnicas

As Permissões não são atribuídas diretamente ao Usuário: derivam do Perfil, como
determina o modelo RBAC. "Efetivas" descreve o resultado dessa derivação no
momento da consulta, não um conjunto armazenado separadamente.

O 404 para Usuário de outro Tenant segue o precedente estabelecido na ADR-018
para a pertinência entre Carteira e Devedor: um código distinto confirmaria a
existência do identificador em outra organização.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Consultar Permissões Efetivas. |
