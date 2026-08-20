import { randomBytes } from "node:crypto";

import { describe, expect, it } from "vitest";

import {
  assertTrustedMutation,
  expiredSessionCookieOptions,
  readBffConfig,
  sealSession,
  SESSION_COOKIE_NAME,
  DEVELOPMENT_SESSION_COOKIE_NAME,
  sessionCookieOptions,
  sessionCookieName,
  SessionError,
  type BffConfig,
  type SessionData,
  unsealSession,
} from "@/lib/bff/session.server";

const NOW = new Date("2026-08-13T12:00:00.000Z");

function key(): string {
  return randomBytes(32).toString("base64url");
}

function config(overrides: Partial<BffConfig> = {}): BffConfig {
  return {
    backendUrl: "http://127.0.0.1:8000",
    origin: "http://127.0.0.1:3000",
    production: true,
    loginTenantIdentifier: "ACME",
    currentKeyId: "current",
    currentKey: randomBytes(32),
    ...overrides,
  };
}

function session(overrides: Partial<SessionData> = {}): SessionData {
  return {
    accessToken: "access-sensitive-token",
    accessTokenExpiresAt: "2026-08-13T12:15:00.000Z",
    refreshToken: "refresh-sensitive-token",
    refreshTokenExpiresAt: "2026-08-20T12:00:00.000Z",
    tenantId: "75a5d893-50bd-4d9c-ae61-27a6450f2c90",
    userId: "301cd6e7-26cc-4b31-a4d0-8c329f441dbc",
    ...overrides,
  };
}

function trustedRequest(overrides: HeadersInit = {}): Request {
  return new Request("http://127.0.0.1:3000/api/auth/login", {
    method: "POST",
    headers: {
      Origin: "http://127.0.0.1:3000",
      "Sec-Fetch-Site": "same-origin",
      "X-CSRF-Protection": "1",
      ...overrides,
    },
  });
}

describe("sessao JWE server-only", () => {
  it("cifra, autentica e usa nonce aleatorio sem expor tokens", async () => {
    const settings = config();
    const first = await sealSession(session(), settings, NOW);
    const second = await sealSession(session(), settings, NOW);

    expect(first).not.toBe(second);
    expect(first).not.toContain("access-sensitive-token");
    expect(first).not.toContain("refresh-sensitive-token");
    expect(first.length).toBeLessThan(4096);
    await expect(unsealSession(first, settings, NOW)).resolves.toEqual(session());
  });

  it("rejeita adulteracao, chave incorreta e expiracao", async () => {
    const settings = config();
    const encrypted = await sealSession(session(), settings, NOW);
    const parts = encrypted.split(".");
    const ciphertext = parts[3];
    if (!ciphertext) throw new Error("ciphertext JWE ausente");
    const index = Math.floor(ciphertext.length / 2);
    const replacement = ciphertext[index] === "a" ? "b" : "a";
    parts[3] = `${ciphertext.slice(0, index)}${replacement}${ciphertext.slice(index + 1)}`;
    await expect(unsealSession(parts.join("."), settings, NOW)).rejects.toMatchObject({ code: "sessao_invalida" });
    await expect(unsealSession(encrypted, config(), NOW)).rejects.toMatchObject({ code: "sessao_invalida" });
    await expect(unsealSession(encrypted, settings, new Date("2026-08-21T12:00:00.000Z"))).rejects.toMatchObject({ code: "sessao_invalida" });
  });

  it("aceita chave anterior apenas durante rotacao por kid", async () => {
    const previous = config({ currentKeyId: "previous" });
    const encrypted = await sealSession(session(), previous, NOW);
    const rotated = config({ previousKeyId: previous.currentKeyId, previousKey: previous.currentKey });
    await expect(unsealSession(encrypted, rotated, NOW)).resolves.toEqual(session());
  });

  it("governa flags, duracao e remocao do cookie", () => {
    const settings = config();
    expect(SESSION_COOKIE_NAME).toBe("__Host-emprestimo-session");
    expect(sessionCookieName(settings)).toBe(SESSION_COOKIE_NAME);
    expect(sessionCookieName(config({ production: false }))).toBe(DEVELOPMENT_SESSION_COOKIE_NAME);
    expect(sessionCookieOptions(session(), settings, NOW)).toEqual({
      httpOnly: true,
      maxAge: 604800,
      path: "/",
      priority: "high",
      sameSite: "lax",
      secure: true,
    });
    expect(expiredSessionCookieOptions(settings)).toEqual({ httpOnly: true, maxAge: 0, path: "/", priority: "high", sameSite: "lax", secure: true });
  });

  it("falha fechado para segredo, URL e rotacao invalidos", () => {
    const base: NodeJS.ProcessEnv = {
      NODE_ENV: "production",
      FRONTEND_BACKEND_URL: "https://api.example.test",
      FRONTEND_ORIGIN: "https://app.example.test",
      FRONTEND_SESSION_KEY_ID: "current",
      FRONTEND_SESSION_KEY: key(),
    };
    expect(readBffConfig(base)).toMatchObject({ loginTenantIdentifier: "ACME", production: true, origin: "https://app.example.test" });
    expect(readBffConfig({ ...base, FRONTEND_LOGIN_TENANT_IDENTIFICADOR: "JORNADAS" })).toMatchObject({ loginTenantIdentifier: "JORNADAS" });
    expect(() => readBffConfig({ ...base, FRONTEND_SESSION_KEY: undefined })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_SESSION_KEY: "short" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_SESSION_KEY: `${key()}!` })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_BACKEND_URL: "http://api.example.test" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_BACKEND_URL: "ftp://localhost" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_BACKEND_URL: "https://api.example.test/v1" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_BACKEND_URL: "https://user:password@api.example.test" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_SESSION_PREVIOUS_KEY_ID: "old" })).toThrow(SessionError);
    expect(() => readBffConfig({ ...base, FRONTEND_SESSION_PREVIOUS_KEY_ID: "current", FRONTEND_SESSION_PREVIOUS_KEY: key() })).toThrow(SessionError);
  });

  it("rejeita Origin/CSRF ausentes, hostis e same-site", () => {
    const settings = config();
    expect(() => assertTrustedMutation(trustedRequest(), settings)).not.toThrow();
    for (const request of [
      new Request("http://127.0.0.1:3000", { method: "POST" }),
      trustedRequest({ Origin: "null" }),
      trustedRequest({ Origin: "http://127.0.0.1:3000.attacker.invalid" }),
      trustedRequest({ "X-CSRF-Protection": "0" }),
      trustedRequest({ "Sec-Fetch-Site": "same-site" }),
      trustedRequest({ "Sec-Fetch-Site": "cross-site" }),
    ]) {
      expect(() => assertTrustedMutation(request, settings)).toThrow(SessionError);
    }
  });
});
