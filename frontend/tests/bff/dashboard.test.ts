import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { beginDashboardLoads } from "@/lib/bff/dashboard.server";
import type { DashboardPeriod } from "@/lib/dashboard/dashboard-policy";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-13T12:00:00.000Z");
const period: DashboardPeriod = { referenceDate: "2026-08-13", agendaStart: "2026-08-13T00:00:00.000-03:00", agendaEnd: "2026-08-13T23:59:59.999-03:00" };
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const AGENDA_ID = "00000000-0000-4000-8000-000000000007";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000008";
const CASE_ID = "00000000-0000-4000-8000-000000000009";

function config(): BffConfig {
  return { backendUrl: "http://backend.dashboard.invalid", origin: "http://frontend.dashboard.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-13T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-20T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

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
  if (pathname.endsWith("/resumo")) return { carteira_id: WALLET_ID, data_referencia: "2026-08-13", operacoes_ativas: 2, operacoes_quitadas: 1, acertos_pendentes: 1, tenant_id: TENANT_ID, total_operacoes: 3, principal_a_receber: "40.00", total_realizado: "10.00" };
  if (pathname.endsWith("/vencimentos")) return { carteira_id: WALLET_ID, data_referencia: "2026-08-13", itens: [], tenant_id: TENANT_ID, total: 0 };
  if (pathname === "/credit/agenda") return { compromissos: [], lembretes: [], total: 0 };
  return { items: [], total: 0 };
}

describe("loader server-only do Dashboard", () => {
  it("inicia os cinco GETs autorizados em paralelo e usa somente a Carteira da sessao", async () => {
    const selected = config();
    const seen: URL[] = [];
    const release: Array<() => void> = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url); seen.push(url);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      expect(request.headers.get("X-Correlation-ID")).toBeTruthy();
      expect(request.cache).toBe("no-store");
      await new Promise<void>((resolve) => { release.push(resolve); if (release.length === 5) release.forEach((item) => item()); });
      return Response.json(payload(url.pathname), { headers: { "X-Correlation-ID": "corr-backend" } });
    });
    const loads = await beginDashboardLoads(await cookieStore(selected), context(["relatorios.operacionais.ler", "agenda.ler", "cobranca.caso.ler"]), period, dependencies(selected, backend));
    await Promise.all([loads.summary, loads.dueDates, loads.agenda, loads.collection, loads.fluxo]);
    expect(backend).toHaveBeenCalledTimes(5);
    expect(seen.map((url) => url.pathname).sort()).toEqual(["/credit/agenda", `/credit/carteiras/${WALLET_ID}/relatorios/fluxo`, `/credit/carteiras/${WALLET_ID}/relatorios/resumo`, `/credit/carteiras/${WALLET_ID}/relatorios/vencimentos`, "/credit/cobrancas/casos"]);
    for (const url of seen) expect(url.searchParams.get("carteira_id") ?? WALLET_ID).toBe(WALLET_ID);
    expect(seen.filter((url) => url.pathname.includes("relatorios") && !url.pathname.endsWith("/fluxo")).every((url) => url.searchParams.get("data_referencia") === "2026-08-13")).toBe(true);
    const fluxo = seen.find((url) => url.pathname.endsWith("/relatorios/fluxo"));
    expect(fluxo?.searchParams.get("inicio")).toBeTruthy();
    expect(fluxo?.searchParams.get("fim")).toBeTruthy();
    const agenda = seen.find((url) => url.pathname === "/credit/agenda");
    expect(agenda?.searchParams.get("janela_inicio")).toBe(period.agendaStart);
    expect(agenda?.searchParams.get("janela_fim")).toBe(period.agendaEnd);
    expect(agenda?.searchParams.get("incluir_lembretes")).toBe("true");
  });

  it("nao chama endpoint sem a permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const loads = await beginDashboardLoads(await cookieStore(selected), context(["agenda.*", "Relatorios.operacionais.ler"]), period, dependencies(selected, backend));
    await expect(loads.summary).resolves.toEqual({ kind: "denied" });
    await expect(loads.dueDates).resolves.toEqual({ kind: "denied" });
    await expect(loads.agenda).resolves.toEqual({ kind: "denied" });
    await expect(loads.collection).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita resposta 200 de outro Tenant ou Carteira sem fabricar vazio", async () => {
    const selected = config();
    const backend: FetchLike = async (request) => {
      const value = payload(new URL(request.url).pathname);
      return Response.json({ ...value, tenant_id: "tenant-cross", carteira_id: "wallet-cross" });
    };
    const loads = await beginDashboardLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, backend));
    await expect(loads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    await expect(loads.dueDates).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const wrongDate: FetchLike = async (request) => Response.json({ ...payload(new URL(request.url).pathname), data_referencia: "2026-08-12" });
    const dateLoads = await beginDashboardLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, wrongDate));
    await expect(dateLoads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mantem estados contratuais seguros e correlation sem revelar detalhe", async () => {
    for (const [status, expectedCode] of [[400, "periodo_invalido"], [401, "sessao_expirada"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const backend: FetchLike = async () => Response.json({ codigo: "interno", mensagem: "stack secreta" }, { status, headers: { "X-Correlation-ID": "corr-safe" } });
      const loads = await beginDashboardLoads(await cookieStore(selected), context(["agenda.ler"]), period, dependencies(selected, backend));
      const result = await loads.agenda;
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        expect(result.problem.codigo).toBe(expectedCode);
        expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.mensagem).not.toContain("stack secreta");
      }
    }
  });

  it("aceita somente 200 e rejeita payload estruturalmente incompleto", async () => {
    const selected = config();
    const created: FetchLike = async (request) => Response.json(payload(new URL(request.url).pathname), { status: 201 });
    const createdLoads = await beginDashboardLoads(await cookieStore(selected), context(["relatorios.operacionais.ler"]), period, dependencies(selected, created));
    await expect(createdLoads.summary).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const incomplete: FetchLike = async (request) => {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/credit/agenda") return Response.json({ total: 1, compromissos: [{ agenda_item_id: AGENDA_ID, carteira_id: WALLET_ID, devedor_id: DEBTOR_ID, estado: "aberto", previsto_para: "2026-08-13T12:00:00-03:00", tenant_id: TENANT_ID, titulo: "Contato", usuario_solicitante_id: USER_ID }], lembretes: [] });
      return Response.json({ total: 1, items: [{ carteira_id: WALLET_ID, caso_id: CASE_ID, criado_em: "2026-08-13T10:00:00Z", devedor_id: DEBTOR_ID, estado: "pendente", origem: "manual", tenant_id: TENANT_ID, titulo: "Caso", total_pendente: "10.00" }] });
    };
    const incompleteLoads = await beginDashboardLoads(await cookieStore(selected), context(["agenda.ler", "cobranca.caso.ler"]), period, dependencies(selected, incomplete));
    await expect(incompleteLoads.agenda).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    await expect(incompleteLoads.collection).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const invalidFormat: FetchLike = async (request) => {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/credit/agenda") return Response.json({ total: 1, compromissos: [{ agenda_item_id: AGENDA_ID, atualizado_em: null, carteira_id: WALLET_ID, devedor_id: DEBTOR_ID, emprestimo_id: null, estado: "inventado", previsto_para: "2026-08-13T12:00:00-03:00", tenant_id: TENANT_ID, titulo: "Contato", usuario_solicitante_id: USER_ID }], lembretes: [] });
      return Response.json({ total: 1.5, items: [] });
    };
    const invalidFormatLoads = await beginDashboardLoads(await cookieStore(selected), context(["agenda.ler", "cobranca.caso.ler"]), period, dependencies(selected, invalidFormat));
    await expect(invalidFormatLoads.agenda).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    await expect(invalidFormatLoads.collection).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });

    const agendaItem = { agenda_item_id: AGENDA_ID, atualizado_em: null, carteira_id: WALLET_ID, devedor_id: DEBTOR_ID, emprestimo_id: null, estado: "aberto", previsto_para: "2026-08-13T12:00:00-03:00", tenant_id: TENANT_ID, titulo: "Contato", usuario_solicitante_id: USER_ID };
    const reminder = { agenda_item_id: AGENDA_ID, carteira_id: WALLET_ID, enviado_por_usuario_id: USER_ID, estado: "enviado", horario: "2026-08-13T12:05:00-03:00", lembrete_id: "00000000-0000-4000-8000-000000000010", mensagem: "Lembrete", tenant_id: TENANT_ID };
    for (const agendaBody of [
      { total: 1, compromissos: [{ ...agendaItem, previsto_para: "2026-02-30T12:00:00Z" }], lembretes: [] },
      { total: 1, compromissos: [{ ...agendaItem, atualizado_em: "2026-02-30T12:00:00Z" }], lembretes: [] },
      { total: 1, compromissos: [], lembretes: [{ ...reminder, horario: "2026-02-30T12:00:00Z" }] },
    ]) {
      const invalidAgendaLoads = await beginDashboardLoads(await cookieStore(selected), context(["agenda.ler"]), period, dependencies(selected, async () => Response.json(agendaBody)));
      await expect(invalidAgendaLoads.agenda).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    }
    const invalidCreatedAtLoads = await beginDashboardLoads(await cookieStore(selected), context(["cobranca.caso.ler"]), period, dependencies(selected, async () => Response.json({ total: 1, items: [{ carteira_id: WALLET_ID, caso_id: CASE_ID, criado_em: "2026-02-30T12:00:00Z", devedor_id: DEBTOR_ID, emprestimo_id: null, estado: "pendente", origem: "manual", tenant_id: TENANT_ID, titulo: "Caso", total_pendente: "10.00" }] })));
    await expect(invalidCreatedAtLoads.collection).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mapeia timeout por secao sem afetar estado de permissao das demais", async () => {
    const selected = config();
    const backend: FetchLike = async (request) => new Promise((_, reject) => request.signal.addEventListener("abort", () => reject(request.signal.reason), { once: true }));
    const loads = await beginDashboardLoads(await cookieStore(selected), context(["cobranca.caso.ler"]), period, dependencies(selected, backend, 5));
    await expect(loads.collection).resolves.toMatchObject({ kind: "problem", problem: { status: 504, codigo: "timeout_backend" } });
    await expect(loads.summary).resolves.toEqual({ kind: "denied" });
  });
});
