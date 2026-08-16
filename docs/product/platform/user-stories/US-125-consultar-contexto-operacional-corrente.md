# US-125 — Consultar Contexto Operacional Corrente

**ID:** US-125

**Versão:** 1.1.0

**Status:** Concluido

---

# 1. História

**Como** Usuario autenticado

**Quero** consultar meu contexto operacional corrente com Usuario, Tenant,
Carteira padrao, Perfil e Permissoes efetivas

**Para** operar apenas no escopo e nas jornadas que o backend autorizou, sem
escolher ou inferir identificadores de outro contexto.

---

# 2. Critérios de Aceitação

A User Story sera considerada concluida quando:

- a consulta identificar o proprio Principal pelo access token, sem aceitar
  `usuario_id`, `tenant_id` ou `carteira_id` arbitrarios na requisicao;
- a resposta contiver Usuario, Tenant, Carteira padrao, Perfil vigente e a
  lista corrente de Permissoes efetivas;
- a Carteira retornada pertencer ao Tenant do Principal e for a Carteira padrao
  criada pelo provisionamento governado;
- Usuario sem Perfil retornar Perfil nulo e lista de Permissoes vazia, sem
  conceder acesso implicito;
- contexto sem Carteira padrao responder `409` com erro operacional seguro, em
  vez de o cliente eleger ou fabricar uma Carteira;
- access token ausente, invalido, expirado ou de Usuario inativo responder
  `401` uniforme;
- a operacao nao exigir uma Permissao administrativa adicional, pois consulta
  somente o contexto do proprio Principal autenticado;
- a consulta for somente leitura e nao gerar trilha de auditoria de mutacao;
- nenhum dado de outro Tenant ou Carteira for revelado, inclusive por mensagens
  de erro;
- o frontend usar essa resposta como fonte unica do contexto operacional e nao
  persistir access ou refresh token em JavaScript do navegador.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-012 - Autorizar Requisicao;
- EPIC-006 - IAM;
- PRODUCT-001 - Administrar Plataforma;
- US-004 - Criar Carteira Padrao;
- US-039 - Validar Token e Resolver Principal;
- US-040 - Autorizar Operacao por Perfil;
- US-041 - Barrar Acesso Cross-Tenant;
- ADR-004 - Autenticacao e Autorizacao;
- FOUNDATION-006 - Arquitetura Multi-Tenant;
- FOUNDATION-009 - RBAC.

---

# 4. Dependências

- Tenant, Usuario e Carteira padrao provisionados por EPIC-001;
- Principal e Perfil correntes resolvidos por FEATURE-012;
- Permissoes derivadas do Perfil conforme FEATURE-011;
- contrato OpenAPI aditivo aprovado antes da implementacao frontend.

---

# 5. Observações Técnicas

O contrato certificado e `GET /iam/contexto-atual`, autenticado por BearerAuth
e sem permissao RBAC administrativa adicional. `ContextoOperacionalResponse`
contem `usuario`, `tenant`, `carteira_padrao`, `perfil` anulavel e
`permissoes`. O backend deriva todos esses dados exclusivamente do Principal,
exige exatamente uma Carteira do Tenant e responde 409 seguro quando o
contexto estiver incompleto.

Esta Story nao autoriza selecao multi-Carteira, troca de Tenant, elevacao de
privilegio nem qualquer calculo financeiro no frontend.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-08-12 | Contrato implementado e recertificado no hardening do PLAN-025. |
| 1.0.0 | 2026-08-12 | Delta Product para bootstrap seguro do contexto operacional corrente. |
