import type { components } from "../api/openapi.generated";
import { normalizarMoeda } from "../formato/brasileiro";

export const MOTOR_LOAN_CREATE_PERMISSION = "motor.emprestimo.criar";
export const MOTOR_LOAN_READ_PERMISSION = "motor.emprestimo.ler";
export const MOTOR_INSTALLMENT_GENERATE_PERMISSION = "motor.parcela.gerar";
export const MOTOR_INSTALLMENT_CREATE_PERMISSION = MOTOR_INSTALLMENT_GENERATE_PERMISSION;
export const MOTOR_INSTALLMENT_READ_PERMISSION = "motor.parcela.ler";
export const MOTOR_PAYMENT_REGISTER_PERMISSION = "motor.pagamento.registrar";
export const MOTOR_PAYMENT_CREATE_PERMISSION = MOTOR_PAYMENT_REGISTER_PERMISSION;
export const MOTOR_BALANCE_READ_PERMISSION = "motor.saldo.ler";
export const MOTOR_MEMORY_READ_PERMISSION = "motor.memoria.ler";
export const MOTOR_PAYOFF_EXECUTE_PERMISSION = "motor.quitacao.executar";
export const MOTOR_SETTLEMENT_EXECUTE_PERMISSION = MOTOR_PAYOFF_EXECUTE_PERMISSION;
export const MOTOR_RENEGOTIATION_CREATE_PERMISSION = "motor.renegociacao.criar";

export type MotorPermission =
  | typeof MOTOR_LOAN_CREATE_PERMISSION
  | typeof MOTOR_LOAN_READ_PERMISSION
  | typeof MOTOR_INSTALLMENT_GENERATE_PERMISSION
  | typeof MOTOR_INSTALLMENT_READ_PERMISSION
  | typeof MOTOR_PAYMENT_REGISTER_PERMISSION
  | typeof MOTOR_BALANCE_READ_PERMISSION
  | typeof MOTOR_MEMORY_READ_PERMISSION
  | typeof MOTOR_PAYOFF_EXECUTE_PERMISSION
  | typeof MOTOR_RENEGOTIATION_CREATE_PERMISSION;

export type Loan = components["schemas"]["EmprestimoResponse"];
export type LoanList = components["schemas"]["EmprestimoListagemResponse"];
export type Balance = components["schemas"]["SaldoResponse"];
export type CalculationMemory = components["schemas"]["MemoriaCalculoResponse"];
export type PayoffQuote = components["schemas"]["QuitacaoCalculadaResponse"];
export type SettlementPreview = PayoffQuote;
export type Payment = components["schemas"]["PagamentoResponse"];
export type Payoff = components["schemas"]["QuitacaoResponse"];
export type Settlement = Payoff;
export type Renegotiation = components["schemas"]["RenegociacaoResponse"];
export type LoanState = components["schemas"]["EmprestimoState"];

export type MotorProblem = Readonly<{ status: number; codigo: string; mensagem: string; correlationId: string }>;
export type MotorReadResult<T> = Readonly<{ kind: "ready"; data: T } | { kind: "problem"; problem: MotorProblem } | { kind: "denied" }>;
export type MotorActionState = Readonly<{ kind: "idle"; status?: undefined; message?: undefined; correlationId?: undefined; targetId?: undefined } | { kind: "success"; status: number; message: string; correlationId: string; targetId?: string } | { kind: "problem"; status: number; message: string; correlationId?: string; targetId?: undefined }>;

export const INITIAL_MOTOR_ACTION_STATE: MotorActionState = { kind: "idle" };

export type LoanFilters = Readonly<{
  devedorId?: string;
  estado?: LoanState;
  page: number;
  size: number;
}>;

export const LOAN_STATES: readonly LoanState[] = ["ativo", "quitado", "cancelado"];
export const MOTOR_COMMANDS = ["criar-emprestimo", "registrar-pagamento", "executar-quitacao", "registrar-renegociacao"] as const;
export type MotorCommand = typeof MOTOR_COMMANDS[number];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const FORBIDDEN_FINANCIAL_KEYS = /juros|mora|multa|amortiza|saldo|quitacao|parcela|pagamento|principal|encargo|regra|memoria|resultado/i;

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

export function isDateTime(value: unknown): value is string {
  return typeof value === "string" && DATE_TIME_PATTERN.test(value);
}

export function hasExactPermission(effectivePermissions: readonly string[], permission: MotorPermission): boolean {
  return effectivePermissions.some((candidate) => candidate === permission);
}

export function hasAnyMotorPermission(effectivePermissions: readonly string[]): boolean {
  const granted = new Set(effectivePermissions);
  const permissions: readonly MotorPermission[] = [
    MOTOR_LOAN_CREATE_PERMISSION,
    MOTOR_LOAN_READ_PERMISSION,
    MOTOR_INSTALLMENT_GENERATE_PERMISSION,
    MOTOR_INSTALLMENT_READ_PERMISSION,
    MOTOR_PAYMENT_REGISTER_PERMISSION,
    MOTOR_BALANCE_READ_PERMISSION,
    MOTOR_MEMORY_READ_PERMISSION,
    MOTOR_PAYOFF_EXECUTE_PERMISSION,
    MOTOR_RENEGOTIATION_CREATE_PERMISSION,
  ];
  return permissions.some((permission) => granted.has(permission));
}

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function positiveInt(value: string | undefined, fallback: number, max: number): number {
  if (!value || !/^\d+$/.test(value)) return fallback;
  const numeric = Number(value);
  return numeric >= 1 && numeric <= max ? numeric : fallback;
}

export function resolveLoanFilters(query: Record<string, string | string[] | undefined>): LoanFilters {
  const estado = one(query.estado);
  const devedorId = one(query.devedor_id);
  return {
    ...(isUuid(devedorId) ? { devedorId } : {}),
    ...(LOAN_STATES.some((state) => state === estado) ? { estado: estado as LoanState } : {}),
    page: positiveInt(one(query.page), 1, 10_000),
    size: positiveInt(one(query.size), 20, 100),
  };
}

/**
 * Os tres grupos que o Credor pediu, cada um amarrado a um estado que o backend
 * retorna. Nao ha derivacao: "quitado" e o estado oficial do Emprestimo, nunca
 * uma conclusao tirada de datas ou de saldo no browser.
 */
export const SITUACOES = [
  {
    chave: "em-andamento",
    estado: "ativo",
    titulo: "Em andamento",
    vazio: "Nenhum emprestimo em andamento.",
  },
  {
    chave: "quitados",
    estado: "quitado",
    titulo: "Quitados",
    vazio: "Nenhum emprestimo quitado ainda.",
  },
  {
    chave: "encerrados",
    estado: "cancelado",
    titulo: "Encerrados",
    vazio: "Nenhum emprestimo encerrado.",
  },
] as const satisfies readonly { chave: string; estado: LoanState; titulo: string; vazio: string }[];

export type Situacao = (typeof SITUACOES)[number];

/** Separa a pagina retornada nos tres grupos, comparando o estado literalmente. */
export function agruparPorSituacao(loans: readonly Loan[]): readonly (Situacao & { emprestimos: readonly Loan[] })[] {
  return SITUACOES.map((situacao) => ({
    ...situacao,
    emprestimos: loans.filter((loan) => loan.estado === situacao.estado),
  }));
}

/** Tipo da memoria de calculo, dito ao Credor em vez de `geracao_parcelas`. */
const ROTULO_MEMORIA: Readonly<Record<string, string>> = {
  geracao_parcelas: "Geracao das parcelas",
  saldo: "Calculo do saldo",
  pagamento: "Aplicacao do pagamento",
  quitacao: "Calculo da quitacao",
  renegociacao: "Renegociacao",
};

export function rotuloMemoria(tipo: string): string {
  return ROTULO_MEMORIA[tipo] ?? tipo;
}

export function allowedMotorCommands(loan: Pick<Loan, "estado">, permissions: readonly string[]): readonly MotorCommand[] {
  if (loan.estado !== "ativo") return [];
  const commands: MotorCommand[] = [];
  if (hasExactPermission(permissions, MOTOR_PAYMENT_REGISTER_PERMISSION)) commands.push("registrar-pagamento");
  if (hasExactPermission(permissions, MOTOR_PAYOFF_EXECUTE_PERMISSION)) commands.push("executar-quitacao");
  if (hasExactPermission(permissions, MOTOR_RENEGOTIATION_CREATE_PERMISSION)) commands.push("registrar-renegociacao");
  return commands;
}

export function formString(formData: FormData, key: string, max = 5_000): string | undefined {
  const value = formData.get(key);
  const trimmed = typeof value === "string" ? value.trim() : "";
  return trimmed && trimmed.length <= max ? trimmed : undefined;
}

export function validMoneyInput(value: string | undefined): value is string {
  return normalizarMoeda(value) !== undefined;
}

export function formDate(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 10);
  return isDate(value) ? value : undefined;
}

export function formDateTime(formData: FormData, key: string): string | undefined {
  const value = formString(formData, key, 40);
  return isDateTime(value) ? value : undefined;
}

/**
 * Aceita a data que o Credor escolhe no calendario e devolve o instante que o
 * contrato exige.
 *
 * O formulario pedia `2026-08-14T12:00:00Z` digitado a mao. Agora pede uma data,
 * e o meio-dia UTC entra aqui. Meio-dia, e nao meia-noite: em America/Sao_Paulo
 * `00:00Z` e 21h do dia anterior, e um pagamento mudaria de dia sozinho.
 */
export function formDataDeRecebimento(formData: FormData, key: string): string | undefined {
  const bruto = formString(formData, key, 40);
  if (bruto === undefined) return undefined;
  // `isDate`, e nao so o formato: "2026-13-01" casa com a forma e nao existe.
  if (isDate(bruto)) return `${bruto}T12:00:00Z`;
  return isDateTime(bruto) ? bruto : undefined;
}

/**
 * Le um valor em dinheiro do formulario, aceitando a virgula decimal.
 *
 * O Credor digita "500,00", que e como se escreve dinheiro em portugues, e o
 * contrato exige "500.00". A troca e de pontuacao, feita por texto — nao ha
 * conta aqui, e o Motor continua sendo a unica autoridade sobre o valor.
 */
export function formMoney(formData: FormData, key: string): string | undefined {
  const bruto = formString(formData, key, 40);
  return normalizarMoeda(bruto);
}

export const formDecimalText = formMoney;

export function parseOpaqueRenegotiationParameters(value: string | undefined): Record<string, unknown> | undefined {
  if (!value) return undefined;
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    return undefined;
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return undefined;
  const entries = Object.entries(parsed);
  if (entries.length === 0) return undefined;
  if (entries.some(([key]) => FORBIDDEN_FINANCIAL_KEYS.test(key))) return undefined;
  return parsed as Record<string, unknown>;
}

export function parseOpaqueJson(formData: FormData, key: string): Record<string, unknown> | undefined {
  return parseOpaqueRenegotiationParameters(formString(formData, key, 5_000));
}

export function motorReferenceDate(value: string | undefined): string {
  return isDate(value) ? value : "2026-08-14";
}
