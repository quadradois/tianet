# PLAN-010 - Relatorio de Recertificacao PLAN-009/EPIC-003 - 2026-08-09

**ID:** PLAN-010

**Plano recertificado:** PLAN-009

**Versao:** 1.0.0

**Status:** Concluido com caveats operacionais

## Resultado

O EPIC-003/Comercial foi implementado e recertificado em 2026-08-09 apos o
macro-loop IMP-104..IMP-124 e uma revisao adversarial final pos-correcao. O
backend passou a cobrir simulacoes comerciais nao vinculantes, propostas
comerciais, estados e decisoes, persistencia, repositories, UnitOfWork, API
protegida por RBAC, contrato logico de proposta aprovada para o contexto de
Contratos futuro e guardrails para impedir calculo financeiro definitivo no
Comercial.

A rodada adversarial final encontrou tres lacunas e elas foram corrigidas:
criacao de simulacao/proposta agora rejeita Devedor inativo, transicoes
comerciais invalidas retornam 409 `conflito_estado`, e a consulta de Simulacao
Comercial por ID foi exposta na API e documentada no OpenAPI/PLAN.

## Escopo Recertificado

| IMP | Resultado | Evidencia principal |
|-----|-----------|---------------------|
| IMP-104 | Suites de dominio Comercial criadas | `tests/unit/domain/test_simulacao_comercial.py`, `tests/unit/domain/test_proposta_comercial.py` |
| IMP-105 | Guardrail anti-Motor criado | `tests/unit/domain/test_comercial_guardrails.py` |
| IMP-106 | `SimulacaoComercial` implementada | `src/emprestimo/domain/credit/simulacao_comercial.py` |
| IMP-107 | `PropostaComercial` e estados implementados | `src/emprestimo/domain/credit/proposta_comercial.py`, `proposta_comercial_state.py` |
| IMP-108 | Decisoes/eventos comerciais implementados | `decisao_comercial.py`, `eventos_comercial.py` |
| IMP-109 | Contrato logico de proposta aprovada implementado | `proposta_aprovada.py` |
| IMP-110 | Migration Comercial criada | `migrations/versions/0009_comercial_schema.py` |
| IMP-111 | ORM/repositories Comercial criados | `src/emprestimo/infrastructure/repositories/__init__.py` |
| IMP-112 | UnitOfWork Comercial integrado | `src/emprestimo/infrastructure/unit_of_work.py` |
| IMP-113 | Service de Simulacao Comercial concluido | `src/emprestimo/application/comercial.py` |
| IMP-114 | Service de Proposta Comercial concluido | `src/emprestimo/application/comercial.py` |
| IMP-115 | Consulta Comercial concluida | `src/emprestimo/application/comercial.py` |
| IMP-116 | Decisao Comercial concluida | `src/emprestimo/application/comercial.py` |
| IMP-117 | Integracao de proposta aprovada concluida | `src/emprestimo/application/comercial.py` |
| IMP-118 | Permissoes Comerciais integradas ao RBAC | `src/emprestimo/application/iam_catalogo.py` |
| IMP-119 | Schemas/dependencies API Comercial concluidos | `comercial_schemas.py`, `dependencies.py` |
| IMP-120 | Endpoints de simulacao/proposta concluidos | `src/emprestimo/presentation/api/comercial_routes.py` |
| IMP-121 | Endpoints de decisao/contrato logico concluidos | `src/emprestimo/presentation/api/comercial_routes.py` |
| IMP-122 | OpenAPI Comercial recertificado | `tests/integration/api/test_api_comercial.py`, `test_api_protected_endpoints.py` |
| IMP-123 | Guardrails Comercial/Motor recertificados | `tests/unit/domain/test_comercial_guardrails.py` |
| IMP-124 | Recertificacao completa concluida | este relatorio e gates abaixo |

## Correcoes Pos-Revisao Adversarial

| Achado | Correcao | Evidencia |
|--------|----------|-----------|
| Devedor inativo ainda originava operacao Comercial | `_validar_contexto` passou a exigir `DevedorState.ATIVO` | `test_servicos_comerciais_rejeitam_devedor_inativo`, `test_api_comercial_rejeita_devedor_inativo` |
| Transicao Comercial invalida retornava 422 | `DecisaoComercialService` traduz `ViolacaoInvarianteError` para `TransicaoEstadoInvalidaError` | `test_decisao_comercial_traduz_transicao_invalida_para_conflito`, `test_api_comercial_transicao_invalida_retorna_409` |
| US-044 nao estava exposta na API | Adicionado `GET /credit/simulacoes-comerciais/{simulacao_id}` | `test_api_comercial_consulta_simulacao_por_id`, OpenAPI e PLAN-009 |

## Matriz de Aceite

| Contrato | Estado | Evidencia |
|----------|--------|-----------|
| Simulacao Comercial nao vinculante | Aprovado | dominio, application, repositories e API |
| Proposta Comercial com estados | Aprovado | testes de dominio e application |
| Decisoes registram transicao e ator | Aprovado | testes de dominio e API |
| Proposta aprovada gera saida logica | Aprovado | `IntegracaoPropostaAprovadaService` e API |
| Devedor inativo bloqueado | Aprovado | regressao pos-revisao adversarial |
| Cross-tenant responde 404 | Aprovado | application/API e contratos protegidos |
| RBAC Comercial responde 403 sem permissao | Aprovado | `test_api_comercial_exige_permissao` |
| OpenAPI declara 401/403/404/409 | Aprovado | `test_openapi_declara_contratos_de_erro_iam_autorizacao` |
| Comercial nao executa Motor Financeiro | Aprovado | guardrail AST anti-Motor |

## Gates Observados

- `uv run pytest -q`: passou na suite completa; permanece um warning externo
  de deprecacao do `fastapi.testclient`/Starlette.
- `uv run ruff check .`: passou.
- `uv run black --check .`: passou, 140 arquivos sem alteracao.
- `uv run mypy src tests`: passou, 129 source files sem issues.
- `npm run docs:validate`: 161 verificacoes OK, 40 avisos, 0 erros.
- `npm run docs:test`: 42/42 testes documentais passaram.
- Suite focada pos-correcao:
  `uv run pytest tests/integration/application/test_comercial_application.py tests/integration/api/test_api_comercial.py tests/integration/api/test_api_protected_endpoints.py::test_openapi_declara_contratos_de_erro_iam_autorizacao tests/unit/domain/test_comercial_guardrails.py -q`
  passou com 17 testes.

## Caveats

- O worktree segue com muitas mudancas acumuladas e varios arquivos ainda
  `untracked`; esta recertificacao registra o estado observado por execucao de
  gates, nao uma atribuicao limpa de autoria por diff.
- O validador documental segue com 40 avisos historicos de referencias futuras,
  buracos de numeracao e namespaces legados, mas com 0 erros.
- A suite Python segue com um warning externo de deprecacao do
  `fastapi.testclient`/Starlette.
- O EPIC-003 entrega somente proposta aprovada como contrato logico. Criacao de
  Contrato, Emprestimo, parcelas, pagamentos e calculo financeiro definitivo
  permanecem fora do escopo.

## Veredito

**VERIFIED WITH CAVEATS.**

O EPIC-003/Comercial esta pronto para ser considerado encerrado no backend, com
as ressalvas operacionais acima. O proximo ciclo deve escolher entre Contratos,
Motor Financeiro/Emprestimos ou uma etapa de consolidacao de worktree/PR antes
de abrir novo escopo funcional.

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Fecha IMP-124 com recertificacao adversarial final do EPIC-003/Comercial e registro das correcoes pos-auditoria. |
