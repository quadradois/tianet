# US-040 — Autorizar Operação por Perfil

**ID:** US-040

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuário operador autenticado do Tenant

**Quero** executar apenas as operações que as Permissões do meu Perfil de Acesso permitem

**Para** que cada solicitação seja autorizada conforme o Perfil do Principal (RBAC), concedendo as operações permitidas e recusando de forma explícita e padronizada as não permitidas.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a operação solicitada for sempre confrontada com o conjunto de Permissões do Perfil do Principal autenticado, antes de qualquer efeito sobre o recurso;
- o Principal possuidor da Permissão necessária executar a operação normalmente, sem bloqueio adicional;
- o Principal autenticado, porém sem a Permissão exigida, receber HTTP 403 (Forbidden) e a operação não executar;
- o Principal sem token válido receber 401 antes de qualquer checagem de Perfil — autorização nunca precede a autenticação;
- o controle por Perfil aplicar a todos os 13 endpoints protegidos, permanecendo o `/health` público;
- a solicitação a recurso de outro Tenant responder 404, e não 403 — a negação não revela a existência do recurso (precedente da ADR-018);
- a negação de autorização ser registrada na trilha de auditoria append-only (ADR-002);
- a decisão ser tomada por Perfil de Acesso, nunca por atributo de recurso individual (RBAC).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): decisão de autorização pelo Perfil do Usuário autenticado, RBAC como modelo;
- DOMAIN-017 — Aggregate Tenant: base do isolamento, nenhuma operação cruza a fronteira de Tenant;
- DOMAIN-018 — Entity Usuario (INV-001): cada Usuário pertence exatamente a um Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant: isolamento absoluto entre Tenants (Princípios 01-03);
- FOUNDATION-009 — Capability Map (§117): autorização RBAC, perfis e permissões como modelo do contexto IAM;
- PRODUCT-001 — Capability Administrar Plataforma: o IAM é o EPIC-006;
- EPIC-006 — Discovery do IAM: caso de uso UC-027, regras de negócio e critérios transversais;
- FEATURE-012 — Autorizar Requisição: Feature de origem desta User Story.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-012 — Autorizar Requisição;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Administrar Plataforma;
- FEATURE-009 — Autenticar Usuário: a autorização pressupõe o Principal autenticado e com Tenant resolvido;
- FEATURE-011 — Gerir Perfis e Permissões: o Perfil do Principal e suas Permissões existem antes da autorização ser avaliada;
- ADR-004 — Autenticação e Autorização (IAM): contrato de erros 401/403/404 e modelo de autorização RBAC.

---

# 5. Observações Técnicas

A autorização é decidida pelo Perfil do Principal já autenticado (RBAC, FOUNDATION-009 §117), nunca por recurso individual. A avaliação ocorre depois da resolução do Principal — que carrega Usuário e Tenant autenticados — e antes de qualquer efeito sobre o recurso. O contrato de erros distingue as três negações: sem token válido (401), token válido sem Permissão (403) e recurso de outro Tenant (404), esta última sem revelar a inexistência. O mapeamento Unauthorized/Forbidden/NotFound para HTTP fica na camada Presentation, e a trilha de auditoria (ADR-002) registra o acesso negado como evento de acesso. O desenho interno de onde as Permissões do Perfil são resolvidas é definido na Fase de Domínio e no PLAN-004, sem alterar o contrato aqui fixado.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Autorizar Operação por Perfil, criada no ciclo SDD do EPIC-006. |