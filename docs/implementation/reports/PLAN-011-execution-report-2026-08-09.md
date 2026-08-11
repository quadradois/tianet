# PLAN-012 - Relatorio de Recertificacao PLAN-011/EPIC-004 - 2026-08-09

**ID:** PLAN-012

**Versao:** 1.0.0

**Status:** VERIFIED WITH CAVEATS

---

# 1. Escopo Recertificado

Este relatorio fecha o macro-loop de implementacao do `PLAN-011` para o
`EPIC-004/Contratos de Credito`, cobrindo os itens `IMP-125` a `IMP-145`.

Foram recertificados:

- dominio `ContratoCredito`, estados, eventos/decisoes e saida logica de
  contrato liberado;
- guardrail anti-Motor no contexto Contratos;
- migration `0010_contratos_schema`;
- ORM, repository e Unit of Work de Contratos;
- application services de formalizacao, consulta, assinatura, liberacao,
  cancelamento e encerramento;
- permissoes RBAC, dependencies, schemas e endpoints protegidos;
- contrato OpenAPI para 400/401/403/404/409.

---

# 2. Evidencias de Verificacao

Comandos executados em 2026-08-09:

- `uv run pytest tests/unit/domain/test_contrato_credito.py tests/unit/domain/test_contratos_guardrails.py tests/unit/application/test_contratos.py -q`:
  17 testes passaram;
- `uv run pytest tests/integration/migrations/test_contratos_schema.py tests/integration/repositories/test_contratos_repositories.py tests/integration/application/test_contratos_application.py tests/integration/api/test_api_contratos.py -q`:
  19 testes passaram;
- `uv run pytest tests/unit/domain/test_contrato_credito.py tests/unit/domain/test_contratos_guardrails.py tests/unit/application/test_contratos.py tests/integration/api/test_api_protected_endpoints.py tests/integration/api/test_api_authorization.py tests/unit/application/test_autorizacao.py -q`:
  67 testes passaram;
- `uv run ruff check src tests migrations`: aprovado;
- `uv run black --check src tests migrations`: aprovado;
- `uv run mypy src tests`: aprovado sem issues em 144 source files;
- `uv run pytest -q`: suite completa aprovada com exit code 0;
- `npm run docs:validate`: 183 verificacoes OK, 46 avisos, 0 erros;
- `npm run docs:test`: 42/42 testes documentais passaram.

---

# 3. Caveats

- `docs:validate` permanece com avisos historicos/planejados, incluindo
  referencias futuras a `EPIC-005`, aliases legados e lacunas ja existentes de
  sequenciamento documental. Nao houve erro documental.
- A primeira tentativa paralela de rodar duas baterias de pytest contra o mesmo
  Postgres gerou colisao de `CREATE TABLE tenant`; a bateria de Contratos foi
  rerodada de forma serial e passou.
- O warning `StarletteDeprecationWarning` do `fastapi.testclient` permanece
  preexistente e nao bloqueia a recertificacao.
- As rotas por identificador global de contrato (`/credit/contratos/{id}`) estao
  isoladas por Tenant, conforme o `Principal` IAM atual. Isolamento por Carteira
  existe nas operacoes sob `/credit/carteiras/{carteira_id}/...` e nos filtros
  de listagem/repository; escopo IAM por Carteira fica para decisao futura.
- O handler global de `RequestValidationError` da API retorna 400 para entrada
  invalida. O PLAN-011 foi alinhado a esse contrato global em vez de criar uma
  excecao local de 422 para Contratos.

---

# 4. Revisao Adversarial

Uma revisao adversarial read-only apontou tres lacunas objetivas, todas
corrigidas antes deste veredito:

- criacao de contrato agora registra decisao/evento inicial `criado`;
- `evento_contrato` agora persiste e expoe o campo `tipo`;
- foi adicionada suite unitária de application em
  `tests/unit/application/test_contratos.py`;
- rotas de Contratos entraram na suite global runtime de endpoints protegidos;
- entrada invalida em Contratos passou a ter cobertura runtime como 400.

---

# 5. Veredito

`EPIC-004/Contratos` esta implementado e recertificado como
`VERIFIED WITH CAVEATS`.

O escopo entregue nao implementa Motor Financeiro: Contratos apenas gera uma
saida logica para futura integracao com `EPIC-005`.

---

# 6. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Relatorio final de recertificacao do PLAN-011/EPIC-004 apos implementacao dos IMP-125..IMP-145. |
