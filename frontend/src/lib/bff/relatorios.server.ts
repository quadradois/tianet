import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  hasExactPermission,
  REPORTS_PERMISSION,
  type CashFlowReport,
  type DueDatesReport,
  type PaymentsReport,
  type ReportsPeriod,
  type SummaryReport,
} from "../relatorios/relatorios-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;
type ReadonlyCookieStore = Pick<CookieStore, "get">;
type PaymentState = components["schemas"]["PagamentoState"];
type ParcelState = components["schemas"]["ParcelaState"];

export type ReportsSectionResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ApiProblem }>;

export type ReportsLoads = Readonly<{
  summary: Promise<ReportsSectionResult<SummaryReport>>;
  dueDates: Promise<ReportsSectionResult<DueDatesReport>>;
  payments: Promise<ReportsSectionResult<PaymentsReport>>;
  cashFlow: Promise<ReportsSectionResult<CashFlowReport>>;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const DECIMAL_PATTERN = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const PARCELA_STATES: ReadonlySet<string> = new Set<ParcelState>(["prevista", "vencida", "parcialmente_liquidada", "liquidada", "cancelada"]);
const PAYMENT_STATES: ReadonlySet<string> = new Set<PaymentState>(["recebido", "processado", "confirmado", "estornado"]);

const RELATORIOS_HEADER_CONTRACT = [
  { path: "/credit/carteiras/{carteira_id}/relatorios/resumo", idempotent: false },
  { path: "/credit/carteiras/{carteira_id}/relatorios/vencimentos", idempotent: false },
  { path: "/credit/carteiras/{carteira_id}/relatorios/pagamentos", idempotent: false },
  { path: "/credit/carteiras/{carteira_id}/relatorios/fluxo", idempotent: false },
] as const;
void RELATORIOS_HEADER_CONTRACT;

const RELATORIOS_IDEMPOTENCY_MARKERS = [
  "sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/resumo",
  "sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/vencimentos",
  "sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/pagamentos",
  "sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/fluxo",
] as const;
void RELATORIOS_IDEMPOTENCY_MARKERS;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string");
}

function integers(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => Number.isInteger(value[key]));
}

function uuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function uuids(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => uuid(value[key]));
}

function calendarPartsAreValid(year: number, month: number, day: number): boolean {
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

function calendarDate(value: unknown): boolean {
  if (typeof value !== "string" || !DATE_PATTERN.test(value)) return false;
  const [year = 0, month = 0, day = 0] = value.split("-").map(Number);
  return calendarPartsAreValid(year, month, day);
}

function decimal(value: unknown): boolean {
  return typeof value === "string" && DECIMAL_PATTERN.test(value);
}

function decimalStrings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => decimal(value[key]));
}

function matchesContext(value: unknown, context: OperationalContext): boolean {
  return isRecord(value)
    && uuids(value, ["tenant_id", "carteira_id"])
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id;
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

async function safeProblem(response: Response, fallback: string, errorBody?: unknown): Promise<ApiProblem> {
  const selectedCorrelation = responseCorrelation(response, fallback);
  if (response.status !== 200 && response.status < 400) {
    return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: selectedCorrelation });
  }
  if (response.status === 400) {
    return new ApiProblem({ status: 400, codigo: "periodo_invalido", mensagem: "O periodo informado e invalido.", correlationId: selectedCorrelation });
  }
  if (response.status === 401) {
    return new ApiProblem({ status: 401, codigo: "sessao_expirada", mensagem: "A sessao precisa ser renovada.", correlationId: selectedCorrelation });
  }
  if (response.status === 403) {
    return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Relatorios indisponiveis para este acesso.", correlationId: selectedCorrelation });
  }
  if (response.status === 404) {
    return new ApiProblem({ status: 404, codigo: "recurso_indisponivel", mensagem: "Dados de relatorio nao encontrados ou indisponiveis.", correlationId: selectedCorrelation });
  }
  if (response.status > 404 && response.status < 500) {
    return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Nao foi possivel concluir a consulta de Relatorios.", correlationId: selectedCorrelation });
  }
  if (response.status >= 500) {
    return new ApiProblem({ status: response.status, codigo: "erro_tecnico", mensagem: "Servico temporariamente indisponivel.", correlationId: selectedCorrelation });
  }
  if (isRecord(errorBody) && typeof errorBody.codigo === "string" && typeof errorBody.mensagem === "string") {
    return new ApiProblem({ status: response.status, codigo: errorBody.codigo, mensagem: "Nao foi possivel concluir a consulta de Relatorios.", correlationId: selectedCorrelation });
  }
  return apiProblemFromResponse(response, fallback);
}

function technicalProblem(correlation: string, timeout: boolean): ApiProblem {
  return new ApiProblem({
    status: timeout ? 504 : 502,
    codigo: timeout ? "timeout_backend" : "backend_indisponivel",
    mensagem: timeout ? "O servico nao respondeu no tempo esperado." : "Servico temporariamente indisponivel.",
    correlationId: correlation,
  });
}

function validSummary(value: unknown, context: OperationalContext, period: ReportsPeriod): value is SummaryReport {
  if (!matchesContext(value, context) || !isRecord(value)) return false;
  return strings(value, ["data_referencia"])
    && value.data_referencia === period.referenceDate
    && calendarDate(value.data_referencia)
    && integers(value, ["total_operacoes", "operacoes_ativas", "operacoes_quitadas", "acertos_pendentes"])
    && decimalStrings(value, ["principal_a_receber", "total_realizado"]);
}

function validDueDates(value: unknown, context: OperationalContext, period: ReportsPeriod): value is DueDatesReport {
  if (!matchesContext(value, context) || !isRecord(value)) return false;
  return calendarDate(value.data_referencia)
    && value.data_referencia === period.referenceDate
    && Number.isInteger(value.total)
    && Array.isArray(value.itens)
    && value.itens.every((item) => isRecord(item)
      && uuids(item, ["emprestimo_id", "parcela_id"])
      && Number.isInteger(item.numero)
      && calendarDate(item.vencimento)
      && decimalStrings(item, ["valor_previsto", "valor_liquidado"])
      && typeof item.estado === "string" && PARCELA_STATES.has(item.estado)
      && typeof item.situacao === "string");
}

function validPayments(value: unknown, context: OperationalContext, period: ReportsPeriod): value is PaymentsReport {
  if (!matchesContext(value, context) || !isRecord(value)) return false;
  return calendarDate(value.inicio)
    && calendarDate(value.fim)
    && value.inicio === period.startDate
    && value.fim === period.endDate
    && decimal(value.total_realizado)
    && Array.isArray(value.operacoes_quitadas)
    && value.operacoes_quitadas.every(uuid)
    && Array.isArray(value.pagamentos)
    && value.pagamentos.every((item) => isRecord(item)
      && uuids(item, ["pagamento_id", "emprestimo_id"])
      && calendarDate(item.recebido_em)
      && decimal(item.valor_recebido)
      && typeof item.estado === "string" && PAYMENT_STATES.has(item.estado));
}

function validCashFlow(value: unknown, context: OperationalContext, period: ReportsPeriod): value is CashFlowReport {
  if (!matchesContext(value, context) || !isRecord(value)) return false;
  return calendarDate(value.inicio)
    && calendarDate(value.fim)
    && value.inicio === period.startDate
    && value.fim === period.endDate
    && Array.isArray(value.itens)
    && value.itens.every((item) => isRecord(item)
      && calendarDate(item.data)
      && decimalStrings(item, ["previsto", "realizado"])
      && Array.isArray(item.parcela_ids) && item.parcela_ids.every(uuid)
      && Array.isArray(item.pagamento_ids) && item.pagamento_ids.every(uuid));
}

async function readAccessToken(cookies: ReadonlyCookieStore, dependencies: BffDependencies, context: OperationalContext): Promise<string> {
  const encrypted = cookies.get(sessionCookieName(dependencies.config))?.value;
  if (!encrypted) throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: correlationId() });
  try {
    const session = await unsealSession(encrypted, dependencies.config, dependencies.now?.() ?? new Date());
    if (session.userId !== context.usuario.id || session.tenantId !== context.tenant.id) throw new Error("identity mismatch");
    return session.accessToken;
  } catch {
    throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: correlationId() });
  }
}

async function execute<T>(
  dependencies: BffDependencies,
  accessToken: string,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
  carteiraId: string,
): Promise<ReportsSectionResult<T>> {
  const requestCorrelation = correlationId();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  try {
    const backendOrigin = new URL(dependencies.config.backendUrl).origin;
    const client = createBackendClient(dependencies.config.backendUrl, {
      fetch: async (request) => {
        if (new URL(request.url).origin !== backendOrigin) throw technicalProblem(requestCorrelation, false);
        const headers = new Headers(request.headers);
        headers.set("Authorization", `Bearer ${accessToken}`);
        headers.set("X-Correlation-ID", requestCorrelation);
        return dependencies.fetch(new Request(request, { cache: "no-store", headers, redirect: "error", signal: controller.signal }));
      },
    });
    const result = await call(client, carteiraId, requestCorrelation, controller.signal);
    if (result.response.status !== 200) return { kind: "problem", problem: await safeProblem(result.response, requestCorrelation, result.error) };
    if (validate(result.data)) return { kind: "ready", data: result.data };
    return { kind: "problem", problem: new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }) };
  } catch (error) {
    if (error instanceof ApiProblem) return { kind: "problem", problem: error };
    return { kind: "problem", problem: technicalProblem(requestCorrelation, controller.signal.aborted) };
  } finally {
    clearTimeout(timer);
  }
}

function denied<T>(): Promise<ReportsSectionResult<T>> {
  return Promise.resolve({ kind: "denied" });
}

export async function beginReportsLoads(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  period: ReportsPeriod,
  dependencies: BffDependencies,
): Promise<ReportsLoads> {
  const allowed = hasExactPermission(context.permissoes, REPORTS_PERMISSION);
  if (!allowed) return { summary: denied(), dueDates: denied(), payments: denied(), cashFlow: denied() };
  const accessToken = await readAccessToken(cookies, dependencies, context);
  const carteiraId = context.carteira_padrao.id;
  return {
    summary: execute(dependencies, accessToken, (client, selectedCarteira, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/resumo",
      { params: { path: { carteira_id: selectedCarteira }, query: { data_referencia: period.referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is SummaryReport => validSummary(value, context, period), carteiraId),
    dueDates: execute(dependencies, accessToken, (client, selectedCarteira, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/vencimentos",
      { params: { path: { carteira_id: selectedCarteira }, query: { data_referencia: period.referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is DueDatesReport => validDueDates(value, context, period), carteiraId),
    payments: execute(dependencies, accessToken, (client, selectedCarteira, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/pagamentos",
      { params: { path: { carteira_id: selectedCarteira }, query: { inicio: period.startDate, fim: period.endDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is PaymentsReport => validPayments(value, context, period), carteiraId),
    cashFlow: execute(dependencies, accessToken, (client, selectedCarteira, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/fluxo",
      { params: { path: { carteira_id: selectedCarteira }, query: { inicio: period.startDate, fim: period.endDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is CashFlowReport => validCashFlow(value, context, period), carteiraId),
  };
}
