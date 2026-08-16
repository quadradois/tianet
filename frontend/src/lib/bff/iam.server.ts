import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import {
  formString,
  hasExactIamPermission,
  isPermissionCode,
  isUuid,
  PERFIL_MANAGE_PERMISSION,
  PERFIL_READ_PERMISSION,
  type IamActionState,
  type IamFilters,
  type IamPermission,
  type IamReadResult,
  type Perfil,
  type PermissoesCatalogo,
  type PermissoesEfetivas,
} from "@/lib/iam/iam-policy";

import { ApiProblem, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import { sessionCookieName, type CookieStore, unsealSession } from "./session.server";

type ReadonlyCookieStore = Pick<CookieStore, "get">;
type PerfilCreateRequest = components["schemas"]["PerfilCreateRequest"];
type PerfilUpdateRequest = components["schemas"]["PerfilUpdateRequest"];

export type IamLoads = Readonly<{
  catalogo: Promise<IamReadResult<PermissoesCatalogo>>;
  perfil: Promise<IamReadResult<Perfil | null>>;
  perfis: Promise<IamReadResult<readonly Perfil[]>>;
  usuarioPermissoes: Promise<IamReadResult<PermissoesEfetivas | null>>;
}>;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const PERFIL_STATES = new Set(["ativo", "inativo"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function uuid(value: unknown): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function responseCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

function isPerfil(value: unknown, context: OperationalContext): value is Perfil {
  return isRecord(value)
    && value.tenant_id === context.tenant.id
    && uuid(value.id)
    && typeof value.nome === "string"
    && typeof value.estado === "string"
    && PERFIL_STATES.has(value.estado)
    && Array.isArray(value.permissoes)
    && value.permissoes.every((permission) => typeof permission === "string");
}

function isCatalogo(value: unknown): value is PermissoesCatalogo {
  return isRecord(value)
    && typeof value.versao === "string"
    && Array.isArray(value.itens)
    && value.itens.every((item) =>
      isRecord(item)
      && typeof item.codigo === "string"
      && typeof item.descricao === "string"
      && typeof item.grupo === "string");
}

function isPermissoesEfetivas(value: unknown, usuarioId: string): value is PermissoesEfetivas {
  return isRecord(value)
    && value.usuario_id === usuarioId
    && Object.hasOwn(value, "perfil_id")
    && (value.perfil_id === null || uuid(value.perfil_id))
    && Object.hasOwn(value, "perfil_nome")
    && (value.perfil_nome === null || typeof value.perfil_nome === "string")
    && Array.isArray(value.permissoes)
    && value.permissoes.every((permission) => typeof permission === "string");
}

function validationProblem(message: string): IamActionState {
  return { kind: "problem", message, status: 400, correlationId: correlationId() };
}

function actionProblem(error: unknown): IamActionState {
  if (error instanceof ApiProblem) return { kind: "problem", message: error.mensagem, status: error.status, correlationId: error.correlationId };
  return { kind: "problem", message: "Servico IAM temporariamente indisponivel.", status: 502, correlationId: correlationId() };
}

async function safeProblem(response: Response, fallback: string): Promise<ApiProblem> {
  const selectedCorrelation = responseCorrelation(response, fallback);
  if (response.status < 400) return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico IAM temporariamente indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 400) return new ApiProblem({ status: 400, codigo: "requisicao_invalida", mensagem: "Dados IAM invalidos.", correlationId: selectedCorrelation });
  if (response.status === 401) return new ApiProblem({ status: 401, codigo: "sessao_expirada", mensagem: "A sessao precisa ser renovada.", correlationId: selectedCorrelation });
  if (response.status === 403) return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "IAM indisponivel para este acesso.", correlationId: selectedCorrelation });
  if (response.status === 404) return new ApiProblem({ status: 404, codigo: "recurso_indisponivel", mensagem: "Recurso IAM nao encontrado ou indisponivel.", correlationId: selectedCorrelation });
  if (response.status === 409) return new ApiProblem({ status: 409, codigo: "conflito_iam", mensagem: "Conflito de IAM impediu a operacao.", correlationId: selectedCorrelation });
  if (response.status === 422) return new ApiProblem({ status: 422, codigo: "regra_violada", mensagem: "Regra IAM rejeitou a operacao.", correlationId: selectedCorrelation });
  if (response.status >= 500) return new ApiProblem({ status: response.status, codigo: "erro_tecnico", mensagem: "Servico IAM temporariamente indisponivel.", correlationId: selectedCorrelation });
  return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico IAM temporariamente indisponivel.", correlationId: selectedCorrelation });
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
    const headers = new Headers({
      Authorization: `Bearer ${accessToken}`,
      "X-Correlation-ID": requestCorrelation,
    });
    if (init.idempotency) headers.set("Idempotency-Key", init.idempotency);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const requestInit: RequestInit = {
      cache: "no-store",
      headers,
      method: init.method,
      redirect: "error",
      signal: controller.signal,
    };
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

async function executeRead<T>(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: IamPermission,
  path: string,
  validate: (value: unknown) => value is T,
): Promise<IamReadResult<T>> {
  if (!hasExactIamPermission(context.permissoes, permission)) return { kind: "denied" };
  try {
    const result = await backendFetch(cookies, context, dependencies, path, { method: "GET" });
    if (result.response.status !== 200) return { kind: "problem", problem: await safeProblem(result.response, result.correlationId) };
    if (!validate(result.data)) return { kind: "problem", problem: new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico IAM retornou dados invalidos.", correlationId: responseCorrelation(result.response, result.correlationId) }) };
    return { kind: "ready", data: result.data };
  } catch (error) {
    return { kind: "problem", problem: error instanceof ApiProblem ? error : new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico IAM temporariamente indisponivel.", correlationId: correlationId() }) };
  }
}

export async function beginIamLoads(
  cookies: ReadonlyCookieStore,
  context: OperationalContext,
  filters: IamFilters,
  dependencies: BffDependencies,
): Promise<IamLoads> {
  return {
    catalogo: executeRead(cookies, context, dependencies, PERFIL_READ_PERMISSION, "/iam/permissoes", isCatalogo),
    perfil: filters.perfilId
      ? executeRead(cookies, context, dependencies, PERFIL_READ_PERMISSION, `/iam/perfis/${encodeURIComponent(filters.perfilId)}`, (value): value is Perfil => isPerfil(value, context))
      : Promise.resolve({ kind: "ready", data: null }),
    perfis: executeRead(cookies, context, dependencies, PERFIL_READ_PERMISSION, "/iam/perfis", (value): value is readonly Perfil[] =>
      Array.isArray(value) && value.every((item) => isPerfil(item, context))),
    usuarioPermissoes: filters.usuarioId
      ? executeRead(cookies, context, dependencies, PERFIL_READ_PERMISSION, `/iam/usuarios/${encodeURIComponent(filters.usuarioId)}/permissoes`, (value): value is PermissoesEfetivas => isPermissoesEfetivas(value, filters.usuarioId ?? ""))
      : Promise.resolve({ kind: "ready", data: null }),
  };
}

async function executeMutation<T>(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  path: string,
  init: Readonly<{ body?: unknown; expectedStatus?: 200 | 201; idempotency: string; method: string }>,
  validate: (value: unknown) => value is T,
  message: string,
): Promise<IamActionState> {
  if (!hasExactIamPermission(context.permissoes, PERFIL_MANAGE_PERMISSION)) return { kind: "problem", message: "Sem permissao perfil.gerir.", status: 403, correlationId: correlationId() };
  try {
    const fetchWithSession = await createCookieAuthenticatedFetch(cookies, dependencies);
    const headers = new Headers({ "Idempotency-Key": init.idempotency, "X-Correlation-ID": correlationId() });
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const requestInit: RequestInit = {
      cache: "no-store",
      headers,
      method: init.method,
      redirect: "error",
    };
    if (init.body !== undefined) requestInit.body = JSON.stringify(init.body);
    const response = await fetchWithSession(new Request(new URL(path, dependencies.config.backendUrl), requestInit));
    const expected = init.expectedStatus ?? 200;
    if (response.status !== expected) throw await safeProblem(response, headers.get("X-Correlation-ID") ?? correlationId());
    const data = await response.clone().json();
    if (!validate(data)) throw new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico IAM retornou dados invalidos.", correlationId: responseCorrelation(response, headers.get("X-Correlation-ID") ?? correlationId()) });
    return { kind: "success", message, status: response.status, correlationId: responseCorrelation(response, headers.get("X-Correlation-ID") ?? correlationId()) };
  } catch (error) {
    return actionProblem(error);
  }
}

function mutationKey(formData: FormData): string {
  const key = idempotencyKey(true, formString(formData, "idempotency_key", 255));
  if (!key) throw new ApiProblem({ status: 400, codigo: "idempotencia_invalida", mensagem: "Idempotency-Key invalida.", correlationId: correlationId() });
  return key;
}

export async function createPerfil(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const nome = formString(formData, "nome", 120);
  if (!nome) return validationProblem("Informe o nome do Perfil.");
  const body: PerfilCreateRequest = { nome };
  return executeMutation(cookies, context, dependencies, "/iam/perfis", { body, expectedStatus: 201, idempotency: mutationKey(formData), method: "POST" }, (value): value is Perfil => isPerfil(value, context), "Perfil criado.");
}

export async function renamePerfil(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const perfilId = formString(formData, "perfil_id", 64);
  const nome = formString(formData, "nome", 120);
  if (!perfilId || !isUuid(perfilId) || !nome) return validationProblem("Informe perfil_id e nome validos.");
  const body: PerfilUpdateRequest = { nome };
  return executeMutation(cookies, context, dependencies, `/iam/perfis/${encodeURIComponent(perfilId)}`, { body, idempotency: mutationKey(formData), method: "PATCH" }, (value): value is Perfil => isPerfil(value, context), "Perfil renomeado.");
}

export async function inactivatePerfil(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const perfilId = formString(formData, "perfil_id", 64);
  if (!perfilId || !isUuid(perfilId)) return validationProblem("Informe perfil_id valido.");
  return executeMutation(cookies, context, dependencies, `/iam/perfis/${encodeURIComponent(perfilId)}/inativar`, { idempotency: mutationKey(formData), method: "POST" }, (value): value is Perfil => isPerfil(value, context), "Perfil inativado.");
}

export async function addPermissionToPerfil(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const perfilId = formString(formData, "perfil_id", 64);
  const codigo = formString(formData, "codigo", 160);
  if (!perfilId || !isUuid(perfilId) || !codigo || !isPermissionCode(codigo)) return validationProblem("Informe perfil_id e codigo de permissao validos.");
  return executeMutation(cookies, context, dependencies, `/iam/perfis/${encodeURIComponent(perfilId)}/permissoes/${encodeURIComponent(codigo)}`, { idempotency: mutationKey(formData), method: "PUT" }, (value): value is Perfil => isPerfil(value, context), "Permissao associada.");
}

export async function removePermissionFromPerfil(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const perfilId = formString(formData, "perfil_id", 64);
  const codigo = formString(formData, "codigo", 160);
  if (!perfilId || !isUuid(perfilId) || !codigo || !isPermissionCode(codigo)) return validationProblem("Informe perfil_id e codigo de permissao validos.");
  return executeMutation(cookies, context, dependencies, `/iam/perfis/${encodeURIComponent(perfilId)}/permissoes/${encodeURIComponent(codigo)}`, { idempotency: mutationKey(formData), method: "DELETE" }, (value): value is Perfil => isPerfil(value, context), "Permissao removida.");
}

export async function assignPerfilToUsuario(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const usuarioId = formString(formData, "usuario_id", 64);
  const perfilId = formString(formData, "perfil_id", 64);
  if (!usuarioId || !isUuid(usuarioId) || !perfilId || !isUuid(perfilId)) return validationProblem("Informe usuario_id e perfil_id validos.");
  return executeMutation(cookies, context, dependencies, `/iam/usuarios/${encodeURIComponent(usuarioId)}/perfil/${encodeURIComponent(perfilId)}`, { idempotency: mutationKey(formData), method: "PUT" }, (value): value is PermissoesEfetivas => isPermissoesEfetivas(value, usuarioId), "Perfil atribuido ao Usuario conhecido.");
}

export async function removePerfilFromUsuario(cookies: CookieStore, context: OperationalContext, formData: FormData, dependencies: BffDependencies): Promise<IamActionState> {
  const usuarioId = formString(formData, "usuario_id", 64);
  if (!usuarioId || !isUuid(usuarioId)) return validationProblem("Informe usuario_id valido.");
  return executeMutation(cookies, context, dependencies, `/iam/usuarios/${encodeURIComponent(usuarioId)}/perfil`, { idempotency: mutationKey(formData), method: "DELETE" }, (value): value is PermissoesEfetivas => isPermissoesEfetivas(value, usuarioId), "Perfil removido do Usuario conhecido.");
}
