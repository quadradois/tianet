import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { beginReportsLoads } from "@/lib/bff/relatorios.server";
import type { ReportsPeriod } from "@/lib/relatorios/relatorios-policy";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const period: ReportsPeriod = { endDate: "2026-08-31", referenceDate: "2026-08-14", startDate: "2026-08-01" };
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const LOAN_ID = "00000000-0000-4000-8000-000000000010";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000011";
const PAYMENT_ID = "00000000-0000-4000-8000-000000000012";

function config(): BffConfig {
  return { backendUrl: "http://backend.relatorios.invalid", origin: "http://frontend.relatorios.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, whatsapp: { numero: null, pareada: false }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
}

async function cookieStore(selected: BffConfig) {
  const encrypted = await sealSession(session, selected, NOW);
  return { get(name: string) { return name === sessionCookieName(selected) ? { value: encrypted } : undefined; } };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

function payload(pathname: string) {
  if (pathname.endsWith("/resumo")) return { carteira_id: WALLET_ID, data_referencia: period.referenceDate, operacoes_ativas: 2, operacoes_quitadas: 1, acertos_pendentes: 1, tenant_id: TENANT_ID, total_operacoes: 3, principal_a_receber: "40.00", total_realizado: "10.00" };
  if (pathname.endsWith("/vencimentos")) return { carteira_id: WALLET_ID, data_referencia: period.referenceDate, itens: [{ acerto_em: "2026-08-10", devedor_id: DEBTOR_ID, dia_de_acerto: 10, dias_sem_pagamento: 4, emprestimo_id: LOAN_ID, principal_original: "10.00", situacao: "acerto_pendente" }], tenant_id: TENANT_ID, total: 1 };
  if (pathname.endsWith("/pagamentos")) return { carteira_id: WALLET_ID, fim: period.endDate, inicio: period.startDate, operacoes_quitadas: [LOAN_ID], pagamentos: [{ emprestimo_id: LOAN_ID, estado: "confirmado", pagamento_id: PAYMENT_ID, recebido_em: "2026-08-12", valor_recebido: "10.00" }], tenant_id: TENANT_ID, total_realizado: "10.00" };
  return { carteira_id: WALLET_ID, fim: period.endDate, inicio: period.startDate, itens: [{ acertos: 1, data: "2026-08-12", pagamento_ids: [PAYMENT_ID], realizado: "10.00" }], tenant_id: TENANT_ID };
}

describe("loader server-only de Relatorios", () => {
  it("inicia os quatro GETs oficiais e usa somente a Carteira do contexto", async () => {
    const selected = config();
    const seen: URL[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.get("X-Correlation-ID")).toBeTruthy();
      expect(request.headers.get("Idempotency-Key")).toBeNull();
      expect(request.cache).toBe("no-store");
      return Response.json(payload(url.pathname), { headers: { "X-Correlation-ID": "corr-relatorios" } });
    });
    const loads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, backend));
    await Promise.all([loads.summary, loads.dueDates, loads.payments, loads.cashFlow]);
    expect(backend).toHaveBeenCalledTimes(4);
    expect(seen.map((url) => url.pathname).sort()).toEqual([
      `/credit/carteiras/${WALLET_ID}/relatorios/fluxo`,
      `/credit/carteiras/${WALLET_ID}/relatorios/pagamentos`,
      `/credit/carteiras/${WALLET_ID}/relatorios/resumo`,
      `/credit/carteiras/${WALLET_ID}/relatorios/vencimentos`,
    ]);
    expect(seen.every((url) => url.searchParams.get("data_referencia") === period.referenceDate || (url.searchParams.get("inicio") === period.startDate && url.searchParams.get("fim") === period.endDate))).toBe(true);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const loads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.*", "Relatorios.operacionais.ler"]), period, dependencies(selected, backend));
    await expect(loads.summary).resolves.toEqual({ kind: "denied" });
    await expect(loads.dueDates).resolves.toEqual({ kind: "denied" });
    await expect(loads.payments).resolves.toEqual({ kind: "denied" });
    await expect(loads.cashFlow).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita resposta 200 de outro Tenant, Carteira ou periodo", async () => {
    const selected = config();
    const crossWallet: FetchLike = async (request) => Response.json({ ...payload(new URL(request.url).pathname), carteira_id: "00000000-0000-4000-8000-000000000099" });
    const loads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, crossWallet));
    await expect(loads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const wrongPeriod: FetchLike = async (request) => Response.json({ ...payload(new URL(request.url).pathname), inicio: "2026-07-01" });
    const periodLoads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, wrongPeriod));
    await expect(periodLoads.payments).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mantem estados contratuais seguros e correlation sem vazar detalhe backend", async () => {
    for (const [status, expectedCode] of [[400, "periodo_invalido"], [401, "sessao_expirada"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const backend: FetchLike = async () => Response.json({ codigo: "interno", mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } });
      const loads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, backend));
      const result = await loads.summary;
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.codigo).toBe(expectedCode);
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("aceita somente 200 e rejeita payload incompleto ou data impossivel", async () => {
    const selected = config();
    const created: FetchLike = async (request) => Response.json(payload(new URL(request.url).pathname), { status: 201 });
    const createdLoads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, created));
    await expect(createdLoads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const incomplete: FetchLike = async (request) => Response.json({ ...payload(new URL(request.url).pathname), principal_a_receber: undefined });
    const incompleteLoads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, incomplete));
    await expect(incompleteLoads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const impossibleDate: FetchLike = async (request) => Response.json({ ...payload(new URL(request.url).pathname), data_referencia: "2026-02-30" });
    const impossibleLoads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, impossibleDate));
    await expect(impossibleLoads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mapeia timeout por secao sem transformar permissao ausente em chamada", async () => {
    const selected = config();
    const backend: FetchLike = async (request) => new Promise((_, reject) => request.signal.addEventListener("abort", () => reject(request.signal.reason), { once: true }));
    const loads = await beginReportsLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, backend, 5));
    await expect(loads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 504, codigo: "timeout_backend" } });
  });
});
