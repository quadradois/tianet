import "server-only";

import type { components } from "@/lib/api/openapi.generated";
import { createBackendClient } from "@/lib/api/client.server";

import {
  apiProblemFromResponse,
  ApiProblem,
  correlationId,
  createCookieAuthenticatedFetch,
  type BffDependencies,
} from "./backend.server";
import {
  assertTrustedMutation,
  sessionCookieName,
  type CookieStore,
  type SessionData,
  unsealSession,
} from "./session.server";

export type OperationalContext = components["schemas"]["ContextoOperacionalResponse"];

type ReadonlyCookieStore = Pick<CookieStore, "get">;

const CORRELATION_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;

export function recoveryAttemptCookieName(config: BffDependencies["config"]): string {
  return config.production ? "__Host-frontend-recovery-attempt" : "frontend_recovery_attempt";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasRequiredIdentity(value: unknown): value is Readonly<{ id: string; nome: string }> {
  return isRecord(value) && typeof value.id === "string" && value.id.length > 0
    && typeof value.nome === "string" && value.nome.length > 0;
}

function isContextUser(value: unknown): value is OperationalContext["usuario"] {
  return isRecord(value)
    && typeof value.id === "string" && value.id.length > 0
    && typeof value.nome === "string" && value.nome.length > 0
    && typeof value.email === "string" && value.email.length > 0;
}

function isContextTenant(value: unknown): value is OperationalContext["tenant"] {
  return isRecord(value)
    && typeof value.id === "string" && value.id.length > 0
    && typeof value.nome === "string" && value.nome.length > 0
    && typeof value.identificador_institucional === "string"
    && value.identificador_institucional.length > 0;
}

export function isOperationalContext(value: unknown): value is OperationalContext {
  if (!isRecord(value) || !isContextUser(value.usuario) || !isContextTenant(value.tenant)
    || !hasRequiredIdentity(value.carteira_padrao)) return false;
  if (value.perfil !== null && !hasRequiredIdentity(value.perfil)) return false;
  if (!Array.isArray(value.permissoes) || !value.permissoes.every((permission) => typeof permission === "string")) return false;
  return value.perfil !== null || value.permissoes.length === 0;
}

function contextMatchesSession(context: OperationalContext, session: SessionData): boolean {
  return context.usuario.id === session.userId && context.tenant.id === session.tenantId;
}

function selectedCorrelation(response: Response, fallback: string): string {
  const received = response.headers.get("X-Correlation-ID");
  return received && CORRELATION_PATTERN.test(received) ? received : fallback;
}

function responseHeaders(correlation: string): HeadersInit {
  return { "Cache-Control": "no-store, private", "X-Correlation-ID": correlation };
}

function problemResponse(problem: ApiProblem): Response {
  return Response.json(problem.toJSON(), { status: problem.status, headers: responseHeaders(problem.correlationId) });
}

function invalidBackendResponse(correlation: string): ApiProblem {
  return new ApiProblem({
    status: 502,
    codigo: "resposta_backend_invalida",
    mensagem: "O servico esta temporariamente indisponivel.",
    correlationId: correlation,
  });
}

async function contextProblem(response: Response, error: unknown, fallback: string): Promise<ApiProblem> {
  if (response.status === 500) return apiProblemFromResponse(response, fallback);
  if ((response.status !== 401 && response.status !== 409) || !isRecord(error)
    || typeof error.codigo !== "string" || typeof error.mensagem !== "string") {
    return invalidBackendResponse(selectedCorrelation(response, fallback));
  }
  return new ApiProblem({
    status: response.status,
    codigo: error.codigo,
    mensagem: error.mensagem,
    correlationId: selectedCorrelation(response, fallback),
  });
}

export async function loadOperationalContext(
  cookies: ReadonlyCookieStore,
  dependencies: BffDependencies,
  requestCorrelation = correlationId(),
): Promise<OperationalContext> {
  const encrypted = cookies.get(sessionCookieName(dependencies.config))?.value;
  if (!encrypted) {
    throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: requestCorrelation });
  }
  let session;
  try {
    session = await unsealSession(encrypted, dependencies.config, dependencies.now?.() ?? new Date());
  } catch {
    throw new ApiProblem({ status: 401, codigo: "sessao_invalida", mensagem: "Sessao ausente, invalida ou expirada.", correlationId: requestCorrelation });
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), dependencies.timeoutMs ?? 10_000);
  try {
    const client = createBackendClient(dependencies.config.backendUrl, {
      fetch: async (request) => {
        if (new URL(request.url).origin !== new URL(dependencies.config.backendUrl).origin) {
          throw invalidBackendResponse(requestCorrelation);
        }
        const headers = new Headers(request.headers);
        headers.set("Authorization", `Bearer ${session.accessToken}`);
        headers.set("X-Correlation-ID", requestCorrelation);
        return dependencies.fetch(new Request(request, { cache: "no-store", headers, redirect: "error", signal: controller.signal }));
      },
    });
    const result = await client.GET("/iam/contexto-atual", {
      headers: { "X-Correlation-ID": requestCorrelation },
      signal: controller.signal,
    });
    if (!result.response.ok) {
      throw await contextProblem(result.response, result.error, requestCorrelation);
    }
    const payload: unknown = result.data;
    if (!isOperationalContext(payload) || !contextMatchesSession(payload, session)) {
      throw invalidBackendResponse(requestCorrelation);
    }
    return payload;
  } catch (error) {
    if (error instanceof ApiProblem) throw error;
    if (controller.signal.aborted) {
      throw new ApiProblem({ status: 504, codigo: "timeout_backend", mensagem: "O servico nao respondeu no tempo esperado.", correlationId: requestCorrelation });
    }
    throw new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "O servico esta temporariamente indisponivel.", correlationId: requestCorrelation });
  } finally {
    clearTimeout(timer);
  }
}

export async function handleContextBootstrap(
  request: Request,
  cookies: CookieStore,
  dependencies: BffDependencies,
): Promise<Response> {
  const requestCorrelation = correlationId(request.headers.get("X-Correlation-ID"));
  try {
    try {
      assertTrustedMutation(request, dependencies.config);
    } catch {
      throw new ApiProblem({ status: 403, codigo: "origem_recusada", mensagem: "Origem da solicitacao recusada.", correlationId: requestCorrelation });
    }
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation);
    const response = await authenticatedFetch(new Request(`${dependencies.config.backendUrl}/iam/contexto-atual`, {
      cache: "no-store",
      headers: { "X-Correlation-ID": requestCorrelation },
      method: "GET",
      redirect: "error",
      signal: request.signal,
    }));
    if (!response.ok) {
      let error: unknown;
      try { error = await response.clone().json(); } catch { error = undefined; }
      throw await contextProblem(response, error, requestCorrelation);
    }
    let body: unknown;
    try {
      body = await response.clone().json();
    } catch {
      body = undefined;
    }
    if (!isOperationalContext(body)) throw invalidBackendResponse(requestCorrelation);
    const updatedEncrypted = cookies.get(sessionCookieName(dependencies.config))?.value;
    if (!updatedEncrypted) throw invalidBackendResponse(requestCorrelation);
    let updatedSession: SessionData;
    try {
      updatedSession = await unsealSession(updatedEncrypted, dependencies.config, dependencies.now?.() ?? new Date());
    } catch {
      throw invalidBackendResponse(requestCorrelation);
    }
    if (!contextMatchesSession(body, updatedSession)) throw invalidBackendResponse(requestCorrelation);
    cookies.set(recoveryAttemptCookieName(dependencies.config), "1", {
      httpOnly: true,
      maxAge: 60,
      path: "/",
      priority: "high",
      sameSite: "lax",
      secure: dependencies.config.production,
    });
    const returnedCorrelation = selectedCorrelation(response, requestCorrelation);
    return new Response(null, { status: 204, headers: responseHeaders(returnedCorrelation) });
  } catch (error) {
    if (error instanceof ApiProblem) return problemResponse(error);
    return problemResponse(new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "O servico esta temporariamente indisponivel.", correlationId: requestCorrelation }));
  }
}
