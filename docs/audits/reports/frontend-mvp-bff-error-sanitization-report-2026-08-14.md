# Sanitizacao transversal de erros BFF — PLAN-025

**Data:** 2026-08-14
**Plano relacionado:** PLAN-025 — Frontend MVP
**Status:** Concluido localmente; IMP-297 permanece Planejado e exige novo judge antes de iniciar.

## 1. Objetivo

Corrigir o falso verde transversal encontrado depois do IMP-296: BFFs herdados
de Devedores, Comercial, Contratos, Motor e Cobranca ainda podiam repassar a
`mensagem` bruta do backend em respostas estruturadas 400/401/403/409/422.

A correcao preserva o `codigo` e o `X-Correlation-ID` selecionado do backend
quando valido, mas troca a mensagem publica por texto seguro por dominio.

## 2. Evidencia RED -> GREEN

- **RED observado:** os testes BFF herdados aceitavam `stack cross-carteira` em
  400/403/409/422, porque a assercao de nao vazamento era limitada a 404/500.
- **GREEN local:** os cinco testes BFF herdados passaram com 31/31 casos e a
  busca por `mensagem: errorBody.mensagem` nao encontrou ocorrencias restantes
  em `frontend/src/lib/bff`.
- **Contrato documental:** `node scripts/tests/test-plan-025-contracts.js`
  exige a mensagem segura e rejeita a regressao que limita a assercao a 404/500.

## 3. Escopo

Baseline encadeado:

- predecessor: `docs/audits/evidence/frontend-mvp-imp-296-protected-baseline.json`
- baseline: 301 caminhos
- mutaveis: 12 caminhos
- protegidos: 289 caminhos
- novos: 3 caminhos
- inventario final esperado: 304 caminhos

Arquivos funcionais alterados:

- `frontend/src/lib/bff/devedores.server.ts`
- `frontend/src/lib/bff/comercial.server.ts`
- `frontend/src/lib/bff/contratos.server.ts`
- `frontend/src/lib/bff/motor.server.ts`
- `frontend/src/lib/bff/cobranca.server.ts`

Testes alterados:

- `frontend/tests/bff/devedores.test.ts`
- `frontend/tests/bff/comercial.test.ts`
- `frontend/tests/bff/contratos.test.ts`
- `frontend/tests/bff/motor.test.ts`
- `frontend/tests/bff/cobranca.test.ts`

Governanca/gates:

- `.github/workflows/quality.yml`
- `scripts/tests/test-plan-025-contracts.js`
- `scripts/tests/test-bff-error-sanitization-scope.js`
- `docs/audits/evidence/frontend-mvp-bff-error-sanitization-protected-baseline.json`

## 4. Fronteiras preservadas

- Nenhum backend Python, migration, teste Python, Product, Registry, OpenAPI,
  dependencia ou lockfile foi alterado.
- Nenhuma rota, componente ou jornada nova foi criada.
- O IMP-297 permanece Planejado e bloqueado ate novo `fable-judge`.
- O manifesto historico do IMP-296 permanece imutavel; este pacote cria um
  scope corrente encadeado para a correcao transversal.

## 5. Caveats

- A CI remota Linux/Windows nao foi observada nesta sessao.
- O RED e temporal, reconstruido pela comparacao entre a assercao antiga e a
  politica corrigida.
- O worktree continua local e sem commit/push/PR.
