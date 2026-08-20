import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  AGENDA_COMMITMENT_MANAGE_PERMISSION,
  AGENDA_READ_PERMISSION,
  AGENDA_REMINDER_MANAGE_PERMISSION,
  COMMUNICATION_READ_PERMISSION,
  COMMUNICATION_REGISTER_PERMISSION,
  NOTIFICATION_RECONCILE_PERMISSION,
  formCommunicationChannel,
  formDateTime,
  formOptionalString,
  formOptionalUuid,
  formString,
  formUuid,
  hasExactPermission,
  type AgendaActionState,
  type AgendaFilters,
  type AgendaItem,
  type AgendaPermission,
  type AgendaReadResult,
  type AgendaResponse,
  type CommunicationHistory,
  type CommunicationRecord,
  type Reminder,
} from "../agenda/agenda-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;
type CommitmentCreateRequest = components["schemas"]["CompromissoAgendaCreateRequest"];
type ReminderCreateRequest = components["schemas"]["LembreteAgendaCreateRequest"];
type RescheduleRequest = components["schemas"]["ReagendarRequest"];
type CommunicationCreateRequest = components["schemas"]["ComunicacaoManualCreateRequest"];
type LegacyReconcileRequest = components["schemas"]["ConciliacaoLegadaRequest"];
type NotificationResponse = components["schemas"]["NotificacaoResponse"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const COMMITMENT_STATES = new Set(["aberto", "reagendado", "concluido", "cancelado"]);
const REMINDER_STATES = new Set(["programa", "enviado", "concluido", "cancelado"]);
const COMMUNICATION_CHANNELS = new Set(["telefone", "email", "chat", "presencial"]);

const AGENDA_HEADER_CONTRACT = [
  { path: "/credit/agenda", idempotent: false },
  { path: "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos", idempotent: true },
  { path: "/credit/agenda/compromissos/{agenda_item_id}/lembretes", idempotent: true },
  { path: "/credit/agenda/compromissos/{agenda_item_id}/reagendar", idempotent: true },
  { path: "/credit/agenda/compromissos/{agenda_item_id}/concluir", idempotent: true },
  { path: "/credit/agenda/compromissos/{agenda_item_id}/cancelar", idempotent: true },
  { path: "/credit/agenda/lembretes/{lembrete_id}/reagendar", idempotent: true },
  { path: "/credit/agenda/lembretes/{lembrete_id}/enviar", idempotent: true },
  { path: "/credit/agenda/lembretes/{lembrete_id}/concluir", idempotent: true },
  { path: "/credit/agenda/lembretes/{lembrete_id}/cancelar", idempotent: true },
  { path: "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes", idempotent: true },
  { path: "/credit/comunicacoes", idempotent: false },
] as const;
void AGENDA_HEADER_CONTRACT;

const AGENDA_IDEMPOTENCY_MARKERS = [
  "sem-idempotency:/credit/agenda",
  "sem-idempotency:/credit/comunicacoes",
  "Idempotency-Key:/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos",
  "Idempotency-Key:/credit/agenda/compromissos/{agenda_item_id}/lembretes",
  "Idempotency-Key:/credit/agenda/compromissos/{agenda_item_id}/reagendar",
  "Idempotency-Key:/credit/agenda/compromissos/{agenda_item_id}/concluir",
  "Idempotency-Key:/credit/agenda/compromissos/{agenda_item_id}/cancelar",
  "Idempotency-Key:/credit/agenda/lembretes/{lembrete_id}/reagendar",
  "Idempotency-Key:/credit/agenda/lembretes/{lembrete_id}/enviar",
  "Idempotency-Key:/credit/agenda/lembretes/{lembrete_id}/concluir",
  "Idempotency-Key:/credit/agenda/lembretes/{lembrete_id}/cancelar",
  "Idempotency-Key:/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes",
] as const;
void AGENDA_IDEMPOTENCY_MARKERS;

function requiredIdempotencyKey(formData: FormData): AgendaActionState | string {
  try {
    const selected = idempotencyKey(true, formString(formData, "idempotency_key", 255));
    if (!selected) return validationProblem("Idempotency-Key invalida.");
    return selected;
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return validationProblem("Idempotency-Key invalida.");
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function uuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function nullableUuid(value: Record<string, unknown>, key: string): boolean {
  return Object.hasOwn(value, key) && (value[key] === null || uuid(value[key]));
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

function matchesContext(value: Record<string, unknown>, context: OperationalContext): boolean {
  return uuid(value.tenant_id)
    && uuid(value.carteira_id)
    && value.tenant_id === context.tenant.id
    && value.carteira_id === context.carteira_padrao.id;
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
      mensagem: "Agenda ou comunicacao nao encontrada ou indisponivel.",
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
      mensagem: "Nao foi possivel concluir a operacao de Agenda/Comunicacao.",
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

function validCommitment(value: unknown, context: OperationalContext, devedorId?: string): value is AgendaItem {
  return isRecord(value)
    && matchesContext(value, context)
    && uuid(value.agenda_item_id)
    && uuid(value.devedor_id)
    && (devedorId === undefined || value.devedor_id === devedorId)
    && uuid(value.usuario_solicitante_id)
    && typeof value.titulo === "string"
    && dateTime(value.previsto_para)
    && nullableUuid(value, "emprestimo_id")
    && typeof value.estado === "string"
    && COMMITMENT_STATES.has(value.estado)
    && nullableDateTime(value, "atualizado_em");
}

function validReminder(value: unknown, context: OperationalContext, agendaItemId?: string): value is Reminder {
  return isRecord(value)
    && matchesContext(value, context)
    && uuid(value.lembrete_id)
    && uuid(value.agenda_item_id)
    && (agendaItemId === undefined || value.agenda_item_id === agendaItemId)
    && uuid(value.enviado_por_usuario_id)
    && dateTime(value.horario)
    && typeof value.mensagem === "string"
    && typeof value.estado === "string"
    && REMINDER_STATES.has(value.estado);
}

function validAgenda(value: unknown, context: OperationalContext): value is AgendaResponse {
  return isRecord(value)
    && Array.isArray(value.compromissos)
    && Array.isArray(value.lembretes)
    && Number.isInteger(value.total)
    && value.compromissos.every((item) => validCommitment(item, context))
    && value.lembretes.every((item) => validReminder(item, context));
}

function validCommunication(value: unknown, context: OperationalContext, devedorId?: string): value is CommunicationRecord {
  return isRecord(value)
    && matchesContext(value, context)
    && uuid(value.registro_id)
    && nullableUuid(value, "responsavel_id")
    && typeof value.canal === "string"
    && COMMUNICATION_CHANNELS.has(value.canal)
    && dateTime(value.ocorrido_em)
    && typeof value.resumo === "string"
    && typeof value.resultado === "string"
    && nullableUuid(value, "devedor_id")
    && (devedorId === undefined || value.devedor_id === devedorId)
    && nullableUuid(value, "emprestimo_id")
    && nullableUuid(value, "cobranca_acao_id")
    && nullableUuid(value, "agenda_item_id");
}

function validCommunicationHistory(value: unknown, context: OperationalContext): value is CommunicationHistory {
  return isRecord(value)
    && Array.isArray(value.registros)
    && Number.isInteger(value.total)
    && value.registros.every((item) => validCommunication(item, context));
}

function validNotification(value: unknown, context: OperationalContext, reminderId: string): value is NotificationResponse {
  return isRecord(value)
    && uuid(value.id)
    && uuid(value.carteira_id)
    && value.carteira_id === context.carteira_padrao.id
    && uuid(value.lembrete_id)
    && value.lembrete_id === reminderId
    && uuid(value.job_id)
    && typeof value.estado === "string"
    && Object.hasOwn(value, "provider_message_id")
    && Object.hasOwn(value, "resultado_em")
    && Object.hasOwn(value, "codigo_resultado");
}

function problemState(problem: ApiProblem): AgendaActionState {
  return { correlationId: problem.correlationId, kind: "problem", message: problem.mensagem, status: problem.status };
}

function validationProblem(message: string): AgendaActionState {
  return problemState(new ApiProblem({ status: 400, codigo: "entrada_invalida", mensagem: message, correlationId: correlationId() }));
}

function successState(message: string, correlation: string): AgendaActionState {
  return { correlationId: correlation, kind: "success", message, status: 200 };
}

async function executeRead<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: AgendaPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string, signal: AbortSignal) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
): Promise<AgendaReadResult<T>> {
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
  permission: AgendaPermission,
  call: (client: TypedClient, carteiraId: string, correlation: string) => Promise<{ data?: unknown; error?: unknown; response: Response }>,
  validate: (value: unknown) => value is T,
  message: string,
): Promise<AgendaActionState> {
  const requestCorrelation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    return problemState(new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: requestCorrelation }));
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const result = await call(client, context.carteira_padrao.id, requestCorrelation);
    if (result.response.status !== 200) return problemState(await safeProblem(result.response, requestCorrelation, result.error));
    if (!validate(result.data)) {
      return problemState(new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: responseCorrelation(result.response, requestCorrelation) }));
    }
    return successState(message, responseCorrelation(result.response, requestCorrelation));
  } catch (error) {
    if (error instanceof ApiProblem) return problemState(error);
    return problemState(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}

export async function listAgenda(
  cookies: CookieStore,
  context: OperationalContext,
  filters: AgendaFilters,
  dependencies: BffDependencies,
): Promise<AgendaReadResult<AgendaResponse>> {
  return executeRead(cookies, context, dependencies, AGENDA_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET("/credit/agenda", {
    params: {
      query: {
        carteira_id: carteiraId,
        ...(filters.devedorId ? { devedor_id: filters.devedorId } : {}),
        ...(filters.emprestimoId ? { emprestimo_id: filters.emprestimoId } : {}),
        ...(filters.estado ? { estado: filters.estado } : {}),
        ...(filters.janelaInicio ? { janela_inicio: filters.janelaInicio } : {}),
        ...(filters.janelaFim ? { janela_fim: filters.janelaFim } : {}),
        incluir_lembretes: filters.incluirLembretes,
      },
      header: { "X-Correlation-ID": correlation },
    },
    signal,
  }), (value): value is AgendaResponse => validAgenda(value, context));
}

export async function listCommunications(
  cookies: CookieStore,
  context: OperationalContext,
  filters: { agendaItemId?: string; cobrancaAcaoId?: string; devedorId?: string; emprestimoId?: string },
  dependencies: BffDependencies,
): Promise<AgendaReadResult<CommunicationHistory>> {
  return executeRead(cookies, context, dependencies, COMMUNICATION_READ_PERMISSION, (client, carteiraId, correlation, signal) => client.GET("/credit/comunicacoes", {
    params: {
      query: {
        carteira_id: carteiraId,
        ...(filters.devedorId ? { devedor_id: filters.devedorId } : {}),
        ...(filters.emprestimoId ? { emprestimo_id: filters.emprestimoId } : {}),
        ...(filters.cobrancaAcaoId ? { cobranca_acao_id: filters.cobrancaAcaoId } : {}),
        ...(filters.agendaItemId ? { agenda_item_id: filters.agendaItemId } : {}),
      },
      header: { "X-Correlation-ID": correlation },
    },
    signal,
  }), (value): value is CommunicationHistory => validCommunicationHistory(value, context));
}

export async function createCommitment(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const devedorId = formUuid(formData, "devedor_id");
  const titulo = formString(formData, "titulo", 140);
  const previstoPara = formDateTime(formData, "previsto_para");
  if (!devedorId || !titulo || !previstoPara) return validationProblem("Compromisso idempotente invalido.");
  const emprestimoId = formOptionalUuid(formData, "emprestimo_id");
  const request: CommitmentCreateRequest = { titulo, previsto_para: previstoPara, ...(emprestimoId ? { emprestimo_id: emprestimoId } : {}) };
  const idem = requiredIdempotencyKey(formData);
  if (typeof idem !== "string") return idem;
  return executeMutation(cookies, context, dependencies, AGENDA_COMMITMENT_MANAGE_PERMISSION, (client, carteiraId, correlation) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos",
    { body: request, params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), (value): value is AgendaItem => validCommitment(value, context, devedorId), "Compromisso idempotente registrado.");
}

export async function createReminder(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const agendaItemId = formUuid(formData, "agenda_item_id");
  const horario = formDateTime(formData, "horario");
  const mensagem = formString(formData, "mensagem", 500);
  if (!agendaItemId || !horario || !mensagem) return validationProblem("Lembrete idempotente invalido.");
  const request: ReminderCreateRequest = { horario, mensagem };
  const idem = requiredIdempotencyKey(formData);
  if (typeof idem !== "string") return idem;
  return executeMutation(cookies, context, dependencies, AGENDA_REMINDER_MANAGE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
    "/credit/agenda/compromissos/{agenda_item_id}/lembretes",
    { body: request, params: { path: { agenda_item_id: agendaItemId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), (value): value is Reminder => validReminder(value, context, agendaItemId), "Lembrete idempotente registrado.");
}

export async function changeCommitment(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const agendaItemId = formUuid(formData, "agenda_item_id");
  const command = formString(formData, "command", 40);
  if (!agendaItemId || !command) return validationProblem("Comando de compromisso invalido.");
  const idem = requiredIdempotencyKey(formData);
  if (typeof idem !== "string") return idem;
  const headers = (correlation: string) => ({ "Idempotency-Key": idem, "X-Correlation-ID": correlation });
  const rescheduleBody = (): RescheduleRequest | undefined => {
    const novoHorario = formDateTime(formData, "novo_horario");
    return novoHorario ? { novo_horario: novoHorario } : undefined;
  };
  if (command === "reagendar-compromisso") {
    const body = rescheduleBody();
    if (!body) return validationProblem("Novo horario invalido.");
    return executeMutation(cookies, context, dependencies, AGENDA_COMMITMENT_MANAGE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
      "/credit/agenda/compromissos/{agenda_item_id}/reagendar",
      { body, params: { path: { agenda_item_id: agendaItemId }, header: headers(correlation) } },
    ), (value): value is AgendaItem => validCommitment(value, context), "Compromisso idempotente reagendado.");
  }
  const path = command === "concluir-compromisso"
    ? "/credit/agenda/compromissos/{agenda_item_id}/concluir"
    : command === "cancelar-compromisso"
      ? "/credit/agenda/compromissos/{agenda_item_id}/cancelar"
      : undefined;
  if (!path) return validationProblem("Comando de compromisso invalido.");
  return executeMutation(cookies, context, dependencies, AGENDA_COMMITMENT_MANAGE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
    path,
    { params: { path: { agenda_item_id: agendaItemId }, header: headers(correlation) } },
  ), (value): value is AgendaItem => validCommitment(value, context), "Compromisso idempotente atualizado.");
}

export async function changeReminder(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const lembreteId = formUuid(formData, "lembrete_id");
  const command = formString(formData, "command", 40);
  if (!lembreteId || !command) return validationProblem("Comando de lembrete invalido.");
  const idem = requiredIdempotencyKey(formData);
  if (typeof idem !== "string") return idem;
  const headers = (correlation: string) => ({ "Idempotency-Key": idem, "X-Correlation-ID": correlation });
  if (command === "reagendar-lembrete") {
    const novoHorario = formDateTime(formData, "novo_horario");
    if (!novoHorario) return validationProblem("Novo horario invalido.");
    return executeMutation(cookies, context, dependencies, AGENDA_REMINDER_MANAGE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
      "/credit/agenda/lembretes/{lembrete_id}/reagendar",
      { body: { novo_horario: novoHorario }, params: { path: { lembrete_id: lembreteId }, header: headers(correlation) } },
    ), (value): value is Reminder => validReminder(value, context), "Lembrete idempotente reagendado.");
  }
  if (command === "enviar-lembrete") {
    const motivo = formString(formData, "motivo", 500);
    const provider = formString(formData, "provider_message_id", 255);
    const notification = formUuid(formData, "notification_id");
    if (!motivo || !provider || !notification) return validationProblem("Conciliacao legada invalida.");
    const body: LegacyReconcileRequest = { motivo, notification_id: notification, provider_message_id: provider };
    return executeMutation(cookies, context, dependencies, NOTIFICATION_RECONCILE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
      "/credit/agenda/lembretes/{lembrete_id}/enviar",
      { body, params: { path: { lembrete_id: lembreteId }, header: headers(correlation) } },
    ), (value): value is NotificationResponse => validNotification(value, context, lembreteId), "Lembrete idempotente conciliado.");
  }
  const path = command === "concluir-lembrete"
    ? "/credit/agenda/lembretes/{lembrete_id}/concluir"
    : command === "cancelar-lembrete"
      ? "/credit/agenda/lembretes/{lembrete_id}/cancelar"
      : undefined;
  if (!path) return validationProblem("Comando de lembrete invalido.");
  return executeMutation(cookies, context, dependencies, AGENDA_REMINDER_MANAGE_PERMISSION, (client, _carteiraId, correlation) => client.POST(
    path,
    { params: { path: { lembrete_id: lembreteId }, header: headers(correlation) } },
  ), (value): value is Reminder => validReminder(value, context), "Lembrete idempotente atualizado.");
}

export async function registerCommunication(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const devedorId = formUuid(formData, "devedor_id");
  const canal = formCommunicationChannel(formData);
  const ocorridoEm = formDateTime(formData, "ocorrido_em");
  const resumo = formString(formData, "resumo", 1_000);
  const resultado = formString(formData, "resultado", 1_000);
  if (!devedorId || !canal || !ocorridoEm || !resumo || !resultado) return validationProblem("Comunicacao idempotente invalida.");
  const agendaItemId = formOptionalUuid(formData, "agenda_item_id");
  const cobrancaAcaoId = formOptionalUuid(formData, "cobranca_acao_id");
  const emprestimoId = formOptionalUuid(formData, "emprestimo_id");
  const request: CommunicationCreateRequest = {
    canal,
    ocorrido_em: ocorridoEm,
    resumo,
    resultado,
    ...(agendaItemId ? { agenda_item_id: agendaItemId } : {}),
    ...(cobrancaAcaoId ? { cobranca_acao_id: cobrancaAcaoId } : {}),
    ...(emprestimoId ? { emprestimo_id: emprestimoId } : {}),
  };
  const idem = requiredIdempotencyKey(formData);
  if (typeof idem !== "string") return idem;
  return executeMutation(cookies, context, dependencies, COMMUNICATION_REGISTER_PERMISSION, (client, carteiraId, correlation) => client.POST(
    "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes",
    { body: request, params: { path: { carteira_id: carteiraId, devedor_id: devedorId }, header: { "Idempotency-Key": idem, "X-Correlation-ID": correlation } } },
  ), (value): value is CommunicationRecord => validCommunication(value, context, devedorId), "Comunicacao idempotente registrada.");
}

export async function agendaCommand(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<AgendaActionState> {
  const command = formOptionalString(formData, "command", 40);
  if (command === "criar-compromisso") return createCommitment(cookies, context, formData, dependencies);
  if (command === "criar-lembrete") return createReminder(cookies, context, formData, dependencies);
  if (command === "reagendar-compromisso" || command === "concluir-compromisso" || command === "cancelar-compromisso") return changeCommitment(cookies, context, formData, dependencies);
  if (command === "reagendar-lembrete" || command === "enviar-lembrete" || command === "concluir-lembrete" || command === "cancelar-lembrete") return changeReminder(cookies, context, formData, dependencies);
  if (command === "registrar-comunicacao") return registerCommunication(cookies, context, formData, dependencies);
  return validationProblem("Comando de Agenda/Comunicacao invalido.");
}
