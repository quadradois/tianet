import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import type { BffDependencies, FetchLike } from "@/lib/bff/backend.server";
import { beginOpenAILogin, disconnectOpenAI, readOpenAIConnection, refreshOpenAIDiagnostic } from "@/lib/bff/openai.server";
import { sealSession, SESSION_COOKIE_NAME, type BffConfig, type CookieStore, type SessionCookieOptions } from "@/lib/bff/session.server";
import type { OperationalContext } from "@/lib/bff/context.server";

const NOW = new Date("2026-09-09T12:00:00.000Z");
const config: BffConfig = { backendUrl: "http://backend.test", origin: "http://frontend.test", production: true, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
const context: OperationalContext = {
  carteira_padrao: { id: "wallet", nome: "Carteira" },
  perfil: { id: "profile", nome: "Administrador" },
  permissoes: ["openai.conexao.ler", "openai.conexao.gerir"],
  tenant: { id: "tenant", identificador_institucional: "ACME", nome: "ACME" },
  usuario: { id: "user", nome: "Operador", email: "operador@example.test" },
  whatsapp: { alerta_queda_ativa: false, numero: null, pareada: false, queda_detectada_em: null },
};

class MemoryCookies implements CookieStore {
  values = new Map<string, string>();
  get(name: string) { const value = this.values.get(name); return value === undefined ? undefined : { value }; }
  set(name: string, value: string, options: SessionCookieOptions) { void options; this.values.set(name, value); }
}

async function setup(fetch: FetchLike) {
  const cookies = new MemoryCookies();
  cookies.values.set(SESSION_COOKIE_NAME, await sealSession({ accessToken: "access", accessTokenExpiresAt: "2099-01-01T00:00:00Z", refreshToken: "refresh", refreshTokenExpiresAt: "2099-01-02T00:00:00Z", tenantId: "tenant", userId: "user" }, config, NOW));
  const dependencies: BffDependencies = { config, fetch, now: () => NOW };
  return { cookies, dependencies };
}

function json(body: unknown, status = 200) { return Response.json(body, { status, headers: { "X-Correlation-ID": "corr-openai" } }); }

describe("BFF OpenAI", () => {
  it("lê somente o snapshot de conexão e valida schema fechado", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ enabled: true, processAvailable: true, accountConnected: false, planType: null, state: "DESCONECTADO", usageSummary: null }));
    const { cookies, dependencies } = await setup(backend);
    await expect(readOpenAIConnection(cookies, context, dependencies)).resolves.toMatchObject({ kind: "ready", connection: { state: "DESCONECTADO" } });
    const connectionRequest = backend.mock.calls[0]?.[0];
    if (!connectionRequest) throw new Error("requisição ausente");
    expect(new URL(connectionRequest.url).pathname).toBe("/platform/openai/conexao");

    backend.mockImplementationOnce(async () => json({ enabled: true, processAvailable: true, accountConnected: false, planType: null, state: "DESCONECTADO", usageSummary: null, token: "vazamento" }));
    await expect(readOpenAIConnection(cookies, context, dependencies)).resolves.toMatchObject({ kind: "problem", status: 502 });
  });

  it("aceita apenas desafio vigente no host oficial", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ verificationUrl: "https://auth.openai.com/codex/device", userCode: "ABCD-EFGH", expiresAt: "2099-01-01T00:10:00Z" }));
    const { cookies, dependencies } = await setup(backend);
    await expect(beginOpenAILogin(cookies, context, dependencies)).resolves.toMatchObject({ kind: "login", challenge: { userCode: "ABCD-EFGH" } });
    backend.mockImplementationOnce(async () => json({ verificationUrl: "https://openai.example.test/phishing", userCode: "ABCD", expiresAt: "2099-01-01T00:10:00Z" }));
    await expect(beginOpenAILogin(cookies, context, dependencies)).resolves.toMatchObject({ kind: "problem", status: 502 });
  });

  it("diagnóstico é explícito e valida modelos e janelas", async () => {
    const diagnostic = { state: "CONECTADO", observedAt: "2026-09-09T12:00:00Z", accountStatus: "ok", accountConnected: true, planType: "plus", modelsStatus: "ok", models: [{ id: "gpt-test", displayName: "GPT Test", default: true }], rateLimitsStatus: "ok", rateLimits: [{ limitId: "codex", planType: "plus", primary: { usedPercent: 20, windowDurationMinutes: 300, resetsAt: 1790000000 }, secondary: null }] };
    const backend = vi.fn<FetchLike>(async () => json(diagnostic));
    const { cookies, dependencies } = await setup(backend);
    await expect(refreshOpenAIDiagnostic(cookies, context, dependencies)).resolves.toMatchObject({ kind: "diagnostic", diagnostic: { planType: "plus" } });
    const diagnosticRequest = backend.mock.calls[0]?.[0];
    if (!diagnosticRequest) throw new Error("requisição ausente");
    expect(new URL(diagnosticRequest.url).pathname).toBe("/platform/openai/diagnostico");
  });

  it("logout envia idempotência e comunica escopo local", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ state: "DESCONECTADO", localLogout: true, remoteRevocationVerified: false }));
    const { cookies, dependencies } = await setup(backend);
    await expect(disconnectOpenAI(cookies, context, dependencies)).resolves.toMatchObject({ kind: "logout", logout: { localLogout: true, remoteRevocationVerified: false } });
    const logoutRequest = backend.mock.calls[0]?.[0];
    if (!logoutRequest) throw new Error("requisição ausente");
    expect(logoutRequest.headers.get("Idempotency-Key")).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("nega leitura e gestão sem permissões exatas sem chamar backend", async () => {
    const backend = vi.fn<FetchLike>();
    const { cookies, dependencies } = await setup(backend);
    const denied = { ...context, permissoes: ["openai.conexao.*"] } as OperationalContext;
    await expect(readOpenAIConnection(cookies, denied, dependencies)).resolves.toMatchObject({ kind: "problem", status: 403 });
    await expect(beginOpenAILogin(cookies, denied, dependencies)).resolves.toMatchObject({ kind: "problem", status: 403 });
    expect(backend).not.toHaveBeenCalled();
  });
});
