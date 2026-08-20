import "server-only";

import { createHash, randomUUID } from "node:crypto";

import type { components } from "@/lib/api/openapi.generated";
import { createBackendClient } from "@/lib/api/client.server";

import {
  assertTrustedMutation,
  expiredSessionCookieOptions,
  readBffConfig,
  sealSession,
  sessionCookieName,
  sessionCookieOptions,
  SessionError,
  type BffConfig,
  type CookieStore,
  type SessionData,
  unsealSession,
} from "./session.server";

type AuthLoginRequest = components["schemas"]["AuthLoginRequest"];
type AuthLoginResponse = components["schemas"]["AuthLoginResponse"];
type AuthRefreshResponse = components["schemas"]["AuthRefreshResponse"];
type ErroResponse = components["schemas"]["ErroResponse"];
type BrowserLoginRequest = Readonly<{
  email: string;
  segredo: string;
}>;

export type FetchLike = (request: Request) => Promise<Response>;

export type ApiProblemShape = Readonly<{
  status: number;
  codigo: string;
  mensagem: string;
  correlationId: string;
}>;

export class ApiProblem extends Error implements ApiProblemShape {
  readonly status: number;
  readonly codigo: string;
  readonly correlationId: string;

  constructor(problem: ApiProblemShape) {
    super(problem.mensagem);
    this.name = "ApiProblem";
    this.status = problem.status;
    this.codigo = problem.codigo;
    this.correlationId = problem.correlationId;
  }

  get mensagem(): string {
    return this.message;
  }

  toJSON(): ApiProblemShape {
    return { status: this.status, codigo: this.codigo, mensagem: this.message, correlationId: this.correlationId };
  }
}

export type BffDependencies = Readonly<{
  config: BffConfig;
  fetch: FetchLike;
  now?: () => Date;
  timeoutMs?: number;
  refreshCoordinator?: RefreshCoordinator;
  seal?: typeof sealSession;
}>;

export type AuthenticatedContext = Readonly<{
  session: SessionData;
  saveSession(session: SessionData): Promise<void>;
  clearSession(): Promise<void>;
}>;

const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const IDEMPOTENCY_PATTERN = /^[\x21-\x7E]{1,255}$/;
const SAFE_REPLAY_METHODS = new Set(["GET", "HEAD"]);
const PUBLIC_BACKEND_PATHS = new Set(["/auth/ativar", "/auth/login", "/auth/logout", "/auth/refresh", "/health"]);
const MAX_LOGIN_BODY_BYTES = 16_384;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isErroResponse(value: unknown): value is ErroResponse {
  return isRecord(value) && typeof value.codigo === "string" && typeof value.mensagem === "string";
}

function isBrowserLoginRequest(value: unknown): value is BrowserLoginRequest {
  if (!isRecord(value)) return false;
  const keys = Object.keys(value).sort().join(",");
  return keys === "email,segredo"
    && typeof value.email === "string"
    && typeof value.segredo === "string";
}

function isAuthLoginResponse(value: unknown): value is AuthLoginResponse {
  if (!isRecord(value)) return false;
  return [
    value.access_token,
    value.access_token_expira_em,
    value.refresh_token,
    value.refresh_token_expira_em,
    value.tenant_id,
    value.token_type,
    value.usuario_id,
  ].every((item) => typeof item === "string" && item.length > 0)
    && typeof value.token_type === "string"
    && value.token_type.toLowerCase() === "bearer";
}

function isAuthRefreshResponse(value: unknown): value is AuthRefreshResponse {
  if (!isRecord(value)) return false;
  return [
    value.access_token,
    value.access_token_expira_em,
    value.tenant_id,
    value.token_type,
    value.usuario_id,
  ].every((item) => typeof item === "string" && item.length > 0)
    && typeof value.token_type === "string"
    && value.token_type.toLowerCase() === "bearer";
}

export function correlationId(value?: string | null): string {
  return value && CORRELATION_PATTERN.test(value) ? value : randomUUID();
}

function responseCorrelationId(response: Response, fallbackCorrelationId: string): string {
  const receivedCorrelation = response.headers.get("X-Correlation-ID");
  return receivedCorrelation && CORRELATION_PATTERN.test(receivedCorrelation)
    ? receivedCorrelation
    : fallbackCorrelationId;
}

export function idempotencyKey(required: boolean, value?: string | null): string | undefined {
  if (!required) return undefined;
  if (value) {
    if (!IDEMPOTENCY_PATTERN.test(value)) {
      throw new ApiProblem({ status: 400, codigo: "idempotencia_invalida", mensagem: "Idempotency-Key inválida.", correlationId: randomUUID() });
    }
    return value;
  }
  return randomUUID();
}

function safeMessage(status: number): string {
  if (status === 404) return "Recurso não encontrado ou indisponível.";
  if (status >= 500) return "Serviço temporariamente indisponível.";
  return "A solicitação não pôde ser concluída.";
}

export async function apiProblemFromResponse(response: Response, fallbackCorrelationId: string): Promise<ApiProblem> {
  const selectedCorrelationId = responseCorrelationId(response, fallbackCorrelationId);
  let body: unknown;
  try {
    body = await response.clone().json();
  } catch {
    body = undefined;
  }
  if (response.status !== 404 && response.status < 500 && isErroResponse(body)) {
    return new ApiProblem({
      status: response.status,
      codigo: body.codigo,
      mensagem: body.mensagem,
      correlationId: selectedCorrelationId,
    });
  }
  return new ApiProblem({
    status: response.status,
    codigo: response.status === 404 ? "recurso_indisponivel" : "erro_tecnico",
    mensagem: safeMessage(response.status),
    correlationId: selectedCorrelationId,
  });
}

function problemResponse(problem: ApiProblem): Response {
  return Response.json(problem.toJSON(), {
    status: problem.status,
    headers: {
      "Cache-Control": "no-store, private",
      "X-Correlation-ID": problem.correlationId,
    },
  });
}

function sessionProblem(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 401,
    codigo: "sessao_invalida",
    mensagem: "Sessão ausente, inválida ou expirada.",
    correlationId: correlation,
  });
}

function securityProblem(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 403,
    codigo: "origem_recusada",
    mensagem: "Origem da solicitação recusada.",
    correlationId: correlation,
  });
}

function timeoutProblem(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 504,
    codigo: "timeout_backend",
    mensagem: "O serviço não respondeu no tempo esperado.",
    correlationId: correlation,
  });
}

function networkProblem(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 502,
    codigo: "backend_indisponivel",
    mensagem: "O serviço está temporariamente indisponível.",
    correlationId: correlation,
  });
}

function cancelledProblem(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 499,
    codigo: "request_cancelado",
    mensagem: "A solicitação foi cancelada.",
    correlationId: correlation,
  });
}

function now(dependencies: BffDependencies): Date {
  return dependencies.now ? dependencies.now() : new Date();
}

function deadline(dependencies: BffDependencies): { signal: AbortSignal; clear(): void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

function toSession(data: AuthLoginResponse): SessionData {
  return {
    accessToken: data.access_token,
    accessTokenExpiresAt: data.access_token_expira_em,
    refreshToken: data.refresh_token,
    refreshTokenExpiresAt: data.refresh_token_expira_em,
    tenantId: data.tenant_id,
    userId: data.usuario_id,
  };
}

function responseHeaders(correlation: string): HeadersInit {
  return { "Cache-Control": "no-store, private", "X-Correlation-ID": correlation, Vary: "Origin, Sec-Fetch-Site" };
}

async function readLoginBody(
  request: Request,
  correlation: string,
  dependencies: BffDependencies,
): Promise<unknown> {
  const declaredLength = request.headers.get("Content-Length");
  if (declaredLength && (!/^\d+$/.test(declaredLength) || Number(declaredLength) > MAX_LOGIN_BODY_BYTES)) {
    throw new ApiProblem({ status: 413, codigo: "payload_excedido", mensagem: "Payload excede o limite permitido.", correlationId: correlation });
  }
  if (!request.body) return undefined;
  const reader = request.body.getReader();
  const clock = deadline(dependencies);
  const signal = AbortSignal.any([request.signal, clock.signal]);
  const chunks: Uint8Array[] = [];
  let total = 0;
  let removeAbort: () => void = () => undefined;
  const aborted = new Promise<never>((_resolve, reject) => {
    const onAbort = () => reject(new DOMException("request aborted", "AbortError"));
    if (signal.aborted) {
      onAbort();
      return;
    }
    signal.addEventListener("abort", onAbort, { once: true });
    removeAbort = () => signal.removeEventListener("abort", onAbort);
  });
  try {
    while (true) {
      const part = await Promise.race([reader.read(), aborted]);
      if (part.done) break;
      total += part.value.byteLength;
      if (total > MAX_LOGIN_BODY_BYTES) {
        void reader.cancel("payload limit exceeded").catch(() => undefined);
        throw new ApiProblem({ status: 413, codigo: "payload_excedido", mensagem: "Payload excede o limite permitido.", correlationId: correlation });
      }
      chunks.push(part.value);
    }
  } catch (error) {
    if (error instanceof ApiProblem) throw error;
    void reader.cancel("payload read cancelled").catch(() => undefined);
    if (request.signal.aborted) throw cancelledProblem(correlation);
    if (clock.signal.aborted) {
      throw new ApiProblem({ status: 408, codigo: "payload_timeout", mensagem: "Tempo de leitura do payload excedido.", correlationId: correlation });
    }
    throw error;
  } finally {
    removeAbort();
    clock.clear();
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    return undefined;
  }
}

function isJsonContentType(value: string | null): boolean {
  if (!value) return false;
  const [mediaType, ...parameters] = value.toLowerCase().split(";").map((part) => part.trim());
  if (mediaType !== "application/json") return false;
  return parameters.every((parameter) => /^charset=(?:"?utf-8"?)$/.test(parameter));
}

function restrictedBackendFetch(dependencies: BffDependencies): FetchLike {
  return async (request) => {
    if (new URL(request.url).origin !== new URL(dependencies.config.backendUrl).origin) {
      throw new ApiProblem({
        status: 500,
        codigo: "destino_backend_invalido",
        mensagem: "Destino backend recusado.",
        correlationId: correlationId(request.headers.get("X-Correlation-ID")),
      });
    }
    return dependencies.fetch(new Request(request, { redirect: "error" }));
  };
}

export async function handleLogin(
  request: Request,
  cookies: CookieStore,
  dependencies: BffDependencies,
): Promise<Response> {
  const requestCorrelation = correlationId(request.headers.get("X-Correlation-ID"));
  try {
    try {
      assertTrustedMutation(request, dependencies.config);
    } catch {
      throw securityProblem(requestCorrelation);
    }
    if (!isJsonContentType(request.headers.get("Content-Type"))) {
      throw new ApiProblem({ status: 400, codigo: "payload_invalido", mensagem: "Payload JSON inválido.", correlationId: requestCorrelation });
    }
    const browserBody: unknown = await readLoginBody(request, requestCorrelation, dependencies);
    if (!isBrowserLoginRequest(browserBody)) {
      throw new ApiProblem({ status: 400, codigo: "payload_invalido", mensagem: "Payload de login inválido.", correlationId: requestCorrelation });
    }
    const body: AuthLoginRequest = {
      email: browserBody.email,
      identificador_institucional: dependencies.config.loginTenantIdentifier,
      segredo: browserBody.segredo,
    };
    const clock = deadline(dependencies);
    try {
      const client = createBackendClient(dependencies.config.backendUrl, { fetch: restrictedBackendFetch(dependencies) });
      const result = await client.POST("/auth/login", {
        body,
        headers: { "X-Correlation-ID": requestCorrelation },
        signal: clock.signal,
      });
      if (!result.response.ok) throw await apiProblemFromResponse(result.response, requestCorrelation);
      const payload: unknown = result.data;
      if (!isAuthLoginResponse(payload)) {
        throw new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: safeMessage(502), correlationId: requestCorrelation });
      }
      const session = toSession(payload);
      const encrypted = await sealSession(session, dependencies.config, now(dependencies));
      cookies.set(sessionCookieName(dependencies.config), encrypted, sessionCookieOptions(session, dependencies.config, now(dependencies)));
      const returnedCorrelation = responseCorrelationId(result.response, requestCorrelation);
      return Response.json({ authenticated: true, correlationId: returnedCorrelation }, { status: 200, headers: responseHeaders(returnedCorrelation) });
    } finally {
      clock.clear();
    }
  } catch (error) {
    if (error instanceof ApiProblem) return problemResponse(error);
    if (error instanceof DOMException && error.name === "AbortError") return problemResponse(timeoutProblem(requestCorrelation));
    return problemResponse(networkProblem(requestCorrelation));
  }
}

export async function handleLogout(
  request: Request,
  cookies: CookieStore,
  dependencies: BffDependencies,
): Promise<Response> {
  const requestCorrelation = correlationId(request.headers.get("X-Correlation-ID"));
  let trusted = false;
  try {
    try {
      assertTrustedMutation(request, dependencies.config);
      trusted = true;
    } catch {
      throw securityProblem(requestCorrelation);
    }
    const encrypted = cookies.get(sessionCookieName(dependencies.config))?.value;
    if (!encrypted) return new Response(null, { status: 204, headers: responseHeaders(requestCorrelation) });
    let session: SessionData;
    try {
      session = await unsealSession(encrypted, dependencies.config, now(dependencies));
    } catch {
      throw sessionProblem(requestCorrelation);
    }
    const coordinator = dependencies.refreshCoordinator ?? processRefreshCoordinator;
    coordinator.revoke(session.refreshToken, session.refreshTokenExpiresAt);
    const clock = deadline(dependencies);
    try {
      const client = createBackendClient(dependencies.config.backendUrl, { fetch: restrictedBackendFetch(dependencies) });
      const result = await client.POST("/auth/logout", {
        body: { refresh_token: session.refreshToken },
        headers: { "X-Correlation-ID": requestCorrelation },
        signal: clock.signal,
      });
      if (!result.response.ok) throw await apiProblemFromResponse(result.response, requestCorrelation);
      const returnedCorrelation = responseCorrelationId(result.response, requestCorrelation);
      return new Response(null, { status: 204, headers: responseHeaders(returnedCorrelation) });
    } finally {
      clock.clear();
    }
  } catch (error) {
    if (error instanceof ApiProblem) return problemResponse(error);
    if (error instanceof DOMException && error.name === "AbortError") return problemResponse(timeoutProblem(requestCorrelation));
    return problemResponse(networkProblem(requestCorrelation));
  } finally {
    if (trusted) cookies.set(sessionCookieName(dependencies.config), "", expiredSessionCookieOptions(dependencies.config));
  }
}

export class RefreshCoordinator {
  private readonly active = new Map<string, { controller: AbortController; promise: Promise<SessionData> }>();
  private readonly revoked = new Map<string, number>();
  private readonly maximum: number;
  private readonly timeoutMs: number;
  private readonly currentTime: () => number;

  constructor(maximum = 1_024, timeoutMs = 10_000, currentTime: () => number = Date.now) {
    this.maximum = maximum;
    this.timeoutMs = timeoutMs;
    this.currentTime = currentTime;
  }

  get size(): number {
    return this.active.size;
  }

  revoke(refreshToken: string, expiresAt: string): void {
    const key = createHash("sha256").update(refreshToken).digest("hex");
    const expiration = Date.parse(expiresAt);
    this.pruneRevoked();
    if (Number.isFinite(expiration) && expiration > this.currentTime()) this.revoked.set(key, expiration);
    this.active.get(key)?.controller.abort();
  }

  isRevoked(refreshToken: string): boolean {
    this.pruneRevoked();
    return this.revoked.has(createHash("sha256").update(refreshToken).digest("hex"));
  }

  private pruneRevoked(): void {
    const current = this.currentTime();
    for (const [key, expiration] of this.revoked) {
      if (expiration <= current) this.revoked.delete(key);
    }
    while (this.revoked.size > this.maximum) {
      const oldest = this.revoked.keys().next().value;
      if (typeof oldest !== "string") break;
      this.revoked.delete(oldest);
    }
  }

  async run(
    refreshToken: string,
    callerSignal: AbortSignal,
    work: (sharedSignal: AbortSignal) => Promise<SessionData>,
  ): Promise<SessionData> {
    const key = createHash("sha256").update(refreshToken).digest("hex");
    if (this.isRevoked(refreshToken)) throw new SessionError("sessao_invalida");
    const current = this.active.get(key);
    if (current) return this.waitForCaller(current.promise, callerSignal);
    if (this.active.size >= this.maximum) {
      throw new ApiProblem({ status: 503, codigo: "refresh_saturado", mensagem: safeMessage(503), correlationId: randomUUID() });
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const pending = work(controller.signal).finally(() => {
      clearTimeout(timer);
      if (this.active.get(key)?.promise === pending) this.active.delete(key);
    });
    this.active.set(key, { controller, promise: pending });
    return this.waitForCaller(pending, callerSignal);
  }

  private async waitForCaller(pending: Promise<SessionData>, signal: AbortSignal): Promise<SessionData> {
    if (signal.aborted) throw new DOMException("request aborted", "AbortError");
    let removeListener: () => void = () => undefined;
    const aborted = new Promise<never>((_resolve, reject) => {
      const onAbort = () => reject(new DOMException("request aborted", "AbortError"));
      signal.addEventListener("abort", onAbort, { once: true });
      removeListener = () => signal.removeEventListener("abort", onAbort);
    });
    try {
      return await Promise.race([pending, aborted]);
    } finally {
      removeListener();
    }
  }
}

const processRefreshCoordinator = new RefreshCoordinator();

async function refreshSession(
  session: SessionData,
  correlation: string,
  dependencies: BffDependencies,
  signal: AbortSignal,
): Promise<SessionData> {
  const client = createBackendClient(dependencies.config.backendUrl, { fetch: restrictedBackendFetch(dependencies) });
  const result = await client.POST("/auth/refresh", {
    body: { refresh_token: session.refreshToken },
    headers: { "X-Correlation-ID": correlation },
    signal,
  });
  if (!result.response.ok) throw await apiProblemFromResponse(result.response, correlation);
  const payload: unknown = result.data;
  if (!isAuthRefreshResponse(payload) || payload.tenant_id !== session.tenantId || payload.usuario_id !== session.userId) {
    throw sessionProblem(correlation);
  }
  return {
    ...session,
    accessToken: payload.access_token,
    accessTokenExpiresAt: payload.access_token_expira_em,
  };
}

function requestWithSession(
  request: Request,
  session: SessionData,
  correlation: string,
  signal: AbortSignal,
  backendUrl: string,
): Request {
  if (new URL(request.url).origin !== new URL(backendUrl).origin) {
    throw new ApiProblem({
      status: 500,
      codigo: "destino_backend_invalido",
      mensagem: "Destino backend recusado.",
      correlationId: correlation,
    });
  }
  if (PUBLIC_BACKEND_PATHS.has(new URL(request.url).pathname)) {
    throw new ApiProblem({
      status: 500,
      codigo: "transporte_inadequado",
      mensagem: "Operação pública recusada pelo transporte autenticado.",
      correlationId: correlation,
    });
  }
  const headers = new Headers(request.headers);
  for (const name of [
    "Cookie", "Origin", "Host", "Forwarded", "Via", "Content-Length",
    "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-Dest", "X-CSRF-Protection",
    "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Port", "X-Forwarded-Proto",
    "Connection", "Keep-Alive", "Proxy-Authenticate", "Proxy-Authorization", "TE",
    "Trailer", "Transfer-Encoding", "Upgrade",
  ]) {
    headers.delete(name);
  }
  headers.set("Authorization", `Bearer ${session.accessToken}`);
  headers.set("X-Correlation-ID", correlation);
  return new Request(request, { cache: "no-store", headers, redirect: "error", signal });
}

function canReplay(request: Request): boolean {
  const key = request.headers.get("Idempotency-Key");
  return SAFE_REPLAY_METHODS.has(request.method.toUpperCase()) || Boolean(key && IDEMPOTENCY_PATTERN.test(key));
}

export function createAuthenticatedFetch(
  context: AuthenticatedContext,
  dependencies: BffDependencies,
): FetchLike {
  let activeSession = context.session;
  return async (input: Request): Promise<Response> => {
    const original = input.clone();
    const requestCorrelation = correlationId(input.headers.get("X-Correlation-ID"));
    const clock = deadline(dependencies);
    const combinedSignal = AbortSignal.any([original.signal, clock.signal]);
    try {
      if (combinedSignal.aborted) throw new DOMException("request aborted", "AbortError");
      const first = requestWithSession(original.clone(), activeSession, requestCorrelation, combinedSignal, dependencies.config.backendUrl);
      const firstResponse = await dependencies.fetch(first);
      if (firstResponse.status !== 401) return firstResponse;
      const coordinator = dependencies.refreshCoordinator ?? processRefreshCoordinator;
      try {
        activeSession = await coordinator.run(
          activeSession.refreshToken,
          combinedSignal,
          (sharedSignal) => refreshSession(activeSession, requestCorrelation, dependencies, sharedSignal),
        );
        if (coordinator.isRevoked(activeSession.refreshToken)) throw new SessionError("sessao_invalida");
        if (combinedSignal.aborted) throw new DOMException("request aborted", "AbortError");
        await context.saveSession(activeSession);
      } catch {
        if (original.signal.aborted) throw cancelledProblem(requestCorrelation);
        if (clock.signal.aborted) throw timeoutProblem(requestCorrelation);
        await context.clearSession();
        throw sessionProblem(requestCorrelation);
      }
      if (!canReplay(original)) return firstResponse;
      if (combinedSignal.aborted) throw new DOMException("request aborted", "AbortError");
      const replay = requestWithSession(original.clone(), activeSession, requestCorrelation, combinedSignal, dependencies.config.backendUrl);
      const replayResponse = await dependencies.fetch(replay);
      if (replayResponse.status === 401) await context.clearSession();
      return replayResponse;
    } catch (error) {
      if (original.signal.aborted) throw cancelledProblem(requestCorrelation);
      if (clock.signal.aborted) throw timeoutProblem(requestCorrelation);
      if (error instanceof ApiProblem) throw error;
      throw networkProblem(requestCorrelation);
    } finally {
      clock.clear();
    }
  };
}

export async function createCookieAuthenticatedFetch(
  cookies: CookieStore,
  dependencies: BffDependencies,
  requestCorrelation: string = randomUUID(),
): Promise<FetchLike> {
  const cookieName = sessionCookieName(dependencies.config);
  const encrypted = cookies.get(cookieName)?.value;
  if (!encrypted) throw sessionProblem(correlationId(requestCorrelation));
  let current: SessionData;
  try {
    current = await unsealSession(encrypted, dependencies.config, now(dependencies));
  } catch {
    cookies.set(cookieName, "", expiredSessionCookieOptions(dependencies.config));
    throw sessionProblem(correlationId(requestCorrelation));
  }
  const context: AuthenticatedContext = {
    session: current,
    saveSession: async (sessionValue) => {
      current = sessionValue;
      const sealed = await (dependencies.seal ?? sealSession)(sessionValue, dependencies.config, now(dependencies));
      const coordinator = dependencies.refreshCoordinator ?? processRefreshCoordinator;
      if (coordinator.isRevoked(sessionValue.refreshToken)) throw new SessionError("sessao_invalida");
      cookies.set(cookieName, sealed, sessionCookieOptions(sessionValue, dependencies.config, now(dependencies)));
    },
    clearSession: async () => {
      cookies.set(cookieName, "", expiredSessionCookieOptions(dependencies.config));
    },
  };
  return createAuthenticatedFetch(context, dependencies);
}

export function createRuntimeDependencies(): BffDependencies {
  const config = readBffConfig();
  return { config, fetch: (request) => fetch(request) };
}
