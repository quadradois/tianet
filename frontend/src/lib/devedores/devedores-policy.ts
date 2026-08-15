import type { components } from "../api/openapi.generated";

export const DEVEDOR_READ_PERMISSION = "devedor.ler";
export const DEVEDOR_CREATE_PERMISSION = "devedor.criar";
export const DEVEDOR_UPDATE_PERMISSION = "devedor.atualizar";
export const DEVEDOR_INACTIVATE_PERMISSION = "devedor.inativar";
export const DEVEDOR_REACTIVATE_PERMISSION = "devedor.reativar";

export const DEVEDORES_PERMISSIONS = [
  DEVEDOR_READ_PERMISSION,
  DEVEDOR_CREATE_PERMISSION,
  DEVEDOR_UPDATE_PERMISSION,
  DEVEDOR_INACTIVATE_PERMISSION,
  DEVEDOR_REACTIVATE_PERMISSION,
] as const;

export type DevedorPermission = typeof DEVEDORES_PERMISSIONS[number];
export type Devedor = components["schemas"]["DevedorResponse"];
export type DevedoresList = components["schemas"]["DevedorListagemResponse"];
export type DevedorHistory = components["schemas"]["DevedorHistoricoResponse"];

export type DevedoresProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

export type DevedoresReadResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: DevedoresProblem }>;

export type DevedorActionState = Readonly<{
  kind: "idle" | "success" | "problem";
  message: string;
  correlationId?: string;
  status?: number;
}>;

export const INITIAL_DEVEDOR_ACTION_STATE: DevedorActionState = {
  kind: "idle",
  message: "Aguardando envio do formulario.",
};

export type DevedorListFilters = Readonly<{
  documento?: string;
  estado?: "ativo" | "inativo";
  nome?: string;
  page: number;
  size: number;
}>;

const DOCUMENT_PATTERN = /^[0-9A-Za-z.\-/]{1,20}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function hasExactPermission(permissions: readonly string[], permission: DevedorPermission): boolean {
  return new Set(permissions).has(permission);
}

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

function clean(value: string | readonly string[] | undefined, max: number): string | undefined {
  const selected = first(value)?.trim();
  if (!selected || selected.length > max) return undefined;
  return selected;
}

function numberBetween(value: string | readonly string[] | undefined, min: number, max: number, fallback: number): number {
  const selected = first(value);
  if (!selected || !/^\d+$/.test(selected)) return fallback;
  const parsed = Number(selected);
  return parsed >= min && parsed <= max ? parsed : fallback;
}

export function resolveDevedoresFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): DevedorListFilters {
  const documento = clean(searchParams.documento, 20);
  const nome = clean(searchParams.nome, 200);
  const estadoCandidate = clean(searchParams.estado, 20);
  const estado = estadoCandidate === "ativo" || estadoCandidate === "inativo" ? estadoCandidate : undefined;
  return {
    page: numberBetween(searchParams.page, 1, 10_000, 1),
    size: numberBetween(searchParams.size, 1, 100, 20),
    ...(documento && DOCUMENT_PATTERN.test(documento) ? { documento } : {}),
    ...(estado ? { estado } : {}),
    ...(nome ? { nome } : {}),
  };
}

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function formString(formData: FormData, key: string, max: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) return undefined;
  return trimmed;
}

export function formBoolean(formData: FormData, key: string): boolean {
  return formData.get(key) === "on" || formData.get(key) === "true";
}
