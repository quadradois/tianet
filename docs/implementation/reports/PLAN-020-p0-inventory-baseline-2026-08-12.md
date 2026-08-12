# PLAN-021 - Inventario e Baseline P0 do Backend MVP

**ID:** PLAN-021

**Data:** 2026-08-12

**Escopo:** IMP-255 e IMP-256

**Plano relacionado:** PLAN-020

**Status:** Baseline P0 concluido com caveats operacionais classificados

---

# 1. Objetivo

Registrar o estado inicial verificavel do Backend MVP antes das suites E2E
transversais do PLAN-020. Este relatorio nao implementa regra de negocio,
nao cria endpoint e nao altera regra financeira.

---

# 2. Inventario API, OpenAPI e RBAC

Evidencia automatizada adicionada:

- `tests/integration/api/test_backend_mvp_inventory.py`;
- `uv run pytest tests/integration/api/test_backend_mvp_inventory.py -q`.

Resultado observado:

- OpenAPI publica 105 operacoes HTTP de negocio/operacao;
- 5 operacoes sao publicas: `/health` e rotas `/auth/*`;
- 100 operacoes exigem `BearerAuth`;
- todas as operacoes documentadas possuem `X-Correlation-ID` nas respostas
  publicadas, exceto respostas padrao `422` geradas pelo framework;
- as superficies de Platform, IAM, Cadastro, Comercial, Contratos, Motor,
  Operacao Diaria, Relatorios, Configuracoes, Automacao, Notificacoes e Health
  estao presentes.

Comparabilidade atual:

| Eixo | Estado observado | Classificacao |
|---|---|---|
| Rotas reais e OpenAPI | OpenAPI gerado pela app lista 105 operacoes e e validado por teste vivo | Verde para inventario |
| Publico vs protegido | `/health` e `/auth/*` publicos; demais operacoes com `BearerAuth` | Verde para inventario |
| Catalogo IAM | `src/emprestimo/application/iam_catalogo.py` possui 56 permissoes catalogadas | Verde para inventario |
| Teste runtime sem token | `test_api_protected_endpoints.py` cobre 65 endpoints representativos | Gap planejado para IMP-262/IMP-269/IMP-270 |
| Matriz HTTP global | Contratos existem por contexto, mas nao ha matriz unica 400/401/403/404/409 | Gap planejado para IMP-270 |

---

# 3. Inventario de Suites

Coleta executada:

- `uv run pytest --collect-only -q`;
- total coletado: 918 testes Python;
- aviso observado: `StarletteDeprecationWarning` em `fastapi.testclient`,
  sem falha de coleta.

Distribuicao por pasta:

| Area | Arquivos |
|---|---:|
| `tests/integration/api` | 13 |
| `tests/integration/application` | 10 |
| `tests/integration/migrations` | 6 |
| `tests/integration/repositories` | 10 |
| `tests/unit/application` | 21 |
| `tests/unit/architecture` | 3 |
| `tests/unit/domain` | 31 |
| `tests/unit/presentation` | 3 |
| `tests/unit/presentation/api` | 2 |
| `tests/unit/worker` | 3 |

Suites documentais ativas no `npm run docs:test`:

- `scripts/tests/test-validator.js`;
- `scripts/tests/test-identifiers.js`;
- `scripts/tests/test-epic-007-contracts.js`;
- `scripts/tests/test-epic-008-contracts.js`;
- `scripts/tests/test-epic-009-contracts.js`;
- `scripts/tests/test-epic-010-contracts.js`;
- `scripts/tests/test-plan-020-contracts.js`.

---

# 4. Inventario de Migrations

Migrations versionadas observadas:

- `0001_platform_credit.py`;
- `0002_usuario_perfil_acesso.py`;
- `0003_idempotency_audit.py`;
- `0004_devedor_contato.py`;
- `0005_idempotency_key_escopo.py`;
- `0006_contato_removido_em.py`;
- `0007_iam_schema.py`;
- `0008_iam_operacional.py`;
- `0009_comercial_schema.py`;
- `0010_contratos_schema.py`;
- `0011_motor_financeiro_schema.py`;
- `0012_motor_financeiro_permissoes.py`;
- `0013_operacao_diaria_schema.py`;
- `0014_configuracoes_financeiras_schema.py`;
- `0015_automacao_scheduler_notification_schema.py`;
- `0016_automacao_permissoes.py`.

Gate `npm run quality:migrations` observado:

- resultado: recusado de forma segura;
- classificacao: problema ambiental/controlado, nao falha funcional;
- motivo: `scripts/validate_migrations.py` exige
  `MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE=1` e banco descartavel, pois executa
  `upgrade head -> downgrade base -> upgrade head` com reset destrutivo do
  schema publico.

---

# 5. Baseline de Gates

| Comando | Resultado observado | Classificacao |
|---|---|---|
| `node scripts/tests/test-plan-020-contracts.js` | 13/13 passou | Verde |
| `uv run pytest tests/integration/api/test_backend_mvp_inventory.py -q` | 3/3 passou | Verde |
| `npm run docs:validate` | 302 OK, 29 avisos, 0 erros | Verde com avisos historicos |
| `npm run docs:test` | todas as suites documentais passaram | Verde |
| `git diff --check` | passou | Verde |
| `uv run pytest --collect-only -q` | 918 testes coletados | Verde com aviso deprecacao Starlette |
| `uv run pytest -q` | timeout apos 184s nesta execucao | Inconclusivo por tempo de execucao |
| `npm run quality:migrations` | recusado sem flag destrutiva | Ambiental/controlado |

O timeout do `pytest -q` nao foi classificado como falha funcional porque o
processo nao retornou falha de teste antes do limite local. A execucao foi
interrompida para nao deixar processos pendurados.

---

# 6. Lacunas Confirmadas para Proximos IMPs

- criar E2E transversais F1 a F6 com PostgreSQL real;
- expandir RBAC global para comparar catalogo IAM, OpenAPI e rotas protegidas;
- consolidar matriz HTTP global 400/401/403/404/409;
- executar `quality:migrations` somente contra banco descartavel explicitamente
  autorizado;
- rodar `pytest -q` com janela maior ou em pipeline para obter resultado final
  completo;
- emitir relatorio final de prontidao apenas apos IMP-272.

---

# 7. Conclusao P0

IMP-255 e IMP-256 ficam materializados como baseline de inventario e controle.
As lacunas restantes sao esperadas pelo PLAN-020 e seguem para P1/P2/P3,
principalmente E2E transversal, RBAC global, HTTP matrix e migrations
destrutivas em banco descartavel.

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Inventario e baseline P0 do PLAN-020 para IMP-255 e IMP-256. |
