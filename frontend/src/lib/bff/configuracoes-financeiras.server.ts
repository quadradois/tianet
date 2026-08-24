import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import { createBackendClient } from "@/lib/api/client.server";
import {
  CALENDARIO_MANAGE_PERMISSION,
  CONFIGURACOES_ACTIVATE_PERMISSION,
  CONFIGURACOES_APPROVE_PERMISSION,
  CONFIGURACOES_MANAGE_PERMISSION,
  CONFIGURACOES_READ_PERMISSION,
  MODALIDADE_MANAGE_PERMISSION,
  SNAPSHOT_CAPTURE_PERMISSION,
  formString,
  hasExactPermission,
  isCalendarDate,
  isUuid,
  type CalendarioFinanceiro,
  type ConfiguracaoFinanceira,
  type ConfiguracaoPermission,
  type ConfiguracaoState,
  type ConfiguracaoVigente,
  type ConfiguracoesActionState,
  type ConfiguracoesFilters,
  type ModalidadeFinanceira,
  type SnapshotConfiguracao,
} from "@/lib/configuracoes-financeiras/configuracoes-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;
type ReadonlyCookieStore = Pick<CookieStore, "get">;
type ConfigCreateRequest = components["schemas"]["ConfiguracaoFinanceiraCreateRequest"];
type ModalidadeCreateRequest = components["schemas"]["ModalidadeFinanceiraCreateRequest"];
type CalendarioCreateRequest = components["schemas"]["CalendarioFinanceiroCreateRequest"];
type DecisaoRequest = components["schemas"]["DecisaoConfiguracaoRequest"];
type ProgramarRequest = components["schemas"]["ProgramarConfiguracaoRequest"];
type SnapshotRequest = components["schemas"]["CapturaSnapshotConfiguracaoRequest"];
type TaxaRequest = components["schemas"]["TaxaFinanceiraRequest"];
type ParametroRequest = components["schemas"]["ParametroFinanceiroRequest"];
type PoliticaRequest = components["schemas"]["PoliticaArredondamentoRequest"];

export type ConfiguracoesSectionResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ApiProblem }>;

export type ConfiguracoesLoads = Readonly<{
  configuracoes: Promise<ConfiguracoesSectionResult<readonly ConfiguracaoFinanceira[]>>;
  vigente: Promise<ConfiguracoesSectionResult<ConfiguracaoVigente | null>>;
  modalidades: Promise<ConfiguracoesSectionResult<readonly ModalidadeFinanceira[]>>;
  calendarios: Promise<ConfiguracoesSectionResult<readonly CalendarioFinanceiro[]>>;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const DECIMAL_OR_NUMBER_PATTERN = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const STATES: ReadonlySet<string> = new Set<ConfiguracaoState>(["rascunho", "aprovada", "programada", "ativa", "substituida", "inativa"]);

const CONFIGURACOES_HEADER_CONTRACT = [
  { path: "/credit/configuracoes-financeiras", idempotent: true },
  { path: "/credit/configuracoes-financeiras/{configuracao_id}", idempotent: false },
  { path: "/credit/configuracoes-financeiras/{configuracao_id}/aprovar", idempotent: true },
  { path: "/credit/configuracoes-financeiras/{configuracao_id}/ativar", idempotent: true },
  { path: "/credit/configuracoes-financeiras/{configuracao_id}/inativar", idempotent: true },
  { path: "/credit/configuracoes-financeiras/{configuracao_id}/programar", idempotent: true },
  { path: "/credit/configuracoes-financeiras/calendarios", idempotent: true },
  { path: "/credit/configuracoes-financeiras/modalidades", idempotent: true },
  { path: "/credit/configuracoes-financeiras/snapshots", idempotent: true },
  { path: "/credit/configuracoes-financeiras/vigente", idempotent: false },
] as const;
void CONFIGURACOES_HEADER_CONTRACT;

const CONFIGURACOES_IDEMPOTENCY_MARKERS = [
  "Idempotency-Key:/credit/configuracoes-financeiras",
  "Idempotency-Key:/credit/configuracoes-financeiras/{configuracao_id}/aprovar",
  "Idempotency-Key:/credit/configuracoes-financeiras/{configuracao_id}/ativar",
  "Idempotency-Key:/credit/configuracoes-financeiras/{configuracao_id}/inativar",
  "Idempotency-Key:/credit/configuracoes-financeiras/{configuracao_id}/programar",
  "Idempotency-Key:/credit/configuracoes-financeiras/calendarios",
  "Idempotency-Key:/credit/configuracoes-financeiras/modalidades",
  "Idempotency-Key:/credit/configuracoes-financeiras/snapshots",
] as const;
void CONFIGURACOES_IDEMPOTENCY_MARKERS;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function uuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function strings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string");
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

function nullableDate(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || (typeof value[key] === "string" && isCalendarDate(value[key])));
}

function nullableDateTime(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || dateTime(value[key]));
}

function sameTenantAndWallet(value: unknown, context: OperationalContext): boolean {
  return isRecord(value)
    && value.tenant_id === context.tenant.id
    && (value.carteira_id === null || value.carteira_id === context.carteira_padrao.id);
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

async function safeProblem(response: Response, fallback: string, errorBody?: unknown): Promise<ApiProblem> {
  const selectedCorrelation = responseCorrelation(response, fallback);
  if (response.status < 400) return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 400) return new ApiProblem({ status: 400, codigo: "requisicao_invalida", mensagem: "Dados de Configuracoes Financeiras invalidos.", correlationId: selectedCorrelation });
  if (response.status === 401) return new ApiProblem({ status: 401, codigo: "sessao_expirada", mensagem: "A sessao precisa ser renovada.", correlationId: selectedCorrelation });
  if (response.status === 403) return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Configuracoes Financeiras indisponiveis para este acesso.", correlationId: selectedCorrelation });
  if (response.status === 404) return new ApiProblem({ status: 404, codigo: "recurso_indisponivel", mensagem: "Configuracao Financeira nao encontrada ou indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 409) return new ApiProblem({ status: 409, codigo: "transicao_invalida", mensagem: "Transicao indisponivel para a Configuracao Financeira atual.", correlationId: selectedCorrelation });
  if (response.status === 422) return new ApiProblem({ status: 422, codigo: "regra_violada", mensagem: "Regra de Configuracoes Financeiras rejeitou a operacao.", correlationId: selectedCorrelation });
  if (response.status >= 500) return new ApiProblem({ status: response.status, codigo: "erro_tecnico", mensagem: "Servico temporariamente indisponivel.", correlationId: selectedCorrelation });
  if (isRecord(errorBody) && typeof errorBody.codigo === "string" && typeof errorBody.mensagem === "string") {
    return new ApiProblem({ status: response.status, codigo: errorBody.codigo, mensagem: "Nao foi possivel concluir Configuracoes Financeiras.", correlationId: selectedCorrelation });
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

function validConfiguracao(value: unknown, context: OperationalContext): value is ConfiguracaoFinanceira {
  if (!sameTenantAndWallet(value, context) || !isRecord(value)) return false;
  return uuid(value.id)
    && uuid(value.calendario_id)
    && uuid(value.criada_por_usuario_id)
    && typeof value.modalidade === "string"
    && typeof value.estado === "string" && STATES.has(value.estado)
    && Number.isInteger(value.versao)
    && Number.isInteger(value.total_eventos)
    && isCalendarDate(String(value.vigencia_inicio))
    && nullableDate(value, "vigencia_fim")
    && dateTime(value.criada_em)
    && nullableDateTime(value, "atualizada_em")
    && nullableDateTime(value, "aprovada_em")
    && Object.hasOwn(value, "aprovada_por_usuario_id")
    && (value.aprovada_por_usuario_id === null || uuid(value.aprovada_por_usuario_id))
    && isRecord(value.parametros);
}

function validVigente(value: unknown, context: OperationalContext): value is ConfiguracaoVigente {
  return sameTenantAndWallet(value, context)
    && isRecord(value)
    && uuid(value.configuracao_id)
    && typeof value.modalidade === "string"
    && isRecord(value.parametros)
    && dateTime(value.consultada_em);
}

function validModalidade(value: unknown, context: OperationalContext): value is ModalidadeFinanceira {
  return sameTenantAndWallet(value, context)
    && isRecord(value)
    && uuid(value.id)
    && typeof value.ativa === "boolean"
    && strings(value, ["codigo", "nome"]);
}

function validCalendario(value: unknown, context: OperationalContext): value is CalendarioFinanceiro {
  return sameTenantAndWallet(value, context)
    && isRecord(value)
    && uuid(value.id)
    && strings(value, ["codigo", "nome"])
    && Array.isArray(value.feriados)
    && value.feriados.every((item) => typeof item === "string" && isCalendarDate(item));
}

function validSnapshot(value: unknown, context: OperationalContext): value is SnapshotConfiguracao {
  return sameTenantAndWallet(value, context)
    && isRecord(value)
    && uuid(value.configuracao_id)
    && uuid(value.capturado_por_usuario_id)
    && strings(value, ["hash_parametros", "modalidade"])
    && Number.isInteger(value.versao)
    && isRecord(value.parametros)
    && Object.hasOwn(value, "motivo")
    && (value.motivo === null || typeof value.motivo === "string")
    && dateTime(value.capturado_em);
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
  permission: ConfiguracaoPermission,
  call: (client: TypedClient, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<ConfiguracoesSectionResult<T>> {
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
    const result = await call(client, requestCorrelation, controller.signal);
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

function denied<T>(): Promise<ConfiguracoesSectionResult<T>> {
  return Promise.resolve({ kind: "denied" });
}

export async function beginConfiguracoesLoads(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  filters: ConfiguracoesFilters,
  dependencies: BffDependencies,
): Promise<ConfiguracoesLoads> {
  if (!hasExactPermission(context.permissoes, CONFIGURACOES_READ_PERMISSION)) {
    return { configuracoes: denied(), vigente: denied(), modalidades: denied(), calendarios: denied() };
  }
  const carteiraId = context.carteira_padrao.id;
  const vigenteReferencia = filters.dataReferencia;
  const vigenteModalidade = filters.modalidade;
  return {
    configuracoes: executeRead(cookies, context, dependencies, CONFIGURACOES_READ_PERMISSION, (client, correlation, signal) => client.GET(
      "/credit/configuracoes-financeiras",
      { params: { query: { carteira_id: carteiraId, ...(filters.dataReferencia ? { data_referencia: filters.dataReferencia } : {}), ...(filters.estado ? { estado: filters.estado } : {}), ...(filters.modalidade ? { modalidade: filters.modalidade } : {}) }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is readonly ConfiguracaoFinanceira[] => Array.isArray(value) && value.every((item) => validConfiguracao(item, context))),
    vigente: vigenteReferencia && vigenteModalidade
      ? executeRead(cookies, context, dependencies, CONFIGURACOES_READ_PERMISSION, (client, correlation, signal) => client.GET(
        "/credit/configuracoes-financeiras/vigente",
        { params: { query: { carteira_id: carteiraId, data_referencia: vigenteReferencia, modalidade: vigenteModalidade }, header: { "X-Correlation-ID": correlation } }, signal },
      ), (value): value is ConfiguracaoVigente => validVigente(value, context))
      : Promise.resolve({ kind: "ready", data: null }),
    modalidades: executeRead(cookies, context, dependencies, CONFIGURACOES_READ_PERMISSION, (client, correlation, signal) => client.GET(
      "/credit/configuracoes-financeiras/modalidades",
      { params: { header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is readonly ModalidadeFinanceira[] => Array.isArray(value) && value.every((item) => validModalidade(item, context))),
    calendarios: executeRead(cookies, context, dependencies, CONFIGURACOES_READ_PERMISSION, (client, correlation, signal) => client.GET(
      "/credit/configuracoes-financeiras/calendarios",
      { params: { header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is readonly CalendarioFinanceiro[] => Array.isArray(value) && value.every((item) => validCalendario(item, context))),
  };
}

function actionProblem(problem: ApiProblem): ConfiguracoesActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function actionSuccess(message: string, correlation: string): ConfiguracoesActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

function parseJsonValue(raw: string | undefined): unknown | undefined {
  if (!raw) return undefined;
  try {
    const parsed: unknown = JSON.parse(raw);
    return parsed;
  } catch {
    return undefined;
  }
}

function taxa(value: unknown): value is TaxaRequest {
  return isRecord(value)
    && typeof value.nome === "string"
    && (typeof value.valor === "number" || (typeof value.valor === "string" && DECIMAL_OR_NUMBER_PATTERN.test(value.valor)))
    && typeof value.periodicidade === "string";
}

function parametro(value: unknown): value is ParametroRequest {
  return isRecord(value) && typeof value.nome === "string" && Object.hasOwn(value, "valor");
}

function arrayOfTaxas(value: unknown): readonly TaxaRequest[] | undefined {
  return Array.isArray(value) && value.length > 0 && value.every(taxa) ? value : undefined;
}

function arrayOfParametros(value: unknown): readonly ParametroRequest[] | undefined {
  return Array.isArray(value) && value.length > 0 && value.every(parametro) ? value : undefined;
}

function politica(value: unknown): PoliticaRequest | undefined {
  if (!isRecord(value)) return undefined;
  const escala = value.escala;
  return isRecord(value)
    && typeof value.modo === "string"
    && typeof escala === "number"
    && Number.isInteger(escala)
    && escala >= 0
    && escala <= 12
    ? { escala, modo: value.modo }
    : undefined;
}

async function executeMutation<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: ConfiguracaoPermission,
  expectedStatus: number,
  call: (client: TypedClient, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
  message: string,
): Promise<ConfiguracoesActionState> {
  const requestCorrelation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    return actionProblem(new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: requestCorrelation }));
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const result = await call(client, requestCorrelation);
    if (result.response.status !== expectedStatus) return actionProblem(await safeProblem(result.response, requestCorrelation, result.error));
    if (!validate(result.data)) return actionProblem(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }));
    return actionSuccess(message, responseCorrelation(result.response, requestCorrelation));
  } catch (error) {
    if (error instanceof ApiProblem) return actionProblem(error);
    return actionProblem(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function createModalidade(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const codigo = formString(formData, "modalidade_codigo", 80);
  const nome = formString(formData, "modalidade_nome", 120);
  if (!codigo || !nome) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Informe codigo e nome da Modalidade.", correlationId: correlationId() }));
  const body: ModalidadeCreateRequest = { codigo, nome, carteira_id: context.carteira_padrao.id };
  return executeMutation(cookies, context, dependencies, MODALIDADE_MANAGE_PERMISSION, 201, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/modalidades",
    { body, params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ModalidadeFinanceira => validModalidade(value, context), "Modalidade financeira cadastrada.");
}

export async function createCalendario(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const codigo = formString(formData, "calendario_codigo", 80);
  const nome = formString(formData, "calendario_nome", 120);
  const feriados = formString(formData, "feriados", 500)
    ?.split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!codigo || !nome) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Informe codigo e nome do Calendario.", correlationId: correlationId() }));
  const body: CalendarioCreateRequest = { codigo, nome, carteira_id: context.carteira_padrao.id, ...(feriados && feriados.every(isCalendarDate) ? { feriados } : {}) };
  return executeMutation(cookies, context, dependencies, CALENDARIO_MANAGE_PERMISSION, 201, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/calendarios",
    { body, params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is CalendarioFinanceiro => validCalendario(value, context), "Calendario financeiro cadastrado.");
}

export async function createConfiguracao(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const modalidade = formString(formData, "config_modalidade", 80);
  const calendarioId = formString(formData, "config_calendario_id", 80);
  const inicio = formString(formData, "vigencia_inicio", 10);
  const fim = formString(formData, "vigencia_fim", 10);
  const taxas = arrayOfTaxas(parseJsonValue(formString(formData, "taxas_json", 2_000)));
  const parametros = arrayOfParametros(parseJsonValue(formString(formData, "parametros_json", 2_000)));
  const politicaArredondamento = politica(parseJsonValue(formString(formData, "politica_json", 500)));
  if (!modalidade || !calendarioId || !isUuid(calendarioId) || !inicio || !isCalendarDate(inicio) || !taxas || !parametros || !politicaArredondamento) {
    return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Informe configuracao financeira valida e opaca.", correlationId: correlationId() }));
  }
  const body: ConfigCreateRequest = {
    calendario_id: calendarioId,
    carteira_id: context.carteira_padrao.id,
    modalidade,
    parametros,
    politica_arredondamento: politicaArredondamento,
    taxas,
    vigencia_inicio: inicio,
    ...(fim && isCalendarDate(fim) ? { vigencia_fim: fim } : {}),
  };
  return executeMutation(cookies, context, dependencies, CONFIGURACOES_MANAGE_PERMISSION, 201, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras",
    { body, params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ConfiguracaoFinanceira => validConfiguracao(value, context), "Configuracao financeira criada em rascunho.");
}

function decisaoBody(formData: FormData): DecisaoRequest {
  return { motivo: formString(formData, "motivo", 500) ?? null };
}

function configuracaoId(formData: FormData): string | undefined {
  const id = formString(formData, "configuracao_id", 80);
  return id && isUuid(id) ? id : undefined;
}

export async function approveConfiguracao(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const id = configuracaoId(formData);
  if (!id) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Identificador da Configuracao invalido.", correlationId: correlationId() }));
  const body = decisaoBody(formData);
  return executeMutation(cookies, context, dependencies, CONFIGURACOES_APPROVE_PERMISSION, 200, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/{configuracao_id}/aprovar",
    { body, params: { path: { configuracao_id: id }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ConfiguracaoFinanceira => validConfiguracao(value, context), "Configuracao financeira aprovada.");
}

export async function programConfiguracao(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const id = configuracaoId(formData);
  const dataAtivacao = formString(formData, "data_ativacao", 10);
  if (!id || !dataAtivacao || !isCalendarDate(dataAtivacao)) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Informe data de ativacao valida.", correlationId: correlationId() }));
  const body: ProgramarRequest = { data_ativacao: dataAtivacao, motivo: formString(formData, "motivo", 500) ?? null };
  return executeMutation(cookies, context, dependencies, CONFIGURACOES_ACTIVATE_PERMISSION, 200, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/{configuracao_id}/programar",
    { body, params: { path: { configuracao_id: id }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ConfiguracaoFinanceira => validConfiguracao(value, context), "Configuracao financeira programada.");
}

export async function activateConfiguracao(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const id = configuracaoId(formData);
  if (!id) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Identificador da Configuracao invalido.", correlationId: correlationId() }));
  return executeMutation(cookies, context, dependencies, CONFIGURACOES_ACTIVATE_PERMISSION, 200, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/{configuracao_id}/ativar",
    { body: { motivo: null }, params: { path: { configuracao_id: id }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ConfiguracaoFinanceira => validConfiguracao(value, context), "Configuracao financeira ativada.");
}

export async function inactivateConfiguracao(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const id = configuracaoId(formData);
  if (!id) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Identificador da Configuracao invalido.", correlationId: correlationId() }));
  return executeMutation(cookies, context, dependencies, CONFIGURACOES_ACTIVATE_PERMISSION, 200, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/{configuracao_id}/inativar",
    { body: { motivo: null }, params: { path: { configuracao_id: id }, header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is ConfiguracaoFinanceira => validConfiguracao(value, context), "Configuracao financeira inativada.");
}

export async function captureSnapshot(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<ConfiguracoesActionState> {
  const id = configuracaoId(formData);
  if (!id) return actionProblem(new ApiProblem({ status: 400, codigo: "formulario_invalido", mensagem: "Identificador da Configuracao invalido.", correlationId: correlationId() }));
  const body: SnapshotRequest = { configuracao_id: id, motivo: formString(formData, "motivo", 500) ?? null };
  return executeMutation(cookies, context, dependencies, SNAPSHOT_CAPTURE_PERMISSION, 200, (client, correlation) => client.POST(
    "/credit/configuracoes-financeiras/snapshots",
    { body, params: { header: { "X-Correlation-ID": correlation, "Idempotency-Key": idempotencyKey(true, formString(formData, "idempotency_key", 255)) as string } } },
  ), (value): value is SnapshotConfiguracao => validSnapshot(value, context), "Snapshot contratual capturado.");
}
