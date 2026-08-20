import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  appropriatePaymentPromise,
  listCollectionCases,
  registerCollectionAction,
  registerPaymentPromise,
} from "@/lib/bff/cobranca.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const LOAN_ID = "00000000-0000-4000-8000-000000000040";
const CASE_ID = "00000000-0000-4000-8000-000000000090";
const ACTION_ID = "00000000-0000-4000-8000-000000000091";
const PROMISE_ID = "00000000-0000-4000-8000-000000000092";
const PAYMENT_ID = "00000000-0000-4000-8000-000000000070";
const APPROPRIATION_ID = "00000000-0000-4000-8000-000000000093";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.cobranca.invalid", origin: "http://frontend.cobranca.invalid", production: false, currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
}

async function cookieStore(selected: BffConfig) {
  const values = new Map<string, string>();
  values.set(sessionCookieName(selected), await sealSession(session, selected, NOW));
  return {
    get(name: string) { const value = values.get(name); return value ? { value } : undefined; },
    set(name: string, value: string) { values.set(name, value); },
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

function collectionCase(carteira_id = WALLET_ID) {
  return { carteira_id, caso_id: CASE_ID, criado_em: "2026-08-14T10:00:00Z", devedor_id: DEBTOR_ID, emprestimo_id: LOAN_ID, estado: "pendente", origem: "motor", tenant_id: TENANT_ID, titulo: "Parcela vencida", total_pendente: "100.00" };
}

function collectionAction() {
  return { acao_id: ACTION_ID, carteira_id: WALLET_ID, caso_id: CASE_ID, devedor_id: DEBTOR_ID, emprestimo_id: LOAN_ID, registrada_em: "2026-08-14T12:00:00Z", resultado: "Contato realizado", tenant_id: TENANT_ID, tipo: "contato", usuario_id: USER_ID };
}

function paymentPromise() {
  return { carteira_id: WALLET_ID, data_promessa: "2026-08-21", devedor_id: DEBTOR_ID, emprestimo_id: LOAN_ID, estado: "pendente", promessa_id: PROMISE_ID, tenant_id: TENANT_ID, valor_declarado: "100.00" };
}

function appropriation() {
  return { apropriacao_id: APPROPRIATION_ID, estado_promessa: "cumprida", pagamento_id: PAYMENT_ID, promessa_id: PROMISE_ID, realizado_em: "2026-08-14T12:10:00Z", valor: "100.00" };
}

describe("BFF Cobranca", () => {
  it("lista fila usando somente Carteira propria e filtros oficiais", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.has("Idempotency-Key")).toBe(false);
      return Response.json({ items: [collectionCase()], total: 1 }, { headers: { "X-Correlation-ID": "corr-list" } });
    });
    const result = await listCollectionCases(await cookieStore(selected), context(["cobranca.caso.ler"]), { devedorId: DEBTOR_ID, estado: "pendente" }, dependencies(selected, backend));
    expect(result).toMatchObject({ kind: "ready" });
    expect(seen[0]?.pathname).toBe("/credit/cobrancas/casos");
    expect(seen[0]?.searchParams.get("carteira_id")).toBe(WALLET_ID);
    expect(seen[0]?.searchParams.get("devedor_id")).toBe(DEBTOR_ID);
    expect(seen[0]?.searchParams.has("tenant_id")).toBe(false);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listCollectionCases(await cookieStore(selected), context(["cobranca.caso"]), {}, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar vazio", async () => {
    const selected = config();
    const missing = await listCollectionCases(await cookieStore(selected), context(["cobranca.caso.ler"]), {}, dependencies(selected, async () => Response.json({ items: [{ ...collectionCase(), total_pendente: undefined }], total: 1 })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await listCollectionCases(await cookieStore(selected), context(["cobranca.caso.ler"]), {}, dependencies(selected, async () => Response.json({ items: [collectionCase(OTHER_WALLET)], total: 1 })));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("envia Idempotency-Key nos tres comandos e nunca no GET da fila", async () => {
    const selected = config();
    const keys: Array<[string, boolean]> = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      keys.push([url.pathname, request.headers.has("Idempotency-Key")]);
      if (url.pathname.endsWith("/acoes")) return Response.json(collectionAction());
      if (url.pathname.endsWith("/promessas")) return Response.json(paymentPromise());
      if (url.pathname.endsWith("/apropriacoes")) return Response.json(appropriation());
      return Response.json({ items: [collectionCase()], total: 1 });
    };
    await expect(listCollectionCases(await cookieStore(selected), context(["cobranca.caso.ler"]), {}, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    const actionForm = new FormData();
    actionForm.set("caso_id", CASE_ID);
    actionForm.set("tipo", "contato");
    actionForm.set("resultado", "Contato realizado");
    await expect(registerCollectionAction(await cookieStore(selected), context(["cobranca.acao.registrar"]), actionForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const promiseForm = new FormData();
    promiseForm.set("caso_id", CASE_ID);
    promiseForm.set("valor_declarado", "100.00");
    promiseForm.set("data_promessa", "2026-08-21");
    await expect(registerPaymentPromise(await cookieStore(selected), context(["cobranca.promessa.registrar"]), promiseForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const appropriationForm = new FormData();
    appropriationForm.set("promessa_id", PROMISE_ID);
    appropriationForm.set("pagamento_id", PAYMENT_ID);
    await expect(appropriatePaymentPromise(await cookieStore(selected), context(["cobranca.promessa.apropriar"]), appropriationForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(keys).toEqual([
      ["/credit/cobrancas/casos", false],
      [`/credit/cobrancas/casos/${CASE_ID}/acoes`, true],
      [`/credit/cobrancas/casos/${CASE_ID}/promessas`, true],
      [`/credit/cobrancas/promessas/${PROMISE_ID}/apropriacoes`, true],
    ]);
  });

  it("mapeia 400, 403, 404, 409, 422 e 5xx com correlation e 404 neutro", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "conflito_estado"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listCollectionCases(await cookieStore(selected), context(["cobranca.caso.ler"]), {}, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });
});
