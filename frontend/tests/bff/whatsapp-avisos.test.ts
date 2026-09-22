import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import type { BffDependencies, FetchLike } from "@/lib/bff/backend.server";
import { readNumeroAvisos, saveNumeroAvisos } from "@/lib/bff/whatsapp.server";
import { sealSession, SESSION_COOKIE_NAME, type BffConfig, type CookieStore, type SessionCookieOptions } from "@/lib/bff/session.server";
import type { OperationalContext } from "@/lib/bff/context.server";

const NOW = new Date("2026-09-20T12:00:00.000Z");
const config: BffConfig = { backendUrl: "http://backend.test", origin: "http://frontend.test", production: true, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
const base: OperationalContext = {
  carteira_padrao: { id: "wallet", nome: "Carteira" },
  perfil: { id: "profile", nome: "Administrador" },
  permissoes: ["whatsapp.conexao.ler", "whatsapp.conexao.gerir"],
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

function json(body: unknown, status = 200) { return Response.json(body, { status, headers: { "X-Correlation-ID": "corr-avisos" } }); }

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) data.set(key, value);
  return data;
}

describe("BFF numero que recebe os avisos", () => {
  it("lê o número cadastrado (ou nulo) e valida o schema", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ numero: "5511999998888" }));
    const { cookies, dependencies } = await setup(backend);
    await expect(readNumeroAvisos(cookies, base, dependencies)).resolves.toEqual({ kind: "ready", numero: "5511999998888" });
    const request = backend.mock.calls[0]?.[0];
    if (!request) throw new Error("requisição ausente");
    expect(new URL(request.url).pathname).toBe("/platform/whatsapp/avisos");

    backend.mockImplementationOnce(async () => json({ numero: 12 }));
    await expect(readNumeroAvisos(cookies, base, dependencies)).resolves.toMatchObject({ kind: "problem", status: 502 });
  });

  it("grava com Idempotency-Key vinda do formulário e devolve o número normalizado", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ numero: "5511999998888" }));
    const { cookies, dependencies } = await setup(backend);

    const result = await saveNumeroAvisos(cookies, base, dependencies, form({ numero: "+55 (11) 99999-8888", idempotency_key: "11111111-1111-4111-8111-111111111111" }));

    expect(result).toMatchObject({ kind: "success", numero: "5511999998888" });
    const request = backend.mock.calls[0]?.[0];
    if (!request) throw new Error("requisição ausente");
    expect(request.method).toBe("PUT");
    expect(new URL(request.url).pathname).toBe("/platform/whatsapp/avisos");
    expect(request.headers.get("Idempotency-Key")).toBe("11111111-1111-4111-8111-111111111111");
    await expect(request.json()).resolves.toEqual({ numero: "+55 (11) 99999-8888" });
  });

  it("nega gravação sem permissão de gerir, sem chamar o backend", async () => {
    const backend = vi.fn<FetchLike>();
    const { cookies, dependencies } = await setup(backend);
    const somenteLeitura = { ...base, permissoes: ["whatsapp.conexao.ler"] };

    const result = await saveNumeroAvisos(cookies, somenteLeitura, dependencies, form({ numero: "5511999998888", idempotency_key: "11111111-1111-4111-8111-111111111111" }));

    expect(result).toMatchObject({ kind: "problem", status: 403 });
    expect(backend).not.toHaveBeenCalled();
  });

  it("recusa numero curto antes de chamar o backend, com mensagem legivel", async () => {
    const backend = vi.fn<FetchLike>();
    const { cookies, dependencies } = await setup(backend);

    const result = await saveNumeroAvisos(cookies, base, dependencies, form({ numero: "123", idempotency_key: "11111111-1111-4111-8111-111111111111" }));

    expect(result).toMatchObject({ kind: "problem", status: 400, message: expect.stringContaining("10 a 15 digitos") });
    expect(backend).not.toHaveBeenCalled();
  });

  it("repassa 400 do backend como problema", async () => {
    const backend = vi.fn<FetchLike>(async () => json({ codigo: "payload_invalido", mensagem: "Payload, parametros ou headers invalidos" }, 400));
    const { cookies, dependencies } = await setup(backend);

    const result = await saveNumeroAvisos(cookies, base, dependencies, form({ numero: "5511999998888", idempotency_key: "11111111-1111-4111-8111-111111111111" }));

    expect(result).toMatchObject({ kind: "problem", status: 400 });
  });
});
