# PLAN-011-EXEC - Backlog de Execucao do EPIC-004/Contratos

**ID:** PLAN-011-EXEC

**Versao:** 1.0.0

**Status:** Concluido em 2026-08-09

---

# 1. Contexto

Este backlog transforma o `PLAN-011` em uma sequencia executavel para o
EPIC-004/Contratos. A numeracao continua o PLAN-009-EXEC, que encerrou em
IMP-124.

A implementacao deve seguir a ordem definida aqui, preservando a rastreabilidade
Product -> Implementation -> Codigo e impedindo que Contratos implemente Motor
Financeiro.

---

# 2. Ordem Executavel

## P1 - Suites de Dominio e Guardrail

### IMP-125 - Criar suites de dominio Contratos antes do codigo

- **Objetivo:** criar testes para `ContratoCredito`, estados, eventos e
  invariantes.
- **Componentes afetados:** `tests/unit/domain/test_contrato_credito.py`.
- **Dependencias:** PLAN-011, EPIC-004 Product.
- **Criterios de conclusao:** suites expressam criacao por proposta aprovada,
  snapshot, transicoes e imutabilidade.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contrato_credito.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-126 - Criar guardrail anti-Motor em Contratos

- **Objetivo:** criar testes que falham se Contratos criar Emprestimo, Parcela,
  Pagamento ou executar calculo financeiro definitivo.
- **Componentes afetados:** `tests/unit/domain/test_contratos_guardrails.py`.
- **Dependencias:** IMP-125.
- **Criterios de conclusao:** guardrail cobre imports, instanciacoes e funcoes
  financeiras proibidas no escopo de Contratos.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contratos_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

## P2 - Dominio Contratos

### IMP-127 - Implementar ContratoCredito e estados

- **Objetivo:** modelar contrato, estados `rascunho`, `formalizado`,
  `assinado`, `liberado_para_motor`, `cancelado` e `encerrado`.
- **Componentes afetados:** `src/emprestimo/domain/credit/contrato_credito.py`,
  `src/emprestimo/domain/credit/contrato_credito_state.py`.
- **Dependencias:** IMP-125, IMP-126.
- **Criterios de conclusao:** transicoes validas e invalidas cobertas; snapshot
  contratual protegido.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contrato_credito.py tests/unit/domain/test_contratos_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-128 - Implementar eventos e decisoes contratuais

- **Objetivo:** registrar eventos/decisoes com ator, instante, estado anterior,
  estado posterior e motivo opcional.
- **Componentes afetados:** `src/emprestimo/domain/credit/eventos_contrato.py`,
  `src/emprestimo/domain/credit/decisao_contrato.py`.
- **Dependencias:** IMP-127.
- **Criterios de conclusao:** criacao, assinatura, liberacao, cancelamento e
  encerramento geram trilha consistente.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contrato_credito.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-129 - Implementar saida logica de contrato liberado

- **Objetivo:** criar objeto imutavel para Motor Financeiro futuro sem criar
  Emprestimo, Parcela ou Pagamento.
- **Componentes afetados:** `src/emprestimo/domain/credit/contrato_liberado.py`.
- **Dependencias:** IMP-128.
- **Criterios de conclusao:** apenas contrato liberado gera saida logica.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contrato_credito.py tests/unit/domain/test_contratos_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

## P3 - Persistencia e Migrations

### IMP-130 - Criar migration Contratos

- **Objetivo:** adicionar tabelas `contrato_credito` e `evento_contrato`.
- **Componentes afetados:** nova migration Alembic.
- **Dependencias:** IMP-127..IMP-129.
- **Criterios de conclusao:** upgrade/downgrade/upgrade reproduzivel, FKs,
  indices e unicidade por proposta.
- **Suite minima:** `uv run pytest tests/integration/migrations/test_contratos_schema.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-131 - Criar ORM e repositories Contratos

- **Objetivo:** persistir e consultar contratos e eventos contratuais.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/orm.py`,
  `src/emprestimo/infrastructure/repositories/__init__.py`,
  `src/emprestimo/domain/credit/ports.py`.
- **Dependencias:** IMP-130.
- **Criterios de conclusao:** round-trip real, filtros por Tenant/Carteira/
  Devedor/estado e nenhuma consulta cross-tenant.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_contratos_repositories.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-132 - Integrar repositories Contratos ao UnitOfWork

- **Objetivo:** expor repositories de Contratos no UoW mantendo commit unico e
  rollback automatico.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`,
  `src/emprestimo/application/ports.py`.
- **Dependencias:** IMP-131.
- **Criterios de conclusao:** application services acessam contratos sem commit
  fora do UoW.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_contratos_repositories.py`.
- **Status:** Concluido em 2026-08-09.

## P4 - Application Contratos

### IMP-133 - Implementar FormalizacaoContratoService

- **Objetivo:** criar contrato a partir de proposta aprovada, validando Devedor
  ativo e Carteira autenticada.
- **Componentes afetados:** `src/emprestimo/application/contratos.py`.
- **Dependencias:** IMP-132.
- **Criterios de conclusao:** cria contrato, audita criacao e retorna 404
  logico para proposta/devedor invalidos ou cross-tenant.
- **Suite minima:** `uv run pytest tests/unit/application/test_contratos.py tests/integration/application/test_contratos_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-134 - Implementar ConsultaContratoService

- **Objetivo:** consultar contrato por ID, listar contratos e consultar
  historico.
- **Componentes afetados:** `src/emprestimo/application/contratos.py`.
- **Dependencias:** IMP-133.
- **Criterios de conclusao:** filtros, paginacao deterministica e leitura sem
  auditoria de escrita.
- **Suite minima:** `uv run pytest tests/unit/application/test_contratos.py tests/integration/application/test_contratos_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-135 - Implementar AssinaturaContratoService

- **Objetivo:** registrar assinatura/formalizacao com auditoria.
- **Componentes afetados:** `src/emprestimo/application/contratos.py`.
- **Dependencias:** IMP-134.
- **Criterios de conclusao:** transicoes invalidas retornam conflito de estado;
  ator e instante preservados.
- **Suite minima:** `uv run pytest tests/unit/application/test_contratos.py tests/integration/application/test_contratos_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-136 - Implementar LiberacaoContratoService

- **Objetivo:** expor saida logica de contrato liberado para Motor futuro.
- **Componentes afetados:** `src/emprestimo/application/contratos.py`.
- **Dependencias:** IMP-135.
- **Criterios de conclusao:** apenas contrato assinado/formalizado gera saida;
  sem criar Motor ou entidades financeiras.
- **Suite minima:** `uv run pytest tests/unit/application/test_contratos.py tests/unit/domain/test_contratos_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-137 - Implementar CancelamentoEncerramentoContratoService

- **Objetivo:** cancelar ou encerrar contratos conforme estado, com auditoria.
- **Componentes afetados:** `src/emprestimo/application/contratos.py`.
- **Dependencias:** IMP-136.
- **Criterios de conclusao:** transicoes invalidas retornam conflito; nenhuma
  operacao financeira e alterada.
- **Suite minima:** `uv run pytest tests/unit/application/test_contratos.py tests/integration/application/test_contratos_application.py`.
- **Status:** Concluido em 2026-08-09.

## P5 - RBAC, API e OpenAPI

### IMP-138 - Registrar permissoes contratuais no catalogo IAM

- **Objetivo:** adicionar permissoes `contratos:*` ao catalogo RBAC.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py`.
- **Dependencias:** IMP-133..IMP-137.
- **Criterios de conclusao:** perfil sem permissao recebe 403; perfil com
  permissao executa operacao correspondente.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py tests/integration/api/test_api_authorization.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-139 - Criar schemas e dependencies da API Contratos

- **Objetivo:** criar DTOs de requests/responses e dependencies de resolucao de
  Contrato dentro do Tenant autenticado.
- **Componentes afetados:** `src/emprestimo/presentation/api/contratos_schemas.py`,
  `src/emprestimo/presentation/api/dependencies.py`.
- **Dependencias:** IMP-138.
- **Criterios de conclusao:** DTOs sem dados internos e 404 cross-tenant
  indistinguivel.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_contratos.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-140 - Criar endpoints de criacao e consulta de contratos

- **Objetivo:** expor criacao, consulta por ID, listagem e historico.
- **Componentes afetados:** `src/emprestimo/presentation/api/contratos_routes.py`,
  `src/emprestimo/presentation/api/main.py`.
- **Dependencias:** IMP-139.
- **Criterios de conclusao:** contratos HTTP 200/201/400/401/403/404 cobertos.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_contratos.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-141 - Criar endpoints de assinatura, liberacao e encerramento

- **Objetivo:** expor assinar, liberar para Motor, cancelar e encerrar contrato.
- **Componentes afetados:** `src/emprestimo/presentation/api/contratos_routes.py`.
- **Dependencias:** IMP-140.
- **Criterios de conclusao:** contratos HTTP 200/400/401/403/404/409 cobertos.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_contratos.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-142 - Atualizar OpenAPI Contratos

- **Objetivo:** documentar endpoints, security Bearer e respostas de erro.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`.
- **Dependencias:** IMP-140, IMP-141.
- **Criterios de conclusao:** OpenAPI declara 400/401/403/404/409 conforme
  rotas e schemas.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py tests/integration/api/test_api_contratos.py`.
- **Status:** Concluido em 2026-08-09.

## P6 - Recertificacao

### IMP-143 - Recertificar guardrails Contratos/Motor

- **Objetivo:** provar que Contratos nao implementa Motor Financeiro.
- **Componentes afetados:** suites guardrail e revisao de imports.
- **Dependencias:** IMP-142.
- **Criterios de conclusao:** busca e testes nao encontram criacao de
  Emprestimo, Parcela, Pagamento ou calculo financeiro definitivo em Contratos.
- **Suite minima:** `uv run pytest tests/unit/domain/test_contratos_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-144 - Recertificar EPIC-004 com suite completa

- **Objetivo:** fechar o EPIC-004 com gates globais e documentais verdes.
- **Componentes afetados:** relatorio de execucao e status de PLAN/Product se
  implementado.
- **Dependencias:** IMP-143.
- **Criterios de conclusao:** suite Python completa e gates Ruff/Black/Mypy/docs
  aprovados.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido em 2026-08-09.

### IMP-145 - Revisao adversarial final do EPIC-004

- **Objetivo:** revisar diffs, contratos HTTP, OpenAPI, RBAC, auditoria,
  isolamento cross-tenant e guardrails anti-Motor antes de abrir PR.
- **Componentes afetados:** relatorio de recertificacao final.
- **Dependencias:** IMP-144.
- **Criterios de conclusao:** veredito VERIFIED ou VERIFIED WITH CAVEATS com
  evidencias e pendencias explicitas.
- **Suite minima:** gates do IMP-144 mais revisao de diff.
- **Status:** Concluido em 2026-08-09.

---

# 3. Gates

O EPIC-004 avanca somente com:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`.

---

# 4. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-09 | IMP-125..IMP-145 concluidos com suites de dominio, guardrails, persistencia, aplicacao, API/RBAC/OpenAPI e recertificacao global. |
| 1.0.0 | 2026-08-09 | Backlog tecnico do PLAN-011/EPIC-004 com IMP-125..IMP-145 e suites antes de codigo. |
