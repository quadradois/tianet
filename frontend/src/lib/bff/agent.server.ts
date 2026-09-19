import "server-only";

import { createBackendClient } from "../api/client.server";
import {
  AGENT_READ_PERMISSION,
  hasExactPermission,
  isAgentInbox,
  type AgentPermission,
  type AgentReadResult,
} from "../agent/agent-policy";

import { ApiProblem, apiProblemFromResponse, correlationId, createCookieAuthenticatedFetch, type BffDependencies } from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

const ROTA_INBOX = "/platform/agent/inbox" as const;

/** Leitura da inbox do agente (S3). Sem escrita, sem `Idempotency-Key`. */

function correlationOf(response: Response, fallback: string): string {
  const header = response.headers.get("X-Correlation-ID");
  return header && header.length > 0 ? header : fallback;
}

async function problemOf(response: Response, fallback: string): Promise<ApiProblem> {
  try {
    return await apiProblemFromResponse(response, correlationOf(response, fallback));
  } catch {
    return new ApiProblem({ status: response.status, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(response, fallback) });
  }
}

function negado(correlation: string): ApiProblem {
  return new ApiProblem({ status: 403, codigo: "acesso_negado", mensagem: "Acao indisponivel para este acesso.", correlationId: correlation });
}

function indisponivel(correlation: string): ApiProblem {
  return new ApiProblem({ status: 502, codigo: "backend_indisponivel", mensagem: "Servico temporariamente indisponivel.", correlationId: correlation });
}

/** Resumo + recentes da inbox do Tenant, para triagem do operador. */
export async function readAgentInbox(
  cookies: CookieStore,
  context: OperationalContext,
  dependencies: BffDependencies,
  permission: AgentPermission = AGENT_READ_PERMISSION,
): Promise<AgentReadResult> {
  const correlation = correlationId();
  if (!hasExactPermission(context.permissoes, permission)) {
    const problem = negado(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(cookies, dependencies, correlation);
    const client = createBackendClient(dependencies.config.backendUrl, { fetch: authenticatedFetch });
    const result = await client.GET(ROTA_INBOX, {
      params: { header: { "X-Correlation-ID": correlation } },
    });
    if (result.response.status !== 200) {
      const problem = await problemOf(result.response, correlation);
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    if (!isAgentInbox(result.data)) {
      const problem = new ApiProblem({ status: 502, codigo: "resposta_backend_invalida", mensagem: "Servico temporariamente indisponivel.", correlationId: correlationOf(result.response, correlation) });
      return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
    }
    return { kind: "ready", inbox: result.data };
  } catch (error) {
    const problem = error instanceof ApiProblem ? error : indisponivel(correlation);
    return { kind: "problem", message: problem.message, status: problem.status, correlationId: problem.correlationId };
  }
}
