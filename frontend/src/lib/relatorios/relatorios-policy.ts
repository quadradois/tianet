import type { components } from "../api/openapi.generated";

export const REPORTS_PERMISSION = "relatorios.operacionais.ler";
export const MIN_REPORT_DATE = "1970-01-01";
export const MAX_REPORT_DATE = "9998-12-31";

export type SummaryReport = components["schemas"]["ResumoCarteiraResponse"];
export type DueDatesReport = components["schemas"]["VencimentosInadimplenciaResponse"];
export type PaymentsReport = components["schemas"]["PagamentosEncerramentosResponse"];
export type CashFlowReport = components["schemas"]["FluxoPrevistoRealizadoResponse"];

export type ReportsPeriod = Readonly<{
  referenceDate: string;
  startDate: string;
  endDate: string;
}>;

export type ReportsPeriodResolution =
  | Readonly<{ kind: "ready"; period: ReportsPeriod }>
  | Readonly<{ kind: "missing" }>
  | Readonly<{ kind: "invalid" }>;

export function hasExactPermission(permissions: readonly string[], permission: string): boolean {
  return new Set(permissions).has(permission);
}

function single(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? undefined : value;
}

function calendarPartsAreValid(year: number, month: number, day: number): boolean {
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

export function isReportDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  if (value < MIN_REPORT_DATE || value > MAX_REPORT_DATE) return false;
  const [year = 0, month = 0, day = 0] = value.split("-").map(Number);
  return calendarPartsAreValid(year, month, day);
}

export function resolveReportsPeriod(raw: Readonly<{
  data_referencia?: string | string[];
  inicio?: string | string[];
  fim?: string | string[];
}>): ReportsPeriodResolution {
  const referenceDate = single(raw.data_referencia);
  const startDate = single(raw.inicio);
  const endDate = single(raw.fim);
  if (referenceDate === undefined && startDate === undefined && endDate === undefined) return { kind: "missing" };
  if (referenceDate === undefined || startDate === undefined || endDate === undefined) return { kind: "invalid" };
  if (!isReportDate(referenceDate) || !isReportDate(startDate) || !isReportDate(endDate)) return { kind: "invalid" };
  if (startDate > endDate) return { kind: "invalid" };
  return { kind: "ready", period: { referenceDate, startDate, endDate } };
}
