import "server-only";

import { decodeProtectedHeader, EncryptJWT, jwtDecrypt } from "jose";

export const SESSION_COOKIE_NAME = "__Host-emprestimo-session";
export const DEVELOPMENT_SESSION_COOKIE_NAME = "emprestimo-session";
export const CSRF_HEADER_NAME = "X-CSRF-Protection";
export const CSRF_HEADER_VALUE = "1";

const SESSION_ISSUER = "emprestimo-frontend";
const SESSION_AUDIENCE = "emprestimo-bff";
const SESSION_VERSION = 1;

export type SessionData = Readonly<{
  accessToken: string;
  accessTokenExpiresAt: string;
  refreshToken: string;
  refreshTokenExpiresAt: string;
  tenantId: string;
  userId: string;
}>;

export type BffConfig = Readonly<{
  backendUrl: string;
  origin: string;
  production: boolean;
  loginTenantIdentifier: string;
  currentKeyId: string;
  currentKey: Uint8Array;
  previousKeyId?: string;
  previousKey?: Uint8Array;
}>;

export type SessionCookieOptions = Readonly<{
  httpOnly: true;
  maxAge: number;
  path: "/";
  priority: "high";
  sameSite: "lax";
  secure: boolean;
}>;

export type CookieStore = Readonly<{
  get(name: string): { value: string } | undefined;
  set(name: string, value: string, options: SessionCookieOptions): void;
}>;

export class SessionError extends Error {
  readonly code: "configuracao_invalida" | "sessao_expirada" | "sessao_invalida";

  constructor(code: SessionError["code"]) {
    super(code);
    this.name = "SessionError";
    this.code = code;
  }
}

export function sessionCookieName(config: BffConfig): string {
  return config.production ? SESSION_COOKIE_NAME : DEVELOPMENT_SESSION_COOKIE_NAME;
}

function required(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name]?.trim();
  if (!value) throw new SessionError("configuracao_invalida");
  return value;
}

function decodeKey(value: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]{43}$/.test(value)) throw new SessionError("configuracao_invalida");
  let key: Uint8Array;
  try {
    key = Uint8Array.from(Buffer.from(value, "base64url"));
  } catch {
    throw new SessionError("configuracao_invalida");
  }
  if (key.byteLength !== 32) throw new SessionError("configuracao_invalida");
  if (Buffer.from(key).toString("base64url") !== value) throw new SessionError("configuracao_invalida");
  return key;
}

function parseServerUrl(value: string, production: boolean): URL {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new SessionError("configuracao_invalida");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new SessionError("configuracao_invalida");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new SessionError("configuracao_invalida");
  }
  if (parsed.pathname !== "/") throw new SessionError("configuracao_invalida");
  const loopback = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost" || parsed.hostname === "::1";
  if (production && parsed.protocol !== "https:" && !loopback) {
    throw new SessionError("configuracao_invalida");
  }
  return parsed;
}

function parseOrigin(value: string, production: boolean): string {
  const parsed = parseServerUrl(value, production);
  if (parsed.origin !== value || parsed.pathname !== "/") {
    throw new SessionError("configuracao_invalida");
  }
  return parsed.origin;
}

export function readBffConfig(env: NodeJS.ProcessEnv = process.env): BffConfig {
  const production = env.NODE_ENV === "production";
  const backendUrl = parseServerUrl(required(env, "FRONTEND_BACKEND_URL"), production);
  const origin = parseOrigin(required(env, "FRONTEND_ORIGIN"), production);
  const loginTenantIdentifier = env.FRONTEND_LOGIN_TENANT_IDENTIFICADOR?.trim() || "ACME";
  const currentKeyId = required(env, "FRONTEND_SESSION_KEY_ID");
  const currentKey = decodeKey(required(env, "FRONTEND_SESSION_KEY"));
  const previousKeyId = env.FRONTEND_SESSION_PREVIOUS_KEY_ID?.trim();
  const previousKeyValue = env.FRONTEND_SESSION_PREVIOUS_KEY?.trim();
  if (Boolean(previousKeyId) !== Boolean(previousKeyValue)) {
    throw new SessionError("configuracao_invalida");
  }
  if (previousKeyId && previousKeyValue) {
    if (previousKeyId === currentKeyId) throw new SessionError("configuracao_invalida");
    return {
      backendUrl: backendUrl.origin,
      origin,
      production,
      loginTenantIdentifier,
      currentKeyId,
      currentKey,
      previousKeyId,
      previousKey: decodeKey(previousKeyValue),
    };
  }
  return { backendUrl: backendUrl.origin, origin, production, loginTenantIdentifier, currentKeyId, currentKey };
}

function timestamp(value: string): number {
  const result = Date.parse(value);
  if (!Number.isFinite(result)) throw new SessionError("sessao_invalida");
  return result;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSessionPayload(value: unknown): value is SessionData & { version: number } {
  if (!isRecord(value) || value.version !== SESSION_VERSION) return false;
  return [
    value.accessToken,
    value.accessTokenExpiresAt,
    value.refreshToken,
    value.refreshTokenExpiresAt,
    value.tenantId,
    value.userId,
  ].every((item) => typeof item === "string" && item.length > 0);
}

export function sessionCookieOptions(
  session: SessionData,
  config: BffConfig,
  now = new Date(),
): SessionCookieOptions {
  const remainingSeconds = Math.floor((timestamp(session.refreshTokenExpiresAt) - now.getTime()) / 1000);
  if (remainingSeconds <= 0) throw new SessionError("sessao_expirada");
  return {
    httpOnly: true,
    maxAge: remainingSeconds,
    path: "/",
    priority: "high",
    sameSite: "lax",
    secure: config.production,
  };
}

export function expiredSessionCookieOptions(config: BffConfig): SessionCookieOptions {
  return { httpOnly: true, maxAge: 0, path: "/", priority: "high", sameSite: "lax", secure: config.production };
}

export async function sealSession(
  session: SessionData,
  config: BffConfig,
  now = new Date(),
): Promise<string> {
  sessionCookieOptions(session, config, now);
  const expiration = Math.floor(timestamp(session.refreshTokenExpiresAt) / 1000);
  const issuedAt = Math.floor(now.getTime() / 1000);
  return new EncryptJWT({ ...session, version: SESSION_VERSION })
    .setProtectedHeader({ alg: "dir", enc: "A256GCM", kid: config.currentKeyId, typ: "JWT" })
    .setIssuer(SESSION_ISSUER)
    .setAudience(SESSION_AUDIENCE)
    .setIssuedAt(issuedAt)
    .setExpirationTime(expiration)
    .encrypt(config.currentKey);
}

export async function unsealSession(
  value: string,
  config: BffConfig,
  now = new Date(),
): Promise<SessionData> {
  try {
    const header = decodeProtectedHeader(value);
    if (header.alg !== "dir" || header.enc !== "A256GCM" || header.typ !== "JWT" || !header.kid) {
      throw new SessionError("sessao_invalida");
    }
    let key: Uint8Array | undefined;
    if (header.kid === config.currentKeyId) key = config.currentKey;
    else if (header.kid === config.previousKeyId) key = config.previousKey;
    if (!key) throw new SessionError("sessao_invalida");
    const result = await jwtDecrypt(value, key, {
      audience: SESSION_AUDIENCE,
      clockTolerance: 0,
      contentEncryptionAlgorithms: ["A256GCM"],
      currentDate: now,
      issuer: SESSION_ISSUER,
      keyManagementAlgorithms: ["dir"],
    });
    if (!isSessionPayload(result.payload)) throw new SessionError("sessao_invalida");
    if (timestamp(result.payload.refreshTokenExpiresAt) <= now.getTime()) {
      throw new SessionError("sessao_expirada");
    }
    return {
      accessToken: result.payload.accessToken,
      accessTokenExpiresAt: result.payload.accessTokenExpiresAt,
      refreshToken: result.payload.refreshToken,
      refreshTokenExpiresAt: result.payload.refreshTokenExpiresAt,
      tenantId: result.payload.tenantId,
      userId: result.payload.userId,
    };
  } catch (error) {
    if (error instanceof SessionError) throw error;
    throw new SessionError("sessao_invalida");
  }
}

export function assertTrustedMutation(request: Request, config: BffConfig): void {
  const origin = request.headers.get("Origin");
  const fetchSite = request.headers.get("Sec-Fetch-Site");
  const csrf = request.headers.get(CSRF_HEADER_NAME);
  if (origin !== config.origin || csrf !== CSRF_HEADER_VALUE) {
    throw new SessionError("sessao_invalida");
  }
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") {
    throw new SessionError("sessao_invalida");
  }
}
