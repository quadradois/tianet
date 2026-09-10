import "server-only";

import { createBackendClient } from "../api/client.server";
import {
  OPENAI_MANAGE_PERMISSION, OPENAI_READ_PERMISSION, hasOpenAIPermission,
  isOpenAIChallenge, isOpenAIConnection, isOpenAIDiagnostic, isOpenAILogout,
  type OpenAIActionState, type OpenAIReadResult,
} from "../openai/openai-policy";
import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, idempotencyKey, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type TypedClient = ReturnType<typeof createBackendClient>;
const CONNECTION = "/platform/openai/conexao" as const;

function responseCorrelation(response: Response, fallback: string): string {
  return response.headers.get("X-Correlation-ID") || fallback;
}

function denied(correlation: string): ApiProblem {
  return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Ação indisponível para este acesso.", correlationId: correlation });
}

function unavailable(correlation: string): ApiProblem {
  return new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Serviço temporariamente indisponível.", correlationId: correlation });
}

function invalid(response: Response, correlation: string): ApiProblem {
  return new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "O serviço OpenAI retornou dados inválidos.", correlationId: responseCorrelation(response, correlation) });
}

function problemState(problem: ApiProblem): OpenAIActionState {
  return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
}

async function clientFor(cookies: CookieStore, dependencies: BffDependencies, correlation: string): Promise<TypedClient> {
  return createBackendClient(dependencies.config.backendUrl, {
    fetch: await createCookieAuthenticatedFetch(cookies, dependencies, correlation),
  });
}

async function responseProblem(response: Response, correlation: string): Promise<ApiProblem> {
  try { return await apiProblemFromResponse(response, responseCorrelation(response, correlation)); }
  catch { return invalid(response, correlation); }
}

export async function readOpenAIConnection(cookies: CookieStore, context: OperationalContext, dependencies: BffDependencies): Promise<OpenAIReadResult> {
  const correlation = correlationId();
  if (!hasOpenAIPermission(context.permissoes, OPENAI_READ_PERMISSION)) {
    const problem = denied(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
  try {
    const result = await (await clientFor(cookies, dependencies, correlation)).GET(CONNECTION, { params: { header: { "X-Correlation-ID": correlation } } });
    if (result.response.status !== 200) {
      const problem = await responseProblem(result.response, correlation);
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    if (!isOpenAIConnection(result.data)) {
      const problem = invalid(result.response, correlation);
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    return { kind: "ready", connection: result.data };
  } catch (error) {
    const problem = error instanceof ApiProblem ? error : unavailable(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
}

export async function beginOpenAILogin(cookies: CookieStore, context: OperationalContext, dependencies: BffDependencies): Promise<OpenAIActionState> {
  const correlation = correlationId();
  if (!hasOpenAIPermission(context.permissoes, OPENAI_MANAGE_PERMISSION)) return problemState(denied(correlation));
  try {
    const result = await (await clientFor(cookies, dependencies, correlation)).POST("/platform/openai/conexao/login", { params: { header: { "X-Correlation-ID": correlation } } });
    if (result.response.status !== 200) return problemState(await responseProblem(result.response, correlation));
    if (!isOpenAIChallenge(result.data)) return problemState(invalid(result.response, correlation));
    return { kind: "login", challenge: result.data, message: "Login iniciado. Abra o endereço oficial e informe o código.", correlationId: responseCorrelation(result.response, correlation) };
  } catch (error) { return problemState(error instanceof ApiProblem ? error : unavailable(correlation)); }
}

export async function refreshOpenAIDiagnostic(cookies: CookieStore, context: OperationalContext, dependencies: BffDependencies): Promise<OpenAIActionState> {
  const correlation = correlationId();
  if (!hasOpenAIPermission(context.permissoes, OPENAI_READ_PERMISSION)) return problemState(denied(correlation));
  try {
    const result = await (await clientFor(cookies, dependencies, correlation)).GET("/platform/openai/diagnostico", { params: { header: { "X-Correlation-ID": correlation } } });
    if (result.response.status !== 200) return problemState(await responseProblem(result.response, correlation));
    if (!isOpenAIDiagnostic(result.data)) return problemState(invalid(result.response, correlation));
    return { kind: "diagnostic", diagnostic: result.data, message: "Diagnóstico atualizado.", correlationId: responseCorrelation(result.response, correlation) };
  } catch (error) { return problemState(error instanceof ApiProblem ? error : unavailable(correlation)); }
}

export async function disconnectOpenAI(cookies: CookieStore, context: OperationalContext, dependencies: BffDependencies): Promise<OpenAIActionState> {
  const correlation = correlationId();
  if (!hasOpenAIPermission(context.permissoes, OPENAI_MANAGE_PERMISSION)) return problemState(denied(correlation));
  try {
    const result = await (await clientFor(cookies, dependencies, correlation)).DELETE(CONNECTION, {
      params: { header: { "Idempotency-Key": idempotencyKey(true) as string, "X-Correlation-ID": correlation } },
    });
    if (result.response.status !== 200) return problemState(await responseProblem(result.response, correlation));
    if (!isOpenAILogout(result.data)) return problemState(invalid(result.response, correlation));
    return { kind: "logout", logout: result.data, message: "Sessão OpenAI removida deste ambiente.", correlationId: responseCorrelation(result.response, correlation) };
  } catch (error) { return problemState(error instanceof ApiProblem ? error : unavailable(correlation)); }
}
