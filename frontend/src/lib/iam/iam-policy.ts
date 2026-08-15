import type { components } from "../api/openapi.generated";

export const PERFIL_READ_PERMISSION = "perfil.ler";
export const PERFIL_MANAGE_PERMISSION = "perfil.gerir";

export const IAM_PERMISSIONS = [
  PERFIL_READ_PERMISSION,
  PERFIL_MANAGE_PERMISSION,
] as const;

export type IamPermission = typeof IAM_PERMISSIONS[number];
export type Perfil = components["schemas"]["PerfilResponse"];
export type PermissoesCatalogo = components["schemas"]["PermissoesCatalogoResponse"];
export type PermissoesEfetivas = components["schemas"]["PermissoesEfetivasResponse"];
export type PerfilState = components["schemas"]["PerfilState"];

export type IamProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

export type IamReadResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: IamProblem }>;

export type IamActionState = Readonly<{
  kind: "idle" | "success" | "problem";
  message: string;
  correlationId?: string;
  status?: number;
}>;

export type IamFilters = Readonly<{
  perfilId?: string;
  usuarioId?: string;
}>;

export const INITIAL_IAM_ACTION_STATE: IamActionState = {
  kind: "idle",
  message: "Aguardando comando IAM permitido.",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PERMISSION_CODE_PATTERN = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/;

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

function clean(value: string | readonly string[] | undefined, max: number): string | undefined {
  const selected = first(value)?.trim();
  if (!selected || selected.length > max) return undefined;
  return selected;
}

export function hasExactIamPermission(permissions: readonly string[], permission: IamPermission): boolean {
  return new Set(permissions).has(permission);
}

export function hasAnyIamPermission(permissions: readonly string[]): boolean {
  return IAM_PERMISSIONS.some((permission) => hasExactIamPermission(permissions, permission));
}

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function isPermissionCode(value: string): boolean {
  return value.length <= 160 && PERMISSION_CODE_PATTERN.test(value);
}

export function resolveIamFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): IamFilters {
  const perfilId = clean(searchParams.perfil_id, 64);
  const usuarioId = clean(searchParams.usuario_id, 64);
  return {
    ...(perfilId && isUuid(perfilId) ? { perfilId } : {}),
    ...(usuarioId && isUuid(usuarioId) ? { usuarioId } : {}),
  };
}

export function formString(formData: FormData, key: string, max: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) return undefined;
  return trimmed;
}

export function formatPerfilState(state: PerfilState): string {
  return state === "ativo" ? "ativo" : "inativo";
}
