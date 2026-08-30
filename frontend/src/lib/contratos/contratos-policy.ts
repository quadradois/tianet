import type { components } from "../api/openapi.generated";

export const CONTRATO_CREATE_PERMISSION = "contratos.contrato.criar";
export const CONTRATO_READ_PERMISSION = "contratos.contrato.ler";
export const CONTRATO_SIGN_PERMISSION = "contratos.contrato.assinar";
export const CONTRATO_RELEASE_PERMISSION = "contratos.contrato.liberar";
export const CONTRATO_CLOSE_PERMISSION = "contratos.contrato.encerrar";

export const CONTRATO_PERMISSIONS = [
  CONTRATO_CREATE_PERMISSION,
  CONTRATO_READ_PERMISSION,
  CONTRATO_SIGN_PERMISSION,
  CONTRATO_RELEASE_PERMISSION,
  CONTRATO_CLOSE_PERMISSION,
] as const;

export const CONTRACT_STATES = ["rascunho", "formalizado", "assinado", "liberado_para_motor", "cancelado", "encerrado"] as const;
export const CONTRACT_DECISIONS = ["assinar", "liberar-para-motor", "cancelar", "encerrar"] as const;

export type ContratoPermission = typeof CONTRATO_PERMISSIONS[number];
export type ContractState = typeof CONTRACT_STATES[number];
export type ContractDecision = typeof CONTRACT_DECISIONS[number];
export type Contract = components["schemas"]["ContratoCreditoResponse"];
export type ContractList = components["schemas"]["ContratoCreditoListagemResponse"];
export type ContractEvent = components["schemas"]["EventoContratoResponse"];
export type ReleasedContract = components["schemas"]["ContratoLiberadoLogicoResponse"];

export type ContratoProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

export type ContratoReadResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ContratoProblem }>;

export type ContratoActionState = Readonly<{
  kind: "idle" | "success" | "problem";
  message: string;
  correlationId?: string;
  status?: number;
}>;

export const INITIAL_CONTRATO_ACTION_STATE: ContratoActionState = {
  kind: "idle",
  message: "Aguardando acao contratual.",
};

export type ContractFilters = Readonly<{
  devedorId?: string;
  estado?: ContractState;
  page: number;
  size: number;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const FORBIDDEN_FINANCIAL_TERMS = /(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia|parcela|pagamento|emprestimo|memoria|pix|boleto)/i;

export function hasExactPermission(permissions: readonly string[], permission: ContratoPermission): boolean {
  return new Set(permissions).has(permission);
}

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value);
}

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

function numberBetween(value: string | readonly string[] | undefined, min: number, max: number, fallback: number): number {
  const selected = first(value);
  if (!selected || !/^\d+$/.test(selected)) return fallback;
  const parsed = Number(selected);
  return parsed >= min && parsed <= max ? parsed : fallback;
}

export function resolveContractFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): ContractFilters {
  const estadoCandidate = first(searchParams.estado)?.trim();
  const devedorCandidate = first(searchParams.devedor_id)?.trim();
  const estado = CONTRACT_STATES.includes(estadoCandidate as ContractState) ? estadoCandidate as ContractState : undefined;
  const devedorId = devedorCandidate && isUuid(devedorCandidate) ? devedorCandidate : undefined;
  return {
    page: numberBetween(searchParams.page, 1, 10_000, 1),
    size: numberBetween(searchParams.size, 1, 100, 20),
    ...(estado ? { estado } : {}),
    ...(devedorId ? { devedorId } : {}),
  };
}

export function allowedContractDecisions(contract: Pick<Contract, "estado">, permissions: readonly string[]): readonly ContractDecision[] {
  const decisions: ContractDecision[] = [];
  if ((contract.estado === "rascunho" || contract.estado === "formalizado")
    && hasExactPermission(permissions, CONTRATO_SIGN_PERMISSION)) decisions.push("assinar");
  if (contract.estado === "assinado" && hasExactPermission(permissions, CONTRATO_RELEASE_PERMISSION)) decisions.push("liberar-para-motor");
  if ((contract.estado === "rascunho" || contract.estado === "formalizado")
    && hasExactPermission(permissions, CONTRATO_CLOSE_PERMISSION)) decisions.push("cancelar");
  if ((contract.estado === "assinado" || contract.estado === "liberado_para_motor")
    && hasExactPermission(permissions, CONTRATO_CLOSE_PERMISSION)) decisions.push("encerrar");
  return decisions;
}

export function formString(formData: FormData, key: string, max: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) return undefined;
  return trimmed;
}

export function parseContractReason(formData: FormData): string | undefined {
  return formString(formData, "motivo", 500);
}

export function assertOpaqueContractParameters(value: Record<string, unknown>): boolean {
  return !Object.keys(value).some((key) => FORBIDDEN_FINANCIAL_TERMS.test(key));
}
