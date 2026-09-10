import type { components } from "../api/openapi.generated";

export const OPENAI_READ_PERMISSION = "openai.conexao.ler" as const;
export const OPENAI_MANAGE_PERMISSION = "openai.conexao.gerir" as const;

export type OpenAIConnection = components["schemas"]["OpenAIConnectionResponse"];
export type OpenAIChallenge = components["schemas"]["OpenAIDeviceChallengeResponse"];
export type OpenAIDiagnostic = components["schemas"]["OpenAIDiagnosticResponse"];
export type OpenAILogout = components["schemas"]["OpenAILogoutResponse"];
export type OpenAIState = OpenAIConnection["state"];

export type OpenAIActionState =
  | Readonly<{ kind: "idle" }>
  | Readonly<{ kind: "login"; challenge: OpenAIChallenge; message: string; correlationId: string }>
  | Readonly<{ kind: "diagnostic"; diagnostic: OpenAIDiagnostic; message: string; correlationId: string; challenge?: OpenAIChallenge }>
  | Readonly<{ kind: "logout"; logout: OpenAILogout; message: string; correlationId: string }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string; challenge?: OpenAIChallenge }>;

export type OpenAIReadResult =
  | Readonly<{ kind: "ready"; connection: OpenAIConnection }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export const INITIAL_OPENAI_ACTION_STATE: OpenAIActionState = { kind: "idle" };

export function hasOpenAIPermission(granted: readonly string[], permission: string): boolean {
  return granted.includes(permission);
}

const STATES = new Set<OpenAIState>([
  "DESABILITADO", "INDISPONIVEL", "DESCONECTADO", "AGUARDANDO_USUARIO",
  "CONECTADO", "LIMITE_ATINGIDO", "ERRO", "ERRO_RESULTADO_DESCONHECIDO",
]);

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function exact(value: Record<string, unknown>, keys: readonly string[]): boolean {
  return Object.keys(value).sort().join("\0") === [...keys].sort().join("\0");
}

function state(value: unknown): value is OpenAIState {
  return typeof value === "string" && STATES.has(value as OpenAIState);
}

function nullableString(value: unknown): boolean {
  return value === null || typeof value === "string";
}

function validDateTime(value: unknown): boolean {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

export function isOpenAIConnection(value: unknown): value is OpenAIConnection {
  if (!record(value) || !exact(value, ["accountConnected", "enabled", "planType", "processAvailable", "state", "usageSummary"])) return false;
  return typeof value.enabled === "boolean" && typeof value.processAvailable === "boolean"
    && typeof value.accountConnected === "boolean" && nullableString(value.planType) && state(value.state)
    && (value.usageSummary === null || validUsageSummary(value.usageSummary));
}

export function isOfficialOpenAIUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "auth.openai.com" && url.username === "" && url.password === "";
  } catch {
    return false;
  }
}

export function isOpenAIChallenge(value: unknown): value is OpenAIChallenge {
  if (!record(value) || !exact(value, ["expiresAt", "userCode", "verificationUrl"])) return false;
  const verificationUrl = value.verificationUrl;
  const expiresAt = value.expiresAt;
  return typeof value.userCode === "string" && value.userCode.length > 0 && value.userCode.length <= 128
    && typeof verificationUrl === "string" && isOfficialOpenAIUrl(verificationUrl)
    && validDateTime(expiresAt) && typeof expiresAt === "string" && Date.parse(expiresAt) > Date.now();
}

export function validatedChallengeFromActionState(state: OpenAIActionState): OpenAIChallenge | undefined {
  if (!("challenge" in state)) return undefined;
  return isOpenAIChallenge(state.challenge) ? state.challenge : undefined;
}

function validModel(value: unknown): boolean {
  return record(value) && exact(value, ["default", "displayName", "id"])
    && typeof value.id === "string" && typeof value.displayName === "string" && typeof value.default === "boolean";
}

function validWindow(value: unknown): boolean {
  return record(value) && exact(value, ["resetsAt", "usedPercent", "windowDurationMinutes"])
    && Number.isInteger(value.usedPercent) && Number(value.usedPercent) >= 0 && Number(value.usedPercent) <= 100
    && (value.windowDurationMinutes === null || Number.isInteger(value.windowDurationMinutes))
    && (value.resetsAt === null || Number.isInteger(value.resetsAt));
}

function validRateLimit(value: unknown): boolean {
  return record(value) && exact(value, ["limitId", "planType", "primary", "secondary"])
    && nullableString(value.limitId) && nullableString(value.planType)
    && (value.primary === null || validWindow(value.primary))
    && (value.secondary === null || validWindow(value.secondary));
}

function validUsageSummary(value: unknown): boolean {
  return record(value) && exact(value, ["observedAt", "rateLimits", "rateLimitsStatus"])
    && validDateTime(value.observedAt)
    && (value.rateLimitsStatus === "ok" || value.rateLimitsStatus === "error")
    && Array.isArray(value.rateLimits) && value.rateLimits.every(validRateLimit);
}

export function isOpenAIDiagnostic(value: unknown): value is OpenAIDiagnostic {
  if (!record(value) || !exact(value, ["accountConnected", "accountStatus", "models", "modelsStatus", "observedAt", "planType", "rateLimits", "rateLimitsStatus", "state"])) return false;
  return state(value.state) && validDateTime(value.observedAt)
    && (value.accountStatus === "ok" || value.accountStatus === "error")
    && (value.accountConnected === null || typeof value.accountConnected === "boolean")
    && nullableString(value.planType)
    && (value.modelsStatus === "ok" || value.modelsStatus === "error")
    && Array.isArray(value.models) && value.models.every(validModel)
    && (value.rateLimitsStatus === "ok" || value.rateLimitsStatus === "error")
    && Array.isArray(value.rateLimits) && value.rateLimits.every(validRateLimit);
}

export function isOpenAILogout(value: unknown): value is OpenAILogout {
  return record(value) && exact(value, ["localLogout", "remoteRevocationVerified", "state"])
    && state(value.state) && typeof value.localLogout === "boolean" && typeof value.remoteRevocationVerified === "boolean";
}
