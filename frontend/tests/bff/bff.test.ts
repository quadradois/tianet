import { randomBytes } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, it, vi } from "vitest";

import {
  apiProblemFromResponse,
  ApiProblem,
  correlationId,
  createAuthenticatedFetch,
  createCookieAuthenticatedFetch,
  handleLogin,
  handleLogout,
  idempotencyKey,
  RefreshCoordinator,
  type AuthenticatedContext,
  type BffDependencies,
  type FetchLike,
} from "@/lib/bff/backend.server";
import {
  SESSION_COOKIE_NAME,
  sealSession,
  type BffConfig,
  type CookieStore,
  type SessionCookieOptions,
  type SessionData,
  unsealSession,
} from "@/lib/bff/session.server";

const NOW = new Date("2026-08-13T12:00:00.000Z");
const CORRELATION = "corr-frontend-bff-288";
const APP_ORIGIN = "http://frontend.bff.invalid";

function config(): BffConfig {
  return {
    backendUrl: "http://backend.bff.invalid",
    origin: "http://frontend.bff.invalid",
    production: true,
    currentKeyId: "current",
    currentKey: randomBytes(32),
  };
}

function session(overrides: Partial<SessionData> = {}): SessionData {
  return {
    accessToken: "expired-access-token",
    accessTokenExpiresAt: "2026-08-13T11:59:00.000Z",
    refreshToken: "refresh-sensitive-token",
    refreshTokenExpiresAt: "2026-08-20T12:00:00.000Z",
    tenantId: "75a5d893-50bd-4d9c-ae61-27a6450f2c90",
    userId: "301cd6e7-26cc-4b31-a4d0-8c329f441dbc",
    ...overrides,
  };
}

function dependencies(fetch: FetchLike, overrides: Partial<BffDependencies> = {}): BffDependencies {
  return { config: config(), fetch, now: () => NOW, timeoutMs: 1_000, ...overrides };
}

function mutationRequest(path: string, body?: unknown, headers: HeadersInit = {}): Request {
  return new Request(`http://frontend.bff.invalid${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: "http://frontend.bff.invalid",
      "Sec-Fetch-Site": "same-origin",
      "X-Correlation-ID": CORRELATION,
      "X-CSRF-Protection": "1",
      ...headers,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

class MemoryCookies implements CookieStore {
  readonly values = new Map<string, string>();
  readonly options = new Map<string, SessionCookieOptions>();

  get(name: string): { value: string } | undefined {
    const value = this.values.get(name);
    return value === undefined ? undefined : { value };
  }

  set(name: string, value: string, options: SessionCookieOptions): void {
    this.values.set(name, value);
    this.options.set(name, options);
  }
}

function json(data: unknown, status = 200, correlation = CORRELATION): Response {
  return Response.json(data, { status, headers: { "X-Correlation-ID": correlation } });
}

function responseWithCorrelation(data: unknown, status: number, correlation?: string): Response {
  return Response.json(data, {
    status,
    ...(correlation === undefined ? {} : { headers: { "X-Correlation-ID": correlation } }),
  });
}

const RESPONSE_CORRELATION_CASES = [
  { label: "valido", backendCorrelation: "corr-backend-valid-288", expected: "corr-backend-valid-288" },
  { label: "invalido", backendCorrelation: "correlation invalido", expected: CORRELATION },
  { label: "ausente", backendCorrelation: undefined, expected: CORRELATION },
] as const;

describe("Route Handlers BFF", () => {
  it("login usa shape OpenAPI, cifra tokens e retorna JSON sanitizado", async () => {
    const cookies = new MemoryCookies();
    const backend = vi.fn<FetchLike>(async (request) => {
      expect(request.url).toBe("http://backend.bff.invalid/auth/login");
      expect(request.redirect).toBe("error");
      expect(request.headers.get("X-Correlation-ID")).toBe(CORRELATION);
      expect(await request.json()).toEqual({ identificador_institucional: "ACME", email: "user@example.test", segredo: "secret" });
      return json({
        access_token: "access-sensitive-token",
        access_token_expira_em: "2026-08-13T12:15:00.000Z",
        refresh_token: "refresh-sensitive-token",
        refresh_token_expira_em: "2026-08-20T12:00:00.000Z",
        tenant_id: session().tenantId,
        token_type: "bearer",
        usuario_id: session().userId,
      });
    });
    const deps = dependencies(backend);
    const response = await handleLogin(
      mutationRequest("/api/auth/login", { identificador_institucional: "ACME", email: "user@example.test", segredo: "secret" }),
      cookies,
      deps,
    );
    expect(response.status).toBe(200);
    const browserBody = JSON.stringify(await response.json());
    expect(browserBody).not.toContain("access-sensitive-token");
    expect(browserBody).not.toContain("refresh-sensitive-token");
    expect(cookies.options.get(SESSION_COOKIE_NAME)).toMatchObject({ httpOnly: true, sameSite: "lax", secure: true, path: "/" });
    const encrypted = cookies.values.get(SESSION_COOKIE_NAME);
    expect(encrypted).toBeDefined();
    if (!encrypted) throw new Error("cookie ausente");
    await expect(unsealSession(encrypted, deps.config, NOW)).resolves.toMatchObject({ accessToken: "access-sensitive-token" });
  });

  it.each(RESPONSE_CORRELATION_CASES)(
    "login 200 com correlation backend $label preserva a selecao no header e corpo publico",
    async ({ backendCorrelation, expected }) => {
      const backend = vi.fn<FetchLike>(async () => responseWithCorrelation({
        access_token: "access-sensitive-token",
        access_token_expira_em: "2026-08-13T12:15:00.000Z",
        refresh_token: "refresh-sensitive-token",
        refresh_token_expira_em: "2026-08-20T12:00:00.000Z",
        tenant_id: session().tenantId,
        token_type: "bearer",
        usuario_id: session().userId,
      }, 200, backendCorrelation));

      const response = await handleLogin(
        mutationRequest("/api/auth/login", { identificador_institucional: "ACME", email: "user@example.test", segredo: "secret" }),
        new MemoryCookies(),
        dependencies(backend),
      );

      expect(response.headers.get("X-Correlation-ID")).toBe(expected);
      expect(await response.json()).toEqual({ authenticated: true, correlationId: expected });
    },
  );

  it("rejeita Origin/CSRF e payload inesperado antes do backend", async () => {
    const backend = vi.fn<FetchLike>();
    const cookies = new MemoryCookies();
    const missingOrigin = mutationRequest("/api/auth/login", { identificador_institucional: "ACME", email: "user@example.test", segredo: "secret" });
    missingOrigin.headers.delete("Origin");
    expect((await handleLogin(missingOrigin, cookies, dependencies(backend))).status).toBe(403);
    expect((await handleLogin(mutationRequest("/api/auth/login", { extra: true }), cookies, dependencies(backend))).status).toBe(400);
    expect(backend).not.toHaveBeenCalled();
  });

  it("limita o payload de login antes do backend", async () => {
    const backend = vi.fn<FetchLike>();
    let pulls = 0;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        pulls += 1;
        controller.enqueue(new TextEncoder().encode("x".repeat(9_000)));
        if (pulls >= 10) controller.close();
      },
    });
    const init: RequestInit & { duplex: "half" } = {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        Origin: APP_ORIGIN,
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Protection": "1",
      },
      body: stream,
      duplex: "half",
    };
    const response = await handleLogin(
      new Request(`${APP_ORIGIN}/api/auth/login`, init),
      new MemoryCookies(),
      dependencies(backend),
    );
    expect(response.status).toBe(413);
    expect(pulls).toBeLessThan(10);
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita media type parecido com JSON", async () => {
    const backend = vi.fn<FetchLike>();
    const request = mutationRequest("/api/auth/login", { identificador_institucional: "ACME", email: "user@example.test", segredo: "secret" });
    request.headers.set("Content-Type", "application/jsonp");
    expect((await handleLogin(request, new MemoryCookies(), dependencies(backend))).status).toBe(400);
    expect(backend).not.toHaveBeenCalled();
  });

  it("interrompe leitura lenta do payload de login", async () => {
    const backend = vi.fn<FetchLike>();
    const cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({ cancel });
    const init: RequestInit & { duplex: "half" } = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: APP_ORIGIN,
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Protection": "1",
      },
      body: stream,
      duplex: "half",
    };
    const response = await handleLogin(
      new Request(`${APP_ORIGIN}/api/auth/login`, init),
      new MemoryCookies(),
      dependencies(backend, { timeoutMs: 10 }),
    );
    expect(response.status).toBe(408);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejeita payload de login previamente cancelado sem aguardar timeout", async () => {
    const backend = vi.fn<FetchLike>();
    const controller = new AbortController();
    controller.abort(new Error("caller stopped"));
    const stream = new ReadableStream<Uint8Array>();
    const init: RequestInit & { duplex: "half" } = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: APP_ORIGIN,
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Protection": "1",
      },
      body: stream,
      duplex: "half",
      signal: controller.signal,
    };
    const response = await handleLogin(
      new Request(`${APP_ORIGIN}/api/auth/login`, init),
      new MemoryCookies(),
      dependencies(backend, { timeoutMs: 1_000 }),
    );
    expect(response.status).toBe(499);
    expect(backend).not.toHaveBeenCalled();
  });

  it("logout hostil nao consegue apagar a sessao local", async () => {
    const settings = config();
    const cookies = new MemoryCookies();
    const encrypted = await sealSession(session(), settings, NOW);
    cookies.values.set(SESSION_COOKIE_NAME, encrypted);
    const hostile = mutationRequest("/api/auth/logout", undefined, { Origin: "http://attacker.invalid" });
    const response = await handleLogout(hostile, cookies, dependencies(vi.fn<FetchLike>(), { config: settings }));
    expect(response.status).toBe(403);
    expect(cookies.values.get(SESSION_COOKIE_NAME)).toBe(encrypted);
  });

  it("logout envia AuthRefreshRequest e sempre remove o cookie, inclusive em 5xx", async () => {
    const settings = config();
    const cookies = new MemoryCookies();
    cookies.values.set(SESSION_COOKIE_NAME, await sealSession(session(), settings, NOW));
    const backend = vi.fn<FetchLike>(async (request) => {
      expect(request.url).toBe("http://backend.bff.invalid/auth/logout");
      expect(request.redirect).toBe("error");
      expect(await request.json()).toEqual({ refresh_token: "refresh-sensitive-token" });
      return json({ codigo: "erro_tecnico", mensagem: "internal secret detail" }, 500);
    });
    const response = await handleLogout(mutationRequest("/api/auth/logout"), cookies, dependencies(backend, { config: settings }));
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ status: 500, codigo: "erro_tecnico", mensagem: "Serviço temporariamente indisponível.", correlationId: CORRELATION });
    expect(cookies.values.get(SESSION_COOKIE_NAME)).toBe("");
    expect(cookies.options.get(SESSION_COOKIE_NAME)?.maxAge).toBe(0);
  });

  it.each(RESPONSE_CORRELATION_CASES)(
    "logout 2xx com correlation backend $label preserva a selecao no header",
    async ({ backendCorrelation, expected }) => {
      const settings = config();
      const cookies = new MemoryCookies();
      cookies.values.set(SESSION_COOKIE_NAME, await sealSession(session(), settings, NOW));
      const backend = vi.fn<FetchLike>(async () => new Response(null, {
        status: 204,
        ...(backendCorrelation === undefined ? {} : { headers: { "X-Correlation-ID": backendCorrelation } }),
      }));

      const response = await handleLogout(
        mutationRequest("/api/auth/logout"),
        cookies,
        dependencies(backend, { config: settings }),
      );

      expect(response.status).toBe(204);
      expect(response.headers.get("X-Correlation-ID")).toBe(expected);
    },
  );
});

describe("transporte autenticado", () => {
  it("carrega e persiste a sessao somente pelo cookie cifrado", async () => {
    const settings = config();
    const cookies = new MemoryCookies();
    cookies.values.set(SESSION_COOKIE_NAME, await sealSession(session({ accessToken: "valid-access" }), settings, NOW));
    const backend = vi.fn<FetchLike>(async (request) => {
      expect(request.headers.get("Authorization")).toBe("Bearer valid-access");
      return json({ ok: true });
    });
    const authenticated = await createCookieAuthenticatedFetch(cookies, dependencies(backend, { config: settings }));
    expect((await authenticated(new Request("http://backend.bff.invalid/protected"))).status).toBe(200);
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("faz single-flight real por sessao/processo e preserva correlation/idempotency/payload", async () => {
    const originalSession = session();
    const saved: SessionData[] = [];
    const cleared = vi.fn(async () => undefined);
    const context: AuthenticatedContext = { session: originalSession, saveSession: async (value) => { saved.push(value); }, clearSession: cleared };
    const refreshCoordinator = new RefreshCoordinator();
    let refreshCount = 0;
    const observedCommands: Request[] = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        expect(request.redirect).toBe("error");
        refreshCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 20));
        return json({
          access_token: "renewed-access-token",
          access_token_expira_em: "2026-08-13T12:15:00.000Z",
          tenant_id: originalSession.tenantId,
          token_type: "bearer",
          usuario_id: originalSession.userId,
        });
      }
      observedCommands.push(request.clone());
      return request.headers.get("Authorization") === "Bearer renewed-access-token"
        ? json({ ok: true })
        : json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    });
    const authenticated = createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator }));
    const command = () => authenticated(new Request("http://backend.bff.invalid/credit/command", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "same-intention", "X-Correlation-ID": CORRELATION },
      body: JSON.stringify({ command: "technical-fixture" }),
    }));
    const responses = await Promise.all([command(), command(), command(), command()]);

    expect(responses.every((response) => response.status === 200)).toBe(true);
    expect(refreshCount).toBe(1);
    expect(refreshCoordinator.size).toBe(0);
    expect(saved).toHaveLength(4);
    const replays = observedCommands.filter((request) => request.headers.get("Authorization") === "Bearer renewed-access-token");
    expect(replays).toHaveLength(4);
    for (const replay of replays) {
      expect(replay.headers.get("Idempotency-Key")).toBe("same-intention");
      expect(replay.headers.get("X-Correlation-ID")).toBe(CORRELATION);
      expect(await replay.text()).toBe(JSON.stringify({ command: "technical-fixture" }));
    }
    expect(cleared).not.toHaveBeenCalled();
  });

  it("nao repete mutacao sem Idempotency-Key apos refresh", async () => {
    const originalSession = session();
    let protectedCalls = 0;
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession: async () => undefined };
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: originalSession.tenantId, token_type: "bearer", usuario_id: originalSession.userId });
      }
      protectedCalls += 1;
      return json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    };
    const response = await createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator() }))(
      new Request("http://backend.bff.invalid/credit/unkeyed", { method: "POST", body: "same-body", headers: { "Content-Type": "text/plain" } }),
    );
    expect(response.status).toBe(401);
    expect(protectedCalls).toBe(1);
  });

  it("nao repete mutacao com Idempotency-Key invalida", async () => {
    const originalSession = session();
    let protectedCalls = 0;
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession: async () => undefined };
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: originalSession.tenantId, token_type: "bearer", usuario_id: originalSession.userId });
      }
      protectedCalls += 1;
      return json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    };
    const response = await createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator() }))(
      new Request("http://backend.bff.invalid/credit/unkeyed", { method: "POST", headers: { "Idempotency-Key": "invalid key with spaces" } }),
    );
    expect(response.status).toBe(401);
    expect(protectedCalls).toBe(1);
  });

  it("recusa destino diferente antes de anexar Bearer", async () => {
    const backend = vi.fn<FetchLike>();
    const context: AuthenticatedContext = { session: session(), saveSession: async () => undefined, clearSession: async () => undefined };
    await expect(createAuthenticatedFetch(context, dependencies(backend))(new Request("http://attacker.invalid/collect")))
      .rejects.toMatchObject({ status: 500, codigo: "destino_backend_invalido" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("respeita AbortSignal do chamador antes e durante o refresh", async () => {
    const originalSession = session();
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession: async () => undefined };
    const backend = vi.fn<FetchLike>(async (request) => {
      if (!request.url.endsWith("/auth/refresh")) return json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
      return new Promise((_resolve, reject) => request.signal.addEventListener("abort", () => reject(new DOMException("cancelled", "AbortError"))));
    });
    const authenticated = createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator(), timeoutMs: 5_000 }));
    const alreadyAborted = new AbortController();
    alreadyAborted.abort();
    await expect(authenticated(new Request("http://backend.bff.invalid/protected", { signal: alreadyAborted.signal })))
      .rejects.toMatchObject({ status: 499, codigo: "request_cancelado" });
    expect(backend).not.toHaveBeenCalled();

    const duringRefresh = new AbortController();
    const pending = authenticated(new Request("http://backend.bff.invalid/protected", { signal: duringRefresh.signal }));
    await vi.waitFor(() => expect(backend).toHaveBeenCalledTimes(2));
    duringRefresh.abort();
    await expect(pending).rejects.toMatchObject({ status: 499, codigo: "request_cancelado" });
  });

  it("isola cancelamento do lider e mantém o seguidor vivo", async () => {
    const coordinator = new RefreshCoordinator(10, 1_000);
    let refreshCount = 0;
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        refreshCount += 1;
        await new Promise((resolveDelay) => setTimeout(resolveDelay, 80));
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: session().tenantId, token_type: "bearer", usuario_id: session().userId });
      }
      return request.headers.get("Authorization") === "Bearer renewed"
        ? json({ ok: true })
        : json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    };
    const leaderSave = vi.fn(async () => undefined);
    const followerSave = vi.fn(async () => undefined);
    const leader = createAuthenticatedFetch({ session: session(), saveSession: leaderSave, clearSession: async () => undefined }, dependencies(backend, { refreshCoordinator: coordinator }));
    const follower = createAuthenticatedFetch({ session: session(), saveSession: followerSave, clearSession: async () => undefined }, dependencies(backend, { refreshCoordinator: coordinator }));
    const leaderAbort = new AbortController();
    const leaderPending = leader(new Request("http://backend.bff.invalid/one", { signal: leaderAbort.signal }));
    await vi.waitFor(() => expect(refreshCount).toBe(1));
    const followerPending = follower(new Request("http://backend.bff.invalid/two"));
    leaderAbort.abort(new Error("leader-cancelled"));
    await expect(leaderPending).rejects.toMatchObject({ status: 499, codigo: "request_cancelado" });
    await expect(followerPending).resolves.toMatchObject({ status: 200 });
    expect(refreshCount).toBe(1);
    expect(leaderSave).not.toHaveBeenCalled();
    expect(followerSave).toHaveBeenCalledTimes(1);
  });

  it("cancela waiter imediatamente sem derrubar o refresh compartilhado", async () => {
    const coordinator = new RefreshCoordinator(10, 1_000);
    let refreshCount = 0;
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        refreshCount += 1;
        await new Promise((resolveDelay) => setTimeout(resolveDelay, 100));
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: session().tenantId, token_type: "bearer", usuario_id: session().userId });
      }
      return request.headers.get("Authorization") === "Bearer renewed" ? json({ ok: true }) : json({}, 401);
    };
    const owner = createAuthenticatedFetch({ session: session(), saveSession: async () => undefined, clearSession: async () => undefined }, dependencies(backend, { refreshCoordinator: coordinator }));
    const waiterSave = vi.fn(async () => undefined);
    const waiter = createAuthenticatedFetch({ session: session(), saveSession: waiterSave, clearSession: async () => undefined }, dependencies(backend, { refreshCoordinator: coordinator }));
    const ownerPending = owner(new Request("http://backend.bff.invalid/owner"));
    await vi.waitFor(() => expect(refreshCount).toBe(1));
    const waiterAbort = new AbortController();
    const startedAt = performance.now();
    const waiterPending = waiter(new Request("http://backend.bff.invalid/waiter", { signal: waiterAbort.signal }));
    waiterAbort.abort(new Error("waiter-cancelled"));
    await expect(waiterPending).rejects.toMatchObject({ status: 499, codigo: "request_cancelado" });
    expect(performance.now() - startedAt).toBeLessThan(80);
    await expect(ownerPending).resolves.toMatchObject({ status: 200 });
    expect(waiterSave).not.toHaveBeenCalled();
    expect(refreshCount).toBe(1);
  });

  it("logout vence refresh em voo e impede ressurreicao do cookie no processo", async () => {
    const settings = config();
    const coordinator = new RefreshCoordinator(10, 1_000);
    const cookies = new MemoryCookies();
    cookies.values.set(SESSION_COOKIE_NAME, await sealSession(session(), settings, NOW));
    let releaseRefresh: (() => void) | undefined;
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        await new Promise<void>((resolveRelease, reject) => {
          releaseRefresh = resolveRelease;
          request.signal.addEventListener("abort", () => reject(new DOMException("revoked", "AbortError")), { once: true });
        });
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: session().tenantId, token_type: "bearer", usuario_id: session().userId });
      }
      if (request.url.endsWith("/auth/logout")) return json({ status: "encerrada" });
      return json({}, 401);
    };
    const deps = dependencies(backend, { config: settings, refreshCoordinator: coordinator });
    const authenticated = await createCookieAuthenticatedFetch(cookies, deps, CORRELATION);
    const protectedPending = authenticated(new Request("http://backend.bff.invalid/protected"));
    await vi.waitFor(() => expect(releaseRefresh).toBeTypeOf("function"));
    expect((await handleLogout(mutationRequest("/api/auth/logout"), cookies, deps)).status).toBe(204);
    releaseRefresh?.();
    await expect(protectedPending).rejects.toMatchObject({ status: 401, codigo: "sessao_invalida" });
    expect(cookies.values.get(SESSION_COOKIE_NAME)).toBe("");
  });

  it("revalida logout depois de cifrar e antes de persistir o cookie", async () => {
    const settings = config();
    const coordinator = new RefreshCoordinator(10, 1_000);
    const cookies = new MemoryCookies();
    cookies.values.set(SESSION_COOKIE_NAME, await sealSession(session(), settings, NOW));
    let releaseSeal: (() => void) | undefined;
    let sealStarted = false;
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        return json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: session().tenantId, token_type: "bearer", usuario_id: session().userId });
      }
      return json({}, 401);
    };
    const deps = dependencies(backend, {
      config: settings,
      refreshCoordinator: coordinator,
      seal: async (value, sealConfig, sealNow) => {
        sealStarted = true;
        await new Promise<void>((resolveSeal) => { releaseSeal = resolveSeal; });
        return sealSession(value, sealConfig, sealNow);
      },
    });
    const authenticated = await createCookieAuthenticatedFetch(cookies, deps, CORRELATION);
    const pending = authenticated(new Request("http://backend.bff.invalid/protected"));
    await vi.waitFor(() => expect(sealStarted).toBe(true));
    coordinator.revoke(session().refreshToken, session().refreshTokenExpiresAt);
    cookies.set(SESSION_COOKIE_NAME, "", { httpOnly: true, maxAge: 0, path: "/", priority: "high", sameSite: "lax", secure: true });
    releaseSeal?.();
    await expect(pending).rejects.toMatchObject({ status: 401, codigo: "sessao_invalida" });
    expect(cookies.values.get(SESSION_COOKIE_NAME)).toBe("");
  });

  it("remove cookies e headers browser antes de chamar o backend", async () => {
    const backend = vi.fn<FetchLike>(async (request) => {
      for (const name of ["Cookie", "Origin", "Host", "Forwarded", "Via", "Content-Length", "Sec-Fetch-Site", "X-CSRF-Protection", "Connection", "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto"]) expect(request.headers.has(name)).toBe(false);
      return json({ ok: true });
    });
    const context: AuthenticatedContext = { session: session({ accessToken: "valid" }), saveSession: async () => undefined, clearSession: async () => undefined };
    await createAuthenticatedFetch(context, dependencies(backend))(new Request("http://backend.bff.invalid/protected", {
      headers: { Cookie: "secret-cookie", Origin: "http://frontend.bff.invalid", Host: "attacker.invalid", Forwarded: "for=attacker", Via: "evil", "Content-Length": "0", "Sec-Fetch-Site": "same-origin", "X-CSRF-Protection": "1", Connection: "keep-alive", "X-Forwarded-For": "203.0.113.1", "X-Forwarded-Host": "attacker.invalid", "X-Forwarded-Proto": "https" },
    }));
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("recusa operacao publica no transporte autenticado", async () => {
    const backend = vi.fn<FetchLike>();
    const context: AuthenticatedContext = { session: session(), saveSession: async () => undefined, clearSession: async () => undefined };
    await expect(createAuthenticatedFetch(context, dependencies(backend))(new Request("http://backend.bff.invalid/auth/login")))
      .rejects.toMatchObject({ status: 500, codigo: "transporte_inadequado" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("falha de refresh limpa todas as chamadas concorrentes sem loop", async () => {
    const originalSession = session();
    const clearSession = vi.fn(async () => undefined);
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession };
    let refreshCount = 0;
    const backend: FetchLike = async (request) => {
      if (request.url.endsWith("/auth/refresh")) {
        refreshCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 20));
      }
      return json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    };
    const authenticated = createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator() }));
    const calls = await Promise.allSettled([
      authenticated(new Request("http://backend.bff.invalid/a")),
      authenticated(new Request("http://backend.bff.invalid/b")),
      authenticated(new Request("http://backend.bff.invalid/c")),
    ]);
    expect(calls.every((item) => item.status === "rejected" && item.reason instanceof ApiProblem)).toBe(true);
    expect(refreshCount).toBe(1);
    expect(clearSession).toHaveBeenCalledTimes(3);
  });

  it("refresh com identidade divergente encerra a sessao", async () => {
    const originalSession = session();
    const clearSession = vi.fn(async () => undefined);
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession };
    const backend: FetchLike = async (request) => request.url.endsWith("/auth/refresh")
      ? json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: "outro-tenant", token_type: "bearer", usuario_id: originalSession.userId })
      : json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401);
    await expect(createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator() }))(
      new Request("http://backend.bff.invalid/protected"),
    )).rejects.toMatchObject({ status: 401, codigo: "sessao_invalida" });
    expect(clearSession).toHaveBeenCalledTimes(1);
  });

  it("coordenador limita entradas e limpa falhas em finally", async () => {
    const coordinator = new RefreshCoordinator(1);
    let rejectFirst: ((reason: Error) => void) | undefined;
    const first = coordinator.run("refresh-a", new AbortController().signal, () => new Promise<SessionData>((_resolve, reject) => { rejectFirst = reject; }));
    await expect(coordinator.run("refresh-b", new AbortController().signal, async () => session())).rejects.toMatchObject({ status: 503, codigo: "refresh_saturado" });
    rejectFirst?.(new Error("falha-controlada-sem-token"));
    await expect(first).rejects.toThrow("falha-controlada-sem-token");
    expect(coordinator.size).toBe(0);
  });

  it("nao faz refresh para 403/404/409/422/5xx", async () => {
    for (const status of [403, 404, 409, 422, 500]) {
      const backend = vi.fn<FetchLike>(async () => json({ codigo: "erro", mensagem: "mensagem" }, status));
      const context: AuthenticatedContext = { session: session(), saveSession: async () => undefined, clearSession: async () => undefined };
      const response = await createAuthenticatedFetch(context, dependencies(backend))(new Request("http://backend.bff.invalid/protected"));
      expect(response.status).toBe(status);
      expect(backend).toHaveBeenCalledTimes(1);
    }
  });

  it("segundo 401 limpa a sessao sem terceiro request", async () => {
    const originalSession = session();
    const clearSession = vi.fn(async () => undefined);
    const context: AuthenticatedContext = { session: originalSession, saveSession: async () => undefined, clearSession };
    const backend = vi.fn<FetchLike>(async (request) => request.url.endsWith("/auth/refresh")
      ? json({ access_token: "renewed", access_token_expira_em: "2026-08-13T12:15:00.000Z", tenant_id: originalSession.tenantId, token_type: "bearer", usuario_id: originalSession.userId })
      : json({ codigo: "autenticacao_recusada", mensagem: "recusada" }, 401));
    const response = await createAuthenticatedFetch(context, dependencies(backend, { refreshCoordinator: new RefreshCoordinator() }))(
      new Request("http://backend.bff.invalid/protected"),
    );
    expect(response.status).toBe(401);
    expect(backend).toHaveBeenCalledTimes(3);
    expect(clearSession).toHaveBeenCalledTimes(1);
  });
});

describe("contratos tecnicos", () => {
  it("confirma 5 operacoes publicas e 102 protegidas no snapshot governado", async () => {
    const snapshotPath = resolve(process.cwd(), "..", "docs", "governance", "contracts", "openapi", "frontend-mvp-backend-openapi.json");
    const snapshot: unknown = JSON.parse(await readFile(snapshotPath, "utf8"));
    if (typeof snapshot !== "object" || snapshot === null || !("paths" in snapshot)) throw new Error("snapshot invalido");
    const paths = snapshot.paths;
    if (typeof paths !== "object" || paths === null) throw new Error("paths invalidos");
    const operations = Object.values(paths).flatMap((item) => {
      if (typeof item !== "object" || item === null) return [];
      return Object.values(item).filter((operation) => typeof operation === "object" && operation !== null && "responses" in operation);
    });
    const protectedCount = operations.filter((operation) => "security" in operation && Array.isArray(operation.security) && operation.security.length > 0).length;
    expect(operations).toHaveLength(107);
    expect(protectedCount).toBe(102);
    expect(operations.length - protectedCount).toBe(5);
  });
  it("normaliza correlation e idempotency sem confundir os identificadores", () => {
    expect(correlationId(CORRELATION)).toBe(CORRELATION);
    expect(correlationId("bad value")).toMatch(/^[0-9a-f-]{36}$/);
    expect(correlationId("x".repeat(129))).toMatch(/^[0-9a-f-]{36}$/);
    expect(idempotencyKey(false, "provided")).toBeUndefined();
    expect(idempotencyKey(true, "provided")).toBe("provided");
    expect(idempotencyKey(true)).toMatch(/^[0-9a-f-]{36}$/);
    expect(() => idempotencyKey(true, "invalid key with spaces")).toThrow(ApiProblem);
  });

  it.each([400, 401, 403, 404, 409, 422, 500, 503])("normaliza status %i e mantem 404/5xx neutros", async (status) => {
    const response = json({ codigo: `codigo-${status}`, mensagem: `detalhe-interno-${status}` }, status, "corr-backend");
    const problem = await apiProblemFromResponse(response, CORRELATION);
    expect(problem.status).toBe(status);
    expect(problem.correlationId).toBe("corr-backend");
    if (status === 404 || status >= 500) expect(problem.message).not.toContain("detalhe-interno");
    else expect(problem.message).toBe(`detalhe-interno-${status}`);
  });

  it("usa correlation outbound quando o backend devolve header invalido", async () => {
    const problem = await apiProblemFromResponse(json({ codigo: "conflito", mensagem: "conflito" }, 409, "invalid correlation with spaces"), CORRELATION);
    expect(problem.correlationId).toBe(CORRELATION);
  });

  it("timeout e resposta malformada nao vazam causa ou payload", async () => {
    const context: AuthenticatedContext = { session: session(), saveSession: async () => undefined, clearSession: async () => undefined };
    const never: FetchLike = (request) => new Promise((_resolve, reject) => {
      request.signal.addEventListener("abort", () => reject(new DOMException("secret-timeout-cause", "AbortError")));
    });
    await expect(createAuthenticatedFetch(context, dependencies(never, { timeoutMs: 5 }))(new Request("http://backend.bff.invalid/protected")))
      .rejects.toMatchObject({ status: 504, codigo: "timeout_backend", correlationId: expect.any(String) });
    const malformed = await apiProblemFromResponse(new Response("internal stack", { status: 500 }), CORRELATION);
    expect(malformed.message).toBe("Serviço temporariamente indisponível.");
  });
});
