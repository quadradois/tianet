import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import { createBackendClient } from "@/lib/api/client.server";
import {
  DEVEDOR_CREATE_PERMISSION,
  DEVEDOR_INACTIVATE_PERMISSION,
  DEVEDOR_REACTIVATE_PERMISSION,
  DEVEDOR_READ_PERMISSION,
  DEVEDOR_UPDATE_PERMISSION,
  formBoolean,
  formString,
  hasExactPermission,
  isUuid,
  type Devedor,
  type DevedorActionState,
  type DevedorHistory,
  type DevedorListFilters,
  type DevedorPermission,
  type DevedoresList,
  type DevedoresReadResult,
} from "@/lib/devedores/devedores-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type DevedorCreateRequest = components["schemas"]["DevedorCreateRequest"];
type DevedorUpdateRequest = components["schemas"]["DevedorUpdateRequest"];

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type TypedClient = ReturnType<typeof createBackendClient>;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const DEVEDOR_STATES = new Set(["ativo", "inativo"]);
const CONTACT_TYPES = new Set(["telefone", "email", "whatsapp"]);

function isContactType(value: string): value is DevedorCreateRequest["contatos"][number]["tipo"] {
  return CONTACT_TYPES.has(value);
}

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
  return !Object.hasOwn(value, key) || value[key] === null || dateTime(value[key]);
}

function contact(value: unknown): boolean {
  return isRecord(value)
    && typeof value.tipo === "string" && CONTACT_TYPES.has(value.tipo)
    && typeof value.valor === "string" && value.valor.length > 0
    && typeof value.preferencial === "boolean";
}

function validDevedor(value: unknown, context: OperationalContext): value is Devedor {
  return isRecord(value)
    && strings(value, ["id", "carteira_id", "documento", "nome", "criado_em"])
    && UUID_PATTERN.test(String(value.id))
    && value.carteira_id === context.carteira_padrao.id
    && dateTime(value.criado_em)
    && nullableDateTime(value, "atualizado_em")
    && typeof value.estado === "string" && DEVEDOR_STATES.has(value.estado)
    && Array.isArray(value.contatos) && value.contatos.every(contact);
}

function validList(value: unknown, context: OperationalContext): value is DevedoresList {
  return isRecord(value)
    && Array.isArray(value.items)
    && integers(value, ["total", "page", "size", "pages"])
    && value.items.every((item) => validDevedor(item, context));
}

function validHistory(value: unknown, context: OperationalContext, devedorId: string): value is DevedorHistory {
  return isRecord(value)
    && value.devedor_id === devedorId
    && Array.isArray(value.eventos)
    && value.eventos.every((event) => isRecord(event)
      && strings(event, ["acao", "status", "criado_em"])
      && dateTime(event.criado_em)
      && (!Object.hasOwn(event, "detalhes") || event.detalhes === null || typeof event.detalhes === "string"))
    && context.carteira_padrao.id.length > 0;
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
      mensagem: "Devedor nao encontrado ou indisponivel.",
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
      mensagem: "Nao foi possivel concluir a operacao de Devedores.",
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
  permission: DevedorPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<DevedoresReadResult<T>> {
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

export async function listDevedores(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  filters: DevedorListFilters,
  dependencies: BffDependencies,
): Promise<DevedoresReadResult<DevedoresList | Devedor>> {
  return executeRead(cookies, context, dependencies, DEVEDOR_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/devedores",
    {
      params: {
        path: { carteira_id: carteiraId },
        query: { page: filters.page, size: filters.size, ...(filters.documento ? { documento: filters.documento } : {}), ...(filters.estado ? { estado: filters.estado } : {}), ...(filters.nome ? { nome: filters.nome } : {}) },
        header: { "X-Correlation-ID": correlation },
      },
      signal,
    },
  ), (value): value is DevedoresList | Devedor => validList(value, context) || validDevedor(value, context));
}

export async function getDevedor(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  devedorId: string,
  dependencies: BffDependencies,
): Promise<DevedoresReadResult<Devedor>> {
  if (!isUuid(devedorId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Devedor invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, DEVEDOR_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}",
    { params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is Devedor => validDevedor(value, context));
}

export async function getDevedorHistory(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  devedorId: string,
  dependencies: BffDependencies,
): Promise<DevedoresReadResult<DevedorHistory>> {
  if (!isUuid(devedorId)) return { kind: "problem", problem: new ApiProblem({ status: 400, codigo: "parametro_invalido", mensagem: "Identificador do Devedor invalido.", correlationId: correlationId() }) };
  return executeRead(cookies, context, dependencies, DEVEDOR_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico",
    { params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "X-Correlation-ID": correlation } }, signal },
  ), (value): value is DevedorHistory => validHistory(value, context, devedorId));
}

function contactPayload(formData: FormData): DevedorCreateRequest["contatos"][number] | undefined {
  const tipo = formString(formData, "contato_tipo", 20);
  const valor = formString(formData, "contato_valor", 254);
  if (!tipo || !isContactType(tipo) || !valor) return undefined;
  return { preferencial: formBoolean(formData, "contato_preferencial"), tipo, valor };
}

function problemState(problem: ApiProblem): DevedorActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function successState(message: string, correlation: string): DevedorActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

async function executeMutation(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: DevedorPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, idem: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  message: string,
): Promise<DevedorActionState> {
  const requestCorrelation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    return problemState(new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: requestCorrelation }));
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const idem = idempotencyKey(true);
    if (!idem) throw new ApiProblem({ status: 400, codigo: "idempotencia_invalida", mensagem: "Idempotency-Key invalida.", correlationId: requestCorrelation });
    const result = await call(client, context.carteira_padrao.id, requestCorrelation, idem);
    if (!result.response.ok) return problemState(await safeProblem(result.response, requestCorrelation, result.error));
    if (!validDevedor(result.data, context)) {
      return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }));
    }
    return successState(message, responseCorrelation(result.response, requestCorrelation));
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return problemState(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function createDevedor(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<DevedorActionState> {
  const documento = formString(formData, "documento", 20);
  const nome = formString(formData, "nome", 200);
  const contato = contactPayload(formData);
  if (!documento || !nome || !contato) {
    return { kind: "problem", message: "Informe documento, nome e um contato valido.", status: 400, correlationId: correlationId() };
  }
  const body: DevedorCreateRequest = { contatos: [contato], documento, nome };
  return executeMutation(cookies, context, dependencies, DEVEDOR_CREATE_PERMISSION, (client, carteiraId, correlation, idem) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores",
    { body, params: { path: { carteira_id: carteiraId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), "Devedor cadastrado com sucesso.");
}

export async function updateDevedor(
  cookies: CookieStore,
  context: OperationalContext,
  devedorId: string,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<DevedorActionState> {
  if (!isUuid(devedorId)) return { kind: "problem", message: "Identificador do Devedor invalido.", status: 400, correlationId: correlationId() };
  const nome = formString(formData, "nome", 200);
  const contato = contactPayload(formData);
  const body: DevedorUpdateRequest = { ...(nome ? { nome } : {}), ...(contato ? { contatos: [contato] } : {}) };
  if (!body.nome && !body.contatos) return { kind: "problem", message: "Informe ao menos nome ou contato valido.", status: 400, correlationId: correlationId() };
  return executeMutation(cookies, context, dependencies, DEVEDOR_UPDATE_PERMISSION, (client, carteiraId, correlation, idem) => client.PATCH(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}",
    { body, params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), "Devedor atualizado com sucesso.");
}

export async function inactivateDevedor(
  cookies: CookieStore,
  context: OperationalContext,
  devedorId: string,
  dependencies: BffDependencies,
): Promise<DevedorActionState> {
  if (!isUuid(devedorId)) return { kind: "problem", message: "Identificador do Devedor invalido.", status: 400, correlationId: correlationId() };
  return executeMutation(cookies, context, dependencies, DEVEDOR_INACTIVATE_PERMISSION, (client, carteiraId, correlation, idem) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
    { params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), "Devedor inativado com sucesso.");
}

export async function reactivateDevedor(
  cookies: CookieStore,
  context: OperationalContext,
  devedorId: string,
  dependencies: BffDependencies,
): Promise<DevedorActionState> {
  if (!isUuid(devedorId)) return { kind: "problem", message: "Identificador do Devedor invalido.", status: 400, correlationId: correlationId() };
  return executeMutation(cookies, context, dependencies, DEVEDOR_REACTIVATE_PERMISSION, (client, carteiraId, correlation, idem) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar",
    { params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), "Devedor reativado com sucesso.");
}
