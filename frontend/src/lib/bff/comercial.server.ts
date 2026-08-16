import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  COMERCIAL_PROPOSAL_CREATE_PERMISSION,
  COMERCIAL_PROPOSAL_DECIDE_PERMISSION,
  COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION,
  COMERCIAL_PROPOSAL_READ_PERMISSION,
  COMERCIAL_SIMULATION_CREATE_PERMISSION,
  formString,
  hasExactPermission,
  isUuid,
  parseOpaqueParameters,
  type ApprovedProposalContract,
  type ComercialActionState,
  type ComercialPermission,
  type ComercialReadResult,
  type Proposal,
  type ProposalFilters,
  type ProposalList,
  type Simulation,
} from "../comercial/comercial-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type TypedClient = ReturnType<typeof createBackendClient>;
type SimulationCreateRequest = components["schemas"]["SimulacaoComercialCreateRequest"];
type ProposalCreateRequest = components["schemas"]["PropostaComercialCreateRequest"];
type ProposalUpdateRequest = components["schemas"]["PropostaComercialUpdateRequest"];
type DecisionRequest = components["schemas"]["DecisaoComercialRequest"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const PROPOSAL_STATES = new Set(["rascunho", "em_analise", "aprovada", "recusada", "cancelada", "expirada"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string");
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
      mensagem: "Recurso comercial nao encontrado ou indisponivel.",
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
      mensagem: "Nao foi possivel concluir a operacao Comercial.",
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

function validSimulation(value: unknown, context: OperationalContext, devedorId?: string, simulacaoId?: string): value is Simulation {
  return isRecord(value)
    && strings(value, ["id", "tenant_id", "carteira_id", "devedor_id", "criada_por_usuario_id", "criado_em"])
    && UUID_PATTERN.test(String(value.id))
    && (simulacaoId === undefined || value.id === simulacaoId)
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && (devedorId === undefined || value.devedor_id === devedorId)
    && dateTime(value.criado_em)
    && opaqueObject(value.parametros);
}

function validProposal(value: unknown, context: OperationalContext, devedorId?: string): value is Proposal {
  return isRecord(value)
    && strings(value, ["id", "tenant_id", "carteira_id", "devedor_id", "criada_por_usuario_id", "criado_em"])
    && UUID_PATTERN.test(String(value.id))
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && (devedorId === undefined || value.devedor_id === devedorId)
    && nullableUuid(value, "simulacao_id")
    && typeof value.estado === "string" && PROPOSAL_STATES.has(value.estado)
    && opaqueObject(value.parametros)
    && dateTime(value.criado_em)
    && nullableDateTime(value, "atualizado_em")
    && nullableUuid(value, "aprovada_por_usuario_id")
    && nullableDateTime(value, "aprovada_em")
    && Number.isInteger(value.total_decisoes);
}

function validProposalList(value: unknown, context: OperationalContext, devedorId: string): value is ProposalList {
  return isRecord(value)
    && Array.isArray(value.items)
    && integers(value, ["total", "page", "size", "pages"])
    && value.items.every((item) => validProposal(item, context, devedorId));
}

function validApprovedContract(value: unknown, context: OperationalContext): value is ApprovedProposalContract {
  return isRecord(value)
    && strings(value, ["proposta_id", "tenant_id", "carteira_id", "devedor_id", "aprovada_por_usuario_id", "aprovada_em"])
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id
    && opaqueObject(value.parametros_aprovados)
    && dateTime(value.aprovada_em);
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
  permission: ComercialPermission,
  expectedStatus: 200,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<ComercialReadResult<T>> {
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
    if (result.response.status !== expectedStatus) return { kind: "problem", problem: await safeProblem(result.response, requestCorrelation, result.error) };
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

function problemState(problem: ApiProblem): ComercialActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function successState(message: string, correlation: string): ComercialActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

async function executeMutation(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: ComercialPermission,
  expectedStatus: 200 | 201,
  call: (client: TypedClient, carteiraId: string, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is Proposal | Simulation,
  message: string,
): Promise<ComercialActionState> {
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

export async function listCommercialProposals(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  devedorId: string,
  filters: ProposalFilters,
  dependencies: BffDependencies,
): Promise<ComercialReadResult<ProposalList>> {
  if (!isUuid(devedorId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Devedor invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, COMERCIAL_PROPOSAL_READ_PERMISSION, 200, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    {
      params: {
        path: { carteira_id: carteiraId, devedor_id: devedorId },
        query: { page: filters.page, size: filters.size, ...(filters.estado ? { estado: filters.estado } : {}) },
        header: { "X-Correlation-ID": correlation },
      },
      signal,
    },
  ), (value): value is ProposalList => validProposalList(value, context, devedorId));
}

export async function getCommercialProposal(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  propostaId: string,
  dependencies: BffDependencies,
): Promise<ComercialReadResult<Proposal>> {
  if (!isUuid(propostaId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador da Proposta invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, COMERCIAL_PROPOSAL_READ_PERMISSION, 200, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/propostas-comerciais/{proposta_id}",
    { params: { path: { proposta_id: propostaId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Proposal => validProposal(value, context));
}

export async function getCommercialSimulation(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  simulacaoId: string,
  dependencies: BffDependencies,
  devedorId?: string,
): Promise<ComercialReadResult<Simulation>> {
  if (!isUuid(simulacaoId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador da Simulacao invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, COMERCIAL_PROPOSAL_READ_PERMISSION, 200, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/simulacoes-comerciais/{simulacao_id}",
    { params: { path: { simulacao_id: simulacaoId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Simulation => validSimulation(value, context, devedorId, simulacaoId));
}

export async function getApprovedProposalContract(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  propostaId: string,
  dependencies: BffDependencies,
): Promise<ComercialReadResult<ApprovedProposalContract>> {
  if (!isUuid(propostaId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador da Proposta invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, COMERCIAL_PROPOSAL_INTEGRATE_PERMISSION, 200, (client, _carteiraId, correlation, signal) => client.GET(
    "/credit/propostas-comerciais/{proposta_id}/contrato-logico",
    { params: { path: { proposta_id: propostaId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is ApprovedProposalContract => validApprovedContract(value, context));
}

export async function createCommercialSimulation(
  cookies: CookieStore,
  context: OperationalContext,
  devedorId: string,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ComercialActionState> {
  if (!isUuid(devedorId)) return { kind: "problem", message: "Identificador do Devedor invalido.", status: 400, correlationId: correlationId() };
  const parametros = parseOpaqueParameters(formString(formData, "parametros", 5_000) ?? "");
  if (!parametros) return { kind: "problem", message: "Informe parametros comerciais em JSON objeto nao vazio.", status: 400, correlationId: correlationId() };
  const body: SimulationCreateRequest = { parametros };
  return executeMutation(cookies, context, dependencies, COMERCIAL_SIMULATION_CREATE_PERMISSION, 201, (client, carteiraId, correlation) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
    { body, params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "X-Correlation-ID": correlation } } },
  ), (value): value is Simulation => validSimulation(value, context, devedorId), "Simulacao comercial registrada.");
}

export async function createCommercialProposal(
  cookies: CookieStore,
  context: OperationalContext,
  devedorId: string,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ComercialActionState> {
  if (!isUuid(devedorId)) return { kind: "problem", message: "Identificador do Devedor invalido.", status: 400, correlationId: correlationId() };
  const parametros = parseOpaqueParameters(formString(formData, "parametros", 5_000) ?? "");
  if (!parametros) return { kind: "problem", message: "Informe parametros comerciais em JSON objeto nao vazio.", status: 400, correlationId: correlationId() };
  const simulacaoId = formString(formData, "simulacao_id", 36);
  if (simulacaoId && !isUuid(simulacaoId)) return { kind: "problem", message: "Identificador da Simulacao invalido.", status: 400, correlationId: correlationId() };
  const body: ProposalCreateRequest = { parametros, ...(simulacaoId ? { simulacao_id: simulacaoId } : {}) };
  return executeMutation(cookies, context, dependencies, COMERCIAL_PROPOSAL_CREATE_PERMISSION, 201, (client, carteiraId, correlation) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    { body, params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "X-Correlation-ID": correlation } } },
  ), (value): value is Proposal => validProposal(value, context, devedorId), "Proposta comercial criada.");
}

export async function updateCommercialProposal(
  cookies: CookieStore,
  context: OperationalContext,
  propostaId: string,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ComercialActionState> {
  if (!isUuid(propostaId)) return { kind: "problem", message: "Identificador da Proposta invalido.", status: 400, correlationId: correlationId() };
  const parametros = parseOpaqueParameters(formString(formData, "parametros", 5_000) ?? "");
  if (!parametros) return { kind: "problem", message: "Informe parametros comerciais em JSON objeto nao vazio.", status: 400, correlationId: correlationId() };
  const body: ProposalUpdateRequest = { parametros };
  return executeMutation(cookies, context, dependencies, COMERCIAL_PROPOSAL_CREATE_PERMISSION, 200, (client, _carteiraId, correlation) => client.PATCH(
    "/credit/propostas-comerciais/{proposta_id}",
    { body, params: { path: { proposta_id: propostaId }, header: { "X-Correlation-ID": correlation } } },
  ), (value): value is Proposal => validProposal(value, context), "Proposta comercial atualizada.");
}

export async function decideCommercialProposal(
  cookies: CookieStore,
  context: OperationalContext,
  propostaId: string,
  decision: "enviar-para-analise" | "aprovar" | "recusar" | "cancelar" | "expirar",
  formData: FormData,
  dependencies: BffDependencies,
): Promise<ComercialActionState> {
  if (!isUuid(propostaId)) return { kind: "problem", message: "Identificador da Proposta invalido.", status: 400, correlationId: correlationId() };
  const motivo = formString(formData, "motivo", 500);
  const body: DecisionRequest = { ...(motivo ? { motivo } : {}) };
  return executeMutation(cookies, context, dependencies, COMERCIAL_PROPOSAL_DECIDE_PERMISSION, 200, (client, _carteiraId, correlation) => {
    const params = { path: { proposta_id: propostaId }, header: { "X-Correlation-ID": correlation } };
    if (decision === "enviar-para-analise") return client.POST("/credit/propostas-comerciais/{proposta_id}/enviar-para-analise", { params });
    if (decision === "aprovar") return client.POST("/credit/propostas-comerciais/{proposta_id}/aprovar", { params });
    if (decision === "recusar") return client.POST("/credit/propostas-comerciais/{proposta_id}/recusar", { body, params });
    if (decision === "cancelar") return client.POST("/credit/propostas-comerciais/{proposta_id}/cancelar", { body, params });
    return client.POST("/credit/propostas-comerciais/{proposta_id}/expirar", { params });
  }, (value): value is Proposal => validProposal(value, context), "Decisao comercial registrada.");
}
