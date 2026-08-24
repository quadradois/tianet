import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import {
  formString,
  hasExactAutomacaoPermission,
  isUuid,
  JOB_CANCEL_PERMISSION,
  JOB_READ_PERMISSION,
  JOB_RETRY_PERMISSION,
  NOTIFICATION_READ_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  TEMPLATE_MANAGE_PERMISSION,
  type AutomacaoActionState,
  type AutomacaoFilters,
  type AutomacaoPermission,
  type AutomacaoReadResult,
  type Job,
  type JobList,
  type Notification,
  type NotificationList,
  type Template,
  type TemplateList,
} from "@/lib/automacao/automacao-policy";

import { ApiProblem, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type TemplateCreateRequest = components["schemas"]["TemplateCreateRequest"];
type ConciliacaoRequest = components["schemas"]["ConciliacaoRequest"];

export type AutomacaoLoads = Readonly<{
  job: Promise<AutomacaoReadResult<Job | null>>;
  jobs: Promise<AutomacaoReadResult<JobList>>;
  notification: Promise<AutomacaoReadResult<Notification | null>>;
  notifications: Promise<AutomacaoReadResult<NotificationList>>;
  templates: Promise<AutomacaoReadResult<TemplateList>>;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const JOB_STATES = new Set(["agendado", "em_execucao", "concluido", "falha_temporaria", "falha_permanente", "cancelado"]);
const NOTIFICATION_STATES = new Set(["preparada", "aceita", "falha_temporaria", "falha_permanente", "resultado_desconhecido", "conciliada"]);
const TEMPLATE_STATES = new Set(["rascunho", "aprovado", "ativo", "inativo"]);

const AUTOMACAO_OPERATION_CONTRACT = [
  "Idempotency-Key:/credit/automacao/jobs/{job_id}/cancelar",
  "Idempotency-Key:/credit/automacao/jobs/{job_id}/retry",
  "Idempotency-Key:/credit/notificacoes/templates",
  "Idempotency-Key:/credit/notificacoes/templates/{template_id}/aprovar",
  "Idempotency-Key:/credit/notificacoes/templates/{template_id}/ativar",
  "Idempotency-Key:/credit/notificacoes/{notification_id}/conciliar",
] as const;
void AUTOMACAO_OPERATION_CONTRACT;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function uuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
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
  return calendarPartsAreValid(year, month, day) && hour <= 23 && minute <= 59 && second <= 59 && offsetHour <= 23 && offsetMinute <= 59;
}

function nullableDateTime(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || dateTime(value[key]));
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

async function safeProblem(response: Response, fallback: string): Promise<ApiProblem> {
  const selectedCorrelation = responseCorrelation(response, fallback);
  if (response.status < 400) return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico de Automacao temporariamente indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 400) return new ApiProblem({ status: 400, codigo: "requisicao_invalida", mensagem: "Dados de Automacao invalidos.", correlationId: selectedCorrelation });
  if (response.status === 401) return new ApiProblem({ status: 401, codigo: "sessao_expirada", mensagem: "A sessao precisa ser renovada.", correlationId: selectedCorrelation });
  if (response.status === 403) return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Automacao indisponivel para este acesso.", correlationId: selectedCorrelation });
  if (response.status === 404) return new ApiProblem({ status: 404, codigo: "recurso_indisponivel", mensagem: "Recurso de Automacao nao encontrado ou indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 409) return new ApiProblem({ status: 409, codigo: "transicao_invalida", mensagem: "Transicao indisponivel para o estado atual da Automacao.", correlationId: selectedCorrelation });
  if (response.status === 422) return new ApiProblem({ status: 422, codigo: "regra_violada", mensagem: "Regra de Automacao rejeitou a operacao.", correlationId: selectedCorrelation });
  if (response.status >= 500) return new ApiProblem({ status: response.status, codigo: "erro_tecnico", mensagem: "Servico de Automacao temporariamente indisponivel.", correlationId: selectedCorrelation });
  return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico de Automacao temporariamente indisponivel.", correlationId: selectedCorrelation });
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

async function backendFetch(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  path: string,
  init: Readonly<{ body?: unknown; idempotency?: string; method: string }>,
): Promise<Readonly<{ correlationId: string; data: unknown; response: Response }>> {
  const requestCorrelation = correlationId();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  try {
    const accessToken = await readAccessToken(cookies, dependencies, context);
    const headers = new Headers({ Authorization: `Bearer ${accessToken}`, "X-Correlation-ID": requestCorrelation });
    if (init.idempotency) headers.set("Idempotency-Key", init.idempotency);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const requestInit: RequestInit = { cache: "no-store", headers, method: init.method, redirect: "error", signal: controller.signal };
    if (init.body !== undefined) requestInit.body = JSON.stringify(init.body);
    const response = await dependencies.fetch(new Request(new URL(path, dependencies.config.backendUrl), requestInit));
    let data: unknown;
    try {
      data = await response.clone().json();
    } catch {
      data = undefined;
    }
    return { correlationId: requestCorrelation, data, response };
  } finally {
    clearTimeout(timer);
  }
}

function validJob(value: unknown, context: OperationalContext): value is Job {
  const attemptsAreValid = isRecord(value)
    && typeof value.tentativas === "number"
    && typeof value.max_tentativas === "number"
    && Number.isInteger(value.tentativas)
    && Number.isInteger(value.max_tentativas)
    && value.tentativas >= 0 && value.max_tentativas >= 1 && value.tentativas <= value.max_tentativas;
  return isRecord(value)
    && uuid(value.id)
    && value.carteira_id === context.carteira_padrao.id
    && typeof value.tipo === "string"
    && typeof value.origem_tipo === "string"
    && uuid(value.origem_id)
    && typeof value.estado === "string" && JOB_STATES.has(value.estado)
    && dateTime(value.executar_em)
    && nullableDateTime(value, "proxima_execucao_em")
    && attemptsAreValid
    && typeof value.cancelamento_solicitado === "boolean"
    && typeof value.correlation_id === "string";
}

function validNotification(value: unknown, context: OperationalContext): value is Notification {
  const reminderIsValid = isRecord(value)
    && (!Object.hasOwn(value, "lembrete_id")
      || value.lembrete_id === null
      || uuid(value.lembrete_id));
  return isRecord(value)
    && uuid(value.id)
    && value.carteira_id === context.carteira_padrao.id
    && reminderIsValid
    && uuid(value.job_id)
    && typeof value.estado === "string" && NOTIFICATION_STATES.has(value.estado)
    && Object.hasOwn(value, "provider_message_id")
    && (value.provider_message_id === null || typeof value.provider_message_id === "string")
    && nullableDateTime(value, "resultado_em")
    && Object.hasOwn(value, "codigo_resultado")
    && (value.codigo_resultado === null || typeof value.codigo_resultado === "string");
}

function validTemplate(value: unknown): value is Template {
  return isRecord(value)
    && uuid(value.id)
    && typeof value.codigo === "string"
    && Number.isInteger(value.versao)
    && typeof value.estado === "string" && TEMPLATE_STATES.has(value.estado)
    && typeof value.hash_conteudo === "string"
    && nullableDateTime(value, "aprovado_em")
    && nullableDateTime(value, "ativado_em");
}

function validPage(value: unknown, itemGuard: (item: unknown) => boolean): boolean {
  return isRecord(value)
    && Array.isArray(value.items)
    && value.items.every(itemGuard)
    && typeof value.total === "number" && Number.isInteger(value.total) && value.total >= 0
    && typeof value.page === "number" && Number.isInteger(value.page) && value.page >= 1
    && typeof value.size === "number" && Number.isInteger(value.size) && value.size >= 1
    && typeof value.pages === "number" && Number.isInteger(value.pages) && value.pages >= 0;
}

async function executeRead<T>(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: AutomacaoPermission,
  path: string,
  validate: (value: unknown) => value is T,
): Promise<AutomacaoReadResult<T>> {
  if (!hasExactAutomacaoPermission(context.permissoes, permission)) return { kind: "denied" };
  try {
    const result = await backendFetch(cookies, context, dependencies, path, { method: "GET" });
    if (result.response.status !== 200) return { kind: "problem", problem: await safeProblem(result.response, result.correlationId) };
    if (!validate(result.data)) return { kind: "problem", problem: new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico de Automacao retornou dados invalidos.", correlationId: responseCorrelation(result.response, result.correlationId) }) };
    return { kind: "ready", data: result.data };
  } catch (error) {
    return { kind: "problem", problem: error instanceof ApiProblem ? error : new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico de Automacao temporariamente indisponivel.", correlationId: correlationId() }) };
  }
}

export async function beginAutomacaoLoads(cookies: ReadonlyCookieStore, context: OperationalContext, filters: AutomacaoFilters, dependencies: BffDependencies): Promise<AutomacaoLoads> {
  const page = `page=${filters.page}&size=${filters.size}&carteira_id=${encodeURIComponent(context.carteira_padrao.id)}`;
  return {
    job: filters.jobId
      ? executeRead(cookies, context, dependencies, JOB_READ_PERMISSION, `/credit/automacao/jobs/${encodeURIComponent(filters.jobId)}`, (value): value is Job => validJob(value, context))
      : Promise.resolve({ kind: "ready", data: null }),
    jobs: executeRead(cookies, context, dependencies, JOB_READ_PERMISSION, `/credit/automacao/jobs?${page}`, (value): value is JobList => validPage(value, (item) => validJob(item, context))),
    notification: filters.notificationId
      ? executeRead(cookies, context, dependencies, NOTIFICATION_READ_PERMISSION, `/credit/notificacoes/${encodeURIComponent(filters.notificationId)}`, (value): value is Notification => validNotification(value, context))
      : Promise.resolve({ kind: "ready", data: null }),
    notifications: executeRead(cookies, context, dependencies, NOTIFICATION_READ_PERMISSION, `/credit/notificacoes?${page}`, (value): value is NotificationList => validPage(value, (item) => validNotification(item, context))),
    templates: executeRead(cookies, context, dependencies, TEMPLATE_MANAGE_PERMISSION, `/credit/notificacoes/templates?page=${filters.page}&size=${filters.size}`, (value): value is TemplateList => validPage(value, validTemplate)),
  };
}

function validationProblem(message: string): AutomacaoActionState {
  return { kind: "problem", message, status: 400, correlationId: correlationId() };
}

function actionProblem(error: unknown): AutomacaoActionState {
  if (error instanceof ApiProblem) return { kind: "problem", message: error.mensagem, status: error.status, correlationId: error.correlationId };
  return { kind: "problem", message: "Servico de Automacao temporariamente indisponivel.", status: 502, correlationId: correlationId() };
}

async function executeMutation<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: AutomacaoPermission,
  path: string,
  init: Readonly<{ body?: unknown; expectedStatus?: 200 | 201 | 202; idempotency?: string; method: string }>,
  validate: (value: unknown) => value is T,
  message: string,
): Promise<AutomacaoActionState> {
  if (!hasExactAutomacaoPermission(context.permissoes, permission)) return { kind: "problem", message: "Sem permissao para Automacao.", status: 403, correlationId: correlationId() };
  try {
    const fetchWithSession = await createCookieAuthenticatedFetch(cookies, dependencies);
    const requestCorrelation = correlationId();
    const headers = new Headers({ "X-Correlation-ID": requestCorrelation });
    if (init.idempotency) headers.set("Idempotency-Key", init.idempotency);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const requestInit: RequestInit = { cache: "no-store", headers, method: init.method, redirect: "error" };
    if (init.body !== undefined) requestInit.body = JSON.stringify(init.body);
    const response = await fetchWithSession(new Request(new URL(path, dependencies.config.backendUrl), requestInit));
    const expected = init.expectedStatus ?? 200;
    if (response.status !== expected) throw await safeProblem(response, requestCorrelation);
    const data = await response.clone().json();
    if (!validate(data)) throw new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico de Automacao retornou dados invalidos.", correlationId: responseCorrelation(response, requestCorrelation) });
    return { kind: "success", message, status: response.status, correlationId: responseCorrelation(response, requestCorrelation) };
  } catch (error) {
    return actionProblem(error);
  }
}

function mutationKey(formData: FormData): string {
  const key = idempotencyKey(true, formString(formData, "idempotency_key", 255));
  if (!key) throw new ApiProblem({ status: 400, codigo: "idempotencia_invalida", mensagem: "Idempotency-Key invalida.", correlationId: correlationId() });
  return key;
}

export async function cancelJob(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const jobId = formString(formData, "job_id", 64);
  if (!isUuid(jobId)) return validationProblem("Informe job_id valido.");
  return executeMutation(cookies, context, dependencies, JOB_CANCEL_PERMISSION, `/credit/automacao/jobs/${encodeURIComponent(jobId)}/cancelar`, { expectedStatus: 202, idempotency: mutationKey(formData), method: "POST" }, (value): value is Job => validJob(value, context), "Job recebeu pedido de cancelamento.");
}

export async function retryJob(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const jobId = formString(formData, "job_id", 64);
  if (!isUuid(jobId)) return validationProblem("Informe job_id valido.");
  return executeMutation(cookies, context, dependencies, JOB_RETRY_PERMISSION, `/credit/automacao/jobs/${encodeURIComponent(jobId)}/retry`, { expectedStatus: 202, idempotency: mutationKey(formData), method: "POST" }, (value): value is Job => validJob(value, context), "Retry tecnico solicitado.");
}

export async function createTemplate(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const codigo = formString(formData, "codigo", 120);
  const assunto = formString(formData, "assunto", 300);
  const corpo = formString(formData, "corpo", 5000);
  const versaoRaw = formString(formData, "versao", 20);
  const versao = versaoRaw ? Number(versaoRaw) : NaN;
  if (!codigo || !assunto || !corpo || !Number.isInteger(versao) || versao < 1) return validationProblem("Informe template valido.");
  const body: TemplateCreateRequest = { assunto, codigo, corpo, parametros_permitidos: [], versao };
  return executeMutation(cookies, context, dependencies, TEMPLATE_MANAGE_PERMISSION, "/credit/notificacoes/templates", { body, expectedStatus: 201, idempotency: mutationKey(formData), method: "POST" }, validTemplate, "Template criado.");
}

export async function approveTemplate(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const templateId = formString(formData, "template_id", 64);
  if (!isUuid(templateId)) return validationProblem("Informe template_id valido.");
  return executeMutation(cookies, context, dependencies, TEMPLATE_MANAGE_PERMISSION, `/credit/notificacoes/templates/${encodeURIComponent(templateId)}/aprovar`, { idempotency: mutationKey(formData), method: "POST" }, validTemplate, "Template aprovado.");
}

export async function activateTemplate(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const templateId = formString(formData, "template_id", 64);
  if (!isUuid(templateId)) return validationProblem("Informe template_id valido.");
  return executeMutation(cookies, context, dependencies, TEMPLATE_MANAGE_PERMISSION, `/credit/notificacoes/templates/${encodeURIComponent(templateId)}/ativar`, { idempotency: mutationKey(formData), method: "POST" }, validTemplate, "Template ativado.");
}

export async function reconcileNotification(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AutomacaoActionState> {
  const notificationId = formString(formData, "notification_id", 64);
  const motivo = formString(formData, "motivo", 500);
  const providerMessageId = formString(formData, "provider_message_id", 255);
  if (!isUuid(notificationId) || !motivo || !providerMessageId) return validationProblem("Informe notificacao, provider_message_id e motivo validos.");
  let key: string;
  try {
    key = mutationKey(formData);
  } catch (error) {
    return actionProblem(error);
  }
  const body: ConciliacaoRequest = { motivo, provider_message_id: providerMessageId };
  return executeMutation(cookies, context, dependencies, NOTIFICATION_RECONCILE_PERMISSION, `/credit/notificacoes/${encodeURIComponent(notificationId)}/conciliar`, { body, idempotency: key, method: "POST" }, (value): value is Notification => validNotification(value, context), "Notificacao conciliada.");
}
