import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import type { BffDependencies, FetchLike } from "@/lib/bff/backend.server";
import { readAgentInbox } from "@/lib/bff/agent.server";
import { sealSession, SESSION_COOKIE_NAME, type BffConfig, type CookieStore, type SessionCookieOptions } from "@/lib/bff/session.server";
import type { OperationalContext } from "@/lib/bff/context.server";

const NOW = new Date("2026-09-19T12:00:00.000Z");
const config: BffConfig = { backendUrl: "http://backend.test", origin: "http://frontend.test", production: true, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
const context: OperationalContext = {
  carteira_padrao: { id: "wallet", nome: "Carteira" },
  perfil: { id: "profile", nome: "Administrador" },
  permissoes: ["agent.inbox.ler"],
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

function json(body: unknown, status = 200) { return Response.json(body, { status, headers: { "X-Correlation-ID": "corr-agent" } }); }

const INBOX = {
  total: 2,
  operadora: 1,
  devedor: 0,
  pre_cadastro: 1,
  recentes: [
    { provider_input_id: "a", remetente_normalizado: "556299999999", classe: "operadora", texto: "ola", estado: "recebida", recebido_em: "2026-09-19T12:00:00.000Z" },
    { provider_input_id: "b", remetente_normalizado: "556288888888", classe: "pre_cadastro", texto: null, estado: "recebida", recebido_em: "2026-09-19T11:00:00.000Z" },
  ],
};

describe("BFF Agent", () => {
  it("lê resumo e recentes e valida schema fechado", async () => {
    const backend = vi.fn<FetchLike>(async () => json(INBOX));
    const { cookies, dependencies } = await setup(backend);
    await expect(readAgentInbox(cookies, context, dependencies)).resolves.toMatchObject({ kind: "ready", inbox: { total: 2, operadora: 1 } });
    const inboxRequest = backend.mock.calls[0]?.[0];
    if (!inboxRequest) throw new Error("requisição ausente");
    expect(new URL(inboxRequest.url).pathname).toBe("/platform/agent/inbox");

    backend.mockImplementationOnce(async () => json({ ...INBOX, total: "dois" }));
    await expect(readAgentInbox(cookies, context, dependencies)).resolves.toMatchObject({ kind: "problem", status: 502 });
  });

  it("nega leitura sem permissão exata sem chamar backend", async () => {
    const backend = vi.fn<FetchLike>();
    const { cookies, dependencies } = await setup(backend);
    const denied = { ...context, permissoes: ["agent.inbox.*"] } as OperationalContext;
    await expect(readAgentInbox(cookies, denied, dependencies)).resolves.toMatchObject({ kind: "problem", status: 403 });
    expect(backend).not.toHaveBeenCalled();
  });
});
