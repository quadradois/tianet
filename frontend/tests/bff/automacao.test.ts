import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  activateTemplate,
  approveTemplate,
  beginAutomacaoLoads,
  cancelJob,
  createTemplate,
  reconcileNotification,
  retryJob,
} from "@/lib/bff/automacao.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const JOB_ID = "00000000-0000-4000-8000-000000000081";
const NOTIFICATION_ID = "00000000-0000-4000-8000-000000000082";
const TEMPLATE_ID = "00000000-0000-4000-8000-000000000083";
const REMINDER_ID = "00000000-0000-4000-8000-000000000084";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.automacao.invalid", origin: "http://frontend.automacao.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
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
    delete: vi.fn(),
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

function job(carteira_id = WALLET_ID) {
  return { cancelamento_solicitado: false, carteira_id, correlation_id: "corr-job", estado: "agendado", executar_em: "2026-08-14T15:00:00Z", id: JOB_ID, max_tentativas: 3, origem_id: REMINDER_ID, origem_tipo: "lembrete", proxima_execucao_em: null, tentativas: 0, tipo: "notificacao" };
}

function notification(carteira_id = WALLET_ID) {
  return { carteira_id, codigo_resultado: null, estado: "resultado_desconhecido", id: NOTIFICATION_ID, job_id: JOB_ID, lembrete_id: REMINDER_ID, provider_message_id: "provider-ok", resultado_em: null };
}

function template() {
  return { aprovado_em: null, ativado_em: null, codigo: "cobranca-lembrete", estado: "rascunho", hash_conteudo: "hash-template", id: TEMPLATE_ID, versao: 1 };
}

function page<T>(items: readonly T[]) {
  return { items, page: 1, pages: 1, size: 20, total: items.length };
}

function form(values: Record<string, string>) {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

const allPermissions = ["automacao.job.consultar", "automacao.job.cancelar", "automacao.job.retry", "notificacao.consultar", "notificacao.template.gerir", "notificacao.conciliar"];

describe("BFF Automacao", () => {
  it("consulta jobs, notificacoes e templates com Carteira propria e sem Idempotency-Key", async () => {
    const selected = config();
    const seen: Array<[string, string | null, boolean]> = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push([url.pathname, url.searchParams.get("carteira_id"), request.headers.has("Idempotency-Key")]);
      expect(request.headers.get("Authorization")).toBe("Bearer access-sensitive");
      if (url.pathname === "/credit/automacao/jobs") return Response.json(page([job()]), { headers: { "X-Correlation-ID": "corr-auto" } });
      if (url.pathname === `/credit/automacao/jobs/${JOB_ID}`) return Response.json(job(), { headers: { "X-Correlation-ID": "corr-auto" } });
      if (url.pathname === "/credit/notificacoes") return Response.json(page([notification()]), { headers: { "X-Correlation-ID": "corr-auto" } });
      if (url.pathname === `/credit/notificacoes/${NOTIFICATION_ID}`) return Response.json(notification(), { headers: { "X-Correlation-ID": "corr-auto" } });
      return Response.json(page([template()]), { headers: { "X-Correlation-ID": "corr-auto" } });
    });
    const loads = await beginAutomacaoLoads(await cookieStore(selected), context(allPermissions), { jobId: JOB_ID, notificationId: NOTIFICATION_ID, page: 1, size: 20 }, dependencies(selected, backend));
    await Promise.all([loads.job, loads.jobs, loads.notification, loads.notifications, loads.templates]);
    expect(seen.map(([path, wallet, idem]) => `${path}|${wallet ?? ""}|${String(idem)}`).toSorted()).toEqual([
      `/credit/automacao/jobs/${JOB_ID}||false`,
      `/credit/automacao/jobs|${WALLET_ID}|false`,
      `/credit/notificacoes/${NOTIFICATION_ID}||false`,
      `/credit/notificacoes|${WALLET_ID}|false`,
      "/credit/notificacoes/templates||false",
    ].toSorted());
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const loads = await beginAutomacaoLoads(await cookieStore(selected), context(["automacao.*", "notificacao.*"]), { jobId: JOB_ID, notificationId: NOTIFICATION_ID, page: 1, size: 20 }, dependencies(selected, backend));
    await expect(loads.jobs).resolves.toEqual({ kind: "denied" });
    await expect(loads.notifications).resolves.toEqual({ kind: "denied" });
    await expect(loads.templates).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita payload 2xx incompleto ou de outra Carteira", async () => {
    const selected = config();
    const missing = await beginAutomacaoLoads(await cookieStore(selected), context(["automacao.job.consultar"]), { jobId: null, notificationId: null, page: 1, size: 20 }, dependencies(selected, async () => Response.json(page([{ ...job(), correlation_id: undefined }]))));
    await expect(missing.jobs).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await beginAutomacaoLoads(await cookieStore(selected), context(["notificacao.consultar"]), { jobId: null, notificationId: null, page: 1, size: 20 }, dependencies(selected, async () => Response.json(page([notification(OTHER_WALLET)]))));
    await expect(cross.notifications).resolves.toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mapeia 400, 401, 403, 404, 409, 422 e 500 sem repassar mensagem bruta", async () => {
    for (const status of [400, 401, 403, 404, 409, 422, 500] as const) {
      const selected = config();
      const loads = await beginAutomacaoLoads(await cookieStore(selected), context(["automacao.job.consultar"]), { jobId: JOB_ID, notificationId: null, page: 1, size: 20 }, dependencies(selected, async () => Response.json({ codigo: "interno", mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      const result = await loads.job;
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        if (status === 401) expect(result.problem.correlationId).toMatch(/^[A-Za-z0-9._:-]{1,128}$/);
        else expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("executa comandos de job e template sem Idempotency-Key inventada", async () => {
    const selected = config();
    const seen: Array<[string, boolean]> = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      seen.push([url.pathname, request.headers.has("Idempotency-Key")]);
      if (url.pathname.includes("/jobs/")) return Response.json(job(), { status: 202 });
      return Response.json(template(), { status: url.pathname === "/credit/notificacoes/templates" ? 201 : 200 });
    };
    const cookie = await cookieStore(selected);
    const ctx = context(["automacao.job.cancelar", "automacao.job.retry", "notificacao.template.gerir"]);
    await expect(cancelJob(cookie, ctx, form({ job_id: JOB_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(retryJob(cookie, ctx, form({ job_id: JOB_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(createTemplate(cookie, ctx, form({ codigo: "cobranca", versao: "1", assunto: "Aviso", corpo: "Corpo" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(approveTemplate(cookie, ctx, form({ template_id: TEMPLATE_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    await expect(activateTemplate(cookie, ctx, form({ template_id: TEMPLATE_ID }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(seen).toEqual([
      [`/credit/automacao/jobs/${JOB_ID}/cancelar`, false],
      [`/credit/automacao/jobs/${JOB_ID}/retry`, false],
      ["/credit/notificacoes/templates", false],
      [`/credit/notificacoes/templates/${TEMPLATE_ID}/aprovar`, false],
      [`/credit/notificacoes/templates/${TEMPLATE_ID}/ativar`, false],
    ]);
  });

  it("envia Idempotency-Key apenas na conciliacao de notificacao", async () => {
    const selected = config();
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      expect(url.pathname).toBe(`/credit/notificacoes/${NOTIFICATION_ID}/conciliar`);
      expect(request.headers.get("Idempotency-Key")).toBe("idem-conciliar");
      return Response.json(notification(), { headers: { "X-Correlation-ID": "corr-conciliar" } });
    };
    await expect(reconcileNotification(await cookieStore(selected), context(["notificacao.conciliar"]), form({ idempotency_key: "idem-conciliar", motivo: "Conferencia manual", notification_id: NOTIFICATION_ID, provider_message_id: "provider-ok" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "success", correlationId: "corr-conciliar" });
  });

  it("rejeita comando local invalido sem chamar backend", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(reconcileNotification(await cookieStore(selected), context(["notificacao.conciliar"]), form({ idempotency_key: "chave invalida", motivo: "ok", notification_id: NOTIFICATION_ID, provider_message_id: "provider" }), dependencies(selected, backend))).resolves.toMatchObject({ kind: "problem", status: 400 });
    expect(backend).not.toHaveBeenCalled();
  });
});
