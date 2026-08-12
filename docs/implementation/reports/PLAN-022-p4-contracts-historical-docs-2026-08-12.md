# PLAN-022 - Recertificacao P4 de Contratos HTTP e Documentacao Historica

**ID:** PLAN-022

**Data:** 2026-08-12

**Escopo:** IMP-269, IMP-270 e IMP-271

**Plano relacionado:** PLAN-020

**Status:** P4 concluido sem divergencias ativas bloqueantes

---

# 1. Objetivo

Registrar a recertificacao dos contratos publicos do Backend MVP, cobrindo
OpenAPI, matriz HTTP global e classificacao de documentacao historica. Este
relatorio nao cria EPIC funcional, nao inicia frontend e nao altera regra de
negocio ou regra financeira.

---

# 2. Evidencia Automatizada

Suite adicionada:

- `tests/integration/api/test_backend_mvp_contracts.py`.

Cobertura da suite:

- `IMP-269`: compara as 105 operacoes OpenAPI contra os routers FastAPI
  importados pela aplicacao, verifica `BearerAuth`, `X-Correlation-ID`,
  `operationId`, `ErroResponse` e resposta tecnica `500`;
- `IMP-270`: consolida matriz HTTP 400/401/403/404/409 por contrato OpenAPI e
  executa amostras runtime para payload invalido, ausencia de token, permissao
  insuficiente, inexistencia logica e conflito de idempotencia;
- `IMP-271`: garante que este relatorio classifica os documentos historicos
  com caveats aceitos e sem pendencia superada tratada como bloqueante atual.

---

# 3. Matriz HTTP Global

| Status | Semantica certificada | Evidencia runtime |
|---|---|---|
| 400 | payload, parametros ou periodo invalido | relatorio de pagamentos com `inicio > fim` |
| 401 | token ausente, invalido ou expirado | `GET /platform/tenants` sem `Authorization` |
| 403 | principal autenticado sem permissao | `GET /platform/tenants` com perfil sem permissao |
| 404 | recurso inexistente ou fora do escopo | `GET /platform/tenants/{tenant_id}` inexistente |
| 409 | conflito de idempotencia ou estado | replay divergente em cadastro de Devedor |

---

# 4. Classificacao Historica

Divergencias ativas bloqueantes: nenhuma.

Caveats historicos aceitos:

| Documento | Classificacao | Decisao |
|---|---|---|
| `docs/audits/audits/vistoria-backend-2026-08-08.md` | Historico aceito | Mantido como fotografia anterior ao fechamento do Backend MVP. Nao representa pendencia atual sem evidência nova. |
| `docs/audits/audits/auditoria-as-is-to-be-backend-2026-08-08.md` | Historico aceito | Mantido como auditoria de estado anterior; gaps ali descritos foram consumidos pelos EPICs posteriores e pelo PLAN-020. |
| `docs/implementation/reports/PLAN-020-p0-inventory-baseline-2026-08-12.md` | Baseline P0 | O timeout de `pytest -q` e a recusa segura de `quality:migrations` permanecem classificados como baseline inicial; P3 executou `quality:migrations` com flag destrutivo em banco descartavel. |
| `docs/implementation/backlogs/PLAN-020-execution-backlog.md` | Documento vivo | Atualizado para refletir P4 concluido e manter P5 como proximo bloco. |

Regra de interpretacao para leituras futuras: documentos em `docs/audits/` e
relatorios intermediarios registram contexto historico. Pendencia ativa do
Backend MVP passa a exigir evidencia em codigo, teste vivo, PLAN-020 ou
backlog vigente.

---

# 5. Resultado P4

`IMP-269`, `IMP-270` e `IMP-271` ficam materializados por teste vivo e
classificacao documental. O proximo bloco limpo e P5, com `IMP-272` para
recertificacao completa e `IMP-273` para relatorio final de prontidao.

---

# 6. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Recertificacao P4 de OpenAPI, matriz HTTP e documentacao historica do PLAN-020. |
