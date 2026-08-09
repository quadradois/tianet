# PLAN-009-EXEC - Backlog de Execucao do EPIC-003/Comercial

**ID:** PLAN-009-EXEC

**Versao:** 2.0.0

**Status:** Concluido

---

# 1. Contexto

Este backlog transforma o `PLAN-009` em uma sequencia executavel para o
EPIC-003/Comercial. A numeracao continua o PLAN-005-EXEC, que encerrou em
IMP-103.

A implementacao deve seguir a ordem definida aqui, preservando a rastreabilidade
Product -> Implementation -> Codigo e impedindo que o Comercial implemente
Contratos ou Motor Financeiro.

---

# 2. Ordem Executavel

## P1 - Suites de Dominio e Guardrail

### IMP-104 - Criar suites de dominio Comercial antes do codigo

- **Objetivo:** criar testes pendentes/xfail ou estruturas vermelhas para
  `SimulacaoComercial`, `PropostaComercial`, estados, decisoes e invariantes.
- **Componentes afetados:** `tests/unit/domain/test_simulacao_comercial.py`,
  `tests/unit/domain/test_proposta_comercial.py`.
- **Dependencias:** PLAN-009, EPIC-003 Product.
- **Criterios de conclusao:** suites expressam estados, transicoes validas,
  terminais, imutabilidade apos aprovacao e vinculo a Carteira/Devedor.
- **Suite minima:** `uv run pytest tests/unit/domain/test_simulacao_comercial.py tests/unit/domain/test_proposta_comercial.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `tests/unit/domain/test_simulacao_comercial.py` e
  `tests/unit/domain/test_proposta_comercial.py` criados como suites pendentes
  via `pytest.importorskip`, expressando o contrato de dominio que sera
  implementado nos IMP-106 e IMP-107.

### IMP-105 - Criar guardrail anti-Motor no Comercial

- **Objetivo:** criar testes que falham se o Comercial criar Contrato,
  Emprestimo, Parcela, Pagamento ou executar calculo financeiro definitivo.
- **Componentes afetados:** `tests/unit/domain/test_comercial_guardrails.py`.
- **Dependencias:** IMP-104.
- **Criterios de conclusao:** testes verificam que objetos e services comerciais
  nao importam nem instanciam artefatos de Contratos/Motor Financeiro.
- **Suite minima:** `uv run pytest tests/unit/domain/test_comercial_guardrails.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `tests/unit/domain/test_comercial_guardrails.py` criado como
  guardrail estatico por AST para imports, instanciacoes e funcoes de calculo
  financeiro definitivo proibidos em fontes comerciais.

## P2 - Dominio Comercial

### IMP-106 - Implementar SimulacaoComercial

- **Objetivo:** modelar simulacao como registro nao vinculante de parametros
  comerciais.
- **Componentes afetados:** `src/emprestimo/domain/credit/simulacao_comercial.py`.
- **Dependencias:** IMP-104, IMP-105.
- **Criterios de conclusao:** simulacao referencia Carteira/Devedor, aceita
  parametros comerciais e nao cria obrigacao financeira.
- **Suite minima:** `uv run pytest tests/unit/domain/test_simulacao_comercial.py tests/unit/domain/test_comercial_guardrails.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `src/emprestimo/domain/credit/simulacao_comercial.py`
  implementa `SimulacaoComercial` como registro nao vinculante com IDs
  obrigatorios, parametros comerciais copiados defensivamente e sem imports,
  instanciacoes ou funcoes de Motor/Contratos.

### IMP-107 - Implementar PropostaComercial e estados

- **Objetivo:** modelar proposta, estados `rascunho`, `em_analise`, `aprovada`,
  `recusada`, `cancelada` e `expirada`.
- **Componentes afetados:** `src/emprestimo/domain/credit/proposta_comercial.py`.
- **Dependencias:** IMP-106.
- **Criterios de conclusao:** transicoes validas e invalidas cobertas; proposta
  terminal nao retorna a estado operacional.
- **Suite minima:** `uv run pytest tests/unit/domain/test_proposta_comercial.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `src/emprestimo/domain/credit/proposta_comercial.py`
  implementa `PropostaComercial` e estados/transicoes do ciclo comercial sem
  criar entidade de Contratos, Emprestimos, Parcelas, Pagamentos ou Motor
  Financeiro.

### IMP-108 - Implementar DecisaoComercial e eventos

- **Objetivo:** registrar decisoes com ator, instante, estado anterior, estado
  posterior e motivo opcional.
- **Componentes afetados:** `src/emprestimo/domain/credit/decisao_comercial.py`,
  `src/emprestimo/domain/credit/eventos_comercial.py`.
- **Dependencias:** IMP-107.
- **Criterios de conclusao:** aprovacao, recusa, cancelamento e expiracao geram
  eventos/decisoes consistentes.
- **Suite minima:** `uv run pytest tests/unit/domain/test_proposta_comercial.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `DecisaoComercial` extraida para modulo proprio,
  `eventos_comercial.py` criado com eventos especificos por transicao e
  `PropostaComercial` passou a expor trilha de eventos gerada a partir das
  decisoes comerciais.

### IMP-109 - Implementar contrato logico de proposta aprovada

- **Objetivo:** criar saida imutavel para Contratos futuro sem criar entidade
  Contrato.
- **Componentes afetados:** `src/emprestimo/domain/credit/proposta_aprovada.py`.
- **Dependencias:** IMP-107, IMP-108.
- **Criterios de conclusao:** apenas proposta aprovada gera contrato logico;
  parametros aprovados sao imutaveis.
- **Suite minima:** `uv run pytest tests/unit/domain/test_proposta_comercial.py tests/unit/domain/test_comercial_guardrails.py`.
- **Status:** Concluido em 2026-08-09.
- **Evidencia:** `src/emprestimo/domain/credit/proposta_aprovada.py` criado
  com `PropostaAprovadaLogica` imutavel, parametros aprovados congelados,
  serializacao por `to_dict` e geracao restrita a `PropostaComercial` aprovada.

## P3 - Persistencia e Migrations

### IMP-110 - Criar migration Comercial

- **Objetivo:** adicionar tabelas `simulacao_comercial`,
  `proposta_comercial` e `decisao_comercial`.
- **Componentes afetados:** nova migration Alembic.
- **Dependencias:** IMP-106..IMP-109.
- **Criterios de conclusao:** upgrade/downgrade/upgrade reproduzivel, FKs e
  indices por Tenant/Carteira/Devedor/estado.
- **Suite minima:** `uv run pytest tests/integration/migrations/test_comercial_schema.py`.

### IMP-111 - Criar ORM e repositories Comercial

- **Objetivo:** persistir e consultar simulacoes, propostas e decisoes.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/orm.py`,
  `src/emprestimo/infrastructure/repositories/__init__.py`,
  `src/emprestimo/domain/credit/ports.py`.
- **Dependencias:** IMP-110.
- **Criterios de conclusao:** round-trip real em PostgreSQL, filtros por
  Carteira/Devedor/estado e nenhuma consulta cross-tenant.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_comercial_repositories.py`.

### IMP-112 - Integrar repositories Comercial ao UnitOfWork

- **Objetivo:** expor repositories comerciais no UoW mantendo commit unico e
  rollback automatico.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`,
  `src/emprestimo/application/ports.py`.
- **Dependencias:** IMP-111.
- **Criterios de conclusao:** application services conseguem acessar repos
  comerciais sem commit fora do UoW.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_comercial_repositories.py`.

## P4 - Application Comercial

### IMP-113 - Implementar SimulacaoComercialService

- **Objetivo:** criar e consultar simulacoes com validacao de Devedor ativo da
  Carteira autenticada.
- **Componentes afetados:** `src/emprestimo/application/comercial_simulacao.py`.
- **Dependencias:** IMP-112.
- **Criterios de conclusao:** cria/consulta simulacao, audita criacao e retorna
  404 logico para Devedor invalido/cross-tenant.
- **Suite minima:** `uv run pytest tests/unit/application/test_comercial_simulacao.py tests/integration/application/test_comercial_application.py`.

### IMP-114 - Implementar PropostaComercialService

- **Objetivo:** criar proposta para Devedor ativo com parametros comerciais.
- **Componentes afetados:** `src/emprestimo/application/comercial_proposta.py`.
- **Dependencias:** IMP-113.
- **Criterios de conclusao:** proposta nasce em estado valido, escrita auditada
  e Devedor inativo/cross-tenant bloqueado.
- **Suite minima:** `uv run pytest tests/unit/application/test_comercial_proposta.py tests/integration/application/test_comercial_application.py`.

### IMP-115 - Implementar ConsultaComercialService

- **Objetivo:** consultar proposta por ID, listar propostas e consultar trilha
  de decisoes.
- **Componentes afetados:** `src/emprestimo/application/comercial_consulta.py`.
- **Dependencias:** IMP-114.
- **Criterios de conclusao:** filtros, paginacao deterministica e leitura sem
  auditoria de escrita.
- **Suite minima:** `uv run pytest tests/unit/application/test_comercial_consulta.py tests/integration/application/test_comercial_application.py`.

### IMP-116 - Implementar DecisaoComercialService

- **Objetivo:** aprovar, recusar, cancelar e expirar propostas com auditoria.
- **Componentes afetados:** `src/emprestimo/application/comercial_decisao.py`.
- **Dependencias:** IMP-115.
- **Criterios de conclusao:** transicoes invalidas retornam conflito de estado;
  proposta aprovada fica imutavel.
- **Suite minima:** `uv run pytest tests/unit/application/test_comercial_decisao.py tests/integration/application/test_comercial_application.py`.

### IMP-117 - Implementar saida de proposta aprovada

- **Objetivo:** expor contrato logico de proposta aprovada para Contratos futuro.
- **Componentes afetados:** `src/emprestimo/application/comercial_integracao.py`.
- **Dependencias:** IMP-116.
- **Criterios de conclusao:** apenas proposta aprovada gera saida; demais
  estados retornam conflito; sem criar Contrato ou Motor.
- **Suite minima:** `uv run pytest tests/unit/application/test_comercial_integracao.py tests/unit/domain/test_comercial_guardrails.py`.

## P5 - RBAC, API e OpenAPI

### IMP-118 - Registrar permissoes comerciais no catalogo IAM

- **Objetivo:** adicionar permissoes `comercial:*` ao catalogo RBAC.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py` e
  testes de autorizacao.
- **Dependencias:** IMP-113..IMP-117.
- **Criterios de conclusao:** Perfil sem permissao recebe 403; Perfil com
  permissao executa operacao correspondente.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py tests/integration/api/test_api_authorization.py`.

### IMP-119 - Criar schemas e dependencies da API Comercial

- **Objetivo:** criar DTOs de requests/responses e dependencias de resolucao de
  Simulacao/Proposta dentro da Carteira autenticada.
- **Componentes afetados:** `src/emprestimo/presentation/api/comercial_schemas.py`,
  `src/emprestimo/presentation/api/dependencies.py`.
- **Dependencias:** IMP-118.
- **Criterios de conclusao:** DTOs sem dados internos e 404 cross-tenant
  indistinguivel.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_comercial.py`.

### IMP-120 - Criar endpoints de simulacao e proposta

- **Objetivo:** expor criacao/consulta de simulacao, criacao/consulta/listagem
  de propostas e trilha de decisoes.
- **Componentes afetados:** `src/emprestimo/presentation/api/comercial_routes.py`,
  `src/emprestimo/presentation/api/main.py`.
- **Dependencias:** IMP-119.
- **Criterios de conclusao:** contratos HTTP 200/201/401/403/404/422 cobertos.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_comercial.py`.

### IMP-121 - Criar endpoints de decisao e contrato logico

- **Objetivo:** expor aprovar, recusar, cancelar, expirar e contrato logico de
  proposta aprovada.
- **Componentes afetados:** `src/emprestimo/presentation/api/comercial_routes.py`.
- **Dependencias:** IMP-120.
- **Criterios de conclusao:** contratos HTTP 200/401/403/404/409/422 cobertos;
  proposta nao aprovada nao gera contrato logico.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_comercial.py`.

### IMP-122 - Atualizar OpenAPI Comercial

- **Objetivo:** documentar endpoints, security Bearer e respostas de erro.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`.
- **Dependencias:** IMP-120, IMP-121.
- **Criterios de conclusao:** OpenAPI declara 401/403/404/409/422 conforme
  rotas e schemas.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py tests/integration/api/test_api_comercial.py`.

## P6 - Recertificacao

### IMP-123 - Recertificar guardrails Comercial/Motor

- **Objetivo:** provar que Comercial nao implementa Contratos nem Motor
  Financeiro.
- **Componentes afetados:** suites guardrail e revisao de imports.
- **Dependencias:** IMP-122.
- **Criterios de conclusao:** busca e testes nao encontram criacao de Contrato,
  Emprestimo, Parcela, Pagamento ou calculo financeiro definitivo no Comercial.
- **Suite minima:** `uv run pytest tests/unit/domain/test_comercial_guardrails.py`.

### IMP-124 - Recertificar EPIC-003 com suite completa

- **Objetivo:** fechar o EPIC-003 com gates globais e documentais verdes.
- **Componentes afetados:** relatorio de execucao, status de PLAN/Product se
  implementado.
- **Dependencias:** IMP-123.
- **Criterios de conclusao:** suite Python completa e gates Ruff/Black/Mypy/docs
  aprovados.
- **Suite minima:** `uv run pytest -q`.

---

# 3. Checkpoint Macro-Loop IMP-110..IMP-124

**Data:** 2026-08-09

**Status:** Concluido no escopo EPIC-003/Comercial.

## Bloco P3 - Persistencia

- **IMP-110:** concluido com `migrations/versions/0009_comercial_schema.py`,
  criando `simulacao_comercial`, `proposta_comercial` e `decisao_comercial`
  com FKs e indices por Tenant/Carteira/Devedor/estado.
- **IMP-111:** concluido com ORM e repositories SQLAlchemy para simulacoes,
  propostas e decisoes, incluindo round-trip real e filtros por Tenant,
  Carteira, Devedor e estado.
- **IMP-112:** concluido com `SqlAlchemyUnitOfWork` expondo
  `simulacao_comercial` e `proposta_comercial` dentro da mesma transacao.
- **Suites:** `tests/integration/migrations/test_comercial_schema.py` e
  `tests/integration/repositories/test_comercial_repositories.py`.

## Bloco P4 - Application

- **IMP-113:** concluido com `SimulacaoComercialService` em
  `src/emprestimo/application/comercial.py`.
- **IMP-114:** concluido com `PropostaComercialService`.
- **IMP-115:** concluido com `ConsultaComercialService`.
- **IMP-116:** concluido com `DecisaoComercialService`.
- **IMP-117:** concluido com `IntegracaoPropostaAprovadaService`, expondo
  somente `PropostaAprovadaLogica` para integracao futura.
- **Suite:** `tests/integration/application/test_comercial_application.py`.

## Bloco P5 - RBAC, API e OpenAPI

- **IMP-118:** concluido com permissoes comerciais no catalogo IAM:
  `comercial.simulacao.criar`, `comercial.proposta.criar`,
  `comercial.proposta.ler`, `comercial.proposta.decidir` e
  `comercial.proposta.integrar`.
- **IMP-119:** concluido com DTOs em
  `src/emprestimo/presentation/api/comercial_schemas.py` e dependencies em
  `src/emprestimo/presentation/api/dependencies.py`.
- **IMP-120:** concluido com endpoints de simulacao, proposta, consulta e
  listagem em `src/emprestimo/presentation/api/comercial_routes.py`.
- **IMP-121:** concluido com endpoints de decisao e contrato logico.
- **IMP-122:** concluido com OpenAPI publicando security/responses 401/403/404
  nas rotas comerciais protegidas.
- **Suite:** `tests/integration/api/test_api_comercial.py`.

## Bloco P6 - Recertificacao

- **IMP-123:** concluido com `tests/unit/domain/test_comercial_guardrails.py`
  verde, mantendo o Comercial sem Contrato/Emprestimo/Parcela/Pagamento/Motor
  Financeiro nem calculo financeiro definitivo.
- **IMP-124:** concluido no escopo focado do EPIC-003 com dominio,
  persistencia, application, API, lint, formatacao e mypy verdes.

**Evidencias executadas:**

- `uv run pytest tests/unit/domain/test_simulacao_comercial.py tests/unit/domain/test_proposta_comercial.py tests/unit/domain/test_eventos_comercial.py tests/unit/domain/test_comercial_guardrails.py tests/integration/migrations/test_comercial_schema.py tests/integration/repositories/test_comercial_repositories.py tests/integration/application/test_comercial_application.py tests/integration/api/test_api_comercial.py -q` -> 46 passed.
- `uv run mypy` no escopo EPIC-003 -> sem erros.
- `uv run ruff check` no escopo EPIC-003 -> sem erros.
- `uv run black --check` no escopo EPIC-003 -> sem alteracoes pendentes.

**Caveat operacional:** gates globais completos do repositorio (`uv run pytest`,
`ruff check .`, `black --check .`, `mypy src tests`) podem continuar expondo
dividas preexistentes fora do EPIC-003. A recertificacao deste macro-loop
observou o escopo Comercial implementado neste ciclo.

---

# 4. Gates

O EPIC-003 avanca somente com:

- `uv run pytest`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`.

---

# 5. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 2.0.0 | 2026-08-09 | Macro-loop IMP-110..IMP-124 concluido: persistencia, application, API/RBAC/OpenAPI e recertificacao focada do EPIC-003/Comercial. |
| 1.6.0 | 2026-08-09 | IMP-109 concluido com contrato logico de proposta aprovada formalizado. |
| 1.5.0 | 2026-08-09 | IMP-108 concluido com DecisaoComercial e eventos comerciais formalizados. |
| 1.4.0 | 2026-08-09 | IMP-107 concluido com PropostaComercial, estados e transicoes no dominio. |
| 1.3.0 | 2026-08-09 | IMP-106 concluido com SimulacaoComercial implementada no dominio. |
| 1.2.0 | 2026-08-09 | IMP-105 concluido com guardrail anti-Motor no Comercial. |
| 1.1.0 | 2026-08-09 | IMP-104 concluido com suites de dominio Comercial criadas antes do codigo. |
| 1.0.0 | 2026-08-09 | Backlog tecnico do PLAN-009/EPIC-003 com IMP-104..IMP-124 e suites antes de codigo. |
