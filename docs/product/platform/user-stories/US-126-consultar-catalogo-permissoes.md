# US-126 — Consultar Catalogo de Permissoes

**ID:** US-126

**Versão:** 1.1.0

**Status:** Concluido

---

# 1. História

**Como** Administrador do Tenant autorizado a consultar Perfis

**Quero** consultar o catalogo canonico e versionado de Permissoes

**Para** associar apenas codigos reconhecidos pelo backend aos Perfis do meu
Tenant, sem manter uma lista paralela na interface.

---

# 2. Critérios de Aceitação

A User Story sera considerada concluida quando:

- a consulta retornar todos os codigos de Permissao suportados pelo backend,
  com descricao segura, grupo funcional e versao do catalogo;
- cada codigo retornado corresponder ao mesmo catalogo usado pela autorizacao
  runtime e pela validacao de associacao a Perfil;
- o catalogo for somente leitura e nao aceitar criacao, renomeacao ou exclusao
  de codigos pela interface;
- a operacao exigir autenticacao e `perfil.ler`;
- ausencia de token responder `401` e ausencia de `perfil.ler` responder `403`;
- a resposta nao expuser Perfis, Usuarios ou dados de outro Tenant;
- o frontend nunca embutir uma lista canonica independente nem enviar codigo
  que nao veio do contrato vigente;
- mudanca incompatível no catalogo exigir nova versao e teste de contrato antes
  de chegar ao cliente tipado.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-011 - Gerir Perfis e Permissoes;
- EPIC-006 - IAM;
- PRODUCT-001 - Administrar Plataforma;
- US-035 - Criar e Manter Perfis de Acesso;
- US-036 - Associar Permissoes a Perfil;
- US-038 - Consultar Permissoes Efetivas;
- ADR-004 - Autenticacao e Autorizacao;
- FOUNDATION-009 - RBAC.

---

# 4. Dependências

- catalogo canonico do backend e validacao de codigos existentes;
- autorizacao `perfil.ler` da FEATURE-012;
- contrato OpenAPI aditivo aprovado antes da interface IAM P1.

---

# 5. Observações Técnicas

O contrato certificado e `GET /iam/permissoes`, protegido por BearerAuth e
`perfil.ler`. `PermissoesCatalogoResponse` publica a versao `1.0.0` e os 55
itens canonicos com `codigo`, `descricao` e `grupo`, ordenados por codigo. A
fonte e `CATALOGO_PERMISSOES`, a mesma usada por bootstrap e validacao runtime;
o endpoint nao introduz configuracao de Permissao por Tenant.

Esta Story nao amplia o ciclo de vida de Usuarios. Listagem, convite,
inativacao, reativacao ou remocao de Usuarios continuam fora do recorte ate
existir decisao Product e contrato backend proprios.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-08-12 | Contrato implementado e recertificado no hardening do PLAN-025. |
| 1.0.0 | 2026-08-12 | Delta Product para expor o catalogo IAM canonico a administracao autorizada. |
