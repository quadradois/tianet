# US-041 — Barrar Acesso Cross-Tenant

**ID:** US-041

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Sistema (camada de autorização)

**Quero** barrar todo acesso a recurso de outro Tenant, respondendo 404 e não 403

**Para** garantir o isolamento absoluto entre Tenants (FOUNDATION-006) sem revelar a existência de recursos alheios — seguindo o precedente da ADR-018 para a pertinência Carteira/Devedor, em que "recurso de outro Tenant" e "recurso inexistente" são indistinguíveis para quem pergunta.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- toda requisição a recurso pertencente a outro Tenant responder 404, e não 403, em qualquer endpoint protegido;
- a resposta a recurso de outro Tenant for idêntica, em código e corpo, à resposta de recurso inexistente — sem indicar se o recurso existe ou pertence a outra organização;
- a verificação de pertinência do recurso ao Tenant for centralizada — resolvida uma única vez a partir do Principal autenticado — e aplicada a todos os endpoints protegidos, sem duplicação por handler;
- o Tenant do recurso, quando não estiver no caminho da URL (ex.: `devedor_id` informado em corpo), for resolvido a partir do recurso persistido e comparado ao Tenant do Principal antes de qualquer ação;
- Usuário autenticado acessando recurso do próprio Tenant sem permissão para a operação responder 403 — o 404 cross-tenant não substitui o 403 por falta de permissão dentro do Tenant;
- requisição sem token válido continuar respondendo 401, e o recurso de outro Tenant permanecer respondendo 404 mesmo quando o acesso ocorre dentro da janela de 15 minutos de validade do token;
- o acesso negado por violação de fronteira de Tenant ser registrado na trilha de auditoria append-only (ADR-002), sem expor na resposta qualquer detalhe do recurso alvo;
- `/health` permanecer acessível sem token e sem verificação de pertinência.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): recurso de outro Tenant responde 404, não 403; o Tenant vem do token e é verificado, não presumido;
- ADR-018 — Identidade Externa do Devedor (precedente de não revelar existência e de verificação centralizada de pertinência);
- DOMAIN-017 — Aggregate Tenant (todo recurso de negócio pertence a exatamente um Tenant);
- DOMAIN-018 — Entity Usuario (INV-001: Usuário pertence a exatamente um Tenant e só acessa recursos desse Tenant);
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03: isolamento absoluto entre Tenants);
- PRODUCT-001 — Capability Administrar Plataforma (o IAM é o EPIC-006);
- EPIC-006 — Discovery IAM (UC-028 Resolver o Tenant do Principal e barrar acesso cruzado; critério de aceitação transversal);
- FEATURE-012 — Autorizar Requisição.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-012 — Autorizar Requisição;
- US-039 — Validar Token e Resolver Principal (o Principal, com Usuário e Tenant, é a base da verificação de pertinência);
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM);
- ADR-018 — Identidade Externa do Devedor (precedente de pertinência Carteira/Devedor).

---

# 5. Observações Técnicas

A verificação de pertinência usa o Tenant do Principal como referência e resolve o recurso na base antes da operação. A ADR-018 concentra as rotas por `devedor_id` em uma dependência comum. Existência e pertinência são verificadas antes da permissão, garantindo que o 404 cross-tenant prevaleça sobre o 403 e não crie oráculo de existência. O Tenant corrente do Principal e o Tenant do recurso são comparados em cada requisição.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Barrar Acesso Cross-Tenant. |
