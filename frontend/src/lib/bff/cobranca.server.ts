import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  COBRANCA_ACTION_REGISTER_PERMISSION,
  COBRANCA_CASE_READ_PERMISSION,
  COBRANCA_PROMISE_APPROPRIATE_PERMISSION,
  COBRANCA_PROMISE_REGISTER_PERMISSION,
  formActionType,
  formBoolean,
  formDate,
  formMoney,
  formString,
  formUuid,
  hasExactPermission,
  type CobrancaActionState,
  type CobrancaPermission,
  type CobrancaReadResult,
  type CollectionAction,
  type CollectionFilters,
  type CollectionQueue,
  type PaymentPromise,
  type PromiseAppropriation,
} from "../cobranca/cobranca-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;
type ActionRequest = components["schemas"]["AcaoCobrancaCreateRequest"];
type PromiseRequest = components["schemas"]["PromessaPagamentoCreateRequest"];
type AppropriationRequest = components["schemas"]["ApropriacaoPagamentoCreateRequest"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const DECIMAL_PATTERN = /^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const COLLECTION_STATES = new Set(["pendente", "em_andamento", "encerrado"]);
const ACTION_TYPES = new Set(["contato", "telefone", "email", "visita", "outro"]);
const PROMISE_STATES = new Set(["pendente", "pagamento_informado", "cumprida", "descumprida"]);

const COBRANCA_HEADER_CONTRACT = [
  { path: "/credit/cobrancas/casos", idempotent: false },
  { path: "/credit/cobrancas/casos/{cobranca_caso_id}/acoes", idempotent: true },
  { path: "/credit/cobrancas/casos/{cobranca_caso_id}/promessas", idempotent: true },
  { path: "/credit/cobrancas/promessas/{promessa_id}/apropriacoes", idempotent: true },
] as const;
void COBRANCA_HEADER_CONTRACT;

const COBRANCA_IDEMPOTENCY_MARKERS = [
  "sem-idempotency:/credit/cobrancas/casos",
  "Idempotency-Key:/credit/cobrancas/casos/{cobranca_caso_id}/acoes",
  "Idempotency-Key:/credit/cobrancas/casos/{cobranca_caso_id}/promessas",
  "Idempotency-Key:/credit/cobrancas/promessas/{promessa_id}/apropriacoes",
] as const;
void COBRANCA_IDEMPOTENCY_MARKERS;

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

function nullableUuid(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || (typeof value[key] === "string" && UUID_PATTERN.test(value[key])));
}

function calendarPartsAreValid(year: number, month: number, day: number): boolean {
  const probe = new Date(0);
  probe.setUTCFullYear(year, month - 1, day);
  probe.setUTCHours(0, 0, 0, 0);
  return probe.getUTCFullYear() === year && probe.getUTCMonth() + 1 === month && probe.getUTCDate() === day;
}

function date(value: unknown): boolean {
  if (typeof value !== "string" || !DATE_PATTERN.test(value)) return false;
  const [year = 0, month = 0, day = 0] = value.split("-").map(Number);
  return calendarPartsAreValid(year, month, day);
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
  return calendarPartsAreValid(year, month, day) && hour <= 23 && minute <= 59 && second <= 59 && offsetHour <= 23 && offsetMinute <= 59;
}

function decimal(value: unknown): boolean {
  return typeof value === "string" && DECIMAL_PATTERN.test(value);
}

function matchesContext(value: unknown, context: OperationalContext): boolean {
  return isRecord(value)
    && uuids(value, ["tenant_id", "carteira_id"])
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id;
}

function validCase(value: unknown, context: OperationalContext): boolean {
  return isRecord(value)
    && matchesContext(value, context)
    && uuids(value, ["caso_id", "devedor_id"])
    && nullableUuid(value, "emprestimo_id")
    && strings(value, ["titulo", "origem"])
    && typeof value.estado === "string"
    && COLLECTION_STATES.has(value.estado)
    && decimal(value.total_pendente)
    && dateTime(value.criado_em);
}

function validQueue(value: unknown, context: OperationalContext): value is CollectionQueue {
  return isRecord(value)
    && Number.isInteger(value.total)
    && Array.isArray(value.items)
    && value.items.every((item) => validCase(item, context));
}

function validAction(value: unknown, context: OperationalContext, caseId: string): value is CollectionAction {
  return isRecord(value)
    && matchesContext(value, context)
    && uuids(value, ["acao_id", "caso_id", "emprestimo_id", "tenant_id", "carteira_id", "usuario_id"])
    && value.caso_id === caseId
    && nullableUuid(value, "devedor_id")
    && typeof value.tipo === "string"
    && ACTION_TYPES.has(value.tipo)
    && typeof value.resultado === "string"
    && dateTime(value.registrada_em);
}

function validPromise(value: unknown, context: OperationalContext, caseId: string): value is PaymentPromise {
  void caseId;
  return isRecord(value)
    && matchesContext(value, context)
    && uuids(value, ["promessa_id", "tenant_id", "carteira_id", "devedor_id", "emprestimo_id"])
    && typeof value.estado === "string"
    && PROMISE_STATES.has(value.estado)
    && decimal(value.valor_declarado)
    && date(value.data_promessa);
}

function validAppropriation(value: unknown, _context: OperationalContext, promiseId: string): value is PromiseAppropriation {
  return isRecord(value)
    && uuids(value, ["apropriacao_id", "promessa_id", "pagamento_id"])
    && value.promessa_id === promiseId
    && typeof value.estado_promessa === "string"
    && PROMISE_STATES.has(value.estado_promessa)
    && decimal(value.valor)
    && dateTime(value.realizado_em);
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
      mensagem: "Caso de cobranca nao encontrado ou indisponivel.",
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
      mensagem: "Nao foi possivel concluir a operacao de Cobranca.",
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

function problemState(problem: ApiProblem): CobrancaActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function successState(message: string, correlation: string): CobrancaActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

async function executeRead<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: CobrancaPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<CobrancaReadResult<T>> {
  if (!hasExactPermission(context.permissoes, permission)) return { kind: "denied" };
  const requestCorrelation = correlationId();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
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

async function executeMutation<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: CobrancaPermission,
  call: (client: TypedClient, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
  message: string,
): Promise<CobrancaActionState> {
  const requestCorrelation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    return problemState(new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: requestCorrelation }));
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const result = await call(client, requestCorrelation);
    if (result.response.status !== 200) return problemState(await safeProblem(result.response, requestCorrelation, result.error));
    if (!validate(result.data)) return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }));
    return successState(message, responseCorrelation(result.response, requestCorrelation));
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return problemState(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function listCollectionCases(
  cookies: CookieStore,
  context: OperationalContext,
  filters: CollectionFilters,
  dependencies: BffDependencies,
): Promise<CobrancaReadResult<CollectionQueue>> {
  return executeRead(cookies, context, dependencies, COBRANCA_CASE_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/cobrancas/casos",
    { params: { query: { carteira_id: carteiraId, ...(filters.devedorId ? { devedor_id: filters.devedorId } : {}), ...(filters.estado ? { estado: filters.estado } : {}) }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is CollectionQueue => validQueue(value, context));
}

export async function registerCollectionAction(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<CobrancaActionState> {
  const caseId = formUuid(formData, "caso_id") ?? formUuid(formData, "cobranca_caso_id");
  const tipo = formActionType(formData);
  const resultado = formString(formData, "resultado", 1_000);
  if (!caseId || !tipo || !resultado) return { kind: "problem", message: "Informe acao de cobranca valida.", status: 400, correlationId: correlationId() };
  const body: ActionRequest = { tipo, resultado };
  return executeMutation(cookies, context, dependencies, COBRANCA_ACTION_REGISTER_PERMISSION, (client, correlation) => client.POST(
    "/credit/cobrancas/casos/{cobranca_caso_id}/acoes",
    { body, params: { path: { cobranca_caso_id: caseId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is CollectionAction => validAction(value, context, caseId), "Acao de cobranca registrada.");
}

export async function registerPaymentPromise(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<CobrancaActionState> {
  const caseId = formUuid(formData, "caso_id") ?? formUuid(formData, "cobranca_caso_id");
  const valorDeclarado = formMoney(formData, "valor_declarado");
  const dataPromessa = formDate(formData, "data_promessa");
  if (!caseId || !valorDeclarado || !dataPromessa) return { kind: "problem", message: "Informe promessa declaratoria valida.", status: 400, correlationId: correlationId() };
  const observacao = formString(formData, "observacao", 1_000);
  const body: PromiseRequest = {
    data_promessa: dataPromessa,
    pagamento_informado: formBoolean(formData, "pagamento_informado"),
    valor_declarado: valorDeclarado,
    ...(observacao ? { observacao } : {}),
  };
  return executeMutation(cookies, context, dependencies, COBRANCA_PROMISE_REGISTER_PERMISSION, (client, correlation) => client.POST(
    "/credit/cobrancas/casos/{cobranca_caso_id}/promessas",
    { body, params: { path: { cobranca_caso_id: caseId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is PaymentPromise => validPromise(value, context, caseId), "Promessa declaratoria registrada sem calculo local.");
}

export async function appropriatePaymentPromise(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<CobrancaActionState> {
  const promiseId = formUuid(formData, "promessa_id");
  const pagamentoId = formUuid(formData, "pagamento_id");
  if (!promiseId || !pagamentoId) return { kind: "problem", message: "Informe apropriacao de pagamento oficial valida.", status: 400, correlationId: correlationId() };
  const dataReferencia = formDate(formData, "data_referencia");
  const body: AppropriationRequest = { pagamento_id: pagamentoId, ...(dataReferencia ? { data_referencia: dataReferencia } : {}) };
  return executeMutation(cookies, context, dependencies, COBRANCA_PROMISE_APPROPRIATE_PERMISSION, (client, correlation) => client.POST(
    "/credit/cobrancas/promessas/{promessa_id}/apropriacoes",
    { body, params: { path: { promessa_id: promiseId }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": requiredIdempotencyKey(formData) } } },
  ), (value): value is PromiseAppropriation => validAppropriation(value, context, promiseId), "Pagamento oficial apropriado a promessa.");
}
