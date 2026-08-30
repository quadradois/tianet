import type { components } from "../api/openapi.generated";
import { normalizarMoeda } from "../formato/brasileiro";

export const COBRANCA_CASE_READ_PERMISSION = "cobranca.caso.ler";
export const COBRANCA_ACTION_REGISTER_PERMISSION = "cobranca.acao.registrar";
export const COBRANCA_PROMISE_REGISTER_PERMISSION = "cobranca.promessa.registrar";
export const COBRANCA_PROMISE_APPROPRIATE_PERMISSION = "cobranca.promessa.apropriar";

export const COBRANCA_PERMISSIONS = [
  COBRANCA_CASE_READ_PERMISSION,
  COBRANCA_ACTION_REGISTER_PERMISSION,
  COBRANCA_PROMISE_REGISTER_PERMISSION,
  COBRANCA_PROMISE_APPROPRIATE_PERMISSION,
] as const;

export const COLLECTION_STATES = ["pendente", "em_andamento", "encerrado"] as const;
export const COLLECTION_ACTION_TYPES = ["contato", "telefone", "email", "visita", "outro"] as const;
export type CobrancaPermission = typeof COBRANCA_PERMISSIONS[number];
export type CollectionState = components["schemas"]["EstadoCobranca"];
export type CollectionActionType = components["schemas"]["TipoAcaoCobranca"];
export type CollectionCase = components["schemas"]["CobrancaCasoResponse"];
export type CollectionQueue = components["schemas"]["FilaCobrancaResponse"];
export type CollectionAction = components["schemas"]["AcaoCobrancaResponse"];
export type PaymentPromise = components["schemas"]["PromessaPagamentoResponse"];
export type PromiseAppropriation = components["schemas"]["ApropriacaoPagamentoResponse"];
export type CobrancaActionType = CollectionActionType;
export type CobrancaCase = CollectionCase;
export type CobrancaQueue = CollectionQueue;
export type CobrancaFilters = CollectionFilters;
export type CobrancaProblem = Readonly<{ status: number; codigo: string; mensagem: string; correlationId: string }>;
export type CobrancaReadResult<T> = Readonly<{ kind: "ready"; data: T } | { kind: "problem"; problem: CobrancaProblem } | { kind: "denied" }>;
export type CobrancaActionState = Readonly<{ kind: "idle"; message: string; status?: undefined; correlationId?: undefined } | { kind: "success"; message: string; status: number; correlationId: string } | { kind: "problem"; message: string; status: number; correlationId?: string }>;

export const INITIAL_COBRANCA_ACTION_STATE: CobrancaActionState = {
  kind: "idle",
  message: "Aguardando acao de cobranca.",
};

export type CollectionFilters = Readonly<{
  devedorId?: string;
  estado?: CollectionState;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

export function hasExactPermission(permissions: readonly string[], permission: CobrancaPermission): boolean {
  return new Set(permissions).has(permission);
}

export function hasAnyCobrancaPermission(permissions: readonly string[]): boolean {
  const granted = new Set(permissions);
  return COBRANCA_PERMISSIONS.some((permission) => granted.has(permission));
}

export function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

export function isDate(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = DATE_PATTERN.exec(value);
  if (!match) return false;
  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

export function resolveCollectionFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): CollectionFilters {
  const estado = first(searchParams.estado);
  const devedorId = first(searchParams.devedor_id);
  return {
    ...(COLLECTION_STATES.some((state) => state === estado) ? { estado: estado as CollectionState } : {}),
    ...(isUuid(devedorId) ? { devedorId } : {}),
  };
}

export function formString(formData: FormData, key: string, max = 5_000): string | undefined {
  const value = formData.get(key);
  const trimmed = typeof value === "string" ? value.trim() : "";
  return trimmed && trimmed.length <= max ? trimmed : undefined;
}

export function formOptionalString(formData: FormData, key: string, max = 5_000): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed.length <= max ? trimmed || undefined : undefined;
}

export function formUuid(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 36);
  return isUuid(value) ? value : undefined;
}

export const formOptionalUuid = formUuid;

export function formDate(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 10);
  return isDate(value) ? value : undefined;
}

export function formMoney(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 40);
  return normalizarMoeda(value);
}

export function formActionType(formData: FormData): CollectionActionType | undefined {
  const value = formString(formData, "tipo", 20);
  return COLLECTION_ACTION_TYPES.some((item) => item === value) ? value as CollectionActionType : undefined;
}

export function formBoolean(formData: FormData, key: string): boolean {
  return formData.get(key) === "true" || formData.get(key) === "on";
}
