import type { components } from "@/lib/api/openapi.generated";

export const CONFIGURACOES_READ_PERMISSION = "configuracoes_financeiras.configuracao.ler";
export const CONFIGURACOES_MANAGE_PERMISSION = "configuracoes_financeiras.configuracao.gerir";
export const CONFIGURACOES_APPROVE_PERMISSION = "configuracoes_financeiras.configuracao.aprovar";
export const CONFIGURACOES_ACTIVATE_PERMISSION = "configuracoes_financeiras.configuracao.ativar";
export const MODALIDADE_MANAGE_PERMISSION = "configuracoes_financeiras.modalidade.gerir";
export const CALENDARIO_MANAGE_PERMISSION = "configuracoes_financeiras.calendario.gerir";
export const SNAPSHOT_CAPTURE_PERMISSION = "configuracoes_financeiras.snapshot.capturar";

export type ConfiguracaoPermission =
  | typeof CONFIGURACOES_READ_PERMISSION
  | typeof CONFIGURACOES_MANAGE_PERMISSION
  | typeof CONFIGURACOES_APPROVE_PERMISSION
  | typeof CONFIGURACOES_ACTIVATE_PERMISSION
  | typeof MODALIDADE_MANAGE_PERMISSION
  | typeof CALENDARIO_MANAGE_PERMISSION
  | typeof SNAPSHOT_CAPTURE_PERMISSION;

export type ConfiguracaoFinanceira = components["schemas"]["ConfiguracaoFinanceiraResponse"];
export type ConfiguracaoVigente = components["schemas"]["ConfiguracaoFinanceiraVigenteResponse"];
export type ModalidadeFinanceira = components["schemas"]["ModalidadeFinanceiraResponse"];
export type CalendarioFinanceiro = components["schemas"]["CalendarioFinanceiroResponse"];
export type SnapshotConfiguracao = components["schemas"]["SnapshotConfiguracaoContratualResponse"];
export type ConfiguracaoState = components["schemas"]["ConfiguracaoFinanceiraState"];

export type ConfiguracoesFilters = Readonly<{
  dataReferencia?: string;
  estado?: ConfiguracaoState;
  modalidade?: string;
}>;

export type ConfiguracoesActionState =
  | Readonly<{ kind: "idle"; message: string }>
  | Readonly<{ kind: "success"; message: string; status: number; correlationId: string }>
  | Readonly<{ kind: "problem"; message: string; status: number | null; correlationId: string }>;

export const CONFIGURACAO_STATES: readonly ConfiguracaoState[] = [
  "rascunho",
  "aprovada",
  "programada",
  "ativa",
  "substituida",
  "inativa",
];

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function hasExactPermission(permissions: readonly string[], permission: ConfiguracaoPermission): boolean {
  return new Set(permissions).has(permission);
}

export function formString(formData: FormData, key: string, maxLength: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized.length > 0 && normalized.length <= maxLength ? normalized : undefined;
}

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function isCalendarDate(value: string): boolean {
  if (!DATE_PATTERN.test(value)) return false;
  const [year = 0, month = 0, day = 0] = value.split("-").map(Number);
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

function isConfiguracaoState(value: string): value is ConfiguracaoState {
  return CONFIGURACAO_STATES.some((state) => state === value);
}

export function resolveConfiguracoesFilters(query: Record<string, string | string[] | undefined>): ConfiguracoesFilters {
  const rawData = typeof query.data_referencia === "string" ? query.data_referencia : undefined;
  const rawEstado = typeof query.estado === "string" ? query.estado : undefined;
  const rawModalidade = typeof query.modalidade === "string" ? query.modalidade.trim() : undefined;
  return {
    ...(rawData && isCalendarDate(rawData) ? { dataReferencia: rawData } : {}),
    ...(rawEstado && isConfiguracaoState(rawEstado) ? { estado: rawEstado } : {}),
    ...(rawModalidade ? { modalidade: rawModalidade.slice(0, 80) } : {}),
  };
}

export function formatOpaqueValue(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
