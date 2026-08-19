import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  formDate,
  formDataDeRecebimento,
  formMoney,
  formString,
  hasExactPermission,
  isDate,
  isUuid,
  MOTOR_BALANCE_READ_PERMISSION,
  MOTOR_INSTALLMENT_CREATE_PERMISSION,
  MOTOR_INSTALLMENT_READ_PERMISSION,
  MOTOR_LOAN_CREATE_PERMISSION,
  MOTOR_LOAN_READ_PERMISSION,
  MOTOR_MEMORY_READ_PERMISSION,
  MOTOR_PAYMENT_CREATE_PERMISSION,
  MOTOR_RENEGOTIATION_CREATE_PERMISSION,
  MOTOR_SETTLEMENT_EXECUTE_PERMISSION,
  parseOpaqueRenegotiationParameters,
  type Balance,
  type CalculationMemory,
  type InstallmentPlan,
  type Loan,
  type LoanList,
  type MotorActionState,
  type MotorPermission,
  type MotorReadResult,
  type Payment,
  type Renegotiation,
  type Settlement,
  type SettlementPreview,
} from "../motor/motor-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type TypedClient = ReturnType<typeof createBackendClient>;
type PaymentCreateRequest = components["schemas"]["PagamentoCreateRequest"];
type PlanRequest = components["schemas"]["PlanoParcelasRequest"];
type SettlementRequest = components["schemas"]["QuitacaoRequest"];
type RenegotiationRequest = components["schemas"]["RenegociacaoCreateRequest"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const DECIMAL_PATTERN = /^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const LOAN_STATES = new Set(["ativo", "quitado", "cancelado"]);
const INSTALLMENT_STATES = new Set(["prevista", "vencida", "parcialmente_liquidada", "liquidada", "cancelada"]);
const PAYMENT_STATES = new Set(["recebido", "processado", "confirmado", "estornado"]);

type HeadersByPath = Readonly<{ path: string; idempotent: boolean }>;
const MOTOR_HEADER_CONTRACT: readonly HeadersByPath[] = [
  { path: "/credit/contratos/{contrato_id}/emprestimos", idempotent: true },
  { path: "/credit/emprestimos/{emprestimo_id}/pagamentos", idempotent: true },
  { path: "/credit/emprestimos/{emprestimo_id}/quitacao", idempotent: true },
  { path: "/credit/emprestimos/{emprestimo_id}/renegociacoes", idempotent: true },
  { path: "/credit/emprestimos/{emprestimo_id}/parcelas", idempotent: false },
];

void MOTOR_HEADER_CONTRACT;
const MOTOR_IDEMPOTENCY_MARKERS = [
  "Idempotency-Key:/credit/contratos/{contrato_id}/emprestimos",
  "Idempotency-Key:/credit/emprestimos/{emprestimo_id}/pagamentos",
  "Idempotency-Key:/credit/emprestimos/{emprestimo_id}/quitacao",
  "Idempotency-Key:/credit/emprestimos/{emprestimo_id}/renegociacoes",
  "sem-idempotency:/credit/emprestimos/{emprestimo_id}/parcelas",
] as const;
void MOTOR_IDEMPOTENCY_MARKERS;

function requiredIdempotencyKey(formData: FormData): string {
  const selected = idempotencyKey(true, formString(formData, "idempotency_key", 255));
  if (!selected) throw new ApiProblem({ status: 400, codigo: "idempotencia_invalida", mensagem: "Idempotency-Key invalida.", correlationId: correlationId() });
  return selected;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string");
}

function uuids(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string" && UUID_PATTERN.test(value[key]));
}

function integers(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => Number.isInteger(value[key]));
}

function calendarPartsAreValid(year: number, month: number, day: number): boolean {
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

function dateTime(value: unknown): boolean {
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

function decimal(value: unknown): boolean {
  return typeof value === "string" && DECIMAL_PATTERN.test(value);
}

function opaqueObject(value: unknown): value is Record<string, unknown> {
  return isRecord(value);
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

async function safeProblem(response: Response, fallback: string, errorBody?: unknown): Promise<ApiProblem> {
  const selectedCorrelation = responseCorrelation(response, fallback);
  if (response.status === 404) {
    return new ApiProblem({
      status: 404,
      codigo: "recurso_indisponivel",
      mensagem: "Emprestimo nao encontrado ou indisponivel.",
      correlationId: selectedCorrelation,
    });
  }
  if (response.status >= 500) {
    return new ApiProblem({
      status: response.status,
      codigo: "erro_tecnico",
      mensagem: "Servico temporariamente indisponivel.",
      correlationId: selectedCorrelation,
    });
  }
  if (isRecord(errorBody) && typeof errorBody.codigo === "string" && typeof errorBody.mensagem === "string") {
    return new ApiProblem({
      status: response.status,
      codigo: errorBody.codigo,
      mensagem: "Nao foi possivel concluir a operacao do Motor.",
      correlationId: selectedCorrelation,
    });
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

function validMemory(value: unknown): value is CalculationMemory {
  return isRecord(value)
    && strings(value, ["id", "tipo", "criado_em"])
    && uuids(value, ["id"])
    && opaqueObject(value.entradas)
    && opaqueObject(value.regra)
    && Array.isArray(value.periodos)
    && Array.isArray(value.passos)
    && value.passos.every((step) => isRecord(step)
      && typeof step.nome === "string"
      && opaqueObject(step.entradas)
      && opaqueObject(step.saidas)
      && Object.hasOwn(step, "arredondamento")
      && (step.arredondamento === null || typeof step.arredondamento === "string"))
    && Array.isArray(value.arredondamentos)
    && value.arredondamentos.every((item) => typeof item === "string")
    && opaqueObject(value.resultados)
    && dateTime(value.criado_em);
}

function validLoan(value: unknown, context: OperationalContext, loanId?: string): value is Loan {
  return isRecord(value)
    && strings(value, ["id", "contrato_id", "tenant_id", "carteira_id", "devedor_id", "estado", "principal_original", "moeda", "criado_em"])
    && uuids(value, ["id", "contrato_id", "tenant_id", "carteira_id", "devedor_id"])
    && (loanId === undefined || value.id === loanId)
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && typeof value.estado === "string"
    && LOAN_STATES.has(value.estado)
    && decimal(value.principal_original)
    && opaqueObject(value.parametros_financeiros)
    && dateTime(value.criado_em);
}

function validLoanList(value: unknown, context: OperationalContext): value is LoanList {
  return isRecord(value)
    && Array.isArray(value.items)
    && integers(value, ["total", "page", "size", "pages"])
    && value.items.every((item) => validLoan(item, context));
}

function validInstallment(value: unknown, loanId: string): boolean {
  return isRecord(value)
    && strings(value, ["id", "emprestimo_id", "vencimento", "valor_previsto", "principal", "juros", "encargos", "valor_liquidado", "estado"])
    && uuids(value, ["id", "emprestimo_id"])
    && value.emprestimo_id === loanId
    && Number.isInteger(value.numero)
    && isDate(value.vencimento)
    && decimal(value.valor_previsto)
    && decimal(value.principal)
    && decimal(value.juros)
    && decimal(value.encargos)
    && decimal(value.valor_liquidado)
    && typeof value.estado === "string"
    && INSTALLMENT_STATES.has(value.estado);
}

function validInstallmentPlan(value: unknown, context: OperationalContext, loanId: string): value is InstallmentPlan {
  return isRecord(value)
    && strings(value, ["emprestimo_id", "tenant_id"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && Array.isArray(value.parcelas)
    && value.parcelas.every((item) => validInstallment(item, loanId))
    && (!Object.hasOwn(value, "memoria") || value.memoria === null || validMemory(value.memoria));
}

function validPayment(value: unknown, context: OperationalContext, loanId: string): value is Payment {
  return isRecord(value)
    && strings(value, ["id", "emprestimo_id", "tenant_id", "valor_recebido", "recebido_em", "valor_juros", "valor_amortizacao", "valor_encargos", "estado"])
    && uuids(value, ["id", "emprestimo_id", "tenant_id"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && dateTime(value.recebido_em)
    && decimal(value.valor_recebido)
    && decimal(value.valor_juros)
    && decimal(value.valor_amortizacao)
    && decimal(value.valor_encargos)
    && typeof value.estado === "string"
    && PAYMENT_STATES.has(value.estado)
    && Object.hasOwn(value, "chave_idempotencia")
    && (value.chave_idempotencia === null || typeof value.chave_idempotencia === "string")
    && Array.isArray(value.parcelas_liquidadas)
    && value.parcelas_liquidadas.every((item) => typeof item === "string" && UUID_PATTERN.test(item))
    && (!Object.hasOwn(value, "memoria") || value.memoria === null || validMemory(value.memoria));
}

function validBalance(value: unknown, context: OperationalContext, loanId: string): value is Balance {
  return isRecord(value)
    && strings(value, ["emprestimo_id", "tenant_id", "data_referencia", "principal", "juros", "encargos", "total"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && isDate(value.data_referencia)
    && decimal(value.principal)
    && decimal(value.juros)
    && decimal(value.encargos)
    && decimal(value.total)
    && validMemory(value.memoria);
}

function validSettlementPreview(value: unknown, context: OperationalContext, loanId: string): value is SettlementPreview {
  return isRecord(value)
    && strings(value, ["emprestimo_id", "tenant_id"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && isRecord(value.valor_quitacao)
    && strings(value.valor_quitacao, ["valor_total", "moeda", "data_referencia"])
    && decimal(value.valor_quitacao.valor_total)
    && isDate(value.valor_quitacao.data_referencia)
    && opaqueObject(value.valor_quitacao.componentes)
    && Object.values(value.valor_quitacao.componentes).every(decimal)
    && validMemory(value.memoria);
}

function validSettlement(value: unknown, context: OperationalContext, loanId: string): value is Settlement {
  return isRecord(value)
    && strings(value, ["emprestimo_id", "tenant_id", "estado"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && typeof value.estado === "string"
    && LOAN_STATES.has(value.estado)
    && validPayment(value.pagamento, context, loanId)
    && validMemory(value.memoria_quitacao);
}

function validRenegotiation(value: unknown, context: OperationalContext, loanId: string): value is Renegotiation {
  return isRecord(value)
    && strings(value, ["emprestimo_id", "tenant_id"])
    && value.emprestimo_id === loanId
    && value.tenant_id === context.tenant.id
    && opaqueObject(value.novos_parametros)
    && validMemory(value.memoria);
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

async function executeRead<T>(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: MotorPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<MotorReadResult<T>> {
  if (!hasExactPermission(context.permissoes, permission)) return { kind: "denied" };
  const requestCorrelation = correlationId();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  try {
    const accessToken = await readAccessToken(cookies, dependencies, context);
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
    const result = await call(client, context.carteira_padrao.id, requestCorrelation, controller.signal);
    if (result.response.status !== 200) return { kind: "problem", problem: await safeProblem(result.response, requestCorrelation, result.error) };
    return validate(result.data)
      ? { kind: "ready", data: result.data }
      : { kind: "problem", problem: new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }) };
  } catch (error) {
    if (error instanceof ApiProblem) return { kind: "problem", problem: error };
    return { kind: "problem", problem: technicalProblem(requestCorrelation, controller.signal.aborted) };
  } finally {
    clearTimeout(timer);
  }
}

function problemState(problem: ApiProblem): MotorActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function successState(message: string, correlation: string, targetId?: string): MotorActionState {
  return { correlationId: correlation, kind: "success", message, status: 200, ...(targetId ? { targetId } : {}) };
}

async function executeMutation<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: MotorPermission,
  expectedStatus: 200 | 201,
  call: (client: TypedClient, carteiraId: string, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
  message: string,
  target: (value: T) => string | undefined = () => undefined,
): Promise<MotorActionState> {
  const requestCorrelation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    return problemState(new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: requestCorrelation }));
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const result = await call(client, context.carteira_padrao.id, requestCorrelation);
    if (result.response.status !== expectedStatus) return problemState(await safeProblem(result.response, requestCorrelation, result.error));
    if (!validate(result.data)) {
      return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }));
    }
    return successState(message, responseCorrelation(result.response, requestCorrelation), target(result.data));
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return problemState(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function listLoans(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  filters: { devedorId?: string; estado?: "ativo" | "quitado" | "cancelado"; page: number; size: number },
  dependencies: BffDependencies,
): Promise<MotorReadResult<LoanList>> {
  return executeRead(cookies, context, dependencies, MOTOR_LOAN_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/emprestimos",
    { params: { path: { carteira_id: carteiraId }, query: { page: filters.page, size: filters.size, ...(filters.estado ? { estado: filters.estado } : {}), ...(filters.devedorId ? { devedor_id: filters.devedorId } : {}) }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is LoanList => validLoanList(value, context));
}

export async function getLoan(cookies: ReadonlyCookieStore, context: OperationalContext, loanId: string, dependencies: BffDependencies): Promise<MotorReadResult<Loan>> {
  if (!isUuid(loanId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Emprestimo invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, MOTOR_LOAN_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/emprestimos/{emprestimo_id}",
    { params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Loan => validLoan(value, context, loanId));
}

export async function getInstallments(cookies: ReadonlyCookieStore, context: OperationalContext, loanId: string, dependencies: BffDependencies): Promise<MotorReadResult<InstallmentPlan>> {
  if (!isUuid(loanId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Emprestimo invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, MOTOR_INSTALLMENT_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/emprestimos/{emprestimo_id}/parcelas",
    { params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is InstallmentPlan => validInstallmentPlan(value, context, loanId));
}

export async function getBalance(cookies: ReadonlyCookieStore, context: OperationalContext, loanId: string, referenceDate: string, dependencies: BffDependencies): Promise<MotorReadResult<Balance>> {
  if (!isUuid(loanId) || !isDate(referenceDate)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Parametros do saldo invalidos.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, MOTOR_BALANCE_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/emprestimos/{emprestimo_id}/saldo",
    { params: { path: { emprestimo_id: loanId }, query: { data_referencia: referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Balance => validBalance(value, context, loanId));
}

export async function getMemories(cookies: ReadonlyCookieStore, context: OperationalContext, loanId: string, dependencies: BffDependencies): Promise<MotorReadResult<readonly CalculationMemory[]>> {
  if (!isUuid(loanId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Emprestimo invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, MOTOR_MEMORY_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/emprestimos/{emprestimo_id}/memoria-calculo",
    { params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is readonly CalculationMemory[] => Array.isArray(value) && value.every(validMemory));
}

export async function getSettlementPreview(cookies: ReadonlyCookieStore, context: OperationalContext, loanId: string, referenceDate: string, dependencies: BffDependencies): Promise<MotorReadResult<SettlementPreview>> {
  if (!isUuid(loanId) || !isDate(referenceDate)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Parametros da quitacao invalidos.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, MOTOR_SETTLEMENT_EXECUTE_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/emprestimos/{emprestimo_id}/quitacao",
    { params: { path: { emprestimo_id: loanId }, query: { data_referencia: referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is SettlementPreview => validSettlementPreview(value, context, loanId));
}

export const getCalculationMemory = getMemories;
export const getSettlementQuote = getSettlementPreview;

export async function createLoanFromContract(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<MotorActionState> {
  const contratoId = formString(formData, "contrato_id", 36);
  if (!contratoId || !isUuid(contratoId)) return { kind: "problem", message: "Informe um Contrato liberado valido.", status: 400, correlationId: correlationId() };
  return executeMutation(cookies, context, dependencies, MOTOR_LOAN_CREATE_PERMISSION, 201, (client, _carteiraId, correlation) => client.POST(
    "/credit/contratos/{contrato_id}/emprestimos",
    { params: { path: { contrato_id: contratoId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is Loan => validLoan(value, context), "Emprestimo criado pelo Motor.", (value) => value.id);
}

export async function createInstallmentPlan(cookies: CookieStore, context: OperationalContext, loanId: string, formData: FormData, dependencies: BffDependencies): Promise<MotorActionState> {
  const referenceDate = formDate(formData, "data_referencia");
  if (!isUuid(loanId) || !referenceDate) return { kind: "problem", message: "Informe data de referencia valida.", status: 400, correlationId: correlationId() };
  const body: PlanRequest = { data_referencia: referenceDate };
  return executeMutation(cookies, context, dependencies, MOTOR_INSTALLMENT_CREATE_PERMISSION, 200, (client, _carteiraId, correlation) => client.POST(
    "/credit/emprestimos/{emprestimo_id}/parcelas",
    { body, params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation } } },
  ), (value): value is InstallmentPlan => validInstallmentPlan(value, context, loanId), "Plano de parcelas gerado pelo Motor.");
}

export async function registerPayment(cookies: CookieStore, context: OperationalContext, loanId: string, formData: FormData, dependencies: BffDependencies): Promise<MotorActionState> {
  const valor = formMoney(formData, "valor");
  const recebidoEm = formDataDeRecebimento(formData, "recebido_em");
  if (!isUuid(loanId) || !valor || !recebidoEm) return { kind: "problem", message: "Informe pagamento valido.", status: 400, correlationId: correlationId() };
  const body: PaymentCreateRequest = { valor, recebido_em: recebidoEm };
  return executeMutation(cookies, context, dependencies, MOTOR_PAYMENT_CREATE_PERMISSION, 200, (client, _carteiraId, correlation) => client.POST(
    "/credit/emprestimos/{emprestimo_id}/pagamentos",
    { body, params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is Payment => validPayment(value, context, loanId), "Pagamento idempotente registrado pelo Motor.");
}

export async function executeSettlement(cookies: CookieStore, context: OperationalContext, loanId: string, formData: FormData, dependencies: BffDependencies): Promise<MotorActionState> {
  const recebidoEm = formDataDeRecebimento(formData, "recebido_em");
  if (!isUuid(loanId) || !recebidoEm) return { kind: "problem", message: "Informe data de quitacao valida.", status: 400, correlationId: correlationId() };
  const body: SettlementRequest = { recebido_em: recebidoEm };
  return executeMutation(cookies, context, dependencies, MOTOR_SETTLEMENT_EXECUTE_PERMISSION, 200, (client, _carteiraId, correlation) => client.POST(
    "/credit/emprestimos/{emprestimo_id}/quitacao",
    { body, params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is Settlement => validSettlement(value, context, loanId), "Quitacao oficial executada pelo Motor.");
}

export async function registerRenegotiation(cookies: CookieStore, context: OperationalContext, loanId: string, formData: FormData, dependencies: BffDependencies): Promise<MotorActionState> {
  const renegociadoEm = formDataDeRecebimento(formData, "renegociado_em");
  const novosParametros = parseOpaqueRenegotiationParameters(formString(formData, "novos_parametros", 5_000) ?? "");
  if (!isUuid(loanId) || !renegociadoEm || !novosParametros) return { kind: "problem", message: "Informe Renegociacao opaca valida.", status: 400, correlationId: correlationId() };
  const body: RenegotiationRequest = { novos_parametros: novosParametros, renegociado_em: renegociadoEm };
  return executeMutation(cookies, context, dependencies, MOTOR_RENEGOTIATION_CREATE_PERMISSION, 200, (client, _carteiraId, correlation) => client.POST(
    "/credit/emprestimos/{emprestimo_id}/renegociacoes",
    { body, params: { path: { emprestimo_id: loanId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is Renegotiation => validRenegotiation(value, context, loanId), "Renegociacao opaca registrada pelo Motor.");
}

export const createRenegotiation = registerRenegotiation;
