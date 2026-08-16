# Frontend MVP — IMP-293 Contratos

**Data:** 2026-08-14

**Plano relacionado:** PLAN-025

**Status:** Concluido com caveats nao bloqueantes

---

# 1. Resultado

O IMP-293 materializou o modulo frontend de Contratos em `/app/contratos` e
`/app/contratos/[contratoId]`, consumindo somente as 8 operacoes oficiais de
EPIC-004:

- listar e criar Contratos por Carteira;
- consultar Contrato por ID;
- consultar historico contratual;
- assinar;
- liberar saida logica para Motor;
- cancelar;
- encerrar.

O pacote nao cria Emprestimo, Parcela, Pagamento, saldo, memoria, quitacao,
renegociacao ou calculo financeiro. `parametros` e `parametros_contratados`
sao exibidos como objetos opacos retornados pelo backend.

---

# 2. Evidencia RED -> GREEN

## RED inicial

- `node scripts/tests/test-plan-025-contracts.js`
- Resultado observado: **128/129**
- Falha unica esperada: `frontend/src/lib/bff/contratos.server.ts ausente`

## GREEN observado

- `npm --prefix frontend run test:unit`: **21/21**
- `npm --prefix frontend run test:component`: **28/28**
- `npm --prefix frontend run test:bff`: **85/85**
- `npm --prefix frontend run test:contract`: **18/18**
- `npm --prefix frontend run test:contratos`: **8/8**
- `npm --prefix frontend run lint`: verde
- `npm --prefix frontend run build`: verde

---

# 3. Decisoes contratuais

- O recorte IMP-293 possui exatamente 8 operacoes de Contratos.
- A rota `POST /credit/contratos/{contrato_id}/emprestimos` pertence ao
  IMP-294/Motor e nao foi chamada, renderizada ou testada como Contratos.
- A rota `GET /credit/propostas-comerciais/{proposta_id}/contrato-logico`
  permanece como upstream Comercial read-only.
- As 8 operacoes de Contratos nao publicam `Idempotency-Key`; o frontend nao
  inventa esse header.
- `liberar-para-motor` e somente saida logica para o Motor futuro; nao cria
  operacao financeira.
- 404 e 5xx usam mensagens seguras e correlation ID; 400/403/409 preservam
  erro contratual quando aplicavel.

---

# 4. Evidencias visuais

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-293-contratos-list-desktop.png` | 1440x900 | `0edb2095cf246b271fb6469af2054734cddeca9ecd3c6a4bda9b6d9929663454` |
| `frontend-mvp-imp-293-contratos-list-mobile.png` | 390x844 | `a21d54491e1af7876cc539e688ac717364ad1657a685a20775b4e3a9b0007259` |
| `frontend-mvp-imp-293-contrato-detail-desktop.png` | 1440x900 | `3e0132daae8fd1fdc284216728ab7ec723b4f0f6937ac86072ded7de2113c587` |
| `frontend-mvp-imp-293-contrato-flow-mobile.png` | 390x844 | `72f0643ccdb957b2ac929613baa0202a757826c083b0a728339901a0f1297405` |

---

# 5. Escopo e inventario

- Baseline IMP-293: 215 caminhos.
- Mutaveis governados: 11.
- Protegidos: 204.
- Novos permitidos: 22.
- Inventario final esperado: 237 caminhos.
- Predecessor: `docs/audits/evidence/frontend-mvp-imp-292-protected-baseline.json`.
- SHA-256 do predecessor: `fc9be3e156c4f932774c95b7601304cf413d0cb80bd8051aa3d6bc77365116d3`.

Arquivos principais criados:

- `frontend/src/lib/bff/contratos.server.ts`
- `frontend/src/lib/contratos/contratos-policy.ts`
- `frontend/src/components/contratos/contratos.tsx`
- `frontend/src/components/contratos/contrato-decision-dialog.client.tsx`
- `frontend/src/app/app/contratos/page.tsx`
- `frontend/src/app/app/contratos/[contratoId]/page.tsx`
- `frontend/src/app/app/contratos/actions.ts`
- `frontend/tests/unit/contratos-policy.test.ts`
- `frontend/tests/component/contratos.test.tsx`
- `frontend/tests/bff/contratos.test.ts`
- `frontend/tests/contract/contratos.test.ts`
- `frontend/tests/contratos-e2e/*`
- `frontend/playwright.contratos.config.ts`
- `scripts/tests/test-imp-293-scope.js`

---

# 6. Caveats nao bloqueantes

- A evidência RED é temporal e não é reexecutável sem reverter o GREEN.
- CI remota Linux/Windows ainda não foi observada porque não houve commit/push.
- O shell local pode divergir da toolchain governada; o workflow continua
  pinando Node 24.19.0 e npm 11.17.0.
- Git pode emitir avisos EOL no Windows; `git diff --check` deve permanecer
  sem erros.
- Product menciona idempotência em Contratos, mas o OpenAPI certificado das 8
  operacoes nao publica `Idempotency-Key`; isso permanece fronteira contratual
  ate eventual hardening backend.

---

# 7. Proximo passo

O IMP-294 permanece bloqueado ate novo `$fable:fable-judge` focal sobre o
IMP-293. Nenhum Motor, pagamento, Emprestimo, Parcela ou calculo financeiro foi
iniciado nesta etapa.
