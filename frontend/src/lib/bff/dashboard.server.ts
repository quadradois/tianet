import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import { createBackendClient } from "@/lib/api/client.server";
import type { DashboardPeriod } from "@/lib/dashboard/dashboard-policy";
import {
  AGENDA_PERMISSION,
  COLLECTION_PERMISSION,
  hasExactPermission,
  REPORTS_PERMISSION,
} from "@/lib/dashboard/dashboard-policy";

import { ApiProblem, correlationId, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type Summary = components["schemas"]["ResumoCarteiraResponse"];
type DueDates = components["schemas"]["VencimentosInadimplenciaResponse"];
type Agenda = components["schemas"]["AgendaOperacionalResponse"];
type CollectionQueue = components["schemas"]["FilaCobrancaResponse"];
type ReadonlyCookieStore = Pick<CookieStore, "get">;

export type DashboardSectionResult<T> =
  | Readonly<{ kind: "ready"; data: T }>
  | Readonly<{ kind: "denied" }>
  | Readonly<{ kind: "problem"; problem: ApiProblem }>;

export type DashboardLoads = Readonly<{
  summary: Promise<DashboardSectionResult<Summary>>;
  dueDates: Promise<DashboardSectionResult<DueDates>>;
  agenda: Promise<DashboardSectionResult<Agenda>>;
  collection: Promise<DashboardSectionResult<CollectionQueue>>;
}>;

type TypedClient = ReturnType<typeof createBackendClient>;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const DECIMAL_PATTERN = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const SITUACOES_DE_ACERTO = new Set(["pendente", "em dia"]);
const AGENDA_STATES = new Set(["aberto", "reagendado", "concluido", "cancelado"]);
const REMINDER_STATES = new Set(["programa", "enviado", "concluido", "cancelado"]);
const COLLECTION_STATES = new Set(["pendente", "em_andamento", "encerrado"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => typeof value[key] === "string");
}

function integers(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => Number.isInteger(value[key]));
}

function uuids(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => {
    const selected = value[key];
    return typeof selected === "string" && UUID_PATTERN.test(selected);
  });
}

function decimalStrings(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && keys.every((key) => {
    const selected = value[key];
    return typeof selected === "string" && DECIMAL_PATTERN.test(selected);
  });
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

function requiredNullableUuid(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || (typeof value[key] === "string" && UUID_PATTERN.test(value[key])));
}

function requiredNullableDateTime(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || dateTime(value[key]));
}

function validSummary(value: unknown, context: OperationalContext, referenceDate: string): value is Summary {
  if (!isRecord(value)) return false;
  return strings(value, ["data_referencia"])
    && uuids(value, ["tenant_id", "carteira_id"])
    && calendarDate(value.data_referencia)
    && decimalStrings(value, ["principal_a_receber", "total_realizado"])
    && integers(value, ["total_operacoes", "operacoes_ativas", "operacoes_quitadas", "acertos_pendentes"])
    && value.tenant_id === context.tenant.id && value.carteira_id === context.carteira_padrao.id
    && value.data_referencia === referenceDate;
}

function validDueDates(value: unknown, context: OperationalContext, referenceDate: string): value is DueDates {
  if (!isRecord(value) || !Array.isArray(value.itens)) return false;
  return uuids(value, ["tenant_id", "carteira_id"])
    && calendarDate(value.data_referencia)
    && Number.isInteger(value.total)
    && value.tenant_id === context.tenant.id && value.carteira_id === context.carteira_padrao.id
    && value.data_referencia === referenceDate
    && value.itens.every((item: unknown) => isRecord(item)
      && uuids(item, ["emprestimo_id", "devedor_id"])
      && calendarDate(item.acerto_em)
      && decimalStrings(item, ["principal_original"])
      && typeof item.situacao === "string" && SITUACOES_DE_ACERTO.has(item.situacao)
      && Number.isInteger(item.dia_de_acerto)
      && Number.isInteger(item.dias_sem_pagamento));
}

function matchesItemIdentity(value: unknown, context: OperationalContext): boolean {
  return isRecord(value) && uuids(value, ["tenant_id", "carteira_id"])
    && value.tenant_id === context.tenant.id && value.carteira_id === context.carteira_padrao.id;
}

function validAgenda(value: unknown, context: OperationalContext): value is Agenda {
  return isRecord(value) && Number.isInteger(value.total) && Array.isArray(value.compromissos)
    && Array.isArray(value.lembretes)
    && value.compromissos.every((item) => isRecord(item) && matchesItemIdentity(item, context)
      && uuids(item, ["agenda_item_id", "devedor_id", "usuario_solicitante_id"])
      && requiredNullableUuid(item, "emprestimo_id") && requiredNullableDateTime(item, "atualizado_em")
      && typeof item.estado === "string" && AGENDA_STATES.has(item.estado)
      && dateTime(item.previsto_para) && typeof item.titulo === "string")
    && value.lembretes.every((item) => isRecord(item) && matchesItemIdentity(item, context)
      && uuids(item, ["agenda_item_id", "enviado_por_usuario_id", "lembrete_id"])
      && typeof item.estado === "string" && REMINDER_STATES.has(item.estado)
      && dateTime(item.horario) && typeof item.mensagem === "string");
}

function validCollection(value: unknown, context: OperationalContext): value is CollectionQueue {
  return isRecord(value) && Number.isInteger(value.total) && Array.isArray(value.items)
    && value.items.every((item) => isRecord(item) && matchesItemIdentity(item, context)
      && uuids(item, ["caso_id", "devedor_id"])
      && requiredNullableUuid(item, "emprestimo_id")
      && dateTime(item.criado_em) && decimalStrings(item, ["total_pendente"])
      && typeof item.estado === "string" && COLLECTION_STATES.has(item.estado)
      && strings(item, ["origem", "titulo"]));
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

function safeProblem(response: Response, fallback: string): ApiProblem {
  const selected = responseCorrelation(response, fallback);
  if (response.status === 400) return new ApiProblem({ status: 400, codigo: "periodo_invalido", mensagem: "O periodo informado e invalido.", correlationId: selected });
  if (response.status === 401) return new ApiProblem({ status: 401, codigo: "sessao_expirada", mensagem: "A sessao precisa ser renovada.", correlationId: selected });
  if (response.status === 403) return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Secao indisponivel para este acesso.", correlationId: selected });
  if (response.status === 404) return new ApiProblem({ status: 404, codigo: "recurso_indisponivel", mensagem: "Dados nao encontrados ou indisponiveis.", correlationId: selected });
  if (response.status === 500) return new ApiProblem({ status: 500, codigo: "erro_tecnico", mensagem: "Servico temporariamente indisponivel.", correlationId: selected });
  return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: selected });
}

function technicalProblem(correlation: string, timeout: boolean): ApiProblem {
  return new ApiProblem({
    status: timeout ? 504 : 502,
    codigo: timeout ? "timeout_backend" : "backend_indisponivel",
    mensagem: timeout ? "O servico nao respondeu no tempo esperado." : "Servico temporariamente indisponivel.",
    correlationId: correlation,
  });
}

async function execute<T>(
  dependencies: BffDependencies,
  accessToken: string,
  call: (client: TypedClient, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<DashboardSectionResult<T>> {
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
    const result = await call(client, requestCorrelation, controller.signal);
    if (result.response.status !== 200) {
      const problem = safeProblem(result.response, requestCorrelation);
      return { kind: "problem", problem };
    }
    return validate(result.data) ? { kind: "ready", data: result.data } : {
      kind: "problem",
      problem: new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }),
    };
  } catch (error) {
    if (error instanceof ApiProblem) return { kind: "problem", problem: error };
    return { kind: "problem", problem: technicalProblem(requestCorrelation, controller.signal.aborted) };
  } finally {
    clearTimeout(timer);
  }
}

function denied<T>(): Promise<DashboardSectionResult<T>> {
  return Promise.resolve({ kind: "denied" });
}

export async function beginDashboardLoads(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  period: DashboardPeriod,
  dependencies: BffDependencies,
): Promise<DashboardLoads> {
  const encrypted = cookies.get(sessionCookieName(dependencies.config))?.value;
  if (!encrypted) throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: correlationId() });
  let accessToken: string;
  try {
    const session = await unsealSession(encrypted, dependencies.config, dependencies.now?.() ?? new Date());
    if (session.userId !== context.usuario.id || session.tenantId !== context.tenant.id) throw new Error("identity mismatch");
    accessToken = session.accessToken;
  } catch {
    throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: correlationId() });
  }
  const carteiraId = context.carteira_padrao.id;
  const permissions = context.permissoes;
  const reportsAllowed = hasExactPermission(permissions, REPORTS_PERMISSION);
  return {
    summary: reportsAllowed ? execute(dependencies, accessToken, (client, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/resumo",
      { params: { path: { carteira_id: carteiraId }, query: { data_referencia: period.referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is Summary => validSummary(value, context, period.referenceDate)) : denied(),
    dueDates: reportsAllowed ? execute(dependencies, accessToken, (client, correlation, signal) => client.GET(
      "/credit/carteiras/{carteira_id}/relatorios/vencimentos",
      { params: { path: { carteira_id: carteiraId }, query: { data_referencia: period.referenceDate }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is DueDates => validDueDates(value, context, period.referenceDate)) : denied(),
    agenda: hasExactPermission(permissions, AGENDA_PERMISSION) ? execute(dependencies, accessToken, (client, correlation, signal) => client.GET(
      "/credit/agenda",
      { params: { query: { carteira_id: carteiraId, incluir_lembretes: true, janela_inicio: period.agendaStart, janela_fim: period.agendaEnd }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is Agenda => validAgenda(value, context)) : denied(),
    collection: hasExactPermission(permissions, COLLECTION_PERMISSION) ? execute(dependencies, accessToken, (client, correlation, signal) => client.GET(
      "/credit/cobrancas/casos",
      { params: { query: { carteira_id: carteiraId }, header: { "X-Correlation-ID": correlation } }, signal },
    ), (value): value is CollectionQueue => validCollection(value, context)) : denied(),
  };
}
