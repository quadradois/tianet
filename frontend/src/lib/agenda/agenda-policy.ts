import type { components } from "../api/openapi.generated";

export const AGENDA_READ_PERMISSION = "agenda.ler";
export const AGENDA_COMMITMENT_MANAGE_PERMISSION = "agenda.compromisso.gerir";
export const AGENDA_REMINDER_MANAGE_PERMISSION = "agenda.lembrete.gerir";
export const NOTIFICATION_RECONCILE_PERMISSION = "notificacao.conciliar";
export const COMMUNICATION_REGISTER_PERMISSION = "comunicacao.registrar";
export const COMMUNICATION_READ_PERMISSION = "comunicacao.ler";

export const AGENDA_PERMISSIONS = [
  AGENDA_READ_PERMISSION,
  AGENDA_COMMITMENT_MANAGE_PERMISSION,
  AGENDA_REMINDER_MANAGE_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  COMMUNICATION_REGISTER_PERMISSION,
  COMMUNICATION_READ_PERMISSION,
] as const;

export const COMMITMENT_STATES = ["aberto", "reagendado", "concluido", "cancelado"] as const;
export const REMINDER_STATES = ["programa", "enviado", "concluido", "cancelado"] as const;
export const COMMUNICATION_CHANNELS = ["telefone", "email", "chat", "presencial"] as const;

export type AgendaPermission = typeof AGENDA_PERMISSIONS[number];
export type CommitmentState = components["schemas"]["EstadoCompromisso"];
export type ReminderState = components["schemas"]["EstadoLembrete"];
export type CommunicationChannel = components["schemas"]["CanalComunicacao"];
export type AgendaItem = components["schemas"]["AgendaItemResponse"];
export type AgendaResponse = components["schemas"]["AgendaOperacionalResponse"];
export type Reminder = components["schemas"]["LembreteResponse"];
export type Notification = components["schemas"]["NotificacaoResponse"];
export type CommunicationRecord = components["schemas"]["RegistroComunicacaoResponse"];
export type CommunicationHistory = components["schemas"]["HistoricoComunicacaoResponse"];

export type AgendaProblem = Readonly<{ status: number; codigo: string; mensagem: string; correlationId: string }>;
export type AgendaReadResult<T> = Readonly<{ kind: "ready"; data: T } | { kind: "denied" } | { kind: "problem"; problem: AgendaProblem }>;
export type AgendaActionState = Readonly<
  | { kind: "idle"; message: string; status?: undefined; correlationId?: undefined }
  | { kind: "success"; message: string; status: number; correlationId: string }
  | { kind: "problem"; message: string; status: number; correlationId?: string }
>;

export type AgendaFilters = Readonly<{
  devedorId?: string;
  emprestimoId?: string;
  estado?: CommitmentState;
  janelaFim?: string;
  janelaInicio?: string;
  incluirLembretes: boolean;
}>;

export type CommunicationFilters = Readonly<{
  agendaItemId?: string;
  cobrancaAcaoId?: string;
  devedorId?: string;
  emprestimoId?: string;
}>;

export const INITIAL_AGENDA_ACTION_STATE: AgendaActionState = {
  kind: "idle",
  message: "Aguardando acao de Agenda ou Comunicacao.",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;

export function hasExactPermission(permissions: readonly string[], permission: AgendaPermission): boolean {
  return new Set(permissions).has(permission);
}

export function hasAnyAgendaPermission(permissions: readonly string[]): boolean {
  const granted = new Set(permissions);
  return AGENDA_PERMISSIONS.some((permission) => granted.has(permission));
}

export function isUuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function calendarPartsAreValid(year: number, month: number, day: number): boolean {
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

export function isDateTime(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = DATE_TIME_PATTERN.exec(value);
  if (!match) return false;
  const [, yearText, monthText, dayText, hourText, minuteText, secondText, , offsetHourText, offsetMinuteText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const offsetHour = offsetHourText === undefined ? 0 : Number(offsetHourText);
  const offsetMinute = offsetMinuteText === undefined ? 0 : Number(offsetMinuteText);
  return calendarPartsAreValid(year, month, day)
    && hour <= 23 && minute <= 59 && second <= 59
    && offsetHour <= 23 && offsetMinute <= 59;
}

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

export function resolveAgendaFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): AgendaFilters {
  const estadoCandidate = first(searchParams.estado)?.trim();
  const janelaInicio = first(searchParams.janela_inicio)?.trim();
  const janelaFim = first(searchParams.janela_fim)?.trim();
  const devedorId = first(searchParams.devedor_id)?.trim();
  const emprestimoId = first(searchParams.emprestimo_id)?.trim();
  return {
    incluirLembretes: first(searchParams.incluir_lembretes) !== "false",
    ...(COMMITMENT_STATES.some((state) => state === estadoCandidate) ? { estado: estadoCandidate as CommitmentState } : {}),
    ...(isDateTime(janelaInicio) ? { janelaInicio } : {}),
    ...(isDateTime(janelaFim) ? { janelaFim } : {}),
    ...(isUuid(devedorId) ? { devedorId } : {}),
    ...(isUuid(emprestimoId) ? { emprestimoId } : {}),
  };
}

export function resolveCommunicationFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): CommunicationFilters {
  const devedorId = first(searchParams.devedor_id)?.trim();
  const emprestimoId = first(searchParams.emprestimo_id)?.trim();
  const cobrancaAcaoId = first(searchParams.cobranca_acao_id)?.trim();
  const agendaItemId = first(searchParams.agenda_item_id)?.trim();
  return {
    ...(isUuid(devedorId) ? { devedorId } : {}),
    ...(isUuid(emprestimoId) ? { emprestimoId } : {}),
    ...(isUuid(cobrancaAcaoId) ? { cobrancaAcaoId } : {}),
    ...(isUuid(agendaItemId) ? { agendaItemId } : {}),
  };
}

export function formString(formData: FormData, key: string, max = 5_000): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
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

export function formDateTime(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 40);
  return isDateTime(value) ? value : undefined;
}

export function formCommitmentState(formData: FormData): CommitmentState | undefined {
  const value = formString(formData, "estado", 20);
  return COMMITMENT_STATES.some((state) => state === value) ? value as CommitmentState : undefined;
}

export function formCommunicationChannel(formData: FormData): CommunicationChannel | undefined {
  const value = formString(formData, "canal", 20);
  return COMMUNICATION_CHANNELS.some((channel) => channel === value) ? value as CommunicationChannel : undefined;
}
