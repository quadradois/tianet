import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  CONTRATO_CLOSE_PERMISSION,
  CONTRATO_CREATE_PERMISSION,
  CONTRATO_READ_PERMISSION,
  CONTRATO_RELEASE_PERMISSION,
  CONTRATO_SIGN_PERMISSION,
  formString,
  hasExactPermission,
  isUuid,
  parseContractReason,
  type Contract,
  type ContractDecision,
  type ContractEvent,
  type ContractFilters,
  type ContractList,
  type ContratoActionState,
  type ContratoPermission,
  type ContratoReadResult,
  type ReleasedContract,
} from "../contratos/contratos-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type TypedClient = ReturnType<typeof createBackendClient>;
type ContractCreateRequest = components["schemas"]["ContratoCreditoCreateRequest"];
type DecisionRequest = components["schemas"]["DecisaoContratoRequest"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const CONTRACT_STATES = new Set(["rascunho", "formalizado", "assinado", "liberado_para_motor", "cancelado", "encerrado"]);

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

function nullableDateTime(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || dateTime(value[key]));
}

function nullableUuid(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || (typeof value[key] === "string" && UUID_PATTERN.test(value[key])));
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
      mensagem: "Contrato nao encontrado ou indisponivel.",
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
      mensagem: "Nao foi possivel concluir a operacao de Contratos.",
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

function validContract(value: unknown, context: OperationalContext, contratoId?: string): value is Contract {
  return isRecord(value)
    && strings(value, ["id", "tenant_id", "carteira_id", "devedor_id", "proposta_comercial_id", "criado_por_usuario_id", "criado_em"])
    && uuids(value, ["id", "tenant_id", "carteira_id", "devedor_id", "proposta_comercial_id", "criado_por_usuario_id"])
    && (contratoId === undefined || value.id === contratoId)
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && typeof value.estado === "string" && CONTRACT_STATES.has(value.estado)
    && opaqueObject(value.parametros)
    && dateTime(value.criado_em)
    && nullableDateTime(value, "atualizado_em")
    && nullableUuid(value, "formalizado_por_usuario_id")
    && nullableDateTime(value, "formalizado_em")
    && nullableUuid(value, "assinado_por_usuario_id")
    && nullableDateTime(value, "assinado_em")
    && nullableUuid(value, "liberado_por_usuario_id")
    && nullableDateTime(value, "liberado_em")
    && Object.hasOwn(value, "motivo_encerramento")
    && (value.motivo_encerramento === null || typeof value.motivo_encerramento === "string")
    && Number.isInteger(value.total_eventos);
}

function validContractList(value: unknown, context: OperationalContext): value is ContractList {
  return isRecord(value)
    && Array.isArray(value.items)
    && integers(value, ["total", "page", "size", "pages"])
    && value.items.every((item) => validContract(item, context));
}

function validEvent(value: unknown, contratoId: string): value is ContractEvent {
  return isRecord(value)
    && strings(value, ["id", "contrato_id", "usuario_id", "tipo", "criado_em"])
    && value.contrato_id === contratoId
    && uuids(value, ["id", "contrato_id", "usuario_id"])
    && typeof value.estado_anterior === "string" && CONTRACT_STATES.has(value.estado_anterior)
    && typeof value.estado_posterior === "string" && CONTRACT_STATES.has(value.estado_posterior)
    && Object.hasOwn(value, "motivo")
    && (value.motivo === null || typeof value.motivo === "string")
    && dateTime(value.criado_em);
}

function validReleased(value: unknown, context: OperationalContext, contratoId: string): value is ReleasedContract {
  return isRecord(value)
    && strings(value, ["contrato_id", "proposta_comercial_id", "tenant_id", "carteira_id", "devedor_id", "liberado_por_usuario_id", "liberado_em"])
    && uuids(value, ["contrato_id", "proposta_comercial_id", "tenant_id", "carteira_id", "devedor_id", "liberado_por_usuario_id"])
    && value.contrato_id === contratoId
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && opaqueObject(value.parametros_contratados)
    && dateTime(value.liberado_em);
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
  permission: ContratoPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<ContratoReadResult<T>> {
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

function problemState(problem: ApiProblem): ContratoActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function successState(message: string, correlation: string): ContratoActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

async function executeMutation(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: ContratoPermission,
  expectedStatus: 200 | 201,
  call: (client: TypedClient, carteiraId: string, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => boolean,
  message: string,
): Promise<ContratoActionState> {
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
    return successState(message, responseCorrelation(result.response, requestCorrelation));
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return problemState(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function listContracts(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  filters: ContractFilters,
  dependencies: BffDependencies,
): Promise<ContratoReadResult<ContractList>> {
  return executeRead(cookies, context, dependencies, CONTRATO_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/contratos",
    {
      params: {
        path: { carteira_id: carteiraId },
        query: {
          page: filters.page,
          size: filters.size,
          ...(filters.devedorId ? { devedor_id: filters.devedorId } : {}),
          ...(filters.estado ? { estado: filters.estado } : {}),
        },
        header: { "X-Correlation-ID": correlation },
      },
      signal,
    },
  ), (value): value is ContractList => validContractList(value, context));
}

export async function getContract(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  contratoId: string,
  dependencies: BffDependencies,
): Promise<ContratoReadResult<Contract>> {
  if (!isUuid(contratoId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Contrato invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, CONTRATO_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/contratos/{contrato_id}",
    { params: { path: { contrato_id: contratoId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Contract => validContract(value, context, contratoId));
}

export async function getContractHistory(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  contratoId: string,
  dependencies: BffDependencies,
): Promise<ContratoReadResult<readonly ContractEvent[]>> {
  if (!isUuid(contratoId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Contrato invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, CONTRATO_READ_PERMISSION, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/contratos/{contrato_id}/historico",
    { params: { path: { contrato_id: contratoId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is readonly ContractEvent[] => Array.isArray(value) && value.every((item) => validEvent(item, contratoId)));
}

export async function createContract(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ContratoActionState> {
  const propostaComercialId = formString(formData, "proposta_comercial_id", 36);
  if (!propostaComercialId || !isUuid(propostaComercialId)) return { kind: "problem", message: "Informe uma Proposta aprovada valida.", status: 400, correlationId: correlationId() };
  const body: ContractCreateRequest = { proposta_comercial_id: propostaComercialId };
  return executeMutation(cookies, context, dependencies, CONTRATO_CREATE_PERMISSION, 201, (client, carteiraId, correlation) => client.POST(
    "/credit/carteiras/{carteira_id}/contratos",
    { body, params: { path: { carteira_id: carteiraId }, header: { "X-Correlation-ID": correlation } } },
  ), (value): value is Contract => validContract(value, context), "Contrato formalizado a partir da Proposta aprovada.");
}

export async function decideContract(
  cookies: CookieStore,
  context: OperationalContext,
  contratoId: string,
  decision: ContractDecision,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ContratoActionState> {
  if (!isUuid(contratoId)) return { kind: "problem", message: "Identificador do Contrato invalido.", status: 400, correlationId: correlationId() };
  const motivo = parseContractReason(formData);
  const body: DecisionRequest = { ...(motivo ? { motivo } : {}) };
  const permission = decision === "assinar"
    ? CONTRATO_SIGN_PERMISSION
    : decision === "liberar-para-motor"
      ? CONTRATO_RELEASE_PERMISSION
      : CONTRATO_CLOSE_PERMISSION;
  return executeMutation(cookies, context, dependencies, permission, 200, (client, _carteiraId, correlation) => {
    const params = { path: { contrato_id: contratoId }, header: { "X-Correlation-ID": correlation } };
    if (decision === "assinar") return client.POST("/credit/contratos/{contrato_id}/assinar", { params });
    if (decision === "liberar-para-motor") return client.POST("/credit/contratos/{contrato_id}/liberar-para-motor", { params });
    if (decision === "cancelar") return client.POST("/credit/contratos/{contrato_id}/cancelar", { body, params });
    return client.POST("/credit/contratos/{contrato_id}/encerrar", { body, params });
  }, (value) => decision === "liberar-para-motor" ? validReleased(value, context, contratoId) : validContract(value, context, contratoId), "Acao contratual registrada.");
}
