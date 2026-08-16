import type { components } from "../api/openapi.generated";

export const COMERCIAL_SIMULATION_CREATE_PERMISSION = "comercial.simulacao.criar";
export const COMERCIAL_PROPOSAL_CREATE_PERMISSION = "comercial.proposta.criar";
export const COMERCIAL_PROPOSAL_READ_PERMISSION = "comercial.proposta.ler";
export const COMERCIAL_PROPOSAL_DECIDE_PERMISSION = "comercial.proposta.decidir";
export const COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION = "comercial.proposta.integrar";

export const COMERCIAL_PERMISSIONS = [
  COMERCIAL_SIMULATION_CREATE_PERMISSION,
  COMERCIAL_PROPOSAL_CREATE_PERMISSION,
  COMERCIAL_PROPOSAL_READ_PERMISSION,
  COMERCIAL_PROPOSAL_DECIDE_PERMISSION,
  COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION,
] as const;

export const PROPOSAL_STATES = ["rascunho", "em_analise", "aprovada", "recusada", "cancelada", "expirada"] as const;

export type ComercialPermission = typeof COMERCIAL_PERMISSIONS[number];
export type ProposalState = typeof PROPOSAL_STATES[number];
export type Simulation = components["schemas"]["SimulacaoComercialResponse"];
export type Proposal = components["schemas"]["PropostaComercialResponse"];
export type ProposalList = components["schemas"]["PropostaComercialListagemResponse"];
export type ApprovedProposalContract = components["schemas"]["PropostaAprovadaLogicaResponse"];

export type ComercialProblem = Readonly<{
  codigo: string;
  correlationId: string;
  mensagem: string;
  status: number;
}>;

export type ComercialReadResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ComercialProblem }>;

export type ComercialActionState = Readonly<{
  kind: "idle" | "success" | "problem";
  message: string;
  correlationId?: string;
  status?: number;
}>;

export const INITIAL_COMERCIAL_ACTION_STATE: ComercialActionState = {
  kind: "idle",
  message: "Aguardando acao comercial.",
};

export type ProposalFilters = Readonly<{
  estado?: ProposalState;
  page: number;
  size: number;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function hasExactPermission(permissions: readonly string[], permission: ComercialPermission): boolean {
  return new Set(permissions).has(permission);
}

export function hasAnyComercialPermission(permissions: readonly string[]): boolean {
  const granted = new Set(permissions);
  return COMERCIAL_PERMISSIONS.some((permission) => granted.has(permission));
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

export function resolveProposalFilters(searchParams: Readonly<Record<string, string | readonly string[] | undefined>>): ProposalFilters {
  const estadoCandidate = first(searchParams.estado)?.trim();
  const estado = PROPOSAL_STATES.includes(estadoCandidate as ProposalState) ? estadoCandidate as ProposalState : undefined;
  return {
    page: numberBetween(searchParams.page, 1, 10_000, 1),
    size: numberBetween(searchParams.size, 1, 100, 20),
    ...(estado ? { estado } : {}),
  };
}

export function allowedProposalDecisions(proposal: Pick<Proposal, "estado">, permissions: readonly string[]): readonly string[] {
  if (!hasExactPermission(permissions, COMERCIAL_PROPOSAL_DECIDE_PERMISSION)) return [];
  if (proposal.estado === "rascunho") return ["enviar-para-analise", "cancelar"];
  if (proposal.estado === "em_analise") return ["aprovar", "recusar", "cancelar", "expirar"];
  return [];
}

// DR-002: os parametros comerciais sao opacos por contrato, entao o BFF nao
// inspeciona nomes de chave. Filtrar por nome bloqueava o vocabulario canonico
// do Motor (`quantidade_parcelas`, `taxa_juros_mensal`) e nunca impediu calculo,
// que pode usar qualquer nome. A garantia anti-motor-paralelo e o scanner
// estatico certifyNoFinancialEngineParallel, que veta aritmetica no frontend.
export function parseOpaqueParameters(raw: string): Record<string, unknown> | undefined {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return undefined;
    if (Object.keys(parsed).length === 0) return undefined;
    return parsed as Record<string, unknown>;
  } catch {
    return undefined;
  }
}

export function formString(formData: FormData, key: string, max: number): string | undefined {
  const value = formData.get(key);
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) return undefined;
  return trimmed;
}
