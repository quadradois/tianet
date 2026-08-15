import type { components } from "@/lib/api/openapi.generated";

export const JOB_READ_PERMISSION = "automacao.job.consultar";
export const JOB_CANCEL_PERMISSION = "automacao.job.cancelar";
export const JOB_RETRY_PERMISSION = "automacao.job.retry";
export const NOTIFICATION_READ_PERMISSION = "notificacao.consultar";
export const TEMPLATE_MANAGE_PERMISSION = "notificacao.template.gerir";
export const NOTIFICATION_RECONCILE_PERMISSION = "notificacao.conciliar";

export type AutomacaoPermission =
  | typeof JOB_READ_PERMISSION
  | typeof JOB_CANCEL_PERMISSION
  | typeof JOB_RETRY_PERMISSION
  | typeof NOTIFICATION_READ_PERMISSION
  | typeof TEMPLATE_MANAGE_PERMISSION
  | typeof NOTIFICATION_RECONCILE_PERMISSION;

export type Job = components["schemas"]["JobResponse"];
export type JobList = components["schemas"]["JobListResponse"];
export type Notification = components["schemas"]["NotificacaoResponse"];
export type NotificationList = components["schemas"]["NotificacaoListResponse"];
export type Template = components["schemas"]["TemplateResponse"];
export type TemplateList = components["schemas"]["TemplateListResponse"];

export type AutomacaoProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

export type AutomacaoReadResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: AutomacaoProblem }>;

export type AutomacaoActionState =
  | Readonly<{ kind: "idle"; message: "" }>
  | Readonly<{ correlationId: string; kind: "problem"; message: string; status: number }>
  | Readonly<{ correlationId: string; kind: "success"; message: string; status: number }>;

export const INITIAL_AUTOMACAO_ACTION_STATE: AutomacaoActionState = { kind: "idle", message: "" };

export type AutomacaoFilters = Readonly<{
  jobId: string | null;
  notificationId: string | null;
  page: number;
  size: number;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const AUTOMACAO_PERMISSIONS = [
  JOB_READ_PERMISSION,
  JOB_CANCEL_PERMISSION,
  JOB_RETRY_PERMISSION,
  NOTIFICATION_READ_PERMISSION,
  TEMPLATE_MANAGE_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
] as const;

export function hasExactAutomacaoPermission(permissions: readonly string[], permission: AutomacaoPermission): boolean {
  return new Set(permissions).has(permission);
}

export function hasAnyAutomacaoPermission(permissions: readonly string[]): boolean {
  return AUTOMACAO_PERMISSIONS.some((permission) => hasExactAutomacaoPermission(permissions, permission));
}

export function isUuid(value: string | null | undefined): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

export function formString(formData: FormData, key: string, maxLength: number): string | null {
  const value = formData.get(key);
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > maxLength) return null;
  return trimmed;
}

function firstString(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveInteger(value: string | undefined, fallback: number, max: number): number {
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= max ? parsed : fallback;
}

export function resolveAutomacaoFilters(searchParams: Record<string, string | string[] | undefined>): AutomacaoFilters {
  const jobId = firstString(searchParams.job_id);
  const notificationId = firstString(searchParams.notification_id);
  return {
    jobId: isUuid(jobId) ? jobId : null,
    notificationId: isUuid(notificationId) ? notificationId : null,
    page: positiveInteger(firstString(searchParams.page), 1, 10_000),
    size: positiveInteger(firstString(searchParams.size), 20, 100),
  };
}
