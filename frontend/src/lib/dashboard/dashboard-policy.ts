export const REPORTS_PERMISSION = "relatorios.operacionais.ler";
export const AGENDA_PERMISSION = "agenda.ler";
export const COLLECTION_PERMISSION = "cobranca.caso.ler";
export const DASHBOARD_PERMISSIONS = [REPORTS_PERMISSION, AGENDA_PERMISSION, COLLECTION_PERMISSION] as const;
export const BUSINESS_TIME_ZONE = "America/Sao_Paulo";
export const MIN_REFERENCE_DATE = "1970-01-01";
export const MAX_REFERENCE_DATE = "9998-12-31";

const LOCAL_DATE_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  day: "2-digit",
  month: "2-digit",
  timeZone: BUSINESS_TIME_ZONE,
  year: "numeric",
});
const LOCAL_DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  day: "2-digit",
  fractionalSecondDigits: 3,
  hour: "2-digit",
  hourCycle: "h23",
  minute: "2-digit",
  month: "2-digit",
  second: "2-digit",
  timeZone: BUSINESS_TIME_ZONE,
  timeZoneName: "longOffset",
  year: "numeric",
});

export type DashboardPeriod = Readonly<{
  referenceDate: string;
  agendaStart: string;
  agendaEnd: string;
}>;

export type PeriodResolution =
  | Readonly<{ kind: "ready"; period: DashboardPeriod }>
  | Readonly<{ kind: "canonical"; referenceDate: string }>
  | Readonly<{ kind: "invalid" }>;

export function hasExactPermission(permissions: readonly string[], permission: string): boolean {
  return new Set(permissions).has(permission);
}

export function hasDashboardAccess(permissions: readonly string[]): boolean {
  return DASHBOARD_PERMISSIONS.some((permission) => hasExactPermission(permissions, permission));
}

function calendarDateIsValid(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  if (value < MIN_REFERENCE_DATE || value > MAX_REFERENCE_DATE) return false;
  const [year, month, day] = value.split("-").map(Number);
  const probe = new Date(Date.UTC(year ?? 0, (month ?? 0) - 1, day ?? 0));
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

export function businessDate(now: Date): string {
  const parts = LOCAL_DATE_FORMATTER.formatToParts(now);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

function nextCalendarDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  const probe = new Date(0);
  probe.setUTCFullYear(year ?? 0, (month ?? 0) - 1, (day ?? 0) + 1);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.toISOString().slice(0, 10);
}

function firstInstantOfCivilDate(value: string): number {
  const [year, month, day] = value.split("-").map(Number);
  const anchor = new Date(0);
  anchor.setUTCFullYear(year ?? 0, (month ?? 0) - 1, day ?? 0);
  anchor.setUTCHours(0, 0, 0, 0);
  let lower = anchor.getTime() - 36 * 60 * 60 * 1_000;
  let upper = anchor.getTime() + 36 * 60 * 60 * 1_000;
  while (lower < upper) {
    const middle = Math.floor((lower + upper) / 2);
    if (businessDate(new Date(middle)) < value) lower = middle + 1;
    else upper = middle;
  }
  if (businessDate(new Date(lower)) !== value) throw new RangeError("Data civil indisponivel no timezone governado.");
  return lower;
}

function zonedDateTime(instant: number): string {
  const parts = Object.fromEntries(LOCAL_DATE_TIME_FORMATTER.formatToParts(new Date(instant)).map((part) => [part.type, part.value]));
  const offset = String(parts.timeZoneName).replace(/^GMT/, "") || "+00:00";
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}.${parts.fractionalSecond}${offset}`;
}

function agendaWindow(referenceDate: string): Pick<DashboardPeriod, "agendaStart" | "agendaEnd"> {
  const start = firstInstantOfCivilDate(referenceDate);
  const end = firstInstantOfCivilDate(nextCalendarDate(referenceDate)) - 1;
  return { agendaStart: zonedDateTime(start), agendaEnd: zonedDateTime(end) };
}

export function resolveDashboardPeriod(raw: string | string[] | undefined, now = new Date()): PeriodResolution {
  if (raw === undefined) return { kind: "canonical", referenceDate: businessDate(now) };
  if (Array.isArray(raw) || !calendarDateIsValid(raw)) return { kind: "invalid" };
  return {
    kind: "ready",
    period: {
      referenceDate: raw,
      ...agendaWindow(raw),
    },
  };
}
