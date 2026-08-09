# PLAN-005 - Plano Tecnico do EPIC-006/IAM

**ID:** PLAN-005

**Versao:** 1.4.0

**Status:** Concluido

---

# 1. Objetivo

Implementar o EPIC-006/IAM no Platform Context, seguindo ADR-004, para que o
backend deixe de depender de acesso anonimo aos endpoints de negocio.

O escopo cobre credenciais, autenticacao, refresh token, perfis, permissoes,
resolucao de Principal, autorizacao RBAC e bloqueio cross-tenant.

---

# 2. Referencias

- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`;
- `docs/product/platform/epics/EPIC-006-iam.md`;
- `docs/product/platform/features/FEATURE-009-autenticar-usuario.md`;
- `docs/product/platform/features/FEATURE-010-gerir-credenciais.md`;
- `docs/product/platform/features/FEATURE-011-gerir-perfis-e-permissoes.md`;
- `docs/product/platform/features/FEATURE-012-autorizar-requisicao.md`;
- `docs/product/platform/user-stories/US-028-autenticar-com-credencial.md`;
- `docs/product/platform/user-stories/US-029-renovar-token-de-acesso.md`;
- `docs/product/platform/user-stories/US-030-encerrar-sessao.md`;
- `docs/product/platform/user-stories/US-031-recusar-autenticacao-invalida.md`;
- `docs/product/platform/user-stories/US-032-definir-credencial-inicial.md`;
- `docs/product/platform/user-stories/US-033-alterar-a-propria-credencial.md`;
- `docs/product/platform/user-stories/US-034-redefinir-credencial-de-usuario.md`;
- `docs/product/platform/user-stories/US-035-criar-e-manter-perfis-de-acesso.md`;
- `docs/product/platform/user-stories/US-036-associar-permissoes-a-perfil.md`;
- `docs/product/platform/user-stories/US-037-atribuir-perfil-a-usuario.md`;
- `docs/product/platform/user-stories/US-038-consultar-permissoes-efetivas.md`;
- `docs/product/platform/user-stories/US-039-validar-token-e-resolver-principal.md`;
- `docs/product/platform/user-stories/US-040-autorizar-operacao-por-perfil.md`;
- `docs/product/platform/user-stories/US-041-barrar-acesso-cross-tenant.md`;
- `docs/product/platform/user-stories/US-042-auditar-eventos-de-acesso.md`.

---

# 3. Ordem de Implementacao

## Fase 1 - Dominio IAM

Criar entidades e value objects antes da API:

- `Credencial`: hash, algoritmo, validade logica e troca sem texto legivel;
- `Sessao`: refresh token persistido, expiravel e revogavel;
- `PerfilAcesso`: nome unico por Tenant, estado ativo/inativo e permissoes;
- `Permissao`: catalogo de operacoes autorizaveis;
- `Principal`: Usuario, Tenant e Perfil resolvidos a partir do token.

Suites:

- `tests/unit/domain/test_credencial.py`;
- `tests/unit/domain/test_sessao.py`;
- `tests/unit/domain/test_perfil.py`;
- `tests/unit/domain/test_permissao.py`.

## Fase 2 - Persistencia e Migrations

Criar migrations aditivas apos os testes de dominio:

- tabela de credenciais por Usuario;
- tabela de sessoes/refresh tokens;
- tabela de perfis por Tenant;
- tabela de permissoes;
- associacao perfil-permissao;
- associacao Usuario-perfil, substituindo o uso operacional de `perfil_acesso`
  como string simples.

Suite:

- `tests/integration/migrations/test_iam_schema.py`.

## Fase 3 - Casos de Uso

Implementar em Application:

- definir credencial inicial e ativar Usuario convidado;
- alterar propria credencial;
- redefinir credencial de outro Usuario do mesmo Tenant;
- autenticar com e-mail e credencial;
- renovar access token por refresh token;
- encerrar sessao revogando refresh token;
- consultar permissoes efetivas.

Suites:

- `tests/unit/application/test_credenciais.py`;
- `tests/unit/application/test_autenticacao.py`;
- `tests/unit/application/test_autorizacao.py`;
- `tests/integration/application/test_autenticacao_integration.py`;
- `tests/integration/repositories/test_iam_repositories.py`.

## Fase 4 - Presentation/API

Criar endpoints publicos apenas para autenticacao e manter `/health` publico.
Todos os demais endpoints de Platform e Credit passam a exigir Principal.

Contratos minimos:

- 200 para login, refresh e logout validos;
- 401 uniforme para credencial invalida, Usuario inexistente, Usuario nao ativo,
  token ausente, token malformado, assinatura invalida ou expirado;
- 403 para Principal autenticado sem permissao;
- 404 para recurso de outro Tenant.

Suites:

- `tests/integration/api/test_api_auth.py`;
- `tests/integration/api/test_api_authorization.py`;
- `tests/integration/api/test_api_protected_endpoints.py`;
- isolamento cross-tenant consolidado em
  `tests/integration/api/test_api_authorization.py`.

## Fase 5 - Retrofit dos Endpoints Existentes

Aplicar dependencias de autenticacao/autorizacao em:

- endpoints de Tenant;
- endpoints de Carteira;
- endpoints de Devedor;
- consultas de historico;
- transicoes de estado.

`/health` permanece sem token.

---

# 4. API

Endpoints publicos de autenticacao (IMP-090):

- `POST /auth/login` - autentica Usuario ativo por e-mail e credencial; responde
  200 com access token, refresh token, `usuario_id`, `tenant_id` e expiracoes.
- `POST /auth/refresh` - renova access token mediante refresh token valido;
  responde 200 com novo access token, `usuario_id`, `tenant_id` e expiracao.
- `POST /auth/logout` - encerra sessao revogando refresh token; responde 200
  quando o refresh token e valido, inclusive se a sessao ja estiver encerrada.
- `POST /auth/ativar` - define a credencial inicial mediante token descartavel,
  persistido somente por hash e invalidado no primeiro uso.

Endpoints IAM protegidos (IMP-094..IMP-097):

- `PATCH /iam/credencial` - altera a propria credencial;
- `POST /iam/usuarios/{usuario_id}/credencial/redefinir` - redefine credencial;
- `POST /iam/perfis` - cria Perfil;
- `GET /iam/perfis` - lista Perfis;
- `GET /iam/perfis/{perfil_id}` - consulta Perfil;
- `PATCH /iam/perfis/{perfil_id}` - renomeia Perfil;
- `POST /iam/perfis/{perfil_id}/inativar` - inativa Perfil sem Usuario vinculado;
- `PUT /iam/perfis/{perfil_id}/permissoes/{codigo}` - associa Permissao;
- `DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}` - remove Permissao;
- `PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}` - atribui Perfil;
- `DELETE /iam/usuarios/{usuario_id}/perfil` - remove atribuicao;
- `GET /iam/usuarios/{usuario_id}/permissoes` - consulta Permissoes efetivas.

Contratos de erro:

- 401 uniforme para credencial invalida, Usuario inexistente, Usuario nao ativo,
  payload de autenticacao invalido, refresh token malformado, expirado ou revogado;
- 403 para Principal autenticado sem permissao (IMP-092);
- 404 para recurso de outro Tenant (IMP-092).

`/health` permanece publico. A protecao dos demais endpoints pertence ao IMP-091.

---

# 5. Decisoes Tecnicas

- O access token e curto, autocontido e valido por 15 minutos.
- O refresh token e persistido, revogavel e valido por 7 dias.
- A credencial nunca e persistida, retornada ou auditada em texto legivel.
- A autorizacao e RBAC por Perfil e Permissao de operacao.
- A resolucao de Tenant vem do Principal autenticado, nao do payload.
- A verificacao cross-tenant deve retornar 404 para nao criar oraculo de
  existencia.
- Eventos de acesso negado sao auditados sem registrar segredo.

---

# 6. Gates de Aceite

O EPIC-006 so pode ser considerado pronto quando:

- `uv run pytest` passar;
- `uv run ruff check .` passar;
- `uv run black --check .` passar;
- `uv run mypy src tests` passar;
- `npm run docs:validate` passar com 0 erros;
- `npm run docs:test` passar;
- endpoint protegido sem token responder 401;
- token valido sem permissao responder 403;
- recurso de outro Tenant responder 404;
- `/health` responder sem token;
- nenhum teste, fixture, auditoria ou banco armazenar credencial em texto legivel.

---

# 7. Fora de Escopo

- Recuperacao de credencial por e-mail;
- MFA;
- SSO/OIDC externo;
- ABAC;
- revogacao instantanea de access token antes dos 15 minutos.

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.4.0 | 2026-08-09 | EPIC-006/IAM fechado formalmente apos IMP-102, com suite Python completa, Ruff, Black, Mypy e validadores documentais verdes. |
| 1.3.0 | 2026-08-09 | Corrige lacunas da segunda auditoria: ativacao segura, FEATURE-010/011 operacional, usuario_perfil e auditoria integrada. |
| 1.2.0 | 2026-08-09 | EPIC-006/IAM recertificado no IMP-093; suites consolidadas registradas. |
| 1.1.0 | 2026-08-08 | Contrato API do IMP-090 formalizado para login, refresh e logout. |
| 1.0.0 | 2026-08-08 | Plano tecnico detalhado do EPIC-006/IAM apos recertificacao P0-P2. |
