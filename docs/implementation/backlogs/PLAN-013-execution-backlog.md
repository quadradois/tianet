# PLAN-013-EXEC - Backlog de Execucao do EPIC-005/Motor Financeiro

**ID:** PLAN-013-EXEC

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Contexto

Este backlog transforma o `PLAN-013` em uma sequencia executavel para o
EPIC-005/Emprestimos, Pagamentos e Motor Financeiro. A numeracao continua o
PLAN-011-EXEC, que encerrou em IMP-145.

A implementacao deve preservar o Motor Financeiro como unica autoridade de
calculo e iniciar por suites/guardrails antes de codigo produtivo.

---

# 2. Ordem Executavel

## P1 - Suites e Guardrails

### IMP-146 - Criar suites de dominio Motor antes do codigo

- **Objetivo:** criar testes para Emprestimo, Parcela, Pagamento, Memoria de
  Calculo, estados e invariantes.
- **Componentes afetados:** `tests/unit/domain/test_motor_financeiro.py`.
- **Dependencias:** PLAN-013, EPIC-005 Product.
- **Criterios de conclusao:** suites expressam criacao por contrato liberado,
  parcelas, pagamentos, saldo, quitacao e renegociacao.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-147 - Criar guardrail de precisao financeira

- **Objetivo:** impedir `float`, arredondamento implicito e periodo fixo
  indevido no dominio financeiro.
- **Componentes afetados:** `tests/unit/domain/test_motor_precision_guardrails.py`.
- **Dependencias:** IMP-146.
- **Criterios de conclusao:** guardrail falha se regras financeiras usarem
  `float` ou periodo implicito.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_precision_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-148 - Criar guardrail anti-calculo fora do Motor

- **Objetivo:** provar que Comercial, Contratos e downstreams nao calculam
  juros, saldo, amortizacao ou quitacao.
- **Componentes afetados:** `tests/unit/domain/test_motor_exclusivity_guardrails.py`.
- **Dependencias:** IMP-147.
- **Criterios de conclusao:** busca AST cobre imports, funcoes e nomes
  proibidos fora do Motor Financeiro.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_exclusivity_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

## P2 - Dominio Motor Financeiro

### IMP-149 - Implementar Aggregate Emprestimo

- **Objetivo:** modelar Emprestimo com Tenant, Carteira, Devedor, Contrato,
  estado e parametros financeiros congelados.
- **Componentes afetados:** `src/emprestimo/domain/credit/emprestimo.py`.
- **Dependencias:** IMP-146..IMP-148.
- **Criterios de conclusao:** Emprestimo nasce somente de contrato liberado e
  impede duplicidade logica.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-150 - Implementar Parcela e Pagamento

- **Objetivo:** modelar Parcelas e Pagamentos como fatos financeiros ligados ao
  Emprestimo.
- **Componentes afetados:** `src/emprestimo/domain/credit/parcela.py`,
  `src/emprestimo/domain/credit/pagamento.py`.
- **Dependencias:** IMP-149.
- **Criterios de conclusao:** Pagamento positivo, Parcela rastreavel e estados
  basicos cobertos.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-151 - Implementar Value Objects financeiros

- **Objetivo:** criar `PeriodoFinanceiro`, `TaxaJuros`, `RegraCalculo` e
  `ValorQuitacao` usando `Decimal`.
- **Componentes afetados:** `src/emprestimo/domain/credit/financeiro.py`.
- **Dependencias:** IMP-150.
- **Criterios de conclusao:** VOs validam datas, moeda, arredondamento e
  precisao.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py tests/unit/domain/test_motor_precision_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-152 - Implementar MotorFinanceiroService

- **Objetivo:** centralizar calculo de parcelas, juros, amortizacao, saldo e
  quitacao.
- **Componentes afetados:** `src/emprestimo/domain/credit/motor_financeiro.py`.
- **Dependencias:** IMP-151.
- **Criterios de conclusao:** service e unica superficie de calculo definitivo.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py tests/unit/domain/test_motor_exclusivity_guardrails.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-153 - Implementar Memoria de Calculo

- **Objetivo:** registrar entradas, periodos, passos, arredondamentos e
  resultados de calculos financeiros.
- **Componentes afetados:** `src/emprestimo/domain/credit/memoria_calculo.py`.
- **Dependencias:** IMP-152.
- **Criterios de conclusao:** toda saida financeira relevante retorna memoria
  reproduzivel.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-154 - Implementar Quitacao, Renegociacao e eventos

- **Objetivo:** modelar quitacao, renegociacao inicial e eventos financeiros.
- **Componentes afetados:** `src/emprestimo/domain/credit/eventos_financeiros.py`.
- **Dependencias:** IMP-153.
- **Criterios de conclusao:** Emprestimo quitado nao recebe Pagamento e
  renegociacao preserva trilha.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

## P3 - Persistencia e Migrations

### IMP-155 - Criar migration Motor Financeiro

- **Objetivo:** adicionar tabelas `emprestimo`, `parcela`, `pagamento`,
  `memoria_calculo` e `evento_financeiro`.
- **Componentes afetados:** nova migration Alembic.
- **Dependencias:** IMP-149..IMP-154.
- **Criterios de conclusao:** upgrade/downgrade/upgrade reproduzivel, FKs,
  indices e constraints.
- **Suite minima:** `uv run pytest tests/integration/migrations/test_motor_financeiro_schema.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-156 - Criar ORM e repositories Motor

- **Objetivo:** persistir e consultar Emprestimos, Parcelas, Pagamentos,
  memorias e eventos.
- **Componentes afetados:** `src/emprestimo/infrastructure/db/orm.py`,
  `src/emprestimo/infrastructure/repositories/__init__.py`,
  `src/emprestimo/domain/credit/ports.py`.
- **Dependencias:** IMP-155.
- **Criterios de conclusao:** round-trip real e filtros por Tenant/Carteira/
  Devedor/estado.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_motor_financeiro_repositories.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-157 - Integrar Motor ao UnitOfWork

- **Objetivo:** expor repositories financeiros no UoW mantendo commit unico e
  rollback automatico.
- **Componentes afetados:** `src/emprestimo/infrastructure/unit_of_work.py`,
  `src/emprestimo/application/ports.py`.
- **Dependencias:** IMP-156.
- **Criterios de conclusao:** services financeiros acessam repositorios sem
  commit fora do UoW.
- **Suite minima:** `uv run pytest tests/integration/repositories/test_motor_financeiro_repositories.py`.
- **Status:** Concluido em 2026-08-09.

## P4 - Application Motor Financeiro

### IMP-158 - Implementar CriacaoEmprestimoService

- **Objetivo:** criar Emprestimo a partir de contrato liberado com auditoria e
  idempotencia.
- **Componentes afetados:** `src/emprestimo/application/motor_financeiro.py`.
- **Dependencias:** IMP-157.
- **Criterios de conclusao:** contrato inexistente/cross-tenant responde 404 e
  duplicidade responde resultado idempotente ou 409 conforme contrato aprovado.
- **Suite minima:** `uv run pytest tests/unit/application/test_motor_financeiro.py tests/integration/application/test_motor_financeiro_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-159 - Implementar PlanoParcelasService

- **Objetivo:** gerar e consultar Parcelas do Emprestimo.
- **Componentes afetados:** `src/emprestimo/application/motor_financeiro.py`.
- **Dependencias:** IMP-158.
- **Criterios de conclusao:** plano de Parcelas e gerado com memoria inicial.
- **Suite minima:** `uv run pytest tests/unit/application/test_motor_financeiro.py tests/integration/application/test_motor_financeiro_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-160 - Implementar PagamentoService

- **Objetivo:** registrar e processar Pagamentos com distribuicao oficial.
- **Componentes afetados:** `src/emprestimo/application/motor_financeiro.py`.
- **Dependencias:** IMP-159.
- **Criterios de conclusao:** valor invalido, duplicidade e Emprestimo quitado
  geram erros de contrato.
- **Suite minima:** `uv run pytest tests/unit/application/test_motor_financeiro.py tests/integration/application/test_motor_financeiro_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-161 - Implementar ConsultaSaldoService

- **Objetivo:** consultar saldo e memoria de calculo por data de referencia.
- **Componentes afetados:** `src/emprestimo/application/motor_financeiro.py`.
- **Dependencias:** IMP-160.
- **Criterios de conclusao:** consulta retorna principal, juros, encargos,
  total e memoria.
- **Suite minima:** `uv run pytest tests/unit/application/test_motor_financeiro.py tests/integration/application/test_motor_financeiro_application.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-162 - Implementar QuitacaoRenegociacaoService

- **Objetivo:** calcular valor de quitacao, quitar Emprestimo e registrar
  renegociacao inicial.
- **Componentes afetados:** `src/emprestimo/application/motor_financeiro.py`.
- **Dependencias:** IMP-161.
- **Criterios de conclusao:** quitacao e renegociacao preservam memoria,
  auditoria e estados.
- **Suite minima:** `uv run pytest tests/unit/application/test_motor_financeiro.py tests/integration/application/test_motor_financeiro_application.py`.
- **Status:** Concluido em 2026-08-09.

## P5 - RBAC, API e OpenAPI

### IMP-163 - Registrar permissoes financeiras no catalogo IAM

- **Objetivo:** adicionar permissoes do Motor Financeiro ao catalogo RBAC.
- **Componentes afetados:** `src/emprestimo/application/iam_catalogo.py`.
- **Dependencias:** IMP-158..IMP-162.
- **Criterios de conclusao:** perfil sem permissao recebe 403; perfil com
  permissao executa operacao correspondente.
- **Suite minima:** `uv run pytest tests/unit/application/test_autorizacao.py tests/integration/api/test_api_authorization.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-164 - Criar schemas e dependencies da API Motor

- **Objetivo:** criar DTOs de requests/responses e dependencies financeiras
  isoladas por Tenant.
- **Componentes afetados:** `src/emprestimo/presentation/api/motor_schemas.py`,
  `src/emprestimo/presentation/api/dependencies.py`.
- **Dependencias:** IMP-163.
- **Criterios de conclusao:** DTOs nao aceitam regra financeira arbitraria e
  cross-tenant retorna 404.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-09.

### IMP-165 - Criar endpoints de Emprestimo

- **Objetivo:** expor `POST /credit/contratos/{contrato_id}/emprestimos`,
  `GET /credit/emprestimos/{emprestimo_id}` e
  `GET /credit/carteiras/{carteira_id}/emprestimos`.
- **Componentes afetados:** `src/emprestimo/presentation/api/motor_routes.py`,
  `src/emprestimo/presentation/api/main.py`.
- **Dependencias:** IMP-164.
- **Criterios de conclusao:** contratos HTTP 200/201/400/401/403/404/409
  cobertos.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-10.

### IMP-166 - Criar endpoints de Parcelas e Pagamentos

- **Objetivo:** expor `GET /credit/emprestimos/{emprestimo_id}/parcelas` e
  `POST /credit/emprestimos/{emprestimo_id}/pagamentos`.
- **Componentes afetados:** `src/emprestimo/presentation/api/motor_routes.py`.
- **Dependencias:** IMP-165.
- **Criterios de conclusao:** Pagamento positivo, replay idempotente, conflito
  de payload divergente, RBAC e cross-tenant cobertos.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-10.

### IMP-167 - Criar endpoints de saldo, memoria, quitacao e renegociacao

- **Objetivo:** expor `GET /credit/emprestimos/{emprestimo_id}/saldo`,
  `GET /credit/emprestimos/{emprestimo_id}/memoria-calculo`,
  `GET /credit/emprestimos/{emprestimo_id}/quitacao`,
  `POST /credit/emprestimos/{emprestimo_id}/quitacao` e
  `POST /credit/emprestimos/{emprestimo_id}/renegociacoes`.
- **Componentes afetados:** `src/emprestimo/presentation/api/motor_routes.py`.
- **Dependencias:** IMP-166.
- **Criterios de conclusao:** consultas nao alteram estado; quitacao e
  renegociacao validam transicoes e aplicam idempotencia transacional.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-10.

### IMP-168 - Atualizar OpenAPI Motor Financeiro

- **Objetivo:** documentar endpoints, security Bearer e respostas de erro.
- **Componentes afetados:** `src/emprestimo/presentation/api/openapi.py`.
- **Dependencias:** IMP-165..IMP-167.
- **Criterios de conclusao:** OpenAPI declara 400/401/403/404/409 conforme
  rotas e schemas.
- **Suite minima:** `uv run pytest tests/integration/api/test_api_protected_endpoints.py tests/integration/api/test_api_motor_financeiro.py`.
- **Status:** Concluido em 2026-08-10.

## P6 - Recertificacao

### IMP-169 - Recertificar guardrails de precisao e exclusividade

- **Objetivo:** provar que o Motor usa `Decimal` e que nenhum outro contexto faz
  calculo financeiro definitivo.
- **Componentes afetados:** suites guardrail e revisao de imports.
- **Dependencias:** IMP-168.
- **Criterios de conclusao:** busca e testes nao encontram `float` financeiro
  nem calculo fora do Motor.
- **Suite minima:** `uv run pytest tests/unit/domain/test_motor_precision_guardrails.py tests/unit/domain/test_motor_exclusivity_guardrails.py`.
- **Status:** Concluido em 2026-08-10.

### IMP-170 - Recertificar EPIC-005 com suite completa

- **Objetivo:** fechar o EPIC-005 com gates globais e revisao adversarial.
- **Componentes afetados:** relatorio de execucao e status de PLAN/Product se
  implementado.
- **Dependencias:** IMP-169.
- **Criterios de conclusao:** suite Python completa, gates Ruff/Black/Mypy/docs
  aprovados e veredito adversarial documentado.
- **Suite minima:** `uv run pytest -q`.
- **Status:** Concluido em 2026-08-10.

---

# 3. Gates

O EPIC-005 avanca somente com:

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
| 1.21.0 | 2026-08-10 | Pos-revisao adversarial: pagamento, quitacao e renegociacao passam a rejeitar replay divergente e renegociacao exige `Idempotency-Key`. |
| 1.20.0 | 2026-08-10 | IMP-170 concluido com recertificacao completa do EPIC-005, suite Python, qualidade e docs verdes. |
| 1.19.0 | 2026-08-10 | IMP-169 concluido com guardrails de precisao Decimal e exclusividade do Motor recertificados apos a API financeira. |
| 1.18.0 | 2026-08-10 | IMP-165..IMP-168 concluidos com rotas REST do Motor Financeiro, schemas, RBAC, OpenAPI e suite integrada de API. |
| 1.17.0 | 2026-08-09 | IMP-164 concluido com schemas REST do Motor Financeiro e dependencies dos servicos financeiros preparadas para os endpoints. |
| 1.16.0 | 2026-08-09 | IMP-163 concluido com permissoes `motor.*` registradas no catalogo IAM, migration de seed e testes de RBAC financeiro. |
| 1.15.0 | 2026-08-09 | IMP-162 concluido com QuitacaoRenegociacaoService calculando quitacao, quitando emprestimo e registrando renegociacao com memorias, eventos e estados preservados. |
| 1.14.0 | 2026-08-09 | IMP-161 concluido com ConsultaSaldoService retornando principal, juros, encargos, total e memoria sem alterar estado persistido. |
| 1.13.0 | 2026-08-09 | IMP-160 concluido com PagamentoService, distribuicao oficial pelo Motor, replay por chave e persistencia de pagamento, memoria, evento e parcelas. |
| 1.12.0 | 2026-08-09 | IMP-159 concluido com PlanoParcelasService gerando, persistindo e consultando parcelas com memoria inicial. |
| 1.11.0 | 2026-08-09 | IMP-158 concluido com CriacaoEmprestimoService, auditoria, idempotencia, 404 cross-tenant e conflito de duplicidade. |
| 1.10.0 | 2026-08-09 | IMP-157 concluido com repositories do Motor Financeiro expostos no UnitOfWork e teste transacional. |
| 1.9.0 | 2026-08-09 | IMP-156 concluido com ORM e repositories do Motor Financeiro para emprestimos, parcelas, pagamentos, memorias e eventos. |
| 1.8.0 | 2026-08-09 | IMP-155 concluido com migration do Motor Financeiro para emprestimos, parcelas, pagamentos, memorias e eventos. |
| 1.7.0 | 2026-08-09 | IMP-154 concluido com eventos financeiros formais para pagamento, quitacao e renegociacao. |
| 1.6.0 | 2026-08-09 | IMP-153 concluido com MemoriaCalculo formalizada em modulo proprio, passos, periodos, regra e arredondamentos. |
| 1.5.0 | 2026-08-09 | IMP-152 concluido com MotorFinanceiro centralizando parcelas, pagamento, saldo, quitacao e renegociacao inicial. |
| 1.4.0 | 2026-08-09 | IMP-151 concluido com Value Objects financeiros para periodo, taxa, regra e quitacao. |
| 1.3.0 | 2026-08-09 | IMP-150 concluido com entities Parcela e Pagamento como fatos financeiros sem calculo definitivo. |
| 1.2.0 | 2026-08-09 | IMP-149 concluido com Aggregate Emprestimo originado por ContratoLiberadoLogico. |
| 1.1.0 | 2026-08-09 | IMP-146..IMP-148 concluidos com suites de dominio e guardrails iniciais do Motor Financeiro. |
| 1.0.0 | 2026-08-09 | Backlog tecnico do PLAN-013/EPIC-005 com IMP-146..IMP-170, suites antes de codigo e guardrails do Motor. |
